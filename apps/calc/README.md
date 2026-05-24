# `apps/calc` — the CLI calculator

Type `5 * 10 =` and get `50` — or a full expression like
`2 + 3 * 4 = 14`. A plain text-in / text-out calculator — the
small, definitive contrast with Meta's *Neural Computers* (NCCLIGen, a
DiT video model that *generates* terminal frames and whose own paper
lists symbolic stability as unsolved). Two things it shows:

1. **Text parsing** — a real expression parser, not frame generation.
2. **Reliable math** — the arithmetic runs on the Sutra substrate
   through the kernel, exact by construction. Where a diffusion model
   hallucinates a plausible-looking number, Yantra computes the true
   one.

Multi-term expressions with operator precedence and parentheses are
supported (`2 + 3 * 4 = 14`, `(10 - 2) * 5 = 40`): a recursive-descent
parser on the host evaluates **each binary operation on the substrate**
in turn, and the whole expression is refused if any step can't be exact.

## Layering

Per `planning/01-architecture.md`, text I/O + parsing is **host
orchestration** (the CPU side's job); the arithmetic — **including which
operation runs** — happens on the substrate:

- `switch.su` — one service computes all four operations and selects the
  requested one **on the substrate**, through Sutra's own `select`
  primitive made exact by softmax saturation. The host passes an operator
  code (`0=+ 1=- 2=* 3=/`); `dot(op - make_real(t), make_real(1))` reads
  the real-axis coordinate `op - t` as a clean scalar, and scores
  `-120*(op-t)^2` push `select`'s softmax past the float32 underflow point
  (`exp(-120)` = exactly 0), so it is a TRUE one-hot — the matched branch
  passes through, the others are killed by exact-zero weights. A second
  `select` guards the division denominator so `b=0` can't nan a killed
  branch. This replaced host `OPS[op]` dispatch (the host no longer picks
  which operation runs — the substrate does). Needs Sutra **v0.6.1** (the
  `dot` builtin). Verified 18/18 bit-exact incl. `b=0` and the `2**24`
  ceiling — see `planning/23-calc-substrate-purity.md`. (Naive
  unsharpened `select` blends all four branches; saturation is what makes
  it exact. An interim Lagrange-polynomial-mask switch was retired when
  v0.6.1 landed.)
- `calc.py` — the host driver: `Calculator.evaluate("5 * 10 =")` parses
  the expression, encodes the operands + operator code into an axon,
  routes it through the kernel to `switch.su`, and decodes the real-axis
  result. `python apps/calc/calc.py` is an interactive REPL.

## Scope

- **Never a wrong answer.** Every result is verified exact against a
  host oracle before it is returned; anything the substrate can't
  compute exactly is **refused**, not guessed. Integers up to `2**24`
  are always exact, and some larger ones too — the gate checks each
  result's correctness, not a crude cutoff (`5000 * 5000` is returned;
  `4729 * 8831` is refused). Extending the exact range to arbitrarily
  large products needs an arbitrary-precision digit encoding —
  `planning/22-meta-demo-replication.md` Stage 3.
- **All four operators** (`+ - * /`). Division uses Sutra's
  `complex_div` runtime and returns exact quotients (`10 / 2 = 5`,
  `7 / 2 = 3.5`); non-terminating quotients (`10 / 3`) and divide-by-zero
  are refused, never approximated — same "never a wrong answer" gate.
- No GUI. The button/grid version is the stretch demo in `planning/22`.

## Run the tests

```bash
pytest tests/test_calc.py -v   # 53 cases, all exact-or-refused
```
