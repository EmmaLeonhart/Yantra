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

### Font app — MIGRATED to Sutra `demos/font/` 2026-05-28

The font app (`apps/font/font.su`, `font_bound.su`, `font_demo.py`,
`font_data.py`, both generators, all three test files, the d108 fixture)
landed Sutra-side in commit `e12e1ebd`. Further work on the font happens
Sutra-side now — including the queued antipodal-filler variant of the
bound-vector rewrite, the d484 fixture for CI test coverage, and the
demo-wiring decision. See Sutra `demos/font/` + the queue items appended
to Sutra's `queue.md`.

### GUI apps — MIGRATED to Sutra `demos/gui/` 2026-05-28

Phase 2 of the migration landed Sutra-side at `ff5183ef`. `apps/gui/`'s
count.su / frame.su / toggle.su + their Python tkinter demos + the
Rust-GUI subprocess server + the 9 GUI tests all live at
`external/Sutra/demos/gui/` now. The Rust binary at
`apps/gui-rust/` stays Yantra-side but spawns the substrate server from
the Sutra location (path updated in src/main.rs). Further GUI work
(live-window verification, per-pixel render batching, reverse-CNN
decoder) happens Sutra-side.

### 🏁 LAST ITEM — migrate GUI / I-O apps from Yantra → Sutra (Emma 2026-05-27)

Strategic decision: **the GUI / I-O work in `apps/` is too tightly coupled to Sutra-the-language to live in Yantra.** It's actually Sutra-language-development work — exercising what the substrate can do — not OS work. The OS-level work was failing because we were doing language-level work at the OS level without enough context. Move the language-level work back to Sutra; put the OS on hold while the language matures.

**Do this LAST** — after every other open item in this queue is done. The migration is the *closing* action, not the next one.

Migration plan:

1. Move `apps/echo/`, `apps/calc/`, `apps/gui/*`, `apps/font/`, `apps/terminal/` (the .su files + their Python drivers + their tests) into the Sutra repo (likely under `examples/` or a new `demos/` directory — Sutra-side decision). Keep them on Yantra `main` until the Sutra commit lands, then delete from Yantra in the same Yantra commit that points to the new Sutra location.
2. Append to Sutra `queue.md` (at the very BACK, per Emma) — items below under § "What goes at the back of Sutra's queue.md".
3. After this migration: pause OS-level work. Next Yantra work is documentation about what Sutra actually does, so future autonomous-loop cron jobs build from documentation rather than from re-implementation guesses.

### What goes at the back of Sutra's queue.md (to be appended in the same migration commit)

Order matters. These are the new tail items for Sutra's queue:

1. **Audit any inappropriate use of the 768-dim embedding space for non-embedding code.** Claude was lying about what was running on the substrate in Yantra's GUI demos — every .su that doesn't call `basis_vector` was paying 96× the runtime cost it should. Apply the same audit (Yantra `planning/27-substrate-honesty-audit-2026-05-27.md`) to every Sutra-side .su example and update `runtime_dim` to match each example's actual needs.
2. **Update all documentation about the I-O / GUI things added to Sutra in this migration**, based on recent Yantra history. The .su sources have their own headers; the Sutra-side docs (`docs/`, `planning/`, README) need to describe what those programs do and what they don't do.
3. **General honesty test on every migrated demo** to ensure the looping actually happens on the substrate, not on the host. Specifically: does the recurrent state live as a substrate vector across ticks, or is the host shuttling a scalar via `vsa.real()` between ticks? The latter is NOT an RNN; if a demo claims to be one, the claim is fake until proven by measurement. (See `apps/font/font_demo.py` 2026-05-27 framing rewrite — same misframing was inherited from existing `toggle.su` / `count.su` patterns; check those too.)
4. **Write up the full design + history** — one document in Sutra that explains what we were trying to do across the recent Yantra GUI / I-O sessions (the cycle demo, the font demo, the rotation-binding rewrite design, the dim-bloat discovery, the host-state-shuttle misframing). Lessons learned, not just final state.
5. **After all the above:** append the rest of THIS Yantra queue's open items to Sutra's queue (font bound-vector rewrite, the daily-audit GH Action — Sutra-side half of it, etc.). The Yantra-side half of the queue empties out as items either ship or migrate.

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
