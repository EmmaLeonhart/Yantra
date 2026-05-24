"""Yantra CLI calculator — type ``5 * 10 =`` and it prints ``50``.

Not a GUI: a plain text-in / text-out calculator. It is the small,
definitive contrast with Meta's *Neural Computers* (NCCLIGen — a DiT
video model that *generates* terminal frames, and whose own paper
names symbolic stability as unsolved). Two things it demonstrates:

  1. **Text parsing** — a real expression parser, not frame generation.
  2. **Reliable math** — the arithmetic runs on the Sutra substrate
     through the kernel, exact by construction. Where a diffusion model
     would hallucinate a plausible-looking number, Yantra computes the
     true one.

Layering matches the architecture (planning/01): text I/O + parsing is
**host orchestration** (the CPU side's job); the arithmetic — including
*which* operation runs — happens on the substrate. ``switch.su`` computes
all four ops and selects the requested one with exact Lagrange one-hot
masks driven by an operator code, so the host does not pick the operation
with an ``OPS[op]`` dispatch. Multi-term expressions with precedence and
parentheses are supported (``2 + 3 * 4 = 14``, ``(10 - 2) * 5 = 40``) — a
recursive-descent parser on the host evaluates each binary operation on
the substrate in turn.

Known remaining purity gap (planning/23 step c): the result is still
verified against a host oracle and REFUSED if it can't be confirmed (a
non-terminating quotient like ``10 / 3``, a divide-by-zero, or a result
past the float32 exact range) — never approximated. Returning the
substrate's own decoded float (dropping the refuse-gate) is a pending
product decision. Arbitrary precision is planning/22 Stage 3.
"""
from __future__ import annotations

import operator
import pathlib
import re
import sys
from fractions import Fraction

# Allow running standalone (`python apps/calc/calc.py`, `demo.py`): put
# the repo root on sys.path so `from kernel import ...` resolves even
# when this file is the script entry point (pytest already does this via
# pyproject's pythonpath; a bare `python` invocation does not).
_REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from kernel import Init, Manifest, PythonService, SutraService  # noqa: E402
from kernel.router import Axon  # noqa: E402

APPS_CALC = pathlib.Path(__file__).resolve().parent
AXON_WIDTH = 768

# operator symbol -> real-axis op-code fed to switch.su, which selects the
# operation ON THE SUBSTRATE via exact Lagrange one-hot masks (not a host
# `if`/dict). 0=+, 1=-, 2=*, 3=/ — the integer grid switch.su interpolates.
CODE = {"+": 0.0, "-": 1.0, "*": 2.0, "/": 3.0}
# Host oracle for the exactness gate (monitoring only): exact rational
# arithmetic used to verify each substrate op's result.
_FOPS = {
    "+": operator.add, "-": operator.sub,
    "*": operator.mul, "/": operator.truediv,
}
# Expression tokens: integer literals, the four operators, parentheses.
_TOKEN = re.compile(r"\d+|[-+*/()]")


def _fmt(x: Fraction) -> int | float:
    """An int when integral, else a float — for display/error messages."""
    return int(x) if x.denominator == 1 else float(x)


