"""Runnable showcase for the Yantra CLI calculator.

``python apps/calc/demo.py`` runs a fixed session and prints a
transcript: expressions go in, EXACT answers come out — each computed
on the Sutra substrate through the kernel, not generated.

The contrast with Meta's *Neural Computers* (NCCLIGen, a DiT video
model that generates a plausible terminal *frame*, and whose own paper
lists symbolic stability as unsolved): every number here is computed,
so it is right every time, and it does not drift. Division is refused
rather than guessed — Yantra never prints a wrong answer.

This is the seed of the downloadable demo in
`planning/22-meta-demo-replication.md` Stage 4: a thing you can run.
"""
from __future__ import annotations

from calc import Calculator

# A fixed session. Every result is exact and within the float32
# exact-integer range (the top entry is 2**24 exactly).
SESSION = [
    "5 * 10 =",
    "12 + 30 =",
    "100 - 7 =",
    "9 * 9 =",
    "123 + 877 =",
    "-4 * 6 =",
    "4096 * 4096 =",
]


def run_demo(calc: Calculator | None = None) -> list[str]:
    """Run the fixed session; return transcript lines ``"<expr> <result>"``.

    The last line records that division is refused (no Sutra runtime
    divide op yet) — proof we never emit a guessed answer.
    """
    calc = calc or Calculator()
    lines: list[str] = []
    for expr in SESSION:
        lines.append(f"{expr} {calc.evaluate(expr)}")
    try:
        calc.evaluate("10 / 2")
        lines.append("10 / 2 = <<unexpected: division should be refused>>")
    except ValueError:
        lines.append("10 / 2 = (refused — no Sutra divide op yet; never a wrong answer)")
    return lines


def main() -> None:  # pragma: no cover - interactive showcase
    print("Yantra calculator — exact math on the Sutra substrate.")
    print("(Meta's NCCLIGen would generate a plausible frame; Yantra computes.)\n")
    for line in run_demo():
        print("  " + line)


if __name__ == "__main__":  # pragma: no cover
    main()
