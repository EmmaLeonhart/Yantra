# Yantra — Work Queue

**This file is a queue, not a state snapshot.** It lists what is being worked on right now. Finished work lives in `git log`; longer-horizon ideas live in `planning/` or `todo.md`. When an item is done, delete it — no checkmarks, no status indicators. If an item is still here, it is not done.

**Why this file exists:** when a planning step (formal planning mode or just "think before doing") produces a plan, that plan is written here BEFORE execution starts. An interrupted session can pick up from the queue rather than from chat context that may be gone.

This repo currently holds **planning documents and a v0.0 kernel nucleus**, not a full implementation, so most "work" here is design and small implementation pieces. The same rule applies: design plans go into queue.md before they get executed against `planning/*.md` or `kernel/`.

See `CLAUDE.md` § "Workflow Rules" for how this file, planning mode, and the task tool stay in sync. Longer-horizon items live in `todo.md`.

---

## Active

### Dev container (Docker) — the first VM tier

Build the smallest reproducible dev environment per the three-tier plan in the previous session: tier 1 (Docker dev container) is the immediate win, tier 2 (cloud GPU VM) waits on upstream Sutra GPU work, tier 3 (QEMU full-system) waits on a Rust kernel image to boot.

What ships:

1. `Dockerfile` at repo root — Python 3.13-slim base + build tools + pre-installed pytest + CPU torch + tree-sitter (the heavy deps, cached as image layers). Source NOT baked in — the container expects the repo bind-mounted at `/workspace` so edits flow back to the host.
2. `.dockerignore` — exclude bloat (`.git`, `chats/`, the big Linux util submodules, pytest cache, `__pycache__`).
3. `.devcontainer/devcontainer.json` — VS Code Remote-Containers config so opening the project in VS Code offers "reopen in container."
4. `scripts/dev-shell.sh` + `scripts/dev-shell.bat` — one-line wrappers for non-VS-Code users (`./scripts/dev-shell.sh` drops you into the container with the repo mounted).
5. README updates — "Dev environment" section explaining the three modes (host Python, Docker container, VS Code devcontainer).
6. CI extension — add a job that builds the Docker image and runs pytest inside it. Verifies the Dockerfile actually works on every push.

What does NOT ship in this round:

- GPU passthrough (would need NVIDIA Container Toolkit; CPU torch is fine for the kernel tests we have today).
- Cloud GPU VM provisioning (tier 2).
- QEMU image (tier 3).
- A pre-built image on Docker Hub / ghcr.io (we'd publish later if/when others want to pull without building).

---

## Pointers

- Longer-horizon items: `todo.md`
- Kernel runtime nucleus: `kernel/` (see `kernel/README.md`)
- Design notes: `planning/` (numbered for reading order)
- Open architectural questions: `planning/15-open-questions.md`
- Memory model open hard problem: `planning/17-memory-model.md`
- Kernel + browser readiness audit: `planning/18-kernel-browser-readiness.md`
- Chat history the design grew out of: `chats/`
- Paper + AI peer review pipeline: `paper/` (see `paper/README.md`)
- External dependencies: `external/` (submodules)
- Cross-repo workflow (Yantra ↔ Sutra): `CLAUDE.md` § "Cross-repo workflow"
- Narrative history: `git log`
