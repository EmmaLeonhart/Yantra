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
- **Kernel implementation.** The `kernel/` directory in this repo
  is the v0.0 Connectome Manager. **Sutra is doing the
  computation** — `SutraService` compiles `.su` source via the
  Sutra v0.4.0 compiler and runs `on_axon(vector) -> vector` on
  real torch tensors routed through the kernel. The
  **orchestration layer** (init/resource-manager + axon router +
  capability check) is in Python here; the production form on the
  CPU side is **Rust** per `planning/01-architecture.md` § "CPU
  side: small, Rust, orchestrator." When updating Yantra-side
  kernel code today, edit the Python and write `.su` files;
  treat the Python as the API-shape pin the eventual Rust
  reimplementation must match.
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
  **WASM target deferred — eventually in scope but not now and not
  for a long time** (decision 2026-05-14; not a v0 target, not a
  v0.1 target, not on any near-term roadmap). See
  `planning/07-transpilers.md` and `planning/06-gui-stack.md`.
- **TS→Sutra transpiler is browser/GUI-scoped only.** Outside the
  browser layer, TS→Sutra is not used. **Shipped as Sutra v0.3.2**
  (released 2026-05-14): CLI works, 17 fixtures pass, `pip install
  sutra-dev[ts]` bundles it. Coverage caveat: typed core works,
  but TS-completeness is not a solved problem — real-world bundles
  may need new lowering rules. Foundation, not finished feature.

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
     in this repo at `external/Sutra` (submodule, currently v0.4.0).
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

## Cross-repo workflow (Yantra ↔ Sutra)

**This is atypical, but it's the right shape for these two projects
because they are tightly coupled.** Yantra and Sutra are not really
independent codebases — Yantra is "the OS that uses Sutra"; Sutra is
"the language Yantra is built in." A change to one frequently
requires a change to the other in the same session.

### Division of responsibility

- **Yantra (this repo) — actual kernel orchestration, runtime
  shape, OS-level concerns.** What goes in `kernel/`, the
  Connectome Manager design, the eventual Rust orchestrator,
  storage-tier moves, capability check architecture, the FS
  bridge, the GUI/browser stack, the paper.
- **Sutra (`external/Sutra` submodule) — connecting things
  together at the language level, debugging the language,
  language-side primitives Yantra needs.** What goes in
  `sdk/sutra-compiler/`, `sdk/sutra-from-ts/`,
  `sdk/sutra-from-c/`, the compiler, the lowering passes, the
  axon spec, the multi-process runtime, the
  serialise-process-state primitive, the runtime ABI Yantra
  consumes.

When working in this repo and a Sutra-side change is needed, do
**not** treat that as someone else's problem. The submodule is a
real git checkout you have push access to. Edit it, commit on
Sutra master, push, tag a release, bump the submodule pointer
here.

### The mechanics

```bash
# 1. Move into the submodule, get on master.
cd external/Sutra
git checkout master
git pull origin master --ff-only

# 2. Edit Sutra-side files. (The Sutra repo has its own CLAUDE.md
#    with its own workflow rules — read it first; in particular,
#    Sutra requires plan-into-queue.md and commit + push immediately
#    rather than batching local commits.)

# 3. Commit + push on Sutra master.
git add ...
git commit -m "..."
git push origin master

# 4. (If the change is meaningful) tag a release.
git tag -a vX.Y.Z -m "..."
git push origin vX.Y.Z
gh release create vX.Y.Z --repo EmmaLeonhart/Sutra ...

# 5. Pin the submodule at the tag.
git checkout vX.Y.Z

# 6. Back in Yantra: bump the submodule pointer + commit + push.
cd ../..
git add external/Sutra
git commit -m "Bump Sutra submodule to vX.Y.Z — <reason>"
git push origin master
```

### When NOT to do this

- Don't make a Sutra-side change just because Yantra-side code is
  awkward. Sutra has its own audience (the language's users beyond
  Yantra) and its own NeurIPS-paper code-durability constraint.
  If a Yantra workaround is possible, prefer it.
- Don't tag a Sutra release for a docs-only fix unless something
  in Yantra needs to depend on a specific Sutra version that
  carries the doc. A submodule pointer bump to master HEAD is
  enough for non-release-shaped changes.
- Don't edit anything under `external/Sutra/paper/neurips/` —
  that's Sutra's frozen NeurIPS submission archive (per Sutra's
  CLAUDE.md). If a Yantra change makes the Sutra paper claims look
  shaky, surface that to the user, don't silently amend the frozen
  copy.

### Read the Sutra CLAUDE.md before editing the submodule

`external/Sutra/CLAUDE.md` has rules that are stricter than
Yantra's in places — notably, Sutra is biomedical-hardware-adjacent
("PEOPLE CAN DIE IF YOU FAKE RESULTS") with hard rules about
substrate purity (no Python shortcuts inside Sutra operations, no
numpy on the runtime hot path, every operation runs on the
substrate). When editing Sutra source, those rules bind. When
editing Sutra docs / pyproject / CLI scaffolding, they don't, but
the workflow rules (commit + push immediately, plan into Sutra's
own queue.md, mirror to task tool) still apply.

## Honesty rules (added 2026-05-14)

Two rules added after the user pointed out the docs were papering
over difficulty:

