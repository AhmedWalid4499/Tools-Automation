"""GOLD Express look: side menu, rounded panels, gradient stat cards and rounded buttons / fields.

Tkinter draws only square shapes, so rounded and gradient surfaces are drawn as images (Pillow) and
redrawn when their size changes.
"""
import tkinter as tk
from pathlib import Path
from tkinter import ttk

from PIL import Image, ImageDraw, ImageFilter, ImageTk

FONT = "Segoe UI"
ICONS = "Segoe Fluent Icons" if Path(r"C:\Windows\Fonts\SegoeIcons.ttf").exists() else "Segoe MDL2 Assets"

# Warm, light palette
BG = "#F4F2EE"        # window background (warm off-white)
CARD = "#FFFFFF"
INK = "#1F2328"
MUTED = "#80868F"
FAINT = "#A7ACB3"
LINE = "#ECE9E4"
ORANGE = "#FF7900"
ORANGE_DARK = "#E06A00"
ORANGE_SOFT = "#FFF1E3"

# Gradient card palettes: (top-left colour, bottom-right colour, glow colour, accent / text colour)
PALETTES = {
    "sun":      ("#FFF8E6", "#FFE6BF", "#FFD27A", "#B86B00"),
    "peach":    ("#FFF1E6", "#FFD9BF", "#FFB27A", "#D35F00"),
    "mint":     ("#EFFAF3", "#D3F1DE", "#9FE0B5", "#1E7B34"),
    "amber":    ("#FFF8E1", "#FFE7A8", "#FFD15C", "#9A5B00"),
    "rose":     ("#FFF0F0", "#FBD6D6", "#F5A3A3", "#C62828"),
    "lavender": ("#F1F0FF", "#FDEBCD", "#D9D4FF", "#4F46C8"),
    "sky":      ("#EEF6FF", "#D7E8FF", "#A9CBFF", "#1F5FBF"),
    "grey":     ("#F7F6F4", "#ECEBE8", "#DDDBD6", "#5F6670"),
}
RAG_PALETTE = {"Green": "mint", "Amber": "amber", "Red": "rose", "No date": "grey", None: "grey"}


def _hex(c):
    c = c.lstrip("#")
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))


def rounded_image(w, h, r, fill, outline=None, scale=3):
    """A rounded rectangle (anti-aliased) as a PIL image with a transparent outside."""
    W, H = max(w, 2) * scale, max(h, 2) * scale
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((0, 0, W - 1, H - 1), radius=r * scale, fill=fill,
                        outline=outline, width=scale if outline else 0)
    return img.resize((max(w, 2), max(h, 2)), Image.LANCZOS)


