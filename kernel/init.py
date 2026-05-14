"""init / resource manager — admission control for the GPU pool.

Per `planning/01-architecture.md`, init is a small CPU-side program
that:

  - Loads manifests + admits processes against a fixed pool budget.
  - Maintains the table of active vs cold-stored processes.
  - Refuses new admissions cleanly when the pool is exhausted.
  - Does NOT schedule — the GPU runs every admitted process
    simultaneously.

In v0.0:

  - "GPU pool budget" is a single integer counter. Admission
    decrements it; deregistration increments it back. Real device-
    memory carve-outs are NOT performed; this is bookkeeping only.
    Documented limitation; the v0.1 multi-process Sutra runtime
    needs to make this real.
  - Eviction to RAM cold-store (per `planning/03-process-lifecycle.md`)
    is not implemented in v0.0. Either a process is admitted, or
    its admission was refused.
"""

from __future__ import annotations

import dataclasses
import pathlib
import threading

from kernel.manifest import Manifest, load_manifest
from kernel.router import AxonRouter
from kernel.services import Service


class AdmissionError(RuntimeError):
    """Generic admission failure (use a subclass for specifics)."""


class PoolExhaustedError(AdmissionError):
    """The compute-units pool does not have room for this process."""


@dataclasses.dataclass(frozen=True)
class AdmittedProcess:
    """A live process: manifest + the service handle running its code."""
    manifest: Manifest
    service: Service


class Init:
    """The kernel's resource manager.

    Holds the live process table and a budget counter. Wraps an
    `AxonRouter` instance — admit/deregister keep both sides in sync.
    """

    def __init__(self, *, compute_pool: int, router: AxonRouter | None = None) -> None:
        if compute_pool <= 0:
            raise ValueError(
                f"compute_pool must be positive, got {compute_pool}"
            )
        self._lock = threading.RLock()
        self._compute_pool_total = compute_pool
        self._compute_pool_free = compute_pool
        self._router = router or AxonRouter()
        self._table: dict[str, AdmittedProcess] = {}

    # --- admission lifecycle ---

    def admit(self, manifest: Manifest, service: Service) -> AdmittedProcess:
        """Admit a process if its budget fits. Wires it to the router."""
        with self._lock:
            if manifest.name in self._table:
                raise AdmissionError(
                    f"process {manifest.name!r} is already admitted"
                )
            if manifest.compute_units > self._compute_pool_free:
                raise PoolExhaustedError(
                    f"cannot admit {manifest.name!r}: needs "
                    f"{manifest.compute_units} compute_units, only "
                    f"{self._compute_pool_free} of {self._compute_pool_total} "
                    f"free in the pool"
                )
            # Validate write_roles ⊆ {role names from any manifest's
            # read_roles + this manifest's read_roles + this manifest's
            # write_roles}. Loose check: a write to a role nobody reads
            # is allowed (black-hole, see router docstring) — we only
            # check write_roles ∩ read_roles consistency lazily at
            # send-time. Nothing to do at admission.
            self._router.register(manifest)
            service.bind(manifest=manifest, router=self._router)
            self._compute_pool_free -= manifest.compute_units
            ap = AdmittedProcess(manifest=manifest, service=service)
            self._table[manifest.name] = ap
            return ap

    def admit_from_path(
        self, manifest_path: str | pathlib.Path, service: Service,
    ) -> AdmittedProcess:
        """Convenience: load the manifest from a TOML file, then admit."""
        manifest = load_manifest(manifest_path)
        return self.admit(manifest, service)

    def deregister(self, name: str) -> None:
        """Remove a process; free its budget; tear down its routes."""
        with self._lock:
            if name not in self._table:
                raise AdmissionError(
                    f"process {name!r} is not admitted; cannot deregister"
                )
            ap = self._table.pop(name)
            self._router.deregister(name)
            self._compute_pool_free += ap.manifest.compute_units

    # --- tick scheduler (sequential; v0.1 will swap for GPU-tick) ---

    def tick(self) -> dict[str, int]:
        """Run one tick: every admitted service drains its inbox once.

        Returns a per-process dict of axons-processed counts. The
        order is not promised stable; the production GPU-tick model
        runs every admitted process simultaneously.
        """
        counts: dict[str, int] = {}
        # Snapshot the table so a service that deregisters another
        # mid-tick doesn't blow up the iteration.
        with self._lock:
            snapshot = list(self._table.values())
        for ap in snapshot:
            counts[ap.manifest.name] = ap.service.tick()
        return counts

    # --- introspection ---

    @property
    def router(self) -> AxonRouter:
        return self._router

    @property
    def compute_pool_total(self) -> int:
        return self._compute_pool_total

    @property
    def compute_pool_free(self) -> int:
        with self._lock:
            return self._compute_pool_free

    def admitted(self) -> list[str]:
        with self._lock:
            return sorted(self._table)
