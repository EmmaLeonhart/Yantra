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
- **Step 6 (Sutra docs accuracy refresh) done + PR #35 merged.** Emma: do the refresh, PR it, automerge. Evidenced fixes (audit-backed): `capabilities.md` — removed the `real()/imag()/truth()/component()/semantic()/synthetic()` accessors (listed as supported but are violations being removed per the 2026-06-07 no-readout ruling) + the stale free-function axis-read row; `typescript-to-sutra.md` — corrected the import/export summary-table row (named ES imports work since 2026-05-10; namespace/require don't). Did NOT touch agent-facing `AGENTS.md` or advertise the other language frontends publicly (Emma's branding call — flagged). Site rebuilds clean. Folded into **PR EmmaLeonhart/Sutra#35**, which **auto-merged (squash) to Sutra main**. Submodule switched back to tracking main (a881c16); website-celestial branch deleted; Sutra-pull cron simplified to main-only.
- **Branding clarified (Emma 2026-06-13): debranding is SAFETY ONLY; "interpretable" stays.** Restored "interpretable" as a Sutra descriptor on the Yantra site (it had been over-stripped with the safety language). Sutra docs grepped — no AI-safety branding present, nothing to debrand. Step 6's remaining piece is an optional content-accuracy refresh (not branding), left for Emma to direct.
- **Queue step 5 (Sutra celestial restyle) done + PR opened.** Created Sutra branch `website-celestial`; added `web/celestial.css` (mirror of Yantra's bolder layer) and wired it into `scripts/build_site.py` (linked in the page `<head>`, copied into the built site). Sutra site is a custom static build (`build_site.py` from `docs/*.md` on the shared identity — not MkDocs). Render-verified locally (home page shows the celestial layer). Pushed; **PR EmmaLeonhart/Sutra#35** (docs/website-only, no language code touched). Step 6 (Sutra docs *content* pass) deferred to Emma — needs accurate review of the +300 commits and a call on whether safety-debranding applies to Sutra's technical "interpretable" framing.
- **Step 7 (verify) done inline.** Both sites render-verified via Playwright this session: Yantra dark+light (celestial + wedge copy, no safety/OS language), Sutra home (celestial layer loads). Yantra Pages green; Sutra PR build is docs/website-only.
- **Queue step 4 (Yantra copy pivot) done — Emma OK'd + "barrel through".** Front page pivoted off the OS / interpretable-neural-computer framing to the self-optimizing-landing-pages wedge (mechanism-forward headline "Your page, improving itself."). Stripped ALL AI-safety / interpretability / verifiability / critical-systems language (Emma: not a brand she wants anymore). Removed the paper CTA, bootloader bullet, financial/defense market section, and the co-founder/book-a-call asks. New sections: How it works / Why it's different / Built on Sutra (Sutra as enabling tech, not a safety story). Public-safe wording only. Render-verified; shipped to main; Pages deploys.
- **Queue step 3 (Yantra celestial layer) done.** `site/celestial.css` — a new layer linked after `identity.css` (shared identity untouched): deep-space field, cool periwinkle/cyan/violet nebula bloom, a glowing bloom behind the hero headline, twinkling starfield, fine grain, bloom on accent type/controls, gradient-hairline dividers. Dark-scoped; light theme stays calm. Render-verified both themes via Playwright; deployed via Pages (green). First pass was restrained; pushed bolder per Emma's call. Mirroring the look onto Sutra (step 5) waits on her confirm of the bolder intensity.
- **Decisions applied (Emma 2026-06-13):** archive dropped (keep all code); copy pivots to the self-optimizing-landing-pages wedge (mechanism-forward headline picked; full draft presented, awaiting sign-off); kernel/apps CI red is accepted (ignore — parked prototype, site Pages is green); one-shot PR cron set to PR `website-celestial`→Sutra main ~19:55 local; Sutra pin re-bumped to v0.7.1-747 on the 2-hourly tick.
- **Queue step 1 (audit) done** → `planning/24-website-repo-refocus.md`. Finding:
  most "non-website" code is NOT duplicated in Sutra (kernel, orchestrator,
  bootloader, paper, planning are Yantra-only); only `apps/{calc,echo,terminal}`
  are genuine Sutra duplicates. Two decisions raised for Emma (archive scope;
  current public positioning) that block queue steps 2/4/6. Step 3 (celestial CSS)
  is positioning-neutral and stays unblocked.
