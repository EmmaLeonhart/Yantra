# 23 — Calculator: substrate purity (parse + dispatch + output all on the substrate)

**Why this exists.** The calculator (`apps/calc/`) is the headline demo's
exact-compute piece, but as built it cheats in two places that defeat the whole
point ("symbols/compute stay exact on the substrate where a video-diffusion model
drifts"):

1. **Host Python picks the operation.** `calc.py`'s `OPS[op]` selects which `.su`
   to run. Operation *selection* is part of the computation; a host `if`/dict
   choosing it is a substrate leak.
2. **Host Python returns the answer.** `_binop` computes on the substrate, then
   recomputes the exact answer with a host `Fraction`, compares, and **returns the
   host value** — using the substrate only as a pass/refuse gate. The displayed
   exactness is host-provided, not substrate-provided.

The four per-op files (`add/sub/mul/div.su`) are real substrate math. What's
missing is the *switch* and *trusting the substrate's own output*.

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

**Stage 3 — defuzzified one-hot switch:** from the operator build
`is_add/is_sub/is_mul/is_div` ≈ 1 for the match, ≈ 0 otherwise (defuzzification,
`is_true`/`select`, per
`external/Sutra/planning/sutra-spec/equality-and-defuzzification.md`). Then
`result = is_add·(a+b) + is_sub·(a−b) + is_mul·(a×b) + is_div·(a÷b)` — the three
unselected branches are ×0; only the chosen one survives. One substrate expression,
no host `if`.

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

`apps/calc/gui.py` (+ `!runCalculatorGUI.bat`) is a host Tkinter frontend bolted on
— **fake, to be removed** (see `queue.md`). The real OS-native GUI is doable but a
genuinely complicated thing; it's build-sequence-gated and deferred. String first.
