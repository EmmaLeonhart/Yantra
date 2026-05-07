# The axon model

> A `.su` file is, in 95% of cases, a function `(Axon) -> Axon`. The whole
> OS is what you get when you wire a few hundred of those together.

## What an axon is

An **axon** is a structured embedding: a fixed-width tensor whose contents
are produced by **rotation binding** over a known **codebook of roles**.
Concretely, an axon carries a small bundle of role/filler pairs:

```
axon = bundle( bind(R_subject, F_alice),
               bind(R_action,  F_send),
               bind(R_object,  F_message_42) )
```

Where `R_*` are unit-norm rotation operators (one per role, drawn from a
codebook fixed at compile time) and `F_*` are fillers (vectors that may
themselves come from an embedding model, a Sutra-compiled symbol, or
another axon — they are all the same shape).

Why rotation binding rather than Hadamard or circular convolution:
empirically it dominates the alternatives across multiple real embedding
models, including cross-modality, and it has a clean compile-time story
because the rotation matrices can be materialised once.

## Why this is the right unit of IPC

Three properties make axons the natural inter-process currency:

1. **Composable without parsing.** Two axons combine into a third by
   bundling. No serialization, no schema validation, no version
   negotiation. The receiver decodes the role it needs by unbinding.
2. **Differentiable end-to-end.** Gradients flow through bind/bundle
   exactly the way they flow through any tensor operation. The whole
   IPC graph is a smooth function. Training across process boundaries is
   not a special case.
3. **Same shape as model inputs.** A model that consumes embeddings is
   already prepared to consume axons. JEPA's predicted latents, an LLM's
   activation residual, and a `read_file()` syscall result are all the
   same kind of tensor.

## Axon types

A type system over axons is essentially a contract about *which roles are
expected to be bound* on entry and exit. A type signature looks like:

```
ProcessFoo : { R_input_query, R_caller_ctx } -> { R_response, R_provenance }
```

The compiler can statically check that the body of `ProcessFoo` only reads
roles that are guaranteed by the input type, and only writes roles that
its output type promises. This is structural typing on a vector — the
"type" is which rotation slots are populated, with what fillers, drawn
from what codebooks.

## Capability story

Roles double as capabilities. A process that doesn't possess the rotation
operator `R_x` cannot read or write the `x` slot of an axon, because the
operator literally is the only key into that slot. Capability transfer
happens by bundling the operator (or a derived child operator) into an
axon and handing the axon to another process. This is the same machinery
that does ordinary IPC, used reflectively.

This means:

- Process isolation is a function of which roles each process knows.
- Sandboxing a tab is "give it a child role-codebook with fewer slots."
- A capability revocation is "rotate the parent role; child copies become
  noise that decodes to nothing meaningful."

See `08-security-and-isolation.md` for crosstalk and partitioning details.

## Filesystem bridge

The conventional filesystem returns axons to processes via syscalls:

```
read_file : { R_path } -> { R_bytes_axon, R_metadata_axon }
write_file : { R_path, R_payload_axon } -> { R_status }
```

`R_bytes_axon` carries the file's contents as either:

- a literal embedding produced by an embedding model (e.g. `nomic-embed-text`,
  `mxbai-embed-large`, `ESM-2`) when the file is meant to be consumed
  semantically, or
- a Sutra-compiled axon that decodes losslessly to bytes when the file is
  meant to be consumed exactly (executables, configs, binary blobs).

Which mode applies is part of the file's metadata, not the syscall's job.

## Constraints that fall out of the model

- **Fixed-width state per process.** A process's state at any instant is
  one axon (plus its compiled program). The width is part of its install
  manifest. This is what makes "no degradation under load" enforceable —
  the runtime knows in advance how much GPU it owes the process.
- **No higher-order axons (yet).** The current Sutra core does not bind
  programs as fillers; you can pass embeddings of programs, but not
  programs as first-class axons that other programs can apply. Lifting
  this restriction is research-grade work, not v1.
- **Crosstalk is bounded by codebook depth.** Nesting too many bind/bundle
  layers in a single axon eventually degrades decoding quality. The OS
  should treat "your axon is too deep" as a runtime error, not a slow
  decline.

## Open questions

- What's the right default axon width? Embedding models vary (768, 1024,
  4096). Picking one and forcing converters at the edges vs. carrying
  width as part of the type are both viable.
- Should axons carry an explicit provenance role by default? Useful for
  debugging and for the alignment monitor (`10-ai-native-interface.md`),
  but it costs codebook entries.
- Per-tenant codebooks vs one global codebook with namespaced roles —
  a real partitioning question for multi-process safety.
