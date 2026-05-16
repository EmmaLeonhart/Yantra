# Yantra — Work Queue

**This file is a queue, not a state snapshot.** It lists what is being worked on right now. Finished work lives in `git log`; longer-horizon ideas live in `planning/` or `todo.md`. When an item is done, delete it — no checkmarks, no status indicators. If an item is still here, it is not done.

**Why this file exists:** when a planning step (formal planning mode or just "think before doing") produces a plan, that plan is written here BEFORE execution starts. An interrupted session can pick up from the queue rather than from chat context that may be gone.

This repo currently holds **planning documents and a v0.0 kernel nucleus**, not a full implementation, so most "work" here is design and small implementation pieces. The same rule applies: design plans go into queue.md before they get executed against `planning/*.md` or `kernel/`.

See `CLAUDE.md` § "Workflow Rules" for how this file, planning mode, and the task tool stay in sync. Longer-horizon items live in `todo.md`.

---

## Active

### Investigate the bundle-decoding regression (promoted from todo.md)

`external/Sutra/examples/multi_program_axon/_run.py` was filed
2026-05-14 as producing cosine recovery margins ~10× smaller than
the README's expected output (`cos(recovered,'dog')=+0.04` here vs
`+0.40` expected). Same code path, different numbers → a runtime /
numerical regression somewhere in the bind/permute chain. Degrades
the VSA-capacity story the Sutra paper rests on; not Yantra-wiring.

Plan:
1. Reproduce against current Sutra HEAD (cd464c0a — the submodule
   moved a lot since the 2026-05-14 filing; the regression may have
   been introduced OR fixed by intervening substrate-fix work).
2. If still regressed: bisect the bind/permute/axon chain. Root-
   cause candidates from todo.md — dtype/rounding from the
   defensive `as_tensor(filler, dtype=…, device=…)` cast in
   `bind()` (float64→float32 through chained binds), or the
   axon-keys / axon_project / device-coherence additions.
3. Fix at root cause Sutra-side if clear+safe (cross-repo
   workflow: commit+push Sutra, bump Yantra pointer). Do NOT
   tune numbers to look right — measure honestly, report the
   real delta. If the fix isn't clear, document the bisect
   result as a Sutra finding and leave a precise blocker here.
4. Verify: re-run `_run.py`, report real margins vs expected.

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