### Python is dev tooling, not runtime

- **No Python in the boot path.** The bootloader is Rust (or C);
  there is no interpreter at boot. See
  `planning/19-boot-sequence.md` § "Stage 3" for the long version.
  A Python "bootloader" is a category error — there is nothing for
  the interpreter to run on.
- **No Python features in `kernel/` that wouldn't port cleanly to
  Rust.** The Python in `kernel/` is the behavioural reference for
  the eventual Rust orchestrator. Decorators that do nontrivial
  work, `__getattr__` magic, dynamic monkey-patching, runtime
  type-juggling (e.g. `isinstance` switches that change behaviour),
  metaclass tricks — none of these belong in `kernel/`. If the
  Python is doing something the Rust port can't naturally do, the
  Python is wrong.
- **The Rust port is the production target.** Treat the Python as
  load-bearing for tests, not for runtime. When in doubt, ask:
  "would this compile to a clean Rust translation?" If the answer
  is "you'd have to redesign," don't add it.

### Don't paper over difficulty

When something is hard or unbuilt, name it. Specific things that
are hard, that are not yet built, and that should be called out
plainly when they come up rather than waved past:

- **The bootloader.** Doesn't exist. Rust target. Has to deal with
  bare-metal CPU + GPU initialization, BIOS/UEFI handoff,
  loading the compiled Sutra image into GPU memory.
- **The Rust orchestrator.** Doesn't exist. The Python in
  `kernel/` is a behavioural reference for what its API surface
  should look like, not a "smaller version" of it.
- **Lazy axon evaluation.** Without it, the connectome bandwidth
  is O(N²·D) and collapses under its own weight. See
  `planning/20-lazy-axon-evaluation.md`. The kernel/router.py in
  this repo implements the skip-uninterested-receivers slice of
  this; full per-receiver projection is upstream-Sutra-dependent.
- **The multi-threaded Sutra runtime.** Upstream Sutra-side work,
  not shipped yet. Without it, the orchestrator can't actually
  run all admitted programs simultaneously on a single GPU.
- **Disc ↔ RAM ↔ GPU storage-tier moves.** The Connectome
  Manager's primary job. Not implemented. Blocked on Sutra-side
  primitives (serialise-process-state, evict-from-GPU) that
  don't yet exist.
- **GPU memory carve-outs per process.** Bookkeeping only in the
  Python prototype. Real per-process arenas need the multi-process
  Sutra runtime.
- **Boot-time hardware discovery (PCI scan, GPU init, MMIO
  setup).** Bootloader-stage work. None of it exists.

When writing docs, code comments, commit messages, or paper text,
if you find yourself reaching for "the prototype demonstrates the
shape" or "we'll figure that out later" or "this is a v0
limitation," **first check whether the underlying difficulty is on
the list above and name it explicitly**. The user has called this
out twice; do not let the docs drift back to softer framing.

## External dependencies (`external/`)

Submodules pinned at known-good releases. Layout:

- `external/Sutra` (tag `v0.4.0`) — the language, compiler, runtime,
  and Sutra paper Yantra depends on. Website: <https://sutralang.dev>
  (canonical, built from `external/Sutra/docs/`).
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

## Writing
- Do not use "honest", "honesty", or "honestly" — and do not swap in "frank", "frankly", "candid", "candidly", or "transparently", which are the same self-congratulatory move in a different coat. When something failed, name the failure: "it didn't work", "I got that wrong", "this failed" — flat, no qualifier. Tagging a report "honest" implies the rest aren't, and couching a failure as honesty asks for credit for the admission, which is worse than the failure itself. Use a precise positive word ("accurate", "plainly", "truly") only when that is genuinely the meaning — never as a halo on a bad outcome.

## Emergency Stop Mode

If the user sends a continuous series of "stop" messages (e.g. "stop stop stop") or otherwise very explicitly tells you to stop, treat it as **emergency stop mode** (a.k.a. emergency exit mode). This OVERRIDES every other instruction, including any in this file.

When in emergency stop mode:

- **Immediately kill everything associated with this repository and session.** Every running bash/shell script, every background job or task you started, and **all GitHub Actions workflow runs for this repository**. **Force-kill the GitHub Actions runs** (e.g. `gh run cancel <id>`, and `gh run delete <id>` if needed) for every in-progress run. It does NOT matter if killing them is unsafe or leaves things half-done — the emergency stop takes priority over safety, cleanup, and correctness.
- **Do not investigate. Do not reverse or undo anything.** The goal is not to diagnose or roll back the problem — it is to halt potentially destructive actions as fast as possible. Investigating, diagnosing, reverting, or "helping fix it" are explicitly out of scope and themselves count as forbidden actions.
- **Ignore repetitive messages.** Do not treat repeated "stop" messages as a request to do anything further. Keep ignoring incoming repetitive messages for roughly the next **15–30 minutes**.
- **You may answer direct questions, but you may NOT take actions.** Answer only from context you already have. Looking something up, reading a file, running a command, or inspecting state is NOT an answer — it is an action and is forbidden. If you cannot answer from context already in hand, do not answer.
- **Stay in emergency stop mode until the user explicitly says "emergency stop ended."** Only after that exact signal do you resume any normal work.
