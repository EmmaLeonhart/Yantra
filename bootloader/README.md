# `bootloader/` — Yantra bare-metal kernel v0.4

The first Yantra-authored binary that runs on virtualized bare metal
in QEMU. Per `planning/19-boot-sequence.md` § Stage 3, this is the
first piece of code that executes — *before any operating system,
before any interpreter, before any standard library*. Necessarily
compiled native code; Python or any other interpreted language is a
category error here.

**Status: v0.4 VERIFIED WORKING in QEMU 11.0.50** on Windows (2026-05-14).

Demonstrated end-to-end:

1. Boots via multiboot1 ELF + QEMU's `-kernel` flag.
2. Prints the banner via COM1 serial.
3. **PCI scan**: enumerates the PCI bus and prints all present
   devices. In QEMU's default machine, sees the Intel 440FX
   north bridge, PIIX3/4 south bridges, IDE controller, **GPU
   (class 0x03 display, vendor 1234 device 1111 — QEMU's VGA)**,
   and e1000 NIC.
4. **GPU init (framebuffer)**: reads the GPU's BAR0 from PCI
   config space (0xfd000000 under QEMU's default), writes a
   100x640 BGRA-pixel gradient directly to the linear
   framebuffer. Reads back the first pixel to verify the write.
5. **Kernel image load**: copies a kernel-image placeholder
   (61 bytes, sentinel "YANTRA_KERNEL_IMAGE_PLACEHOLDER...") to a
   designated region of GPU memory (framebuffer + 1 MiB).
   Reads back to confirm. **Real Sutra kernel execution requires
   actual GPU passthrough (Linux + spare GPU + VFIO config) —
   v0.4 demonstrates the *handoff mechanism*, not the *runtime*.**
6. **Orchestrator handoff**: stub orchestrator prints proof-of-life
   (the real Rust orchestrator's tick loop is what runs here once
   we have a GPU compute target).
7. **Long-mode transition**: builds identity-mapped page tables
   (PML4 + PDP with 512 huge 2-MiB pages covering 1 GiB), enables
   PAE, sets EFER.LME, enables paging in CR0, far-jumps to a
   64-bit code segment from a hand-rolled GDT.
8. Prints "Long mode active" from pure 64-bit assembly.
9. Halts.

## Attempted but deferred: v0.2 (real Rust in long mode)

Tried switching the Rust target to `x86_64-unknown-none` so we
could run real Rust in 64-bit mode. **Blocked**: QEMU's `-kernel`
flag refuses 64-bit ELFs (`Cannot load x86-64 image, give a
32bit one`). Multiboot2 (which supports 64-bit) is not directly
loadable via `-kernel` — needs GRUB to boot. Two paths forward:
(a) build a GRUB ISO + load via `-cdrom`, (b) split into two
crates: i686 boot stub + x86_64 payload. Both real follow-up
work. Until then, the kernel stays i686 + Rust runs in 32-bit
mode, with the long-mode tail being pure 64-bit asm.

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

## What v0.4 does NOT do (deferred to v0.5+)

- **Real Sutra kernel execution.** The biggest gap. Sutra
  programs compile to PyTorch modules requiring CUDA; they can't
  run on QEMU's emulated stdvga. v0.4's "kernel image" is a
  sentinel placeholder. Real Sutra-on-GPU needs **actual GPU
  passthrough** (VFIO on a Linux host with a spare GPU). The
  bootloader's handoff mechanism is in place; the runtime is
  gated on hardware we don't have at the QEMU dev tier.
- **Production Rust orchestrator.** The v0.4 orchestrator is a
  stub printing proof-of-life. The real Rust orchestrator
  (`planning/01-architecture.md` § "CPU side: small, Rust,
  orchestrator") manages disc/RAM/GPU storage-tier moves, wires
  the axon router, runs the GPU tick loop. Lots of code; needs
  a real GPU compute target to manage in the first place.
- **64-bit Rust execution.** Attempted in v0.2; blocked by
  QEMU's `-kernel` flag refusing 64-bit ELFs. See "Attempted but
  deferred" section above.
- **GRUB-bootable ISO image.** Would unlock multiboot2 + 64-bit
  ELF entry, enabling 64-bit Rust without the two-crate
  workspace alternative.

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
Yantra bootloader v0.4 - hello from bare metal
-- PCI scan --
  00:00.0 vendor=8086 device=1237 class=06 (bridge) subclass=00
  00:01.0 vendor=8086 device=7000 class=06 (bridge) subclass=01
  00:01.1 vendor=8086 device=7010 class=01 (mass-storage) subclass=01
  00:01.3 vendor=8086 device=7113 class=06 (bridge) subclass=80
  00:02.0 vendor=1234 device=1111 class=03 (display) subclass=00
  00:03.0 vendor=8086 device=100e class=02 (network) subclass=00
-- end PCI scan --
-- GPU init (framebuffer) --
  GPU PCI=00:02.0 BAR0=0xfd000008 framebuffer=0xfd000000
  wrote 100x640 pixel gradient to framebuffer
  first pixel = 0xff000000 (should be 0xFF000000 = top-row black)
-- kernel image load --
  copied 61 bytes to GPU memory at 0xfd100000
  first 4 bytes read back = 0x544e4159 (= 'Y','A','N','T' = 0x544E4159)
-- orchestrator handoff --
  Orchestrator running. (stub - no GPU compute target on QEMU stdvga.)
  ...
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
