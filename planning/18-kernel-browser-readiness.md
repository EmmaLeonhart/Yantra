# Readiness assessment — kernel and browser

> **What this document is.** An honest accounting of what we have *now* (Sutra v0.3.1 + the imported Linux source under `external/`) versus what we need to actually start writing (a) the kernel and (b) the browser. Written 2026-05-13 from a direct read of the Sutra v0.3.1 submodule and the v0.3.0 release notes, not from the marketing tone of `paper/paper.md`.
>
> **What this document is not.** A roadmap commitment. The "should we start" calls at the end are recommendations; the user picks.

## Build sequence

User clarification 2026-05-14: the build order is

1. **Connectome Manager (kernel)** — ship the runtime that decides
   what runs on GPU vs sits in RAM vs on disc. Python prototype
   under `kernel/` exists and is tested; production form is Rust.
2. **Command-line userspace utilities** — simple Linux-shaped file
   utilities (cat, ls, grep, etc.), accessed by SSH or serial from
   a host. **No GUI in this phase.**
3. **Browser / GUI** — only after (1) and (2). Every GUI component
   (start menu, mouse, login) is a browser-rendered HTML page;
   single framework; HTML5 + CSS + TS + WebGL/Three.js, no WASM.

Each section below is read in this sequencing context.

## TL;DR

- **Kernel (Connectome Manager) — Sutra-running v0.0 shipped; Rust port pending.** The v0.0 runtime under `kernel/` is real and tested. **Sutra is doing the actual computation**: `SutraService` compiles `.su` source via the Sutra v0.3.1 compiler at admission time and invokes the program's `on_axon(vector) -> vector` on real torch tensors carried through the router. `tests/test_kernel_sutra.py` admits two real Sutra services (echo + sink), sends a `torch.randn(768)` payload, and verifies it routes producer → echo (Sutra compute) → sink (Sutra compute) end-to-end. The orchestration layer (init/resource-manager + router + capability check) is currently in Python; production form on the CPU side is Rust per `planning/01-architecture.md` § "CPU side: small, Rust, orchestrator." 25 tests pass total (19 unit + 6 real-Sutra integration). **Honestly out of scope until upstream Sutra-side work lands**: real per-process GPU memory carve-outs (blocked by PyTorch's per-process GPU model — needs the multi-threaded Sutra runtime), disc/RAM/GPU storage-tier moves (blocked by missing serialise-process-state and evict-from-GPU primitives), GPU-tick-parallel scheduling (drop-in once the Sutra runtime supports it). The architectural shape works end-to-end and Sutra is doing the compute; the work that remains is upstream.
- **Native userspace utilities (cat, ls, grep, awk, etc.) — second milestone, deferred.** Written natively in Sutra, not C-transpiled. `external/{coreutils,util-linux,busybox}` are behavioural reference, not transpile inputs. Blocked on Sutra's string + IO + FS vocabulary maturing and on the kernel `.su` loader landing.
- **Browser — third milestone, deferred.** "Every GUI component is a browser." HTML5 + CSS + idiomatic TS + WebGL/Three.js. WASM eventually but not for a long time (decision 2026-05-14). **The TS→Sutra transpiler ships as Sutra v0.3.2**: CLI works (`python -m sutra_from_ts in.ts -o out.su`), 17 fixtures pass through, `pip install sutra-dev[ts]` bundles it. Coverage isn't "every npm package compiles" — it's "the typed core works, edge constructs need new lowering rules as encountered." The Sutra-native renderer doesn't depend on the TS transpiler and could in principle start now, but is sequenced third per the user's plan.

## What Sutra v0.3.1 actually ships

Pinned at `external/Sutra` (commit `2582cd46`, tag `v0.3.1`, released 2026-05-14). Direct read of the submodule:

### Working today

- **The Sutra compiler (`sutrac`).** Validate, `--emit` to self-contained PyTorch Python, `--run` end-to-end. Runs on Python 3.11+. Substrate-purity audit landed in v0.3.1 (the bug it fixed: complex `+`/`-`/`/` were silently host-Python instead of substrate-pure — bad enough that it warranted a same-day patch release).
- **Multi-program axon passing.** Demonstrated 2026-05-10: two separately-compiled `.su` programs exchange a 5-key axon vector via a numpy `.npy` wire format. Recovery margin verified via host-side cosine monitoring. **This is the kernel-side IPC primitive.** It is not the full Yantra axon-router, but it is the shippable nucleus of one.
- **Stdlib transcendentals on substrate-pure interpolated lookup tables.** `Math.exp/log/sin/cos/tan/sinh/cosh/tanh/pow/sqrt` all native. Trig uses input mod-reduced to `(-π, π]`; hyperbolic beta-reduces to `exp`. No host-Python fall-throughs.
- **Modulus library.** `Math.mod` (eigen-rotation, ~10⁻⁷ max abs error), `Math.fmod` (truncation, JS/C semantics), the `%` operator now substrate-routed.
- **Async/await/`Promise<T>`** as first-class Sutra vocabulary, two-stage beta-reduction at compile time. This is a load-bearing enabler for the browser stack — async is the only sane way to do event-driven UI.

