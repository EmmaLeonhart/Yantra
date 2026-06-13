# Yantra — Work Queue

**This file is a queue, not a state snapshot.** It lists what is being worked on right now. Finished work lives in `git log` and `devlog.md`; longer-horizon ideas live in `planning/` or `todo.md`. When an item is done, delete it — no checkmarks, no status indicators. If an item is still here, it is not done.

**Why this file exists:** when a planning step produces a plan, that plan is written here BEFORE execution starts, so an interrupted session can resume from the queue rather than from chat context that may be gone.

See `CLAUDE.md` § "Workflow Rules" for how this file, planning mode, and the task tool stay in sync. Longer-horizon items live in `todo.md`.

---

## SESSION DIRECTION — repository refocus + celestial restyle (Emma 2026-06-13)

Yantra is now treated primarily as the **website repository**. The OS / language development happens in the **Sutra** repo (`external/Sutra`), where a substantive language work-loop is running on `main`. This session:

1. **Audit + archive** the non-website code (kernel/, apps/, orchestrator/, bootloader/, paper/, etc.) off `main` to a branch, leaving `main` website-first.
2. **Restyle** the Yantra **and** Sutra websites in an Extropic-style **celestial / glowy** aesthetic with cooler (periwinkle / cyan / violet) colours.
3. **Bring the docs** on both sites in line with Sutra's **real current capabilities** and how the language relates to the OS being built with it.

**Hard constraints for this session:**
- **Do NOT mention the bootloader** in any website copy — it is over-stressed; the site is aspirational about the OS, grounded in the language.
- **Do NOT edit the shared `identity.css`** (Yantra + emmaleonhart.com + Sutra + Loka all link it). Celestial styling goes in **site-specific layers** linked *after* identity.css. Decision: scope = Yantra + Sutra only.
- **Sutra-side edits go on a branch** `website-celestial` off Sutra `main`, never directly on `main` (the language loop owns `main`). PR to `main` is the final queue item.
- Session crons already running: work-loop `:03`, auto-flush `:15`, status-report `:42`, Sutra-pull every 2h. (Started this session — see autonomous-loop playbook.)

---

## Active

> **Gate lifted 2026-06-13 14:51** — Sutra submodule pulled to `11026ca` (v0.7.1-745, +312 commits). Website work may begin at step 1.

### 1. Audit the Yantra repo for what is genuinely website / Yantra-only vs. duplicated Sutra work
- Inventory: `kernel/`, `apps/`, `orchestrator/`, `bootloader/`, `paper/`, `planning/`, `tests/`, `tools/`, `scripts/`, the `!run*.bat` files, `Dockerfile`, `.devcontainer/`.
- For each, decide: (a) duplicates Sutra-side work / already migrated → archive; (b) genuinely Yantra-only worth keeping on `main` (e.g. the paper? the vision planning docs? the website?) → keep.
- Cross-check `external/Sutra` to confirm what already lives there (font/gui demos already migrated per old queue).
- Skim Emma's local context repos for messaging input: `C:\Users\Immanuelle\Documents\Github\life-planning` (life/business planning) and `C:\Users\Immanuelle\Documents\Github\emmas-gstack` (Y-Combinator / Web-Combinator application + misc). Pull anything that should shape the website's positioning.
- Decide the fate of `.github/workflows/daily-audit.yml` (it auto-prepends kernel substrate-honesty audits — moot on a website repo; likely move with the archive).
- Output: `planning/24-website-repo-refocus.md` — findings + the keep/archive list.

### 2. Archive the non-website code; make `main` website-first
- Cut branch `archive/kernel-prototype-2026-06-13` from current `main` (preserves everything, including the kernel queue items below).
- On `main`, remove the archived code per step 1's list; keep `site/`, the website-relevant planning/vision docs, `README.md`, `CLAUDE.md`, `LICENSE`.
- Rewrite `README.md` + `CLAUDE.md` so the repo reads clearly as "the Yantra website (kernel/language prototype archived on a branch; active dev is in Sutra)."
- Disable/remove `daily-audit.yml` (and any CI that referenced removed code) so it stops prepending kernel audits.
- Commit, push, verify CI green.

