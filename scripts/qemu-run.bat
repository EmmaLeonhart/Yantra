@echo off
REM Boot the Yantra bootloader image in QEMU.
REM See scripts/qemu-run.sh for the full doc.

setlocal
set "REPO_ROOT=%~dp0.."
set "IMG=%REPO_ROOT%\bootloader\target\x86_64-unknown-none\release\bootimage-yantra-bootloader.bin"

if not exist "%IMG%" (
  echo ERROR: bootimage not found at %IMG%
  echo Run scripts\qemu-build.bat first.
  exit /b 1
)

REM Look for qemu-system-x86_64.exe in PATH; if not, check common
REM Windows install locations.
where qemu-system-x86_64 >nul 2>nul
if errorlevel 1 (
  if exist "C:\Program Files\qemu\qemu-system-x86_64.exe" (
    set "QEMU=C:\Program Files\qemu\qemu-system-x86_64.exe"
  ) else (
    echo ERROR: qemu-system-x86_64 not found in PATH or C:\Program Files\qemu.
    echo Install QEMU: winget install SoftwareFreedomConservancy.QEMU
    exit /b 1
  )
) else (
  set "QEMU=qemu-system-x86_64"
)

echo ^>^>^> Booting Yantra bootloader in QEMU. Ctrl+A then X to exit.
"%QEMU%" -drive format=raw,file="%IMG%" -serial stdio -display none -no-reboot
