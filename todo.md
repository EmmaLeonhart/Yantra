# Yantra — longer-horizon TODOs

> **What this file is.** Forward work that doesn't fit in the
> current `queue.md` (which is strictly "what's being done right
> now"). Items here can sit for weeks. They migrate to `queue.md`
> when picked up; cleared from `queue.md` when done.
>
> **What this file is not.** A roadmap commitment. Order is
> heuristic; the user picks what to start.

---

## 1. Kernel — beyond the v0.0 nucleus

The `kernel/` directory ships a working v0.0 (manifest + router +
init + two example services + 19 passing tests). The hardening list
to take it from "demonstrates the architecture's shape" to "could
actually run a workload":

- **Real per-process GPU memory arenas.** v0.0's `compute_units`
  is bookkeeping only. Production needs the multi-process Sutra
  runtime to carve out actual device memory per admitted process,
  with an admission-time refusal that corresponds to actual
  hardware capacity rather than an integer counter. Single biggest
  blocker on the "no degradation under load" property.
- **GPU-tick-parallel scheduling.** v0.0 ticks services
  sequentially on CPU. Production runs every admitted process
  simultaneously on the GPU at each tick. Drop-in replacement for
  `Init.tick()` once the parallel scheduler exists; the service
  abstraction is concurrency-agnostic.
- **`.su` service loading** (`kernel.services.load_su_service()`
  is currently `NotImplementedError`). Needs the Sutra-side
  convention for "what does a service-shaped `.su` program
  export?" — sketched in the docstring; needs an upstream Sutra
  decision before we wire it through here.
- **Rotation-operator-based capability check.** v0.0 trusts the
  sender's name (admission grants identity; capability is checked
  by name). Production's threat model (`paper/paper.md` § 3.3.1)
  is operator-based: possession of `R_role` is the capability.
  Lands when the `.su` loader does — a Sutra-side service can
  carry its operators directly.
- **Eviction to RAM cold-store** (`planning/03-process-lifecycle.md`).
  Atomic per-process eviction with bit-exact serialise/resume. The
  open question of cold-store integrity (signed-on-evict,
  verified-on-resume) lives in `planning/17-memory-model.md`.
- **CPU-side hardware shim** for the interrupt + MMIO + tick
  pattern in `paper/paper.md` § 3.5. Blocked on having target
  hardware.
- **Bootloader.** A small program that loads the compiled kernel
  image onto the GPU and starts it executing. The bootloader is the
  one place a C origin is genuinely useful; the C→Sutra transpiler
  is the long-term target for compiling it.

## 2. Userspace utilities — native Sutra rewrites

**Policy:** these are written natively in Sutra. Not C-transpiled.
The `external/{coreutils,util-linux,busybox}` submodules are
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

## 3. Browser — renderer + TS-transpiler-CLI + first transpiled web app

The browser is "everything is a browser" — Yantra's GUI claim. Three
parallel tracks:

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
