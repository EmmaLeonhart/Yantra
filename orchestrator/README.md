# orchestrator — Yantra CPU-side Connectome Manager (Rust)

The incremental Rust port of the orchestrator. The behavioural reference is
the Python `kernel/` package; this crate grows as small, independently
`cargo test`-verified units that each match a slice of that API and compose
toward a freestanding (bare-metal) image over time — the build strategy in
`planning/01-architecture.md` § "CPU side: small, Rust, orchestrator".

`#![cfg_attr(not(test), no_std)]`: `no_std` for real builds (the orchestrator
is bare-metal-bound, like `bootloader/`), with `std` pulled in only for the
test harness so every unit stays host-testable.

## Units

- **`axon`** — the axon wire codecs, byte-for-byte compatible with Python
  `kernel/serialise.py`:
  - `YAXN` payload: `parse_axon_payload` / `write_axon_payload`.
  - `YAXE` envelope (role + from_proc + keys + nested YAXN payload):
    `parse_axon_envelope` / `write_axon_envelope`.

  The tests embed the exact bytes the Python encoder emits and assert both
  decode and byte-for-byte encode match. This is the orchestrator's read/write
  path for checkpointed axon values (see `kernel/checkpoint.py`,
  `planning/26-orchestrator-serialisation.md`).

## Build / test

```bash
cd orchestrator
cargo test            # host, default stable toolchain
```

`bootloader/` pins a nightly for its custom bare-metal target; this crate uses
the default stable toolchain for host testing. The format contract is the
point of the cross-check: if `kernel/serialise.py` changes the wire layout,
the embedded-bytes tests here fail by design.
