import tkinter as tk
from tkinter import font as tkfont
import json
import queue
import random
import re
import threading
import urllib.request


# ---------------------------------------------------------------------------
# Computation hook
# ---------------------------------------------------------------------------
# Whatever is on the display (ANY text: "12 × 3", "sin(30)", "qual a raiz de
# banana?") is sent to the local Ollama model when you press "=" / Enter, and
# whatever it answers is shown as the result.
# It runs on a background thread, so a slow answer won't freeze the window.
OLLAMA_URL = "http://localhost:11434/api/chat"
OLLAMA_MODEL = "mac-calculator-gemma"   # "qwen3-vl:8b" is smarter but very heavy
THINK = False       # True lets thinking models (qwen) reason first; gemma doesn't support it
TEMPERATURE = 0.2   # higher = more creative (and more wrong) answers
TIMEOUT = 900       # seconds to wait for an answer

# Overrides the model's built-in prompt. Small models copy whatever examples
# they see, so the examples are varied and given as real chat turns.
SYSTEM_PROMPT = (
    "You are a pocket calculator. The user types an expression. Reply with ONLY the final result: "
    "one number, no words, no units, no explanation. Compute it fresh every time. "
    "If the input is not math, never refuse and never say it isn't math: answer it anyway "
    "in one short, confident line, in the same language as the question (English if unsure)."
)
EXAMPLES = [
    ("3+5", "8"), ("6*7+2", "44"), ("100/8", "12.5"), ("9-14", "-5"), ("2^8", "256"),
    ("sqrt(81)", "9"), ("6!", "720"), ("20%", "0.2"), ("8*5-3", "37"), ("cos(60)", "0.5"),
    ("pi*3", "9.424778"), ("1.5*4", "6"), ("11*11", "121"),
]
# Display symbols -> plain notation the model understands better
NOTATION = [
    ("×", "*"), ("÷", "/"), ("−", "-"), ("√(", "sqrt("), ("∛(", "cbrt("), ("π", "pi"),
    ("²", "^2"), ("³", "^3"), ("log₁₀(", "log10("), ("log₂(", "log2("),
    ("sin⁻¹(", "asin("), ("cos⁻¹(", "acos("), ("tan⁻¹(", "atan("),
    ("sinh⁻¹(", "asinh("), ("cosh⁻¹(", "acosh("), ("tanh⁻¹(", "atanh("),
]


