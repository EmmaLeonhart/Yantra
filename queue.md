# Yantra — Work Queue

**This file is a queue, not a state snapshot.** It lists what is being worked on right now. Finished work lives in `git log`; longer-horizon ideas live in `planning/` or `todo.md`. When an item is done, delete it — no checkmarks, no status indicators. If an item is still here, it is not done.

**Why this file exists:** when a planning step (formal planning mode or just "think before doing") produces a plan, that plan is written here BEFORE execution starts. An interrupted session can pick up from the queue rather than from chat context that may be gone.

This repo currently holds **planning documents and a v0.0 kernel nucleus**, not a full implementation, so most "work" here is design and small implementation pieces. The same rule applies: design plans go into queue.md before they get executed against `planning/*.md` or `kernel/`.

See `CLAUDE.md` § "Workflow Rules" for how this file, planning mode, and the task tool stay in sync. Longer-horizon items live in `todo.md`.

---

## Active

### Upstream Sutra work — continuation

Item 1 (axon-keys static analysis) shipped in Sutra v0.3.3 + bumped Yantra submodule. Items 2 (per-receiver projection) and 3 (multi-process Sutra runtime) still pending.

- **#2 Per-receiver projection primitive** — Sutra-side function that takes (payload_axon, requested_keys) and returns an axon containing only the requested keys' bound dimensions. Lets the kernel router slice the payload to what each receiver needs, not just decide whether to deliver the full payload.
- **#3 Multi-process Sutra runtime** — per-process GPU memory arenas, simultaneous execution of N admitted programs at each tick. The biggest piece; user has flagged it as the biggest blocker on Yantra's "no degradation under load" claim.

---

## Pointers

- Longer-horizon items: `todo.md`
- Kernel runtime nucleus: `kernel/` (see `kernel/README.md`)
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
