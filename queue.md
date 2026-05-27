# Yantra — Work Queue

**This file is a queue, not a state snapshot.** It lists what is being worked on right now. Finished work lives in `git log`; longer-horizon ideas live in `planning/` or `todo.md`. When an item is done, delete it — no checkmarks, no status indicators. If an item is still here, it is not done.

**Why this file exists:** when a planning step (formal planning mode or just "think before doing") produces a plan, that plan is written here BEFORE execution starts. An interrupted session can pick up from the queue rather than from chat context that may be gone.

This repo currently holds **planning documents and a v0.0 kernel nucleus**, not a full implementation, so most "work" here is design and small implementation pieces. The same rule applies: design plans go into queue.md before they get executed against `planning/*.md` or `kernel/`.

See `CLAUDE.md` § "Workflow Rules" for how this file, planning mode, and the task tool stay in sync. Longer-horizon items live in `todo.md`.

---

## Active

### ⚙️ Environment pin — this machine IS capable (read before doubting hardware)

Emma's machine has a real, good GPU — an RTX 4070, `torch.cuda.is_available() == True`, ample compute. Do NOT assume CPU-only, do NOT assume "the GPU path won't work," do NOT pre-emptively frame Emma's algorithms/logic as unworkable on this hardware. Measured 2026-05-24: admitting a Sutra program allocates real GPU memory; the GPU-tier residency tests pass 4/4 in isolation; the calc runs float64 exactly. When a GPU-dependent test looks like it "fails," first check whether it's a test-isolation / shared-substrate artifact (it usually is) — run it alone before concluding a capability is missing.

### Standing blocker — `axon_project` no-op across separately-compiled programs

Intra-module slice of producer-side pruning shipped (Sutra v0.4.1; submodule pinned). The cross-program (connectome) case remains: producer + consumer are independent `.su` modules wired at admission, which a single-module compiler structurally cannot bridge. The fix is whole-connectome compilation or admission-time producer specialization — a Sutra+kernel design session, deliberately not autonomously forced. Full reasoning + the remaining design options in `planning/20-lazy-axon-evaluation.md` § "Status (2026-05-17)" and `todo.md` § 1.

### Headline demo — replicate Meta *Neural Computers* prototypes, symbol-stable

Goal + roadmap: `planning/22-meta-demo-replication.md`. Stage-1 harness, CLI calculator, terminal surface, and the substrate-decoded result-string (digits.su) are SHIPPED — see `git log` and DEVLOG. **Remaining open work:**

1. **First CLI utilities beyond echo** (`cat`, `ls`, `wc`) — native Sutra; gated on Sutra's string + IO + FS vocabulary. Promote from `todo.md` § 2 as each unblocks.
2. **Multi-digit substrate parse loop** — `parse_int2` handles 1–2 digits via the place-value formula. Variable-length needs a `while_loop`/accumulator pattern over a string, which hit two failure modes 2026-05-25 (slot-var shape coercion, dynamic loop count); BLOCKED pending a deliberate Sutra-loop session with Emma. Without it, two-operand "DD OP DD" splitting also can't land. See `planning/23` Stage-1.
3. **Headline-demo contrast figure** — Yantra side is pinned (zero drift, N=60 through the terminal). The decaying right side needs a CLIGen-shaped DiT-frame baseline or Meta's published degradation numbers — will NOT fabricate. `planning/22` § "Making it measurable".

Not in scope: replicating the *video / screen-frame generation* (NCGUIWorld) — deferred, optional, only if the GUI layer matures.

### Font demo rewrite — per-char bound-vector instead of 25-way inner switch

The existing `apps/font/font.su` design pays **22,500 inner-select branches per keypress** because each of the 36 `bit_<C>(pos)` functions is itself a 25-way defuzzified switch over flat positions. That's the antipattern: a 25-way switch is implementing a tiny lookup table the substrate already has a clean primitive for. Rewrite so each character is encoded as a single **bound-vector of 25 bits**, and `glyph_pixel(x, y, code)` becomes a 36-way outer select where each branch is *one* unbind-by-position operation, not a 25-way inner switch. Render cost per cell drops from ~36×25 substrate ops to ~36. Same external API (`step`, `glyph_pixel`, `cycle_step` unchanged) so the cycle demo, render_glyph, and existing tests/test_font.py still pass after the rewrite.

Triggered by Emma's pushback on 2026-05-27: "a 20,000-thing switch is just bizarre." She's right — that's bloat, not "the cost of substrate purity." The cycle_step demo shipped first so the recurrent step is visible today; this rewrite is the follow-up that makes the renderer not embarrassing.

### GUI — substrate-computed pixels: open follow-ups

DONE 2026-05-24/25: static radial frame (`apps/gui/frame.su` + `window.py`) and the interactive click red↔blue toggle (`apps/gui/toggle.su` + `click_demo.py`) — substrate parts tested, run via `python apps/gui/click_demo.py`. Open:

1. **Live window + click verification** — not headless-testable; the substrate parts pass, the tkinter window + click event need a human at the screen.
2. **Per-pixel render batching** — BLOCKED on a Sutra-side change: `make_real` is scalar-only, so the compiled `pixel` graph can't take a batch dim. Not a clean Yantra-side fix.
3. **Reverse-CNN decoder** (Emma's "return a vector → reorganise into pixels") — unbuilt; the bigger next GUI step (`planning/24-first-gui.md`).
4. **Window belongs in the orchestrator eventually** — host tkinter is the stand-in; the real window is a Rust-orchestrator unit (`planning/01`).
5. Host does tint/colormap + event handling; the field + state are substrate. Keep that split — don't let host-drawn content masquerade as substrate output.

---

## Pointers

- Longer-horizon items: `todo.md`
- Kernel runtime nucleus: `kernel/` (see `kernel/README.md`)
- First userspace utility: `apps/echo/` (see `apps/README.md`)
- Terminal surface (Stage 2): `apps/terminal/` (see `apps/terminal/README.md`)
- Bare-metal QEMU bootloader: `bootloader/` (see `bootloader/README.md`)
- Design notes: `planning/` (numbered for reading order)
- Open architectural questions: `planning/15-open-questions.md`
- Memory model open hard problem: `planning/17-memory-model.md`
- Boot sequence: `planning/19-boot-sequence.md`
- Lazy axon evaluation: `planning/20-lazy-axon-evaluation.md`
- Kernel + browser readiness audit: `planning/18-kernel-browser-readiness.md`
- First GUI: `planning/24-first-gui.md`; v0.2.0 accuracy audit: `planning/25-v0.2.0-retrospective.md`
- Paper + AI peer review pipeline: `paper/` (see `paper/README.md`)
- External dependencies: `external/` (submodules)
- Cross-repo workflow (Yantra ↔ Sutra): `CLAUDE.md` § "Cross-repo workflow"
- **Precompile every .su to prime the codegen cache:** `python scripts/precompile_all_su.py` — run after a fresh clone or after a Sutra submodule bump, so demos + tests don't pay the slow codegen on first launch. Caches are committed; the script just populates them when the manifest changes. Add a row to its `_MANIFEST` when a new .su that benefits from precompilation lands.
- Narrative history: `git log`
