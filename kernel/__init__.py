"""Yantra kernel — multi-process runtime nucleus.

This package is the v0.0 of the Yantra kernel: the Python-side
init/resource-manager + axon router that admits Sutra services as
processes, gives each one a fixed budget at admission time, and
routes axons between them with capability checks.

What is real here:

- Manifest format and parsing (`manifest.py`).
- Per-process admission control against a fixed pool budget,
  refusing new admissions cleanly when the pool is exhausted
  (`init.py`).
- An in-memory axon router with capability check on both write
  (sender must possess the role) and read (receiver must possess
  the role) (`router.py`).
- A service abstraction that does NOT yet require a `.su` file —
  Python-callable services and `.su`-compiled services are both
  supported; in v0.0 the included services are Python stubs
  (`services.py`) and one example `.su` file showing the shape
  the real ones will take (`services/echo.su`).

What is stubbed and known to be stubbed:

- "Fixed GPU memory arena" allocation is currently book-keeping
  only — the runtime tracks a budget pool but does not carve out
  actual device memory. This matches what a v0.0 can do without
  the multi-process runtime that lives in Sutra itself.
- Inter-process concurrency is thread-based, not GPU-tick-based.
  A real Yantra kernel runs all admitted processes simultaneously
  on the GPU at each tick; the v0.0 schedules service ticks
  sequentially on the CPU.
- Service failure isolation is not enforced. A misbehaving
  service can crash the runtime in v0.0; capability discipline
  is what's enforced, not memory isolation.

These stubs are documented at the call sites where they bite, so
that the v0.1 work knows what to harden.
"""

from kernel.manifest import Manifest, ManifestError, load_manifest
from kernel.router import (
    Axon,
    AxonRouter,
    CapabilityError,
    NotAdmittedError,
)
from kernel.init import (
    AdmissionError,
    Init,
    PoolExhaustedError,
)
from kernel.services import EchoService, PythonService, SinkService

__all__ = [
    "AdmissionError",
    "Axon",
    "AxonRouter",
    "CapabilityError",
    "EchoService",
    "Init",
    "Manifest",
    "ManifestError",
    "NotAdmittedError",
    "PoolExhaustedError",
    "PythonService",
    "SinkService",
    "load_manifest",
]
