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
import enum
import pathlib
import threading

from kernel.manifest import Manifest, load_manifest
from kernel.router import AxonRouter
from kernel.services import Service


class Tier(enum.Enum):
    """Where an admitted program currently lives.

    The Connectome Manager's core job is moving programs between
    storage tiers (see `planning/01-architecture.md` § "The kernel
    is a Connectome Manager"). The MVP implements the two tiers that
    matter for "is this program running":

      - ``GPU``  — the Sutra runtime is instantiated and resident on
        the GPU; the program executes on every tick.
      - ``DISC`` — the program is at rest: admitted (route entry
        kept, reloadable) but its Sutra runtime is torn down and it
        holds zero GPU memory. It does not run.

    A ``RAM`` cold-store tier (a *running* program checkpointed to
    host memory and resumed bit-exact) is deliberately NOT modelled
    yet: that needs the Sutra ``serialise-process-state`` primitive,
    which does not exist. Naming the gap, not faking a tier.
    """

    GPU = "gpu"
    DISC = "disc"


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
        # Per-process storage tier. admit() binds the service
        # (compiles its Sutra runtime → GPU-resident), so a freshly
        # admitted process starts on the GPU tier.
        self._tier: dict[str, Tier] = {}

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
            # bind() may have updated the router's manifest entry
            # (e.g. SutraService auto-populates axon_keys from the
            # compiled module's AXON_KEYS_READ if the manifest didn't
            # declare them). Re-read so the AdmittedProcess in our
            # table reflects the final form, not the pre-bind copy.
            final_manifest = self._router._processes.get(  # noqa: SLF001
                manifest.name, manifest,
            )
            ap = AdmittedProcess(manifest=final_manifest, service=service)
            self._table[manifest.name] = ap
            # admit() bound the service: its Sutra runtime is
            # instantiated and (when CUDA is present) GPU-resident.
            self._tier[manifest.name] = Tier.GPU
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
            self._tier.pop(name, None)
            self._compute_pool_free += ap.manifest.compute_units

    # --- GPU residency: load / unload (the Connectome Manager's job) -

    def unload(self, name: str) -> None:
        """Evict a program from the GPU. It stays admitted (route
        entry kept, reloadable) but its Sutra runtime is torn down,
        its GPU memory freed, and it no longer runs on `tick()`.

        Raises `AdmissionError` if not admitted. Raises
        `NotImplementedError` (from the service) if the service
        cannot be individually evicted (e.g. shared-runtime).
        Idempotent: unloading an already-unloaded program is a no-op.
        """
        with self._lock:
            if name not in self._table:
                raise AdmissionError(
                    f"process {name!r} is not admitted; cannot unload"
                )
            ap = self._table[name]
            ap.service.unload()
            self._tier[name] = Tier.DISC

    def load(self, name: str) -> None:
        """(Re)instantiate a program's Sutra runtime so it is
        GPU-resident and runs again. Idempotent: loading an
        already-loaded program is a no-op. Raises `AdmissionError`
        if not admitted."""
        with self._lock:
            if name not in self._table:
                raise AdmissionError(
                    f"process {name!r} is not admitted; cannot load"
                )
            ap = self._table[name]
            ap.service.load()
            self._tier[name] = Tier.GPU

    def tier(self, name: str) -> Tier:
        """The storage tier a program currently lives in."""
        with self._lock:
            if name not in self._tier:
                raise AdmissionError(
                    f"process {name!r} is not admitted"
                )
            return self._tier[name]

    def gpu_resident(self) -> list[str]:
        """Names of programs currently resident on the GPU."""
        with self._lock:
            return sorted(
                n for n, t in self._tier.items() if t is Tier.GPU
            )

    # --- tick scheduler (sequential; v0.1 will swap for GPU-tick) ---

    def tick(self) -> dict[str, int]:
        """Run one tick: every **GPU-resident** admitted service
        drains its inbox once.

        A program that has been `unload()`-ed is on the DISC tier —
        it is not on the GPU, so it does not run. It still appears
        in the returned dict (count 0) so callers can see it was
        skipped, not silently dropped.

        Returns a per-process dict of axons-processed counts. The
        order is not promised stable; the production GPU-tick model
        runs every GPU-resident process simultaneously.
        """
        counts: dict[str, int] = {}
        # Snapshot the table so a service that deregisters another
        # mid-tick doesn't blow up the iteration.
        with self._lock:
            snapshot = [
                (ap, self._tier.get(ap.manifest.name, Tier.GPU))
                for ap in self._table.values()
            ]
        for ap, tier in snapshot:
            if tier is Tier.GPU:
                counts[ap.manifest.name] = ap.service.tick()
            else:
                counts[ap.manifest.name] = 0  # unloaded — not on GPU
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
