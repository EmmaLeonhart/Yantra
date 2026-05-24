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

- **Never a wrong answer.** Every result is verified exact against a
  host oracle before it is returned; anything the substrate can't
  compute exactly is **refused**, not guessed. Integers up to `2**24`
  are always exact, and some larger ones too — the gate checks each
  result's correctness, not a crude cutoff (`5000 * 5000` is returned;
  `4729 * 8831` is refused). Extending the exact range to arbitrarily
  large products needs an arbitrary-precision digit encoding —
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