### Mostly-real but not packaged

- **TypeScript transpiler (`sdk/sutra-from-ts/`).** `lower.py` is 1474 lines of real lowering: function declarations, type annotations, interface/type erasure, member access (`p.x` → `p.item("x")` for axon-typed `p`), JS-coercive `+` via `JavaScriptObject.add`, classes (fields + methods + static + constructors + `new`), discriminated unions, while/for/do-while loops, string concat, arrays, enums via `JavaScriptObject` extension. 17 fixtures under `tests/fixtures/` exercise the path end-to-end. **What is missing**: the CLI entry (`__main__.py`) is still the skeleton "not yet implemented" stub, and the README has not been updated to reflect that `lower.py` actually works. The transpiler is invoked from tests, not from a `ts2su` command. Wiring the CLI to call `lower.py` is a small task; pretending the whole transpiler doesn't exist because the CLI is not wired is a misread.

### Genuinely skeleton

- **C transpiler (`sdk/sutra-from-c/`).** ~57 lines total, no `lower.py`. The CLI prints "not yet implemented" and exits non-zero. To bring across coreutils / util-linux / busybox, this needs to be built. Out of scope for a v1 OS attempt; the imported source under `external/` is for *when* the C transpiler arrives, not for *now*.

### Adjacent

- **`sutraDB/`** — included in the repo. Vector-store-flavoured. Not directly on the OS critical path but useful for the FS bridge's `semantic` mode.
- **CUDA backend** — `compile_to_cuda.py`, `hello_world_cuda.py`. The PyTorch backend works on CPU and CUDA; an explicit CUDA emission path exists.
- **`paper/paper.md`** — the Sutra paper itself, with the empirical measurements Yantra's design rests on (100% bundle decoding through k=8 across four substrates, ~1.5×10⁻¹⁵ round-trip, 4→95% in 50 epochs). Cite this directly from `paper/paper.md` in Yantra rather than paraphrasing.

## Imported Linux userspace (under `external/`)

Three submodules, pinned at their latest stable tags as of 2026-05-13:

| Submodule | Tag | Why |
|---|---|---|
| `external/coreutils` | `v9.11` | `ls`, `cat`, `cp`, `mv`, `rm`, `mkdir`, `cut`, `sort`, `uniq`, `wc`, etc. The minimum-viable shell environment. |
| `external/util-linux` | `v2.42` | `mount`, `umount`, `dmesg`, `lsblk`, `findmnt`, `kill`, etc. The administrative layer. |
| `external/busybox` | `1_36_1` | Compact alt-implementations; useful as a fallback when full coreutils is too heavyweight. |

**These are unusable today** because the C→Sutra transpiler is a skeleton. They are checked in so that, when the C transpiler arrives, the source is already pinned to known-good versions and the build harness can proceed without pulling fresh upstreams. Treat the `external/` directory as a *reservation*, not as a working dependency.

## Kernel — what we have, what we need

### What we have (v0.0, shipped)

- **`kernel/` runtime nucleus.** Manifest parser, axon router with capability check, init resource manager with admission control, two example services (echo + sink), and 19 passing tests including a flagship round-trip. See `kernel/README.md` for the layout.
- A working language (Sutra v0.3.1) with multi-program axon passing demonstrated as a separate primitive in `external/Sutra/examples/multi_program_axon/`.
- A compile-to-CUDA path (Sutra ships `compile_to_cuda.py`) so the kernel runs on real GPUs eventually, not only the PyTorch reference.
- Async / `Promise<T>` for event-driven scheduling primitives.
- All seventeen planning docs defining the kernel's intended behaviour.

### What's stubbed in v0.0 — the v0.1 work list

