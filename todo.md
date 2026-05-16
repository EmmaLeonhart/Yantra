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

- **Bootloader (Rust) — v0.4 shipped + verified in QEMU 11.0.50 (2026-05-14).** The first Yantra-authored code that runs at boot. Lives at `bootloader/`. End-to-end demonstrated: multiboot1 entry, PCI bus enumeration, GPU framebuffer pixel writes, kernel-image placeholder copy to GPU memory, stub orchestrator handoff, long-mode transition with 64-bit "Long mode active" print. **v0.2 (real Rust in long mode) attempted and blocked**: QEMU's `-kernel` refuses 64-bit ELFs; multiboot2 needs GRUB to boot. Two unblock paths: GRUB ISO build, or two-crate i686-boot-stub + x86_64-payload workspace. **v0.5+ (real Sutra kernel execution) gated on actual GPU passthrough**: VFIO on a Linux host with a spare GPU. QEMU's emulated stdvga can't run CUDA, so Sutra-on-virtualized-GPU isn't possible at the QEMU dev tier.
- **Rust port of the Connectome Manager (orchestrator).** The
  production form on the CPU side, runs after boot. "As small as
  possible" with strong static guarantees; the Python prototype
  is the API reference. Single largest piece of post-bootloader
  work in this list, and the one that turns `kernel/` from
  "behavioural harness" into "runtime."
- **Lazy axon evaluation in the production router.** Kernel-level
  slice (skip uninterested receivers) works. Per-receiver
  projection is wired (`register_projector` → `_VSA.axon_project`)
  but the 2026-05-15 end-to-end semantic test
  (`test_projected_payload_still_decodes_semantically`, strict
  xfail) **proves it is a no-op for embedding fillers**:
  `axon_project(bundle,[k]) = bind(k,unbind(k,bundle))` is identity
  for orthogonal rotation binding on semantic-block fillers, so the
  "slimmed" payload still holographically contains every key
  (dropped key decoded +0.5726 vs kept +0.5999). **No bandwidth
  reduction and no capability isolation for the common case** —
  bears on `paper/paper.md` § 3.3.1. The real fix is producer-side
  pruning (rebuild the bundle without the unwanted `axon_add`
  terms, whole-program analysis per Sutra `axons.md` §"Lazy
  evaluation across boundaries") — a **Sutra-side design
  decision**, not a Yantra-side wiring task. See
  `planning/20-lazy-axon-evaluation.md` § Status and `queue.md`.
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
- **`.su` service loading — WORKS (corrected 2026-05-16).** This
  bullet previously claimed `kernel.services.load_su_service()`
  "is currently `NotImplementedError`" and needs "an upstream
  Sutra decision." Both false: `load_su_service` is defined
  nowhere (measured — absent on `kernel` and `kernel.services`),
  and `.su` services load + run via `SutraService(source_path=…,
  output_role=…)` — it compiles the `.su`, invokes
  `on_axon(vector)->vector`, and consumes the compiled module's
  `AXON_KEYS_BOUND`/`AXON_KEYS_READ` static analysis. That export
  convention is the "Sutra-side decision" the old text waited on;
  it shipped and is exercised by many passing
  `tests/test_kernel_sutra.py` tests (incl. real echo/sink `.su`
  services). No `load_su_service` wrapper is needed —
  `SutraService(...)` already is the one-liner. What genuinely
  remains here is the *Rust* orchestrator's own `.su` loader (the
  Python `SutraService` is the API reference), not a missing
  Python stub.
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

## ~~Investigate: bundle-decoding regression~~ — RESOLVED 2026-05-15

Root-caused and fixed in Sutra `eb0ce93e`. It was NOT a numerical /
bind-chain regression and did NOT degrade the VSA-capacity story:
the Sutra compiler coerced `axon_item`'s string-literal key to a
`make_string` codepoint vector (because the stdlib signature types
the param `string`) while the producer's member-access path kept it
a host str → producer/consumer keyed on different role vectors →
cross-module decode corruption. Surgical codegen fix; `_run.py` now
PASS at the exact README numbers (+0.40 / margin +0.20), untuned.
Full record: `external/Sutra/planning/findings/2026-05-15-axon-key-
make-string-coercion-regression.md`. (Line kept as a one-time
breadcrumb; delete on next todo.md tidy.)

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

**Stack: HTML5 + CSS + idiomatic TypeScript + WebGL/Three.js.
WASM is eventually in scope but not for a long time** — not v0,
not v0.1, not on any near-term roadmap (decision 2026-05-14, see
`planning/06-gui-stack.md` and `planning/07-transpilers.md`). TS
components are pre-transpiled to Sutra ahead of time, not at
runtime.

Three parallel tracks once we get to milestone three:

- **Sutra-native renderer.** Layout engine + display server pair
  that consumes axons describing the screen state and emits
  framebuffer-shaped axons. Writable in pure Sutra today; doesn't
  depend on any transpiler. Probably lives at `apps/renderer.su` +
  a `kernel/services/display.su` once we have a real kernel loader.
  First concrete deliverable: render a hand-written Sutra "page"
  (literally just text + a colored rectangle) without touching HTML.
- ~~**TS→Sutra transpiler CLI wired up.**~~ Done in Sutra v0.3.2
  (released 2026-05-14). `python -m sutra_from_ts in.ts -o out.su`
  works end-to-end; `pip install sutra-dev[ts]` bundles it. Real
  TS-completeness work (rules for constructs the 17 fixtures don't
  cover) is the ongoing version of this item, but the CLI itself
  is no longer a blocker.
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
