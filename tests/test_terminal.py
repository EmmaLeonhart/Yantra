"""Tests for the Stage-2 terminal surface (apps/terminal).

The terminal admits utilities through the kernel and shows the
substrate's exact output. The point of the headline demo (planning/22)
is symbolic stability: every command's output is *computed*, exact by
construction, with zero drift across a session — the axis Meta's
NCCLIGen (a DiT video model that generates terminal frames) lists as
unsolved. These tests pin that:

  - ``echo`` carries text bit-exact through ``echo.su`` on the substrate
    (the displayed string is the substrate's decode, not a host re-echo).
  - ``calc`` computes arithmetic on the substrate via the terminal.
  - A scripted N-step interaction trace matches an exact transcript at
    *every* step — the measurable zero-drift claim.

Skipped when torch is not installed (utilities run through real Sutra).
"""
from __future__ import annotations

import pathlib

import pytest

torch = pytest.importorskip("torch", reason="terminal runs utilities through real Sutra")

from apps.terminal.terminal import CommandError, Terminal


REPO = pathlib.Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def term() -> Terminal:
    """One terminal for the module — compiling echo (+ calc on first use)
    is the expensive part; reuse it across cases."""
    return Terminal()


# --- echo: exact text through the substrate ---------------------------------

ECHO_CASES = [
    "hello",
    "hello world",
    "the quick brown fox",
    "echo 12345",
    "punctuation: a,b.c!? (x) [y]",
    "internal  multiple   spaces  kept",  # spaces inside the arg survive
    "",
]


@pytest.mark.parametrize("text", ECHO_CASES)
def test_echo_is_bit_exact_through_substrate(term: Terminal, text: str) -> None:
    """`echo <text>` returns <text> verbatim, decoded from the substrate."""
    assert term.run(f"echo {text}") == text


def test_echo_no_args_is_empty(term: Terminal) -> None:
    """`echo` with no argument echoes the empty string."""
    assert term.run("echo") == ""


# --- calc: arithmetic through the substrate via the terminal -----------------

CALC_CASES = [
    ("calc 5 * 10 =", "50"),
    ("calc 2 + 3 * 4 =", "14"),
    ("calc (10 - 2) * 5 =", "40"),
    ("calc 100 / 4 =", "25"),
    ("calc 7 / 2 =", "3.5"),
]


@pytest.mark.parametrize("line,expected", CALC_CASES)
def test_calc_command_computes(term: Terminal, line: str, expected: str) -> None:
    assert term.run(line) == expected


def test_calc_refuses_inexact(term: Terminal) -> None:
    """A non-terminating quotient is refused, not approximated."""
    with pytest.raises(CommandError, match="calc:"):
        term.run("calc 10 / 3 =")


def test_calc_usage_without_expression(term: Terminal) -> None:
    with pytest.raises(CommandError, match="usage: calc"):
        term.run("calc")


# --- dispatch + housekeeping ------------------------------------------------

def test_unknown_command(term: Terminal) -> None:
    with pytest.raises(CommandError, match="command not found: frobnicate"):
        term.run("frobnicate --help")


def test_blank_line_is_noop(term: Terminal) -> None:
    assert term.run("") == ""
    assert term.run("   ") == ""


def test_help_lists_commands(term: Terminal) -> None:
    out = term.run("help")
    assert "echo" in out and "calc" in out and "help" in out


# --- the measurable claim: a scripted trace, exact at every step ------------

def test_scripted_trace_zero_drift(term: Terminal) -> None:
    """A multi-step interaction trace matches an exact transcript.

    This is the headline-demo measurement (planning/22 § "Making it
    measurable") at small N: record every symbol that should appear, run
    the trace, assert 100% exact match at *every* step. A generative
    (DiT-frame) terminal drifts as N grows; ours is flat at exact.
    """
    script = [
        "echo booting yantra",
        "calc 2 + 2 =",
        "echo symbols stay exact",
        "calc 4729 * 8831 =",          # exact in float64 (was refused in float32)
        "echo 1234567890",
        "calc (3 + 4) * (5 + 6) =",
        "help",
        "echo done",
    ]
    expected = [
        "booting yantra",
        "4",
        "symbols stay exact",
        "41761799",
        "1234567890",
        "77",
        "yterm commands: calc, echo, help",
        "done",
    ]
    assert term.run_script(script) == expected
