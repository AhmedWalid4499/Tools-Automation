"""GOLD Express look: rounded tiles with soft shadows, a side menu with pill highlights, gradient
stat cards, chat bubbles, and rounded buttons / fields / selectors / checkboxes / scrollbars.

Tkinter draws only square shapes, so every rounded or gradient surface is an image (Pillow), redrawn
when its size changes.
"""
import tkinter as tk
from pathlib import Path
from tkinter import font as tkfont

from PIL import Image, ImageDraw, ImageFilter, ImageTk

FONT = "Segoe UI"
ICONS = "Segoe Fluent Icons" if Path(r"C:\Windows\Fonts\SegoeIcons.ttf").exists() else "Segoe MDL2 Assets"

# Warm, light palette
BG = "#F3F1EC"        # window background (warm off-white)
CARD = "#FFFFFF"
INK = "#1F2328"
MUTED = "#7D838C"
FAINT = "#A7ACB3"
LINE = "#EBE7E1"
ORANGE = "#FF7900"
ORANGE_DARK = "#E06A00"
ORANGE_SOFT = "#FFF0E1"
HOVER = "#F6F3EF"

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
    # vivid cards (white text, wave lines), for dashboards
    "v_blue":   ("#55BDF7", "#1F86E0", "#8FD6FF", "#FFFFFF"),
    "v_green":  ("#A3D550", "#56A72C", "#C8EC8E", "#FFFFFF"),
    "v_orange": ("#FFB552", "#FF7A00", "#FFD594", "#FFFFFF"),
    "v_purple": ("#BE6EDC", "#8A3FB8", "#DDA8F2", "#FFFFFF"),
    "v_teal":   ("#33C7B3", "#128577", "#86E6D8", "#FFFFFF"),
    "v_rose":   ("#FF7E8A", "#DD3F58", "#FFB8BF", "#FFFFFF"),
}
VIVID = {k for k in PALETTES if k.startswith("v_")}
RAG_PALETTE = {"Green": "mint", "Amber": "amber", "Red": "rose", "No date": "grey", None: "grey"}


def _hex(c):
    c = c.lstrip("#")
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))


def rounded_image(w, h, r, fill, outline=None, scale=3, width=1):
    """A rounded rectangle (anti-aliased) as a PIL image with a transparent outside."""
    W, H = max(w, 2) * scale, max(h, 2) * scale
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(img).rounded_rectangle((0, 0, W - 1, H - 1), radius=r * scale, fill=fill, outline=outline,
                                          width=scale * width if outline else 0)
    return img.resize((max(w, 2), max(h, 2)), Image.LANCZOS)


def tile_image(w, h, r, fill=CARD, shadow=True, outline=None, m=6):
    """A rounded tile with a soft shadow underneath, inset by m pixels so the shadow fits."""
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    if shadow:
        sh = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        ImageDraw.Draw(sh).rounded_rectangle((m, m + 3, w - m, h - m + 2), radius=r, fill=(70, 50, 20, 26))
        img = Image.alpha_composite(img, sh.filter(ImageFilter.GaussianBlur(5)))
    card = rounded_image(w - 2 * m, h - 2 * m, r, fill, outline)
    img.alpha_composite(card, (m, m))
    return img


