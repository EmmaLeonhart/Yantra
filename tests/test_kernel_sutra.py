"""End-to-end test: real Sutra-compiled .su services through the router.

This is the test that proves Sutra is actually doing the computation
— not a Python stub re-using the same data structures. Two .su files
in `kernel/services/` are compiled by the real Sutra v0.3.1 compiler
(via the submodule under `external/Sutra/sdk/sutra-compiler/`) and
their `on_axon(vector) -> vector` exports are wired to the kernel's
axon router. A real torch tensor is sent in; the router delivers it
through the chain; the receiver gets a real torch tensor back.

Skipped when torch is not installed, so CI lanes that don't carry
the full Sutra runtime stack still pass cleanly. Local dev with
torch installed (which Sutra requires anyway) gets the real test.
"""

from __future__ import annotations

import pathlib

import pytest

torch = pytest.importorskip("torch", reason="Sutra services need torch")

from kernel import Init, Manifest, PythonService, SutraService


KERNEL_DIR = pathlib.Path(__file__).resolve().parent.parent / "kernel"
SERVICES = KERNEL_DIR / "services"

# These tests compile real .su programs through the Sutra v0.3.1
# pipeline. First compile in a fresh interpreter downloads the
# embedding model (`nomic-embed-text` by default), which is slow
# (~tens of seconds to minutes on cold cache). All tests in this
# module share that cost via session-scoped fixtures.

AXON_WIDTH = 768  # matches nomic-embed-text default


@pytest.fixture(scope="module")
def echo_sink_init() -> Init:
    """Init with two real Sutra services (echo, sink) + a producer."""
    init = Init(compute_pool=10)

    echo = SutraService(
        source_path=SERVICES / "echo.su",
        output_role="R_output",
    )
    init.admit(
        Manifest(
            name="echo", axon_width=AXON_WIDTH, compute_units=1,
            read_roles=frozenset({"R_input"}),
            write_roles=frozenset({"R_output"}),
            source="services/echo.su",
        ),
        echo,
    )

    sink = SutraService(
        source_path=SERVICES / "sink.su",
        output_role="R_stat",
    )
    init.admit(
        Manifest(
            name="sink", axon_width=AXON_WIDTH, compute_units=1,
            read_roles=frozenset({"R_output"}),
            write_roles=frozenset({"R_stat"}),
            source="services/sink.su",
        ),
        sink,
    )

    producer = PythonService(lambda s, ax: None)
    init.admit(
        Manifest(
            name="producer", axon_width=AXON_WIDTH, compute_units=1,
            read_roles=frozenset(),
            write_roles=frozenset({"R_input"}),
            source="producer.py",
        ),
        producer,
    )
    return init


def _producer(init: Init) -> PythonService:
    """Look up the producer by name."""
    # The Init API exposes admitted names but not the bound services
    # directly; for the test we know the producer is a PythonService
    # we admitted by hand. Get it via the table.
    return init._table["producer"].service  # noqa: SLF001 — test


def test_real_sutra_services_compile_and_admit(echo_sink_init: Init) -> None:
    """Both Sutra services compiled cleanly and joined the connectome."""
    assert sorted(echo_sink_init.admitted()) == ["echo", "producer", "sink"]
    # Compute pool decremented by 3 * 1 = 3.
    assert echo_sink_init.compute_pool_free == 10 - 3


def test_real_sutra_round_trip_with_torch_tensor(echo_sink_init: Init) -> None:
    """A real torch tensor routes producer → echo (real Sutra) → sink (real Sutra)."""
    payload = torch.randn(AXON_WIDTH)
    expected_norm = payload.norm().item()

    producer = _producer(echo_sink_init)
    delivered = producer.emit("R_input", payload)
    assert delivered == 1, "producer's R_input should route to echo only"
    assert echo_sink_init.router.inbox_depth("echo") == 1
    assert echo_sink_init.router.inbox_depth("sink") == 0

    counts = echo_sink_init.tick()
    # Producer has nothing inbound; echo drains 1; sink drains the 1
    # that echo emitted.
    assert counts["producer"] == 0
    assert counts["echo"] == 1
    assert counts["sink"] == 1

    # Sink's R_stat emit goes to a black hole (no reader admitted)
    # — the dropped count goes up by exactly 1.
    assert echo_sink_init.router.dropped_count() == 1


