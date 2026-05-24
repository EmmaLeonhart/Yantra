# Yantra

**Website · [yantra.emmaleonhart.com](https://yantra.emmaleonhart.com)**

A neuro-symbolic, GPU-native operating system written in Sutra.

🌐 **Website: <https://yantra.emmaleonhart.com>**

## What it is

Yantra is the operating system you get when you take "the symbol *is* the
computation" seriously. The whole running system is one big differentiable
tensor-op graph: kernel, processes, IPC, GUI. There is essentially no
CPU-side runtime — a tiny CPU exists only to boot the system and
orchestrate the GPU. Everything that matters happens as Sutra programs
exchanging **axons** (structured embeddings produced by rotation binding).

Three things that fall out of that:

- **Predictable performance under load.** Once a process has its allocation,
  it doesn't slow down. Adding more processes either fits cleanly or fails
  admission — never degrades what is already running.
- **Verifiable.** The non-AI parts reduce to a tensor normal form +
  polynomial Kleene logic + tail-recursive loops, which is a much cleaner
  surface for formal arguments than a typical kernel.
- **AI-native by construction.** Every process already takes an axon and
  returns an axon, so local AI integrates without a translation layer.

The kernel is a **Connectome Manager**: it decides what runs on the GPU vs
sits in RAM (loaded but not running, semantically closer to disc than to
traditional RAM) vs lives on disc. It does not schedule and does not
allocate per-instruction memory in the traditional sense — its job is the
storage-tier decision. The CPU-side orchestrator is **Rust**.

## Build sequence

1. **Connectome Manager (kernel).** Python prototype in `kernel/`; production form is Rust. ([planning/01-architecture.md](planning/01-architecture.md))
2. **Command-line userspace utilities** (cat, ls, grep, …) — written natively in Sutra. Initial system access is SSH/serial only; no GUI. ([todo.md § 2](todo.md))
3. **Browser / GUI** — every UI component is a browser-rendered HTML page; HTML5 + CSS + idiomatic TS + WebGL/Three.js. WASM eventually but not for a long time. ([planning/06-gui-stack.md](planning/06-gui-stack.md), [todo.md § 3](todo.md))

**Bare-metal QEMU bootloader (v0.0)** at [`bootloader/`](bootloader/) — first Yantra-authored binary that runs on virtualized bare metal. Build with `scripts/qemu-build.{sh,bat}`, boot with `scripts/qemu-run.{sh,bat}`. See [`bootloader/README.md`](bootloader/README.md).

The intended customer is not a consumer desktop user. It is defense,
aerospace, industrial control, medical devices, autonomous systems —
anywhere "predictable latency under load" and "the certifier can read the
code" beat "it runs my favourite app."

## Status

This repo holds **planning documents** plus a v0.0 **Connectome
Manager** under `kernel/` — a Python orchestration layer over real
Sutra compute. The kernel test suite is ~56 tests covering admission
control, the axon router, capability checks, and real `.su` programs
compiled and executed through the router; the core paths pass. (Two
cases are tracked as known gaps rather than green: a GPU-memory
accounting test, and the cross-program axon-projection case — see
`planning/18` and `planning/20`.) The Sutra compiler/runtime live in
the `external/Sutra` submodule (pinned at v0.6.0; ships the TS→Sutra
transpiler CLI, axon-keys static analysis, the per-receiver
projection primitive, and `MultiProcessRuntime` — N programs sharing
one `_VSA`). Sutra's website: <https://sutralang.dev>. The
orchestration layer is Python here as the near-term implementation;
the production target on the CPU side is Rust.

Yantra is being designed (and now early-prototyped) here so that when
the upstream Sutra-side multi-process runtime + the production Rust
orchestrator land, there is a coherent target.

## Dev environment

Three modes, pick one:

**1. Host Python** — the path the existing CI runs on.

```bash
# Python 3.13 + the Sutra submodule
pip install pytest numpy
pip install torch --index-url https://download.pytorch.org/whl/cpu
git submodule update --init external/Sutra
pytest tests/ -v          # kernel suite + real-Sutra integration
```

**2. Docker dev container** — reproducible across machines, no host deps beyond Docker. First run builds the image (~5–10 min, dominated by torch CPU wheel); subsequent runs reuse layers.

```bash
# Linux/macOS
./scripts/dev-shell.sh                 # interactive bash inside the container
./scripts/dev-shell.sh pytest          # one-shot test run

# Windows PowerShell
scripts\dev-shell.bat                  # interactive
scripts\dev-shell.bat pytest           # one-shot
```

The container bind-mounts the repo at `/workspace` so edits flow back to the host. `Dockerfile` at the repo root for the curious; CI builds it on every push so it doesn't rot silently.

**3. VS Code Dev Container** — open the folder in VS Code and click "Reopen in Container" when prompted. Uses the same Dockerfile via `.devcontainer/devcontainer.json`; pre-installs the Python + pytest extensions so the test pane lights up automatically.

This is tier 1 of the three "VM tiers" planned for Yantra. Tier 2 (cloud GPU VM, e.g. RunPod) waits on upstream Sutra GPU work being something to test against. Tier 3 (QEMU full-system emulator) waits on a Rust kernel image worth booting. See [planning/18-kernel-browser-readiness.md](planning/18-kernel-browser-readiness.md).

## Where to start reading

- [paper/paper.md](paper/paper.md) — position paper synthesising the
  planning corpus. The fastest single-document entry to what Yantra is
  and why. Auto-submitted to [clawRxiv](https://clawrxiv.io) for AI peer
  review on every push; reviews live in [paper/reviews/](paper/reviews/).
- [planning/](planning/README.md) — the design notes, in reading order.
  Start with [`00-vision.md`](planning/00-vision.md).

## Paper pipeline

`paper/paper.md` is the canonical position paper. Editing it on main
triggers `.github/workflows/submit-papers.yml`, which submits to
clawRxiv (superseding the previous version tracked in
`paper/.post_id`), fetches the AI peer review, and commits the result
back to `paper/reviews/v{N}_post{ID}_review.{json,md}`. A scheduled
`pull-reviews.yml` runs every 30 minutes to catch up any reviews that
weren't ready at submission time. Requires the `CLAWRXIV_API_KEY`
repository secret to be set.

Local invocation:

```bash
set CLAWRXIV_API_KEY=...
python scripts/paper_submit_and_fetch.py --paper-dir paper \
    --tags operating-systems,neuro-symbolic,gpu,formal-verification,critical-systems
python scripts/pull_all_reviews.py --paper-dir paper
```

## Contributing

Not yet open to contribution. The architecture is moving quickly enough
that an issue tracker would be premature; the right place to push back
on ideas is via the planning docs themselves.

## Project conventions

See [CLAUDE.md](CLAUDE.md) for the conventions this repo runs by — the
short version is: commit early, do not enter planning-only mode without
files and commits, keep README and planning docs in sync with the
current state.
