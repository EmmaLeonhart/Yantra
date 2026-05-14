# Transpilers

Yantra leans on transpilation hard. The language story is not "rewrite
the world in Sutra"; it is "compile what already exists into Sutra well
enough that you don't have to rewrite the world."

Three transpilers are in scope:

1. **JS / TS → Sutra** — userspace, GUI, applications.
2. **C → Sutra** — kernel bootstrap pieces, drivers we adapt from Linux.
3. **WASM → Sutra** — best-effort, falls out of the C transpiler since
   WASM is a cleaner IR than raw C.

## JS / TS → Sutra

**Scope: browser/GUI specifically.** TS→Sutra is on the critical
path *for the browser layer* — Yantra commits to "everything is a
browser" for the GUI, and that choice only works if real JS/TS
bundles compile to Sutra without a human rewrite. Outside the
browser layer, TS→Sutra is not used: the kernel is native Sutra,
userspace utilities are native Sutra rewrites, and there is no
general-purpose "JS apps run on Yantra" promise.

Status: the lowering engine
(`external/Sutra/sdk/sutra-from-ts/sutra_from_ts/lower.py`) is
~1474 lines of real code with 17 passing fixtures covering
functions, classes, async/await, discriminated unions, etc. The
CLI wrapper is unwired and the README still says "skeleton" — both
out of date relative to the actual code. **Status as of this
writing: lowering engine works; CLI is unwired; README is stale.
Both extremes ("done" or "skeleton") are wrong.** Wiring up the
CLI is a small task on the Sutra side that unblocks all browser
layer work.

What it does well:

- Closures, higher-order functions, immutable patterns — these compile
  cleanly because they are already close to Sutra's functional core.
- Reactive UI frameworks (React-style components, Solid-style signals,
  Svelte-style stores) — these push JS toward the dataflow shape Sutra
  wants. Idiomatic React-ish code compiles surprisingly well.
- Tail-recursive loops, when written that way, lower directly to Sutra's
  soft-halt RNN cells.

What is hard, and where we have to impose conventions:

- **Mutation.** `obj.prop = x` is technically legal but semantically a
  mess in a fixed-state model. The transpiler treats it as SSA (every
  assignment is a fresh name) and threads the new value through the
  rest of the function.
- **Async / promises / event listeners.** These dissolve into axon
  channels: an event listener is a process that consumes an axon stream
  from the input router; a promise is a "wait until this role is
  bound" pattern. The translation works, but the patterns idiomatic JS
  programmers reach for sometimes need a small re-shape.
- **Dynamic object shapes.** Objects whose shape changes at runtime are
  hostile to a fixed-width state model. The transpiler refuses them and
  emits a clear error. TS programs avoid this naturally; pure JS
  programs sometimes need to be cleaned up.
- **`eval`, `new Function`, runtime `import()` of remote URLs.** Refused.
  Documented limitation.

### The "flow object" pruning pass

A real wart that surfaced in practice: tail-recursive loops, after
SSA-ification, generate "flow objects" that carry the loop's free
variables across iterations. The naive lowering captures everything in
scope, including variables that are never read on the next iteration.
That bloats GPU memory and degrades crosstalk margins.

The transpiler needs a liveness pass that, for each loop, computes the
set of variables actually consumed on the next iteration and trims the
flow object down to that set. This is straightforward static analysis
but the current transpiler does not do it well enough yet.

### What ships in the minimal viable subset

To get a usable userspace fast, we draw a line at:

- ES2017-style core (let/const, classes, async/await, spread, destructure)
- TS structural types (narrowed enough that the transpiler can statically
  size axons)
- Reactive primitives that the runtime understands natively (a small
  signals library, similar in spirit to Solid)
- The `fetch` / `WebSocket` / DOM subset documented in `06-gui-stack.md`

Anything beyond this still works if it does, but is not promised.

## C → Sutra

