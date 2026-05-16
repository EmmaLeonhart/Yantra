# Yantra — Work Queue

**This file is a queue, not a state snapshot.** It lists what is being worked on right now. Finished work lives in `git log`; longer-horizon ideas live in `planning/` or `todo.md`. When an item is done, delete it — no checkmarks, no status indicators. If an item is still here, it is not done.

**Why this file exists:** when a planning step (formal planning mode or just "think before doing") produces a plan, that plan is written here BEFORE execution starts. An interrupted session can pick up from the queue rather than from chat context that may be gone.

This repo currently holds **planning documents and a v0.0 kernel nucleus**, not a full implementation, so most "work" here is design and small implementation pieces. The same rule applies: design plans go into queue.md before they get executed against `planning/*.md` or `kernel/`.

See `CLAUDE.md` § "Workflow Rules" for how this file, planning mode, and the task tool stay in sync. Longer-horizon items live in `todo.md`.

---

## Active

### End-to-end semantic test for per-receiver axon projection

Investigation 2026-05-15 found the per-receiver projection chain
is ALREADY implemented and wired (router `register_projector` +
projection branch; `SutraService` registers a
`_VSA.axon_project`-backed projector; Sutra ships `axon_project`).
The stale "not done / needs Sutra support" claims in router.py,
todo.md, and 20-lazy-axon-evaluation.md were corrected (they were
the same false-doc class as the substrate-purity audit). Tested:
router branch (stand-in projector) + axon_keys plumbing. The ONE
remaining gap is honest end-to-end proof.

Concrete next step (do not claim projection "works end-to-end"
until this passes):
1. Add a producer .su that bundles a multi-key axon (≥3 keys,
   embedded fillers) and admit it as a SutraService; admit a
   consumer SutraService/manifest declaring a STRICT-SUBSET
   `axon_keys` (e.g. one key).
2. Send through the router; assert: (a) `lazy_projected_count`
   incremented, (b) delivered `axon.keys == intersection`, (c) the
   consumer recovers its requested key from the PROJECTED payload
   with high cos to the true filler (≈ the multi_program_axon
   +0.40 bar), (d) a non-requested key does NOT decode.
3. Keep all existing kernel tests green. Slow (Sutra+CUDA
   compile) — budget for it. If a real defect surfaces, document
   it as a precise blocker; do NOT tune or fake a pass.

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
