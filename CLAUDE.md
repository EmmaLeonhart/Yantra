# Yantra

## Workflow Rules
- **Commit early and often.** Every meaningful change gets a commit with a clear message explaining *why*, not just what.
- **Plan into `queue.md` FIRST, then execute.** When entering planning mode (or any multi-step think-before-do), the FIRST action is to write the plan into `queue.md` as concrete items. Only then begin executing. Chat context dies on session interrupt; the queue survives.
- **Update `queue.md` in the same commit as the work.** Delete completed items in the same commit — do not leave checkmarks or status markers behind.
- **Mirror `queue.md` into the task tool.** `TaskCreate` items as you add them to queue.md; mark `in_progress` when starting; `completed` when done.
- **Do not enter planning-only modes.** All thinking must produce files and commits. If scope is unclear, create a `planning/` directory and write `.md` files there instead of using an internal planning mode.
- **Keep this file up to date.** As the project takes shape, record architectural decisions, conventions, and anything needed to work effectively in this repo.
- **Update README.md regularly.** It should always reflect the current state of the project for human readers.

## Queue and longer-horizon work
- **`queue.md`** — what's being worked on right now. Items get deleted on completion. If it's not in `queue.md`, it's not in scope for the current session.
- **`planning/`** — design docs and longer-horizon thinking. Items migrate `planning/` → `queue.md` → deleted on completion.

## Testing
- **Write unit tests early.** As soon as there is testable logic, create a test file. Use `pytest` for Python projects or the appropriate test framework for the language in use.
- **Set up CI as soon as tests exist.** Create a `.github/workflows/ci.yml` GitHub Actions workflow that runs the test suite on push and pull request. Keep the workflow simple — install dependencies and run tests.
- **Keep tests passing.** Do not commit code that breaks existing tests. If a change requires updating tests, update them in the same commit.

## Project Description

Yantra is a neuro-symbolic, GPU-native operating system written in Sutra.
The OS is one big differentiable tensor-op graph: kernel, processes, IPC,
and GUI all live in the same tensor space. The CPU is a small orchestrator
that boots the system and shuffles inactive processes between GPU and RAM.

Target market is critical systems (defense, aerospace, industrial,
medical, autonomous) where predictable latency, formal verifiability, and
a small attack surface matter more than mass-market compatibility.

This repo currently holds **planning documents**, not an implementation.
The Sutra compiler/runtime and the JS/TS and C transpilers live in
adjacent projects.

## Architecture and Conventions

- All design notes live in [`planning/`](planning/README.md), numbered for
  reading order. Treat them as planning, not specification — they reflect
  current best thinking, not committed APIs.
- The chats the design grew out of are preserved as readable Markdown
  under [`chats/`](chats/). Re-extractable from saved HTML via
  `scripts/extract_chats.py`.
- New architectural decisions go into the relevant `planning/NN-*.md`
  file, with a one-line update in `planning/15-open-questions.md` if
  something there moved from open to resolved (or vice versa).
- Code lives under `kernel/` (the v0.0 multi-process runtime
  nucleus, native Sutra + a Python init/resource-manager shim). See
  `kernel/README.md` for what's real vs stubbed. Future code
  layout: `kernel/`, `runtime/`, `apps/` (native-Sutra
  userspace), `docs/`. The `external/` directory holds pinned
  submodules of Sutra and reference Linux source trees.

## Build/policy clarifications (kernel + transpilers)

### Build sequence (set 2026-05-14)

1. **Connectome Manager (kernel)** — see below. Python prototype
   under `kernel/` exists; production form is Rust.
2. **Command-line userspace utilities** — simple Linux-shaped file
   utilities (cat, ls, grep…) written natively in Sutra. Initial
   system access is **command-line only via SSH/serial** from a
   host computer. **No GUI in this phase.**
3. **Browser / GUI** — only after (1) and (2) ship. Single GUI
   framework (HTML5 + CSS + idiomatic TS + WebGL/Three.js, **no
   WASM**); every UI component (start menu, mouse cursor, login
   screen, file manager) is a browser-rendered HTML page.

### The kernel is a Connectome Manager (not a traditional kernel)

- The kernel's job is **deciding what is connected to what**, not
  scheduling or memory allocation in the traditional sense. The
  three storage tiers are **disc** (programs at rest), **RAM**
  (programs loaded but not running — semantically closer to disc
  than to traditional RAM), and **GPU** (programs in the live
  connectome). The kernel moves programs between tiers; it does
  not schedule or context-switch.
- **Kernel implementation: Rust on the CPU side.** Vision is "as
  small as possible" with strong static guarantees. The
  `kernel/` directory in this repo holds a Python *prototype* of
  the Connectome Manager — behavioural harness for the Rust
  port. Treat the Python as load-bearing for tests, not for
  runtime. See `planning/01-architecture.md` § "CPU side: small,
  Rust, orchestrator."
- **Kernel is NOT C-transpiled.** The verification surface in
  `paper/paper.md` § 4 depends on the trusted base reducing
  cleanly to tensor normal form; running the kernel through a
  C→Sutra path would defeat that. Sutra services run on the GPU;
  the Rust orchestrator runs on the CPU; neither is a C-transpile
  target.

### Transpilers