### 3. Yantra site — celestial / glow aesthetic layer
- Study reference: `extropic.ai` (deep space-black, glowing accents, celestial gradients, subtle grain/starfield, slow animated glow). Cooler palette than Extropic's warm orange — lean into the existing periwinkle `--accent`, push toward cyan/violet/celestial.
- Add `site/celestial.css` — a NEW layer linked AFTER `/identity.css` in `index.html`. Do not modify `identity.css`.
- Build: glowing gradient hero, intensified animated aurora/nebula, subtle starfield or grain, glow on buttons/eyebrow/pills, celestial section dividers. Respect `prefers-reduced-motion`.
- Keep dark default; confirm light theme still reads.

### 4. Yantra site — copy pass to real current capabilities
- **Remove the bootloader bullet** from `index.html`'s "What's built"; rewrite that section so it is accurate without it.
- Update "Why now" / "What's built" / "Where it goes" to reflect Sutra's actual current state (after the 2h Sutra-pull cron refreshes the submodule). Talk on-the-ground: what the language can do today and how it relates to the OS. No overclaim; cite Sutra-paper numbers where used.

### 5. Sutra site — celestial restyle on the `website-celestial` branch
- In `external/Sutra`: create/checkout `website-celestial` off `main` (merge latest `main` first).
- Apply the matching celestial/glow aesthetic to the Sutra docs site (MkDocs Material — custom `extra_css` layer; do not touch language/runtime code).
- Commit + push the branch.

### 6. Sutra docs — content pass to current capabilities
- Light, accurate updates to `docs/index.md`, `what-is-sutra.md`, `capabilities.md`, `vision.md`, etc. to reflect the 433+ commits past `v0.7.1`. Correct, don't rewrite what's already right.

### 7. Verify both sites
- Yantra: open `site/index.html`, confirm the celestial layer renders, theme toggle works, no broken links, bootloader gone, copy accurate.
- Sutra: build docs locally if tooling present, else visually verify the CSS layer.

---

## Pinned tail (run in this order, last)

### Z1. Open the Sutra website PR
- After `website-celestial` is complete and pushed, `gh pr create` merging `website-celestial` → Sutra `main`, titled as docs/website-only so it can merge alongside the language loop. Report the PR URL.

### Z2. Ensure the four session crons are still running
- `CronList`; recreate any of work-loop `:03`, auto-flush `:15`, status-report `:42`, Sutra-pull `every 2h` that a planning burst or restart killed.

### Z3. Final status report
- Run the status-report action once more, independently: end-of-session summary of everything done this session.

---

## ⛔ To be dispositioned in step 1 / archived in step 2 (pre-existing kernel/language queue)

These items pertain to the kernel/language prototype that is moving to the archive branch and/or is now developed Sutra-side. Step 1 decides which (if any) belong on website `main`; the rest ride to `archive/kernel-prototype-2026-06-13`. The daily substrate-honesty audit items below are about `.su` commits — this session does no `.su` work, so they are superseded by the archive, not skipped.

- **Daily substrate-honesty audits 2026-05-28 … 2026-06-13** (auto-prepended by `daily-audit.yml`) — kernel `.su` audit items; archive with the kernel code and stop the workflow prepending them.
- **⚙️ Environment pin — this machine IS capable** (RTX 4070, CUDA available; don't pre-emptively frame algorithms as unworkable). Keep this fact in `CLAUDE.md`/archive if still useful for the language work.
- **Standing blocker — `axon_project` no-op across separately-compiled programs** — Sutra+kernel design problem; lives with the archived kernel + `planning/20`.
- **Headline demo — replicate Meta *Neural Computers* prototypes** — `planning/22`; kernel/Sutra work, archive.
- **Yantra → Sutra migration phase 3** (`apps/calc`, `apps/echo`, `apps/terminal`) — needs design; archive with the apps.

---

## Pointers

- Longer-horizon items: `todo.md`
- Website: `site/` (`index.html`, `identity.css`, and the new `celestial.css`)
- Design / vision notes: `planning/` (numbered for reading order)
- Sutra (the language Yantra is built in): `external/Sutra` — website on the `website-celestial` branch this session
- Cross-repo workflow (Yantra ↔ Sutra): `CLAUDE.md` § "Cross-repo workflow"
- Narrative history: `git log`, `devlog.md`
