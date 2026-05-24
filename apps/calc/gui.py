"""Yantra calculator — a button GUI over the Sutra substrate.

A normal desktop window (Tkinter): press buttons (or type), hit ``=``, and
the answer is **computed on the Sutra substrate** through the kernel by
the same `apps/calc` services the CLI uses. Press `5 * 10 =` and it shows
`50`; `2 + 3 * 4 =` shows `14`; a result it can't compute exactly
(`10 / 3`, division by zero) shows ``refused`` — never a wrong number.

This is the *optimal* contrast with Meta's NCCLIGen, which would
*generate* a plausible-looking calculator frame (and the digits can be
wrong). Here the frame is a plain GUI; the arithmetic is real and exact.

**What this is and isn't.** The window is a **host frontend** — Tkinter
on the CPU, the orchestrator's job per `planning/01-architecture.md`. It
is NOT the Yantra OS GUI layer (the Sutra-native, "everything is a
browser" stack), which is build-sequence milestone 3 and not built. The
buttons are orchestration; the math is substrate.

Run: ``python apps/calc/gui.py`` (or ``!runCalculatorGUI.bat``). First
launch compiles the ``.su`` services, so the window takes a few seconds.
"""
from __future__ import annotations

from calc import Calculator


class CalcController:
    """Tk-free controller: holds the on-screen expression and evaluates
    it on the substrate via :class:`Calculator`. Kept separate from the
    Tk widgets so the button logic is testable without a display.
    """

    _APPEND = set("0123456789+-*/() ")

    def __init__(self, calc: Calculator) -> None:
        self.calc = calc
        self.expr = ""
        self.display = "0"
        self._fresh = False  # a result is showing; a digit starts a new one

    def press(self, key: str) -> str:
        """Handle one key ('0'-'9', operator, '(', ')', 'C', '<', '='),
        update :attr:`display`, and return it."""
        if key == "C":
            self.expr, self.display, self._fresh = "", "0", False
        elif key in ("<", "Back"):
            self.expr = self.expr[:-1]
            self.display = self.expr or "0"
            self._fresh = False
        elif key == "=":
            if self.expr:
                try:
                    result = self.calc.evaluate(self.expr)
                    self.display = str(result)
                    self.expr = str(result)  # let the result chain forward
                except (ValueError, RuntimeError):
                    self.display = "refused"
                    self.expr = ""
                self._fresh = True
        elif key in self._APPEND:
            if self._fresh and key.isdigit():
                self.expr = ""  # typing a digit after a result starts over
            self.expr += key
            self.display = self.expr
            self._fresh = False
        # unknown keys are ignored
        return self.display


def main() -> None:  # pragma: no cover - opens a window
    import tkinter as tk

    print("Yantra calculator (GUI) — compiling Sutra services, please wait…")
    ctrl = CalcController(Calculator())

    BG, PANEL, FG, MUTE, KEY, KEY_HI = (
        "#161313", "#0d0b0b", "#e8d9b5", "#8a8276", "#2a2624", "#3a352f"
    )
    root = tk.Tk()
    root.title("Yantra Calculator — math on the Sutra substrate")
    root.configure(bg=BG)

    shown = tk.StringVar(value=ctrl.display)
    tk.Label(
        root, textvariable=shown, anchor="e", font=("Consolas", 30),
        bg=PANEL, fg=FG, padx=18, pady=18,
    ).grid(row=0, column=0, columnspan=4, sticky="nsew")
    tk.Label(
        root, text="computed on the Sutra substrate — exact, or refused",
        anchor="e", font=("Consolas", 8), bg=BG, fg=MUTE, padx=18,
    ).grid(row=1, column=0, columnspan=4, sticky="nsew")

    def on(key: str) -> None:
        shown.set(ctrl.press(key))

    layout = [
        ["C", "(", ")", "/"],
        ["7", "8", "9", "*"],
        ["4", "5", "6", "-"],
        ["1", "2", "3", "+"],
        ["0", "<", "=", None],
    ]
    for r, row in enumerate(layout, start=2):
        for c, key in enumerate(row):
            if key is None:
                continue
            label = "⌫" if key == "<" else key
            tk.Button(
                root, text=label, font=("Consolas", 16), width=4, height=2,
                bg=(KEY_HI if key in "=" else KEY), fg=FG,
                activebackground=KEY_HI, relief="flat", bd=1,
                command=lambda k=key: on(k),
            ).grid(row=r, column=c, sticky="nsew", padx=2, pady=2)
    for i in range(4):
        root.grid_columnconfigure(i, weight=1)

    def on_key(event: "tk.Event") -> None:
        if event.char in CalcController._APPEND and event.char.strip():
            on(event.char)
        elif event.keysym in ("Return", "KP_Enter", "equal"):
            on("=")
        elif event.keysym == "BackSpace":
            on("<")
        elif event.keysym in ("Escape", "Delete"):
            on("C")

    root.bind("<Key>", on_key)
    root.mainloop()


if __name__ == "__main__":  # pragma: no cover
    main()
