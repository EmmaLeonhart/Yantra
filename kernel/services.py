"""Service abstraction for the kernel.

A `Service` is what backs an admitted process. It has two lifecycle
hooks the kernel calls:

  - `bind(manifest, router)` — once at admission, so the service
    knows its name (for capability checks) and how to send axons.
  - `tick() -> int` — once per kernel tick, drains any inbound
    axons and pushes any outbound ones. Returns the count of
    inbound axons processed.

**The default service implementation in this kernel is `SutraService`
— a real Sutra-compiled `.su` program whose `on_axon(vector) -> vector`
function is invoked on every inbound axon, with the result emitted on
the configured output role.** The Python `PythonService` exists only
for tests and harness code that doesn't need real Sutra compute.

Compilation pattern follows
`external/Sutra/examples/multi_program_axon/_run.py`: lex → parse →
torch_translate → exec into a fresh module → call the exposed
function. The first call into a freshly-compiled service downloads
the embedding model on first use (handled by Sutra's runtime),
which can be slow on cold start; subsequent calls reuse the cached
embedding tables.
"""

from __future__ import annotations

import dataclasses
import os
import pathlib
import sys
import types
from typing import Any, Callable

from kernel.manifest import Manifest
from kernel.router import Axon, AxonRouter, CapabilityError


# Make the Sutra compiler importable from the submodule. We do this
# at module-import time rather than per-call so SutraService can rely
# on the import succeeding in __init__.
_SUTRA_SDK = pathlib.Path(__file__).resolve().parent.parent / "external" / "Sutra" / "sdk" / "sutra-compiler"
if _SUTRA_SDK.is_dir() and str(_SUTRA_SDK) not in sys.path:
    sys.path.insert(0, str(_SUTRA_SDK))


class Service:
    """Base class. The only protocol the kernel actually depends on."""

    def bind(self, *, manifest: Manifest, router: AxonRouter) -> None:
        self._manifest = manifest
        self._router = router

    @property
    def name(self) -> str:
        return self._manifest.name

    def emit(
        self, role: str, payload: Any,
        *, keys: frozenset[str] | set[str] = frozenset(),
    ) -> int:
        """Send an axon; capability check + lazy-skip happen in the router.

        `keys` is the set of axon-internal keys actually bound in
        `payload`. Pass it (the Sutra compiler emits this set in
        production; for v0.0 the calling service passes it
        explicitly) to enable the router's lazy-skip filter against
        receivers' `axon_keys` declarations. Empty (default) =
        eager-fallback: the router delivers to every receiver on
        the role regardless.
        """
        return self._router.send(
            Axon(
                role=role, payload=payload, from_proc=self.name,
                keys=frozenset(keys),
            )
        )

    def tick(self) -> int:  # pragma: no cover — overridden
        raise NotImplementedError


