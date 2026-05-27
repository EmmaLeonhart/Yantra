# 26 — Font rewrite: per-character bound-vector, drop the 25-way inner switch

**Status:** queued; cycle demo (Emma 2026-05-27) shipped on the old renderer
first. This is the follow-up.

**Trigger:** Emma 2026-05-27, looking at the font demo:

> I just feel like it's, I feel like you might be doing you. I don't
> understand how there would be so much branching in it.
> ...
> A 20,000-thing switch is just, it's just, it's not.

She's right. The current `apps/font/font.su` design pays **~22,500 inner-select
branches per keypress**. That is not "the cost of substrate purity" — it is
a switch-as-lookup-table antipattern. The substrate has a clean primitive for
this (rotation-binding); the current code reaches past it.

## What the existing design does

`glyph_pixel(x, y, char_code)` is two nested defuzzified selects:

1. **Outer 36-way select** over `char_code`: picks one of `bit_A(pos)` ..
   `bit_9(pos)` (where `pos = y*5 + x`).
2. **Inner 25-way select** inside each `bit_<C>(pos)`: picks the lit/unlit bit
   at position `pos` for character `<C>` from a hardcoded 25-element list.

Per cell: 36 × 25 = 900 inner-select branches (every `bit_<C>` evaluates all
25 of its branches because defuzzified select computes every branch — that's
the whole point of substrate dispatch). Per keypress (25 cells): 22,500.

The inner 25-way switch is the antipattern. A 25-bit lookup table should be
*one bound value*, not a 25-way switch over scalars.

## The bound-vector design

Each character is a **single bundle of rotation-bindings**, one binding per
position. The position acts as the role; the lit/unlit marker acts as the
filler. To read the bit at (x, y), unbind the corresponding position vector
from the glyph bundle and check cosine similarity to the lit marker.

```sutra
// Position basis vectors — 25 distinct rotation roles, one per cell.
vector p_00 = basis_vector("font_pos_00");
vector p_01 = basis_vector("font_pos_01");
...
vector p_24 = basis_vector("font_pos_24");

// Lit / unlit markers — fillers.
vector LIT   = basis_vector("font_lit");
vector UNLIT = basis_vector("font_unlit");

// Each glyph is a single bundle of 25 bindings.
vector glyph_A = bundle(
    bind(p_00, UNLIT), bind(p_01, LIT), bind(p_02, LIT), bind(p_03, LIT), bind(p_04, UNLIT),
    bind(p_05, LIT),   bind(p_06, UNLIT), ..., bind(p_24, LIT)
);
... glyph_B, glyph_C, ..., glyph_9 ...

// Outer 36-way select — pick which glyph by char_code. SAME pattern as
// today's glyph_pixel outer, just over glyph bundles instead of bit_<C> calls.
function vector lookup_glyph(scalar char_code) {
    scalar s_A = 0.0 - 1000.0 * (char_code - 65.0) * (char_code - 65.0);
    ...
    return select([s_A, s_B, ..., s_d9], [glyph_A, glyph_B, ..., glyph_9]);
}

// Per-cell: unbind the position from the picked glyph, then similarity to LIT.
function vector glyph_pixel(scalar x, scalar y, scalar char_code) {
    vector glyph = lookup_glyph(char_code);
    vector pos = lookup_position(x, y);   // 25-way select over (x, y) → p_NN
    vector bit_vec = unbind(pos, glyph);
    // Return similarity to LIT, lifted onto the real axis. Fuzzy: ~1 for lit,
    // ~0 for unlit, with rotation-binding noise at the 25-item capacity.
    scalar sim = cosine_similarity(bit_vec, LIT);
    return make_real(sim);
}
```

**Per-cell cost:**

- 1 outer 36-way select (36 branches over scalars + 36 vector picks) — same
  as today's outer.
- 1 inner 25-way select (`lookup_position`) — 25 branches over scalars + 25
  vector picks. This is the cost we couldn't get rid of: scalar `(x, y)` →
  vector `p_NN` requires *some* switch. **But the inner select is now over
  the SAME 25 position vectors for ALL 36 characters**, not 36 separate
  25-way switches per character. We pay 25 once per cell, not 25 × 36.
- 1 unbind.
- 1 cosine_similarity.

