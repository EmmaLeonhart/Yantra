# Yantra — Work Queue

**This file is a queue, not a state snapshot.** It lists what is being worked on right now. Finished work lives in `git log`; longer-horizon ideas live in `planning/` or `todo.md`. When an item is done, delete it — no checkmarks, no status indicators. If an item is still here, it is not done.

**Why this file exists:** when a planning step (formal planning mode or just "think before doing") produces a plan, that plan is written here BEFORE execution starts. An interrupted session can pick up from the queue rather than from chat context that may be gone.

This repo currently holds **planning documents and a v0.0 kernel nucleus**, not a full implementation, so most "work" here is design and small implementation pieces. The same rule applies: design plans go into queue.md before they get executed against `planning/*.md` or `kernel/`.

See `CLAUDE.md` § "Workflow Rules" for how this file, planning mode, and the task tool stay in sync. Longer-horizon items live in `todo.md`.

---

## Active

### Documentation honesty pass — boot sequence, Python-trap, lazy axons

The user is right that I've been papering over the difficulty in places. Substantive doc updates land:

1. **`planning/19-boot-sequence.md` (new)** — Explicit BIOS → bootloader → Rust orchestrator → Sutra image on GPU → connectome flow. Names the bootloader as Rust-or-C *because Python is interpreted and the boot path runs before any interpreter exists*, not because Rust is fashionable. Documents what each stage does and what state the system is in at each transition.

2. **`planning/20-lazy-axon-evaluation.md` (new)** — Lazy axon evaluation as a hard requirement, not an optional optimization. Includes the combinatorial-explosion reasoning (every program receiving every other program's full output is N²·D where D is bundle width, vs O(K) where K is the keys actually read), and the spec reference to `external/Sutra/planning/sutra-spec/axons.md` § "Lazy evaluation across boundaries." Explicit gap call-out: `kernel/router.py` does eager full-payload copying today, which is fine for the v0.0 smoke test but does not scale.

3. **`planning/01-architecture.md`** — Connectome Manager section gets a "boot flow" subsection pointing at the new doc; CPU side section sharpens "Rust because compiled native is required at the boot path" rather than the previous softer framing. Layer cake updated to show the bootloader explicitly as a separate tier below the Rust orchestrator.

4. **`planning/17-memory-model.md`** — Add a section explicitly framing how memory ties to the boot sequence: at boot time RAM holds only the bootloader; after the bootloader runs, RAM holds the program images and the GPU holds the live connectome. The disc/RAM/GPU tier semantics get their boot-time grounding.

5. **`kernel/README.md`** — Honesty pass:
   - "What is real today" gets a hard line: the router does eager full-payload routing. Lazy axon evaluation is a known gap, *not* implemented.
   - "What this is not" gets sharper: the Python is a behavioural harness for the *post-boot orchestration logic*, not a smaller version of the bootloader. The bootloader is a different artifact entirely (Rust, not present in this repo today).
   - Cross-link to `planning/19-boot-sequence.md` for the full flow.

6. **`CLAUDE.md`** — Two new rules:
   - **Python is dev tooling, not runtime.** No Python in the boot path. No Python features in `kernel/` that wouldn't port cleanly to Rust. No "convenient" Python idioms (decorators, dynamic type juggling, monkey-patching, `__getattr__` magic).
   - **Don't paper over difficulty.** When something is hard or unbuilt, say so plainly. "We'll figure it out" or "the Python prototype demonstrates the shape" without explicitly naming what's missing is dishonest. Specific things that are hard and that should be named when they come up: the bootloader, the Rust orchestrator, lazy axon evaluation, the multi-threaded Sutra runtime, disc/RAM/GPU storage-tier moves.

7. **`planning/18-kernel-browser-readiness.md`** — Re-audit the readiness section against the new docs. The Connectome Manager TL;DR should explicitly mention lazy axons as gap.

8. **`todo.md`** — Add the bootloader, the lazy axon evaluation work, and the Rust orchestrator as named items in the kernel-section forward list.

After: commit + push. No code changes in this round; this is the documentation honesty pass before any more code lands.

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
