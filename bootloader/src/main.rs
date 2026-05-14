//! Yantra bare-metal kernel v0.0 — multiboot1, 32-bit, no third-party deps.
//!
//! Boots in QEMU via `qemu-system-x86_64 -kernel <this-binary>`. QEMU's
//! `-kernel` flag accepts multiboot1-compatible ELF binaries directly:
//! no disk image, no BIOS boot sector, no third-party bootloader crate.
//! The kernel runs in 32-bit protected mode (multiboot1 hands off in
//! that mode) and prints "Yantra bootloader v0.0 — hello from bare
//! metal" via QEMU's COM1 serial port.
//!
//! This replaces the v0.0.1 bootloader-v0.9-crate setup, which
//! triple-faulted at boot under Rust 1.96 nightly. The hand-rolled
//! multiboot1 path has no version-skew surface — multiboot1 is a
//! fixed spec (1995), QEMU's loader has been stable since the early
//! 2000s, and the only Rust feature we use beyond `no_std` is inline
//! `asm!` (stable since Rust 1.59).
//!
//! What this binary does:
//!   - Multiboot1 header at the start of the binary.
//!   - `_start` entry (in `global_asm!`): sets ESP to a known stack
//!     top, then jumps to Rust `kernel_main`.
//!   - `kernel_main`: writes "Yantra bootloader v0.0 — hello from
//!     bare metal" to COM1 (I/O port 0x3F8). QEMU's `-serial stdio`
//!     forwards this to the host terminal.
//!   - Halts in `cli; hlt` loop forever.

#![no_std]
#![no_main]

use core::arch::{asm, global_asm};
use core::panic::PanicInfo;

// --- multiboot1 header ----------------------------------------------

const MULTIBOOT_MAGIC: u32 = 0x1BADB002;
const MULTIBOOT_FLAGS: u32 = 0;
const MULTIBOOT_CHECKSUM: u32 = (-((MULTIBOOT_MAGIC + MULTIBOOT_FLAGS) as i32)) as u32;

#[link_section = ".multiboot"]
#[used]
static MULTIBOOT_HEADER: [u32; 3] = [
    MULTIBOOT_MAGIC,
    MULTIBOOT_FLAGS,
    MULTIBOOT_CHECKSUM,
];

// --- entry: set up stack, call into Rust ----------------------------
//
// global_asm! defines the actual `_start` entry point so we control
// the very first instructions. Multiboot1 hands off in 32-bit
// protected mode but doesn't guarantee a usable stack, so the very
// first thing we do is point ESP at our own stack buffer. Then we
// call into `kernel_main` which is regular Rust.
//
// AT&T-style asm because that's what global_asm! defaults to on
// x86 with the LLVM backend; the `.intel_syntax noprefix` directive
// switches to Intel syntax for readability.

global_asm!(
    r#"
    .section .text
    .global _start
    .intel_syntax noprefix
_start:
    /* Multiboot puts magic in EAX, info ptr in EBX. We don't use
     * them in v0.0, but preserve them in case a future revision
     * does — push to stack after setting ESP. */
    lea esp, [stack_top]
    push ebx                /* multiboot info pointer */
    push eax                /* multiboot magic */
    call kernel_main
    /* kernel_main is `-> !` so we never return; loop just in case. */
1:  cli
    hlt
    jmp 1b

    .section .bss
    .align 16
stack_bottom:
    .skip 16384             /* 16 KB stack — plenty for v0.0 */
stack_top:
    "#
);

// --- Rust kernel ----------------------------------------------------

const HELLO: &[u8] = b"Yantra bootloader v0.0 - hello from bare metal\n";
const SERIAL_COM1: u16 = 0x3F8;

#[no_mangle]
pub extern "C" fn kernel_main(_multiboot_magic: u32, _multiboot_info: u32) -> ! {
    write_serial(HELLO);
    halt_loop();
}

fn write_serial(bytes: &[u8]) {
    for &b in bytes {
        unsafe { outb(SERIAL_COM1, b) };
    }
}

unsafe fn outb(port: u16, val: u8) {
    asm!(
        "out dx, al",
        in("dx") port,
        in("al") val,
        options(nostack, preserves_flags),
    );
}

fn halt_loop() -> ! {
    loop {
        unsafe {
            asm!("cli; hlt", options(nostack, preserves_flags));
        }
    }
}

#[panic_handler]
fn panic(_info: &PanicInfo) -> ! {
    write_serial(b"\n[Yantra PANIC]\n");
    halt_loop();
}