def test_real_sutra_output_is_torch_tensor(echo_sink_init: Init) -> None:
    """The vector that lands in sink's inbox came back from real Sutra compute."""
    # We need to inspect what arrives at sink BEFORE sink's tick drains
    # it, so do this in two halves.
    payload = torch.ones(AXON_WIDTH) * 0.5
    producer = _producer(echo_sink_init)
    producer.emit("R_input", payload)

    # Tick echo manually so we can peek at sink's inbox before sink ticks.
    echo_svc = echo_sink_init._table["echo"].service  # noqa: SLF001
    echo_svc.tick()

    inbound_to_sink = echo_sink_init.router.receive("sink")
    assert inbound_to_sink is not None
    assert inbound_to_sink.from_proc == "echo"
    assert inbound_to_sink.role == "R_output"
    assert torch.is_tensor(inbound_to_sink.payload), (
        "sink received a real torch tensor; the .su compute path produced it"
    )
    assert inbound_to_sink.payload.shape == (AXON_WIDTH,)


def test_real_sutra_capability_check_still_fires(echo_sink_init: Init) -> None:
    """The router still refuses sends from Sutra services on roles they don't hold."""
    from kernel.router import CapabilityError
    echo_svc = echo_sink_init._table["echo"].service  # noqa: SLF001
    with pytest.raises(CapabilityError, match="cannot write role 'R_stat'"):
        echo_svc.emit("R_stat", torch.zeros(AXON_WIDTH))


def test_sutra_service_unbound_tick_raises() -> None:
    """A SutraService not yet admitted to an Init can't tick — clear error."""
    svc = SutraService(
        source_path=SERVICES / "echo.su",
        output_role="R_output",
    )
    with pytest.raises(RuntimeError, match="not bound"):
        svc.tick()


def test_sutra_service_missing_entry_point_raises(tmp_path: pathlib.Path) -> None:
    """A .su without the expected entry-point function fails at admit time."""
    bad = tmp_path / "no_entry.su"
    bad.write_text(
        "function string main() { return \"nope\"; }\n",
        encoding="utf-8",
    )

    init = Init(compute_pool=5)
    svc = SutraService(source_path=bad, output_role="R_x")
    with pytest.raises(AttributeError, match="no `on_axon` symbol"):
        init.admit(
            Manifest(
                name="bad", axon_width=AXON_WIDTH, compute_units=1,
                read_roles=frozenset({"R_in"}),
                write_roles=frozenset({"R_x"}),
                source=str(bad),
            ),
            svc,
        )


# ---- lazy axon evaluation: compiler-emitted constants drive routing -


def test_sutra_service_exposes_axon_keys_from_compiled_module(tmp_path: pathlib.Path) -> None:
    """The Sutra v0.3.3+ AXON_KEYS_BOUND/READ constants surface as service properties."""
    # A .su that both binds and reads — exercise both halves of the static analysis.
    src = tmp_path / "mixed.su"
    src.write_text(
        "function vector on_axon(vector input_axon) {\n"
        "    Axon a;\n"
        "    a.add(\"out_key\", input_axon);\n"
        "    return axon_item(a, \"out_key\");\n"
        "}\n",
        encoding="utf-8",
    )

    init = Init(compute_pool=5)
    svc = SutraService(source_path=src, output_role="R_out")
    init.admit(
        Manifest(
            name="mixed", axon_width=AXON_WIDTH, compute_units=1,
            read_roles=frozenset({"R_in"}),
            write_roles=frozenset({"R_out"}),
            source=str(src),
        ),
        svc,
    )
    assert svc.axon_keys_bound == frozenset({"out_key"})
    assert svc.axon_keys_read == frozenset({"out_key"})


def test_sutra_service_auto_populates_manifest_axon_keys(tmp_path: pathlib.Path) -> None:
    """When manifest doesn't declare axon_keys, SutraService fills it from the .su."""
    consumer = tmp_path / "consumer.su"
    consumer.write_text(
        "function vector on_axon(vector input_axon) {\n"
        "    return axon_item(input_axon, \"animal_2\");\n"
        "}\n",
        encoding="utf-8",
    )

    init = Init(compute_pool=5)
    svc = SutraService(source_path=consumer, output_role="R_out")
    init.admit(
        Manifest(
            name="consumer", axon_width=AXON_WIDTH, compute_units=1,
            read_roles=frozenset({"R_in"}),
            write_roles=frozenset({"R_out"}),
            source=str(consumer),
            # axon_keys NOT declared — service should auto-populate.
        ),
        svc,
    )
    # The router's view of the receiver's axon_keys should now reflect
    # what the .su source statically reads.
    receiver_manifest = init._table["consumer"].manifest  # noqa: SLF001
    assert receiver_manifest.axon_keys == frozenset({"animal_2"})


