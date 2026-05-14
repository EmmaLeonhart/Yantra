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

    def emit(self, role: str, payload: Any) -> int:
        """Send an axon; capability check happens in the router."""
        return self._router.send(
            Axon(role=role, payload=payload, from_proc=self.name)
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
    ) -> None:
        self._source_path = pathlib.Path(source_path)
        self._entry_point = entry_point
        self._output_role = output_role
        self._llm_model = llm_model
        self._compiled_module: types.ModuleType | None = None
        self._on_axon: Callable[[Any], Any] | None = None

    def bind(self, *, manifest: Manifest, router: AxonRouter) -> None:
        super().bind(manifest=manifest, router=router)
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

    def tick(self) -> int:
        if self._on_axon is None:
            raise RuntimeError(
                f"SutraService for {self._source_path.name!r} not bound; "
                f"call init.admit(...) first"
            )
        n = 0
        for inbound in self._router.drain(self.name):
            outbound = self._on_axon(inbound.payload)
            self.emit(self._output_role, outbound)
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