def gradient_card_image(w, h, r, palette):
    """Rounded card with a soft diagonal gradient and a warm glow in the lower right, like a light
    shining through frosted glass."""
    c0, c1, glow, _ = (_hex(x) for x in PALETTES[palette])
    sw, sh = max(w // 2, 2), max(h // 2, 2)          # draw at half size, then scale (smooth anyway)
    base = Image.new("RGB", (sw, sh))
    px = base.load()
    for y in range(sh):
        for x in range(sw):
            t = (x / sw * 0.65 + y / sh * 0.35)
            px[x, y] = tuple(round(a + (b - a) * t) for a, b in zip(c0, c1))
    blob = Image.new("L", (sw, sh), 0)
    ImageDraw.Draw(blob).ellipse((sw * 0.55, sh * 0.35, sw * 1.25, sh * 1.45), fill=170)
    blob = blob.filter(ImageFilter.GaussianBlur(max(sw, sh) * 0.12))
    base = Image.composite(Image.new("RGB", (sw, sh), glow), base, blob)
    base = base.resize((w, h), Image.BICUBIC)
    mask = rounded_image(w, h, r, (255, 255, 255, 255)).split()[-1]
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    out.paste(base, (0, 0), mask)
    return out


def fit_text(text, font, width, lines):
    """Word-wrap text to width (pixels) in at most `lines` lines; the last one ends with … if cut."""
    out, words = [], (text or "").replace("\n", " \n ").split(" ")
    cur = ""
    for word in words:
        if word == "\n":
            out.append(cur)
            cur = ""
            continue
        test = (cur + " " + word).strip()
        if font.measure(test) <= width or not cur:
            cur = test
        else:
            out.append(cur)
            cur = word
    out.append(cur)
    out = [l for l in out if l.strip()] or [""]
    if len(out) > lines:
        last = out[lines - 1]
        while last and font.measure(last + "…") > width:
            last = last[:-1]
        out = out[:lines - 1] + [last.rstrip() + "…"]
    return "\n".join(out)


class Panel(tk.Canvas):
    """A white rounded panel on the window background. Put widgets in .body."""

    def __init__(self, parent, radius=18, pad=0, bg=BG, fill=CARD, outline=LINE, **kw):
        super().__init__(parent, background=bg, highlightthickness=0, borderwidth=0, **kw)
        self.radius, self.pad, self.fill, self.outline = radius, pad, fill, outline
        self.body = tk.Frame(self, background=fill)
        self._win = self.create_window(0, 0, window=self.body, anchor="nw")
        self._img = None
        self._size = None
        self.bind("<Configure>", self._redraw)

    def _redraw(self, e=None):
        w, h = self.winfo_width(), self.winfo_height()
        if w < 10 or h < 10 or (w, h) == self._size:
            return
        self._size = (w, h)
        self._img = ImageTk.PhotoImage(rounded_image(w, h, self.radius, self.fill, self.outline))
        self.delete("bgimg")
        self.create_image(0, 0, image=self._img, anchor="nw", tags="bgimg")
        self.tag_lower("bgimg")
        inset = self.radius // 2 + self.pad
        self.coords(self._win, inset, inset)
        self.itemconfigure(self._win, width=w - 2 * inset, height=h - 2 * inset)


class StatCard(tk.Canvas):
    """A colourful gradient card: caption, big value, small text and an optional icon bubble."""

    PAD = 16

    def __init__(self, parent, caption="", icon="", palette="sun", sub_lines=2, big_size=24, bg=CARD,
                 command=None, **kw):
        from tkinter import font as tkfont
        self.f_cap = tkfont.Font(family=FONT, size=8, weight="bold")
        self.f_sub = tkfont.Font(family=FONT, size=9)
        self.big_size = big_size
        ls = lambda f: f.metrics("linespace")
        big_ls = ls(tkfont.Font(family="Segoe UI Light", size=big_size))
        height = self.PAD + ls(self.f_cap) + 4 + big_ls + 4 + sub_lines * ls(self.f_sub) + self.PAD - 4
        super().__init__(parent, height=height, background=bg, highlightthickness=0, borderwidth=0, **kw)
        self.caption, self.icon, self.palette, self.sub_lines = caption, icon, palette, sub_lines
        self.big, self.sub = "-", ""
        self._img = self._bubble = None
        self._key = None
        self.bind("<Configure>", lambda e: self._draw())
        if command:
            self.configure(cursor="hand2")
            self.bind("<Button-1>", lambda e: command())

    def set(self, big=None, sub=None, palette=None, caption=None):
        if big is not None:
            self.big = big
        if sub is not None:
            self.sub = sub
        if palette:
            self.palette = palette
        if caption is not None:
            self.caption = caption
        self._key = None
        self._draw()

    def _draw(self):
        w, h = self.winfo_width(), self.winfo_height()
        if w < 20 or h < 20:
            return
        key = (w, h, self.palette)
        if key != self._key:
            self._img = ImageTk.PhotoImage(gradient_card_image(w, h, 16, self.palette))
            self._key = key
        from tkinter import font as tkfont
        accent = PALETTES[self.palette][3]
        p = self.PAD
        self.delete("all")
        self.create_image(0, 0, image=self._img, anchor="nw")
        y = p
        bubble = (self.f_cap.metrics("linespace") + 20) if self.icon else 0
        cap = fit_text(self.caption.upper(), self.f_cap, w - 2 * p - bubble, 1)
        self.create_text(p + 2, y, text=cap, anchor="nw", fill=accent, font=self.f_cap)
        y += self.f_cap.metrics("linespace") + 4
        # the big value on one line: a smaller font when it is long
        size = self.big_size
        big = tkfont.Font(family="Segoe UI Light", size=size)
        while size > 11 and big.measure(self.big) > w - 2 * p - 4:
            size -= 1
            big = tkfont.Font(family="Segoe UI Light", size=size)
        self._big_font = big
        self.create_text(p, y, text=self.big, anchor="nw", fill=INK, font=big)
        y += tkfont.Font(family="Segoe UI Light", size=self.big_size).metrics("linespace") + 4
        self.create_text(p + 2, y, text=fit_text(self.sub, self.f_sub, w - 2 * p - 4, self.sub_lines),
                         anchor="nw", fill="#4B5159", font=self.f_sub)
        if self.icon:
            d = self.f_cap.metrics("linespace") + 14
            if self._bubble is None or self._bubble.width() != d:
                self._bubble = ImageTk.PhotoImage(rounded_image(d, d, d // 2, (255, 255, 255, 200)))
            self.create_image(w - p + 6, p - 6, image=self._bubble, anchor="ne")
            self.create_text(w - p + 6 - d // 2, p - 6 + d // 2, text=self.icon, fill=accent, font=(ICONS, 10))


class SideNav(tk.Frame):
    """Left side menu with sections, icons and a highlighted current page. Works like the parts of
    ttk.Notebook the app uses: add(), select(), index("current" / "end"), current(), and it sends
    <<NotebookTabChanged>> when the page changes."""

    def __init__(self, parent, host, on_change=None):
        super().__init__(parent, background=CARD)
        self.host = host            # frame the pages are shown in
        self.pages = []             # (frame, title, subtitle, item widgets)
        self.cur = None
        self.on_change = on_change
        self.top = tk.Frame(self, background=CARD)
        self.top.pack(fill="x")
        self.items = tk.Frame(self, background=CARD)
        self.items.pack(fill="both", expand=True, padx=12)
        self.bottom = tk.Frame(self, background=CARD)
        self.bottom.pack(side="bottom", fill="x", padx=12, pady=(0, 12))
        tk.Frame(self, background=LINE, width=1).place(relx=1, x=-1, y=0, relheight=1)

    def section(self, title):
        tk.Label(self.items, text=title.upper(), bg=CARD, fg=FAINT, font=(FONT, 8, "bold"),
                 anchor="w").pack(fill="x", padx=12, pady=(14, 4))

    def add(self, frame, text, icon="", subtitle=""):
        row = tk.Frame(self.items, background=CARD, cursor="hand2")
        row.pack(fill="x", pady=1)
        bar = tk.Frame(row, background=CARD, width=3)
        bar.pack(side="left", fill="y")
        ic = tk.Label(row, text=icon, bg=CARD, fg=MUTED, font=(ICONS, 12), width=3, cursor="hand2")
        ic.pack(side="left", padx=(6, 2), pady=8)
        lab = tk.Label(row, text=text, bg=CARD, fg=INK, font=(FONT, 10), anchor="w", cursor="hand2")
        lab.pack(side="left", fill="x", expand=True, padx=(0, 18))
        index = len(self.pages)
        widgets = (row, bar, ic, lab)
        for w in (row, ic, lab):
            w.bind("<Button-1>", lambda e, i=index: self.select(i))
            w.bind("<Enter>", lambda e, i=index: self._hover(i, True))
            w.bind("<Leave>", lambda e, i=index: self._hover(i, False))
        self.pages.append((frame, text, subtitle, widgets))
        if self.cur is None:
            self.select(0)

    def _paint(self, i, active, hover=False):
        row, bar, ic, lab = self.pages[i][3]
        bg = ORANGE_SOFT if active else ("#F7F5F2" if hover else CARD)
        for w in (row, ic, lab):
            w.configure(background=bg)
        bar.configure(background=ORANGE if active else bg)
        ic.configure(fg=ORANGE if active else MUTED)
        lab.configure(fg=ORANGE_DARK if active else INK, font=(FONT, 10, "bold" if active else "normal"))

    def _hover(self, i, on):
        if i != self.cur:
            self._paint(i, False, on)

    def _resolve(self, page):
        if isinstance(page, int):
            return page
        return next(i for i, p in enumerate(self.pages) if p[0] is page or str(p[0]) == str(page))

    def select(self, page=None):
        if page is None:
            return str(self.pages[self.cur][0]) if self.cur is not None else ""
        i = self._resolve(page)
        if i == self.cur:
            return
        if self.cur is not None:
            self.pages[self.cur][0].pack_forget()
            self._paint(self.cur, False)
        self.cur = i
        self._paint(i, True)
        self.pages[i][0].pack(in_=self.host, fill="both", expand=True)
        if self.on_change:
            self.on_change(self.pages[i][1], self.pages[i][2])
        self.event_generate("<<NotebookTabChanged>>")

    def index(self, what):
        if what == "current":
            return self.cur
        if what == "end":
            return len(self.pages)
        return self._resolve(what)

    def current(self):
        return self.pages[self.cur][0] if self.cur is not None else None


def style_rounded(style, root):
    """Rounded buttons (normal + accent) and entry fields, drawn from images."""
    keep = root._rounded_imgs = []

    def img(w, h, r, fill, outline=None):
        p = ImageTk.PhotoImage(rounded_image(w, h, r, fill, outline), master=root)
        keep.append(p)
        return p

    W, H, R = 44, 36, 10
    n = img(W, H, R, "#FFFFFF", "#E1DDD6")
    hv = img(W, H, R, "#FFF7EF", "#FFB27A")
    pr = img(W, H, R, "#FFEBD8", ORANGE)
    ds = img(W, H, R, "#F7F6F4", "#ECE9E4")
    style.element_create("RButton.border", "image", n, ("disabled", ds), ("pressed", pr), ("active", hv),
                         border=(R, R), sticky="nsew")
    an = img(W, H, R, ORANGE)
    ah = img(W, H, R, ORANGE_DARK)
    ad = img(W, H, R, "#F9CBA0")
    style.element_create("AButton.border", "image", an, ("disabled", ad), ("pressed", ah), ("active", ah),
                         border=(R, R), sticky="nsew")
    sn = img(W, H, R, CARD)
    sh = img(W, H, R, "#F7F5F2")
    style.element_create("SButton.border", "image", sn, ("pressed", sh), ("active", sh),
                         border=(R, R), sticky="nsew")
    for name, element in (("TButton", "RButton.border"), ("Accent.TButton", "AButton.border"),
                          ("Side.TButton", "SButton.border")):
        style.layout(name, [(element, {"sticky": "nsew", "children": [
            ("Button.padding", {"sticky": "nsew", "children": [("Button.label", {"sticky": "nsew"})]})]})])
    style.configure("TButton", padding=(14, 7), background=CARD, foreground=INK, width=-4)  # sized to text
    style.configure("Accent.TButton", padding=(18, 7), foreground="white", font=(FONT, 10, "bold"))
    style.map("Accent.TButton", foreground=[("disabled", "white")])
    style.configure("Side.TButton", padding=(12, 7), foreground=INK, anchor="w", font=(FONT, 10))
    style.map("Side.TButton", foreground=[("active", ORANGE_DARK)])

    fn = img(W, H, R, "#FFFFFF", "#DEDAD3")
    ff = img(W, H, R, "#FFFFFF", ORANGE)
    fd = img(W, H, R, "#F7F6F4", "#ECE9E4")
    style.element_create("REntry.field", "image", fn, ("disabled", fd), ("focus", ff), border=(R, R),
                         sticky="nsew")
    style.layout("TEntry", [("REntry.field", {"sticky": "nsew", "children": [
        ("Entry.padding", {"sticky": "nsew", "children": [("Entry.textarea", {"sticky": "nsew"})]})]})])
    style.configure("TEntry", padding=(10, 6), fieldbackground=CARD)
