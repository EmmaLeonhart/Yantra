# Replicating Linux 0.00 on Yantra

> **What this document is.** A concrete, executable design for a
> Yantra-native replica of **Linux 0.00** — Linus Torvalds' earliest
> preserved kernel. Written 2026-05-17 from a queue item the user
> added (`try to implement this
> https://computernewb.com/wiki/Linux_0.00`) so a fresh session
> (incl. the scheduled cron) can execute it without chat context.
>
> **What this document is not.** A claim that Yantra boots bare
> metal like Linux 0.00 does. The honest-scope section below states
> exactly what maps and what does not.

## What Linux 0.00 actually is

Linux 0.00 (1991, preserved at oldlinux.org `kernel/0.00/`) is
**two assembly files**:

- `boot.s` — a 512-byte boot sector. BIOS loads it at `0x7c00`; it
  prints a load message, pulls the kernel off disk, sets up a
  minimal GDT, enters 32-bit protected mode, jumps to the kernel.
- `head.s` — the kernel. Sets up the GDT/IDT, **two TSS + two LDT**
  (one per task), programs the 8253 PIT timer and unmasks the
  timer IRQ on the 8259 PIC, installs a timer-interrupt handler
  that **hardware-task-switches** between the two tasks (far jump
  to the other task's TSS selector), and installs an `int 0x80`
  `write_char` system call that pokes a character into VGA text
  memory and advances the cursor.

Runtime behaviour: **task A loops writing `A`; task B loops writing
`B`; the timer interrupt flips between them**, so the screen fills
with `AAAA…BBBB…AAAA…`. That is the entire program. Its whole point
is *the smallest possible OS that demonstrates kernel-mediated
multitasking of two trivial output tasks*.

## The faithful Yantra mapping

Yantra's build sequence (CLAUDE.md, `planning/18`): **milestone 1
is the Connectome Manager**, whose Python v0.0 (`kernel/`) is real
and tested — `Init` admission + `AxonRouter` + `tick()` +
`SutraService` running real Sutra-compiled `.su` on torch tensors.
That is "enough built for it."

Linux 0.00 concept → Yantra-native realization:

| Linux 0.00 | Yantra |
|---|---|
| Task A (writes `A` forever) | `kernel/services/task_a.su` — `on_axon` emits a vector decoding to codepoint **65** on its output role each tick |
| Task B (writes `B` forever) | `kernel/services/task_b.su` — same, codepoint **66** |
| `write_char` syscall (`int 0x80`) → VGA memory | a console/sink service that consumes both output roles and accumulates the ordered character stream |
| Timer IRQ that flips tasks | `Init.tick()` — one tick = one timer fire; the kernel runs the admitted tasks and the router carries their output |
| Hardware TSS context switch | **(deliberately NOT replicated — see honest scope)** Yantra's kernel does not context-switch (`kernel/init.py` docstring: "Does NOT schedule — the GPU runs every admitted process simultaneously"). Both tasks live in the connectome at once; the tick is the timer analogue; output interleaves under kernel mediation |

This is a *faithful translation of Linux 0.00's purpose*, not a
cargo-culted TSS. Linux 0.00 demonstrates "kernel mediates two
trivial output tasks"; the Yantra realization demonstrates exactly
that in Yantra's connectome model.

## Concrete deliverables (a fresh session executes these)

1. **`kernel/services/task_a.su`** and **`task_b.su`**. Contract:
   `function vector on_axon(vector input_axon)` returns a vector
   that decodes to codepoint 65 (`A`) / 66 (`B`) using the current
   Sutra string/number vocabulary (e.g. `make_string`/codepoint).
   **If the Sutra string vocab cannot cleanly emit a single
   codepoint vector, fall back to a distinct constant per task and
   decode by nearest-vector in the test — and say so plainly in
   this doc and the test (do not fake an `A`/`B` that isn't there).**
   Keep the body substrate-pure (no host shortcuts) per Sutra
   CLAUDE.md.
2. **`kernel/manifests/task_a.toml`, `task_b.toml`**, and a console
   manifest (reuse `sink.toml` shape if it fits). Each declares
   `axon_width`, `compute_units`, `read_roles`, `write_roles`,
   `source`.
3. **`tests/test_linux_000.py`**. Admit `task_a`, `task_b`, console
   into one `Init`; run N ticks; assert: (a) both characters reach
   the console, (b) the stream is kernel-mediated and interleaved
   (both tasks present across ticks — the `AAAA…BBBB…` analogue),
   (c) each task's emitted vector decodes to its intended codepoint.
   Real `SutraService` (use `make_shared_sutra_services` for one
   shared `_VSA`). **No weakened assertions; report measured
   decode similarity honestly** (Sutra CLAUDE.md safety rules bind
   even in a Yantra-driven session).
4. **README / queue**: note the demo under `kernel/README.md`
   "What runs today"; delete the queue item on completion.
5. Update this doc's status section with measured results.

## Honest scope — what is NOT replicated

- **No bare-metal boot.** Linux 0.00's defining trait is that it
  boots from a 512-byte sector into protected mode on real x86.
  Yantra's bootloader (`bootloader/`, Rust, v0.4) reaches long
  mode in QEMU but **real Sutra-kernel execution at boot is gated
  on GPU passthrough** (VFIO + spare GPU, or a GRUB ISO build —
  `bootloader/README.md`). A bare-metal A/B-on-the-framebuffer
  replica (real PIT IRQ + TSS + VGA writes in Rust long mode) is
  the *deeper-fidelity* version and is a **separate, bootloader-
  track item**, not this one. This item is the milestone-1
  (Connectome Manager) realization, which is what is buildable
  today. Naming this gap is required by CLAUDE.md "Don't paper
  over difficulty."
- **No hardware task switch.** By Yantra architecture, on purpose
  (see table). The faithfulness is to the *purpose*, not the TSS
  mechanism.

## Status

**DONE — 2026-05-17** (executed by the scheduled cron session).

Files added:

- `kernel/services/task_a.su`, `task_b.su` — emit `real_number(65.0)`
  / `real_number(66.0)` (substrate op `_VSA.make_real`; the literal
  ASCII codepoints of `A`/`B`, not a faked constant).
- `kernel/services/console.su` — passthrough fan-in receiver (the
  VGA-memory analogue).
- `kernel/manifests/task_a.toml`, `task_b.toml`, `console.toml`.
- `tests/test_linux_000.py` — 3 tests, real shared-runtime
  `SutraService`s via `make_shared_sutra_services`.

Measured (printed by the test, not tuned):

```
[linux 0.00] stream='ABABABABABABABAB'  real(task_a)=65.0  real(task_b)=66.0
```

- `real(task_a) == 65.0` exactly, `real(task_b) == 66.0` exactly —
  decoded host-side via the `.real()` monitoring accessor. Literal
  `chr(65)=='A'` / `chr(66)=='B'`; **no fudged tolerance** (the
  1e-5 guard is float-repr only; the values are exact).
- `stream == "AB" * 8` over 8 ticks: both hardcoded tasks ran every
  tick under kernel mediation (neither starved), output interleaved
  and carried by the real `AxonRouter` — the faithful Linux-0.00
  "kernel alternates two trivial output tasks" behaviour.
- Capability check verified real (a task cannot write a role it
  doesn't hold) — this is the real Connectome Manager, not a stub.

`pytest tests/test_linux_000.py` → **3 passed**. Full kernel
regression `tests/test_kernel.py tests/test_kernel_sutra.py
tests/test_linux_000.py` → **50 passed, 1 xfailed** (the
unrelated connectome-projection strict-xfail, still correctly
xfailing — no regression from the Sutra v0.4.1 submodule bump).

The per-task-constant fallback in the deliverables note was NOT
needed: Sutra's `real_number` cleanly emits a single decodable
codepoint vector, so the A/B are genuine substrate values, not
opaque constants. Honest-scope limits below stand unchanged.

## Cross-references

- `kernel/README.md` — the v0.0 Connectome Manager API this builds on.
- `kernel/init.py` — `Init.tick()` (the timer-IRQ analogue) + the
  explicit "does NOT schedule / context-switch" design.
- `bootloader/README.md` — where the deeper bare-metal replica's
  blockers (GPU passthrough / GRUB ISO) are recorded.
- `planning/18-kernel-browser-readiness.md` — build-sequence context.
- Source: <https://computernewb.com/wiki/Linux_0.00>,
  oldlinux.org `Linux.old/kernel/0.00/`.
