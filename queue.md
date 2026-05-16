# Yantra — Work Queue

**This file is a queue, not a state snapshot.** It lists what is being worked on right now. Finished work lives in `git log`; longer-horizon ideas live in `planning/` or `todo.md`. When an item is done, delete it — no checkmarks, no status indicators. If an item is still here, it is not done.

**Why this file exists:** when a planning step (formal planning mode or just "think before doing") produces a plan, that plan is written here BEFORE execution starts. An interrupted session can pick up from the queue rather than from chat context that may be gone.

This repo currently holds **planning documents and a v0.0 kernel nucleus**, not a full implementation, so most "work" here is design and small implementation pieces. The same rule applies: design plans go into queue.md before they get executed against `planning/*.md` or `kernel/`.

See `CLAUDE.md` § "Workflow Rules" for how this file, planning mode, and the task tool stay in sync. Longer-horizon items live in `todo.md`.

---

## Active

### Refresh planning/18-kernel-browser-readiness.md to current ground truth

CLAUDE.md: "refresh it when the situation changes." It was written
2026-05-13 vs Sutra v0.3.1 (commit 2582cd46); we are now at
`dd448b47` (past v0.4.0). It is also internally contradictory
(line 27 says the TS→Sutra CLI shipped v0.3.2; lines 43/102/117/119
still call it an "unwired skeleton, wire it up first thing") — the
exact false-doc harm this loop is mandated to fix.

Verify-then-correct (no claim without measuring):
1. Sutra version: v0.3.1 → current submodule commit (past v0.4.0).
2. TS CLI contradiction → resolve to the true state (verify
   `python -m sutra_from_ts` actually runs in the submodule).
3. "Multi-process Sutra runtime is THE bottleneck / hasn't
   landed" — Sutra v0.4.0 shipped MultiProcessRuntime; verify via
   the shared-runtime kernel tests
   (`test_make_shared_sutra_services_share_one_vsa`,
   `test_shared_runtime_axon_passing_through_router`).
4. Lazy axon eval / "kernel IPC primitive" — add the proven
   caveat: `axon_project` is a no-op for embedding fillers (this
   loop's strict-xfail finding), so per-receiver projection gives
   no bandwidth reduction / no capability isolation for the common
   case — bears on the "no degradation under load" claim.
5. Transcendentals "substrate-pure, no host fall-throughs" — was
   false 2026-05-15 (the leak), fixed in Sutra 21a9ff77 via
   eigenrotation/cexp + saturate-not-raise; state accurately.
6. Test counts ("25 tests") — refresh against current suites.
Bounded doc-honesty pass; commit+push when done.

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
