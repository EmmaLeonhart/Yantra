# Orchestrator serialisation — design

> **What this document is.** The standing design for the orchestrator's
> serialisation primitives. Emma's direction 2026-05-24 split the work into
> two distinct kinds and asked we start with the easy one. This document
> records the split, the format the easy slice uses, and what composes on
> top of it.
>
> **Bottom line.** The easy slice — serialising an axon's output value —
> lands now as `kernel/serialise.py`. The long pole — serialising a *running*
> program's full state (weights + in-flight memory + scheduler position) —
> needs Sutra-side `serialise-process-state` and is genuinely out of scope
> until that primitive exists.

## The two kinds (Emma's direction 2026-05-24)

The orchestrator does serialisation, but the two interesting cases are
different jobs at different layers.

### (a) Serialise an axon's *output* — the easy, near-term kind

The structured-embedding value a program emits. By the time the router
sees an axon, the payload is already a well-typed torch tensor — a
1-D vector of the runtime dim (e.g. 768) carrying every binding the
producer wrote. Capturing it is "read these bytes off the GPU and write
them somewhere," and restoring it is "write these bytes back into a
fresh tensor on the right device with the right dtype."

This is the right place to start because:

1. The shape is **already settled** — the router defines payloads as
   1-D vectors; we don't have to design a new envelope.
2. **No co-design with Sutra** — the substrate doesn't need to expose
   any new primitive; we're capturing the value the substrate already
   emitted.
3. **Useful immediately** — every persistence story we eventually want
   (IPC, network, checkpoint of a conversation's history, audit log of
   what flowed through the connectome) composes from this.

### (b) Serialise a *running* program's full state — the long pole

The slice of VRAM holding the program's weights *and* its in-flight
memory, so a *running* program can be checkpointed and resumed
bit-exact. This is the hard kind:

1. Weights live on the device, often as multiple tensors at addresses
   the orchestrator doesn't directly own.
2. In-flight state (the loop-carrier of a `loop`, the iterator
   counter, any partially-computed intermediate) is the substrate's
   business, not the orchestrator's.
3. Scheduler position — which axon the program was about to consume,
   what tick we're on — is router state, not program state.

This is what the Sutra-side `serialise-process-state` primitive is for.
Until that primitive exists, (b) cannot be built honestly; the
orchestrator can only see the device addresses, not the semantic
checkpoint boundary. Out of scope for the easy slice; flagged in
`todo.md` § 1 and `planning/17-memory-model.md`.

## Format for (a): `kernel/serialise.py`

Rust-portable, no Python pickle. The format is intentionally tiny so
that the eventual Rust orchestrator (planning/01 § "CPU side: small,
Rust, orchestrator") can read and write the same bytes with `struct`-
equivalent C primitives — no serde framework, no version negotiation
beyond a magic + version byte.

```
Offset  Size  Field         Notes
0       4     Magic         b'YAXN' (Yantra AXoN)
4       1     Version       Current: 1
5       1     Dtype tag     0=float32, 1=float64, 2=complex64, 3=complex128
6       2     Reserved      Pads the header to an 8-byte boundary
8       4     Width         uint32 little-endian; the 1-D payload length
12      W·S   Payload body  Raw little-endian bytes; W=width, S=dtype size
```

Total header: 12 bytes. Body: width × dtype-size bytes. A 768-d
float64 axon: 12 + 768·8 = 6156 bytes.

### What the format is NOT

- **Not the router envelope.** The bytes carry the *payload only* —
  `Axon.role`, `Axon.from_proc`, and `Axon.keys` are orchestrator
  routing state, not part of the value the program emitted. Persisting
  those alongside is a *separate* envelope concern (a caller that
  needs them writes them to its own log alongside the payload bytes).
- **Not the VSA configuration.** The receiver must already have a
  VSA configured with the same role-vector basis (the LLM embedding)
  and the same per-key permutation function (deterministic from
  `_role_hash`); decoding a restored tensor through `axon_item` will
  only round-trip if the VSA matches what the producer used. A future
  version of the format may carry a VSA-config fingerprint at the
  caller layer, but the bytes the easy slice produces are the payload
  bytes, not the VSA spec.
- **Not pickled.** No Python class identity, no version-pinned object
  graph. Same shape rule the bootloader follows: every cross-process
  format must be parseable from a non-Python reader.

### Round-trip guarantees (measured, not promised)

1. `deserialise_axon_payload(serialise_axon_payload(t))` returns a
   tensor that is `torch.equal` to `t`. Bit-exact (no quantisation,
   no normalisation).
2. Every binding decodes from the restored tensor through `axon_item`
   the same as from the original. Verified by composing the calc's
   real VSA: bind `a`, `b`, `op_char`; serialise; deserialise; check
   each binding's decode value is unchanged.
3. Round-trip works on both CPU and CUDA. The `device` parameter
   of `deserialise_axon_payload` controls where the result lives,
   not the values it carries.

## What's deliberately not in v1

- **Multi-axon batches / streams.** The easy slice is one axon →
  bytes. A persistence layer that wants to log N axons in a single
  file can frame them itself (length-prefix, etc.); the kernel
  primitive doesn't impose a framing.
- **Compression.** A float64 axon is 6 KiB; compression complicates
  the format without materially shrinking storage at the scales we
  care about for v1. If the connectome's audit log eventually wants
  it, that's a layer above the primitive.
- **Encryption / signing.** Same reasoning. Future capability work
  (rotation-operator-based capability checks, the §3.5 hardware
  boundary in `paper/paper.md`) may want signed axons; this primitive
  is the wire-shape, not the security envelope.
- **Cross-VSA-config conversion.** A float32 axon cannot be restored
  into a float64 VSA without explicit dtype conversion + the recipient
  knowing the conversion is safe. The format records the dtype the
  payload was written with; matching it to the VSA's dtype is the
  caller's job.

## Rust port note

This is a candidate first target for the "many small Rust programs"
build strategy under `planning/01-architecture.md` § "CPU side": the
format is small enough to port end-to-end, the test surface
(round-trip a tensor) is unambiguous, and the Python implementation
is already pinned to the wire shape a Rust reader would see. A Rust
port of `serialise.py` doesn't need any of the rest of the orchestrator
to be Rust-ported first.

## Cross-references

- `todo.md` § 1 — Storage-tier moves, Emma's direction 2026-05-24
  (the source of the (a)-then-(b) split).
- `planning/01-architecture.md` § "CPU side: small, Rust,
  orchestrator" — the eventual Rust target.
- `planning/17-memory-model.md` — the broader disc/RAM/GPU storage
  question that (b) is gated on.
- `kernel/router.py` — the `Axon` dataclass whose `payload` field is
  the value being serialised.
- `kernel/serialise.py` — the implementation.
- `tests/test_axon_serialise.py` — the round-trip + bindings-decode
  tests.
