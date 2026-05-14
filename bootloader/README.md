# `bootloader/` — Yantra bare-metal kernel v0.0

The first Yantra-authored binary that runs on virtualized bare metal
in QEMU. Per `planning/19-boot-sequence.md` § Stage 3, this is the
first piece of code that executes — *before any operating system,
before any interpreter, before any standard library*. Necessarily
compiled native code; Python or any other interpreted language is a
category error here.

**Status: VERIFIED WORKING in QEMU 11.0.50** on Windows (2026-05-14).
The boot prints "Yantra bootloader v0.0 — hello from bare metal" via
COM1 serial; QEMU's `-serial stdio` forwards it to the host terminal.

## Architecture

- 32-bit i686 ELF binary with a multiboot1 header in `.multiboot`
  section (first 8KB of the image, per multiboot1 spec).
- QEMU's `-kernel` flag boots multiboot1 ELFs directly — no disk
  image, no BIOS boot sector, no third-party bootloader crate.
  Multiboot1 hands off in 32-bit protected mode.
- `_start` (in `global_asm!`) sets ESP to a known stack top, then
  calls into Rust `kernel_main`.
- `kernel_main` writes to COM1 (I/O port 0x3F8), then halts in
  `cli; hlt`.

The earlier v0.0.1 attempt used the `bootloader = "0.9.x"` crate +
disk-image boot. That crate triple-faults at boot under Rust 1.96
nightly. Multiboot1 has zero version-skew surface — the spec is
fixed (1995), QEMU's loader has been stable since the early 2000s,
and the only Rust feature beyond `no_std` is inline `asm!` (stable
since 1.59).

## What v0.0 does NOT do

These are real bootloader work, deferred to v0.1+:

- **No GPU init.** Discovering + initing the GPU is real bootloader
  responsibility per the boot-sequence plan. v0.0 doesn't touch the
  GPU.
- **No long-mode (64-bit) transition.** v0.0 stays in 32-bit
  protected mode. 64-bit Sutra runtime needs a long-mode jump.
- **No kernel image load.** The Sutra-compiled kernel isn't loaded
  onto a virtual GPU yet.
- **No orchestrator handoff.** Stage 4 of the boot sequence (the
  Rust orchestrator that becomes the standing CPU-side companion to
  the GPU) isn't reached. v0.0 just halts.

## Prerequisites

### Rust toolchain

The `rust-toolchain.toml` pins to nightly Rust (need `build-std`
+ JSON target spec). Rustup auto-installs the pinned version when
you `cd bootloader/`.

If you don't have rustup yet: <https://rustup.rs/>.

### QEMU

| OS | Install |
|---|---|
| Windows | `winget install SoftwareFreedomConservancy.QEMU` |
| Debian / Ubuntu | `sudo apt install qemu-system-x86` |
| Arch | `sudo pacman -S qemu-full` |
| macOS (Homebrew) | `brew install qemu` |

After install, `qemu-system-x86_64 --version` should print a version
string. On Windows it lands at `C:\Program Files\qemu\` — the
`scripts/qemu-run.{sh,bat}` wrappers check that location if QEMU
isn't on PATH.

## Build + run

```bash
# From repo root:
./scripts/qemu-build.sh    # produces bootloader/target/i686-yantra/release/yantra-bootloader
./scripts/qemu-run.sh      # boots it in QEMU; prints to stdout

# Windows:
scripts\qemu-build.bat
scripts\qemu-run.bat
```

Expected output (after a few seconds of boot delay):

```
>>> Booting Yantra kernel in QEMU. Ctrl+A then X to exit.
Yantra bootloader v0.0 - hello from bare metal
```

Then QEMU stays open with the VM halted — exit with `Ctrl+A`, then
`X`.

## Files

| File | What |
|---|---|
| `Cargo.toml` | Crate manifest. No third-party deps — pure no_std + inline asm. |
| `src/main.rs` | Multiboot1 header static, `_start` in `global_asm!` (sets stack), `kernel_main` in Rust (writes to serial, halts). |
| `linker.ld` | Linker script. Puts `.multiboot` first (multiboot1 needs it in the first 8KB), loads at 1MB physical (where QEMU's `-kernel` puts multiboot binaries). |
| `i686-yantra.json` | Custom target spec — bare-metal i686, no OS, no SSE. |
| `.cargo/config.toml` | Cargo config: target = our JSON; `build-std` rebuilds core for the bare target; `-Tlinker.ld` linker arg. |
| `rust-toolchain.toml` | Pin to nightly Rust (build-std + JSON target spec need it). |

## Cross-references

- `planning/19-boot-sequence.md` — full stage-by-stage flow.
- `planning/01-architecture.md` § "CPU side: small, Rust, orchestrator" — why Rust.
- `kernel/README.md` — the Python prototype of the orchestrator that runs *after* this bootloader hands off (in v0.1+).
- `paper/paper.md` § 3.5 — hardware boundary (interrupts, MMIO) that the production bootloader has to handle.
