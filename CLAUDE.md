# Yantra

## Workflow Rules
- **Commit early and often.** Every meaningful change gets a commit with a clear message explaining *why*, not just what.
- **Plan into `queue.md` FIRST, then execute.** When entering planning mode (or any multi-step think-before-do), the FIRST action is to write the plan into `queue.md` as concrete items. Only then begin executing. Chat context dies on session interrupt; the queue survives.
- **Update `queue.md` in the same commit as the work.** Delete completed items in the same commit — do not leave checkmarks or status markers behind.
- **Mirror `queue.md` into the task tool.** `TaskCreate` items as you add them to queue.md; mark `in_progress` when starting; `completed` when done.
- **Do not enter planning-only modes.** All thinking must produce files and commits. If scope is unclear, create a `planning/` directory and write `.md` files there instead of using an internal planning mode.
- **Keep this file up to date.** As the project takes shape, record architectural decisions, conventions, and anything needed to work effectively in this repo.
- **Update README.md regularly.** It should always reflect the current state of the project for human readers.

## Session-local auto-flush cron — RESTART AT THE START OF EVERY SESSION (Emma 2026-05-24)

**Leaving the `external/Sutra` submodule with uncommitted or unpushed changes actively causes complications** (dirty/detached submodule state, the Yantra working tree showing `M external/Sutra`, work that silently disappears). So: **push all the time** — never let the submodule sit dirty.

**At the START of every session, (re)create this `CronCreate` job** (it is session-local — `durable: false` — so it dies when the session ends and must be recreated each session):

- **Schedule:** `15 * * * *` (every hour at :15).
- **What it does:** commit + push ALL pending work in BOTH repos so nothing sits uncommitted —
  1. `external/Sutra`: `git -C external/Sutra fetch origin --quiet`; fast-forward if behind; if the working tree has changes, commit them on the current branch (**`main`** unless told otherwise this session — Emma works on `main`, not `yantra-driven`); push if ahead. **Never force-push, never `reset --hard`, never discard the other machine's work.**
  2. Yantra: `git fetch origin --quiet`; ff if behind; if the pin moved (`M external/Sutra`) or files changed, commit + push `origin main` (bump the pin in the same commit).
  3. Only commit/push when something is actually pending — no empty commits.
  4. Report one line: what was pushed (shas) or "nothing pending".
- **Caveats:** recurring `CronCreate` jobs auto-expire after 7 days; sessions are usually shorter, and each new session recreates it anyway. Not remote-durable by design — it is a within-session safety net, not infrastructure.

This complements (does not replace) the "commit early and often" rule above — the cron is the backstop that catches anything left uncommitted between manual pushes.

## Autonomous productivity loop — the three-cron playbook (Emma 2026-05-25)

**This loop has been the single most productive way of working in this repo, so it is the default for any session meant to make sustained progress.** It is three **session-local** `CronCreate` jobs (`durable: false` — they die with the session, so **recreate all three at the start of every session**). They turn "barrel through `queue.md`, and when it's empty atomise the next `todo.md` item into it" into a self-sustaining hourly cadence with a commit/push backstop and a heartbeat.

