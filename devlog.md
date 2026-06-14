# Yantra — Devlog

Where "done" lives. Each completed `queue.md` item is deleted from the queue and
recorded here, dated, in the same commit as the work. Releases and milestones too.

---

## 2026-06-13

- **Website-refocus session set up.** Planned the repository-refocus + celestial
  restyle into `queue.md`; created the 2:30pm Sutra-pull/ignition cron and (after
  the pull) the work-loop / auto-flush / status-report crons. All session-local.
- **Sutra submodule pulled to v0.7.1-745 (`11026ca`)**, +312 commits past the prior
  pin, so website docs can reflect current capabilities. Pure fast-forward.
- **Queue step 3 (Yantra celestial layer) done.** `site/celestial.css` — a new layer linked after `identity.css` (shared identity untouched): deep-space field, cool periwinkle/cyan/violet nebula bloom, a glowing bloom behind the hero headline, twinkling starfield, fine grain, bloom on accent type/controls, gradient-hairline dividers. Dark-scoped; light theme stays calm. Render-verified both themes via Playwright; deployed via Pages (green). First pass was restrained; pushed bolder per Emma's call. Mirroring the look onto Sutra (step 5) waits on her confirm of the bolder intensity.
- **Decisions applied (Emma 2026-06-13):** archive dropped (keep all code); copy pivots to the self-optimizing-landing-pages wedge (mechanism-forward headline picked; full draft presented, awaiting sign-off); kernel/apps CI red is accepted (ignore — parked prototype, site Pages is green); one-shot PR cron set to PR `website-celestial`→Sutra main ~19:55 local; Sutra pin re-bumped to v0.7.1-747 on the 2-hourly tick.
- **Queue step 1 (audit) done** → `planning/24-website-repo-refocus.md`. Finding:
  most "non-website" code is NOT duplicated in Sutra (kernel, orchestrator,
  bootloader, paper, planning are Yantra-only); only `apps/{calc,echo,terminal}`
  are genuine Sutra duplicates. Two decisions raised for Emma (archive scope;
  current public positioning) that block queue steps 2/4/6. Step 3 (celestial CSS)
  is positioning-neutral and stays unblocked.
