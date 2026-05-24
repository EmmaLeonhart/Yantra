# 23 — Calculator: substrate purity (parse + dispatch + output all on the substrate)

**Why this exists.** The calculator (`apps/calc/`) is the headline demo's
exact-compute piece, but as built it cheats in two places that defeat the whole
point ("symbols/compute stay exact on the substrate where a video-diffusion model
drifts"):

1. **Host Python picks the operation.** `calc.py`'s `OPS[op]` selects which `.su`
   to run. Operation *selection* is part of the computation; a host `if`/dict
   choosing it is a substrate leak. **CLOSED 2026-05-24** — replaced by
   `switch.su` (exact Lagrange one-hot masks on the substrate; see Stage 3).
2. **Host Python returns the answer.** `_binop` computes on the substrate, then
   recomputes the exact answer with a host `Fraction`, compares, and **returns the
   host value** — using the substrate only as a pass/refuse gate. The displayed
   exactness is host-provided, not substrate-provided. **STILL OPEN** — closing it
   means dropping the "never a wrong answer" refuse-gate, which is a user-facing
   product decision (see "Drop the exactness oracle" below). Flag for Emma; do not
   do autonomously.

The four per-op files (`add/sub/mul/div.su`) were real substrate math; they are
**removed** — `switch.su` computes all four internally and selects on the substrate.

## The correct design — parse + switch, all on the substrate

Host does **I/O only**: read the input line in, print the float out. Everything in
between runs in Sutra (which has the string ops — the codepoint `String`/`Character`
model).

**Stage 1 — a Sutra loop parses the string into two operand floats + an operator.**
Walk the codepoint string:
- Digit chars → strip the character flag (`AXIS_CHAR_FLAG`) → numeric value
  (`'5'` → `5.0`).
- Assemble multi-digit numbers by **place value**: accumulate (first digit ×10 +
  next ×1; generalizes to ×10^position). `"50"` → `5×10 + 0×1 = 50`. Fixed digit
  slots allocated up front — **start scope: 2-digit × 2-digit**; widen later
  (arbitrary precision = the digit-array generalization of exactly this).
- A **space** ends the current operand and advances the slot.
- The **operator char** is recorded (kept as a vector for Stage 3).
- **`=` is the trigger** — both operands assembled + operator known → fire.

**Stage 2 — compute all four ops at once:** `a+b`, `a−b`, `a×b`, `a÷b`.

**Stage 3 — exact one-hot switch. SHIPPED (Emma's `select` approach, active).**

`apps/calc/switch.su` selects the operation through the language's own
conditional-branching primitive, `select`, made exact by softmax saturation.
Emma's point: defuzzify/sharpen `select` enough and the branches stop blending. I
was wrong to first call this impossible. `select(scores, options)` is a
softmax-weighted superposition; it is not one-hot *at small score scale*, but
softmax **saturates to an exact one-hot** once scores are sharpened past the
float32 underflow point — `exp(−120)` is exactly `0.0`, so the off-branch weights
become exactly zero and the matched branch passes through clean. The piece that
was missing was a *separating scalar score*; `dot(op − make_real(t), make_real(1))`
reads the real-axis coordinate `op − t` as a clean scalar (the dot with the real
unit zeroes every other axis, including axon-recovery noise — which is why
elementwise `tanh` masks failed: they act on that noise). Then
`score_t = −120·(op−t)²` is `0` at the match and `≤ −120` elsewhere → softmax →
exact `[…,1,…]`. A second `select` over `[1,1,1,b]` picks the division denominator
(`b` for `op=÷`, else `1`) so `b=0` can't nan a killed branch. Measured **18/18
bit-exact incl. `b=0` and the 2²⁴ ceiling**; all 53 `tests/test_calc.py` green.
`calc.py` passes the op-code, host `OPS[op]` is gone — **leak 1 closed**.

Needs the `dot` builtin (Sutra **v0.6.1**, merged to main + submodule pinned there).

The earlier "select is softmax, never one-hot, 13/13 wrong" finding was real but
*incomplete*: it used barely-separated LLM-embedding scores and crude ×K scaling
(max weight 0.82), not `dot`-clean scores at saturating scale. **Retired interim:**
a Lagrange-polynomial-mask switch (`m_t(op)=Π_{j≠t}(op−j)/(t−j)`, also 18/18 exact,
no Sutra change) was the active switch until v0.6.1 landed; it worked but was an
arithmetic identity rather than the language's branching primitive, so it was
replaced by the `select` version. See `git log` for the Lagrange `switch.su`.

### Extending the exact range — float64 (LIVE 2026-05-24)

The "2²⁴ ceiling" is float32's exact-integer mantissa, not a fixed property. The
calc now runs the substrate in **float64**, extending the exact-integer range to
**2⁵³ (~9.007×10¹⁵)** with **no host carries** — the same `switch.su`, just
higher-precision substrate. `4729*8831 → 41761799` and `99999*99999 → 9999800001`
now return exact (were refused under float32); past 2⁵³ the substrate is inexact
again, so the gate still refuses (never-a-wrong-answer holds at the new ceiling).
Verified: 57/57 `test_calc.py` + full gate (114 passed, 1 xfail).

Enabling change: a selectable substrate dtype (`Codegen(runtime_dtype="float64")`),
additive + default-float32 — Sutra **v0.6.2** (merged to main, submodule pinned).
`calc.py` requests it; the kernel threads `runtime_dtype` through
`_compile_su_to_module` / `SutraService`.

**Correction (caught by tests, not a probe):** the `select` one-hot is only exact
if the off-branch weights underflow to *exactly* 0. The original sharpening
`−120·(op−t)²` underflows in float32 but **not float64** (`exp(−120) ≈ 8×10⁻⁵³` is
a normal float64), so a zero result like `1000−1000` picked up off-branch residue
`≈ 7.7×10⁻⁴⁷` and was refused. Fix: bump the constant to **1000**, so
`exp(−1000) = 0` in both float32 (underflow ≈ −88) and float64 (≈ −745) and the
one-hot is exact again. This is the substrate-pure path; digit-array arbitrary
precision (carry propagation, which must run on the substrate to stay pure) is the
separate, still-open step.

**Output:** the Sutra program's float goes out to the host, which displays it.
(Native float→string rendering *on the substrate* is a future want — there's no
method yet, so for now the host displays the float.)

This replaces all three host shortcuts: host parsing, host `OPS[op]` dispatch, host
`Fraction` oracle. `calc.py` shrinks to: read line → hand the string to the Sutra
calc → print the float.

**Drop the exactness oracle.** Float is float; verifying against a host oracle is
fine as a *test* in `tests/`, never the runtime value or a runtime refusal.

## Substrate-purity principle (also in CLAUDE.md)

- Host = I/O only. The returned value is decoded from the substrate, not
  host-recomputed.
- Operation *selection* is computation — defuzzified switch on the substrate, not a
  host `if`.
- No host oracle deciding/replacing the output.
- Even parsing belongs on the substrate (Sutra has the string ops); host parsing is
  a shortcut to retire, not a permanent boundary.

## GUI

**Removed (2026-05-24).** `apps/calc/gui.py` (+ `!runCalculatorGUI.bat`) was a host
Tkinter frontend bolted on — a fake stand-in for an OS GUI — and is deleted, along
with its controller test in `tests/test_calc.py`. The real OS-native GUI is doable
but a genuinely complicated thing; it's build-sequence-gated and deferred. String
first.
