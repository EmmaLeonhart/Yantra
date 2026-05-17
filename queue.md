# Yantra — Work Queue

**This file is a queue, not a state snapshot.** It lists what is being worked on right now. Finished work lives in `git log`; longer-horizon ideas live in `planning/` or `todo.md`. When an item is done, delete it — no checkmarks, no status indicators. If an item is still here, it is not done.

**Why this file exists:** when a planning step (formal planning mode or just "think before doing") produces a plan, that plan is written here BEFORE execution starts. An interrupted session can pick up from the queue rather than from chat context that may be gone.

This repo currently holds **planning documents and a v0.0 kernel nucleus**, not a full implementation, so most "work" here is design and small implementation pieces. The same rule applies: design plans go into queue.md before they get executed against `planning/*.md` or `kernel/`.

See `CLAUDE.md` § "Workflow Rules" for how this file, planning mode, and the task tool stay in sync. Longer-horizon items live in `todo.md`.

---

## Active

### Replicate Linux 0.00 on Yantra (user-added 2026-05-17; scheduled +1h cron)

Concrete plan + faithful-mapping design + honest scope are in
**`planning/21-linux-0.00.md`** (written so a fresh/cron session
executes without chat context). Summary: two trivial Sutra
services `task_a.su`/`task_b.su` (emit codepoint `A`/`B`), a
console/sink consumer, driven by the Connectome Manager's
`Init.tick()` as the timer-IRQ analogue — Linux 0.00's "kernel
mediates two trivial output tasks" realized in Yantra's connectome
model (milestone 1; buildable on the tested v0.0 kernel). Deliver:
the two `.su` + manifests + `tests/test_linux_000.py` (real
`SutraService`, honest decode measurement, no weakened asserts).
Honest gap recorded in the planning doc: the deeper bare-metal
replica (real PIT IRQ + TSS + framebuffer in `bootloader/`) is a
separate bootloader-track item gated on GPU passthrough / GRUB
ISO — not faked here. A one-shot cron (~1h out, this session) will
execute this; this entry is the durable plan if the cron is lost.

### IN PROGRESS (Sutra-driven session, 2026-05-17) — producer-side axon pruning across function calls

The `axon_project` no-op blocker's real fix is producer-side
pruning. Investigation found the buildable, spec-mandated slice:
Sutra's `axons.md` § "Lazy evaluation across boundaries" says the
single-function-call case is **"clearly yes"**, but
`_compute_axon_elision` (Sutra `codegen_base.py`) keeps ALL keys
whenever an axon escapes via a call — a spec/implementation
disagreement (Sutra safety rule #5: resolve by fixing the
implementation).

Doing now, Sutra side (cross-repo workflow):

1. New module pre-pass: per-`(function,param)` read-key signature
   via call-graph fixpoint; `OPAQUE` on dynamic-key reads or any
   non-call escape.
2. Extend `_compute_axon_elision`: when an axon local escapes ONLY
   as positional args to statically-known functions, `elide =
   writes − (local reads ∪ propagated callee demand)`; conservative
   (`elide = ∅`) on every opaque/dynamic/return escape.
3. Tests (`test_codegen.py`): emitted code omits pruned `axon_add`,
   keeps demanded; end-to-end semantic (kept decodes / pruned
   absent); transitive; conservative cases; multi-param.
4. Resolve the `axons.md` open-question for the intra-module case.
5. Tag a Sutra release; bump submodule here.

**Honest scope (do NOT overclaim):** closes the *intra-module*
producer-pruning case the spec mandates. Does **not** close the
Yantra **cross-separately-compiled-program connectome** case
(producer + each consumer compiled independently, wired at kernel
admission — a single-module compiler structurally cannot see
across that). That residual stays an explicit blocker, **narrowed
not deleted**, in `planning/20-lazy-axon-evaluation.md` § Status +
`todo.md`.

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