Recreate these at session start (stagger the minutes so they don't collide; the auto-flush one is the same job documented in the section above):

1. **Work-loop cron — `3 * * * *` (hourly at :03).** The engine. Prompt does, in order: **(a) SYNC** — `git fetch origin`, ff/rebase Yantra `main` (never force-push / `reset --hard` / discard the sibling machine's work); `git -C external/Sutra fetch --tags`, and if a Sutra *release tag* is newer than the current pin, verify `pytest tests/ -q` green at it then bump the pin (never move the pin backward — the sibling may pin past the latest tag on `main`). **(b) WORK** — take the top actionable Yantra item from `queue.md` and do it; if nothing in `queue.md` is actionable (all blocked / needs-Emma / a product decision), promote the next *genuinely-unblocked, bounded, verifiable* `todo.md` item — **plan it into `queue.md` first**, mirror to the task tool, then execute. **(c) HARD RAILS** (these are why the loop is trusted — see below). **(d) COMMIT** — commit early/often with *why*; update `queue.md` in the same commit (delete completed items); mark task-tool items done; push `origin main`. **(e)** report one line: the commit shas advanced, or `nothing actionable; <reason>`.
2. **Auto-flush cron — `15 * * * *` (hourly at :15).** The backstop. Exactly the job in the section above: commit + push all pending work in BOTH repos so nothing sits uncommitted; report shas or "nothing pending".
3. **Status-report cron — `42 * * * *` (hourly at :42).** The heartbeat — **reporting only, no code changes**. Covers: what advanced since the last report (shas + one line each); current `queue.md` state; how the work held the hard rails (and any place it brushed one); blockers / items deliberately not done autonomously and why; test-suite health (`pytest tests/` last result + `cargo test` where relevant). This is what stops the loop silently losing the thread.

**The hard rails (the work-loop's (c) — non-negotiable, this is what makes the loop trustworthy):** never fake; never weaken/skip/delete a test to make it pass; never claim "works"/"verified"/"substrate-pure" without having RUN it and measured. A real defect → strict `xfail` or a precise documented blocker, never a loosened assertion. A substrate service's returned value must be DECODED FROM THE SUBSTRATE, never a host re-computation; every decision that affects a result (incl. *which* operation runs) is a substrate op, not a host `if`. Don't implement what you don't 100% understand — write the spec/queue item instead. When Emma gives an algorithmic explanation, implement HERS first and run it. Name unbuilt/hard things plainly (don't paper over difficulty). Correct stale/false docs the moment you find them. **Verify CI, not just local — `gh run watch` after any push that touches code or CI.** Local-green does not imply CI-green (different envs surface different bugs; the 2026-05-25 episode where CI was silently red on every commit while local pytest showed 215 passed was exactly this failure mode). And when adding a CI-bypass mechanism (a cached test fixture, a stub, a pre-warmed cache), **simulate the CI failure mode locally before claiming the fix works** — e.g. `sys.modules['ollama'] = raise-on-call` before re-running pytest, so a local backup path (an installed dep, a running daemon, a real cache directory) cannot quietly hide a misconfigured fix. The first version of the 2026-05-25 ollama-fixture fix passed locally only because ollama backfilled the keys the cache file (wrongly named) couldn't supply — the second CI red caught it.

**Why it works (observed 2026-05-25):** the work-loop makes steady, verifiable, committed progress without waiting on a human; the auto-flush guarantees nothing is lost between ticks; the status-report keeps the thread legible. A productive session of this loop shipped, e.g., the kernel RAM cold-store tier, the full Rust-orchestrator checkpoint codec stack (YAXN→YAXE→YPRC→YKST, each byte-for-byte cross-checked against the Python kernel), two substrate-computed GUIs (Python + a Rust-orchestrator subprocess bridge), and several doc-truth corrections — all under these rails.

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

This repo holds **planning documents** plus a v0.0 kernel nucleus
under `kernel/` (a Python orchestration layer over real Sutra
compute). The Sutra compiler/runtime and the JS/TS transpiler live
in adjacent projects.

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
  Sutra v0.6.2 compiler and runs `on_axon(vector) -> vector` on
  real torch tensors routed through the kernel. The
  **orchestration layer** (init/resource-manager + axon router +
  capability check) is in Python here; the production form on the
  CPU side is **Rust** per `planning/01-architecture.md` § "CPU
  side: small, Rust, orchestrator." When updating Yantra-side
  kernel code today, edit the Python and write `.su` files;
  treat the Python as the API-shape pin the eventual Rust
  reimplementation must match.
- **Kernel is native Sutra, not transpiled.** The verification
  surface in `paper/paper.md` § 4 depends on the trusted base
  reducing cleanly to a compiled tensor-op graph. Sutra services run on the
  GPU; the Rust orchestrator runs on the CPU, written natively in
  Rust.

### Transpilers

- **TS→Sutra is the only transpiler in scope, and it is
  browser/GUI-scoped.** Outside the browser layer, TS→Sutra is not
  used. **Shipped as Sutra v0.3.2** (released 2026-05-14): CLI
  works, 17 fixtures pass, `pip install sutra-dev[ts]` bundles it.
  Coverage caveat: typed core works, but TS-completeness is not a
  solved problem — real-world bundles may need new lowering rules.
  Foundation, not finished feature.
- **C→Sutra transpiler is NOT planned** (decision 2026-05-23).
  Sutra is a systems language for a GPU-native architecture; Yantra
  is not copying the Linux kernel or C apps. Userspace is written
  natively in Sutra; the bootloader and orchestrator are written
  natively in Rust. C→Sutra may be revisited someday but is not on
  any roadmap and must not be presented as planned work.
- **WASM target deferred** — eventually in scope but not now and not
  for a long time (its linear-memory/threading model is alien to
  Sutra's substrate; the v0 GUI is JS/TS only; not a v0 or v0.1
  target). See `planning/07-transpilers.md` and
  `planning/06-gui-stack.md`.

### Userspace utilities (cat, ls, grep, awk, sed, sort, etc.)

Written **natively in Sutra**. The Linux source trees under
`external/` are behavioural reference for native rewrites, not
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
     in this repo at `external/Sutra` (submodule, currently v0.6.2).
     Language website: [sutra.emmaleonhart.com](https://sutra.emmaleonhart.com). The
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
  readiness.md`** — accurate engineering accounting, not paper-tone.
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
  `sdk/sutra-compiler/`, `sdk/sutra-from-ts/`, the compiler,
  the lowering passes, the
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

## Accuracy rules (added 2026-05-14)

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

## Substrate purity — no host shortcuts

Yantra's claim is that computation happens on the Sutra substrate. A host-Python
result in a substrate costume is a lie about what executed — the same rule Sutra
enforces (`external/Sutra/CLAUDE.md` § NO MATH SHORTCUTS).

- **Host code is orchestration + monitoring only — never the returned value.**
  Parsing, I/O, admission live on the CPU side. But a service's returned value must
  be what the *substrate* computed, not a host re-computation. (The 2026-05-24 calc
  bug: it computed on the substrate, discarded that, and returned a host `Fraction`
  — using the substrate only as a gate. Return the substrate's decoded value. See
  `planning/23-calc-substrate-purity.md`.)
- **Operation *selection* is computation — run it on the substrate.** Don't let host
  Python pick which op runs (`OPS[op]` choosing a `.su`). The operator is data;
  dispatch on it in Sutra via a **defuzzified switch** — compute every branch, build
  a one-hot selector from the operator (`is_true`/`select`), sum `branch·selector`
  so unselected branches are ×0.
- **No host oracle deciding the output.** Don't compute the "true" answer on the
  host and gate or replace the substrate output with it. Host-oracle verification is
  allowed as a *test/audit*, never as the runtime value.
- **Parsing belongs on the substrate too.** Sutra has the string ops (codepoint
  `String`/`Character` model); host string-parsing is a shortcut to retire, not a
  permanent boundary. Host stays I/O only (read the line, print the result).

### The fake-substrate-work threat (real, recurring — guard against it)

**This is a real threat that has already occurred, not a hypothetical.** An agent
(or a person) can produce work that *looks like* the spec but is fake underneath —
the computation claimed to run on the substrate is actually done by the host.

**Documented instance (2026-05-24):** the calculator (`apps/calc/`) presented as
"math runs on the Sutra substrate, exact through the kernel," but host Python picked
which operation ran **and** returned a host-`Fraction` answer, using the substrate
only as a pass/refuse gate. It passed its tests and read as real — it was not. Full
write-up: `planning/23-calc-substrate-purity.md`.

**How it happens:** the implementer doesn't 100% understand the substrate mechanism,
so they write code that *resembles* the instruction and lean on the host for the
parts they can't express. The result looks correct and is **worse than nothing** —
it hides the gap and burns trust.

**Guard against it:**
- **Do not implement what you do not 100% understand.** If you cannot build the real
  substrate version, do **not** ship a host-faked stand-in. Stop and ask, or write a
  spec/plan in `planning/` and queue the real work. (That is exactly what
  `planning/23` is — design + queue, not a rushed half-implementation.)
- **The returned value must be decoded from the substrate** (see § Substrate purity).
- **Every decision that affects the result — including *which* operation — is a
  substrate op, not a host `if`.**
- **When reviewing "it works," check *what actually executed*,** not just that a
  number came out right. A passing test against a host oracle proves the *host* is
  right, not the substrate.
- **Don't barrel into code surgery in another repo unbidden.** Add the design + queue;
  let the owner (or a deliberate session) execute. Plausible-looking speed is the trap.

## When Emma gives an algorithmic explanation, implement it

Emma knows Sutra — and the substrate mechanisms Yantra rides on — far better
than an agent does. Recurring, costly failure: she gives a concrete algorithm,
the agent decides it "can't work," substitutes its own variant, the variant
fails, and the idea gets reported as blocked — when **her original idea was
right**. Implement the thing she actually described *first*, run it, read the
output. "I think that can't work" is a hypothesis to test on the substrate, not
a conclusion. If it seems not to compose, the gap is usually a primitive to
expose, not a wrong idea. (2026-05-24: "defuzzify `select` enough so the
branches don't blend" → **18/18 bit-exact** once actually built, after a
session lost to agent-invented detours; full write-up + the Sutra-side rule in
`external/Sutra/CLAUDE.md` § "When Emma gives an algorithmic explanation.")

## External dependencies (`external/`)

Submodules pinned at known-good releases. Layout:

- `external/Sutra` (tag `v0.6.2`) — the language, compiler, runtime,
  and Sutra paper Yantra depends on. Website: <https://sutra.emmaleonhart.com>
  (canonical, built from `external/Sutra/docs/`).
The Linux userspace submodules (`coreutils`, `util-linux`,
`busybox`) were **removed 2026-05-23** along with the C→Sutra
transpilation path they were imported for. GNU behaviour remains the
conceptual reference for native-Sutra utility rewrites, but no Linux
source is vendored. `external/` now holds only `external/Sutra`.

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
- Scope limits beat overclaim every time. If a hardware reality
  (interrupts, MMIO, side channels) is not solved, say so in the paper
  rather than letting a reviewer find the gap.

## Formal verification — keep the FV paper in sync as we work

Formal verification is an active, ongoing strand (early stages: the
framework + first paper, not mechanized proofs yet). **As we do FV
work, update the formal-verification paper alongside it** — the paper is
a live artifact that tracks the work, not a one-off writeup. Canonical
locations (Sutra-side, so edits go on the `yantra-driven` branch per the
cross-repo workflow, and the paper auto-submits to clawRxiv via
`fv-paper-ci.yml`):

- **Paper:** `external/Sutra/paper/formal-verification/paper.md`
  (clawRxiv post 2613). When an FV obligation is discharged, a primitive
  lands, or a claim's scope changes, reflect it in the paper in the same
  session — and cite only measured numbers, mirror the §"What we are not
  claiming" discipline.
- **Rules/spec:** `external/Sutra/planning/sutra-spec/formal-verification.md`
  is the ground truth the paper must not contradict.
- **Agenda:** the FV work items live in Sutra's `todo.md` + `queue.md`;
  keep them current as items move.

The discipline above (one coherent change per revision, name the con,
cite the Sutra paper, scope-limit over overclaim) applies to the FV
paper too.

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

## Cron jobs and scheduled work — LOCAL by default

**When the user says "cron job", "cron", or asks to "schedule" a task, they mean the in-session `CronCreate` tool** — a prompt scheduled to fire locally, inside this Claude Code session, on the user's own running computer. This is the default and the assumption. Do NOT interpret it as anything else unless the user explicitly names a different mechanism.

- **It is local and in-session — use the `CronCreate` tool.** A generic "cron" request is NOT an OS crontab, NOT a GitHub Actions / CI `schedule:` trigger, and NOT a cloud scheduler. (Repos may *also* contain their own GitHub Actions cron schedules — those are a separate thing and are not what the user means when they ask *you* to set up a cron.) The user leaves the computer on and this session running so the scheduled prompt can execute.
- **The user is deliberately away from the keyboard.** They schedule work precisely so it runs while they are out of the house and not physically present. Their absence is the normal, expected condition for these jobs — it is NEVER a reason to delay the work, ask "are you sure?", wait for them to return, or refuse to proceed.
- **Standing consent — just set it up.** Cron / `CronCreate` requests are pre-authorized. Create the job immediately and locally, then report what was scheduled. Do not block on confirmation or follow-up questions. Treating a routine cron request as something that needs hand-holding is itself the obstacle this section exists to remove.

## Hourly status-report cron for extensive work

The status-report cron lives inside the larger **three-cron playbook** documented in §"Autonomous productivity loop" above (work-loop at `:03`, auto-flush at `:15`, status-report at `:42`). On its own it is `42 * * * *` — fires every hour at :42 with a status report of the work being done. The two pinned tail items at the end of the queue ensure all three crons (not just this one) are running and run an end-of-session summary.

## Check cleanvibe for skill updates (weekly)

This `CLAUDE.md` carries cleanvibe-shaped sections (writing rules, emergency stop, cron policy, the productivity loop). cleanvibe ships new sections / skills over time — when one lands, this file should pick it up.

**The check is weekly, not per-session.** At the top of any session, look at the *last cleanvibe update check* date below. If it has been more than 7 days, do this:

1. **Fetch the current skill index** — `WebFetch https://cleanvibe.emmaleonhart.com/updates.md`. This is the canonical, hand-maintained page describing every section / skill / convention cleanvibe templates currently ship, keyed by the cleanvibe version that introduced it.
2. **Compare against the version below.** If `updates.md` lists sections introduced in later versions, fold those sections into THIS `CLAUDE.md`. Match the wording from `updates.md`; don't paraphrase. Yantra-specific carve-outs already in this file (cross-repo workflow, substrate-purity rules, kernel-as-Connectome-Manager, etc.) stay — only the generic sections are kept in sync.
3. **Update the version + date below** to reflect the check. Commit the changes with a message describing which sections were folded in.

If the fetch fails (offline, DNS, page not yet up), leave the date alone and try next session — the check is opportunistic, not mandatory.

- **Last synced cleanvibe version:** `1.11.0`
- **Last cleanvibe update check:** `2026-05-26`
- **Updates source:** <https://cleanvibe.emmaleonhart.com/updates.md>
