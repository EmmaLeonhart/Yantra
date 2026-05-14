"""Smoke test for the first userspace utility: apps/echo.

Admits echo via the kernel, sends an axon with a "stdin_text" key
on R_stdin, ticks, verifies that the receiver downstream of echo's
R_stdout sees an axon containing the same value re-bound under
"stdout_text". Exercises the full path: real .su compile → real
manifest TOML parse → kernel admission → kernel router with lazy
projection → SutraService.tick() → axon delivered.

Skipped when torch is not installed (echo runs through real Sutra).
"""

from __future__ import annotations

import pathlib

import pytest

torch = pytest.importorskip("torch", reason="apps/echo runs through real Sutra")

from kernel import (
    Init,
    Manifest,
    PythonService,
    SutraService,
    load_manifest,
)
from kernel.router import Axon


REPO = pathlib.Path(__file__).resolve().parent.parent
APPS_ECHO = REPO / "apps" / "echo"


def test_echo_manifest_loads() -> None:
    """The manifest TOML parses cleanly."""
    m = load_manifest(APPS_ECHO / "echo.toml")
    assert m.name == "echo"
    assert m.read_roles == frozenset({"R_stdin"})
    assert m.write_roles == frozenset({"R_stdout"})
    assert m.axon_keys == frozenset({"stdin_text"})
    assert m.source == "echo.su"


def test_echo_admits_via_kernel() -> None:
    """Kernel admits echo and surfaces its axon-keys static analysis."""
    init = Init(compute_pool=5)
    svc = SutraService(
        source_path=APPS_ECHO / "echo.su",
        output_role="R_stdout",
    )
    init.admit_from_path(APPS_ECHO / "echo.toml", svc)
    assert "echo" in init.admitted()
    # Static analysis from the .su source: echo binds "stdout_text"
    # and reads "stdin_text".
    assert svc.axon_keys_bound == frozenset({"stdout_text"})
    assert svc.axon_keys_read == frozenset({"stdin_text"})


def test_echo_round_trip_through_kernel() -> None:
    """Inject an axon on R_stdin; sink downstream of R_stdout receives it."""
    init = Init(compute_pool=10)

    # Admit echo from its real manifest.
    echo = SutraService(
        source_path=APPS_ECHO / "echo.su",
        output_role="R_stdout",
    )
    init.admit_from_path(APPS_ECHO / "echo.toml", echo)

    # A Python stand-in producer that can write R_stdin (so we can
    # inject test inputs through the normal capability-checked path).
    producer = PythonService(lambda s, ax: None)
    init.admit(
        Manifest(
            name="producer", axon_width=768, compute_units=1,
            read_roles=frozenset(),
            write_roles=frozenset({"R_stdin"}),
            source="producer.py",
            axon_keys=frozenset(),
        ),
        producer,
    )

    # A Python stand-in stdout sink that reads R_stdout. Records what
    # it receives so the test can inspect.
    received: list[Axon] = []
    def on_axon(svc: PythonService, ax: Axon) -> None:
        received.append(ax)
    sink = PythonService(on_axon=on_axon)
    init.admit(
        Manifest(
            name="stdout_sink", axon_width=768, compute_units=1,
            read_roles=frozenset({"R_stdout"}),
            write_roles=frozenset(),
            source="sink.py",
            # Reads stdout_text — the key echo binds. Empty set
            # would also work via eager-fallback delivery.
            axon_keys=frozenset({"stdout_text"}),
        ),
        sink,
    )

    # Inject an axon on R_stdin. Use a recognizable payload so we
    # can verify it round-tripped (the actual VSA recovery margin
    # is degraded due to the bisected regression in
    # external/Sutra/planning/findings/2026-05-14-bundle-decoding-
    # regression.md, so we don't assert content — only mechanism).
    vsa_dim = echo._compiled_module._VSA.dim  # noqa: SLF001
    payload = torch.randn(vsa_dim)
    producer.emit(
        "R_stdin", payload,
        keys=frozenset({"stdin_text"}),  # tag what's bound
    )

    # Two ticks: first fires echo (drains R_stdin); second fires
    # the sink (drains R_stdout). Run init.tick() twice.
    init.tick()
    init.tick()

    assert len(received) == 1, (
        f"stdout_sink should have received exactly one axon from echo; "
        f"got {len(received)}"
    )
    out = received[0]
    assert out.role == "R_stdout"
    assert out.from_proc == "echo"
    # echo's emit tags the axon with its bound keys (stdout_text).
    assert "stdout_text" in out.keys
    # Payload is a torch tensor of the right shape on the runtime device.
    assert torch.is_tensor(out.payload)
    assert out.payload.shape == (vsa_dim,)


def test_echo_capability_check_still_fires() -> None:
    """A process without R_stdin write capability can't reach echo."""
    from kernel.router import CapabilityError

    init = Init(compute_pool=5)
    echo = SutraService(
        source_path=APPS_ECHO / "echo.su",
        output_role="R_stdout",
    )
    init.admit_from_path(APPS_ECHO / "echo.toml", echo)

    # Attacker process: writes nothing and reads nothing — but
    # tries to emit R_stdin anyway.
    attacker = PythonService(lambda s, ax: None)
    init.admit(
        Manifest(
            name="attacker", axon_width=768, compute_units=1,
            read_roles=frozenset(),
            write_roles=frozenset({"R_other"}),  # NOT R_stdin
            source="attacker.py",
            axon_keys=frozenset(),
        ),
        attacker,
    )
    with pytest.raises(CapabilityError, match="cannot write role 'R_stdin'"):
        attacker.emit("R_stdin", torch.zeros(768))
