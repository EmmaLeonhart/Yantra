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
|  Resource manager + init (small CPU program)              |
|  - Boots the system, hands control to the GPU             |
|  - Decides who gets evicted to RAM cold-store             |
|  - Wakes RAM-resident processes back into GPU on demand   |
+----------------------------------------------------------+
|  CPU + RAM + storage (conventional)                       |
|  - CPU is small/underpowered, only orchestrates the GPU   |
|  - RAM is cold-store for suspended processes              |
|  - Storage is ext4/btrfs/zfs — interpretable on any OS    |
+----------------------------------------------------------+
|  Hardware: GPU today, analog substrate later              |
+----------------------------------------------------------+
```

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

### 3. Init + resource manager

A small CPU program that:

- Loads the bootloader, then the kernel onto the GPU.
- Maintains the table of processes (active in GPU vs cold-stored in RAM).
- Handles evictions and resumes.
- Does *not* schedule — the GPU runs everything that fits, simultaneously.

### 4. GUI

Everything is a browser. HTML5 + CSS + a constrained subset of JS/TS + WebGL.
JS/TS transpiles to Sutra ahead of time. No `eval`, no service workers
pushing code, no continuous server-emitted JS. See `06-gui-stack.md`.

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
