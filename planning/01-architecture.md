# Architecture

## Layer cake

```
+----------------------------------------------------------+
|  GUI layer (everything-is-a-browser)                      |
|  - HTML5 + CSS, AOT-compiled JS/TS, WebGL                 |
|  - JS bundles → Sutra → tensor program                    |
|  - Apps look like Electron from the outside, but compile  |
|    down to the same axon dataflow as kernel services.     |
+----------------------------------------------------------+
|  Userspace processes                                      |
|  - Each is a Sutra program: (Axon) -> Axon                |
|  - Pre-allocated GPU compute + synthetic dim. block       |
|  - Tail-recursive loops, fuzzy superposition, no branches |
+----------------------------------------------------------+
|  Kernel services (Sutra)                                  |
|  - Process table, axon router, capability check           |
|  - File-system bridge (read_file → Axon)                  |
|  - Display server, input router, network stack            |
+----------------------------------------------------------+
|  Sutra runtime                                            |
|  - Tensor-op graph executor                               |
|  - GPU memory arenas, fixed allocations per process       |
|  - Soft-halt RNN cells driving tail-recursive loops       |
+----------------------------------------------------------+
|  Connectome Manager (Rust on the CPU side)                |
|  - Boots the system, hands control to the GPU             |
|  - Loads programs disc→RAM→GPU; offloads GPU→RAM→disc     |
|  - Decides where each program lives at any moment         |
|  - Does NOT schedule — the GPU runs everything that fits  |
+----------------------------------------------------------+
|  CPU + RAM + storage (conventional)                       |
|  - CPU is small/underpowered, only orchestrates the GPU   |
|  - RAM holds programs that are loaded but not running     |
|    (semantically closer to disc than to traditional RAM)  |
|  - Storage is ext4/btrfs/zfs — interpretable on any OS    |
+----------------------------------------------------------+
|  Hardware: GPU today, analog substrate later              |
+----------------------------------------------------------+
```

## The kernel is a Connectome Manager

The phrase "kernel" carries traditional baggage — process scheduler,
memory allocator, syscall dispatcher, interrupt handler. In Yantra
the kernel is something else: a **Connectome Manager**.

There are no traditional memory slots that the CPU code allocates.
The processes are just connected to each other — their axons
(rotation-bound vectors) form a big neural network, with each
process being roughly a neuron and each axon channel being roughly
a synapse. The kernel's job is not to allocate, schedule, or
context-switch; it is to **decide what is connected to what right
now**.

That decision has three storage tiers:

- **Disc** — programs at rest. The conventional filesystem on the
  underlying storage device. A program here is not running, and
  loading it costs storage→RAM bandwidth.
- **RAM** — programs that are loaded but not running. **In Yantra,
  RAM is semantically closer to disc than to traditional RAM.** It
  is the warm cache between disc and GPU, not the working set of an
  active computation. A program in RAM has been brought close to
  the GPU but is not in the connectome.
- **GPU** — the connectome itself. Programs running here are wired
  into the axon graph; their compute is the computation. The GPU
  runs everything that fits, simultaneously.

The Connectome Manager moves programs between these tiers:

- disc → RAM (warm a program for likely use)
- RAM → GPU (admit a program into the live connectome)
- GPU → RAM (offload a program from the connectome without
  evicting from memory entirely)
- RAM → disc (cool a program down to storage)

It does not schedule, does not allocate per-instruction memory,
does not handle traditional context switches. The GPU runs every
admitted program at every tick; the only thing that varies over
time is which programs are admitted vs cold-stored.

This is why Yantra avoids most of the memory-access pathology of
von Neumann machines. There are no shared address spaces, no cache
coherency between cores, no page tables, no TLB shootdowns. The
crosstalk problem (and the bundle-depth budget that bounds it)
replaces them — different concerns, but not the same concerns. See
`planning/17-memory-model.md` for what is open here.

## CPU side: small, Rust, orchestrator

The CPU side of Yantra exists to orchestrate the GPU. Its work is:

- Run the bootloader.
- Load the compiled kernel image onto the GPU.
- Run the Connectome Manager itself.
- Mediate the disc/RAM/GPU storage tier moves.
- Wrap MMIO peripherals as axon channels (paper §3.5).

**Implementation language: Rust.** Justified by:

- Small. The vision is "as small as possible," and Rust gives a
  small surface with strong static guarantees that survive into
  the binary. Yantra targets critical systems where the
  certifiability of the trusted base is a procurement criterion.
