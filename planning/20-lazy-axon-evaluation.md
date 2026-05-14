# Lazy axon evaluation — required, not optional

> **What this document is.** An explicit statement that lazy axon
> evaluation across program boundaries is a **hard requirement** for
> Yantra to scale, not a nice-to-have optimization. Written
> 2026-05-14 to fix a documentation gap: the Yantra-side
> `kernel/router.py` does eager full-payload routing, which is fine
> for the v0.0 1-axon-1-receiver smoke test but is **not the model
> the production connectome runs on**, and the readme didn't say so.
>
> **The Sutra spec calls this out.**
> `external/Sutra/planning/sutra-spec/axons.md` § "Lazy evaluation
> across boundaries" is the canonical reference. This document is
> the Yantra-side statement of why that spec section is load-bearing.

## The problem if axons are eager

Consider a connectome with N programs, each emitting axons of
bundle width D (D dimensions, packing K role-slots). A naive
**eager** router:

- Each program emits its full D-dimensional axon every tick.
- The router copies the full axon to every receiver.
- A receiver only reads the K_r ≤ K slots it has read-roles for.

Cost per tick: every emitter sends D floats to every receiver.
That's **O(N²·D)** floats moved per tick in the worst case, and
**O(N²·D·T)** over T ticks. The K_r-of-K slots a receiver
actually reads are a small fraction; the rest of the axon is
*dead weight on the wire*.

This is exactly the combinatorial-explosion failure mode the
Sutra paper's bundle-depth analysis warns against. At small N the
overhead is unnoticeable; at the scale a real OS connectome
needs to run (hundreds of programs, axons with dozens of slots),
the eager model collapses under its own bandwidth before any
useful computation happens.

## The lazy answer

A **lazy** router only materializes the slots a receiver
references. The emitter declares which roles it writes; the
receiver declares which roles it reads; the router materializes
only the intersection.

Cost per tick: each emitter→receiver edge transports K_intersect
floats, where K_intersect is the number of roles both ends agree
on. Over the connectome, that's **O(E·K_intersect)** where E is
the number of emitter-receiver edges actually wired (not N², just
the connected ones). For sparse connectomes this is a *huge*
constant-factor win and an asymptotic win.

Lazy materialization also means a receiver that never references
a particular role never pays for it — it's not just bandwidth, it's
that the unbind operation is never run on the receiver side for
unreferenced slots.

## Why this matters for the orchestrator's job

The Rust orchestrator's axon-router responsibility (§4 in
`19-boot-sequence.md`) is not "copy bytes around." It is
"materialize, on demand, the dimensions a receiver references,
and only those." The mechanism per the Sutra spec:

1. The compiler knows statically which roles each Sutra program
   reads. This is part of the program's contract surface (the
   spec calls these "read-roles" and Yantra's manifest format
   carries them as `read_roles`).
2. The router precomputes per-receiver projection: for the axon
   emitted on role R by sender S, project onto the dimensions
   receiver R' actually reads.
3. At tick time, the router does the projected copy, not the full
   copy.

For a single GPU running everything in shared memory, "copy"
collapses further — the projections can be expressed as torch
slicing / index ops on the same underlying tensor, with no
physical data movement at all. The lazy model + GPU shared
memory is most of what makes the connectome viable.

## Lazy is fundamentally compile-time wiring

The user driving this work pointed out (correctly) that lazy
evaluation is essentially a compile-time problem. The Sutra
compiler statically knows what keys each program binds (the
producer's `add()` / `bind()` calls in the .su source) and what
keys each program reads (the consumer's `axon_item()` calls).
From those two static sets per program, **the cross-program
connectome wiring is computable as a static table** — for each
(sender role, receiver name) edge, exactly which keys flow.

The kernel router's job at runtime is to **execute** that
wiring, not to compute it. There is no clever runtime intersection
analysis happening in the production design; there's a precomputed
delivery table, populated at admission time from manifest data
the compiler emitted.

What the Yantra-side kernel implements is the runtime expression
of that static wiring:

  - `Manifest.axon_keys` — the keys-this-receiver-reads set.
    In production, the Sutra compiler emits this from static
    analysis. For v0.0, it's hand-written in the manifest TOML.
  - `Axon.keys` — the keys-bound-in-this-payload set. In
    production, the compiler emits this from analysis of the
    producer's bind chain. For v0.0, the calling service passes
    it explicitly to `service.emit(role, payload, keys=...)`.
  - `AxonRouter.send()` — at send time, intersects the axon's
    keys with each receiver's `axon_keys`. Empty intersection
    ⇒ skip. Non-empty ⇒ deliver. Empty on either side ⇒
    eager-fallback (deliver).

## Yantra-side status

**Implemented as of 2026-05-14.** `kernel/router.py` now does the
kernel slice of lazy evaluation as described above. Tested in
`tests/test_kernel.py`:

  - `test_lazy_skip_when_keys_dont_intersect` — receiver
    declaring keys it doesn't share with the axon is skipped;
    `lazy_skipped_count()` increments; black-hole NOT triggered.
  - `test_lazy_delivers_when_keys_intersect` — non-empty
    intersection delivers as expected.
  - `test_lazy_eager_fallback_when_receiver_unkeyed` — receivers
    with empty `axon_keys` get every axon (eager fallback path
    for v0.0 stub receivers and debugger / log processes).
  - `test_lazy_eager_fallback_when_axon_unkeyed` — axons
    emitted without declared keys go to every receiver
    (eager fallback for stub producers and debugger-emitted
    axons that don't go through static wiring).
  - `test_lazy_partial_fanout_one_skips_one_delivers` — two
    receivers on same role, only the keyed-matching one gets
    the axon.
  - `test_lazy_capability_check_still_fires_first` — capability
    check happens before lazy filtering; can't bypass capability
    by playing key games.
  - `test_lazy_keys_optional_in_manifest_toml` /
    `test_lazy_keys_in_manifest_toml` /
    `test_lazy_bad_manifest_axon_keys_raises` — manifest TOML
    schema for `axon_keys` (optional list of strings).

**What remains upstream-Sutra-dependent: per-receiver
projection** — slicing the payload tensor to materialize only the
dimensions the receiver references. This needs Sutra-side support
to expose the per-key projection primitive. The kernel here only
decides deliver-or-skip the full payload; it doesn't slice within
the payload. When the Sutra compiler grows this primitive,
`SutraService.tick()` would call it instead of handing the full
payload to `on_axon()`.

## Cross-references

- `external/Sutra/planning/sutra-spec/axons.md` § "Lazy evaluation
  across boundaries" — canonical spec.
- `01-architecture.md` § "The kernel is a Connectome Manager" —
  the connectome framing this requirement falls out of.
- `19-boot-sequence.md` — where the orchestrator's axon-router
  responsibility lives in the boot/runtime flow.
- `kernel/router.py` — current eager implementation; gap noted in
  `kernel/README.md`.
- `kernel/services.py` — `SutraService` calls the .su program's
  `on_axon(vector)` on the full payload, not on a projected
  slice.