class Calculator:
    """A CLI calculator whose arithmetic runs on the Sutra substrate.

    Construct once (compiles the three op services), then call
    :meth:`evaluate` per expression.
    """

    def __init__(self) -> None:
        self.init = Init(compute_pool=32)
        # ONE service computes every operation and selects the requested
        # one on the substrate (switch.su's Lagrange masks). No host
        # `OPS[op]` choosing which .su to run.
        self._service = SutraService(
            source_path=APPS_CALC / "switch.su",
            output_role="R_switch_out",
        )
        self.init.admit(
            Manifest(
                name="switch", axon_width=AXON_WIDTH, compute_units=1,
                read_roles=frozenset({"R_switch_in"}),
                write_roles=frozenset({"R_switch_out"}),
                source="switch.su",
            ),
            self._service,
        )

        # Host producer (injects the input axon) and sink (reads the
        # result). The math — including which operation runs — happens
        # inside switch.su; these are just the orchestrator's I/O endpoints.
        self._producer = PythonService(lambda s, ax: None)
        self.init.admit(
            Manifest(
                name="calc_in", axon_width=AXON_WIDTH, compute_units=1,
                read_roles=frozenset(), write_roles=frozenset({"R_switch_in"}),
                source="calc_in.py",
            ),
            self._producer,
        )
        self._received: list[Axon] = []
        sink = PythonService(on_axon=lambda s, ax: self._received.append(ax))
        self.init.admit(
            Manifest(
                name="calc_out", axon_width=AXON_WIDTH, compute_units=1,
                read_roles=frozenset({"R_switch_out"}), write_roles=frozenset(),
                source="calc_out.py",
            ),
            sink,
        )

    def evaluate(self, line: str) -> int | float:
        """Evaluate an arithmetic expression on the substrate.

        Supports multi-term expressions with ``+ - * /``, precedence, and
        parentheses (``2 + 3 * 4`` → ``14``), unary minus, and an optional
        trailing ``=``. Each binary operation is computed on a real Sutra
        service through the kernel and verified exact; the returned value
        is an ``int`` (or a ``float`` for an exact fraction like
        ``7 / 2``). Raises ``ValueError`` on a parse error, division by
        zero, or any result the substrate cannot compute exactly (refused,
        never approximated).
        """
        toks = self._tokenize(line)
        self._toks, self._pos = toks, 0
        value = self._parse_expr()
        if self._pos != len(toks):
            raise ValueError(
                f"unexpected token {toks[self._pos]!r} in {line!r}"
            )
        return _fmt(value)

    @staticmethod
    def _tokenize(line: str) -> list[str]:
        s = line.strip()
        if s.endswith("="):
            s = s[:-1]
        toks = _TOKEN.findall(s)
        # Reject stray characters: the tokens must account for everything
        # but whitespace.
        if "".join(toks) != re.sub(r"\s+", "", s):
            raise ValueError(f"cannot parse expression: {line!r}")
        if not toks:
            raise ValueError(f"empty expression: {line!r}")
        return toks

    # --- recursive-descent parser; each binary op runs on the substrate ---

    def _peek(self) -> str | None:
        return self._toks[self._pos] if self._pos < len(self._toks) else None

    def _parse_expr(self) -> Fraction:  # term (('+' | '-') term)*
        value = self._parse_term()
        while self._peek() in ("+", "-"):
            op = self._toks[self._pos]
            self._pos += 1
            value = self._binop(value, op, self._parse_term())
        return value

    def _parse_term(self) -> Fraction:  # factor (('*' | '/') factor)*
        value = self._parse_factor()
        while self._peek() in ("*", "/"):
            op = self._toks[self._pos]
            self._pos += 1
            value = self._binop(value, op, self._parse_factor())
        return value

    def _parse_factor(self) -> Fraction:  # NUMBER | '(' expr ')' | ('-'|'+') factor
        t = self._peek()
        if t is None:
            raise ValueError("unexpected end of expression")
        if t == "-":
            self._pos += 1
            return -self._parse_factor()
        if t == "+":
            self._pos += 1
            return self._parse_factor()
        if t == "(":
            self._pos += 1
            value = self._parse_expr()
            if self._peek() != ")":
                raise ValueError("missing closing parenthesis")
            self._pos += 1
            return value
        if t.isdigit():
            self._pos += 1
            return Fraction(int(t))
        raise ValueError(f"unexpected token {t!r}")

    def _binop(self, a: Fraction, op: str, b: Fraction) -> Fraction:
        """Compute ``a op b`` on the substrate; verify exact; return exact.

        The substrate computes the value; an exact-rational host oracle
        (monitoring) verifies it. Anything not confirmed exact is refused
        rather than approximated.
        """
        if op == "/" and b == 0:
            raise ValueError("division by zero")
        result = self._binop_substrate(float(a), float(b), op)
        true = _FOPS[op](a, b)  # exact rational
        if Fraction(result) != true:
            raise ValueError(
                f"{_fmt(a)} {op} {_fmt(b)} is not exactly representable on "
                f"the substrate (~ {result:g}); refusing rather than printing "
                f"an approximation (arbitrary precision: planning/22 Stage 3)"
            )
        return true

    def _binop_substrate(self, a: float, b: float, op: str) -> float:
        """Run one binary op on the substrate, with the OPERATOR SELECTED
        ON THE SUBSTRATE.

        The host injects operands ``a``/``b`` and an operator *code* (not
        a choice of service); ``switch.su`` computes all four operations
        and returns the one the operator code selects via exact Lagrange
        one-hot masks. There is no host ``OPS[op]`` dispatch — which
        operation runs is decided on the substrate.
        """
        vsa = self._service._compiled_module._VSA  # noqa: SLF001
        axon = vsa.axon_add(vsa.zero_vector(), "a", a)
        axon = vsa.axon_add(axon, "b", b)
        axon = vsa.axon_add(axon, "op", CODE[op])
        self._received.clear()
        self._producer.emit("R_switch_in", axon)
        self.init.tick()  # fire the switch service
        self.init.tick()  # fire the sink
        if len(self._received) != 1:
            raise RuntimeError(
                f"calculator delivered {len(self._received)} results (expected 1)"
            )
        return float(vsa.real(self._received[0].payload))  # decode real axis


def main() -> None:  # pragma: no cover - interactive REPL
    import sys

    calc = Calculator()
    print("Yantra calculator — type an expression, e.g. `2 + 3 * 4 =`  (Ctrl-D to quit).")
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            print(calc.evaluate(line))
        except (ValueError, RuntimeError) as exc:
            print(f"error: {exc}")


if __name__ == "__main__":  # pragma: no cover
    main()