class SutraService(Service):
    """A service whose computation is a real Sutra-compiled .su program.

    The `.su` source must export a function whose name is given by
    `entry_point` (default: "on_axon") with signature
    `(vector) -> vector`. On each tick, the service drains its inbox
    and invokes `entry_point(payload)` once per inbound axon, then
    emits the returned vector on `output_role`.

    Inputs and outputs are torch tensors of shape `(axon_width,)` —
    the axon-shaped vectors Sutra programs operate on natively. The
    router carries them through as the `payload` field of `Axon`.

    **Lazy axon evaluation: the compiled module's `AXON_KEYS_BOUND`
    and `AXON_KEYS_READ` constants** (emitted by Sutra v0.3.3+'s
    static-analysis pass) drive the kernel router's lazy delivery:

      - On `bind()`, if the receiver's manifest has empty
        `axon_keys`, the service auto-populates it from the compiled
        module's `AXON_KEYS_READ` so the router can skip-deliver
        based on what the .su source actually reads — no need to
        hand-write `axon_keys` in the manifest TOML.
      - On `tick()` emission, the service tags outgoing axons with
        the compiled module's `AXON_KEYS_BOUND` so receivers'
        intersection check has data to work with.

    Compilation happens in `bind()`, not in `__init__()`, so the
    service can read the manifest's `axon_width` for the
    `runtime_dim` parameter. First compile of a fresh `.su` source
    downloads the embedding model (Sutra's first-use side effect);
    subsequent compiles in the same process reuse the cache.
    """

    def __init__(
        self,
        *,
        source_path: str | pathlib.Path,
        entry_point: str = "on_axon",
        output_role: str,
        llm_model: str = "nomic-embed-text",
        runtime: Any = None,
        runtime_program_name: str | None = None,
    ) -> None:
        self._source_path = pathlib.Path(source_path)
        self._entry_point = entry_point
        self._output_role = output_role
        self._llm_model = llm_model
        # Optional shared MultiProcessRuntime (Sutra v0.4.0+).
        # When provided, `bind()` skips per-service compilation and
        # pulls handles + key sets from the shared runtime instead.
        # `runtime_program_name` is the name the program is registered
        # under in the runtime — required when `runtime` is set.
        self._runtime = runtime
        self._runtime_program_name = runtime_program_name
        if runtime is not None and runtime_program_name is None:
            raise ValueError(
                "SutraService(runtime=...) also requires runtime_program_name"
            )
        self._compiled_module: types.ModuleType | None = None
        self._on_axon: Callable[[Any], Any] | None = None
        # Populated from compiled-module constants in bind(). Used
        # for lazy axon evaluation (router-side skip-uninterested-
        # receivers + out-emission key tagging).
        self._axon_keys_bound: frozenset[str] = frozenset()
        self._axon_keys_read: frozenset[str] = frozenset()

    @property
    def axon_keys_bound(self) -> frozenset[str]:
        """Keys this service binds (from the compiled module's static analysis)."""
        return self._axon_keys_bound

    @property
    def axon_keys_read(self) -> frozenset[str]:
        """Keys this service reads (from the compiled module's static analysis)."""
        return self._axon_keys_read

    def bind(self, *, manifest: Manifest, router: AxonRouter) -> None:
        super().bind(manifest=manifest, router=router)
        if self._runtime is not None:
            # Shared-runtime path: pull handles from the
            # MultiProcessRuntime instead of compiling here.
            # The runtime already compiled this program at
            # construction time and rebound its _VSA to the
            # shared one; we just need to surface the entry
            # point + key sets to ourselves.
            name = self._runtime_program_name
            assert name is not None  # ctor guarantees this
            prog = self._runtime._programs.get(name)  # noqa: SLF001
            if prog is None:
                raise KeyError(
                    f"SutraService(runtime=...) program {name!r} not "
                    f"admitted to the runtime; admitted: "
                    f"{self._runtime.admitted()}"
                )
            self._compiled_module = prog.module
            self._on_axon = prog.on_axon
            self._axon_keys_bound = prog.axon_keys_bound
            self._axon_keys_read = prog.axon_keys_read
        else:
            # Per-service-compile path (original v0.0 behaviour).
            self._compiled_module = _compile_su_to_module(
                self._source_path,
                llm_model=self._llm_model,
                runtime_dim=manifest.axon_width,
            )
            if not hasattr(self._compiled_module, self._entry_point):
                raise AttributeError(
                    f"{self._source_path} compiled module has no "
                    f"`{self._entry_point}` symbol; available: "
                    f"{[n for n in dir(self._compiled_module) if not n.startswith('_')]}"
                )
            self._on_axon = getattr(self._compiled_module, self._entry_point)
            # Pull the static-analysis results out of the compiled
            # module. Always present in Sutra v0.3.3+; getattr with
            # frozenset() default keeps us safe against an older
            # compiled module slipping in via cache.
            self._axon_keys_bound = frozenset(
                getattr(self._compiled_module, "AXON_KEYS_BOUND", frozenset())
            )
            self._axon_keys_read = frozenset(
                getattr(self._compiled_module, "AXON_KEYS_READ", frozenset())
            )
        # Register the per-receiver projection function with the
        # router. Sutra v0.3.5+ ships _VSA.axon_project. With this
        # registered, the router can slim payloads to per-receiver
        # interest sets at delivery time. Older compiled modules
        # that lack axon_project fall through to no projection —
        # router delivers the full payload, which is correct but
        # bandwidth-non-optimal.
        if hasattr(self._compiled_module._VSA, "axon_project"):
            vsa = self._compiled_module._VSA

            def _project(payload, requested_keys):
                # Frozenset → list for the runtime API.
                return vsa.axon_project(payload, list(requested_keys))

            router.register_projector(manifest.name, _project)
        # If the manifest didn't hand-declare axon_keys, auto-populate
        # from what the compiled .su actually reads. The router only
        # checks the receiver-side (axon_keys), not the sender-side
        # (it gets that via Axon.keys at send-time), so this hooks
        # the static-analysis result into the router's lazy-skip
        # path without any router changes. Manifests that DID
        # declare axon_keys are respected as-is — explicit override.
        if not manifest.axon_keys and self._axon_keys_read:
            # Manifests are frozen dataclasses; rebuild with the new
            # axon_keys value, then re-register the route entry so
            # the router knows about the now-non-empty interest set.
            new_manifest = dataclasses.replace(
                manifest, axon_keys=self._axon_keys_read,
            )
            # Swap the manifest in the router's process table. Done
            # in-place — the router reads receiver.axon_keys at
            # send-time so updating the dict entry is enough.
            router._processes[manifest.name] = new_manifest  # noqa: SLF001
            # Update self._manifest too so the property surfaces the
            # right values.
            self._manifest = new_manifest

    def tick(self) -> int:
        if self._on_axon is None:
            raise RuntimeError(
                f"SutraService for {self._source_path.name!r} not bound; "
                f"call init.admit(...) first"
            )
        n = 0
        for inbound in self._router.drain(self.name):
            outbound = self._on_axon(inbound.payload)
            # Tag outgoing axons with the producer's bound-keys set
            # so receivers' lazy-skip intersection check has data
            # to work with. emit() forwards these to the router.
            self.emit(
                self._output_role, outbound, keys=self._axon_keys_bound,
            )
            n += 1
        return n


