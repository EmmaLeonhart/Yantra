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

## Yantra-side status

**Not implemented.** `kernel/router.py` does eager full-payload
routing today: an `Axon` carries an opaque `payload: Any`
(typically a torch tensor of shape `(axon_width,)`), and `send()`
appends that payload to every receiver's inbox without any
projection. The `SutraService.tick()` invokes the receiver's
`on_axon(payload)` on the full payload.

This is **fine for the v0.0 smoke test** — the test sends one
axon to one receiver and verifies routing works. It is **not the
model the production connectome runs on**. When the multi-process
Sutra runtime upstream lands and Yantra starts running real
multi-program connectomes, this router has to be reworked to do
projection per receiver per role.

The honest reading of the kernel/ directory is therefore: the
admission-control and capability-check shape is right; the
routing primitive is intentionally simplified to "send full
payload" because lazy projection is gated on Sutra-side spec
work that's still in flight.

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
