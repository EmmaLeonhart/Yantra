# Yantra — Work Queue

**This file is a queue, not a state snapshot.** It lists what is being worked on right now. Finished work lives in `git log`; longer-horizon ideas live in `planning/` or `todo.md`. When an item is done, delete it — no checkmarks, no status indicators. If an item is still here, it is not done.

**Why this file exists:** when a planning step (formal planning mode or just "think before doing") produces a plan, that plan is written here BEFORE execution starts. An interrupted session can pick up from the queue rather than from chat context that may be gone.

This repo currently holds **planning documents and a v0.0 kernel nucleus**, not a full implementation, so most "work" here is design and small implementation pieces. The same rule applies: design plans go into queue.md before they get executed against `planning/*.md` or `kernel/`.

See `CLAUDE.md` § "Workflow Rules" for how this file, planning mode, and the task tool stay in sync. Longer-horizon items live in `todo.md`.

---

## Active

### Blocker (NARROWED 2026-05-17, not closed) — axon_project no-op across the connectome

The intra-module slice of the real fix shipped (Sutra v0.4.1,
cross-function producer-side pruning; submodule pinned). What
remains is **only** the cross-separately-compiled-program
(connectome) case — a single-module compiler structurally cannot
bridge producer/consumer wired at kernel admission. Not faked, not
forced; full reasoning + the remaining design options
(whole-connectome compilation / admission-time producer
specialization) in `planning/20-lazy-axon-evaluation.md` § "Status
(2026-05-17)" and `todo.md` § 1. Left here as a precise, narrowed
blocker for a future Sutra+kernel design session.

### Headline demo — replicate the Meta *Neural Computers* prototypes, symbol-stable

The two things the Meta paper demonstrated — (1) a terminal (their
CLIGen) and (2) a desktop GUI (their GUIWorld) — reproduced on Yantra
as real execution so the **symbols stay exact** where their
video-diffusion approach drifts. That contrast is the decisive proof
the design works. **Roadmap drafted: `planning/22-meta-demo-replication.md`**
(current state → Demo 1 terminal → Demo 2 desktop → the
symbol-fidelity-vs-horizon figure). Gated on the build sequence; the
near-term bounded step is Demo 1's exact-symbol terminal once the CLI
utilities + a shell surface land (`todo.md` § 2). Ambition tracked in
`todo.md` § 5.

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
- Paper + AI peer review pipeline: `paper/` (see `paper/README.md`)
- External dependencies: `external/` (submodules)
- Cross-repo workflow (Yantra ↔ Sutra): `CLAUDE.md` § "Cross-repo workflow"
- Narrative history: `git log`
