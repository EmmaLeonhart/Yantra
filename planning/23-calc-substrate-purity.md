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

**Stage 3 — exact one-hot switch (IMPLEMENTED + measured 2026-05-24).** The
original plan was a "defuzzified one-hot switch" via `is_true`/`select`. **That
does not work on the pinned substrate — measured, not assumed:**
- `is_true` is **not a builtin** in the pinned Sutra compiler (`588055e3`).
- `select(scores, options)` is a **softmax-weighted** superposition, never a hard
  one-hot. For a numeric (non-argmax-decodable) result it returns a blend of all
  four branches: measured **13/13 wrong, worst abs error 1.26×10⁷** (e.g.
  `1000 − 1000` → 250492). The operator embeddings are barely separated (match
  similarity 0.089 vs ~0.06 off-match), so softmax is ≈uniform (0.25 each); and
  sharpening can't reach one-hot (×100 → max weight only 0.82), while *any*
  residual weight on the product branch corrupts the real-axis number.

**What works (measured 18/18 bit-exact, incl. `b=0` and the 2²⁴ ceiling):** exact
**Lagrange one-hot masks** over the integer operator grid {0=+, 1=−, 2=×, 3=÷}.
With the operator as a real-axis code `op`, the basis polynomial
`m_t(op) = Π_{j≠t} (op−j)/(t−j)` is **exactly 1 at `op=t` and exactly 0 at every
other integer grid point**, using only real `+ − × ÷`. Then
`result = m0·(a+b) + m1·(a−b) + m2·(a×b) + quot`. The division branch is
**self-guarding** — `quot = (m3·a)/(m3·b + (1−m3))` is `a/b` when `op=÷` (m3=1) and
`0/1 = 0` otherwise — so a zero denominator in an *unselected* branch never poisons
the sum with nan (a genuine `÷0` still yields nan and is caught upstream by the
host, a domain error, not an arithmetic result). Shipped as `apps/calc/switch.su`;
`calc.py` passes the op-code and the host `OPS[op]` dispatch is gone. **Leak 1
closed.** All 53 `tests/test_calc.py` cases stay green.

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
