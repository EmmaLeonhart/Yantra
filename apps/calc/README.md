# `apps/calc` — the CLI calculator

Type `5 * 10 =`, get `50`. A plain text-in / text-out calculator — the
small, definitive contrast with Meta's *Neural Computers* (NCCLIGen, a
DiT video model that *generates* terminal frames and whose own paper
lists symbolic stability as unsolved). Two things it shows:

1. **Text parsing** — a real expression parser, not frame generation.
2. **Reliable math** — the arithmetic runs on the Sutra substrate
   through the kernel, exact by construction. Where a diffusion model
   hallucinates a plausible-looking number, Yantra computes the true
   one.

## Layering

Per `planning/01-architecture.md`, text I/O + parsing is **host
orchestration** (the CPU side's job); the `+ - *` operators are real
`.su` programs the kernel admits and runs on the substrate:

- `add.su`, `sub.su`, `mul.su` — each reads operands `a`/`b` from the
  input axon and returns the result on the real axis. Verified exact
  through the kernel (`tests/test_calc.py`).
- `calc.py` — the host driver: `Calculator.evaluate("5 * 10 =")` parses
  the expression, encodes the operands into a two-key axon, routes it to
  the right op service through the kernel, and decodes the real-axis
  result. `python apps/calc/calc.py` is an interactive REPL.

## Scope

- Exact for integer operands and results within the float32
  exact-integer range (`|value| < 2**24`). Bigger products (e.g.
  `4729 * 8831`) need an arbitrary-precision digit encoding —
  `planning/22-meta-demo-replication.md` Stage 3.
- **Division is not supported yet**: Sutra has no runtime real/complex
  division op (`docs/numeric-math.md` "Pending"). A `/` expression
  errors rather than printing a guess — adding it is a `yantra-driven`
  Sutra-branch change.
- No GUI. The button/grid version is the stretch demo in `planning/22`.

## Run the tests

```bash
pytest tests/test_calc.py -v   # 14 cases, all exact
```