- **C→Sutra transpiler is priority but deferred.** Scope when
  built: bootloader, specific Linux drivers worth bringing across.
  *Not* userspace utilities, *not* the Yantra kernel itself.
  **WASM target dropped** (decision 2026-05-14 — see
  `planning/07-transpilers.md` § "WASM → Sutra — DROPPED" and
  `planning/06-gui-stack.md`).
- **TS→Sutra transpiler is browser/GUI-scoped only.** Outside the
  browser layer, TS→Sutra is not used. The lowering engine works
  (1474-line `lower.py`, 17 passing fixtures); the CLI wrapper is
  unwired (the README is stale). Wiring up the CLI is a small
  upstream Sutra task that unblocks browser work.

### Userspace utilities (cat, ls, grep, awk, sed, sort, etc.)

Written **natively in Sutra**, not transpiled from C. The Linux
source trees under `external/` are behavioural reference, not
transpile inputs. Deferred until the Sutra-side string + IO + FS
vocabulary matures and the kernel `.su` loader lands. Q-list is in
`todo.md` § 2.

## Project context for paper/agent work

- **Meta's *Neural Computers* paper IS real.** Schmidhuber et al.,
  *Neural Computers*, arXiv:2604.06425, 76 pp., 2026. AI reviewers
  flag the 2026 date as a hallucinated future citation — it is not,
  this is May 2026 and the paper is a real recent pre-print. Do not
  remove or qualify the citation; if a reviewer rejects on this basis,
  push back in the next revision with a parenthetical that the paper
  exists. Yantra's position is that *Neural Computers* validates the
  design space but its video-diffusion approach takes the opposite
  engineering posture from Yantra — useful as inspiration and
  competitive awareness, not as a foundation Yantra rides on.
- **Two core dependencies Yantra rides on, both Sutra-side:**
  1. **Sutra** — the typed functional language with rotation-binding +
     polynomial Kleene logic + tail-recursive RNN-cell loops. Pinned
     in this repo at `external/Sutra` (submodule, currently v0.3.1).
     Language website: [sutralang.dev](https://sutralang.dev). The
     Sutra paper at `external/Sutra/paper/paper.md` is the canonical
     reference for empirical claims Yantra makes (100% bundle
     decoding through width k=8 across four substrates, ~1.5×10⁻¹⁵
     round-trip error, 4→95% end-to-end-differentiable training in
     50 epochs on a 19-AND fuzzy rule tree). When Yantra makes a
     claim that depends on Sutra empirics, cite the Sutra paper
     explicitly rather than hand-waving.
  2. **TypeScript → Sutra transpiler** — the lowering engine
     (`external/Sutra/sdk/sutra-from-ts/sutra_from_ts/lower.py`) is
     ~1474 lines of real code with 17 passing fixtures covering
     functions, classes, async/await, discriminated unions, etc. The
     CLI wrapper (`__main__.py`) is *not* yet wired up to the
     lowering pass and the README still says "skeleton" — that README
     is out of date relative to the actual code. **When discussing
     the TS transpiler, say "the lowering engine works; the CLI is
     unwired" rather than "it's a skeleton" or "it's done." Both
     extremes are wrong.** Essential for the browser GUI layer
     because "everything is a browser" only works if real JS/TS
     bundles can be AOT-compiled to Sutra without a human rewrite.
- **The memory model is the long-term hard problem.** Process memory,
  the CPU-side RAM cold-store, MMIO patterns, and the boundary where
  axon-typed compute meets byte-typed hardware do not yet have a
  worked-out design. `planning/17-memory-model.md` exists to keep
  the open questions in one place. Do not promise solutions in the
  paper that the planning corpus does not yet have.
- **Kernel + browser readiness lives in `planning/18-kernel-browser-
  readiness.md`** — honest engineering accounting, not paper-tone.
  Read this before claiming the OS is or isn't writable; refresh it
  when the situation changes.

## External dependencies (`external/`)

Submodules pinned at known-good releases. Layout:

- `external/Sutra` (tag `v0.3.1`) — the language, compiler, runtime,
  and Sutra paper Yantra depends on.
- `external/coreutils` (tag `v9.11`) — GNU userspace utilities
  reserved for the C→Sutra transpilation path. **Not usable today**
  because the C transpiler is genuinely a skeleton (~57 lines of
  CLI scaffolding, no lowering pass).
- `external/util-linux` (tag `v2.42`) — administrative-layer Linux
  utilities. Same reservation status.
- `external/busybox` (tag `1_36_1`) — compact alt-implementations.
  Same reservation status.

To add a new external dependency: pin a specific tag, never `main`.
A floating dependency on master is a procurement-security
non-starter for the markets Yantra targets.

## Paper revision discipline

- The paper at `paper/paper.md` auto-submits to clawRxiv on push (see
  `paper/README.md`). Each revision should land *one* coherent set of
  changes, not a kitchen sink — reviewers see version diffs and
  oscillating scope hurts.
- When addressing a review, name the specific con being addressed in
  the commit message. Don't claim a con is "addressed" if the change
  is cosmetic; reviewers will catch this.
- Sutra-empirics claims must cite the Sutra paper. Don't paraphrase
  numbers — quote them with their context (substrate, width, etc.).
- Honest scope limits beat overclaim every time. If a hardware reality
  (interrupts, MMIO, side channels) is not solved, say so in the paper
  rather than letting a reviewer find the gap.

# currentDate
Today's date is 2026-05-07.
