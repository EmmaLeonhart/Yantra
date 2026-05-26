# Yantra — Work Queue

**This file is a queue, not a state snapshot.** It lists what is being worked on right now. Finished work lives in `git log`; longer-horizon ideas live in `planning/` or `todo.md`. When an item is done, delete it — no checkmarks, no status indicators. If an item is still here, it is not done.

**Why this file exists:** when a planning step (formal planning mode or just "think before doing") produces a plan, that plan is written here BEFORE execution starts. An interrupted session can pick up from the queue rather than from chat context that may be gone.

This repo currently holds **planning documents and a v0.0 kernel nucleus**, not a full implementation, so most "work" here is design and small implementation pieces. The same rule applies: design plans go into queue.md before they get executed against `planning/*.md` or `kernel/`.

See `CLAUDE.md` § "Workflow Rules" for how this file, planning mode, and the task tool stay in sync. Longer-horizon items live in `todo.md`.

---

## Active

### ⚙️ Environment — this machine IS capable (read before doubting hardware)

**Emma's machine has a real, good GPU — an RTX 4070, `torch.cuda.is_available()`
== True — and ample compute.** Do NOT assume CPU-only, do NOT assume "the GPU
path won't work," do NOT pre-emptively frame Emma's algorithms/logic as
unworkable on this hardware. Measured 2026-05-24: admitting a Sutra program
allocates real GPU memory (+712,704 B for `echo`, `_VSA.device == cuda`); the
GPU-tier residency tests pass 4/4 in isolation; the calc runs float64 exactly.
When a GPU-dependent test looks like it "fails," first check whether it's a
test-isolation / shared-substrate artifact (it usually is) — run it alone before
concluding a capability is missing. If you catch yourself hedging "probably no
CUDA / probably won't work," stop: verify by running, the capability is there.

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
(b) the **CLI calculator** — `apps/calc/`, full expressions
(`2 + 3 * 4 = 14`, precedence + parens), exact `+ - * /`. **Which
operation runs is selected ON the substrate** by `switch.su` (Sutra's
`select` made a true one-hot via softmax saturation; needs Sutra v0.6.1
`dot`), and the calc runs the substrate in **float64** (v0.6.2
`runtime_dtype`) so exact integers hold to 2⁵³ (~9.007e15); results past
that are refused, never guessed. `tests/test_calc.py`, **57 cases** incl.
a randomized never-a-wrong-answer property test; full kernel gate 114
passed, 1 xfail (measured 2026-05-24). **Remaining purity gap (step c
only):** the returned value is still a host `Fraction` behind a
host-oracle refuse-gate — closing it is a product decision (drop "never a
wrong answer"), flagged for Emma, not done autonomously. Dispatch is no
longer host-side. See `planning/23`, `planning/22`.

(c) **echo content-verified (2026-05-24).** The `apps/echo` smoke test now
asserts the echoed STRING is recovered verbatim, not just that an axon is
delivered: `test_echo_echoes_string_content_exactly` binds `make_string(text)`
under `stdin_text`, routes through the kernel, unbinds `stdout_text`, and decodes
— bit-exact across 46 varied strings (incl. empty/punctuation/spaces) under the
current pinned Sutra (main 6cdca94b). The 2026-05-14 bundle-decoding regression
the old test cited is stale for this `make_string` path (NB: that finding tracked
codebook-cleanup *cosine margins* — a different decode path not re-measured here).
This de-risks the terminal surface below: a terminal can rely on echo carrying text verbatim.

(d) **Terminal surface (Stage 2) shipped (2026-05-24).** `apps/terminal/terminal.py`
is a command reader over kernel-admitted utilities: `echo <text>` carries text
bit-exact through `echo.su` and shows the SUBSTRATE's decoded string (not a host
re-echo); `calc <expr>` evaluates on the calc substrate; `help`; unknown → shell-style
`command not found`. **Which utility a typed command names is admission/routing = host
orchestration by design** (the Connectome Manager's "what is connected to what"),
distinct from calc's *which-operation* dispatch which is substrate compute — the two
look alike but sit on opposite sides of the host/substrate line. `Terminal.run_script`
runs an N-step interaction trace exact at EVERY step (zero drift — the planning/22
measurement at small N). `tests/test_terminal.py` 19/19 green; `python apps/terminal/demo.py`
prints a transcript. Does NOT close calc's step-c gap (composes calc as-is). See
`apps/terminal/README.md`, `planning/22` Stage 2.

Remaining steps:

1. **First CLI utilities beyond echo** (cat, ls, wc) — native Sutra,
   gated on Sutra's string + IO + FS vocabulary; promote from
   `todo.md` § 2 as each unblocks.
2. **Calculator — make it substrate-pure (PRIORITY), then the optimal demo.**
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
     **FIRST PIECE SHIPPED + VERIFIED 2026-05-24.** `apps/calc/parse_int2.su` parses
     a 1-or-2 digit non-negative integer ON THE SUBSTRATE: `string_char_at` gives
     the codepoint (a real number), digit = `cp−48`, length-aware place value
     without comparisons (`(c0-48)*(1+9*(n-1)) + (c1-48)*(n-1)`, n=`string_length`),
     and `make_real` lifts the final scalar onto the real axis (that lift was the
     blocker — a bare 0-d codepoint scalar didn't decode; `make_real` fixes it).
     `tests/test_calc_parse.py`: exact over all of 0–99 (real run). No host
     parsing in the path. **Operator dispatch WIRED into the calc on the
     substrate — DONE + VERIFIED 2026-05-25.** `switch.su` now reads the operator
     as a 1-char string (`op_char`), takes its codepoint (`string_char_at`), and
     scores the operator codepoints (43/45/42/47 for +−*/) to select the
     operation — so the host `CODE[op]` dict is GONE; `calc.py` feeds
     `make_string(op)`. The operator→operation mapping is now fully a substrate
     decision (no host arithmetic-decision left in the dispatch). Verified against
     the showcase suite: **`tests/test_calc.py` 57/57 pass** (incl. the 18/18
     dispatch + the never-a-wrong-answer property test). `apps/calc/parse_op.su`
     remains as a standalone op-code demonstrator (its 4/4 test still passes; the
     calc no longer needs it since switch.su does the codepoint dispatch inline).
     **Remaining toward full step d:**
       - variable length >2 digits (Sutra accumulator loop / digit array).
         **ATTEMPTED 2026-05-25, BLOCKED — needs a deliberate Sutra-loop session.**
         Numeric `iterative_loop`s work (verified: count-to-5 → 5.0; sum of
         `iterator` 1..4 → 10.0). But a loop that *parses a string* —
         `iterative_loop acc(n, value, str){ d = str.string_char_at(iterator-1)-48;
         pass value*10+d, replace; }` — does not run. Failure modes hit, in order:
         (a) loop state args must be `slot` vars (fixed: `slot string str = s`);
         (b) then a RUNTIME `expand([868], size=[])` in `slot_store` — an 868-vector
         being coerced into a scalar-shaped slot (every value here, incl.
         `string_length()`, is an 868-d vector; `slot scalar n = string_length()`
         and/or the loop's mixed scalar/vector state threading mis-shapes). Tried
         value as `scalar` and as `vector`; same error. Likely also: `iterative_loop`
         wants a STATIC count, but length is dynamic (→ `while_loop i<n`). The clean
         loop idiom for string iteration + dynamic count + a numeric accumulator
         was not found in this session; may need a Sutra-side helper or a documented
         idiom. NOT faked — no working variable-length parser shipped. (parse_int2's
         1–2 digit place-value formula remains the only working substrate int parse.)
       - two-operand "DD OP DD" split — find the operator position on the
         substrate (needs the same scan/loop — blocked by the above);
       - a FULL substrate parser to replace calc.py's host recursive-descent
         parser is a big build, NOT a drop-in: the host parser handles precedence,
         parens, and arbitrary expressions the current pieces do not, so a naive
         swap would REGRESS the calc. Finding: `planning/23` Stage-1.
   - e. **Extend the exact range — float64 DONE 2026-05-24; arbitrary precision open.**
     **float64 substrate (substrate-pure, no host carries) — LIVE.** The calc now
     compiles `switch.su` in float64 (Sutra **v0.6.2** `runtime_dtype`, merged +
     pinned), extending exact integers from float32's ~2²⁴ to **2⁵³ (~9.007e15)**:
     `4729*8831` and `99999*99999` now return exact (were refused), past 2⁵³ still
     refuses (never-a-wrong-answer holds). 57/57 calc + full gate (114 passed, 1
     xfail) green. Sharpening bumped 120→1000 so off-weights still underflow to
     exactly 0 in float64 (else a zero result like 1000−1000 picks up ~1e-47 and
     gets refused — caught by tests, fixed). NOT host-carry arithmetic.
     **Still open — arbitrary precision (digit-array):** true unbounded exactness;
     would need carry propagation on the substrate (not host) to stay pure.
   See `planning/23-calc-substrate-purity.md` (full design + findings) + `planning/22`.
3. **Demo on the site — DONE.** `site/index.html` has a "See it compute"
   section (the calculator transcript + the symbolic-stability contrast),
   live at yantra.emmaleonhart.com; `!runCalculator.bat` at the repo root
   opens the REPL locally, and `python apps/calc/demo.py` prints the
   transcript. Remaining: the contrast figure vs a generative baseline
   (a CLIGen-shaped model or Meta's published degradation numbers).

Not in scope: replicating their *video / screen-frame generation*
(NCGUIWorld-style) — deferred, optional, only if the GUI layer matures.

### GUI — substrate-computed pixels + interactive click toggle

**DONE 2026-05-24/25.** Yantra's first GUI, content computed on the substrate.
- **Static frame:** `apps/gui/frame.su` (`pixel(x,y)=1−x²−y²`) + `apps/gui/window.py`
  render a radial glow; every pixel is a substrate call. `tests/test_gui_render.py`
  (3 tests). First frame: `apps/gui/first_frame.png`.
- **Interactive click red↔blue toggle (Emma's idea):** `apps/gui/toggle.su`
  (`flip(s)=1−s`, the colour STATE transition computed ON THE SUBSTRATE) +
  `apps/gui/click_demo.py` — click anywhere → flip the state on the substrate →
  recolour the glow red (0) / blue (1). Verified: flip 0→1→0 on the substrate;
  red/blue frames render correctly (`click_red.png`, `click_blue.png`).
  `tests/test_gui_click.py` (2 tests pass). Run: `python apps/gui/click_demo.py`.

**Open GUI issues / handoff (next session):**
1. **Live window + click are NOT headless-testable** — the tkinter window and the
   click event can only be verified by hand (`python apps/gui/click_demo.py`).
   The substrate parts (field, flip, tint) ARE tested; the GUI tests stop at the
   render/state boundary. Verify the actual window interactively.
2. **Per-pixel render is slow — batching is BLOCKED on a Sutra-side change.**
   `render_field` calls the substrate once per pixel (64×64 = 4096 calls). The
   obvious fix — call the compiled `pixel` with batched tensor inputs — FAILS:
   probed 2026-05-25, `make_real` is scalar-only (`only one element tensors can
   be converted to Python scalars`), so the compiled graph can't take a batch
   dim. Batching needs either a Sutra-side `make_real` that accepts a batch
   (Sutra change — do on `yantra-driven` / a deliberate session) or the
   returned-vector decoder (#3). Not a clean Yantra-side fix.
3. **Emma's "returns a vector → reorganise into pixels" (reverse-CNN decoder)**
   is not built — the current GUI computes pixels per-coordinate, not by decoding
   one returned vector into a frame. That decoder is the bigger next step
   (planning/24-first-gui.md).
4. **Window belongs in the orchestrator eventually** — host tkinter is the
   stand-in; the real window is a Rust-orchestrator unit (planning/01).
5. Host does tint/colormap + event handling (I/O); the field + state are
   substrate. Keep that split — don't let host-drawn content masquerade as
   substrate output.

---

## Pointers

- Longer-horizon items: `todo.md`
- Kernel runtime nucleus: `kernel/` (see `kernel/README.md`)
- First userspace utility: `apps/echo/` (see `apps/README.md`)
- Terminal surface (Stage 2): `apps/terminal/` (see `apps/terminal/README.md`)
- Bare-metal QEMU bootloader: `bootloader/` (see `bootloader/README.md`)
- Design notes: `planning/` (numbered for reading order)
- Open architectural questions: `planning/15-open-questions.md`
- Memory model open hard problem: `planning/17-memory-model.md`
- Boot sequence: `planning/19-boot-sequence.md`
- Lazy axon evaluation: `planning/20-lazy-axon-evaluation.md`
- Kernel + browser readiness audit: `planning/18-kernel-browser-readiness.md`
- First GUI: `planning/24-first-gui.md`; v0.2.0 accuracy audit: `planning/25-v0.2.0-retrospective.md`
- Paper + AI peer review pipeline: `paper/` (see `paper/README.md`)
- External dependencies: `external/` (submodules)
- Cross-repo workflow (Yantra ↔ Sutra): `CLAUDE.md` § "Cross-repo workflow"
- **Precompile every .su to prime the codegen cache:**
  `python scripts/precompile_all_su.py` — run after a fresh clone or
  after a Sutra submodule bump, so demos + tests don't pay the slow
  codegen on first launch. Caches are committed; the script just
  populates them when the manifest changes. Add a row to its
  `_MANIFEST` when a new .su that benefits from precompilation lands.
- Narrative history: `git log`
