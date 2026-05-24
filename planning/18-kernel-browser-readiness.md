# Readiness assessment — kernel and browser

> **What this document is.** An accurate accounting of what we have *now* versus what we need to actually start writing (a) the kernel and (b) the browser. Originally written 2026-05-13 vs Sutra v0.3.1.
>
> **Refreshed 2026-05-16** (autonomous loop) against the current submodule, **`external/Sutra` @ `v0.4.0-27-gdd448b47`** — every "v0.3.1" / "the multi-process runtime hasn't landed" / "TS CLI is an unwired skeleton" claim below was stale or internally contradictory and is corrected inline, each correction measured (test run / CLI run / `git describe`), not asserted. The original-tone paragraphs are kept where still true.
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

- **Kernel (Connectome Manager) — Sutra-running v0.0 shipped; Rust port pending.** The v0.0 runtime under `kernel/` is real and tested. **Sutra is doing the actual computation**: `SutraService` compiles `.su` source via the Sutra compiler (now `v0.4.0-27-gdd448b47`, not v0.3.1) at admission time and invokes the program's `on_axon(vector) -> vector` on real torch tensors carried through the router. `tests/test_kernel_sutra.py` admits real Sutra services and routes a payload producer → echo → sink end-to-end. The orchestration layer (init/resource-manager + router + capability check) is currently in Python; production form on the CPU side is Rust per `planning/01-architecture.md` § "CPU side: small, Rust, orchestrator." **48 tests collected across `tests/test_kernel.py` + `tests/test_kernel_sutra.py`** (measured 2026-05-16; the old "25 total" is stale). **Correction 2026-05-16:** the Sutra **multi-process runtime SHIPPED** (Sutra v0.4.0) — `kernel.make_shared_sutra_services` builds shared-`_VSA` services and `test_make_shared_sutra_services_share_one_vsa` + `test_shared_runtime_axon_passing_through_router` **pass** (measured this run). So "blocked on the multi-process Sutra runtime" is no longer true for the shared-runtime case. Still genuinely out of scope: real per-process GPU memory carve-outs, disc/RAM/GPU storage-tier moves (missing serialise-process-state / evict-from-GPU primitives), GPU-tick-parallel scheduling. **New caveat (this loop's measured finding):** per-receiver axon projection (`_VSA.axon_project`) is a **no-op for embedding fillers** — `bind(k,unbind(k,bundle))≈identity` under orthogonal rotation binding, so the "slimmed" payload still holographically carries every key (a receiver asking for one key decoded a projected-OUT key at +0.5726 vs kept +0.5999). So lazy axon eval delivers neither the bandwidth nor the capability-isolation property for the common case — see `planning/20-lazy-axon-evaluation.md` § Status; bears on `paper/paper.md` § 3.3.1.
- **Native userspace utilities (cat, ls, grep, awk, etc.) — second milestone, deferred.** Written natively in Sutra, not C-transpiled. `external/{coreutils,util-linux,busybox}` are behavioural reference, not transpile inputs. Blocked on Sutra's string + IO + FS vocabulary maturing and on the kernel `.su` loader landing.
- **Browser — third milestone, deferred.** "Every GUI component is a browser." HTML5 + CSS + idiomatic TS + WebGL/Three.js. WASM eventually but not for a long time (decision 2026-05-14). **The TS→Sutra transpiler ships as Sutra v0.3.2**: CLI works (`python -m sutra_from_ts in.ts -o out.su`), 17 fixtures pass through, `pip install sutra-dev[ts]` bundles it. Coverage isn't "every npm package compiles" — it's "the typed core works, edge constructs need new lowering rules as encountered." The Sutra-native renderer doesn't depend on the TS transpiler and could in principle start now, but is sequenced third per the user's plan.

## What Sutra actually ships

Pinned at `external/Sutra` @ **`v0.4.0-27-gdd448b47`** (refreshed 2026-05-16; was "commit 2582cd46, tag v0.3.1"). Direct read of the submodule:

### Working today