1. **Real GPU memory arena allocation.** `compute_units` in the manifest is bookkeeping only; the runtime tracks budget but does not carve out actual device memory. Production-grade per-process arenas need Sutra-runtime cooperation.
2. **GPU-tick-parallel scheduling.** v0.0 ticks services sequentially on CPU; production runs all admitted processes simultaneously on the GPU at each tick. The service abstraction is concurrency-agnostic, so this is a scheduler swap, not a service-side rewrite.
3. **`.su` service loading.** `kernel.services.load_su_service()` raises `NotImplementedError`; v0.0 services are `PythonService` subclasses. Wiring needs the convention-of-what-`.su`-services-export from the Sutra side. Seed `.su` source files (`kernel/services/{echo,sink}.su`) document the intended shape.
4. **Eviction to RAM cold-store** (per `planning/03-process-lifecycle.md`). Not implemented in v0.0; only admit/deregister.
5. **MMIO / interrupt / hardware-boundary path** (paper §3.5). Blocked on having hardware to develop against.
6. **A worked memory model** (`planning/17-memory-model.md`). Doesn't block first-prototype writing but bites at scale.

### Honest call

The kernel nucleus is real and tested. v0.1 is the hardening list above. The single most important Sutra-side investment that unblocks v0.1 is the multi-process Sutra runtime — without per-process GPU arenas and tick-parallel execution, the "no degradation under load" property remains aspirational.

## Browser — what we have, what we need

### What we have

- Async / `Promise<T>` in Sutra (event-driven UI is feasible).
- The TS transpiler's `lower.py` covering classes, methods, instance fields, arrays, discriminated unions, async/await — i.e., the JS-shape that real reactive frameworks produce after compilation. 17 passing fixtures.
- A WebGL plan in `planning/06-gui-stack.md` (not a runtime, but a plan).
- The `JavaScriptObject` runtime in Sutra for the untyped-JS fallback path.

### What we need to start writing

1. **A Sutra-native renderer** — at minimum a layout engine + display server pair that consumes axons describing the screen state and emits framebuffer-shaped axons. **Writable in pure Sutra today.** The GUI layer's tensor-op shape is exactly what Sutra is for; we do not need any transpiler to start.
2. **The TS transpiler's CLI wired up to `lower.py`.** Small task; not blocked. After this, `ts2su input.ts` is a command that exists.
3. **A minimal JS/TS web app, transpiled, running.** Something on the order of a "Hello world" reactive component that compiles through `ts2su → sutrac → executes`. Once this works, the browser layer is *demonstrably* viable, even at zero-features-beyond-hello-world.

### What we still don't have

- **HTML/CSS parser and layout.** Not in Sutra v0.3.1. Either we write a layout engine in Sutra (substantial) or we transpile a small one (e.g., a stripped-down Servo subset, but that depends on the C/Rust transpiler path which doesn't exist).
- **WebGL bindings.** The plan mentions WebGL; the implementation does not exist.
- **Network stack / `fetch` / `WebSocket`.** A minimum-viable fetch-shim is several weeks of work even with the language in place.

### Honest call

**Start writing the Sutra-native renderer now.** This is the part that does not depend on the TS transpiler being polished, and it is the part that is most novel — the layout engine that consumes axons and emits axons is the load-bearing demonstration that "everything is a browser" can be implemented at all. Defer the web-app-loading story until both the renderer and the TS transpiler CLI are ready. A v0.0 browser that displays a hand-written Sutra "page" before it can load any HTML is a perfectly defensible milestone.

## Cross-cutting recommendations

- **Wire up the TS transpiler CLI first thing.** Five-line task; unblocks all the other browser work and updates the public README's "skeleton" claim to match reality.
- **Don't promise the C-transpilation Linux story in v0.0.** The source is reserved under `external/`; the transpiler is genuinely not built. Yantra's first userspace will be hand-written Sutra (and TS-transpiled) for a long time.
- **The paper currently says "TS→Sutra is already running" (CLAUDE.md, paper §1.1, planning/07-transpilers.md).** This is *broadly* true (the lowering engine works) but skips the nuance that the CLI is unwired and the README is stale. Update CLAUDE.md and the planning docs to be accurate; the next paper revision can quote this readiness doc directly rather than the marketing tone.
- **The bottleneck is not the language; it is the multi-process Sutra runtime.** Until that lands, Yantra can demonstrate behaviour in the small (one process at a time, axon files passed between runs) but cannot claim its load-time properties. This is the single most important Sutra-side investment to track.

## Cross-references

- `paper/paper.md` § 8.2 milestones — high-level readiness, but written before this submodule audit; this doc supersedes for engineering planning.
- `planning/06-gui-stack.md` — what the GUI layer is supposed to look like.
- `planning/07-transpilers.md` — the transpiler section as written; needs updating now that we know the TS transpiler is real-but-unwired and the C transpiler is bare.
- `planning/17-memory-model.md` — the long-pole problem that does not block first writing but bites at scale.
- `external/Sutra/` — the actual code; read it, don't trust this summary alone.