**Total per cell:** ~36 + 25 + 2 = ~63 ops. **Per keypress (25 cells):
~1,575 ops.** That's **~14× fewer than the current 22,500**.

Could go further by having the host loop over the 25 positions outside
the substrate (so the inner `lookup_position` select happens 25 times total,
not per cell) — but that's the same shape `render_glyph` already has, just
moved one level out. Marginal improvement, optional.

## What's fuzzy and what's exact

Today: `glyph_pixel` returns *exactly* 0.0 or 1.0 in float64 because the
defuzzified select uses softmax-saturation with exp(-1000) underflowing to
literal 0. Test tolerance is `1e-9`.

After rewrite: `glyph_pixel` returns the **cosine similarity to LIT** of an
unbound vector. With 25 items bound into a 768-d vector, the lit cells
return cos ≈ 1.0 minus binding-capacity noise; the unlit cells return cos
≈ 0.0 plus noise. Realistic measurement gap: maybe 0.7 between lit and
unlit on average, but with outliers.

**Test tolerance changes from `1e-9` to ~`1e-1`.** That's a real semantic
shift in what the test asserts. The host can still threshold to 0/1 for
display (`np.where(field > 0.5, 1.0, 0.0)`), but the substrate output is
genuinely fuzzy.

This is the Sutra philosophy — fuzzy by default, defuzzification is a
deliberate choice. The current code defuzzifies inside the substrate via
softmax-saturation; the rewrite defuzzifies via cosine threshold on the
host display layer (or substrate `is_true` if we want it truly substrate-
pure).

## Risks and unknowns

1. **Rotation-binding capacity at N=25 in 768-d.** Need to measure
   empirically. The Sutra paper covers width-k bundle decoding at small k;
   25 is bigger. If the noise floor is too high (say lit and unlit overlap),
   the design fails.
2. **`basis_vector(...)` is an Ollama embedding call.** 25 position vectors
   + LIT + UNLIT = 27 Ollama calls at module load. Cached after, but a fresh
   compile is slower. The 36 glyph bundles are computed from those, not
   embedded.
3. **`cosine_similarity` and `make_real` interaction.** Need to verify
   `make_real(cosine_similarity(...))` lifts the scalar similarity to a
   real-axis vector that the existing `step()` recurrent shape can consume.
4. **Existing tests break.** `test_font.py` asserts `1e-9` tolerance per
   cell. The rewrite makes those tolerances impossible. Either:
   - Loosen them to ~`1e-1` (acknowledging fuzziness).
   - Threshold the field via `is_true` in `glyph_pixel` to keep the 0/1
     contract; tolerance becomes "after threshold, exact." That's substrate-
     defuzzification, not host-defuzzification — feels cleaner.

## Plan when this gets done

1. **Write `apps/font/font_bound.su` as a parallel file** — do not touch
   `font.su`. Both compile.
2. **Write a smoke test** — one glyph (`A`), one cell, end-to-end through
   the new path. Measures actual cosine_lit vs cosine_unlit on this machine.
   If the gap is < 0.3, stop and rethink.
3. **If smoke passes, expand**: all 36 glyphs, all 25 cells, measured
   accuracy vs the font oracle.
4. **Decide defuzzification path**: substrate `is_true` threshold inside
   `glyph_pixel` (keeps 0/1 contract), or host threshold in `render_glyph`
   (clean separation).
5. **Plumb into `font_demo.py`** behind a `--bound` flag — old path still
   works while the new one is bedded in.
6. **Switch the default once stable**, retire `font.su` + `bit_<C>` family
   (delete; this is vibe-coded project, legacy paths cause more harm than
   benefit per Sutra's CLAUDE.md).
7. **Update the cycle_step demo** — `cycle_step` itself is unchanged
   (operates on `char_code`, doesn't care how `glyph_pixel` is implemented).

## Why this is queued, not done today

The cycle demo is the user-visible work Emma asked for in this session:
shipped at commit `3d8dae4`. The bound-vector rewrite is substantial
(parallel .su file, new tests, fuzziness tolerance change, empirical
capacity measurement) — half-doing it would be worse than not doing it
because the existing demo still works and is visibly the recurrent step
Emma wanted to see.
