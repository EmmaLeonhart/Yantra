"""Yantra font demo -- the recurrent character-code stepper as an RNN.

Emma's text-input demo (2026-05-26, extended 2026-05-27). The window shows
ONE character at a time as a 5x5 pixel glyph. By default the substrate
advances the char_code every tick through the 36-glyph cycle
(A->B->...->Z->0->...->9->A). Press an A-Z or 0-9 key and the typed code
"takes the place" of the next advance -- substrate weighted sum, not a
host if.

Three substrate computations drive it (apps/font/font.su):

  cycle_step(prev_code, typed_code, has_typed)
      The recurrent step on the *character code*. Without override
      (has_typed=0.0), a 36-way defuzzified select advances prev_code to the
      next code in cycle order. With has_typed=1.0, the weighted sum
      `has_typed*typed + (1-has_typed)*advanced` lets typed_code win.

  step(prev_state, x, y, char_code)
      The recurrent step on the *pixel value*. ``prev*0 + glyph_pixel(...)``
      -- the * 0 is the substrate's explicit "forget previous state."

  glyph_pixel(x, y, char_code)
      Returns 1.0 if (x, y) is lit, else 0.0. 36-way defuzzified select
      over A-Z + 0-9, made one-hot by softmax saturation.

Usage:
    python apps/font/font_demo.py              # open window; auto-cycles, keys override
    python apps/font/font_demo.py --render A   # save A.png and exit (headless)
    python apps/font/font_demo.py --cell 40    # 5x5 glyph at 40px/cell = 200x200
    python apps/font/font_demo.py --fps 2      # cycle rate (default 2 fps)

The live window can't be checked headlessly (tkinter). The substrate parts
(step, cycle_step, glyph_pixel) ARE tested -- tests/test_font.py +
tests/test_font_cycle.py.
"""
from __future__ import annotations

import argparse
import pathlib
import sys

import numpy as np

_REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
_SUTRA_SDK = _REPO_ROOT / "external" / "Sutra" / "sdk" / "sutra-compiler"
if str(_SUTRA_SDK) not in sys.path:
    sys.path.insert(0, str(_SUTRA_SDK))

APPS_FONT = pathlib.Path(__file__).resolve().parent

# Compile cache: font.su is recompiled on the first call and reused. Compiling
# this .su is non-trivial (36 letter functions, each a 25-way select) -- doing
# it per keypress would be unusable. Memo dict mirrors counter_demo.py.
_COMPILED: dict = {}


def _compile():
    """Compile font.su and return its namespace.

    Delegates to ``sutra_compiler.compile_su`` (Sutra >= v0.7.1), which
    caches the emitted Python on disk so repeat runs skip the ~5-min
    codegen pass entirely. The bespoke cache logic that originally lived
    here moved into the SDK so every consumer (calc, gui, kernel, ...)
    gets the same benefit -- see commit fa89d359 in Sutra.
    """
    cached = _COMPILED.get("font.su")
    if cached is not None:
        return cached
    from sutra_compiler import compile_su
    mod = compile_su(
        APPS_FONT / "font.su",
        llm_model="nomic-embed-text",
        runtime_dim=768,
    )
    _COMPILED["font.su"] = mod.__dict__
    return mod.__dict__


def render_glyph(char_code: float, prev_field: np.ndarray | None = None) -> np.ndarray:
    """Render the 5x5 pixel field for the character at ``char_code``.

    Each cell is one substrate ``step(prev, x, y, char_code)`` call -- Emma's
    recurrent step on the substrate. ``prev_field`` is the previous frame; if
    None, treated as all-zero (initial state). The * 0 in the step discards
    prev regardless, so the SAME glyph comes out either way -- prev_field is
    threaded only to honour the recurrent shape (the substrate is what
    forgets, not the host).
    """
    ns = _compile()
    step, vsa = ns["step"], ns["_VSA"]

    if prev_field is None:
        prev_field = np.zeros((5, 5), dtype=np.float64)

    out = np.empty((5, 5), dtype=np.float64)
    for y in range(5):
        for x in range(5):
            prev_pix = vsa.make_real(float(prev_field[y, x]))
            new_pix = step(prev_pix, float(x), float(y), float(char_code))
            out[y, x] = float(vsa.real(new_pix))
    return out


