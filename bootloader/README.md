# `bootloader/` — Yantra bare-metal kernel v0.1

The first Yantra-authored binary that runs on virtualized bare metal
in QEMU. Per `planning/19-boot-sequence.md` § Stage 3, this is the
first piece of code that executes — *before any operating system,
before any interpreter, before any standard library*. Necessarily
compiled native code; Python or any other interpreted language is a
category error here.

**Status: v0.1 VERIFIED WORKING in QEMU 11.0.50** on Windows (2026-05-14).

Demonstrated end-to-end:

1. Boots via multiboot1 ELF + QEMU's `-kernel` flag.
2. Prints the banner via COM1 serial.
3. **PCI scan**: enumerates the PCI bus and prints all present
   devices. In QEMU's default machine, sees the Intel 440FX
   north bridge, PIIX3/4 south bridges, IDE controller, **GPU
   (class 0x03 display, vendor 1234 device 1111 — QEMU's VGA)**,
   and e1000 NIC.
4. **Long-mode transition**: builds identity-mapped page tables
   (PML4 + PDP with 512 huge 2-MiB pages covering 1 GiB), enables
   PAE, sets EFER.LME, enables paging in CR0, far-jumps to a
   64-bit code segment from a hand-rolled GDT.
5. Prints "Long mode active" from pure 64-bit assembly.
6. Halts.

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

## What v0.1 does NOT do (deferred to v0.2+)

- **GPU init.** v0.1 *enumerates* the GPU (we see class 0x03 in
  the scan output) but doesn't program it. Selecting + initing a
  specific GPU is real driver work for v0.2+.
- **64-bit Rust execution.** The Rust kernel target stays i686
  (32-bit). After the long-mode jump we execute pure 64-bit asm
  for the hello-print. Switching the Rust target to
  `x86_64-unknown-none` + multiboot2 (which supports 64-bit ELFs
  directly) is the v0.2 migration. Until then, "do real work in
  64-bit" means more asm or a separately-compiled 64-bit module.
- **Kernel image load.** The Sutra-compiled kernel isn't loaded
  onto a virtual GPU yet. v0.3+.
- **Orchestrator handoff.** Stage 4 of the boot sequence (the
  Rust orchestrator that becomes the standing CPU-side companion
  to the GPU) isn't reached. v0.4+.

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
Yantra bootloader v0.1 - hello from bare metal
-- PCI scan --
  00:00.0 vendor=8086 device=1237 class=06 (bridge) subclass=00
  00:01.0 vendor=8086 device=7000 class=06 (bridge) subclass=01
  00:01.1 vendor=8086 device=7010 class=01 (mass-storage) subclass=01
  00:01.3 vendor=8086 device=7113 class=06 (bridge) subclass=80
  00:02.0 vendor=1234 device=1111 class=03 (display) subclass=00
  00:03.0 vendor=8086 device=100e class=02 (network) subclass=00
-- end PCI scan --
Long mode active
```

Then QEMU stays open with the VM halted — exit with `Ctrl+A`, then
`X`.

## Files

| File | What |
|---|---|
| `Cargo.toml` | Crate manifest. No third-party deps — pure no_std + inline asm. |
| `src/main.rs` | Multiboot1 header static; `_start` + long-mode transition + 64-bit hello-print in `global_asm!`; `kernel_main` in 32-bit Rust (writes banner, runs PCI scan, returns into the long-mode asm tail). |
| `src/pci.rs` | PCI config-space access via I/O ports `0xCF8` / `0xCFC`. Enumerates all (bus, dev, func) combos; calls back per present device. |
| `linker.ld` | Linker script. Puts `.multiboot` first (multiboot1 needs it in the first 8KB), loads at 1MB physical (where QEMU's `-kernel` puts multiboot binaries). |
| `i686-yantra.json` | Custom target spec — bare-metal i686, no OS, no SSE. |
| `.cargo/config.toml` | Cargo config: target = our JSON; `build-std` rebuilds core for the bare target; `-Tlinker.ld` linker arg. |
| `rust-toolchain.toml` | Pin to nightly Rust (build-std + JSON target spec need it). |

## Cross-references

- `planning/19-boot-sequence.md` — full stage-by-stage flow.
- `planning/01-architecture.md` § "CPU side: small, Rust, orchestrator" — why Rust.
- `kernel/README.md` — the Python prototype of the orchestrator that runs *after* this bootloader hands off (in v0.1+).
- `paper/paper.md` § 3.5 — hardware boundary (interrupts, MMIO) that the production bootloader has to handle.
