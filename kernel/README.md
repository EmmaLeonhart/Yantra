# `kernel/` — multi-process runtime nucleus (v0.0)

The smallest thing that demonstrates Yantra's process model
end-to-end. Per `planning/01-architecture.md`, the kernel is a CPU-side
init/resource-manager + axon router that admits Sutra services as
processes, gives each one a fixed budget at admission time, and
routes axons between them with capability checks.

## What runs today

```bash
python -m pytest tests/test_kernel.py -v
```

19 tests pass. The flagship test
(`test_echo_sink_round_trip_with_real_manifests`) admits an `echo`
service and a `sink` service from real manifest TOML files, sends
three payloads via a `producer` process, runs one tick, and verifies
all three round-tripped from producer → echo → sink with the
capability check firing on every hop.

## Layout

| File | Purpose |
|---|---|
| `manifest.py` | TOML manifest parser. One process per manifest. |
| `router.py`   | Axon router with capability check on send + receive. |
| `init.py`     | Resource manager: admission against a fixed pool budget; tick scheduler. |
| `services.py` | `Service` base class + `PythonService` + `EchoService` + `SinkService`. Stub `load_su_service()` for v0.1. |
| `manifests/`  | `echo.toml`, `sink.toml` — declarative process descriptors. |
| `services/`   | `echo.su`, `sink.su` — seed Sutra source for the v0.1 `.su` loader. |

## What is real, what is stubbed

**Real** in v0.0:

- Manifest parsing with structured validation errors.
- Per-process admission against a fixed `compute_pool` budget;
  refusal-on-exhaustion is clean (`PoolExhaustedError`); deregister
  releases budget.
- Capability check on write (sender must hold the role) and read
  (receiver must hold the role) at every send.
- Black-hole policy: a send to a role no admitted process reads is
  audited and dropped, not raised — startup-order tolerance per
  `planning/01-architecture.md`.
- Multi-receiver fan-out (one role, N readers ⇒ N delivered).
- `tick()` scheduler that drains every service's inbox once per tick
  and reports per-process processed counts.

**Stubbed** in v0.0 — documented at the call sites:

- **GPU memory arena allocation.** `compute_units` in the manifest
  is bookkeeping only; the runtime does not yet carve out actual
  GPU memory per process. The v0.1 multi-process Sutra runtime
  needs to make this real.
- **Concurrency model.** v0.0 is single-threaded: `Init.tick()`
  iterates services sequentially. Production Yantra runs all
  admitted processes simultaneously on the GPU at each tick. The
  service abstraction is concurrency-agnostic — a v0.1 scheduler
  that runs services in parallel can drop in without changing the
  service interface.
- **`.su` service loading.** `services.load_su_service()` raises
  `NotImplementedError` with a docstring pointing at the wiring
  plan. v0.0 services are Python (`PythonService` subclasses); the
  seed `.su` files in `services/` document the convention real
  services will follow.
- **Eviction to RAM cold-store.** `planning/03-process-lifecycle.md`
  describes admit/active/cold-store/evict. v0.0 only implements
  admit + deregister. Cold-store is v0.2 work.

## How to add a new service in v0.0

1. Write a manifest TOML in `kernel/manifests/<name>.toml` with the
   process's `axon_width`, `compute_units`, `read_roles`,
   `write_roles`, and `source` (path to the eventual `.su` file).
2. Either subclass `PythonService` and implement `tick()` directly,
   or use `PythonService(on_axon=callable)` for a pure-callback
   service.
3. Admit it: `init.admit_from_path("kernel/manifests/<name>.toml", svc)`.
4. Drive it: `init.tick()` runs every service's tick once.

When v0.1 wires up the `.su` loader, step 2 changes to "drop the
service's `.su` source under `kernel/services/<name>.su`" and the
manifest's `source` field actually loads.

## Hard things deliberately out of scope

- **Bit-exact eviction-and-resume serialisation.** See `planning/17-memory-model.md`.
- **CPU/GPU boundary cost (interrupts, MMIO).** See `paper/paper.md` § 3.5.
- **Adversarial-perturbation robustness of rotation operators.** See
  `paper/paper.md` § 3.3.1. The router's capability check is
  process-name-based in v0.0 (a sender's claim of identity is trusted
  because the sender is admitted by init); rotation-operator-based
  capability check is the production model and is gated on the v0.1
  `.su` loader landing.

These aren't oversights; they're problems the architecture defers to
specific other documents and other layers, and v0.0 is honest about
where its contribution ends.