def test_sutra_service_respects_explicit_manifest_axon_keys(tmp_path: pathlib.Path) -> None:
    """If the manifest DID declare axon_keys, don't overwrite — explicit wins."""
    src = tmp_path / "consumer.su"
    src.write_text(
        "function vector on_axon(vector input_axon) {\n"
        "    return axon_item(input_axon, \"static_key\");\n"
        "}\n",
        encoding="utf-8",
    )
    init = Init(compute_pool=5)
    svc = SutraService(source_path=src, output_role="R_out")
    init.admit(
        Manifest(
            name="explicit", axon_width=AXON_WIDTH, compute_units=1,
            read_roles=frozenset({"R_in"}),
            write_roles=frozenset({"R_out"}),
            source=str(src),
            axon_keys=frozenset({"override_key"}),  # explicit wins
        ),
        svc,
    )
    receiver_manifest = init._table["explicit"].manifest  # noqa: SLF001
    assert receiver_manifest.axon_keys == frozenset({"override_key"})


def test_sutra_service_emit_tags_axon_with_bound_keys(tmp_path: pathlib.Path) -> None:
    """SutraService.tick() forwards AXON_KEYS_BOUND to router.send()'s keys field.

    With Sutra v0.3.4's device-coherence fix in axon_add/bind, the
    .su body can now construct a real Axon from a CPU input tensor
    without crashing. That's the natural shape of a producer
    service: take an input, bind some keys onto it, emit. This
    test exercises that natural shape end-to-end.
    """
    producer = tmp_path / "producer.su"
    producer.write_text(
        "function vector on_axon(vector input_axon) {\n"
        "    Axon a;\n"
        "    a.add(\"key_one\", input_axon);\n"
        "    a.add(\"key_two\", input_axon);\n"
        "    return a;\n"
        "}\n",
        encoding="utf-8",
    )
    init = Init(compute_pool=5)
    prod_svc = SutraService(source_path=producer, output_role="R_out")
    init.admit(
        Manifest(
            name="prod", axon_width=AXON_WIDTH, compute_units=1,
            read_roles=frozenset({"R_in"}),
            write_roles=frozenset({"R_out"}),
            source=str(producer),
        ),
        prod_svc,
    )
    # Sanity: static analysis picked up both bind keys.
    assert prod_svc.axon_keys_bound == frozenset({"key_one", "key_two"})

    # Receiver that wants only "key_one" — producer's emission should
    # still arrive (intersection non-empty), and its keys field
    # should reflect what the producer's source statically binds.
    receiver_consumer = tmp_path / "rcv.su"
    receiver_consumer.write_text(
        "function vector on_axon(vector input_axon) {\n"
        "    return input_axon;\n"
        "}\n",
        encoding="utf-8",
    )
    receiver = SutraService(source_path=receiver_consumer, output_role="R_done")
    init.admit(
        Manifest(
            name="recv", axon_width=AXON_WIDTH, compute_units=1,
            read_roles=frozenset({"R_out"}),
            write_roles=frozenset({"R_done"}),
            source=str(receiver_consumer),
            axon_keys=frozenset({"key_one"}),
        ),
        receiver,
    )

    # Inject an axon on the producer's R_in. CPU tensor — Sutra
    # v0.3.4's device-coherence fix in axon_add/bind handles the
    # CPU→runtime-device coercion now, so we don't need to
    # pre-pin the device on the test side.
    vsa_dim = prod_svc._compiled_module._VSA.dim  # noqa: SLF001
    init.router._inboxes["prod"].append(  # noqa: SLF001 — test
        Axon(
            role="R_in",
            payload=torch.zeros(vsa_dim),  # CPU — Sutra coerces
            from_proc="prod",
        ),
    )
    prod_svc.tick()  # runs on_axon (real Axon construction!) → emits
    inbox = init.router.receive("recv")
    assert inbox is not None
    # The emitted axon's keys field should be the producer's
    # statically-collected bound keys.
    assert inbox.keys == frozenset({"key_one", "key_two"})
    # Intersection {"key_one"} is non-empty → no lazy-skip.
    assert init.router.lazy_skipped_count() == 0


# Need Axon at module scope for the previous test.
from kernel.router import Axon  # noqa: E402
