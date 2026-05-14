"""End-to-end tests for the v0.0 kernel runtime.

Covers the architecture's load-bearing claims at the v0.0 scope:

  - Manifest parsing rejects bad input cleanly.
  - Init admits processes against a fixed pool budget; refuses
    admission when the pool is exhausted; releases budget on
    deregister.
  - Router enforces capability check on send (sender must hold the
    write role) and on receive (receiver must hold the read role).
  - Multi-process axon routing: echo + sink can be admitted, an axon
    sent into echo's inbox arrives at sink's inbox after one tick.
  - Black-hole sends (no receiver for a role) are dropped, not
    raised — startup-order tolerance.

These tests do NOT exercise the .su loader (stubbed) or real GPU
arena allocation (bookkeeping only). When v0.1 makes those real,
add a test class that runs the same scenarios against
SutraService-backed processes.
"""

from __future__ import annotations

import pathlib

import pytest

from kernel import (
    AdmissionError,
    AxonRouter,
    CapabilityError,
    Init,
    Manifest,
    ManifestError,
    NotAdmittedError,
    PoolExhaustedError,
    PythonService,
    load_manifest,
)
from kernel.router import Axon


def _echo_python(output_role: str = "R_output") -> PythonService:
    """Python stand-in for an echo service (real version uses SutraService)."""
    def on_axon(svc: PythonService, ax: Axon) -> None:
        svc.emit(output_role, ax.payload)
    return PythonService(on_axon=on_axon)


class _CountingSink(PythonService):
    """Python stand-in for a sink that counts axons and emits stats."""

    def __init__(self, *, stat_role: str = "R_stat", report_every: int = 1) -> None:
        self._stat_role = stat_role
        self._report_every = report_every
        self.count = 0
        self._since = 0

        def on_axon(svc: PythonService, ax: Axon) -> None:
            self.count += 1
            self._since += 1
            if self._since >= self._report_every:
                svc.emit(self._stat_role, {"count": self.count})
                self._since = 0

        super().__init__(on_axon=on_axon)


KERNEL_DIR = pathlib.Path(__file__).resolve().parent.parent / "kernel"
MANIFESTS = KERNEL_DIR / "manifests"


# ---- manifest parsing -------------------------------------------------


def _make_manifest(name: str = "p", **overrides) -> Manifest:
    fields = {
        "name": name,
        "axon_width": 768,
        "compute_units": 1,
        "read_roles": frozenset({"R_in"}),
        "write_roles": frozenset({"R_out"}),
        "source": "p.su",
    }
    fields.update(overrides)
    return Manifest(**fields)


def test_load_echo_manifest_real_file() -> None:
    m = load_manifest(MANIFESTS / "echo.toml")
    assert m.name == "echo"
    assert m.axon_width == 768
    assert m.compute_units == 1
    assert m.read_roles == frozenset({"R_input"})
    assert m.write_roles == frozenset({"R_output"})
    assert m.source.endswith("echo.su")


def test_load_sink_manifest_real_file() -> None:
    m = load_manifest(MANIFESTS / "sink.toml")
    assert m.name == "sink"
    assert m.read_roles == frozenset({"R_output"})
    assert m.write_roles == frozenset({"R_stat"})


def test_load_manifest_missing_file(tmp_path: pathlib.Path) -> None:
    with pytest.raises(ManifestError, match="not found"):
        load_manifest(tmp_path / "does-not-exist.toml")


def test_load_manifest_missing_required_field(tmp_path: pathlib.Path) -> None:
    p = tmp_path / "bad.toml"
    p.write_text(
        'name = "x"\naxon_width = 1\ncompute_units = 1\n'
        'read_roles = []\n# missing: write_roles, source\n',
        encoding="utf-8",
    )
    with pytest.raises(ManifestError, match="missing required field"):
        load_manifest(p)


def test_load_manifest_bad_types(tmp_path: pathlib.Path) -> None:
    p = tmp_path / "bad.toml"
    p.write_text(
        'name = "x"\naxon_width = 0\ncompute_units = 1\n'
        'read_roles = []\nwrite_roles = []\nsource = "x.su"\n',
        encoding="utf-8",
    )
    with pytest.raises(ManifestError, match="axon_width must be a positive int"):
        load_manifest(p)


# ---- admission control -----------------------------------------------


def test_admit_decrements_pool() -> None:
    init = Init(compute_pool=5)
    assert init.compute_pool_free == 5

    init.admit(_make_manifest("a", compute_units=2), PythonService(lambda s, ax: None))
    assert init.compute_pool_free == 3
    assert init.admitted() == ["a"]

    init.admit(_make_manifest("b", compute_units=3), PythonService(lambda s, ax: None))
    assert init.compute_pool_free == 0
    assert init.admitted() == ["a", "b"]


def test_admit_refuses_when_pool_exhausted() -> None:
    init = Init(compute_pool=2)
    init.admit(_make_manifest("a", compute_units=2), PythonService(lambda s, ax: None))

    with pytest.raises(PoolExhaustedError, match="needs 1 compute_units"):
        init.admit(_make_manifest("b", compute_units=1), PythonService(lambda s, ax: None))

    # Failed admission must not have changed pool state.
    assert init.compute_pool_free == 0
    assert init.admitted() == ["a"]


def test_admit_refuses_duplicate_name() -> None:
    init = Init(compute_pool=10)
    init.admit(_make_manifest("a"), PythonService(lambda s, ax: None))
    with pytest.raises(AdmissionError, match="already admitted"):
        init.admit(_make_manifest("a"), PythonService(lambda s, ax: None))