- **The Sutra compiler (`sutrac`).** Validate, `--emit` to self-contained PyTorch Python, `--run` end-to-end. Runs on Python 3.11+. Substrate-purity audit landed in v0.3.1 (the bug it fixed: complex `+`/`-`/`/` were silently host-Python instead of substrate-pure — bad enough that it warranted a same-day patch release).
- **Multi-program axon passing.** Two separately-compiled `.su` programs exchange a 5-key axon via a numpy `.npy` wire. **History:** this regressed (a compiler bug — `axon_item` string-key was `make_string`-coerced while the producer kept it a host str, so producer/consumer keyed on different role vectors → cross-module decode collapsed to ~0.04). Root-caused + fixed this loop (Sutra `eb0ce93e`); `examples/multi_program_axon/_run.py` is back to **PASS at +0.40 / margin +0.20** (measured, untuned). **This is the kernel-side IPC primitive**, shippable nucleus of the router — but note it round-trips the *full* bundle: lazy per-receiver slimming via `axon_project` is a no-op for embedding fillers (see the kernel TL;DR caveat + `planning/20-lazy-axon-evaluation.md`), so true bandwidth/isolation needs producer-side pruning, not the wire as-is.
- **Stdlib transcendentals — substrate-pure (after a real leak was found and fixed).** `Math.exp/log/sin/cos/tan/sinh/cosh/tanh/pow/sqrt` all native. **History (do not paper over):** the "interpolated lookup table, no host-Python fall-throughs" claim was *false* as of 2026-05-15 — `exp`/`log`/etc. did `float(x)` in, host `if`/`raise`, `float(...)` out (a substrate leak that had been labelled "substrate-pure" in a comment). Fixed in Sutra `21a9ff77`: one `_st()` host→substrate boundary, eigenrotation/`cexp` for trig, real `exp` = `cexp(x,0)` beta-reduced, out-of-range **saturates** (no host raise — the no-runtime-errors rule). Now genuinely substrate-pure; verified by `test_transcendentals` (20 subtests) at the time of the fix.
- **Modulus library.** `Math.mod` (eigen-rotation, ~10⁻⁷ max abs error), `Math.fmod` (truncation, JS/C semantics), the `%` operator now substrate-routed.
- **Async/await/`Promise<T>`** as first-class Sutra vocabulary, two-stage beta-reduction at compile time. This is a load-bearing enabler for the browser stack — async is the only sane way to do event-driven UI.

### TypeScript transpiler — shipped, CLI wired (corrected 2026-05-16)

