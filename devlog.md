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
- **Queue step 1 (audit) done** → `planning/24-website-repo-refocus.md`. Finding:
  most "non-website" code is NOT duplicated in Sutra (kernel, orchestrator,
  bootloader, paper, planning are Yantra-only); only `apps/{calc,echo,terminal}`
  are genuine Sutra duplicates. Two decisions raised for Emma (archive scope;
  current public positioning) that block queue steps 2/4/6. Step 3 (celestial CSS)
  is positioning-neutral and stays unblocked.
