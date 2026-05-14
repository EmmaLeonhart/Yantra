@echo off
REM Build the Yantra bootloader into a bootable disk image QEMU can boot.
REM See scripts/qemu-build.sh for the full doc.

setlocal
set "REPO_ROOT=%~dp0.."
pushd "%REPO_ROOT%\bootloader" || exit /b 1

where cargo >nul 2>nul
if errorlevel 1 (
  echo ERROR: cargo not found. Install Rust from https://rustup.rs/
  exit /b 1
)

where bootimage >nul 2>nul
if errorlevel 1 (
  echo Installing bootimage build tool ^(one-time^)...
  cargo install bootimage
  if errorlevel 1 exit /b 1
)

echo ^>^>^> cargo bootimage --release...
cargo bootimage --release
if errorlevel 1 exit /b 1

set "OUT=target\x86_64-unknown-none\release\bootimage-yantra-bootloader.bin"
if exist "%OUT%" (
  echo ^>^>^> Built: %OUT%
  echo ^>^>^> Run with: scripts\qemu-run.bat
) else (
  echo ERROR: expected output %OUT% not found
  exit /b 1
)

popd
