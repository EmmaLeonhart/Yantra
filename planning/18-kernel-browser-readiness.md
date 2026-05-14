# Readiness assessment — kernel and browser

> **What this document is.** An honest accounting of what we have *now* (Sutra v0.3.1 + the imported Linux source under `external/`) versus what we need to actually start writing (a) the kernel and (b) the browser. Written 2026-05-13 from a direct read of the Sutra v0.3.1 submodule and the v0.3.0 release notes, not from the marketing tone of `paper/paper.md`.
>
> **What this document is not.** A roadmap commitment. The "should we start" calls at the end are recommendations; the user picks.

## TL;DR

- **Kernel** — we *can* start writing it now. The Sutra language, compiler, and runtime are real; multi-program axon passing is demonstrated; the kernel does not depend on any C transpilation. The hard parts are hard regardless of when we start, but there is no language-side blocker.
- **Browser** — we *can* start writing the Sutra-side renderer (display server, layout engine, input router) now. The "everything is a browser" GUI claim further depends on the TS→Sutra transpiler, which is **mostly real** (a 1474-line `lower.py` with 17 passing fixtures) but its CLI is not wired up and the README still says "skeleton." Workable today; not yet a one-line `ts2su file.ts` command.
- **Importing Linux userspace** (coreutils, util-linux, busybox) — gated on the C→Sutra transpiler, which is **genuinely a skeleton today** (~57 lines of CLI scaffolding, no `lower.py`). The source is in place under `external/`; the tool to consume it is not.

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

### What we have

- A working language (Sutra v0.3.1) with axon-passing across processes (the v0.3.0 multi-program demonstration is the kernel's IPC nucleus).
- A compile-to-CUDA path so the kernel runs on real GPUs, not only the PyTorch reference.
- Async / `Promise<T>` for event-driven scheduling primitives.
- All sixteen+ planning docs that define the kernel's intended behaviour (process table, axon router, capability check, FS bridge, resource manager).

### What we need to start writing

In rough order:

1. **The kernel program** — a Sutra `.su` source tree under (proposed) `kernel/` that implements the process table, axon router, and capability check. **Writable in pure Sutra today.** No external blockers.
2. **A minimal CPU-side init shim** — small C or Python program that loads the compiled kernel image onto the GPU and bootstraps it. **Writable today** — we can use Python with PyTorch as the bootloader for a v0.1 prototype before worrying about a real bootloader.
3. **A test harness** — a way to load N processes, route axons between them, and verify the capability checks fire. The v0.3.0 multi-program axon-passing demo is the seed of this.

### What we still don't have

- **The fixed-allocation primitives in the runtime.** The Sutra runtime today executes one program at a time on a GPU; the multi-program demo passes axons between *separately-invoked* runs. The multi-process-on-one-GPU-with-pre-allocated-arenas runtime that Yantra's "no degradation under load" property depends on is a substantial new piece of runtime work, not a kernel-side write.
- **The MMIO / interrupt / hardware-boundary path** (paper §3.5). Not blocked on Sutra; blocked on having actual hardware to develop against and on writing the CPU-side wrapper-driver pattern.
- **A worked memory model** (`planning/17-memory-model.md`). Doesn't block first-prototype writing but bites the moment a process needs more state than the synthetic-dimension block.

### Honest call

**Start writing the kernel now.** The bottom-up demo path: kernel `.su` source → compile through `sutrac` → run the multi-program axon-passing harness with the kernel as one of the programs and a smoke-test "userspace" as another. This produces something runnable in days-to-weeks rather than waiting for the full runtime to land. Treat it as a v0.0 — many of the "predictable performance" claims will not be measurable until the multi-process runtime exists, but the *behavioural* shape of the kernel can be exercised today.

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