def colormap(field: np.ndarray) -> np.ndarray:
    """5x5 brightness field -> uint8 RGB. White on black -- the cleanest read
    for a single-character display. Values are the substrate's; host only
    paints (clamp + scale)."""
    v = np.clip(field, 0.0, 1.0)
    g = (v * 255.0).astype(np.uint8)
    return np.stack([g, g, g], axis=-1)


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Yantra font demo (auto-cycles A-Z-0-9, keypress overrides; all on the substrate)")
    ap.add_argument("--render", metavar="CHAR",
                    help="render the given character and save CHAR.png; exit")
    ap.add_argument("--cell", type=int, default=40,
                    help="pixel size per glyph cell (default 40 -> 200x200 image)")
    ap.add_argument("--fps", type=float, default=2.0,
                    help="auto-cycle rate (default 2 frames/sec)")
    args = ap.parse_args()

    if args.render:
        from PIL import Image
        ch = args.render.upper()
        if len(ch) != 1 or not (ch.isalpha() or ch.isdigit()):
            raise SystemExit(f"--render expects one A-Z/0-9 char, got {args.render!r}")
        field = render_glyph(float(ord(ch)))
        img = Image.fromarray(colormap(field)).resize(
            (5 * args.cell, 5 * args.cell), Image.NEAREST)
        out = pathlib.Path(f"{ch}.png")
        img.save(out)
        print(f"[font] saved {out} (char {ch!r}, code {ord(ch)})")
        return

    # Pre-compile font.su BEFORE opening the window so the window doesn't sit
    # frozen on the first tick while Sutra codegen runs (~5 min on this machine,
    # instant after the on-disk cache is populated -- see _compile()).
    ns = _compile()
    cycle_step = ns["cycle_step"]

    import tkinter as tk
    from PIL import Image, ImageTk

    # State the host shuttles between substrate ticks:
    #   char_code    -- the current scalar code (the RNN's hidden state, decoded
    #                   from the substrate vector each tick via vsa.real()).
    #   field        -- the rendered 5x5 pixel field for that code.
    #   pending_typed -- the last typed code, or None. Set by on_key, cleared
    #                   by tick. The tick passes it to cycle_step as the
    #                   typed-code branch.
    state = {
        "char_code": float(ord("A")),
        "field": np.zeros((5, 5), dtype=np.float64),
        "pending_typed": None,
    }
    tick_ms = max(50, int(1000.0 / max(0.1, args.fps)))

    def make_photo(field: np.ndarray):
        img = Image.fromarray(colormap(field)).resize(
            (5 * args.cell, 5 * args.cell), Image.NEAREST)
        return ImageTk.PhotoImage(img)

    # The window is intentionally minimal — only the 5x5 pixel grid in the
    # middle is substrate output. No status label, no chatty title. Anything
    # painted by tkinter (fonts, borders, the title bar text the OS draws) is
    # host chrome; only the centre image is the substrate's product.
    root = tk.Tk()
    root.title("font")
    root.configure(bg="black")
    photo0 = make_photo(state["field"])
    label = tk.Label(root, image=photo0, bg="black", borderwidth=0)
    label.image = photo0
    label.pack(padx=args.cell, pady=args.cell)

    def tick():
        # Substrate-recurrent step on the char_code. Without a key, the
        # 36-way defuzzified select advances the code one step in cycle order.
        # With a pending key, has_typed=1.0 and the typed code wins via the
        # weighted-sum gate -- no host if.
        has_typed = 1.0 if state["pending_typed"] is not None else 0.0
        typed = float(state["pending_typed"]) if has_typed else 0.0
        next_code_vec = cycle_step(state["char_code"], typed, has_typed)
        next_code = float(ns["_VSA"].real(next_code_vec))
        state["pending_typed"] = None
        # Round to the nearest integer codepoint -- the defuzzified select is
        # exact in float64, but a defensive round() guards against any drift
        # from the typed override (typed_vec * 1.0 is exact, but be careful).
        state["char_code"] = float(round(next_code))

        # Render the 25-cell pixel field for the new code. This is the expensive
        # part (22500 substrate branches via the existing glyph_pixel design);
        # the cycle_step itself is one 36-way select on top.
        new_field = render_glyph(state["char_code"], prev_field=state["field"])
        state["field"] = new_field
        photo = make_photo(new_field)
        label.configure(image=photo)
        label.image = photo
        ch = chr(int(state["char_code"]))
        # Stdout (not the window) for debug — strictly host I/O, not painted
        # anywhere the user could confuse for substrate output.
        print(f"[font] tick -> code {int(state['char_code'])} ({ch!r})", flush=True)
        root.after(tick_ms, tick)

    def on_key(event):
        ch = (event.char or "").upper()
        if len(ch) != 1 or not (ch.isalpha() or ch.isdigit()):
            return
        if ch.isalpha() and ch not in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            return
        # Stash the typed code; the next tick passes it to cycle_step with
        # has_typed=1.0 and the substrate weighted-sum gate picks it.
        state["pending_typed"] = ord(ch)
        print(f"[font] keypress {ch!r} -> pending override (substrate decides next tick)", flush=True)

    root.bind("<Key>", on_key)
    root.after(tick_ms, tick)
    root.mainloop()


if __name__ == "__main__":
    main()