**Status: priority but deferred.** The C transpiler is genuinely a
skeleton today (`external/Sutra/sdk/sutra-from-c/` is ~57 lines of
CLI scaffolding with no lowering pass). It will be built; it is not
v0.0 work.

**Scope when it lands.** Strictly kernel-adjacent C — bootloader,
specific drivers we want to bring across from Linux for well-tested
behaviour, possibly WASM via the C-like IR path. **Userspace is NOT
a target for C-transpile.** The Linux userspace utility sources
under `external/{coreutils,util-linux,busybox}/` are reference
material — useful for "what does GNU `sort` actually do at the
edge" — not transpile inputs. Yantra userspace utilities will be
written natively in Sutra (see `apps/`-shaped work in `todo.md`).

**The kernel itself is NOT C-transpiled.** Yantra's kernel
(`kernel/` in this repo) is native Sutra. C-transpiling would
defeat the verification surface argument in `paper/paper.md` § 4 —
the whole point is that the trusted base reduces to tensor normal
form, which C-transpiled code does not cleanly do.

What the C transpiler IS for, when built:

- Bootstrapping the firmware-side bootloader (small, finite, the
  one place we want a known-good C origin).
- Bringing across specific Linux drivers where the code is
  well-tested and idiomatic re-writing is wasteful (block-device
  handling, common filesystem drivers, networking primitives).
- WASM via the same backend (a cleaner C-shaped IR).

What it is NOT for:

- The kernel — written natively in Sutra.
- Userspace applications and utilities — native Sutra rewrites.
- Browser GUI — that is the TS→Sutra transpiler's job.
- Anything performance-sensitive on the hot path. Translated code
  is correct, not fast.

### The memory model gap

C's mutable memory + pointers does not map cleanly onto Sutra's
fixed-width state. The transpiler does its best, but practically:

- Loops in C tend to write into pre-allocated buffers. The transpiler
  has to reify these as either bounded streams or (when the size is
  known statically) as fixed-length axons.
- Pointers as identity (e.g., `*p == *q`) survive by treating pointers
  as opaque tokens that can be compared but not dereferenced
  arbitrarily.
- Dynamic allocation (`malloc`/`free`) is what you must avoid in
  transpiled C. Code that uses arenas or pre-sized buffers translates
  cleanly; code that depends heavily on `malloc` is a bad candidate.

Practically, this means we curate which Linux components we transpile,
and we do small adjustments to the C source first to make it more
buffer-oriented and less heap-oriented.

## WASM → Sutra

WASM falls out of the C transpiler mostly for free. WASM is:

- Already a low-level IR.
- Strongly typed.
- No garbage collection in the base spec.
- Designed to be compiled to, not interpreted.

So `WASM → Sutra` is really `WASM → C-like IR → Sutra` and the second
half is the existing C path. The result is a usable WASM runtime good
enough for things like Figma to load, even if performance and edge-case
fidelity are not what they would be on V8.

Treating WASM as a first-class compilation target means the Yantra
browser can run a wide swathe of "real" web apps (anything that ships a
WASM bundle) without us writing app-specific transpilers for each one.

## What we do *not* transpile

- The Sutra compiler itself.
- The runtime.
- The kernel (it's written directly in Sutra).
- Userspace utilities we author from scratch (file manager, settings,
  terminal-as-HTML, etc.).

Transpilation is the on-ramp, not the destination.

## Open questions

- **Source maps.** Debugging a transpiled program by reading the Sutra
  intermediate is awful. We need source maps that survive transpilation
  + Sutra compilation, so the GUI debugger can show JS line numbers.
- **Incremental transpilation.** AOT compile-on-page-load means an app
  install can take a while. A cache that survives across launches and
  invalidates on the bundle hash should pay for itself quickly.
- **Coverage of the JS standard library.** We don't have to support
  every weird `Array.prototype` method, but we have to support enough
  that real frameworks work. The current coverage is adequate for
  reactive UI but spotty on the data-manipulation side.
