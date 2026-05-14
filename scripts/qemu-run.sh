#!/usr/bin/env bash
# Boot the Yantra bootloader image in QEMU.
#
# Expects bootloader/target/x86_64-unknown-none/release/bootimage-yantra-bootloader.bin
# to exist. Run scripts/qemu-build.sh first if not.
#
# QEMU args:
#   -drive format=raw,file=...      load the bootimage as a raw disk
#   -serial stdio                   forward COM1 to host stdout
#   -display none                   no graphical window — pure terminal
#   -no-reboot                      don't restart after halt; just exit
#
# Output: the bootloader prints "Yantra bootloader v0.0 — hello from
# bare metal" via the VGA buffer (invisible without -display) and
# via COM1 (which we capture). Then halts. QEMU stays running until
# you Ctrl+A then X (QEMU's standard exit).
#
# Prerequisite: QEMU installed. On Windows: `winget install
# SoftwareFreedomConservancy.QEMU`. On Linux: distro package
# (`apt install qemu-system-x86`, `pacman -S qemu`). On macOS:
# `brew install qemu`.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

IMG="$REPO_ROOT/bootloader/target/x86_64-unknown-none/release/bootimage-yantra-bootloader.bin"
if [ ! -f "$IMG" ]; then
  echo "ERROR: bootimage not found at $IMG" >&2
  echo "Run scripts/qemu-build.sh first." >&2
  exit 1
fi

if ! command -v qemu-system-x86_64 >/dev/null 2>&1; then
  echo "ERROR: qemu-system-x86_64 not found." >&2
  echo "Install QEMU: see bootloader/README.md for platform instructions." >&2
  exit 1
fi

echo ">>> Booting Yantra bootloader in QEMU. Ctrl+A then X to exit."
exec qemu-system-x86_64 \
  -drive format=raw,file="$IMG" \
  -serial stdio \
  -display none \
  -no-reboot