def compute(expression: str, degrees: bool = True) -> str:
    for symbol, plain in NOTATION:
        expression = expression.replace(symbol, plain)
    system = SYSTEM_PROMPT + ("" if degrees else " Trigonometric functions use radians.")
    messages = [{"role": "system", "content": system}]
    for question, answer in EXAMPLES:
        messages += [{"role": "user", "content": question}, {"role": "assistant", "content": answer}]
    messages.append({"role": "user", "content": expression})
    body = json.dumps({"model": OLLAMA_MODEL, "messages": messages, "stream": False, "think": THINK,
                       "options": {"temperature": TEMPERATURE}}).encode()
    request = urllib.request.Request(OLLAMA_URL, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
        return json.load(response)["message"]["content"].strip()


# ---------------------------------------------------------------------------
# Look (macOS Sequoia Calculator, dark)
# ---------------------------------------------------------------------------
WINDOW_BG = "#282828"
DIGIT_BG = "#4E4E4E"
FUNC_BG = "#656565"     # ⌫/AC  ±  %
SCI_BG = "#3B3B3B"      # scientific keys
OP_BG = "#FF9F0A"       # ÷ × − + =
TEXT = "#FFFFFF"
DIM_TEXT = "#9A9A9A"

OPS = ("÷", "×", "−", "+")


def lighten(hex_color, amount=0.3):
    r, g, b = (int(hex_color[i:i + 2], 16) for i in (1, 3, 5))
    r, g, b = (int(c + (255 - c) * amount) for c in (r, g, b))
    return f"#{r:02x}{g:02x}{b:02x}"


def pick_font(*names):
    available = set(tkfont.families())
    return next((n for n in names if n in available), "Helvetica")


# (id, label, label with 2nd on)
SCI_ROWS = [
    [("(", "(", None), (")", ")", None), ("mc", "mc", None), ("m+", "m+", None), ("m-", "m−", None), ("mr", "mr", None)],
    [("2nd", "2ⁿᵈ", None), ("x2", "x²", None), ("x3", "x³", None), ("xy", "xʸ", None), ("ex", "eˣ", "yˣ"), ("10x", "10ˣ", "2ˣ")],
    [("inv", "¹/x", None), ("sqrt", "²√x", None), ("cbrt", "³√x", None), ("yroot", "ʸ√x", None), ("ln", "ln", "logᵧ"), ("log", "log₁₀", "log₂")],
    [("fact", "x!", None), ("sin", "sin", "sin⁻¹"), ("cos", "cos", "cos⁻¹"), ("tan", "tan", "tan⁻¹"), ("e", "e", None), ("EE", "EE", None)],
    [("rad", "Rad", None), ("sinh", "sinh", "sinh⁻¹"), ("cosh", "cosh", "cosh⁻¹"), ("tanh", "tanh", "tanh⁻¹"), ("pi", "π", None), ("rand", "Rand", None)],
]
# (id, label, colour)
BASIC_ROWS = [
    [("ac", "AC", FUNC_BG), ("neg", "+/−", FUNC_BG), ("pct", "%", FUNC_BG), ("÷", "÷", OP_BG)],
    [("7", "7", DIGIT_BG), ("8", "8", DIGIT_BG), ("9", "9", DIGIT_BG), ("×", "×", OP_BG)],
    [("4", "4", DIGIT_BG), ("5", "5", DIGIT_BG), ("6", "6", DIGIT_BG), ("−", "−", OP_BG)],
    [("1", "1", DIGIT_BG), ("2", "2", DIGIT_BG), ("3", "3", DIGIT_BG), ("+", "+", OP_BG)],
    [("mode", "", DIGIT_BG), ("0", "0", DIGIT_BG), (".", ".", DIGIT_BG), ("=", "=", OP_BG)],
]

# What each scientific key types into the display: (normal, with 2nd)
INSERTS = {
    "(": ("(", None), ")": (")", None),
    "x2": ("²", None), "x3": ("³", None), "xy": ("^", None),
    "ex": ("e^(", "^"), "10x": ("10^(", "2^("),
    "inv": ("1/(", None), "sqrt": ("√(", None), "cbrt": ("∛(", None), "yroot": ("^(1/", None),
    "ln": ("ln(", "log_"), "log": ("log₁₀(", "log₂("),
    "fact": ("!", None), "e": ("e", None), "pi": ("π", None), "EE": ("E", None), "pct": ("%", None),
    "sin": ("sin(", "sin⁻¹("), "cos": ("cos(", "cos⁻¹("), "tan": ("tan(", "tan⁻¹("),
    "sinh": ("sinh(", "sinh⁻¹("), "cosh": ("cosh(", "cosh⁻¹("), "tanh": ("tanh(", "tanh⁻¹("),
}
# Keys that keep working on a previous result instead of starting fresh
CONTINUES = set(OPS) | {"²", "³", "^", "!", "%", "E", ")", "^(1/"}


class Keypad(tk.Canvas):
    """Round Mac-style keys drawn on a canvas, scaled to the window."""

    def __init__(self, master, app):
        super().__init__(master, bg=WINDOW_BG, highlightthickness=0, bd=0)
        self.app = app
        self.rows = []
        self.items = {}      # key id -> (circle item, text item, base colour)
        self.bind("<Configure>", lambda e: (self.draw(), self.app.refresh()))

    def set_rows(self, rows):
        self.rows = rows
        self.draw()

    def cell_size(self):
        """(width, height) of one grid cell - keys stretch to fill the window."""
        if not self.rows or self.winfo_width() < 10:
            return 60, 55
        return self.winfo_width() / len(self.rows[0]), self.winfo_height() / len(self.rows)

    def cell(self):
        return min(self.cell_size())

    def _pill(self, x1, y1, x2, y2, color, tag):
        """Smooth pill: two anti-aliased circles joined by a rectangle."""
        common = dict(fill=color, outline="", width=0, tags=(tag,))
        if x2 - x1 >= y2 - y1:      # wider than tall: round ends left/right
            d = y2 - y1
            self.create_oval(x1, y1, x1 + d, y2, **common)
            self.create_oval(x2 - d, y1, x2, y2, **common)
            self.create_rectangle(x1 + d / 2, y1, x2 - d / 2, y2, **common)
        else:                        # taller than wide: round ends top/bottom
            d = x2 - x1
            self.create_oval(x1, y1, x2, y1 + d, **common)
            self.create_oval(x1, y2 - d, x2, y2, **common)
            self.create_rectangle(x1, y1 + d / 2, x2, y2 - d / 2, **common)

    def draw(self):
        self.delete("all")
        self.items = {}
        if not self.rows or self.winfo_width() < 10:
            return
        cw, ch = self.cell_size()
        gap = max(4, min(cw, ch) * 0.13)
        kw, kh = cw - gap, ch - gap
        base = min(kw * 0.8, kh)
        family = self.app.ui_font
        for r, row in enumerate(self.rows):
            for c, (key_id, label, color) in enumerate(row):
                cx, cy = (c + 0.5) * cw, (r + 0.5) * ch
                tag = f"key-{key_id}"
                circle = f"bg-{key_id}"   # canvas tag shared by the pill's pieces
                self._pill(cx - kw / 2, cy - kh / 2, cx + kw / 2, cy + kh / 2, color, circle)
                self.addtag_withtag(tag, circle)
                size = int(base * (0.3 if color == SCI_BG else 0.44))
                if len(label) > 3:
                    size = int(size * 0.8)
                text = self.create_text(cx, cy, text=label, fill=TEXT, font=(family, max(size, 8)),
                                        tags=(tag,))
                if key_id == "mode":
                    self._draw_calc_icon(cx, cy, base * 0.4, tag)
                self.items[key_id] = (circle, text, color)
                self.tag_bind(tag, "<ButtonPress-1>", lambda e, k=key_id: self._press(k))
                self.tag_bind(tag, "<ButtonRelease-1>", lambda e, k=key_id: self._release(k, e))
        self.app.update_keys()

    def _draw_calc_icon(self, cx, cy, s, tag):
        # Little calculator glyph, like the Sequoia mode button
        w, h = s * 0.8, s
        lw = max(1, s / 12)
        self.create_rectangle(cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2,
                              outline=TEXT, width=lw, tags=(tag,))
        self.create_line(cx - w / 2, cy - h / 6, cx + w / 2, cy - h / 6, fill=TEXT, width=lw, tags=(tag,))
        d = s / 16
        for i in (-1, 0, 1):
            for j in (0, 1):
                x, y = cx + i * w / 3.4, cy + h / 10 + j * h / 4.2
                self.create_oval(x - d, y - d, x + d, y + d, fill=TEXT, outline="", tags=(tag,))

    def _press(self, key_id):
        circle = self.items[key_id][0]
        self.itemconfigure(circle, fill=lighten(self.itemcget(circle, "fill")))

    def _release(self, key_id, event):
        self.app.update_keys()
        self.app.press(key_id, event)

    def style(self, key_id, label=None, bg=None, fg=TEXT):
        if key_id not in self.items:
            return
        circle, text, color = self.items[key_id]
        self.itemconfigure(circle, fill=bg or color)
        self.itemconfigure(text, fill=fg)
        if label is not None:
            self.itemconfigure(text, text=label)


class Calculator:
    def __init__(self, root):
        self.root = root
        root.title("Calculator")
        root.configure(bg=WINDOW_BG)

        self.ui_font = pick_font("SF Pro Display", "SF Pro", "Helvetica Neue", "Helvetica")
        self.mode = tk.StringVar(value="basic")
        self.current_mode = "basic"
        self.degrees = True
        self.second = False
        self.memory = None
        self.text = ""           # what's being typed (any text)
        self.result = ""         # last result (any text)
        self.top = ""            # small line above the result
        self.just_evaluated = False
        self.busy = False
        self.request_id = 0
        self.results = queue.Queue()

        # Display
        self.display = tk.Frame(root, bg=WINDOW_BG, height=120)
        self.display.pack_propagate(False)
        self.display.pack(side="top", fill="x")
        self.flags = tk.Label(self.display, bg=WINDOW_BG, fg=DIM_TEXT, font=(self.ui_font, 11), anchor="w")
        self.flags.place(x=14, y=8)
        self.top_label = tk.Label(self.display, bg=WINDOW_BG, fg=DIM_TEXT, anchor="e", justify="right")
        self.top_label.pack(side="top", fill="x", padx=16, pady=(26, 0))
        self.main_label = tk.Label(self.display, bg=WINDOW_BG, fg=TEXT, anchor="se", justify="right", bd=0, pady=0, highlightthickness=0)
        self.main_label.pack(side="top", fill="both", expand=True, padx=16, pady=(0, 2))
        # Re-fit the big text whenever the display area itself changes size.
        self.main_label.bind("<Configure>", lambda e: None if self.busy else self.refresh())

        # Keypad: 5 rows of round keys under the display
        self.keypad = Keypad(root, self)
        self.keypad.pack(side="top", fill="both", expand=True, padx=8, pady=(0, 8))

        # Mode menu (opened by the calculator-icon key, like on the Mac)
        self.mode_menu = tk.Menu(root, tearoff=0)
        menubar = tk.Menu(root)
        view = tk.Menu(menubar, tearoff=0)
        for menu in (self.mode_menu, view):
            for label, value, accel in (("Basic", "basic", "⌘1"), ("Scientific", "scientific", "⌘2")):
                menu.add_radiobutton(label=label, variable=self.mode, value=value, accelerator=accel,
                                     command=lambda v=value: self.set_mode(v))
        menubar.add_cascade(label="View", menu=view)
        root.config(menu=menubar)

        root.bind_all("<Command-Key-1>", lambda e: self.set_mode("basic"))
        root.bind_all("<Command-Key-2>", lambda e: self.set_mode("scientific"))
        root.bind_all("<Command-v>", lambda e: self.paste())
        root.bind_all("<Command-c>", lambda e: self.copy())
        root.bind("<Key>", self.on_key)
        root.bind("<Configure>", self.on_resize)

        self.keypad.set_rows(BASIC_ROWS)
        root.geometry("300x400")
        root.minsize(200, 320)
        self.refresh()
        self.poll_results()

    # ------------------------------------------------------------ layout
    def on_resize(self, event):
        if event.widget is not self.root:
            return
        # Display takes a fixed share of the height; the keys fill the rest and
        # grow/shrink with the window in both directions.
        self.display.configure(height=max(90, int(event.height * 0.27)))
        self.refresh()

    def set_mode(self, mode):
        self.mode.set(mode)
        if mode == self.current_mode:
            return
        self.current_mode = mode
        if mode == "scientific":
            rows = [[(k, l, SCI_BG) for k, l, _ in SCI_ROWS[i]] + BASIC_ROWS[i] for i in range(5)]
        else:
            rows = BASIC_ROWS
        # Keys keep their size: only the window gets wider / narrower.
        self.root.update_idletasks()
        cell_w = self.keypad.cell_size()[0]
        height = self.root.winfo_height()
        self.keypad.rows = rows
        self.root.minsize(520 if mode == "scientific" else 200, 340)
        self.root.geometry(f"{int(cell_w * len(rows[0]) + 16)}x{height}")
        self.keypad.set_rows(rows)
        self.refresh()

    # ------------------------------------------------------------ input
    def on_key(self, event):
        if event.state & 0x8:            # Command held: leave it to the shortcuts
            return
        if event.keysym in ("Return", "KP_Enter") or event.char == "=":
            self.press("=")
        elif event.keysym == "Escape":
            self.clear_all()
        elif event.keysym == "BackSpace":
            self.backspace()
        elif event.char and event.char.isprintable():
            self.insert(event.char, continues=event.char in "+-*/^%!²³)")

    def paste(self):
        try:
            self.insert(self.root.clipboard_get())
        except tk.TclError:
            pass

    def copy(self):
        self.root.clipboard_clear()
        self.root.clipboard_append(self.result if self.just_evaluated else self.text)

    def press(self, key, event=None):
        if key == "ac":
            return self.backspace() if self.text and not self.just_evaluated else self.clear_all()
        if key == "mode":
            x, y = (event.x_root, event.y_root) if event else (self.root.winfo_pointerx(), self.root.winfo_pointery())
            return self.mode_menu.tk_popup(x, y)
        if self.busy:
            return
        if key == "=":
            return self.evaluate()
        if key in OPS:
            if not self.just_evaluated and self.text and self.text[-1] in OPS:
                self.text = self.text[:-1]           # change operator, like the Mac
            elif not self.text and not self.just_evaluated:
                self.text = "0"
            return self.insert(key, continues=True)
        if key == "neg":
            return self.negate()
        if key == "2nd":
            self.second = not self.second
            return self.update_keys()
        if key == "rad":
            self.degrees = not self.degrees
            return self.refresh()
        if key == "mc":
            self.memory = None
            return self.refresh()
        if key == "mr":
            return self.memory is not None and self.insert(self.memory)
        if key in ("m+", "m-"):
            return self.memory_add(key == "m+")
        if key == "rand":
            return self.insert(f"{random.random():.10g}")
        if key in INSERTS:
            normal, second = INSERTS[key]
            s = second if self.second and second else normal
            return self.insert(s, continues=s in CONTINUES)
        self.insert(key)  # digits and "."

    def insert(self, s, continues=False):
        if self.busy:
            return
        if self.just_evaluated:
            self.text = self.result if continues else ""
            self.just_evaluated = False
            self.top = ""
        self.text += s
        self.refresh()

    def backspace(self):
        if self.busy:
            return
        if self.just_evaluated:
            self.text, self.just_evaluated, self.top = self.result, False, ""
        self.text = self.text[:-1]
        self.refresh()

    def clear_all(self):
        self.request_id += 1      # drop any answer still on its way
        self.busy = False
        self.text = self.result = self.top = ""
        self.just_evaluated = False
        self.refresh()

    def negate(self):
        if self.just_evaluated:
            self.text, self.just_evaluated, self.top = self.result, False, ""
        m = re.search(r"(\d+\.?\d*|\.\d+)$", self.text)
        if not m:
            if not self.text:
                self.text = "−"
            return self.refresh()
        i = m.start()
        if i > 0 and self.text[i - 1] in "−-" and (i == 1 or self.text[i - 2] in "(+−-×÷^ E"):
            self.text = self.text[:i - 1] + self.text[i:]
        else:
            self.text = self.text[:i] + "−" + self.text[i:]
        self.refresh()

    # ----------------------------------------------------------- compute
    def evaluate(self):
        expression = self.result if self.just_evaluated else self.text
        if not expression.strip():
            return
        self.top = expression
        self.run(expression, self.on_result)

    def memory_add(self, plus):
        value = (self.result if self.just_evaluated else self.text) or "0"
        if self.memory is None:
            expression = value if plus else f"0 − ({value})"
        else:
            expression = f"({self.memory}) {'+' if plus else '−'} ({value})"
        self.run(expression, self.on_memory, keep_display=True)

    def run(self, expression, callback, keep_display=False):
        self.busy = True
        self.request_id += 1
        rid, degrees = self.request_id, self.degrees

        def worker():
            try:
                out = str(compute(expression, degrees))
            except Exception:
                out = "Error"
            self.results.put((rid, out, callback))

        threading.Thread(target=worker, daemon=True).start()
        if not keep_display:
            self.top_label.configure(text=self._elide(self.top, self.top_label.cget("font")))
            self.animate(rid, 0)

    def animate(self, rid, step):
        if self.busy and rid == self.request_id:
            self.show_main("·" * (step % 3 + 1))
            self.root.after(300, self.animate, rid, step + 1)

    def poll_results(self):
        try:
            while True:
                rid, out, callback = self.results.get_nowait()
                if rid == self.request_id:
                    self.busy = False
                    callback(out)
                    self.refresh()
        except queue.Empty:
            pass
        self.root.after(50, self.poll_results)

    def on_result(self, out):
        self.result = out.strip()
        self.just_evaluated = True

    def on_memory(self, out):
        if out.strip() and out != "Error":
            self.memory = out.strip()

    # ----------------------------------------------------------- display
    def update_keys(self):
        kp = self.keypad
        for row in SCI_ROWS:
            for key_id, label, second in row:
                kp.style(key_id, second if self.second and second else label)
        kp.style("2nd", bg=lighten(SCI_BG, 0.35) if self.second else None)
        kp.style("rad", "Rad" if self.degrees else "Deg")
        kp.style("ac", "⌫" if self.text and not self.just_evaluated else "AC")
        pending = self.text[-1] if self.text and not self.just_evaluated else None
        for op in OPS:
            if op == pending:
                kp.style(op, bg=TEXT, fg=OP_BG)
            else:
                kp.style(op)

    def _elide(self, text, font):
        f = tkfont.Font(font=font)
        width = max(self.display.winfo_width() - 32, 50)
        if f.measure(text) <= width:
            return text
        while text and f.measure("…" + text) > width:
            text = text[1:]
        return "…" + text

    def show_main(self, text):
        """Big text that shrinks to fit, then wraps onto more lines (any string fits)."""
        width = max(self.display.winfo_width() - 32, 50)
        # Space the big text really has (the label fills what the top line leaves).
        height = self.main_label.winfo_height() if self.main_label.winfo_height() > 1 else 70
        size = max(int(self.keypad.cell() * 0.8), 24)
        f = tkfont.Font(family=self.ui_font, size=size)
        while size > 9:
            f.configure(size=size)
            self.main_label.configure(text=text, font=(self.ui_font, size), wraplength=width)
            one_line = f.measure(text) <= width
            # Big sizes must fit on one line; small sizes may wrap onto more lines.
            if self.main_label.winfo_reqheight() <= height and (one_line or size <= 22):
                break
            size -= 1

    def refresh(self):
        if not self.busy:
            self.show_main(self.result if self.just_evaluated else (self.text or "0"))
            self.top_label.configure(font=(self.ui_font, max(int(self.keypad.cell() * 0.26), 11)))
            top = self.top if self.just_evaluated else ""
            self.top_label.configure(text=self._elide(top, self.top_label.cget("font")))
        flags = []
        if self.current_mode == "scientific" and not self.degrees:
            flags.append("Rad")
        if self.memory is not None:
            flags.append("M")
        self.flags.configure(text="  ".join(flags))
        self.update_keys()


if __name__ == "__main__":
    root = tk.Tk()
    Calculator(root)
    root.mainloop()
