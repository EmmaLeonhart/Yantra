"""Service abstraction for the kernel.

A `Service` is what backs an admitted process. It has two lifecycle
hooks the kernel calls:

  - `bind(manifest, router)` — once, at admission, so the service
    knows its name (for capability checks) and how to send axons.
  - `tick() -> int` — once per kernel tick, drains any inbound axons
    and pushes any outbound ones. Returns the count of inbound
    axons processed (used by `Init.tick()` to report activity).

In v0.0 we ship two service implementations:

  - `PythonService`  — base class wrapping a Python `tick` callback.
                       The two example services below use it.
  - `EchoService`    — receives any axon on its inbox, re-emits it
                       on `R_output`. Demonstrates send + receive.
  - `SinkService`    — receives axons, increments a counter, emits
                       a `R_stat` axon every N ticks.

The `.su` loading path — wrap a Sutra-compiled module so the kernel
treats it the same as a `PythonService` — is sketched in
`load_su_service()` and explicitly stubbed: it raises
`NotImplementedError` until the v0.1 work wires it through. The
seed `services/echo.su` source file ships so the shape of a real
`.su` service is on disk to point future work at.
"""

from __future__ import annotations

import pathlib
from typing import Any, Callable

from kernel.manifest import Manifest
from kernel.router import Axon, AxonRouter, CapabilityError


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


class PythonService(Service):
    """A service whose tick is a plain Python callback.

    The callback receives the bound service (so it can `emit`) and
    one inbound axon at a time, returning whatever it emits as a side
    effect. Per-axon-per-call so the callback shape stays simple;
    `tick()` loops over the inbox.
    """

    def __init__(self, on_axon: Callable[["PythonService", Axon], None]) -> None:
        self._on_axon = on_axon

    def tick(self) -> int:
        n = 0
        for ax in self._router.drain(self.name):
            self._on_axon(self, ax)
            n += 1
        return n


class EchoService(PythonService):
    """Receive on any read role; re-emit identical payload on R_output.

    Capability discipline: the manifest must list `R_output` in
    write_roles; otherwise the emit raises CapabilityError on the
    first inbound axon, which is the right way to surface a
    misconfigured manifest.
    """

    def __init__(self, *, output_role: str = "R_output") -> None:
        self._output_role = output_role
        super().__init__(on_axon=self._echo)

    def _echo(self, svc: "EchoService", ax: Axon) -> None:
        svc.emit(self._output_role, ax.payload)


class SinkService(PythonService):
    """Count inbound axons; emit a stat axon every `report_every` ticks."""

    def __init__(
        self, *, stat_role: str = "R_stat", report_every: int = 1,
    ) -> None:
        self._stat_role = stat_role
        self._report_every = report_every
        self._count = 0
        self._since_last_report = 0
        super().__init__(on_axon=self._absorb)

    @property
    def count(self) -> int:
        return self._count

    def _absorb(self, svc: "SinkService", ax: Axon) -> None:
        self._count += 1
        self._since_last_report += 1
        if self._since_last_report >= self._report_every:
            # Emit only if the sender's manifest grants R_stat. If the
            # service was misconfigured, the router will raise on send
            # and the test will catch it — better than silently dropping.
            try:
                svc.emit(self._stat_role, {"count": self._count})
            except CapabilityError:
                # The sink wasn't given write capability for R_stat.
                # That's a manifest bug; surface it on the next tick
                # by re-raising. We swallow here only to allow tests
                # to inspect `count` after a misconfigured run.
                self._since_last_report = 0
                raise
            self._since_last_report = 0


def load_su_service(  # pragma: no cover — stub, see docstring
    source: str | pathlib.Path,
) -> Service:
    """Load a `.su` source file and wrap it as a `Service`.

    Stubbed in v0.0. The wiring needs:
      1. Read the source file.
      2. Lex + parse via `external/Sutra/sdk/sutra-compiler/sutra_compiler`.
      3. `torch_translate(module, llm_model=..., runtime_dim=axon_width)`
         to a Python source string.
      4. exec into a fresh module dict.
      5. Wrap the module's `on_axon`-shaped function as a `PythonService`
         callback.

    The `examples/multi_program_axon/_run.py` in the Sutra repo shows
    steps 1-4 working; the missing piece is the Sutra-side convention
    for "what does a service-shaped .su program export?" — that lands
    in the next iteration. Until then, services are PythonService
    instances written in Python; the v0.0 demonstrates the kernel
    framework, not the .su integration.
    """
    raise NotImplementedError(
        f"loading {source}: .su service wrapping is staged for v0.1; "
        f"see kernel/services.py docstring for the wiring plan."
    )
