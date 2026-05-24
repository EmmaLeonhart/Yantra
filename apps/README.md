# `apps/` — native Sutra userspace utilities

Per `planning/07-transpilers.md` and `todo.md` § 2: userspace
utilities are written **natively in Sutra** here. GNU coreutils /
util-linux behaviour is the conceptual reference for these native
rewrites; no vendored Linux source is kept in-tree. Each
utility ships as its own subdirectory with a `.su` source +
manifest TOML + (eventually) a CLI shim once Sutra has
stdin/stdout vocabulary that doesn't go through axon-passing.

## What ships today

| Utility | Status | Notes |
|---|---|---|
| `echo/` | First v0 (2026-05-14) | Routes input axon's `stdin_text` key to the output's `stdout_text`. Real Sutra service, real `.su` source, real manifest, admitted by the kernel via the same `Init.admit_from_path` path the kernel-services use. The smallest end-to-end demonstration that `apps/` works as a milestone. |

## What's coming (not started)

Per `todo.md` § 2 Q-list, in priority order: `cat`, `ls`, `wc`,
`head/tail`, then mid-wave (`grep`, `cut/tr`, `sort/uniq`, `find`,
`mv/cp/rm`), then late-wave (`awk`, `sed`). Each is gated on the
Sutra-side string + IO + FS vocabulary maturing — `echo` works
today because it's pure axon round-trip; `cat` needs real file
reading; `ls` needs directory iteration; `awk` needs an interior
DSL. Nothing's blocked on Yantra-side decisions.

## Pattern for adding a new utility

1. Create `apps/<name>/<name>.su` exporting `function vector
   on_axon(vector input_axon)`.
2. Create `apps/<name>/<name>.toml` with manifest fields:
   `name`, `axon_width`, `compute_units`, `read_roles`,
   `write_roles`, `axon_keys` (optional), `source`.
3. Add a smoke test under `tests/test_apps_<name>.py` that admits
   the service via the kernel and verifies the round-trip.
4. Add a row to the table above.

The kernel admits an `apps/` service the same way it admits a
`kernel/services/` one — the distinction is documentary
(kernel-shaped vs userspace-shaped), not structural.
