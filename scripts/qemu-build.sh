#!/usr/bin/env bash
# Build the Yantra bootloader into a bootable disk image QEMU can boot.
#
# Two-step process via the bootloader v0.9 crate:
#   1. cargo build --release in bootloader/ produces the kernel ELF.
#   2. cargo bootimage links the kernel with bootloader's BIOS stub
#      and writes a flat-binary disk image.
#
# Output: bootloader/target/x86_64-unknown-none/release/bootimage-yantra-bootloader.bin
#
# Prerequisites (one-time):
#   - Rust nightly (`rust-toolchain.toml` pins it; rustup auto-installs)
#   - bootimage tool: `cargo install bootimage`
#   - llvm-tools-preview: `rustup component add llvm-tools-preview`
#
# Usage:
#   ./scripts/qemu-build.sh
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT/bootloader"

if ! command -v cargo >/dev/null 2>&1; then
  echo "ERROR: cargo not found. Install Rust from https://rustup.rs/" >&2
  exit 1
fi

if ! command -v bootimage >/dev/null 2>&1; then
  echo "Installing bootimage build tool (one-time)..."
  cargo install bootimage
fi

echo ">>> cargo bootimage --release..."
cargo bootimage --release

OUT="target/x86_64-unknown-none/release/bootimage-yantra-bootloader.bin"
if [ -f "$OUT" ]; then
  echo ">>> Built: $OUT ($(stat -c %s "$OUT" 2>/dev/null || stat -f %z "$OUT") bytes)"
  echo ">>> Run with: ./scripts/qemu-run.sh"
else
  echo "ERROR: expected output $OUT not found" >&2
  exit 1
fi
