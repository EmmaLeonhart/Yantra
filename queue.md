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

Reproduce the two things the Meta paper demonstrated — (1) a terminal
(their CLIGen) and (2) a desktop GUI (their GUIWorld) — on Yantra as
real execution, so the **symbols stay exact** where their
video-diffusion approach drifts. That contrast is the decisive proof
the design works. Goal + roadmap: `planning/22-meta-demo-replication.md`;
ambition in `todo.md` § 5.

**Decomposed into ordered, bounded steps. Work top-down; promote each
into its own active item as it is picked up. Focus = symbolic stability
via execution; we are NOT chasing video / screen-frame generation
(deferred, only if the GUI layer lands).**

Shipped: (a) the Stage-1 **symbol-fidelity harness** —
`tests/test_symbol_fidelity.py`, 1024/1024 symbols bit-exact through a
real Sutra service + the kernel router, zero drift — for both numeric
and **text** symbols (text is the axis Meta's NCCLIGen drifts on);
(b) the **CLI
calculator** — `apps/calc/`, full expressions (`2 + 3 * 4 = 14`,
precedence + parens), exact `+ - * /` with each sub-op on real Sutra
services through the kernel (division via `complex_div`;
`tests/test_calc.py`, 54 cases incl. a randomized never-a-wrong-answer
property test); every result is verified exact and refused if not —
**never a wrong answer**. **Caveat (audit 2026-05-24):** the per-op `.su`
math is real, but dispatch + the returned value are currently host-side —
not yet substrate-pure. Fix is step 3 below + `planning/23`. See
`planning/22`. Remaining steps:

1. **Minimal terminal surface.** A Sutra-native command reader
   (scripted or button-driven is fine — need not be keyboard-typed)
   that admits a utility through the kernel and shows its exact output.
   (The calc REPL already proves the text-in → exact-out pattern.)
2. **First CLI utilities beyond echo** (cat, ls, wc) — native Sutra,
   gated on Sutra's string + IO + FS vocabulary; promote from
   `todo.md` § 2 as each unblocks.
3. **Calculator — make it substrate-pure (PRIORITY), then the optimal demo.**
   **Substrate-purity gap (audit 2026-05-24):** as built, host Python picks which
   operation runs (`OPS[op]`) and returns a host `Fraction` answer (the substrate is
   used only as a pass/refuse gate). That defeats "computes on the substrate." Full
   redesign + measured findings in `planning/23-calc-substrate-purity.md`. Steps:
   - b. **Operator dispatch on the substrate — DONE 2026-05-24, shipped via `select`.**
     Host `OPS[op]` removed; the substrate selects through the language's own
     `select` primitive (Emma's idea), made exact by softmax saturation: scores
     `−120·(op−t)²` (read with `dot(op−t, make_real(1))`) push `exp(−120)` to exactly
     0, so softmax is a true one-hot. `apps/calc/switch.su`; needs Sutra **v0.6.1**
     (`dot` builtin), submodule pinned there. 18/18 bit-exact, 53/53 calc tests +
     full kernel gate (110 passed, 1 xfail) green. (The earlier "select can't be
     one-hot" finding was incomplete; a Lagrange-mask interim switch was retired when
     v0.6.1 landed — see `planning/23`.)
   - c. **Return the substrate float (OPEN — needs a product decision).** The host
     still returns a `Fraction` verified by a host oracle that REFUSES inexact /
     out-of-range results. Returning the substrate's decoded float instead means
     dropping the "never a wrong answer" refuse-gate (CLAUDE.md flags the runtime
     refusal as impure). That is a user-facing product change — do not make it
     autonomously. Flag for Emma.
   - d. **Parse on the substrate** — a Sutra loop over the codepoint string: digit →
     strip char flag → value; place-value assembly (2-digit cap to start); space ends
     an operand; `=` triggers. Host shrinks to read-line / print-float.
   - e. **Then the optimal demo:** arbitrary-precision (digit-array) so big products
     stay exact past the float32 2²⁴ ceiling.
   See `planning/23-calc-substrate-purity.md` (full design + findings) + `planning/22`.
4. **Demo on the site — DONE.** `site/index.html` has a "See it compute"
   section (the calculator transcript + the symbolic-stability contrast),
   live at yantra.emmaleonhart.com; `!runCalculator.bat` at the repo root
   opens the REPL locally, and `python apps/calc/demo.py` prints the
   transcript. Remaining: the contrast figure vs a generative baseline
   (a CLIGen-shaped model or Meta's published degradation numbers).

Not in scope: replicating their *video / screen-frame generation*
(NCGUIWorld-style) — deferred, optional, only if the GUI layer matures.

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