def _compile_su_to_module(
    src_path: pathlib.Path, *, llm_model: str, runtime_dim: int,
) -> types.ModuleType:
    """Compile a .su file via the PyTorch backend.

    Pattern mirrors external/Sutra/examples/multi_program_axon/_run.py:
    lex → parse → torch_translate → exec into a fresh module dict.
    Each call returns a freshly-compiled module so two services
    instantiated from the same .su file have independent state.
    """
    # Lazy-import inside the function so that environments without the
    # Sutra SDK on sys.path can still import kernel.services as long
    # as they don't actually instantiate a SutraService.
    from sutra_compiler.codegen_pytorch import translate_module as torch_translate
    from sutra_compiler.lexer import Lexer
    from sutra_compiler.parser import Parser

    src_path = pathlib.Path(src_path).resolve()
    if not src_path.is_file():
        raise FileNotFoundError(f"Sutra source not found: {src_path}")
    src = src_path.read_text(encoding="utf-8")

    lexer = Lexer(src, file=str(src_path))
    tokens = lexer.tokenize()
    parser = Parser(tokens, file=str(src_path), diagnostics=lexer.diagnostics)
    module_ast = parser.parse_module()
    py_src = torch_translate(module_ast, llm_model=llm_model, runtime_dim=runtime_dim)

    mod = types.ModuleType(src_path.stem)
    mod.__file__ = f"<compiled from {src_path}>"
    exec(compile(py_src, mod.__file__, "exec"), mod.__dict__)
    return mod


def make_shared_sutra_services(
    specs: list[dict],
    *,
    llm_model: str = "nomic-embed-text",
    runtime_dim: int = 768,
) -> tuple[Any, list["SutraService"]]:
    """Construct N SutraServices over a single shared MultiProcessRuntime.

    `specs` is a list of dicts:
      [{"name": str, "source_path": Path, "output_role": str,
        "entry_point": str = "on_axon"}, ...]

    Returns (runtime, services). The runtime is a Sutra v0.4.0
    `MultiProcessRuntime`; the services are constructed wired to it,
    so admission to the same `Init` shares one _VSA + codebook +
    embedding cache across all of them. Reduces per-service compile
    overhead and makes cross-service axon-passing coherent without
    each service rebuilding its own rotation cache.

    The kernel `Init.admit()` workflow is unchanged — call it once
    per returned service. The shared runtime is held alive by the
    services' references to it (each service stores its
    `runtime=...`); callers don't need to keep a separate reference
    unless they want runtime-level operations like
    `runtime.axon_project(...)` or `runtime.tick("name", input)`.

    Sutra v0.4.0+ required.
    """
    # Lazy import — only callers that actually use shared services
    # pay the import cost. Same pattern as _compile_su_to_module.
    from sutra_compiler.multi_process import (
        MultiProcessRuntime,
        ProgramSpec,
    )

    program_specs = [
        ProgramSpec(
            name=s["name"],
            source_path=pathlib.Path(s["source_path"]),
            entry_point=s.get("entry_point", "on_axon"),
        )
        for s in specs
    ]
    runtime = MultiProcessRuntime(
        program_specs, llm_model=llm_model, runtime_dim=runtime_dim,
    )
    services = [
        SutraService(
            source_path=s["source_path"],
            entry_point=s.get("entry_point", "on_axon"),
            output_role=s["output_role"],
            llm_model=llm_model,
            runtime=runtime,
            runtime_program_name=s["name"],
        )
        for s in specs
    ]
    return runtime, services


# --- Python service variant — for harness code only ---------------------


class PythonService(Service):
    """A Python-callback service. For tests + harnesses, NOT real services.

    Real kernel services use SutraService. PythonService exists so
    that admission control + router behaviour can be tested without
    paying the cost of compiling a .su file (which downloads the
    embedding model on first use). Production code should not use
    this.
    """

    def __init__(self, on_axon: Callable[["PythonService", Axon], None]) -> None:
        self._on_axon = on_axon

    def tick(self) -> int:
        n = 0
        for ax in self._router.drain(self.name):
            self._on_axon(self, ax)
            n += 1
        return n
