# `kernel/` — Connectome Manager Python prototype (v0.0)

> **What this is.** A **behavioural reference** for what the Rust
> orchestrator in `planning/19-boot-sequence.md` § "Stage 4" does
> once boot is complete: admission control, axon routing,
> capability checks, the tick loop. Sutra is doing the actual
> computation — each service is a real Sutra-compiled `.su` program
> whose `on_axon(vector) -> vector` runs on real torch tensors —
> but the orchestration layer is Python in this repo as a
> short-term implementation choice. The Rust port reimplements the
> same shape; this Python pins the API.
>
> **What this is NOT.**
>
> 1. Not the bootloader. The bootloader runs at stage 3 of
>    `planning/19-boot-sequence.md`, before any interpreter
>    exists, against bare hardware. It is **necessarily Rust or C**.
>    Python cannot be a bootloader; the boot path runs before any
>    interpreter is loaded.
> 2. Partial model of the production axon router. `router.py` now
>    implements the **kernel slice of lazy axon evaluation**:
>    receivers declare which `axon_keys` they read in their
>    manifest, producers attach `keys=...` when they emit, and the
>    router skips delivery to any receiver whose interest set
>    doesn't intersect the axon's key set. Audit counter
>    `lazy_skipped_count()` tracks how often this fires. See
>    `planning/20-lazy-axon-evaluation.md`. **What's still
>    upstream-Sutra-dependent**: per-receiver projection (slicing
>    the payload tensor to materialize only the dimensions the
>    receiver references). The kernel here only decides
>    deliver-or-skip the full payload, not slice within it.
> 3. Not a model of multi-process GPU concurrency. `tick()`
>    iterates services sequentially on CPU. Real Yantra runs all
>    admitted programs simultaneously on the GPU at every tick.
>    Single-program-per-tick is a CPU-side stand-in.
> 4. Not a model of the storage-tier moves the Connectome Manager
>    actually does. The disc ↔ RAM ↔ GPU shuffling that is the
>    Connectome Manager's primary job is not implemented; v0.0
>    only does in-memory admit/deregister.

## What runs today

```bash
# All kernel tests (19 unit + 6 real-Sutra integration = 25):
python -m pytest tests/test_kernel.py tests/test_kernel_sutra.py -v
```

**`tests/test_kernel_sutra.py` is the one that proves Sutra is
running.** It admits two real `SutraService`s — `echo.su` and
`sink.su` compiled by the Sutra v0.3.1 compiler — and routes a
real `torch.randn(768)` tensor through the chain
producer → echo (Sutra compute) → sink (Sutra compute), verifying
the receive end gets a real torch tensor back. The first test in
that file pays the embedding-model download cost (~tens of seconds
to minutes on cold cache); the rest reuse the cached compile.

`tests/test_kernel.py` is the unit-test layer for admission
control + router + capability check, using Python stand-ins so
the unit tests don't pay the Sutra compile cost.

## Layout

| File | Purpose |
|---|---|
| `manifest.py` | TOML manifest parser. One process per manifest. |
| `router.py`   | Axon router with capability check on send + receive. |
| `init.py`     | Resource manager: admission against a fixed pool budget; tick scheduler. |
| `services.py` | `Service` base + `SutraService` (compiles + runs `.su` programs) + `PythonService` (test/harness only). |
| `manifests/`  | `echo.toml`, `sink.toml` — declarative process descriptors. |
| `services/`   | `echo.su`, `sink.su` — real Sutra source executed by the Sutra v0.3.1 compiler at admission time. |

## What is real, what is stubbed

**Real** in v0.0:

- **Real Sutra compute.** `SutraService` compiles a `.su` source
  at admission time via the Sutra v0.3.1 compiler in
  `external/Sutra/sdk/sutra-compiler/`, exposes its `on_axon`
  function, and invokes it on every inbound axon. Inputs and
  outputs are real torch tensors of shape `(axon_width,)`. Tested
  end-to-end in `tests/test_kernel_sutra.py`.
- Manifest parsing with structured validation errors.
- Per-process admission against a fixed `compute_pool` budget;
  refusal-on-exhaustion is clean (`PoolExhaustedError`); deregister
  releases budget.
- Capability check on write (sender must hold the role) and read
  (receiver must hold the role) at every send. Fires the same way
  whether the service is `SutraService` or `PythonService`.
- Black-hole policy: a send to a role no admitted process reads is
  audited and dropped, not raised — startup-order tolerance per
  `planning/01-architecture.md`.
- Multi-receiver fan-out (one role, N readers ⇒ N delivered).
- `tick()` scheduler that drains every service's inbox once per tick
  and reports per-process processed counts.

**Honestly out of scope** in v0.0 — these all require upstream
Sutra-side work that hasn't shipped:

- **Real per-process GPU memory arenas.** `compute_units` is
  bookkeeping only because PyTorch's GPU memory model is
  per-process — one Python process can't hand pre-allocated GPU
  memory regions to N other processes running concurrently on the
  same device. The fix is the **multi-threaded Sutra runtime**
  being built in the Sutra repo upstream; until that lands, no
  orchestrator (Python or Rust) can make real per-process arenas
  work.
- **Disc ↔ RAM ↔ GPU storage-tier moves** — the Connectome
  Manager's actual job. Blocked on Sutra-side primitives that
  don't exist yet: serialise-process-state-to-bytes (so a live
  Sutra process can be paused) and evict-from-GPU. The
  multi-program axon-passing demo in
  `external/Sutra/examples/multi_program_axon/` runs each program
  to completion and serialises its *output*; it doesn't
  pause-and-resume a live process.
- **GPU-tick-parallel scheduling.** `Init.tick()` iterates
  services sequentially on the CPU. Production Yantra runs all
  admitted processes simultaneously on the GPU at each tick. The
  service abstraction is concurrency-agnostic so the swap is
  drop-in once the upstream Sutra runtime supports it.
- **Eviction to RAM cold-store.** Same blocker as the storage-tier
  moves. v0.0 only implements admit + deregister.
- **Rotation-operator-based capability check.** v0.0 trusts the
  sender's name (admission grants identity; capability is checked
  by name). Production's threat model
  (`paper/paper.md` § 3.3.1) is operator-based: possession of
  `R_role` is the capability. Lands when the Sutra-side service
  format formalises operator carriage.

## How to add a new service

1. Write a `.su` source file under `kernel/services/<name>.su`
   exporting a `function vector on_axon(vector input_axon)`.
2. Write a manifest TOML in `kernel/manifests/<name>.toml` with
   the process's `axon_width`, `compute_units`, `read_roles`,
   `write_roles`, and `source` (path to the `.su` file).
3. Construct a `SutraService` and admit it:

   ```python
   from kernel import Init, SutraService
   svc = SutraService(
       source_path="kernel/services/myservice.su",
       output_role="R_my_output",
   )
   init.admit_from_path("kernel/manifests/myservice.toml", svc)
   ```

4. Drive it: `init.tick()` runs every service's tick once.

`PythonService` exists for tests + harness code that doesn't
need real Sutra compute. Production services are `SutraService`.

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
