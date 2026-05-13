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

**This is on Yantra's critical path, not a nice-to-have.** Yantra
commits to "everything is a browser" for the GUI layer. That choice
only works if real JS/TS bundles compile to Sutra without a human
rewrite — otherwise the browser becomes an empty room and the
"looks like ChromeOS to your users" pitch (`12-target-markets.md`)
collapses. The TS→Sutra transpiler is one of two Sutra-side
dependencies Yantra rides on (the other being the Sutra compiler
itself; see `CLAUDE.md` § "Project context for paper/agent work").

It already exists and is running. The "what works" / "what is hard"
sections below are descriptions of the *current* state of that
transpiler, not aspirations.

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

The C transpiler exists, mostly to bring across pieces of Linux and
similar codebases. It is not idiomatic — C's pointer-and-mutation
worldview clashes with Sutra's value-and-relationship worldview — but it
works for well-scoped translations.

What we use it for:

- Bringing across kernel-adjacent code from Linux that is too well-tested
  to rewrite from scratch (block-device handling, common filesystem
  drivers, networking primitives).
- Bootstrapping the firmware-side bootloader (the small C program that
  loads the GPU image).
- Compiling WASM, which is in many ways a cleaner C: typed, no
  garbage collection in the base spec, designed to be lowered.

What we don't use it for:

- Userspace applications. Use JS/TS.
- Anything performance-sensitive on the hot path. The translated code is
  correct, not fast, and the abstractions don't always fuse nicely.

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
