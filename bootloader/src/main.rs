//! Yantra bare-metal bootloader v0.0.
//!
//! Runs in QEMU as a freestanding x86_64 binary booted by the
//! `bootloader` crate's BIOS/UEFI handoff. Prints
//! "Yantra bootloader v0.0 — hello from bare metal" via two channels:
//!
//!   1. The VGA text-mode buffer at `0xb8000` — visible if booted with
//!      QEMU's default display (gfx window).
//!   2. QEMU's emulated COM1 serial port at I/O port `0x3F8` — captured
//!      by `qemu-system-x86_64 -serial stdio`, which is the mode the
//!      `scripts/qemu-run.{sh,bat}` wrappers use so output appears in
//!      the host terminal.
//!
//! After the print, the CPU halts in `cli; hlt`. Nothing else.
//!
//! What this binary is NOT (per `planning/19-boot-sequence.md` § Stage 3):
//!
//!   - It does NOT initialise the GPU. Discovering + initing the GPU
//!     is real bootloader work for v0.1+.
//!   - It does NOT load a Sutra-compiled kernel image into GPU memory.
//!     That needs both GPU init (above) and a defined kernel-image
//!     format. Both v0.1+.
//!   - It does NOT hand off to a Rust orchestrator. The orchestrator
//!     is its own runtime that runs after the bootloader; v0.1 work.
//!
//! What this binary IS: a demonstration that a Yantra-authored binary
//! can boot under QEMU, talk to virtualized hardware (the COM1 UART
//! and the VGA buffer), and run on bare metal with no OS underneath.
//! Tier-3 milestone, smallest possible v0.

#![no_std]
#![no_main]

use core::panic::PanicInfo;
use bootloader::{entry_point, BootInfo};

entry_point!(kernel_main);

const HELLO: &[u8] = b"Yantra bootloader v0.0 - hello from bare metal";

fn kernel_main(_boot_info: &'static BootInfo) -> ! {
    write_vga(HELLO);
    write_serial(HELLO);
    write_serial(b"\n");
    halt_loop();
}

/// Write `bytes` to the VGA text-mode buffer at 0xb8000.
///
/// VGA text-mode each cell is two bytes: `[char, attribute]`. We use
/// attribute `0x0F` (white on black). 80 columns × 25 rows; we write
/// at the start of row 0.
fn write_vga(bytes: &[u8]) {
    let vga_buffer = 0xb8000 as *mut u8;
    for (i, &byte) in bytes.iter().enumerate() {
        // Bound the write to a single row of 80 cells (160 bytes).
        if i >= 80 {
            break;
        }
        unsafe {
            *vga_buffer.add(i * 2) = byte;
            *vga_buffer.add(i * 2 + 1) = 0x0F; // white on black
        }
    }
}

/// Write `bytes` to QEMU's emulated COM1 serial port at 0x3F8.
///
/// QEMU presents the UART as ready by default — no init needed. On
/// real hardware we'd configure the UART (set baud rate, line
/// control, FIFO) before writing; v0.0 leans on QEMU's defaults.
fn write_serial(bytes: &[u8]) {
    for &byte in bytes {
        unsafe {
            outb(0x3F8, byte);
        }
    }
}

/// `out dx, al` — single-byte output to an I/O port.
unsafe fn outb(port: u16, val: u8) {
    core::arch::asm!(
        "out dx, al",
        in("dx") port,
        in("al") val,
        options(nostack, preserves_flags),
    );
}

/// Halt the CPU. `cli` masks interrupts (we have no IDT installed),
/// `hlt` waits for an interrupt (which won't come), repeat forever.
fn halt_loop() -> ! {
    loop {
        unsafe {
            core::arch::asm!("cli; hlt", options(nostack, preserves_flags));
        }
    }
}

#[panic_handler]
fn panic(_info: &PanicInfo) -> ! {
    // Try to surface the panic via serial — even a single byte is
    // useful for "did we get here?" debugging. Skip VGA because we
    // may have crashed mid-write to it.
    write_serial(b"\n[Yantra bootloader PANIC]\n");
    halt_loop();
}
