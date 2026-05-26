"""Yantra font demo -- type a letter, see it rendered on the substrate.

Emma's text-input demo (2026-05-26). Press any A-Z or 0-9 key; the window
shows that character as a 5x5 pixel glyph. Two substrate computations drive
it (apps/font/font.su):

  step(prev_state, x, y, char_code)
      The recurrent step. The current pixel value at (x, y) is the state;
      on a new keypress, `state = prev*0 + glyph_pixel(...)` -- the * 0 is
      the substrate's explicit "forget previous state," the + is the
      substrate's "add the new input." Same shape as toggle.su's flip and
      count.su's +1 (the host is the register; the arithmetic is the
      substrate).

  glyph_pixel(x, y, char_code)
      Returns 1.0 if (x, y) is lit for the typed character, else 0.0.
      Decided ON the substrate by a 36-way defuzzified `select` over A-Z +
      0-9 (made one-hot by softmax saturation -- same trick switch.su uses
      for the calc's operator dispatch). No host font lookup on the runtime
      path; only the displayed pixels are host-painted (tint + scale).

Usage:
    python apps/font/font_demo.py              # open the window; press keys
    python apps/font/font_demo.py --render A   # save A.png and exit (headless)
    python apps/font/font_demo.py --cell 40    # 5x5 glyph at 40px/cell = 200x200

The live window + keypress can't be checked headlessly (tkinter). The
substrate parts (step, glyph_pixel) ARE tested -- tests/test_font.py covers
each of the 36 glyphs.
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
        description="Yantra font demo (type a letter, glyph decided on the substrate)")
    ap.add_argument("--render", metavar="CHAR",
                    help="render the given character and save CHAR.png; exit")
    ap.add_argument("--cell", type=int, default=40,
                    help="pixel size per glyph cell (default 40 -> 200x200 image)")
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
    # frozen on first keypress while Sutra codegen runs (~5 min on this machine,
    # instant after the on-disk cache is populated -- see _compile()). The
    # printout above tells the user what's happening so the wait isn't a black
    # box. After this returns, every keypress is fast.
    _compile()

    import tkinter as tk
    from PIL import Image, ImageTk

    state = {"field": np.zeros((5, 5), dtype=np.float64), "char": None}

    def make_photo(field: np.ndarray):
        img = Image.fromarray(colormap(field)).resize(
            (5 * args.cell, 5 * args.cell), Image.NEAREST)
        return ImageTk.PhotoImage(img)

    root = tk.Tk()
    root.title("Yantra font -- press A-Z or 0-9 (glyph decided on the substrate)")
    # Black background on the toplevel so the padding around the glyph reads as
    # one continuous frame instead of grey-stripe-around-black-rectangle.
    root.configure(bg="black")
    photo0 = make_photo(state["field"])
    label = tk.Label(root, image=photo0, bg="black", borderwidth=0)
    label.image = photo0
    # Padding around the 5x5 glyph: at default cell=40 the glyph is 200x200, so
    # 1 cell of breathing room each side = 40 px gives the character a frame to
    # sit in instead of sitting flush against the window chrome.
    label.pack(padx=args.cell, pady=args.cell)
    status = tk.Label(
        root, bg="black", fg="#aaaaaa",
        text="press any A-Z or 0-9 key -- step(prev, x, y, code) runs on the Sutra substrate")
    status.pack(padx=args.cell, pady=(0, args.cell // 2))

    def on_key(event):
        ch = (event.char or "").upper()
        if len(ch) != 1 or not (ch.isalpha() or ch.isdigit()):
            return  # ignore modifiers, arrows, etc.
        if ch.isalpha() and ch not in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            return
        # Substrate step for every cell: prev*0 + glyph_pixel(...). The new
        # field overwrites the host-held register (state["field"]).
        new_field = render_glyph(float(ord(ch)), prev_field=state["field"])
        state["field"] = new_field
        state["char"] = ch
        photo = make_photo(new_field)
        label.configure(image=photo)
        label.image = photo
        root.title(f"Yantra font -- {ch} (glyph from substrate)")
        status.configure(
            text=f"showing {ch!r} (code {ord(ch)}) -- step ran 25x on the substrate; prev*0 forgot the old glyph")
        print(f"[font] key {ch!r} (code {ord(ch)}) -> substrate step -> 5x5 glyph", flush=True)

    root.bind("<Key>", on_key)
    root.mainloop()


if __name__ == "__main__":
    main()
