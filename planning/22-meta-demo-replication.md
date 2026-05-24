# Meta-demo replication — the symbol-stable Neural Computer demo

## Why this is the demo that matters

Meta's *Neural Computers* (Schmidhuber et al., arXiv:2604.06425, 2026)
shipped two prototypes:

- **CLIGen** — a generative (video-diffusion-style) model of a
  terminal: given a prompt + user keystrokes, it rolls out *plausible
  terminal screen frames*.
- **GUIWorld** — the same idea for a desktop: it rolls out plausible
  desktop GUI frames from user actions.

Their own paper enumerates the failure modes: **poor symbolic
stability** (text and symbols drift / garble over time), weak
long-horizon reasoning, no robust reuse of routines, behaviour drift.

Yantra's posture is the opposite: **neural execution, not neural
simulation.** A terminal on Yantra is a real Sutra program whose
output is *computed*, not *generated*; a desktop is a real
browser-rendered UI whose state is *maintained*, not *diffused*. So
the decisive demonstration is to reproduce both Meta prototypes on
Yantra and show the one thing their approach structurally cannot give:
**the symbols stay exact, indefinitely.**

Done definitively — the same surface (a terminal, a desktop), their
approach drifting and losing symbols while ours stays bit-exact over a
long horizon — this is the single strongest piece of external evidence
that the design works. It is competence made visible.

## The two target demos

### Demo 1 — Terminal (the answer to CLIGen)

A real terminal where typed commands actually execute as Sutra
userspace programs and the rendered text is exact. Where CLIGen
*hallucinates* plausible output, Yantra *computes* it; symbol
stability is perfect by construction.

### Demo 2 — Desktop / GUI (the answer to GUIWorld)

A browser-rendered desktop (the GUI build-sequence layer) whose widget
state, labels, and on-screen text are maintained exactly across
arbitrary interaction. Where GUIWorld diffuses frames, Yantra renders
real UI state.

## "Maintaining the symbols", made measurable

The claim is not vibes — it is exact-match symbol fidelity over a long
horizon. The protocol:

1. Define a scripted interaction trace of N steps (commands / UI
   actions), N large.
2. Record every symbol that *should* appear: command output text, file
   names, numeric results, widget labels.
3. **Yantra target: 100% exact match at every step, with zero drift as
   N grows** — because it is executing the program, not predicting
   frames.
4. Contrast baseline: a generative screen-frame model (the
   CLIGen / GUIWorld posture) degrades in symbol fidelity as N grows.
   The plot of *symbol-fidelity vs. horizon* — Yantra flat at 100%,
   the generative baseline decaying — is the figure that tells the
   whole story.

This rides on the Sutra empirical foundation: exact symbol round-trips
are already what the substrate does (100% bundle decoding through
width k=8; ~1.5×10⁻¹⁵ bind/unbind round-trip — Sutra paper). The
kernel already round-trips a symbol exactly today (`apps/echo`:
`stdin_text` → `stdout_text`, bit-exact). The demos scale that
guarantee up to a terminal and a desktop.

## Roadmap — current state → the two demos

Gated on the existing build sequence (`planning/18` § Build sequence:
kernel → CLI → GUI). What each stage unlocks:

**Stage 0 — already true (the proof in miniature).** The Connectome
Manager round-trips symbols exactly through the axon router;
`apps/echo` is a real Sutra program that preserves text bit-exact.
This is the symbol-stability claim in the small.

**Stage 1 — exact-symbol terminal (Demo 1).** Needs:
- The CLI userspace utilities (`todo.md` § 2: cat, ls, wc, grep, …) as
  native Sutra programs.
- A terminal / shell surface — a Sutra-native REPL or minimal shell
  that reads a command line, admits/runs the utility through the
  kernel, and prints exact output.
- Real stdin/stdout streams (blocked on Sutra's string + IO + FS
  vocabulary maturing).
- Deliverable: a recorded terminal session running a long scripted
  command trace with 100% exact output, framed against CLIGen's drift.

**Stage 2 — exact-symbol desktop (Demo 2).** Needs the GUI layer
(`planning/06`, build-sequence milestone 3):
- The Sutra-native renderer (layout engine + display server consuming
  / emitting framebuffer axons) — writable in Sutra, sequenced third.
- A minimal browser-rendered desktop with a few stateful widgets.
- Deliverable: a long UI interaction trace where widget state +
  on-screen symbols stay exact, framed against GUIWorld's drift.

**Stage 3 — the figure.** The symbol-fidelity-vs-horizon plot: Yantra
flat at 100%, the generative baseline degrading. The headline result.

## Dependencies — what is not built

- Stage 1 is blocked on Sutra's string / IO / FS vocabulary and the
  kernel `.su` loader maturing, plus the CLI utilities themselves
  (only `echo` exists).
- Stage 2 is blocked on the entire GUI layer: the Sutra-native
  renderer, an HTML/CSS layout engine (not built in any form), and
  WebGL bindings (planned, not implemented). See `planning/18`
  § Browser.
- The contrast baseline has to be obtained or reproduced — re-run a
  CLIGen / GUIWorld-shaped generative model, or cite Meta's own
  reported degradation.

None of this is near-term; it is the headline *application* milestone
that rides on the build sequence. But Stage 0 already holds and the
contrast is conceptually decided — the roadmap scales an existing
exact-round-trip guarantee up to a terminal and a desktop, it does not
invent a new capability.

## Open questions

- **How large must N be** for the contrast to be unanswerable? Pick a
  horizon long enough that any generative model has visibly drifted.
- **Which generative baseline** to measure against — a re-implemented
  CLIGen/GUIWorld stand-in, an off-the-shelf screen-frame diffusion
  model, or Meta's own published numbers.
- **Cheapest convincing Stage 1** — can a minimal shell + three or
  four utilities already carry the terminal demo, before the full
  Q-list in `todo.md` § 2 lands?

## Cross-references

- `planning/16-related-work.md` — the Meta *Neural Computers* contrast.
- `paper/paper.md` § 7 — related-work framing (simulation vs.
  execution).
- `planning/18-kernel-browser-readiness.md` — build-sequence gating and
  what is built.
- `todo.md` § 5 — this as a tracked ambition.
