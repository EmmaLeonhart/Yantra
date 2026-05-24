"""The Yantra CLI calculator: type an expression, get the EXACT answer.

Drives `apps/calc.Calculator` with a battery of expressions and asserts
each result is exact. The arithmetic runs on real Sutra `.su` services
through the kernel; the text parsing is host orchestration. This is the
Meta-demo's "text parsing + reliable math" proof (planning/22): where
NCCLIGen would *generate* a plausible terminal frame for `5 * 10 =`,
Yantra *computes* 50 — exactly, every time.

Torch-gated like the other real-Sutra tests.
"""
from __future__ import annotations

import pathlib
import sys

import pytest

torch = pytest.importorskip("torch", reason="calc runs through real Sutra")

sys.path.insert(
    0, str(pathlib.Path(__file__).resolve().parent.parent / "apps" / "calc")
)
from calc import Calculator  # noqa: E402


@pytest.fixture(scope="module")
def calc() -> Calculator:
    return Calculator()


@pytest.mark.parametrize(
    "expr,expected",
    [
        ("5 * 10 =", 50),     # the headline
        ("5 * 10", 50),       # trailing '=' optional
        ("12 + 30", 42),
        ("100 - 7", 93),
        ("9 * 9", 81),
        ("0 * 9999", 0),
        ("123 + 877", 1000),
        ("1000 - 1000", 0),
        ("-4 * 6", -24),
        ("  7   +   8  =", 15),  # whitespace tolerance
        ("2 * 2", 4),
        ("4096 * 4096", 16777216),  # 2**24, top of the float32-exact range
    ],
)
def test_calc_is_exact(calc: Calculator, expr: str, expected: int) -> None:
    assert calc.evaluate(expr) == expected


def test_calc_rejects_unparseable(calc: Calculator) -> None:
    with pytest.raises(ValueError):
        calc.evaluate("not an expression")


def test_calc_division_is_unsupported_not_wrong(calc: Calculator) -> None:
    """Division has no Sutra runtime op yet — it must error, not guess."""
    with pytest.raises(ValueError):
        calc.evaluate("10 / 2")


@pytest.mark.parametrize("expr", ["4729 * 8831", "99999 * 99999", "12345679 * 9"])
def test_calc_refuses_out_of_exact_range(calc: Calculator, expr: str) -> None:
    """A result not float32-representable is refused, never guessed.

    The substrate returns an off-by-some value for these (each result
    is past 2**24 and not exactly representable); the exactness gate
    verifies against a host oracle and raises rather than printing a
    wrong answer. This is the "never a wrong answer" guarantee. (Exactly
    representable large values like 5000*5000=25_000_000 are still
    returned — the gate checks correctness, not a crude cutoff.)
    """
    with pytest.raises(ValueError):
        calc.evaluate(expr)


def test_calc_returns_large_but_exact_value(calc: Calculator) -> None:
    """A large-but-exactly-representable result is still returned."""
    assert calc.evaluate("5000 * 5000") == 25_000_000


def test_calc_demo_transcript_is_exact(calc: Calculator) -> None:
    """The runnable demo (apps/calc/demo.py) prints exact results."""
    from demo import run_demo

    lines = run_demo(calc)
    expected_prefix = [
        "5 * 10 = 50",
        "12 + 30 = 42",
        "100 - 7 = 93",
        "9 * 9 = 81",
        "123 + 877 = 1000",
        "-4 * 6 = -24",
        "4096 * 4096 = 16777216",
    ]
    assert lines[: len(expected_prefix)] == expected_prefix
    assert any(line.startswith("10 / 2 = (refused") for line in lines)
    assert any(line.startswith("99999 * 99999 = (refused") for line in lines)