def gradient_card_image(w, h, r, palette):
    """Rounded card with a soft diagonal gradient and a warm glow in the lower right."""
    c0, c1, glow, _ = (_hex(x) for x in PALETTES[palette])
    sw, sh = max(w // 3, 2), max(h // 3, 2)
    base = Image.new("RGB", (sw, sh))
    px = base.load()
    for y in range(sh):
        for x in range(sw):
            t = (x / sw * 0.65 + y / sh * 0.35)
            px[x, y] = tuple(round(a + (b - a) * t) for a, b in zip(c0, c1))
    blob = Image.new("L", (sw, sh), 0)
    ImageDraw.Draw(blob).ellipse((sw * 0.55, sh * 0.35, sw * 1.25, sh * 1.45), fill=170)
    blob = blob.filter(ImageFilter.GaussianBlur(max(sw, sh) * 0.12))
    base = Image.composite(Image.new("RGB", (sw, sh), glow), base, blob).resize((w, h), Image.BICUBIC)
    if palette in VIVID:  # two soft wave lines across the lower half, like a sparkline
        import math
        s = 3
        waves = Image.new("RGBA", (w * s, h * s), (0, 0, 0, 0))
        d = ImageDraw.Draw(waves)
        for k, (amp, phase, alpha) in enumerate(((0.10, 0.0, 90), (0.07, 1.9, 60))):
            pts = [(x * s, (h * (0.72 + 0.06 * k) + h * amp * math.sin(x / w * 2 * math.pi * 1.15 + phase)) * s)
                   for x in range(0, w + 4, 4)]
            d.line(pts, fill=(255, 255, 255, alpha), width=2 * s, joint="curve")
        base = Image.alpha_composite(base.convert("RGBA"), waves.resize((w, h), Image.LANCZOS))
    mask = rounded_image(w, h, r, (255, 255, 255, 255)).split()[-1]
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    out.paste(base, (0, 0), mask)
    return out


def fit_text(text, font, width, lines=999):
    """Word-wrap text to width (pixels) in at most `lines` lines; the last one ends with … if cut."""
    out, cur = [], ""
    for word in (text or "").replace("\n", " \n ").split(" "):
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


class _Redraw:
    """Redraw a canvas a moment after its size changes (resizing the window stays smooth)."""

    def _watch(self):
        self._size = None
        self._pending = None
        self.bind("<Configure>", self._soon, add="+")

    def _soon(self, e=None):
        if self._pending:
            self.after_cancel(self._pending)
        self._pending = self.after(40, self._check)

    def _check(self):
        self._pending = None
        size = (self.winfo_width(), self.winfo_height())
        if size[0] > 10 and size[1] > 10 and size != self._size:
            self._size = size
            self.redraw(*size)


class Tile(tk.Canvas, _Redraw):
    """A white rounded tile with a soft shadow. Put widgets in .body."""

    M = 6  # room for the shadow around the tile

    def __init__(self, parent, radius=18, pad=10, bg=BG, fill=CARD, shadow=True, outline=None, **kw):
        super().__init__(parent, background=bg, highlightthickness=0, borderwidth=0, **kw)
        self.radius, self.pad, self.fill, self.shadow, self.outline = radius, pad, fill, shadow, outline
        self.body = tk.Frame(self, background=fill)
        self._win = self.create_window(0, 0, window=self.body, anchor="nw")
        self._img = None
        self._watch()
        # the tile takes the size its content asks for (so tiles can sit in a row or column)
        self.body.bind("<Configure>", self._fit, add="+")

    def _fit(self, e=None):
        inset = self.M + self.radius // 2 + self.pad
        rw, rh = self.body.winfo_reqwidth() + 2 * inset, self.body.winfo_reqheight() + 2 * inset
        if int(self.cget("width")) != rw or int(self.cget("height")) != rh:
            self.configure(width=rw, height=rh)

    def redraw(self, w, h):
        self._img = ImageTk.PhotoImage(tile_image(w, h, self.radius, self.fill, self.shadow, self.outline, self.M))
        self.delete("bgimg")
        self.create_image(0, 0, image=self._img, anchor="nw", tags="bgimg")
        self.tag_lower("bgimg")
        inset = self.M + self.radius // 2 + self.pad
        self.coords(self._win, inset, inset)
        self.itemconfigure(self._win, width=max(w - 2 * inset, 1), height=max(h - 2 * inset, 1))


class StatCard(tk.Canvas, _Redraw):
    """A colourful gradient card: caption, big value, small text and an optional icon bubble."""

    PAD = 16

    def __init__(self, parent, caption="", icon="", palette="sun", sub_lines=2, big_size=24, bg=BG,
                 command=None, **kw):
        self.f_cap = tkfont.Font(family=FONT, size=8, weight="bold")
        self.f_sub = tkfont.Font(family=FONT, size=9)
        self.big_size = big_size
        big_ls = tkfont.Font(family="Segoe UI Light", size=big_size).metrics("linespace")
        height = (self.PAD + self.f_cap.metrics("linespace") + 4 + big_ls + 4
                  + sub_lines * self.f_sub.metrics("linespace") + self.PAD - 4)
        super().__init__(parent, height=height, background=bg, highlightthickness=0, borderwidth=0, **kw)
        self.caption, self.icon, self.palette, self.sub_lines = caption, icon, palette, sub_lines
        self.big, self.sub = "-", ""
        self._img = self._bubble = None
        self._key = None
        self._watch()
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
        if self._size:
            self.redraw(*self._size)

    def redraw(self, w, h):
        key = (w, h, self.palette)
        if key != self._key:
            self._img = ImageTk.PhotoImage(gradient_card_image(w, h, 18, self.palette))
            self._key = key
        accent = PALETTES[self.palette][3]
        vivid = self.palette in VIVID
        ink, sub_ink = ("#FFFFFF", "#FFFFFF") if vivid else (INK, "#4B5159")
        p = self.PAD
        self.delete("all")
        self.create_image(0, 0, image=self._img, anchor="nw")
        bubble = (self.f_cap.metrics("linespace") + 20) if self.icon else 0
        cap = fit_text(self.caption.upper(), self.f_cap, w - 2 * p - bubble, 1)
        self.create_text(p + 2, p, text=cap, anchor="nw", fill=accent, font=self.f_cap)
        y = p + self.f_cap.metrics("linespace") + 4
        size = self.big_size  # the big value on one line: a smaller font when it is long
        big = tkfont.Font(family="Segoe UI Light", size=size)
        while size > 11 and big.measure(self.big) > w - 2 * p - 4:
            size -= 1
            big = tkfont.Font(family="Segoe UI Light", size=size)
        self.create_text(p, y, text=self.big, anchor="nw", fill=ink,
                         font=tkfont.Font(family="Segoe UI Semibold" if vivid else "Segoe UI Light", size=size))
        y += tkfont.Font(family="Segoe UI Light", size=self.big_size).metrics("linespace") + 4
        self.create_text(p + 2, y, text=fit_text(self.sub, self.f_sub, w - 2 * p - 4, self.sub_lines),
                         anchor="nw", fill=sub_ink, font=self.f_sub)
        if self.icon:
            d = self.f_cap.metrics("linespace") + 14
            if self._bubble is None or self._bubble.width() != d or getattr(self, "_bubble_vivid", None) != vivid:
                self._bubble = ImageTk.PhotoImage(rounded_image(d, d, d // 2, (255, 255, 255, 70 if vivid else 210)))
                self._bubble_vivid = vivid
            self.create_image(w - p + 6, p - 6, image=self._bubble, anchor="ne")
            self.create_text(w - p + 6 - d // 2, p - 6 + d // 2, text=self.icon, fill=accent, font=(ICONS, 10))


class Donut(tk.Canvas, _Redraw):
    """A ring chart: set(items=[(label, value, colour)], centre_big, centre_small)."""

    def __init__(self, parent, size=None, bg=CARD, thickness=0.2, on_click=None):
        self.f_big = tkfont.Font(family="Segoe UI Semibold", size=15)
        self.f_small = tkfont.Font(family=FONT, size=7)
        size = size or int(self.f_big.metrics("linespace") * 3.9)  # room for the centre text at any scaling
        super().__init__(parent, width=size, height=size, background=bg, highlightthickness=0, borderwidth=0)
        self.items, self.big, self.small, self.thickness = [], "", "", thickness
        self._img = None
        self._watch()

    def set(self, items, big="", small=""):
        self.items, self.big, self.small = [i for i in items if i[1] > 0], big, small
        if self._size:
            self.redraw(*self._size)

    def redraw(self, w, h):
        d = min(w, h) - 4
        s = 4
        im = Image.new("RGBA", (d * s, d * s), (0, 0, 0, 0))
        dr = ImageDraw.Draw(im)
        total = sum(v for _, v, _ in self.items)
        if not total:
            dr.ellipse((0, 0, d * s - 1, d * s - 1), fill="#EFECE7")
        else:
            start = -90.0
            gap = 1.2 if len(self.items) > 1 else 0
            for _, v, colour in self.items:
                sweep = 360.0 * v / total
                dr.pieslice((0, 0, d * s - 1, d * s - 1), start + gap / 2, start + sweep - gap / 2, fill=colour)
                start += sweep
        hole = d * s * self.thickness
        dr.ellipse((hole, hole, d * s - hole, d * s - hole), fill=(0, 0, 0, 0))
        # punch the hole (pieslice painted it): rebuild alpha from a mask
        mask = Image.new("L", im.size, 255)
        ImageDraw.Draw(mask).ellipse((hole, hole, d * s - hole, d * s - hole), fill=0)
        im.putalpha(Image.composite(im.split()[-1], Image.new("L", im.size, 0), mask))
        self._img = ImageTk.PhotoImage(im.resize((d, d), Image.LANCZOS))
        self.delete("all")
        self.create_image(w // 2, h // 2, image=self._img)
        hb, hs = self.f_big.metrics("linespace"), self.f_small.metrics("linespace")
        top = h // 2 - (hb + hs) // 2
        self.create_text(w // 2, top, text=self.big, fill=INK, font=self.f_big, anchor="n")
        self.create_text(w // 2, top + hb - 2, text=self.small, fill=MUTED, font=self.f_small, anchor="n")


class Bars(tk.Canvas, _Redraw):
    """Horizontal bars with labels and values: set([(label, value, colour)]). click(label) when clicked."""

    def __init__(self, parent, bg=CARD, on_click=None, rows=6):
        self.f_label = tkfont.Font(family=FONT, size=9)
        self.f_value = tkfont.Font(family=FONT, size=9, weight="bold")
        self.row_h = self.f_label.metrics("linespace") + 16
        super().__init__(parent, height=self.row_h * rows, background=bg, highlightthickness=0, borderwidth=0)
        self.items, self.on_click, self._imgs = [], on_click, []
        self._watch()
        if on_click:
            self.bind("<Button-1>", self._clicked)

    def set(self, items):
        self.items = list(items)
        if self._size:
            self.redraw(*self._size)

    def _clicked(self, e):
        i = e.y // self.row_h
        if 0 <= i < len(self.items) and self.on_click:
            self.on_click(self.items[i][0])

    def redraw(self, w, h):
        self.delete("all")
        self._imgs = []
        if not self.items:
            return
        top = max(v for _, v, _ in self.items) or 1
        label_w = min(int(w * 0.5), max(self.f_label.measure(l) for l, _, _ in self.items) + 12)
        bar_w = w - label_w - 40
        bh = max(8, self.row_h - 18)
        for i, (label, value, colour) in enumerate(self.items):
            y = i * self.row_h + self.row_h // 2
            self.create_text(0, y, text=fit_text(label, self.f_label, label_w - 8, 1), anchor="w", fill=INK,
                             font=self.f_label)
            track = ImageTk.PhotoImage(rounded_image(bar_w, bh, bh // 2, "#F1EEE9"))
            self._imgs.append(track)
            self.create_image(label_w, y, image=track, anchor="w")
            bw = max(bh, int(bar_w * value / top))
            bar = ImageTk.PhotoImage(rounded_image(bw, bh, bh // 2, colour))
            self._imgs.append(bar)
            self.create_image(label_w, y, image=bar, anchor="w")
            self.create_text(label_w + bar_w + 8, y, text=str(value), anchor="w", fill=INK, font=self.f_value)
        if self.on_click:
            self.configure(cursor="hand2")


class Pill(tk.Canvas):
    """A small rounded label (status, tags). set(text, fg, bg)."""

    def __init__(self, parent, text="", fg=INK, fill=ORANGE_SOFT, bg=BG, size=9, bold=True, command=None):
        super().__init__(parent, background=bg, highlightthickness=0, borderwidth=0)
        self.font = tkfont.Font(family=FONT, size=size, weight="bold" if bold else "normal")
        self._img = None
        if command:
            self.configure(cursor="hand2")
            self.bind("<Button-1>", lambda e: command())
        self.set(text, fg, fill)

    def set(self, text, fg=None, fill=None):
        self.text = text
        self.fg = fg or getattr(self, "fg", INK)
        self.fill = fill or getattr(self, "fill", ORANGE_SOFT)
        h = self.font.metrics("linespace") + 10
        w = self.font.measure(text) + 2 * (h // 2 + 4)
        self.configure(width=w, height=h)
        self._img = ImageTk.PhotoImage(rounded_image(w, h, h // 2, self.fill))
        self.delete("all")
        self.create_image(0, 0, image=self._img, anchor="nw")
        self.create_text(w // 2, h // 2, text=text, fill=self.fg, font=self.font)


class ClickCard(tk.Canvas):
    """A rounded white card with a title and a line of text; orange outline on hover; click = command."""

    def __init__(self, parent, title, text, command, bg=BG, width=300):
        self.f1 = tkfont.Font(family=FONT, size=10, weight="bold")
        self.f2 = tkfont.Font(family=FONT, size=9)
        h = 28 + self.f1.metrics("linespace") + self.f2.metrics("linespace") + 4
        super().__init__(parent, width=width, height=h, background=bg, highlightthickness=0, borderwidth=0,
                         cursor="hand2")
        self.title, self.text, self._imgs = title, text, {}
        self.bind("<Configure>", lambda e: self._draw(False))
        self.bind("<Enter>", lambda e: self._draw(True))
        self.bind("<Leave>", lambda e: self._draw(False))
        self.bind("<Button-1>", lambda e: command())

    def _draw(self, hover):
        w, h = self.winfo_width(), self.winfo_height()
        if w < 20:
            return
        key = (w, h, hover)
        if key not in self._imgs:
            self._imgs = {k: v for k, v in self._imgs.items() if k[:2] == (w, h)}
            self._imgs[key] = ImageTk.PhotoImage(rounded_image(w, h, 16, CARD, "#FFB27A" if hover else LINE,
                                                               width=2 if hover else 1))
        self.delete("all")
        self.create_image(0, 0, image=self._imgs[key], anchor="nw")
        self.create_text(18, 14, text=self.title, anchor="nw", fill=ORANGE_DARK if hover else INK, font=self.f1)
        self.create_text(18, 18 + self.f1.metrics("linespace"), anchor="nw", fill=MUTED, font=self.f2,
                         text=fit_text(self.text, self.f2, w - 36, 1))


class Bubble(tk.Canvas):
    """A rounded chat bubble sized to its (wrapped) text."""

    def __init__(self, parent, text, max_width, fill=ORANGE, fg="white", bg=CARD, size=10):
        f = tkfont.Font(family=FONT, size=size)
        wrapped = fit_text(text, f, max_width - 32)
        lines = wrapped.split("\n")
        w = max(f.measure(l) for l in lines) + 32
        h = len(lines) * f.metrics("linespace") + 20
        super().__init__(parent, width=w, height=h, background=bg, highlightthickness=0, borderwidth=0)
        self._img = ImageTk.PhotoImage(rounded_image(w, h, min(18, h // 2), fill))
        self.create_image(0, 0, image=self._img, anchor="nw")
        self.create_text(16, 10, text=wrapped, anchor="nw", fill=fg, font=f)


class SideNav(tk.Frame):
    """Left side menu with sections, icons and a pill highlight on the current page. Works like the parts
    of ttk.Notebook the app uses: add(), select(), index("current" / "end"), current(), and it sends
    <<NotebookTabChanged>> when the page changes."""

    def __init__(self, parent, host, on_change=None):
        super().__init__(parent, background=CARD)
        self.host = host            # frame the pages are shown in
        self.pages = []             # (frame, title, subtitle, item canvas)
        self.cur = None
        self.on_change = on_change
        self.f_label = tkfont.Font(family=FONT, size=10)
        self.f_bold = tkfont.Font(family=FONT, size=10, weight="bold")
        self.f_icon = tkfont.Font(family=ICONS, size=12)
        self.top = tk.Frame(self, background=CARD)
        self.top.pack(fill="x")
        self.items = tk.Frame(self, background=CARD)
        self.items.pack(fill="both", expand=True, padx=14)
        self.bottom = tk.Frame(self, background=CARD)
        self.bottom.pack(side="bottom", fill="x", padx=14, pady=(0, 14))
        self._imgs = {}

    def section(self, title):
        tk.Label(self.items, text=title.upper(), bg=CARD, fg=FAINT, font=(FONT, 8, "bold"),
                 anchor="w").pack(fill="x", padx=14, pady=(16, 4))

    def add(self, frame, text, icon="", subtitle=""):
        h = self.f_bold.metrics("linespace") + 20
        width = self.f_bold.measure(text) + 90
        c = tk.Canvas(self.items, height=h, width=width, background=CARD, highlightthickness=0, borderwidth=0,
                      cursor="hand2")
        c.pack(fill="x", pady=2)
        index = len(self.pages)
        c.text, c.icon, c.state = text, icon, "normal"
        c.bind("<Configure>", lambda e, i=index: self._paint(i))
        c.bind("<Button-1>", lambda e, i=index: self.select(i))
        c.bind("<Enter>", lambda e, i=index: self._hover(i, True))
        c.bind("<Leave>", lambda e, i=index: self._hover(i, False))
        self.pages.append((frame, text, subtitle, c))
        if self.cur is None:
            self.select(0)

    def _pill(self, w, h, fill):
        key = (w, h, fill)
        if key not in self._imgs:
            self._imgs[key] = ImageTk.PhotoImage(rounded_image(w, h, h // 2, fill))
        return self._imgs[key]

    def _paint(self, i):
        c = self.pages[i][3]
        w, h = c.winfo_width(), c.winfo_height()
        if w < 20:
            return
        active, hover = c.state == "active", c.state == "hover"
        c.delete("all")
        if active or hover:
            c.create_image(0, 0, image=self._pill(w, h, ORANGE_SOFT if active else HOVER), anchor="nw")
        c.create_text(26, h // 2, text=c.icon, fill=ORANGE if active else MUTED, font=self.f_icon)
        c.create_text(50, h // 2, text=c.text, anchor="w", fill=ORANGE_DARK if active else INK,
                      font=self.f_bold if active else self.f_label)
        if active:  # small dot at the end of the pill
            c.create_oval(w - 22, h // 2 - 3, w - 16, h // 2 + 3, fill=ORANGE, outline="")

    def _hover(self, i, on):
        if i != self.cur:
            self.pages[i][3].state = "hover" if on else "normal"
            self._paint(i)

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
            self.pages[self.cur][3].state = "normal"
            self._paint(self.cur)
        self.cur = i
        self.pages[i][3].state = "active"
        self._paint(i)
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
    """Pill buttons, rounded fields, combo boxes, segmented selectors, checkboxes and slim scrollbars,
    all drawn from images."""
    keep = root._rounded_imgs = []

    def photo(image):
        p = ImageTk.PhotoImage(image, master=root)
        keep.append(p)
        return p

    def img(w, h, r, fill, outline=None, width=1):
        return photo(rounded_image(w, h, r, fill, outline, width=width))

    # Buttons: pills
    W, H = 48, 36
    R = H // 2 - 1
    b = dict(border=(R, R), sticky="nsew")
    style.element_create("RButton.border", "image", img(W, H, R, CARD, "#DED9D1"),
                         ("disabled", img(W, H, R, "#F7F6F4", "#EEEBE6")),
                         ("pressed", img(W, H, R, "#FFEBD8", ORANGE)),
                         ("active", img(W, H, R, "#FFF7EF", "#FFB27A")), **b)
    style.element_create("AButton.border", "image", img(W, H, R, ORANGE),
                         ("disabled", img(W, H, R, "#F9CBA0")),
                         ("pressed", img(W, H, R, ORANGE_DARK)), ("active", img(W, H, R, ORANGE_DARK)), **b)
    style.element_create("SButton.border", "image", img(W, H, R, CARD),
                         ("pressed", img(W, H, R, HOVER)), ("active", img(W, H, R, HOVER)), **b)
    for name, element in (("TButton", "RButton.border"), ("Accent.TButton", "AButton.border"),
                          ("Side.TButton", "SButton.border")):
        style.layout(name, [(element, {"sticky": "nsew", "children": [
            ("Button.padding", {"sticky": "nsew", "children": [("Button.label", {"sticky": "nsew"})]})]})])
    # the corners outside the pill show the style's background: keep it the tile's white in every state
    corners = [("disabled", CARD), ("pressed", CARD), ("active", CARD), ("!disabled", CARD)]
    style.configure("TButton", padding=(18, 7), background=CARD, foreground=INK, width=-4)
    style.map("TButton", background=corners, foreground=[("disabled", "#A0A4AB")])
    style.configure("Accent.TButton", padding=(20, 7), foreground="white", font=(FONT, 10, "bold"),
                    background=CARD)
    style.map("Accent.TButton", foreground=[("disabled", "white")], background=corners)
    style.configure("Side.TButton", padding=(16, 7), foreground=INK, anchor="w", font=(FONT, 10), background=CARD)
    style.map("Side.TButton", foreground=[("active", ORANGE_DARK)], background=corners)

    # Fields: rounded
    FR = 12
    f = dict(border=(FR, FR), sticky="nsew")
    field = img(W, H, FR, "#FBFAF8", "#E3DED6")
    focus = img(W, H, FR, CARD, ORANGE, width=2)
    off = img(W, H, FR, "#F5F3F0", "#EEEBE6")
    style.element_create("REntry.field", "image", field, ("disabled", off), ("focus", focus), **f)
    style.layout("TEntry", [("REntry.field", {"sticky": "nsew", "children": [
        ("Entry.padding", {"sticky": "nsew", "children": [("Entry.textarea", {"sticky": "nsew"})]})]})])
    style.configure("TEntry", padding=(12, 7), fieldbackground="#FBFAF8")
    style.element_create("RCombo.field", "image", field, ("disabled", off), ("focus", focus), **f)
    style.layout("TCombobox", [("RCombo.field", {"sticky": "nsew", "children": [
        ("Combobox.downarrow", {"side": "right", "sticky": "ns"}),
        ("Combobox.padding", {"expand": "1", "sticky": "nsew", "children": [
            ("Combobox.textarea", {"sticky": "nsew"})]})]})])
    style.configure("TCombobox", padding=(12, 6), arrowsize=14, background="#FBFAF8", arrowcolor=MUTED,
                    fieldbackground="#FBFAF8")
    style.map("TCombobox", background=[("active", "#FBFAF8"), ("pressed", "#FBFAF8")],
              fieldbackground=[("readonly", "#FBFAF8")])

    # Segmented selector (radio buttons as pills)
    style.element_create("RSeg.border", "image", img(W, H, R, CARD, "#DED9D1"),
                         ("selected", img(W, H, R, ORANGE)), ("active", img(W, H, R, "#FFF7EF", "#FFB27A")), **b)
    style.layout("Seg.TRadiobutton", [("RSeg.border", {"sticky": "nsew", "children": [
        ("Radiobutton.padding", {"sticky": "nsew", "children": [("Radiobutton.label", {"sticky": "nsew"})]})]})])
    style.configure("Seg.TRadiobutton", padding=(18, 7), background=CARD, font=(FONT, 10, "bold"))
    style.map("Seg.TRadiobutton", foreground=[("selected", "white")], background=[("active", CARD)])
    # Smaller pills for toolbars (their own, shorter images)
    w2, h2 = 40, 28
    r2 = h2 // 2 - 1
    b2 = dict(border=(r2, r2), sticky="nsew")
    style.element_create("RSegS.border", "image", img(w2, h2, r2, CARD, "#DED9D1"),
                         ("selected", img(w2, h2, r2, ORANGE)), ("active", img(w2, h2, r2, "#FFF7EF", "#FFB27A")),
                         **b2)
    style.layout("SegSm.TRadiobutton", [("RSegS.border", {"sticky": "nsew", "children": [
        ("Radiobutton.padding", {"sticky": "nsew", "children": [("Radiobutton.label", {"sticky": "nsew"})]})]})])
    style.configure("SegSm.TRadiobutton", padding=(12, 2), background=CARD, font=(FONT, 9, "bold"))
    style.map("SegSm.TRadiobutton", foreground=[("selected", "white")], background=[("active", CARD)])
    style.element_create("RButtonS.border", "image", img(w2, h2, r2, CARD, "#DED9D1"),
                         ("disabled", img(w2, h2, r2, "#F7F6F4", "#EEEBE6")),
                         ("pressed", img(w2, h2, r2, "#FFEBD8", ORANGE)),
                         ("active", img(w2, h2, r2, "#FFF7EF", "#FFB27A")), **b2)
    style.layout("Small.TButton", [("RButtonS.border", {"sticky": "nsew", "children": [
        ("Button.padding", {"sticky": "nsew", "children": [("Button.label", {"sticky": "nsew"})]})]})])
    style.configure("Small.TButton", padding=(12, 2), background=CARD, foreground=INK, font=(FONT, 9), width=-4)
    style.map("Small.TButton", background=corners, foreground=[("disabled", "#A0A4AB")])

    # Checkboxes: rounded squares with a tick
    def check(on):
        S, s = 30, 3
        im = Image.new("RGBA", (S * s, S * s), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        box = (2 * s, 6 * s, 20 * s, 24 * s)
        if on:
            d.rounded_rectangle(box, radius=6 * s, fill=ORANGE)
            d.line([(6 * s, 15 * s), (10 * s, 19 * s), (17 * s, 11 * s)], fill="white", width=int(2.4 * s),
                   joint="curve")
        else:
            d.rounded_rectangle(box, radius=6 * s, fill=CARD, outline="#CFC9C0", width=int(1.4 * s))
        return photo(im.resize((S, S), Image.LANCZOS))
    style.element_create("RCheck.indicator", "image", check(False), ("selected", check(True)), sticky="")
    for name in ("TCheckbutton", "Card.TCheckbutton"):
        style.layout(name, [("Checkbutton.padding", {"sticky": "nswe", "children": [
            ("RCheck.indicator", {"side": "left", "sticky": ""}),
            ("Checkbutton.label", {"side": "left", "sticky": "nswe"})]})])
        style.configure(name, padding=(0, 2), background=CARD)
        style.map(name, background=[("active", CARD)])

    # Slim rounded scrollbars (no arrows)
    def thumb(w, h, fill):
        return img(w, h, min(w, h) // 2, fill)
    style.element_create("RThumbV", "image", thumb(10, 40, "#D8D3CB"), ("active", thumb(10, 40, "#BDB6AC")),
                         ("pressed", thumb(10, 40, "#A9A196")), border=(4, 8), sticky="nsew")
    style.element_create("RThumbH", "image", thumb(40, 10, "#D8D3CB"), ("active", thumb(40, 10, "#BDB6AC")),
                         ("pressed", thumb(40, 10, "#A9A196")), border=(8, 4), sticky="nsew")
    style.layout("Vertical.TScrollbar", [("Vertical.Scrollbar.trough", {"sticky": "ns", "children": [
        ("RThumbV", {"expand": "1", "sticky": "nswe"})]})])
    style.layout("Horizontal.TScrollbar", [("Horizontal.Scrollbar.trough", {"sticky": "ew", "children": [
        ("RThumbH", {"expand": "1", "sticky": "nswe"})]})])
    for name in ("Vertical.TScrollbar", "Horizontal.TScrollbar"):
        style.configure(name, troughcolor=CARD, background=CARD, borderwidth=0, bordercolor=CARD,
                        lightcolor=CARD, darkcolor=CARD, relief="flat")

    # Tables: no frame (they sit in tiles), soft headings
    style.configure("Treeview", borderwidth=0, relief="flat", background=CARD, fieldbackground=CARD)
    style.layout("Treeview", [("Treeview.treearea", {"sticky": "nswe"})])
    style.configure("TPanedwindow", background=BG)
    style.configure("Sash", sashthickness=10, background=BG, gripcount=0)
