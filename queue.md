# Yantra — Work Queue

**This file is a queue, not a state snapshot.** It lists what is being worked on right now. Finished work lives in `git log` and `devlog.md`; longer-horizon ideas live in `planning/` or `todo.md`. When an item is done, delete it — no checkmarks, no status indicators. If an item is still here, it is not done.

See `CLAUDE.md` § "Workflow Rules" and `todo.md` for longer-horizon items.

---

## SESSION DIRECTION — wind-down & loose-ends cleanup (Emma 2026-06-16)

Yantra is winding down / rebranding to **Noldor Technologies**. `yantraos.org`
redirects to `noldor.tech` (PR #1, cutover 2026-06-18 3pm Pacific, driven by a
local cron + the sitemap in the noldor data lake). This session clears loose
ends. Session crons running: work-loop `:03`, auto-flush `:15`, status `:42`.

**Standing rails:** kernel/apps pytest CI is red and ACCEPTED (Emma: "ignore
it") — Pages deploys green; don't fix it, one-line it at most. Never force-push;
leave the `external/Sutra` pin to the 6am job; cross-repo Sutra edits commit +
push on Sutra `main` per `CLAUDE.md` § "Cross-repo workflow".

---

## Active — cleanup

1. **Delete `apps/gui-rust`.** It's a thin Rust `minifb` wrapper that
   subprocess-calls `external/Sutra/demos/gui/`, which has the real demo. Remove
   the directory; update `apps/README.md` to drop the reference and point at the
   Sutra gui demo.

2. **Consolidate `apps/calc`.** Yantra's copy has substrate-parsing `.su` that
   Sutra's `demos/calc/` lacks (`parse_op.su`, `parse_int2.su`). Cross-repo:
   copy those two `.su` into `external/Sutra/demos/calc/`, commit + push on Sutra
   `main`. Then reduce Yantra `apps/calc` to the thin kernel-routing demo
   (`calc.py` wrapper) or drop it; update `apps/README.md`. Don't lose the
   parsing work.

3. **Stop the daily-audit queue spam.** `.github/workflows/daily-audit.yml`
   prepends a substrate-honesty audit item to `queue.md` daily. The repo does no
   `.su` work now. Disable the `schedule:` trigger (keep the file, reversible);
   note it in `devlog.md`.

4. **Reconcile docs to the rebrand.** `README.md`: add a short note that the
   site redirects to noldor.tech and OS/language work lives in Sutra. Light
   touch — don't rewrite the whole README.

---

## Always last (pinned tail)

Y. **Ensure the three session crons are running** (work-loop `:03`, auto-flush
   `:15`, status `:42`) — start/restart if a planning burst killed them.

Z. **Run an end-of-session status report** — everything that advanced this
   session, queue state, rails held, blockers.

---

## Pointers

- Longer-horizon: `todo.md` (see "Project wind-down & loose-ends cleanup")
- Content audit: `CONTENT_AUDIT.md`
- Rebrand redirect: Yantra PR #1; sitemap in `noldor` repo `data_lake/`
- Cross-repo workflow: `CLAUDE.md` § "Cross-repo workflow"
- History: `git log`, `devlog.md`
