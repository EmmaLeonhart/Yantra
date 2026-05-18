# Yantra — Work Queue

**This file is a queue, not a state snapshot.** It lists what is being worked on right now. Finished work lives in `git log`; longer-horizon ideas live in `planning/` or `todo.md`. When an item is done, delete it — no checkmarks, no status indicators. If an item is still here, it is not done.

**Why this file exists:** when a planning step (formal planning mode or just "think before doing") produces a plan, that plan is written here BEFORE execution starts. An interrupted session can pick up from the queue rather than from chat context that may be gone.

This repo currently holds **planning documents and a v0.0 kernel nucleus**, not a full implementation, so most "work" here is design and small implementation pieces. The same rule applies: design plans go into queue.md before they get executed against `planning/*.md` or `kernel/`.

See `CLAUDE.md` § "Workflow Rules" for how this file, planning mode, and the task tool stay in sync. Longer-horizon items live in `todo.md`.

---

## Active

### Bare-metal Linux 0.00 replica (user-requested 2026-05-17) — IN PROGRESS

User asked to "run the bare metal one". Correcting a conflation in
`planning/21` first: the bare-metal Linux 0.00 (32-bit protected
mode, VGA text memory, PIT timer IRQ, task switch) **needs no GPU
at all** — it was wrongly bundled with the v0.5 Sutra-on-real-GPU
passthrough gate. It is buildable now: QEMU is installed
(`C:\Program Files\qemu\`), nightly-2026-04-01 pinned, the v0.4
bootloader already runs real 32-bit Rust in QEMU via multiboot1.

**RESUME HERE (paused 2026-05-17, usage limits):**
`bootloader/src/bin/linux000.rs` is written (full multiboot1 +
GDT/IDT/PIC/PIT + 2 tasks + naked timer-ISR software switch).
Build blocker hit, with the exact fix known: `cargo build
--release --bin linux000` (in `bootloader/`, nightly-2026-04-01)
fails with `.json target specs require -Zjson-target-spec`. Next
step: add `-Zjson-target-spec` — either set
`RUSTFLAGS`/`CARGO_BUILD_RUSTFLAGS` is wrong (it's a cargo/`-Z`
flag): use `cargo +nightly-2026-04-01 -Z json-target-spec build
--release --bin linux000`, OR add `[unstable]
json-target-spec = true` to `bootloader/.cargo/config.toml` (note
the existing v0.4 `qemu-build` scripts may need the same flag — if
so that's a real pre-existing breakage to fix + note, not paper
over). Then: build → run in QEMU (`C:\Program Files\qemu\
qemu-system-x86_64.exe -kernel target/i686-yantra/release/
linux000 -serial stdio -display none -no-reboot`, kill after a few
s) → capture serial → verify banner + breadcrumbs + real
interleaved A/B + `[linux000 DONE]`. Then steps 4–6 below.

Plan (incremental, honest per-stage QEMU serial verification —
do NOT fake output):

1. `bootloader/src/bin/linux000.rs` — 2nd bin in the bootloader
   crate (reuses target spec / linker.ld / rust-toolchain).
   Multiboot1 + `_start` + COM1 serial + VGA text @0xB8000.
2. GDT (code/data), IDT, remap 8259 PIC (IRQ0→0x20), program 8253
   PIT (~100Hz).
3. Two tasks A/B, each its own stack: loop writing its char to VGA
   text buffer + COM1. Timer ISR (`global_asm!` naked: pusha/EOI/
   software ESP switch/popa/iret) round-robins A↔B — the faithful
   timer-interrupt task switch.
4. `scripts/linux000-build.{sh,bat}` + `linux000-run.{sh,bat}`.
5. Run in QEMU `-serial stdio -display none`, capture, assert the
   banner + a real interleaved A/B run + timer-IRQ proof. Report
   the measured serial transcript honestly. If the preemptive
   switch proves unstable after real iteration, document the
   precise failure + the faithful-but-simpler fallback — never a
   faked transcript.
6. Correct `planning/21-linux-0.00.md` + `bootloader/README.md`
   conflation (bare-metal Linux 0.00 ≠ GPU-gated); record measured
   result. Commit early/often.

Honest scope unchanged: this is 32-bit-protected-mode bare metal
in QEMU (faithful to Linux 0.00's actual mode). It is NOT the
v0.5 Sutra-kernel-on-real-GPU path (that needs Linux host + VFIO,
separate + larger; the user's free GPU is relevant to *that*, not
to this).

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
