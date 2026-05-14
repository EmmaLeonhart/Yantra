# `bootloader/` — Yantra bare-metal bootloader v0.0

The first Yantra-authored binary that runs on virtualized bare metal
in QEMU. Per `planning/19-boot-sequence.md` § Stage 3, the bootloader
is the first piece of Yantra-authored code that executes — *before
any operating system, before any interpreter, before any standard
library*. It must be compiled native code; Python or any other
interpreted language is a category error here.

## What v0.0 does

- Boots in QEMU as an x86_64 freestanding binary via the `bootloader`
  v0.9 crate (which handles BIOS/UEFI handoff + the long-mode
  transition).
- Prints `Yantra bootloader v0.0 — hello from bare metal` via two
  channels:
  - VGA text-mode buffer at `0xb8000` (visible in QEMU's gfx window if
    `-display` isn't `none`)
  - QEMU's emulated COM1 serial port at I/O port `0x3F8` (captured by
    `qemu-system-x86_64 -serial stdio` and forwarded to the host
    terminal — the mode `scripts/qemu-run.{sh,bat}` use)
- Halts with `cli; hlt` after the print. Nothing else.

## What v0.0 does NOT do

These are real bootloader work, deferred:

- **No GPU init.** Discovering + initialising the GPU is real
  bootloader responsibility per the boot-sequence plan (Stage 3
  step 1: "Discover the GPU. Probe PCI, identify the device, verify
  it's a Yantra-supported model."). v0.0 doesn't touch the GPU.
- **No kernel image load.** The Sutra-compiled kernel isn't loaded
  onto a virtual GPU yet. That needs both the GPU init above and a
  defined kernel-image format. v0.1+.
- **No orchestrator handoff.** Stage 4 of the boot sequence (the Rust
  orchestrator that becomes the standing CPU-side companion to the
  GPU) isn't reached. v0.0 just halts.

What v0.0 IS: end-to-end demonstration that a Yantra-authored binary
can boot under QEMU, talk to virtualized hardware (UART + VGA), and
run on bare metal with no OS underneath. Smallest possible v0 of the
tier-3 milestone.

## Prerequisites

### Rust toolchain

The `rust-toolchain.toml` pins to a specific nightly Rust version
(bootloader v0.9 + `build-std` need nightly Rust + `rust-src`).
Rustup auto-installs the pinned version when you `cd bootloader/`.

If you don't have rustup yet: <https://rustup.rs/>.

### bootimage build tool (one-time)

```bash
cargo install bootimage
rustup component add llvm-tools-preview
```

`scripts/qemu-build.{sh,bat}` checks for `bootimage` and installs it
if missing.

### QEMU

| OS | Install |
|---|---|
| Windows | `winget install SoftwareFreedomConservancy.QEMU` |
| Debian / Ubuntu | `sudo apt install qemu-system-x86` |
| Arch | `sudo pacman -S qemu-full` |
| macOS (Homebrew) | `brew install qemu` |

After install, `qemu-system-x86_64 --version` should print a version
string. On Windows it might land at `C:\Program Files\qemu\` — the
`scripts/qemu-run.bat` wrapper checks that location if `qemu-system-
x86_64` isn't on PATH.

## Build + run

```bash
# From repo root:
./scripts/qemu-build.sh    # produces bootimage-yantra-bootloader.bin
./scripts/qemu-run.sh      # boots it in QEMU; prints to stdout

# Windows:
scripts\qemu-build.bat
scripts\qemu-run.bat
```

Expected output (after a few seconds of boot delay):

```
>>> Booting Yantra bootloader in QEMU. Ctrl+A then X to exit.
Yantra bootloader v0.0 - hello from bare metal
```

Then QEMU stays open with the VM halted — exit with `Ctrl+A`, then
`X`.

## Files

| File | What |
|---|---|
| `Cargo.toml` | Crate manifest. `bootloader = "0.9.x"` is the Phil-Opp-style boot setup. |
| `src/main.rs` | The kernel itself. `entry_point!(kernel_main)` macro from the bootloader crate sets up the entry. |
| `.cargo/config.toml` | Cargo config: target = `x86_64-unknown-none` (built-in tier-2 bare-metal target since Rust 1.62); `build-std` rebuilds `core` + `compiler_builtins` for it. |
| `rust-toolchain.toml` | Pin to the nightly Rust the bootloader crate + `build-std` need. |

## Cross-references

- `planning/19-boot-sequence.md` — full stage-by-stage flow.
- `planning/01-architecture.md` § "CPU side: small, Rust, orchestrator" — why Rust.
- `kernel/README.md` — the Python prototype of the orchestrator that runs *after* this bootloader hands off (in v0.1+).
- `paper/paper.md` § 3.5 — hardware boundary (interrupts, MMIO) that the production bootloader has to handle.