- The CPU side is the one place memory-safety matters in the
  conventional sense — the connectome on the GPU does not have
  pointers or dynamic allocation in the traditional sense, but the
  Rust orchestrator does, because it is talking to actual
  byte-shaped hardware.
- Compatible with the eventual C-transpile path for the bootloader
  (the bootloader can stay in C/Rust and be transpiled to Sutra
  later if the verification surface argument demands it).

The Yantra-side `kernel/` directory in this repository currently
holds a **Python prototype** of the Connectome Manager, sufficient
for behavioural smoke tests (see `kernel/README.md`). The Rust
implementation is the production target; the Python prototype is
reference and harness.

## Three guiding inversions

Yantra inverts three things people usually take for granted:

1. **CPU is the brain → CPU is the orchestrator.** The CPU exists to load
   the bootloader, kick off the GPU runtime, and shuffle inactive processes
   to and from RAM. It does no application work. It is closer in role to
   a CUDA host than to a conventional kernel.

2. **Programs use the OS to talk to AI → AI talks via the OS.** The OS
   doesn't expose an "AI API" on top of a conventional process model. The
   process model itself is embedding-shaped: every process is something
   that takes an axon and returns an axon. AI integration is what you get
   for free; it is not a feature that was added.

3. **File system is internal → File system is the legible surface.** The
   compute is opaque (matrix soup, by design). The file system is the part
   that has to remain readable by humans and forensics. So the FS stays
   conventional, and the boundary between "compute world" and "storage
   world" is a small, well-defined set of syscalls that read and write
   axons from files.

## The four pieces that need to exist

Roughly in order of "must work" to "would be nice":

### 1. Sutra runtime with fixed allocations

Multi-process Sutra runtime where every process declares its compute and
synthetic-dimension footprint at install time, and the runtime guarantees
those allocations until the process exits. Adding more processes does not
slow existing ones until the GPU is full. Once it is full, new launches
fail; nothing already running degrades.

### 2. Axon-based IPC

A standard data model and protocol for passing axons between processes.
Axon = a structured embedding produced by rotation binding over a fixed
codebook of role-fillers. See `02-axon-model.md`.

### 3. Connectome Manager (Rust on the CPU side)

A small Rust program that:

- Loads the bootloader, then the kernel onto the GPU.
- Maintains the table of programs in the three storage tiers
  (disc / RAM / GPU) and decides which moves to make.
- Mediates disc↔RAM↔GPU transfers.
- Wraps MMIO peripherals as axon channels (`paper/paper.md` § 3.5).
- Does *not* schedule — the GPU runs everything that fits,
  simultaneously.

The v0.0 of this is the Python prototype under `kernel/` in this
repository (see `kernel/README.md`). The production form is Rust,
because (a) "as small as possible" wants a small surface with
strong static guarantees that survive into the binary, and (b)
the CPU side is the one place memory-safety in the conventional
sense matters — the Rust orchestrator talks to actual byte-shaped
hardware.

### 4. Userspace utilities — file access first, command-line only

Sequencing: once the Connectome Manager works, the next milestone
is **command-line file access** — simple Linux-shaped utilities
written natively in Sutra (cat, ls, etc.; see `todo.md` § 2 for
the Q-list). The initial system has **no graphical user interface
at all**; access is via SSH or serial from a host computer. The
GUI/browser is the third milestone, after the utilities work.

### 5. GUI — eventually

Everything is a browser. HTML5 + CSS + idiomatic TypeScript +
WebGL/Three.js. TS is AOT-transpiled to Sutra at page load. No
`eval`, no service workers pushing code, no continuous
server-emitted JS, **no WASM** (decision 2026-05-14, see
`06-gui-stack.md` and `07-transpilers.md`). See `06-gui-stack.md`
for the full GUI commitment.

## What is *not* in the architecture

- A scheduler in the conventional sense. The GPU runs all admitted
  processes together because there is enough room; if there isn't, the
  process is in RAM cold-store waiting to be woken.
- A traditional virtual memory subsystem on the GPU side. Every process
  has a fixed-width state vector and a fixed synthetic-dimension block.
  Crosstalk control happens through rotation binding, not page tables.
- A monolithic kernel surface. Kernel "services" are themselves Sutra
  programs; they happen to be the ones the init system always boots.

## Open architectural questions

Tracked in `15-open-questions.md`. The ones that most affect this layer
cake are:

- How does the resource manager tell the difference between "process is
  cold but live" and "process is dead"?
- How does the GPU runtime expose telemetry to the small CPU without
  becoming a bottleneck?
- What is the smallest possible bootloader that can load a Sutra image
  onto a GPU and start it executing?
