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

> **Gate lifted 2026-06-13 14:51** — Sutra submodule pulled to `11026ca` (v0.7.1-745, +312 commits).
> **Step 1 audit DONE** — see `planning/24-website-repo-refocus.md`. **Emma's decisions (2026-06-13):** (1) Positioning → **pivot the public site to the current GTM wedge** (self-optimizing landing pages), NOT the OS/critical-systems framing. (2) **Archive nothing yet** — leave all code in place. So: archive step is dropped; copy rewrite (step 4) becomes draft-and-confirm-with-Emma; CSS + Sutra restyle + Sutra docs proceed.

### ⚠️ Standing rails for the copy work (do not violate)
- **No private business content on this public repo or site.** Emma's `emmas-gstack/business/` is private; do not copy its wording, pricing, funding, founder-personal, or experiment specs. Public-safe high-level framing only.
- **The one-liner is Emma's and not finalized.** The work-loop must NOT autonomously ship live marketing copy. Draft copy, show Emma, ship only after she confirms.
- No bootloader in copy. Don't edit shared `identity.css`. Sutra edits only on `website-celestial`.
- **CI red is ACCEPTED — stop flagging it (Emma 2026-06-13: "ignore it").** The kernel/apps pytest CI fails against current Sutra (HEAD-tracking drift). It's the parked prototype, not the site. GitHub Pages (the website) deploys green. Do NOT spend cycles fixing it; do NOT list it as a blocker in status reports beyond a one-line "kernel CI red, accepted".
- **Celestial intensity:** Emma approved "push it bolder" (bolder pass committed). Mirror the SAME look onto Sutra (step 5) only after she confirms the bolder version reads right.
- **PR cron:** one-shot `5f4aa096` fires ~19:55 local to PR `website-celestial` → Sutra main.

### 4. Yantra site — copy pivot to the GTM wedge  ⚠️ DRAFT presented; awaiting Emma's "ship it"
- Re-point copy from the OS/critical-systems framing to the **self-optimizing landing pages** wedge (Emma's decision). Public-safe wording only — NO private business-repo content; the one-liner is Emma's pick and pending.
- **Remove the bootloader bullet** and the financial-infrastructure/defense market section (retired framing).
- **Remove the "Read the paper →" hero CTA** (Emma 2026-06-13: the paper isn't appropriate on the Yantra front page for the wedge audience).
- Keep Sutra cited as the substrate/credibility anchor; cite only public, verifiable Sutra-paper numbers.
- STATUS 2026-06-13: Emma picked the **mechanism-forward** headline ("Your page, improving itself."). Full page copy drafted + presented in chat. Awaiting her "ship it" + two open calls (co-founder line keep/soften/drop; whether to add a verifiable Sutra number). Ship to `index.html` only after she confirms.

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
