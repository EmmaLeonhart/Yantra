# Yantra — Work Queue

**This file is a queue, not a state snapshot.** It lists what is being worked on right now. Finished work lives in `git log`; longer-horizon ideas live in `planning/` or `todo.md`. When an item is done, delete it — no checkmarks, no status indicators. If an item is still here, it is not done.

**Why this file exists:** when a planning step (formal planning mode or just "think before doing") produces a plan, that plan is written here BEFORE execution starts. An interrupted session can pick up from the queue rather than from chat context that may be gone.

This repo currently holds **planning documents and a v0.0 kernel nucleus**, not a full implementation, so most "work" here is design and small implementation pieces. The same rule applies: design plans go into queue.md before they get executed against `planning/*.md` or `kernel/`.

See `CLAUDE.md` § "Workflow Rules" for how this file, planning mode, and the task tool stay in sync. Longer-horizon items live in `todo.md`.

---

## Active

try to implement this https://computernewb.com/wiki/Linux_0.00

### BLOCKER (Sutra-side design decision) — axon_project is a no-op for embedding fillers

Surfaced by the 2026-05-15 end-to-end semantic test (delivered;
`tests/test_kernel_sutra.py::test_projected_payload_still_decodes_semantically`,
strict xfail). `_VSA.axon_project(bundle,[k]) = bind(k,unbind(k,
bundle))` ≈ identity for orthogonal rotation binding on
semantic-block (embedding) fillers, so per-receiver projection
delivers **no bandwidth reduction and no capability isolation**
for the common case (measured: dropped key +0.5726 vs kept
+0.5999). Bears on `paper/paper.md` § 3.3.1. The real fix is
producer-side pruning — rebuild the bundle without the unwanted
`axon_add` terms via whole-program analysis of each receiver's
read-keys, per Sutra `axons.md` §"Lazy evaluation across
boundaries". That is a **Sutra-side design + spec decision**, not
a Yantra wiring task — left here as a precise blocker for a
Sutra-driven session rather than forced/faked. Full reasoning:
`planning/20-lazy-axon-evaluation.md` § Status; `todo.md`.

---

## Pointers

- Longer-horizon items: `todo.md`
- Kernel runtime nucleus: `kernel/` (see `kernel/README.md`)
- First userspace utility: `apps/echo/` (see `apps/README.md`)
- Bare-metal QEMU bootloader: `bootloader/` (see `bootloader/README.md`)
- Design notes: `planning/` (numbered for reading order)
- Open architectural questions: `planning/15-open-questions.md`
- Memory model open hard problem: `planning/17-memory-model.md`
- Boot sequence: `planning/19-boot-sequence.md`
- Lazy axon evaluation: `planning/20-lazy-axon-evaluation.md`
- Kernel + browser readiness audit: `planning/18-kernel-browser-readiness.md`
- Chat history the design grew out of: `chats/`
- Paper + AI peer review pipeline: `paper/` (see `paper/README.md`)
- External dependencies: `external/` (submodules)
- Cross-repo workflow (Yantra ↔ Sutra): `CLAUDE.md` § "Cross-repo workflow"
- Narrative history: `git log`