- **TypeScript transpiler (`sdk/sutra-from-ts/`).** `lower.py` is real lowering: function declarations, type annotations, interface/type erasure, member access (`p.x` → `p.item("x")` for axon-typed `p`), JS-coercive `+` via `JavaScriptObject.add`, classes (fields + methods + static + constructors + `new`), discriminated unions, while/for/do-while loops, string concat, arrays, enums. 17 fixtures exercise it end-to-end. **The CLI is WIRED** — measured 2026-05-16: `python -m sutra_from_ts --help` prints the real `ts2su` argparse usage ("Transpile a typed core of TypeScript … into Sutra (.su) source", exit 0), shipped as Sutra v0.3.2 (2026-05-14). The earlier "CLI is still the skeleton not-yet-implemented stub, wiring it is a small task" text in this doc was stale and **contradicted its own TL;DR**; deleted. Real remaining work is TS-completeness (lowering rules for constructs the 17 fixtures don't cover), not CLI wiring.

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
- A working language (Sutra `v0.4.0-27-gdd448b47`) with multi-program axon passing demonstrated as a separate primitive in `external/Sutra/examples/multi_program_axon/` (regression-fixed + verified this loop — see above).
- A compile-to-CUDA path (Sutra ships `compile_to_cuda.py`) so the kernel runs on real GPUs eventually, not only the PyTorch reference.
- Async / `Promise<T>` for event-driven scheduling primitives.
- All seventeen planning docs defining the kernel's intended behaviour.

### What's stubbed in v0.0 — the v0.1 work list

1. **Real GPU memory arena allocation.** `compute_units` in the manifest is bookkeeping only; the runtime tracks budget but does not carve out actual device memory. Production-grade per-process arenas need Sutra-runtime cooperation.
2. **GPU-tick-parallel scheduling.** v0.0 ticks services sequentially on CPU; production runs all admitted processes simultaneously on the GPU at each tick. The service abstraction is concurrency-agnostic, so this is a scheduler swap, not a service-side rewrite.
3. ~~**`.su` service loading.**~~ **Works — corrected 2026-05-16.** The old claim ("`kernel.services.load_su_service()` raises `NotImplementedError`; v0.0 services are `PythonService` subclasses") was false on both counts: `load_su_service` is defined nowhere (measured — absent on `kernel`/`kernel.services`), and real `.su` services load + run via `SutraService(source_path=…, output_role=…)` (compiles the `.su`, runs `on_axon(vector)->vector`, consumes `AXON_KEYS_BOUND/READ` static analysis). The `kernel/services/{echo,sink}.su` seeds are *used*, not just documentation, and many `tests/test_kernel_sutra.py` tests admit real `.su` services. The "convention from the Sutra side" the old text waited on shipped (it's in `SutraService`'s docstring). The genuine remaining work is the *Rust* orchestrator's own `.su` loader, not a missing Python stub — drop from the Python v0.1 list.
4. ~~**Eviction to RAM cold-store.**~~ **Partly done — corrected 2026-05-17.** The old "not implemented; only admit/deregister" is stale. `Init.load`/`unload` now instantiate / tear down a program's CUDA-resident Sutra runtime with GPU memory genuinely reclaimed on the real RTX 4070 (measured 669696→0→669696 B; `tests/test_kernel_gpu_tiers.py`). So **eviction *from the GPU* is done**; what remains is preserving a *running* program's mutated state across the eviction (checkpoint + bit-exact resume), which genuinely needs the Sutra `serialise-process-state` primitive (does not exist). Start/stop-on-GPU: done. Pause-resume-preserving-state: open.
5. **MMIO / interrupt / hardware-boundary path** (paper §3.5). Blocked on having hardware to develop against.
6. **A worked memory model** (`planning/17-memory-model.md`). Doesn't block first-prototype writing but bites at scale.

### Assessment

The kernel nucleus is real and tested. v0.1 is the hardening list above. **Correction 2026-05-16:** the multi-process Sutra runtime *itself* shipped (Sutra v0.4.0; shared-`_VSA` services + router axon-passing tests pass — measured). **Correction 2026-05-17:** DISC↔GPU load/unload (item 4's GPU half) now works on a real GPU (RTX 4070, measured). What remains for the "no degradation under load" property is the *specific* slice still missing: per-process GPU memory arenas and GPU-tick-parallel execution (items 1–2), plus the *state-preserving* half of eviction (RAM cold-store of running state — needs Sutra `serialise-process-state`). Those are now the long pole, not "the runtime hasn't landed" and not "no GPU".

## Browser — what we have, what we need

### What we have

- Async / `Promise<T>` in Sutra (event-driven UI is feasible).
- The TS transpiler's `lower.py` covering classes, methods, instance fields, arrays, discriminated unions, async/await — i.e., the JS-shape that real reactive frameworks produce after compilation. 17 passing fixtures.
- A WebGL plan in `planning/06-gui-stack.md` (not a runtime, but a plan).
- The `JavaScriptObject` runtime in Sutra for the untyped-JS fallback path.

### What we need to start writing

1. **A Sutra-native renderer** — at minimum a layout engine + display server pair that consumes axons describing the screen state and emits framebuffer-shaped axons. **Writable in pure Sutra today.** The GUI layer's tensor-op shape is exactly what Sutra is for; we do not need any transpiler to start.
2. ~~**The TS transpiler's CLI wired up to `lower.py`.**~~ **Done** (Sutra v0.3.2; `ts2su` works — measured 2026-05-16). No longer a prerequisite.
3. **A minimal JS/TS web app, transpiled, running.** Something on the order of a "Hello world" reactive component that compiles through `ts2su → sutrac → executes`. The CLI exists now, so this is the actual next browser-track step (gated only by the build sequence — milestone 3, after kernel + CLI utilities).

### What we still don't have

- **HTML/CSS parser and layout.** Not in Sutra at all (any version). Either we write a layout engine in Sutra (substantial) or we transpile a small one (e.g., a stripped-down Servo subset, but that depends on the C/Rust transpiler path which doesn't exist).
- **WebGL bindings.** The plan mentions WebGL; the implementation does not exist.
- **Network stack / `fetch` / `WebSocket`.** A minimum-viable fetch-shim is several weeks of work even with the language in place.

### Assessment

**Start writing the Sutra-native renderer now.** This is the part that does not depend on the TS transpiler being polished, and it is the part that is most novel — the layout engine that consumes axons and emits axons is the load-bearing demonstration that "everything is a browser" can be implemented at all. Defer the web-app-loading story until both the renderer and the TS transpiler CLI are ready. A v0.0 browser that displays a hand-written Sutra "page" before it can load any HTML is a perfectly defensible milestone.

## Cross-cutting recommendations

- ~~**Wire up the TS transpiler CLI first thing.**~~ **Done** (Sutra v0.3.2). `ts2su` is a working command (measured 2026-05-16). This recommendation is retired.
- **Don't promise the C-transpilation Linux story in v0.0.** The source is reserved under `external/`; the transpiler is genuinely not built (~57 lines, no `lower.py`). Yantra's first userspace will be hand-written Sutra (and TS-transpiled) for a long time. *(This one is still true.)*
- **TS→Sutra is genuinely running, CLI included.** Earlier this doc and the paper hedged on "the CLI is unwired" — that nuance is now obsolete (CLI shipped v0.3.2). The accurate statement: the lowering engine + CLI work; TS-*completeness* (rules for constructs beyond the 17 fixtures) is the open edge, not CLI wiring. Keep CLAUDE.md / `planning/07-transpilers.md` matching this.
- **The bottleneck is not the language, and not "the multi-process runtime hasn't landed" — it landed (Sutra v0.4.0, measured).** The real long pole is now the *specific* GPU-side slice: per-process memory arenas + tick-parallel execution + storage-tier eviction. Plus the newly-measured caveat that `axon_project` doesn't actually slim embedding-filler axons (no lazy-eval bandwidth/isolation for the common case) — a Sutra-side design problem (`planning/20-lazy-axon-evaluation.md` § Status).

## Cross-references

- `paper/paper.md` § 8.2 milestones — high-level readiness, but written before this submodule audit; this doc supersedes for engineering planning.
- `planning/06-gui-stack.md` — what the GUI layer is supposed to look like.
- `planning/07-transpilers.md` — the transpiler section as written; the TS transpiler is real **and CLI-wired** (Sutra v0.3.2), the C transpiler is genuinely bare (~57 lines). Keep that doc matching this.
- `planning/17-memory-model.md` — the long-pole problem that does not block first writing but bites at scale.
- `external/Sutra/` — the actual code; read it, don't trust this summary alone.