def test_deregister_returns_budget() -> None:
    init = Init(compute_pool=5)
    init.admit(_make_manifest("a", compute_units=3), PythonService(lambda s, ax: None))
    assert init.compute_pool_free == 2

    init.deregister("a")
    assert init.compute_pool_free == 5
    assert init.admitted() == []


def test_deregister_unknown_raises() -> None:
    init = Init(compute_pool=5)
    with pytest.raises(AdmissionError, match="not admitted"):
        init.deregister("nope")


def test_init_rejects_zero_pool() -> None:
    with pytest.raises(ValueError, match="compute_pool must be positive"):
        Init(compute_pool=0)


# ---- router capability checks ----------------------------------------


def _admit(init: Init, *, name: str, reads: set[str], writes: set[str], svc: PythonService | None = None) -> PythonService:
    s = svc or PythonService(lambda s, ax: None)
    init.admit(
        _make_manifest(
            name=name,
            read_roles=frozenset(reads),
            write_roles=frozenset(writes),
        ),
        s,
    )
    return s


def test_send_refused_when_sender_lacks_write_role() -> None:
    init = Init(compute_pool=5)
    sender = _admit(init, name="sender", reads=set(), writes={"R_a"})
    _admit(init, name="receiver", reads={"R_b"}, writes=set())

    with pytest.raises(CapabilityError, match="cannot write role 'R_b'"):
        sender.emit("R_b", "payload")


def test_send_to_unadmitted_role_is_black_hole() -> None:
    init = Init(compute_pool=5)
    sender = _admit(init, name="sender", reads=set(), writes={"R_x"})
    # No process has read_roles containing "R_x" — the send is dropped.
    delivered = sender.emit("R_x", "payload")
    assert delivered == 0
    assert init.router.dropped_count() == 1


def test_send_delivers_to_one_receiver() -> None:
    init = Init(compute_pool=5)
    sender = _admit(init, name="sender", reads=set(), writes={"R_x"})
    _admit(init, name="receiver", reads={"R_x"}, writes=set())

    delivered = sender.emit("R_x", "payload")
    assert delivered == 1
    assert init.router.inbox_depth("receiver") == 1


def test_send_fans_out_to_multiple_receivers() -> None:
    init = Init(compute_pool=5)
    sender = _admit(init, name="sender", reads=set(), writes={"R_x"})
    _admit(init, name="r1", reads={"R_x"}, writes=set())
    _admit(init, name="r2", reads={"R_x"}, writes=set())

    delivered = sender.emit("R_x", "payload")
    assert delivered == 2
    assert init.router.inbox_depth("r1") == 1
    assert init.router.inbox_depth("r2") == 1


def test_send_from_unadmitted_process_raises() -> None:
    router = AxonRouter()
    with pytest.raises(NotAdmittedError):
        router.send(Axon(role="R_x", payload=None, from_proc="ghost"))


def test_inbox_depth_unadmitted_raises() -> None:
    router = AxonRouter()
    with pytest.raises(NotAdmittedError):
        router.inbox_depth("ghost")


# ---- multi-process round trip ---------------------------------------


def test_echo_sink_round_trip_with_real_manifests() -> None:
    """Infrastructure round-trip: real manifests, two services, axons routed.

    Uses PythonService stand-ins so this test runs without the Sutra
    runtime cost. The same scenario with real Sutra-compiled services
    is in tests/test_kernel_sutra.py.
    """
    init = Init(compute_pool=4)
    echo = _echo_python(output_role="R_output")
    sink = _CountingSink(stat_role="R_stat", report_every=10_000)

    init.admit_from_path(MANIFESTS / "echo.toml", echo)
    init.admit_from_path(MANIFESTS / "sink.toml", sink)

    # Inject a producer-shaped process that can write R_input. We
    # do this through a third manifest constructed inline so the
    # test doesn't need a real producer.toml shipping.
    producer = PythonService(lambda s, ax: None)
    init.admit(
        _make_manifest(
            name="producer", compute_units=1,
            read_roles=frozenset(),
            write_roles=frozenset({"R_input"}),
        ),
        producer,
    )

    # Send three payloads in. Echo's inbox should fill; sink's
    # should be empty until echo ticks.
    for payload in ("alpha", "beta", "gamma"):
        producer.emit("R_input", payload)
    assert init.router.inbox_depth("echo") == 3
    assert init.router.inbox_depth("sink") == 0

    # One tick: echo drains its inbox, re-emits each on R_output;
    # the router delivers each to sink. Sink's tick then drains.
    counts = init.tick()
    assert counts == {"producer": 0, "echo": 3, "sink": 3}
    assert sink.count == 3
    assert init.router.inbox_depth("echo") == 0
    assert init.router.inbox_depth("sink") == 0


def test_sink_stat_emit_is_black_hole_no_logger() -> None:
    """Sink emits R_stat every report_every ticks; no logger ⇒ dropped."""
    init = Init(compute_pool=3)
    echo = _echo_python()
    sink = _CountingSink(stat_role="R_stat", report_every=2)
    init.admit_from_path(MANIFESTS / "echo.toml", echo)
    init.admit_from_path(MANIFESTS / "sink.toml", sink)
    producer = PythonService(lambda s, ax: None)
    init.admit(
        _make_manifest(
            name="producer", compute_units=1,
            read_roles=frozenset(),
            write_roles=frozenset({"R_input"}),
        ),
        producer,
    )

    for _ in range(4):
        producer.emit("R_input", "x")
    init.tick()  # echo drains 4 → emits 4 to sink → sink drains 4
    # Sink emits R_stat every 2 absorbs ⇒ 2 emissions to a non-existent
    # logger ⇒ dropped audit count goes up by 2.
    assert init.router.dropped_count() == 2
    assert sink.count == 4
