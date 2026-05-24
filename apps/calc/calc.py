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
**host orchestration** (the CPU side's job); the ``+ - *`` services are
real ``.su`` programs the kernel admits and runs on the substrate.

Exact for integer operands and results within the float32 exact-integer
range (|value| < 2**24). Bigger values need an arbitrary-precision
digit encoding (planning/22 Stage 3). Division is omitted on purpose —
Sutra has no runtime real/complex division yet (docs/numeric-math.md
"Pending"), so a ``/`` expression errors rather than printing a guess.
"""
from __future__ import annotations

import pathlib
import re
import sys

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

# operator symbol -> service name (matching the .su files).
OPS = {"+": "add", "-": "sub", "*": "mul"}
# Parse ``a op b`` with an optional trailing ``=``. We accept ``/`` in
# the grammar only so we can give a clear "unsupported" error instead
# of a parse error.
_EXPR = re.compile(r"^\s*(-?\d+)\s*([-+*/])\s*(-?\d+)\s*=?\s*$")


class Calculator:
    """A CLI calculator whose arithmetic runs on the Sutra substrate.

    Construct once (compiles the three op services), then call
    :meth:`evaluate` per expression.
    """

    def __init__(self) -> None:
        self.init = Init(compute_pool=32)
        self.services: dict[str, SutraService] = {}
        in_roles: set[str] = set()
        out_roles: set[str] = set()
        for name in OPS.values():
            svc = SutraService(
                source_path=APPS_CALC / f"{name}.su",
                output_role=f"R_{name}_out",
            )
            self.init.admit(
                Manifest(
                    name=name, axon_width=AXON_WIDTH, compute_units=1,
                    read_roles=frozenset({f"R_{name}_in"}),
                    write_roles=frozenset({f"R_{name}_out"}),
                    source=f"{name}.su",
                ),
                svc,
            )
            self.services[name] = svc
            in_roles.add(f"R_{name}_in")
            out_roles.add(f"R_{name}_out")

        # One host producer that can inject on any op's input role, and
        # one host sink that reads every op's output role. The math
        # still happens inside the .su services; these are just the
        # orchestrator's I/O endpoints.
        self._producer = PythonService(lambda s, ax: None)
        self.init.admit(
            Manifest(
                name="calc_in", axon_width=AXON_WIDTH, compute_units=1,
                read_roles=frozenset(), write_roles=frozenset(in_roles),
                source="calc_in.py",
            ),
            self._producer,
        )
        self._received: list[Axon] = []
        sink = PythonService(on_axon=lambda s, ax: self._received.append(ax))
        self.init.admit(
            Manifest(
                name="calc_out", axon_width=AXON_WIDTH, compute_units=1,
                read_roles=frozenset(out_roles), write_roles=frozenset(),
                source="calc_out.py",
            ),
            sink,
        )

    def evaluate(self, line: str) -> int:
        """Parse ``a op b`` (optional trailing ``=``); compute on substrate.

        Returns the integer result. Raises ``ValueError`` on an
        unparseable expression or an unsupported operator.
        """
        m = _EXPR.match(line)
        if not m:
            raise ValueError(f"cannot parse expression: {line!r}")
        a, op, b = int(m.group(1)), m.group(2), int(m.group(3))
        if op not in OPS:
            raise ValueError(
                f"operator {op!r} is not supported — Sutra has no runtime "
                f"division op yet (docs/numeric-math.md)"
            )
        name = OPS[op]
        vsa = self.services[name]._compiled_module._VSA  # noqa: SLF001
        # Encode the operands into a two-key axon on the substrate.
        axon = vsa.axon_add(vsa.zero_vector(), "a", float(a))
        axon = vsa.axon_add(axon, "b", float(b))

        self._received.clear()
        self._producer.emit(f"R_{name}_in", axon)
        # Two ticks: one fires the op service, one fires the sink.
        self.init.tick()
        self.init.tick()
        if len(self._received) != 1:
            raise RuntimeError(
                f"calculator delivered {len(self._received)} results for "
                f"{line!r} (expected 1)"
            )
        result = float(vsa.real(self._received[0].payload))  # decode real axis
        return int(round(result))


def main() -> None:  # pragma: no cover - interactive REPL
    import sys

    calc = Calculator()
    print("Yantra calculator — type e.g. `5 * 10 =`  (Ctrl-D to quit).")
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
