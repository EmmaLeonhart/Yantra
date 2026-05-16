# Yantra — Work Queue

**This file is a queue, not a state snapshot.** It lists what is being worked on right now. Finished work lives in `git log`; longer-horizon ideas live in `planning/` or `todo.md`. When an item is done, delete it — no checkmarks, no status indicators. If an item is still here, it is not done.

**Why this file exists:** when a planning step (formal planning mode or just "think before doing") produces a plan, that plan is written here BEFORE execution starts. An interrupted session can pick up from the queue rather than from chat context that may be gone.

This repo currently holds **planning documents and a v0.0 kernel nucleus**, not a full implementation, so most "work" here is design and small implementation pieces. The same rule applies: design plans go into queue.md before they get executed against `planning/*.md` or `kernel/`.

See `CLAUDE.md` § "Workflow Rules" for how this file, planning mode, and the task tool stay in sync. Longer-horizon items live in `todo.md`.

---

## Active

### Lazy axon eval: wire per-receiver projection into the router (promoted from todo.md)

`kernel/router.py` ships the v0.0 kernel-level slice (skip a
receiver entirely when `axon.keys ∩ receiver.axon_keys = ∅`) but
NOT per-receiver projection (slim the payload to only the keys the
receiver reads). The router docstring names the blocker: "needs
Sutra-side support to expose the per-key projection primitive."
That blocker is now LIFTED — Sutra ships `axon_project(axon,
requested_keys)` (codegen_pytorch.py; `test_axon_project.py`
green). Per `planning/20-lazy-axon-evaluation.md` this is a hard
scaling requirement (eager = O(N²·D)).

Plan:
1. Read router.py fully + 20-lazy-axon-evaluation.md + how the
   kernel reaches the Sutra runtime (SutraService) — find the
   integration seam for calling `_VSA.axon_project`.
2. Wire a real projector: for a receiver with non-empty
   `axon_keys`, deliver `axon_project(payload, receiver.axon_keys)`
   instead of the full payload. Keep eager fallback (empty
   `axon_keys` ⇒ full payload) and the capability check ordering.
3. Test: extend the kernel test suite — a receiver with declared
   keys gets a slimmed payload that still decodes its keys
   correctly and excludes others; the skip-path and eager-fallback
   still hold. Keep all existing kernel tests green.
4. If the SutraService seam isn't cleanly reachable from the
   Python router without a larger refactor, do NOT force it —
   document the precise integration blocker here + in the kernel
   README and leave it for the next cycle (honest, not faked).

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
