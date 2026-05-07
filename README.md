# Yantra

A neuro-symbolic, GPU-native operating system written in Sutra.

## What it is

Yantra is the operating system you get when you take "the symbol *is* the
computation" seriously. The whole running system is one big differentiable
tensor-op graph: kernel, processes, IPC, GUI. There is essentially no
CPU-side runtime — a tiny CPU exists only to boot the system and
orchestrate the GPU. Everything that matters happens as Sutra programs
exchanging **axons** (structured embeddings produced by rotation binding).

Three things that fall out of that:

- **Predictable performance under load.** Once a process has its allocation,
  it doesn't slow down. Adding more processes either fits cleanly or fails
  admission — never degrades what is already running.
- **Verifiable.** The non-AI parts reduce to a tensor normal form +
  polynomial Kleene logic + tail-recursive loops, which is a much cleaner
  surface for formal arguments than a typical kernel.
- **AI-native by construction.** Every process already takes an axon and
  returns an axon, so local AI integrates without a translation layer.

The intended customer is not a consumer desktop user. It is defense,
aerospace, industrial control, medical devices, autonomous systems —
anywhere "predictable latency under load" and "the certifier can read the
code" beat "it runs my favourite app."

## Status

This repo currently holds **planning documents**, not an implementation.
The implementation lives in adjacent projects (the Sutra compiler and
runtime, transpilers, alignment / connectome research). Yantra is being
designed here so that when the implementation starts, there is a coherent
target.

## Where to start reading

- [planning/](planning/README.md) — the design notes, in reading order.
  Start with [`00-vision.md`](planning/00-vision.md).
- [chats/](chats/) — extracted, readable Markdown of the long-form
  conversations the design grew out of. Useful for context and for the
  motivations behind specific decisions.

## Contributing

Not yet open to contribution. The architecture is moving quickly enough
that an issue tracker would be premature; the right place to push back
on ideas is via the planning docs themselves.

## Project conventions

See [CLAUDE.md](CLAUDE.md) for the conventions this repo runs by — the
short version is: commit early, do not enter planning-only mode without
files and commits, keep README and planning docs in sync with the
current state.
