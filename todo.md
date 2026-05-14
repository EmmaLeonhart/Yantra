# Yantra — longer-horizon TODOs

> **What this file is.** Forward work that doesn't fit in the
> current `queue.md` (which is strictly "what's being done right
> now"). Items here can sit for weeks. They migrate to `queue.md`
> when picked up; cleared from `queue.md` when done.
>
> **What this file is not.** A roadmap commitment. Order is
> heuristic; the user picks what to start.

---

## 1. Kernel — Connectome Manager, beyond the Python v0.0 prototype

The `kernel/` directory ships a working **Python prototype** of the
Connectome Manager (manifest + router + init + two example services
+ 19 passing tests). The Python is a behavioural harness; the
production form is Rust. Hardening list:

- **Rust port of the Connectome Manager.** The production form on
  the CPU side. "As small as possible" with strong static
  guarantees; the Python prototype is the API reference. Single
  largest piece of work in this list, and the one that turns
  `kernel/` from "behavioural harness" into "runtime."
- **Storage-tier moves: disc ↔ RAM ↔ GPU.** The Python prototype
  only implements admit/deregister against an in-memory pool. The
  Connectome Manager's actual job is shuffling programs between
  disc, RAM, and GPU per the architecture. RAM in Yantra is
  semantically closer to disc than to traditional RAM
  (`planning/01-architecture.md` § "The kernel is a Connectome
  Manager"); the manager decides which tier each program lives in
  at any moment.
- **Real per-process GPU memory arenas.** v0.0's `compute_units`
  is bookkeeping only. Production needs the multi-process Sutra
  runtime (being implemented in the Sutra repo upstream) to carve
  out actual device memory per admitted process, with admission-
  time refusal that corresponds to actual hardware capacity rather
  than an integer counter.
- **GPU-tick-parallel scheduling.** v0.0 ticks services
  sequentially on CPU. Production runs every admitted process
  simultaneously on the GPU at each tick. Drop-in once the Sutra
  multi-process runtime lands upstream; the service abstraction is
  concurrency-agnostic.
- **`.su` service loading** (`kernel.services.load_su_service()`
  is currently `NotImplementedError`). Needs the Sutra-side
  convention for "what does a service-shaped `.su` program
  export?" — sketched in the docstring; needs an upstream Sutra
  decision before we wire it through here.
- **Rotation-operator-based capability check.** v0.0 trusts the
  sender's name (admission grants identity; capability is checked
  by name). Production's threat model (`paper/paper.md` § 3.3.1)
  is operator-based: possession of `R_role` is the capability.
  Lands when the `.su` loader does.
- **CPU-side hardware shim** for the interrupt + MMIO + tick
  pattern in `paper/paper.md` § 3.5. Blocked on having target
  hardware. The shim itself is in the Rust orchestrator's scope.
- **Bootloader.** A small program that loads the compiled kernel
  image onto the GPU and starts it executing. C or Rust; the
  C→Sutra transpiler is the long-term target if we want the
  bootloader inside the verification surface.

## 2. Userspace utilities — native Sutra rewrites — second milestone

**Build order:** these are the **second milestone** after the
Connectome Manager works. Initial system access is **command-line
only** (SSH or serial from a host computer). No GUI in this phase.
The vision is "we can edit files on this thing from my computer";
once that works the browser becomes the third milestone.

**Policy:** written natively in Sutra. Not C-transpiled. The
`external/{coreutils,util-linux,busybox}` submodules are
behavioural reference, not transpile inputs.

**Status: cannot do right now.** The blocker is not the language —
it's that Sutra's string + IO + filesystem vocabulary isn't mature
enough to make these comfortable to write yet. Once the kernel
`.su` loader lands and the Sutra stdlib grows pattern-match /
string-split / process-args / read-stdin primitives, this opens
up.

The Q-list, in rough order of priority:

| Priority | Utility | Why first/last |
|---|---|---|
| **High — first wave** | `echo` | Trivial. Smoke test for "Sutra utility writes to stdout." |
| | `cat` | Smoke test for "Sutra utility reads files." |
| | `ls` | First non-trivial — directory iteration + formatting. Forces decisions on the FS-bridge directory-listing axon shape. |
| | `wc` | Stream consumption + counter accumulation. Pure functional pattern. |
| | `head` / `tail` | Stream consumption + bounded buffering. Tail's `-f` is a real exercise of the axon-channel-as-stream model. |
| **Mid wave** | `grep` | Regex (or initial-cut substring match). Forces a regex implementation in Sutra or a stdlib decision to defer. |
| | `cut` / `tr` | Field/character processing. Pure stream transforms. |
| | `sort` / `uniq` | Whole-buffer accumulation + sort. Memory-shape question — how does a Sutra utility allocate "all the input" when the input is unbounded? |
| | `find` | Recursive directory traversal. Forces FS-bridge recursion shape. |
| | `mv` / `cp` / `rm` | Mutating FS operations. Forces capability check on `R_write_path`. |
| | `mkdir` | Trivial once `mv`/`cp`/`rm` work. |
| **Late wave — research-grade** | `awk` | Whole programming-language-in-a-utility. Either ship a minimal `awk` or document the gap. |
| | `sed` | Same shape as `awk` but for stream-edit. Often deferred to "use Sutra source directly." |
| **Out of scope, probably** | `bash` / `sh` | Yantra doesn't have a shell story yet. Possibly a Sutra-native REPL replaces this entirely; possibly we do ship a minimal POSIX shell. Open. |
| | `mount` / `dmesg` / `lsblk` (util-linux) | Kernel-adjacent. Belong with the kernel work, not userspace. |
| | `systemd` / service managers | Yantra's init/resource-manager IS the service manager. systemd has no analogue. |

Each utility lands as `apps/<name>.su` once the Sutra stdlib +
kernel loader can support it. Manifest goes in `apps/manifests/`.

## 3. Browser — renderer + TS-transpiler-CLI + first transpiled web app — third milestone

**Build order: third milestone**, after (1) Connectome Manager and
(2) command-line userspace utilities are working. The browser is
"everything is a browser" — every GUI component (start menu, mouse
cursor, login screen, file manager) is a browser-rendered HTML
page. Single GUI framework, no exceptions.

**Stack: HTML5 + CSS + idiomatic TypeScript + WebGL/Three.js. NO
WebAssembly** (decision 2026-05-14, see `planning/06-gui-stack.md`
and `planning/07-transpilers.md`). TS components are pre-transpiled
to Sutra ahead of time, not at runtime.

Three parallel tracks once we get to milestone three:

- **Sutra-native renderer.** Layout engine + display server pair
  that consumes axons describing the screen state and emits
  framebuffer-shaped axons. Writable in pure Sutra today; doesn't
  depend on any transpiler. Probably lives at `apps/renderer.su` +
  a `kernel/services/display.su` once we have a real kernel loader.
  First concrete deliverable: render a hand-written Sutra "page"
  (literally just text + a colored rectangle) without touching HTML.
- **TS→Sutra transpiler CLI wired up.** Currently
  `external/Sutra/sdk/sutra-from-ts/sutra_from_ts/__main__.py` is
  the skeleton stub even though `lower.py` works. Wiring is small
  and unblocks all browser work that loads real JS/TS bundles.
  This is upstream work, not Yantra-side — a PR or issue in the
  Sutra repo.
- **First transpiled web app.** Once the CLI is wired, a
  hello-world reactive component (Solid/Svelte-style) compiled
  through `ts2su → sutrac → executes` is the smallest demonstration
  that the browser can load real web content.

What's not yet in any plan:

- HTML parser. Probably written natively in Sutra.
- CSS engine. Same.
- WebGL bindings. Mentioned in `planning/06-gui-stack.md` but no
  implementation path.
- Network stack (`fetch`, `WebSocket`). Several weeks of work even
  with the language in place.

---

## Pointers to the live work

- Active: `queue.md`
- Architecture: `planning/01-architecture.md`
- Hard memory problem: `planning/17-memory-model.md`
- Engineering readiness audit: `planning/18-kernel-browser-readiness.md`
- Kernel layout + what's stubbed: `kernel/README.md`
- Paper revision discipline: `CLAUDE.md` § "Paper revision discipline"
