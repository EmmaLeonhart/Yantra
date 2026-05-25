"""Yantra's first INTERACTIVE GUI — click to toggle the glow red <-> blue.

Two substrate computations drive it:
  - frame.su's pixel(x, y) computes the glow field (brightness 1 - x^2 - y^2),
  - toggle.su's flip(s) flips the 0/1 colour state on the substrate (1 - s).

On every click the host calls flip(state) on the substrate to get the new state,
then recolours: state 0 -> red glow, state 1 -> blue glow. The host does only
event delivery (the click) and painting; the field and the state transition are
substrate computations — the same host-is-I/O split as the calculator.

Usage:
    python apps/gui/click_demo.py                  # open the window; click to toggle
    python apps/gui/click_demo.py --render out      # save out_red.png + out_blue.png
    python apps/gui/click_demo.py --size 64

This is the first interactive GUI proof of concept (planning/24-first-gui.md).
The live window + click can't be checked headlessly; --render verifies the two
substrate-coloured frames.
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

APPS_GUI = pathlib.Path(__file__).resolve().parent


def _compile(su_name: str):
    """Compile a .su under apps/gui and return its namespace (functions + _VSA)."""
    from sutra_compiler.codegen_pytorch import translate_module as torch_translate
    from sutra_compiler.lexer import Lexer
    from sutra_compiler.parser import Parser

    src = (APPS_GUI / su_name).read_text(encoding="utf-8")
    lexer = Lexer(src, file=su_name)
    toks = lexer.tokenize()
    parser = Parser(toks, file=su_name, diagnostics=lexer.diagnostics)
    module = parser.parse_module()
    if lexer.diagnostics.has_errors():
        raise SystemExit(f"{su_name} parse error: {list(lexer.diagnostics)}")
    py = torch_translate(module, llm_model="nomic-embed-text", runtime_dim=768)
    ns: dict = {}
    exec(compile(py, su_name, "exec"), ns)
    return ns


def render_field(size: int = 64) -> np.ndarray:
    """(size, size) brightness field, each cell a substrate pixel(x, y) call."""
    ns = _compile("frame.su")
    pixel, vsa = ns["pixel"], ns["_VSA"]
    field = np.empty((size, size), dtype=np.float64)
    for j in range(size):
        cy = 2.0 * j / (size - 1) - 1.0
        for i in range(size):
            cx = 2.0 * i / (size - 1) - 1.0
            field[j, i] = float(vsa.real(pixel(cx, cy)))
    return field


def tint(field: np.ndarray, state: float) -> np.ndarray:
    """Colour the glow by the substrate STATE: 0 -> red, 1 -> blue.

    Brightness comes from the (substrate) field; which channel it lights comes
    from the (substrate) state. black -> hue -> white ramp.
    """
    v = np.clip(field, 0.0, 1.0)
    hot = np.clip(2.0 * v, 0, 1)        # primary hue channel
    rest = np.clip(2.0 * v - 1.0, 0, 1)  # whitens toward the centre
    if round(float(state)) == 0:  # red
        rgb = np.stack([hot, rest, rest], axis=-1)
    else:  # blue
        rgb = np.stack([rest, rest, hot], axis=-1)
    return (rgb * 255).astype(np.uint8)


class _Flip:
    """Substrate-backed 0/1 state: each step is toggle.su's flip() on the substrate."""

    def __init__(self) -> None:
        ns = _compile("toggle.su")
        self._flip, self._vsa = ns["flip"], ns["_VSA"]
        self.state = 0.0

    def toggle(self) -> float:
        self.state = float(self._vsa.real(self._flip(self.state)))  # SUBSTRATE flip
        return self.state


def main() -> None:
    ap = argparse.ArgumentParser(description="Yantra first interactive GUI (click toggles red/blue)")
    ap.add_argument("--render", metavar="PREFIX", help="save PREFIX_red.png + PREFIX_blue.png and exit")
    ap.add_argument("--size", type=int, default=64)
    args = ap.parse_args()

    field = render_field(args.size)

    if args.render:
        from PIL import Image
        for state, name in ((0.0, "red"), (1.0, "blue")):
            img = Image.fromarray(tint(field, state)).resize(
                (args.size * 8, args.size * 8), Image.NEAREST)
            img.save(f"{args.render}_{name}.png")
            print(f"[gui] saved {args.render}_{name}.png (state={state})")
        return

    import tkinter as tk
    from PIL import Image, ImageTk

    flipper = _Flip()

    def make_photo(state: float):
        img = Image.fromarray(tint(field, state)).resize(
            (args.size * 8, args.size * 8), Image.NEAREST)
        return ImageTk.PhotoImage(img)

    root = tk.Tk()
    root.title("Yantra — click to toggle red/blue (state flips on the substrate)")
    label = tk.Label(root, image=make_photo(flipper.state))
    label.pack()

    def on_click(_event):
        state = flipper.toggle()  # substrate flip
        photo = make_photo(state)
        label.configure(image=photo)
        label.image = photo  # keep a ref

    label.bind("<Button-1>", on_click)
    root.bind("<Button-1>", on_click)
    tk.Label(root, text="click anywhere — the colour state flips on the Sutra substrate").pack()
    root.mainloop()


if __name__ == "__main__":
    main()
