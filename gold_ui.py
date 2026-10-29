"""GOLD Express look: rounded tiles with soft shadows, a side menu with pill highlights, gradient
stat cards, chat bubbles, and rounded buttons / fields / selectors / checkboxes / scrollbars.

Tkinter draws only square shapes, so every rounded or gradient surface is an image (Pillow), redrawn
when its size changes.
"""
import tkinter as tk
import weakref
from pathlib import Path
from tkinter import font as tkfont

from PIL import Image, ImageDraw, ImageFilter, ImageTk

FONT = "Segoe UI"
ICONS = "Segoe Fluent Icons" if Path(r"C:\Windows\Fonts\SegoeIcons.ttf").exists() else "Segoe MDL2 Assets"


def sharp_on_scaled_screens():
    """Draw at the screen's real resolution. Without this, at 125% / 150% Windows scaling Windows
    draws the window at 100% and stretches it - blurry, pixelated text and edges.
    Call before the first window is created."""
    import ctypes
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)  # per monitor: sharp on every screen
    except (AttributeError, OSError):
        try:
            ctypes.windll.user32.SetProcessDPIAware()  # older Windows
        except (AttributeError, OSError):
            pass

def _initial_theme():
    """'light' or 'dark', as saved in the settings (Settings > Appearance). Read here, before anything is
    drawn, because the colours below are used as defaults everywhere."""
    import json
    import os
    if os.environ.get("GOLD_THEME"):  # for testing either look without changing the settings
        return os.environ["GOLD_THEME"]
    try:
        from open_gold import HERE
        s = json.loads((HERE / "gold_app_settings.json").read_text(encoding="utf-8"))
    except Exception:
        return "neo"
    # 2.15.0: the Futuristic look is the new default - once for everyone (Settings > Appearance switches back)
    return s.get("theme", "neo") if s.get("theme_v3") else "neo"


THEMES = {
    "light": dict(
        BG="#F3F1EC", CARD="#FFFFFF", INK="#1F2328", MUTED="#7D838C", FAINT="#A7ACB3", LINE="#EBE7E1",
        ORANGE="#FF7900", ORANGE_DARK="#E06A00", ORANGE_SOFT="#FFF0E1", HOVER="#F6F3EF",
        FIELD="#FBFAF8", FIELD_LINE="#E3DED6", PLACEHOLDER="#9CA3AF", ACCENT_OFF="#F9CBA0",
        SUB_INK="#4B5159", TRACK="#F0EDE8", ZEBRA="#FAF9F7", HEAD_BG="#FAF8F5", HEAD_ACTIVE="#F4F1EC",
        BTN_LINE="#DED9D1", BTN_HOVER="#FFF7EF", BTN_HOVER_LINE="#FFB27A", BTN_PRESS="#FFEBD8",
        DISABLED="#F7F6F4", DISABLED_LINE="#EEEBE6", DISABLED_INK="#A0A4AB", CHECK_LINE="#CFC9C0",
        THUMB="#D8D3CB", THUMB_HOVER="#BDB6AC", THUMB_PRESS="#A9A196",
        GREEN_FG="#1E7B34", GREEN_BG="#E4F4E8", AMBER_FG="#A15C00", AMBER_BG="#FFF3D6",
        RED_FG="#C62828", RED_BG="#FDE7E7", GREY_FG="#595959", GREY_BG="#EFEFEF",
    ),
    "dark": dict(
        BG="#141518", CARD="#1F2024", INK="#E8E9EB", MUTED="#A0A5AD", FAINT="#767B84", LINE="#2E3035",
        ORANGE="#FF7900", ORANGE_DARK="#FF9640", ORANGE_SOFT="#3B2716", HOVER="#292A2F",
        FIELD="#18191C", FIELD_LINE="#3A3C42", PLACEHOLDER="#6E737B", ACCENT_OFF="#7A4A22",
        SUB_INK="#C9CCD1", TRACK="#2C2E33", ZEBRA="#232428", HEAD_BG="#26272B", HEAD_ACTIVE="#2E3035",
        BTN_LINE="#3A3C42", BTN_HOVER="#2E2420", BTN_HOVER_LINE="#B8611E", BTN_PRESS="#3B2716",
        DISABLED="#232428", DISABLED_LINE="#2C2E33", DISABLED_INK="#5F646C", CHECK_LINE="#55585F",
        THUMB="#3A3C42", THUMB_HOVER="#4A4D54", THUMB_PRESS="#5A5D64",
        GREEN_FG="#7FD99A", GREEN_BG="#1C3324", AMBER_FG="#F2B861", AMBER_BG="#3A2E16",
        RED_FG="#FF8A8A", RED_BG="#3D1E21", GREY_FG="#A0A5AD", GREY_BG="#2A2B2F",
    ),
    # Futuristic: deep-space indigo, glass tiles with glowing edges, electric violet -> blue accent
    "neo": dict(
        BG="#0C0E22", CARD="#161937", INK="#EEF0FF", MUTED="#A3A8D6", FAINT="#6F75AD", LINE="#272B57",
        ORANGE="#7C6CFF", ORANGE_DARK="#B3A9FF", ORANGE_SOFT="#25225A", HOVER="#1E2250",
        FIELD="#10122C", FIELD_LINE="#2C3170", PLACEHOLDER="#6D73A8", ACCENT_OFF="#3D3878",
        SUB_INK="#C7CBF0", TRACK="#232755", ZEBRA="#191C3F", HEAD_BG="#1B1E44", HEAD_ACTIVE="#24285A",
        BTN_LINE="#2E3370", BTN_HOVER="#211F52", BTN_HOVER_LINE="#7C6CFF", BTN_PRESS="#2A2766",
        DISABLED="#151834", DISABLED_LINE="#232750", DISABLED_INK="#575D93", CHECK_LINE="#3B4185",
        THUMB="#2C3168", THUMB_HOVER="#3A4086", THUMB_PRESS="#4A51A0",
        GREEN_FG="#4ADE9B", GREEN_BG="#123527", AMBER_FG="#FBC562", AMBER_BG="#3A2F14",
        RED_FG="#FF7A90", RED_BG="#3A1630", GREY_FG="#A3A8D6", GREY_BG="#20234A",
    ),
}
# Every theme: the accent gradient (buttons, side menu in Futuristic) and the GOLD bot's "AI" colours
for _t, _extra in {"light": dict(ACCENT2="#FF9A3D", AI_A="#7C5CFF", AI_B="#1FB6E8", AI_SOFT="#F1EEFF"),
                   "dark": dict(ACCENT2="#FF9A3D", AI_A="#8B6CFF", AI_B="#22C3EE", AI_SOFT="#231F3D"),
                   "neo": dict(ACCENT2="#3FA2FF", AI_A="#9D6BFF", AI_B="#22D3EE", AI_SOFT="#221E55")}.items():
    THEMES[_t].update(_extra)
THEME_NAMES = {"neo": "Futuristic", "dark": "Dark", "light": "Light"}
THEME = _initial_theme() if _initial_theme() in THEMES else "neo"
globals().update(THEMES[THEME])
DARK = THEME in ("dark", "neo")
NEO = THEME == "neo"

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
} if not DARK else {
    "sun":      ("#2A2418", "#3A2E17", "#6A4C14", "#FFC266"),
    "peach":    ("#2B2119", "#3B2A1C", "#6E4220", "#FFA866"),
    "mint":     ("#18261E", "#1E3326", "#2E6B45", "#7FD99A"),
    "amber":    ("#2A2516", "#3A3116", "#6E5A16", "#F2C461"),
    "rose":     ("#2B1C1E", "#3B2226", "#73323A", "#FF8A8A"),
    "lavender": ("#1F1E2E", "#2E2A26", "#4A4480", "#B7B0FF"),
    "sky":      ("#18212E", "#1C2B3E", "#2D4F80", "#8FC0FF"),
    "grey":     ("#222327", "#2A2B30", "#3A3C42", "#B0B5BD"),
}
PALETTES.update({
    # vivid cards (white text, wave lines), for dashboards - the same in both themes
    "v_blue":   ("#55BDF7", "#1F86E0", "#8FD6FF", "#FFFFFF"),
    "v_green":  ("#A3D550", "#56A72C", "#C8EC8E", "#FFFFFF"),
    "v_orange": ("#FFB552", "#FF7A00", "#FFD594", "#FFFFFF"),
    "v_purple": ("#BE6EDC", "#8A3FB8", "#DDA8F2", "#FFFFFF"),
    "v_teal":   ("#33C7B3", "#128577", "#86E6D8", "#FFFFFF"),
    "v_rose":   ("#FF7E8A", "#DD3F58", "#FFB8BF", "#FFFFFF"),
} if not NEO else {
    # Futuristic: dark glass cards with a glowing neon wave (light colour, neon colour, glow, caption colour)
    "v_blue":   ("#7DD3FC", "#3B9BFF", "#3B9BFF", "#7DD3FC"),
    "v_green":  ("#86EFAC", "#2DD4A0", "#2DD4A0", "#86EFAC"),
    "v_orange": ("#FFC48A", "#FF8A3D", "#FF8A3D", "#FFC48A"),
    "v_purple": ("#D2B8FF", "#9D6BFF", "#9D6BFF", "#D2B8FF"),
    "v_teal":   ("#7FF0E0", "#22D3C5", "#22D3C5", "#7FF0E0"),
    "v_rose":   ("#FFA3B5", "#FF5C7C", "#FF5C7C", "#FFA3B5"),
    # the plain palettes become neon cards too (Overview cards, RAG status)
    "sun":      ("#FFD48A", "#FFB020", "#FFB020", "#FFD48A"),
    "peach":    ("#FFC48A", "#FF8A3D", "#FF8A3D", "#FFC48A"),
    "mint":     ("#86EFAC", "#2DD4A0", "#2DD4A0", "#86EFAC"),
    "amber":    ("#FFE08A", "#FBBF24", "#FBBF24", "#FFE08A"),
    "rose":     ("#FFA3B5", "#FF5C7C", "#FF5C7C", "#FFA3B5"),
    "lavender": ("#D2B8FF", "#9D6BFF", "#9D6BFF", "#D2B8FF"),
    "sky":      ("#7DD3FC", "#3B9BFF", "#3B9BFF", "#7DD3FC"),
    "grey":     ("#C7CBF0", "#6F75AD", "#6F75AD", "#C7CBF0"),
})
VIVID = set(PALETTES) if NEO else {k for k in PALETTES if k.startswith("v_")}
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


def mix(a, b, t):
    """Colour between a and b (0..1) as #rrggbb."""
    a, b = _hex(a), _hex(b)
    return "#%02x%02x%02x" % tuple(round(x + (y - x) * t) for x, y in zip(a, b))


def gradient(w, h, c0, c1, horizontal=True):
    """A plain RGBA gradient from c0 to c1 (left -> right, or top -> bottom)."""
    n = max(w if horizontal else h, 2)
    line = Image.new("RGBA", (n, 1))
    a, b = _hex(c0), _hex(c1)
    for i in range(n):
        t = i / (n - 1)
        line.putpixel((i, 0), tuple(round(x + (y - x) * t) for x, y in zip(a, b)) + (255,))
    if horizontal:
        return line.resize((max(w, 2), max(h, 2)))
    return line.rotate(-90, expand=True).resize((max(w, 2), max(h, 2)))


def gradient_rounded(w, h, r, c0, c1, horizontal=True):
    """A rounded shape filled with a gradient (pills, bubbles, active menu items)."""
    mask = rounded_image(w, h, r, (255, 255, 255, 255)).split()[-1]
    out = Image.new("RGBA", (max(w, 2), max(h, 2)), (0, 0, 0, 0))
    out.paste(gradient(w, h, c0, c1, horizontal), (0, 0), mask)
    return out


def gradient_ring(w, h, r, c0, c1, width=2, fill=None):
    """A rounded outline drawn with a gradient (glowing AI borders), optionally filled inside."""
    s = 3
    outer = rounded_image(w, h, r, (255, 255, 255, 255)).split()[-1]
    inner = Image.new("L", (w, h), 0)
    inner.paste(rounded_image(w - 2 * width, h - 2 * width, max(r - width, 1), (255, 255, 255, 255)).split()[-1],
                (width, width))
    ring = Image.composite(Image.new("L", (w, h), 0), outer, inner)
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    if fill:
        out.paste(Image.new("RGBA", (w, h), fill), (0, 0), inner)
    out.paste(gradient(w, h, c0, c1), (0, 0), ring)
    return out


def tile_image(w, h, r, fill=CARD, shadow=True, outline=None, m=6):
    """A rounded tile with a soft shadow underneath, inset by m pixels so the shadow fits."""
    if NEO and fill == CARD and outline is None:
        return glass_tile_image(w, h, r, m)
    if isinstance(outline, tuple):  # (c0, c1[, width]): a gradient edge with a soft glow (the AI composer)
        c0, c1, width = (outline + (2,))[:3]
        img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        if width >= 2:
            glow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            ImageDraw.Draw(glow).rounded_rectangle((m, m, w - m, h - m), radius=r, fill=_hex(c0) + (70,))
            img = Image.alpha_composite(img, glow.filter(ImageFilter.GaussianBlur(5)))
        img.alpha_composite(gradient_ring(w - 2 * m, h - 2 * m, r, c0, c1, width=width, fill=fill), (m, m))
        return img
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    if shadow:
        sh = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        ImageDraw.Draw(sh).rounded_rectangle((m, m + 3, w - m, h - m + 2), radius=r, fill=(0, 0, 0, 90) if DARK else (70, 50, 20, 26))
        img = Image.alpha_composite(img, sh.filter(ImageFilter.GaussianBlur(5)))
    card = rounded_image(w - 2 * m, h - 2 * m, r, fill, outline)
    img.alpha_composite(card, (m, m))
    return img


def glass_tile_image(w, h, r, m=6):
    """Futuristic tile: dark glass (a touch lighter at the top), a thin luminous edge and a violet glow."""
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    glow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(glow).rounded_rectangle((m, m + 2, w - m, h - m + 2), radius=r, fill=(70, 55, 190, 70))
    img = Image.alpha_composite(img, glow.filter(ImageFilter.GaussianBlur(6)))
    iw, ih = w - 2 * m, h - 2 * m
    body = rounded_image(iw, ih, r, CARD)  # flat inside: the tile's widgets sit on the same colour
    edge = gradient_ring(iw, ih, r, "#6A62E0", "#2A2F66", width=1)
    body.alpha_composite(edge)
    img.alpha_composite(body, (m, m))
    return img


def neon_card_image(w, h, r, palette):
    """Futuristic stat card: dark glass tinted with the palette colour, a glowing neon wave across the
    top half (like a sparkline) with a soft fill under it, and a thin coloured edge."""
    import math
    light, neon, glow, _ = PALETTES[palette]
    base = gradient_rounded(w, h, r, mix(CARD, neon, 0.16), mix(CARD, BG, 0.25), horizontal=False)
    s = 3
    W, H = w * s, h * s
    def y(x):  # rises from the bottom-left (under the text) to the right, with a gentle wiggle
        t = min(max(x / w, 0), 1)
        return h * (0.95 - 0.5 * t * t * (3 - 2 * t) + 0.05 * math.sin(t * 2 * math.pi * 1.6))
    pts = [(x * s, y(x) * s) for x in range(-4, w + 8, 3)]
    area = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(area).polygon(pts + [(W + 8 * s, H), (-4 * s, H)], fill=_hex(neon) + (38,))
    fade = gradient(W, H, "#ffffff", "#000000", horizontal=False).convert("L")
    area.putalpha(Image.composite(area.split()[-1], Image.new("L", (W, H), 0), fade))
    line = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(line).line(pts, fill=_hex(neon) + (255,), width=int(2.2 * s), joint="curve")
    halo = line.filter(ImageFilter.GaussianBlur(4 * s))
    fx = Image.alpha_composite(Image.alpha_composite(area, halo), line).resize((w, h), Image.LANCZOS)
    mask = rounded_image(w, h, r, (255, 255, 255, 255)).split()[-1]
    clipped = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    clipped.paste(fx, (0, 0), mask)
    base.alpha_composite(clipped)
    base.alpha_composite(gradient_ring(w, h, r, mix(neon, "#ffffff", 0.2), mix(neon, CARD, 0.75), width=1))
    return base


def gradient_card_image(w, h, r, palette):
    """Rounded card with a soft diagonal gradient and a warm glow in the lower right."""
    if NEO and palette in VIVID:
        return neon_card_image(w, h, r, palette)
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


def smooth_window_changes(root):
    """Maximize / restore / un-minimize: lay the window out and redraw every rounded tile in one go,
    instead of tile by tile a moment later (which looked like a glitch). Drag-resizing is unchanged."""
    st = {"state": root.state(), "size": None, "job": None}
    cover = tk.Frame(root, background=BG)  # a plain page shown while everything moves into place

    def uncover():
        st["job"] = None
        _Redraw.redraw_all(root)
        cover.place_forget()

    def changed(e):
        if e.widget is not root:
            return
        state, size = root.state(), (e.width, e.height)
        jump = st["size"] and (abs(size[0] - st["size"][0]) > 200 or abs(size[1] - st["size"][1]) > 200)
        new_state = state != st["state"]
        st["state"], st["size"] = state, size
        if state != "iconic" and (new_state or jump):
            cover.place(x=0, y=0, relwidth=1, relheight=1)
            cover.lift()
            if st["job"]:
                root.after_cancel(st["job"])
            st["job"] = root.after(150, uncover)

    def minimized(e):  # covered while minimized, so coming back shows no half-drawn (black) parts
        if e.widget is root:
            cover.place(x=0, y=0, relwidth=1, relheight=1)
            cover.lift()

    def shown(e):
        if e.widget is root and cover.winfo_manager():
            if st["job"]:
                root.after_cancel(st["job"])
            st["job"] = root.after(150, uncover)

    root.bind("<Configure>", changed, add="+")
    root.bind("<Unmap>", minimized, add="+")
    root.bind("<Map>", shown, add="+")


class _Redraw:
    """Redraw a canvas a moment after its size changes (resizing the window stays smooth)."""
    _all = weakref.WeakSet()

    @classmethod
    def redraw_all(cls, root):
        root.update_idletasks()  # the new layout, all at once
        for w in list(cls._all):
            try:
                if w.winfo_ismapped():
                    w._check()
            except tk.TclError:
                pass

    def _watch(self):
        self._size = None
        self._pending = None
        _Redraw._all.add(self)
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

    PAD = 11

    def __init__(self, parent, caption="", icon="", palette="sun", sub_lines=2, big_size=24, bg=BG,
                 command=None, **kw):
        self.f_cap = tkfont.Font(family=FONT, size=7, weight="bold")
        self.f_sub = tkfont.Font(family=FONT, size=8)
        self.big_size = big_size
        big_ls = tkfont.Font(family="Segoe UI Light", size=big_size).metrics("linespace")
        height = (self.PAD + self.f_cap.metrics("linespace") + 2 + big_ls + 2
                  + sub_lines * self.f_sub.metrics("linespace") + self.PAD - 2)
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
        ink, sub_ink = ("#FFFFFF", "#FFFFFF") if vivid else (INK, SUB_INK)
        p = self.PAD
        self.delete("all")
        self.create_image(0, 0, image=self._img, anchor="nw")
        bubble = (self.f_cap.metrics("linespace") + 20) if self.icon else 0
        cap = fit_text(self.caption.upper(), self.f_cap, w - 2 * p - bubble, 1)
        self.create_text(p + 2, p, text=cap, anchor="nw", fill=accent, font=self.f_cap)
        y = p + self.f_cap.metrics("linespace") + 2
        size = self.big_size  # the big value on one line: a smaller font when it is long
        big = tkfont.Font(family="Segoe UI Light", size=size)
        while size > 11 and big.measure(self.big) > w - 2 * p - 4:
            size -= 1
            big = tkfont.Font(family="Segoe UI Light", size=size)
        self.create_text(p, y, text=self.big, anchor="nw", fill=ink,
                         font=tkfont.Font(family="Segoe UI Semibold" if vivid else "Segoe UI Light", size=size))
        y += tkfont.Font(family="Segoe UI Light", size=self.big_size).metrics("linespace") + 2
        self.create_text(p + 2, y, text=fit_text(self.sub, self.f_sub, w - 2 * p - 4, self.sub_lines),
                         anchor="nw", fill=sub_ink, font=self.f_sub)
        if self.icon:
            d = self.f_cap.metrics("linespace") + 10
            if self._bubble is None or self._bubble.width() != d or getattr(self, "_bubble_vivid", None) != vivid:
                self._bubble = ImageTk.PhotoImage(rounded_image(d, d, d // 2, (255, 255, 255, 70 if vivid else 30 if DARK else 210)))
                self._bubble_vivid = vivid
            self.create_image(w - p + 4, p - 4, image=self._bubble, anchor="ne")
            self.create_text(w - p + 4 - d // 2, p - 4 + d // 2, text=self.icon, fill=accent, font=(ICONS, 8))


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
            dr.ellipse((0, 0, d * s - 1, d * s - 1), fill=TRACK)
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
            track = ImageTk.PhotoImage(rounded_image(bar_w, bh, bh // 2, TRACK))
            self._imgs.append(track)
            self.create_image(label_w, y, image=track, anchor="w")
            bw = max(bh, int(bar_w * value / top))
            bar = ImageTk.PhotoImage(rounded_image(bw, bh, bh // 2, colour))
            self._imgs.append(bar)
            self.create_image(label_w, y, image=bar, anchor="w")
            self.create_text(label_w + bar_w + 8, y, text=str(value), anchor="w", fill=INK, font=self.f_value)
        if self.on_click:
            self.configure(cursor="hand2")


class Progress(tk.Canvas, _Redraw):
    """A rounded progress bar: set(fraction 0..1)."""

    def __init__(self, parent, height=10, bg=CARD, colour=ORANGE):
        super().__init__(parent, height=height, background=bg, highlightthickness=0, borderwidth=0)
        self.fraction, self.colour, self._imgs = 0.0, colour, []
        self._watch()

    def set(self, fraction):
        self.fraction = max(0.0, min(1.0, fraction))
        if self._size:
            self.redraw(*self._size)

    def redraw(self, w, h):
        self.delete("all")
        track = ImageTk.PhotoImage(rounded_image(w, h, h // 2, TRACK))
        self._imgs = [track]
        self.create_image(0, 0, image=track, anchor="nw")
        fw = int(w * self.fraction)
        if fw >= h:
            bar = ImageTk.PhotoImage(rounded_image(fw, h, h // 2, self.colour))
            self._imgs.append(bar)
            self.create_image(0, 0, image=bar, anchor="nw")


class Bot(tk.Canvas):
    """The Friendly GOLD bot, animated: it floats gently above its shadow ("idle"), bobs faster with a
    little wiggle while it works ("busy"), and hops when clicked."""

    _cache = {}

    def __init__(self, parent, image_path, size=120, bg=CARD, mode="idle", clickable=True, halo=False):
        w, h = int(size * 1.0), int(size * 1.22)
        super().__init__(parent, width=w, height=h, background=bg, highlightthickness=0, borderwidth=0)
        self.size, self.mode, self._job, self._i = size, mode, None, 0
        self.frames = {m: self._frames(image_path, size, m, bg, halo) for m in ("idle", "busy", "hop")}
        self._item = self.create_image(w // 2, 0, anchor="n")
        if clickable:
            self.configure(cursor="hand2")
            self.bind("<Button-1>", lambda e: self.hop())
        self.start(mode)

    @classmethod
    def _frames(cls, path, size, mode, bg, halo=False):
        import math
        key = (str(path), size, mode, bg, halo)
        if key in cls._cache:
            return cls._cache[key]
        bot = Image.open(path).convert("RGBA")
        bot.thumbnail((int(size * 0.92), int(size * 0.92)), Image.LANCZOS)
        w, h = int(size * 1.0), int(size * 1.22)
        n = {"idle": 36, "busy": 16, "hop": 14}[mode]
        frames = []
        for i in range(n):
            t = i / n
            if mode == "hop":  # one quick jump
                lift = math.sin(math.pi * t) * 0.16
                angle = math.sin(2 * math.pi * t) * 6
            else:
                lift = (math.sin(2 * math.pi * t) + 1) / 2 * (0.06 if mode == "idle" else 0.09)
                angle = math.sin(4 * math.pi * t) * 4 if mode == "busy" else 0
            im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            if halo:  # an AI glow behind the bot, breathing slowly
                pulse = (math.sin(2 * math.pi * t) + 1) / 2
                g = Image.new("RGBA", (w, h), (0, 0, 0, 0))
                gd = ImageDraw.Draw(g)
                cx, cy, rr = w / 2, h * 0.43, size * (0.27 + 0.03 * pulse)  # fades out well inside the frame
                gd.ellipse((cx - rr, cy - rr, cx + rr, cy + rr), fill=_hex(AI_A) + (int(120 + 60 * pulse),))
                gd.ellipse((cx - rr * 0.55, cy - rr * 0.9, cx + rr * 1.05, cy + rr * 0.5),
                           fill=_hex(AI_B) + (int(90 + 50 * pulse),))
                im.alpha_composite(g.filter(ImageFilter.GaussianBlur(size * 0.08)))
            # shadow: smaller and lighter when the bot is higher
            sw = w * (0.62 - lift * 1.4)
            sy = h - h * 0.07
            shadow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            alpha = int(70 - lift * 250) if not DARK else int(110 - lift * 300)
            ImageDraw.Draw(shadow).ellipse((w / 2 - sw / 2, sy - h * 0.035, w / 2 + sw / 2, sy + h * 0.035),
                                           fill=(120, 160, 220, max(alpha, 20)) if not DARK else (0, 0, 0, max(alpha, 30)))
            im.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(max(1, size // 40))))
            b = bot.rotate(angle, resample=Image.BICUBIC, expand=True) if angle else bot
            top = int(h * 0.02 + (0.12 - lift) * size * 0.9)
            im.alpha_composite(b, ((w - b.width) // 2, max(0, top)))
            frames.append(ImageTk.PhotoImage(im))
        cls._cache[key] = frames
        return frames

    def start(self, mode="idle"):
        self.mode, self._i = mode, 0
        if self._job is None:
            self._tick()

    def hop(self):
        if self.mode != "busy":
            self.start("hop")

    def stop(self):
        if self._job:
            self.after_cancel(self._job)
            self._job = None

    def _tick(self):
        if not self.winfo_exists():
            return
        frames = self.frames[self.mode]
        self.itemconfigure(self._item, image=frames[self._i % len(frames)])
        self._i += 1
        if self.mode == "hop" and self._i >= len(frames):
            self.mode, self._i = "idle", 0
        delay = {"idle": 70, "busy": 50, "hop": 35}[self.mode]
        self._job = self.after(delay, self._tick)


class AIBanner(tk.Canvas, _Redraw):
    """The GOLD bot's header: a rounded, slowly flowing aurora gradient (AI colours) with the bot, its name,
    an "AI" badge, a hint, an optional chip (the order in view) and a "New chat" button drawn on it."""

    def __init__(self, parent, bot_path=None, title="", hint="", on_new=None, bg=CARD, height=64):
        super().__init__(parent, height=height, background=bg, highlightthickness=0, borderwidth=0)
        self.title, self.hint, self.chip, self.on_new = title, hint, "", on_new
        self.f_title = tkfont.Font(family="Segoe UI Semibold", size=12)
        self.f_hint = tkfont.Font(family=FONT, size=9)
        self.f_badge = tkfont.Font(family=FONT, size=8, weight="bold")
        self._bot = None
        if bot_path:
            b = Image.open(bot_path).convert("RGBA")
            b.thumbnail((height - 18, height - 18), Image.LANCZOS)
            self._bot = ImageTk.PhotoImage(b)
        self._frames, self._i, self._job, self._imgs = [], 0, None, []
        self._watch()
        self.bind("<Button-1>", self._clicked)
        self.bind("<Motion>", self._motion)
        self._new_box = None

    def set_chip(self, text):
        self.chip = text or ""
        if self._size:
            self._draw_fg()

    def redraw(self, w, h):
        # a strip twice as wide, looping: AI_A -> AI_B -> pink -> AI_A; frames slide along it
        cols = [AI_A, AI_B, "#E879F9", AI_A]
        n = 3
        wide = Image.new("RGBA", (w * 2, h))
        seg = (w * 2) // n
        for k in range(n):
            wide.paste(gradient(seg + 1, h, cols[k], cols[k + 1]), (k * seg, 0))
        blobs = Image.new("RGBA", (w * 2, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(blobs)
        for cx, cy, rr, a in ((0.15, 0.2, 0.35, 70), (0.55, 0.9, 0.4, 60), (0.85, 0.1, 0.3, 70)):
            d.ellipse(((cx * 2 * w) - rr * h * 3, cy * h - rr * h * 3, (cx * 2 * w) + rr * h * 3, cy * h + rr * h * 3),
                      fill=(255, 255, 255, a))
        wide = Image.alpha_composite(wide, blobs.filter(ImageFilter.GaussianBlur(h * 0.6)))
        mask = rounded_image(w, h, 16, (255, 255, 255, 255)).split()[-1]
        self._frames = []
        steps = 48
        for i in range(steps):
            x = int(i / steps * w)
            frame = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            frame.paste(wide.crop((x, 0, x + w, h)), (0, 0), mask)
            self._frames.append(ImageTk.PhotoImage(frame))
        self.delete("all")
        self._bg = self.create_image(0, 0, anchor="nw", image=self._frames[0])
        self._draw_fg()
        if self._job is None:
            self._tick()

    def _draw_fg(self):
        self.delete("fg")
        w, h = self._size
        x = 14
        if self._bot:
            self.create_image(x, h // 2, image=self._bot, anchor="w", tags="fg")
            x += self._bot.width() + 10
        ty = h // 2 - self.f_title.metrics("linespace") // 2 - 1  # title above the middle, hint below it
        self.create_text(x, ty, text=self.title, anchor="w", fill="white", font=self.f_title, tags="fg")
        tw = self.f_title.measure(self.title)
        bw = self.f_badge.measure("✦ AI") + 14
        bx = x + tw + 10
        badge = ImageTk.PhotoImage(rounded_image(bw, 18, 9, (255, 255, 255, 60)))
        self._imgs = [badge]
        self.create_image(bx, ty, image=badge, anchor="w", tags="fg")
        self.create_text(bx + bw // 2, ty, text="✦ AI", fill="white", font=self.f_badge, tags="fg")
        # right side: New chat button, then the chip
        right = w - 14
        if self.on_new:
            label = "＋  New chat"
            nw = self.f_hint.measure(label) + 26
            img = ImageTk.PhotoImage(rounded_image(nw, 28, 14, (255, 255, 255, 235)))
            self._imgs.append(img)
            self.create_image(right, h // 2, image=img, anchor="e", tags=("fg", "new"))
            self.create_text(right - nw // 2, h // 2, text=label, fill=AI_A, font=(FONT, 9, "bold"), tags=("fg", "new"))
            self._new_box = (right - nw, h // 2 - 14, right, h // 2 + 14)
            right -= nw + 10
        hy = h // 2 + self.f_hint.metrics("linespace") // 2 + 3  # the hint line, under the title
        if self.chip:  # the order in view: a chip at the end of the hint line (clear of the title and badge)
            cw = self.f_hint.measure(self.chip) + 22
            ch = self.f_hint.metrics("linespace") + 4
            img = ImageTk.PhotoImage(rounded_image(cw, ch, ch // 2, (255, 255, 255, 55)))
            self._imgs.append(img)
            self.create_image(right, hy, image=img, anchor="e", tags="fg")
            self.create_text(right - cw // 2, hy, text=self.chip, fill="white", font=(FONT, 9, "bold"), tags="fg")
            right -= cw + 10
        hint = fit_text(self.hint, self.f_hint, max(right - x, 40), 1)
        self.create_text(x, hy, text=hint, anchor="w", fill="#F2F0FF", font=self.f_hint, tags="fg")

    def _in_new(self, e):
        b = self._new_box
        return b and b[0] <= e.x <= b[2] and b[1] <= e.y <= b[3]

    def _clicked(self, e):
        if self.on_new and self._in_new(e):
            self.on_new()

    def _motion(self, e):
        self.configure(cursor="hand2" if self._in_new(e) else "")

    def _tick(self):
        if not self.winfo_exists() or not self._frames:
            self._job = None
            return
        if not self.winfo_ismapped():  # another page is showing: just look again in a moment (no CPU)
            self._job = self.after(600, self._tick)
            return
        self._i = (self._i + 1) % len(self._frames)
        self.itemconfigure(self._bg, image=self._frames[self._i])
        self._job = self.after(90, self._tick)


class AIThinking(tk.Canvas):
    """'Working' row of the GOLD bot: three glowing dots pulsing in the AI colours, then the text."""

    def __init__(self, parent, bg=CARD, text="Thinking..."):
        self.font = tkfont.Font(family=FONT, size=9, slant="italic")
        h = self.font.metrics("linespace") + 10
        super().__init__(parent, height=h, width=420, background=bg, highlightthickness=0, borderwidth=0)
        self.base, self._i, self._dots = text, 0, []
        cols = [AI_A, mix(AI_A, AI_B, 0.5), AI_B]
        for k in range(3):
            self._dots.append(self.create_oval(0, 0, 0, 0, fill=cols[k], outline=""))
        self._text = self.create_text(48, h // 2, text=text, anchor="w", fill=MUTED, font=self.font)
        self.h = h
        self._tick()

    def set_text(self, text):
        self.base = text
        self.itemconfigure(self._text, text=text)
        self.configure(width=min(48 + self.font.measure(text) + 10, 900))

    def _tick(self):
        import math
        if not self.winfo_exists():
            return
        for k, dot in enumerate(self._dots):
            p = (math.sin(self._i / 3.0 - k * 0.9) + 1) / 2  # 0..1, a wave running through the dots
            r = 2.5 + 2.5 * p
            cx, cy = 10 + k * 13, self.h / 2 - 3 * p
            self.coords(dot, cx - r, cy - r, cx + r, cy + r)
        self._i += 1
        self.after(60, self._tick)


class Tooltip:
    """A small dark label under a widget while the mouse rests on it."""

    def __init__(self, widget, text=""):
        self.widget, self.text, self.win, self._job = widget, text, None, None
        widget.bind("<Enter>", self._soon, add="+")
        widget.bind("<Leave>", self.hide, add="+")
        widget.bind("<ButtonPress>", self.hide, add="+")

    def _soon(self, e=None):
        self._job = self.widget.after(450, self.show)

    def show(self):
        if not self.text or not self.widget.winfo_exists():
            return
        self.hide()
        self.win = tk.Toplevel(self.widget)
        self.win.overrideredirect(True)
        self.win.attributes("-topmost", True)
        tk.Label(self.win, text=self.text, bg="#1F2233" if not NEO else "#2A2D66", fg="white", font=(FONT, 9),
                 padx=10, pady=5).pack()
        self.win.update_idletasks()
        x = self.widget.winfo_rootx() + self.widget.winfo_width() // 2 - self.win.winfo_width() // 2
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 6
        self.win.geometry(f"+{max(x, 0)}+{y}")

    def hide(self, e=None):
        if self._job:
            self.widget.after_cancel(self._job)
            self._job = None
        if self.win is not None:
            self.win.destroy()
            self.win = None


class IconButton(tk.Canvas):
    """A round icon button for the top bar (updates, look, settings): soft circle, highlight on hover,
    a tooltip; set_highlight(True) makes it a glowing accent button with a dot (e.g. an update is ready)."""

    def __init__(self, parent, icon, command, tip="", bg=BG, size=38, font=None):
        size = int(size * parent.winfo_fpixels("1i") / 96)  # size is for 100% screen scaling
        super().__init__(parent, width=size, height=size, background=bg, highlightthickness=0, borderwidth=0,
                         cursor="hand2")
        self.icon, self.command, self.size = icon, command, size
        self.font = font or (ICONS, 12)
        self.hover = self.highlight = False
        self._imgs = {}
        self.tip = Tooltip(self, tip)
        self.bind("<Enter>", lambda e: self._set_hover(True), add="+")
        self.bind("<Leave>", lambda e: self._set_hover(False), add="+")
        self.bind("<Button-1>", lambda e: self.command())
        self._draw()

    def set_tip(self, text):
        self.tip.text = text

    def set_icon(self, icon, font=None):
        self.icon = icon
        if font:
            self.font = font
        self._draw()

    def set_highlight(self, on):
        self.highlight = on
        self._draw()

    def _set_hover(self, on):
        self.hover = on
        self._draw()

    def _circle(self, kind):
        s = self.size
        if kind not in self._imgs:
            if kind == "hot":
                im = gradient_rounded(s, s, s // 2, ORANGE, ACCENT2)
            elif kind == "hover":
                im = rounded_image(s, s, s // 2, HOVER if not NEO else "#262B66", ORANGE, width=1)
            else:
                im = rounded_image(s, s, s // 2, CARD, LINE if not NEO else "#2F347A", width=1)
            self._imgs[kind] = ImageTk.PhotoImage(im)
        return self._imgs[kind]

    def _draw(self):
        s = self.size
        self.delete("all")
        kind = "hot" if self.highlight else "hover" if self.hover else "normal"
        self.create_image(0, 0, image=self._circle(kind), anchor="nw")
        fg = "white" if self.highlight else (ORANGE_DARK if self.hover else INK)
        self.create_text(s // 2, s // 2, text=self.icon, fill=fg, font=self.font)
        if self.highlight:  # the "something new" dot
            d = max(s // 5, 6)
            self.create_oval(s - d - 1, 1, s - 1, d + 1, fill="#FF5C7C", outline=BG, width=2)


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
    """A rounded white card with a title and a line of text; orange outline on hover; click = command.
    ai=True: the GOLD bot's style - a sparkle and a glowing AI-gradient edge on hover."""

    def __init__(self, parent, title, text, command, bg=BG, width=300, ai=False):
        self.f1 = tkfont.Font(family=FONT, size=10, weight="bold")
        self.f2 = tkfont.Font(family=FONT, size=9)
        h = 28 + self.f1.metrics("linespace") + self.f2.metrics("linespace") + 4
        super().__init__(parent, width=width, height=h, background=bg, highlightthickness=0, borderwidth=0,
                         cursor="hand2")
        self.title, self.text, self._imgs, self.ai = title, text, {}, ai
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
            if self.ai:
                fill = AI_SOFT if hover else mix(CARD, AI_SOFT, 0.45)
                ring = (AI_A, AI_B) if hover else (mix(AI_A, CARD, 0.55), mix(AI_B, CARD, 0.55))
                self._imgs[key] = ImageTk.PhotoImage(gradient_ring(w, h, 16, *ring, width=2 if hover else 1,
                                                                   fill=_hex(fill) + (255,)))
            else:
                self._imgs[key] = ImageTk.PhotoImage(rounded_image(w, h, 16, CARD, BTN_HOVER_LINE if hover else LINE,
                                                                   width=2 if hover else 1))
        self.delete("all")
        self.create_image(0, 0, image=self._imgs[key], anchor="nw")
        if self.ai:
            self.create_text(18, 14, text="✦", anchor="nw", fill=AI_B if hover else AI_A, font=self.f1)
            self.create_text(38, 14, text=self.title, anchor="nw", fill=AI_A if hover else INK, font=self.f1)
            self.create_text(18, 18 + self.f1.metrics("linespace"), anchor="nw", fill=MUTED, font=self.f2,
                             text=fit_text(self.text, self.f2, w - 36, 1))
            return
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
        if isinstance(fill, tuple):  # (c0, c1): a gradient bubble (the AI chat)
            self._img = ImageTk.PhotoImage(gradient_rounded(w, h, min(18, h // 2), *fill))
        else:
            self._img = ImageTk.PhotoImage(rounded_image(w, h, min(18, h // 2), fill))
        self.create_image(0, 0, image=self._img, anchor="nw")
        self.create_text(16, 10, text=wrapped, anchor="nw", fill=fg, font=f)


class TableCopy:
    """Excel-like copying for a ttk.Treeview: click a cell to select it (orange outline), drag to select a
    block of cells, Ctrl+C to copy; right-click for cell / selection / row / column / whole table. Copied text
    is tab-separated, so it pastes into Excel as cells. Does not change the tree's own row selection."""

    def __init__(self, tree, on_copy=None, menu=True):
        self.tree, self.on_copy = tree, on_copy
        self.anchor = self.cur = None
        self.on_draw = None  # called with the block's (x0, y0, x1, y1), or None when nothing is shown
        self.edges = [tk.Frame(tree, background=ORANGE) for _ in range(4)]
        tree.bind("<Button-1>", self._press, add="+")
        tree.bind("<B1-Motion>", self._drag, add="+")
        for seq in ("<Control-c>", "<Control-C>"):
            tree.bind(seq, lambda e: (self.copy_selection(), "break")[1], add="+")
        for seq in ("<Configure>", "<MouseWheel>", "<KeyRelease>", "<Motion>"):
            tree.bind(seq, lambda e: tree.after_idle(self._draw), add="+")
        if menu:
            tree.bind("<Button-3>", self._menu, add="+")

    # --- geometry
    def _columns(self):
        dc = self.tree["displaycolumns"]
        return list(self.tree["columns"]) if not dc or dc[0] == "#all" else list(dc)

    def _rows(self):
        out = []

        def walk(parent):
            for i in self.tree.get_children(parent):
                out.append(i)
                if self.tree.item(i, "open"):
                    walk(i)
        walk("")
        return out

    def _cell_at(self, e):
        if self.tree.identify_region(e.x, e.y) not in ("cell", "tree"):
            return None
        row, col = self.tree.identify_row(e.y), self.tree.identify_column(e.x)
        cols = self._columns()
        try:
            n = int(col.lstrip("#"))
        except ValueError:
            return None
        if not row or n < 1 or n > len(cols):
            return None
        return row, cols[n - 1]

    def _press(self, e):
        cell = self._cell_at(e)
        self.anchor = self.cur = cell
        self.tree.focus_set()
        self._draw()

    def _drag(self, e):
        cell = self._cell_at(e)
        if cell and self.anchor:
            self.cur = cell
            self._draw()

    def block(self):
        """(rows, columns) of the selected block, top-left to bottom-right."""
        if not self.anchor or not self.cur:
            return [], []
        rows, cols = self._rows(), self._columns()
        try:
            r = sorted((rows.index(self.anchor[0]), rows.index(self.cur[0])))
            c = sorted((cols.index(self.anchor[1]), cols.index(self.cur[1])))
        except ValueError:
            return [], []
        return rows[r[0]:r[1] + 1], cols[c[0]:c[1] + 1]

    def _draw(self):
        for f in self.edges:
            f.place_forget()
        rows, cols = self.block()
        tl = self.tree.bbox(rows[0], cols[0]) if rows else None
        br = self.tree.bbox(rows[-1], cols[-1]) if rows else None
        if not tl or not br:
            if self.on_draw:
                self.on_draw(None)
            return
        x0, y0 = tl[0], tl[1]
        x1, y1 = br[0] + br[2], br[1] + br[3]
        t = 2
        for f, (x, y, w, h) in zip(self.edges, ((x0, y0, x1 - x0, t), (x0, y1 - t, x1 - x0, t),
                                                 (x0, y0, t, y1 - y0), (x1 - t, y0, t, y1 - y0))):
            f.place(x=x, y=y, width=max(w, 1), height=max(h, 1))
        if self.on_draw:
            self.on_draw((x0, y0, x1, y1))

    # --- copying
    def _text(self, rows, cols, header=False):
        lines = ["\t".join(self.tree.heading(c, "text") for c in cols)] if header else []
        lines += ["\t".join(str(self.tree.set(r, c)) for c in cols) for r in rows]
        return "\n".join(lines)

    def _put(self, text, what):
        self.tree.clipboard_clear()
        self.tree.clipboard_append(text)
        if self.on_copy:
            self.on_copy(what)

    def copy_selection(self):
        rows, cols = self.block()
        if rows:
            self._put(self._text(rows, cols), f"Copied {len(rows)} x {len(cols)} cell(s)"
                      if len(rows) * len(cols) > 1 else "Copied the cell")

    def copy_table(self):
        self._put(self._text(self._rows(), self._columns(), header=True), "Copied the whole table")

    def add_items(self, menu, row=None, col=None):
        """Copy commands for a right-click menu (row / col: the clicked cell)."""
        if row and col:
            menu.add_command(label="Copy cell", command=lambda: self._put(str(self.tree.set(row, col)), "Copied the cell"))
        rows, cols = self.block()
        if rows and len(rows) * len(cols) > 1:
            menu.add_command(label=f"Copy selection ({len(rows)} x {len(cols)})", command=self.copy_selection)
        if row:
            menu.add_command(label="Copy row", command=lambda: self._put(self._text([row], self._columns()), "Copied the row"))
        if col:
            menu.add_command(label="Copy column", command=lambda: self._put(
                "\n".join([self.tree.heading(col, "text")] + [str(self.tree.set(r, col)) for r in self._rows()]),
                "Copied the column"))
        menu.add_command(label="Copy whole table (paste into Excel)", command=self.copy_table)

    def _menu(self, e):
        cell = self._cell_at(e)
        if cell and not (self.anchor and cell[0] in self.block()[0] and cell[1] in self.block()[1]):
            self.anchor = self.cur = cell
            self._draw()
        m = tk.Menu(self.tree, tearoff=0)
        self.add_items(m, *(cell or (None, None)))
        m.tk_popup(e.x_root, e.y_root)


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
        if NEO and active:  # Futuristic: a glowing gradient pill, white text
            key = ("neo", w, h)
            if key not in self._imgs:
                self._imgs[key] = ImageTk.PhotoImage(gradient_rounded(w, h, h // 2, ORANGE, ACCENT2))
            c.create_image(0, 0, image=self._imgs[key], anchor="nw")
            c.create_text(26, h // 2, text=c.icon, fill="white", font=self.f_icon)
            c.create_text(50, h // 2, text=c.text, anchor="w", fill="white", font=self.f_bold)
            c.create_oval(w - 22, h // 2 - 3, w - 16, h // 2 + 3, fill="white", outline="")
            return
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
        if NEO and fill in ("ACCENT", "ACCENT_HOT"):  # Futuristic: gradient pills
            hot = fill == "ACCENT_HOT"
            return photo(gradient_rounded(w, h, r, mix(ORANGE, "#ffffff", 0.15) if hot else ORANGE,
                                          mix(ACCENT2, "#ffffff", 0.15) if hot else ACCENT2))
        if fill == "ACCENT":
            fill = ORANGE
        elif fill == "ACCENT_HOT":
            fill = ORANGE_DARK
        return photo(rounded_image(w, h, r, fill, outline, width=width))

    # Buttons: pills
    W, H = 40, 26  # compact pills
    R = H // 2 - 1
    b = dict(border=(R, R), padding=(R // 2 + 2, 1), sticky="nsew")  # padding: not the corner size
    style.element_create("RButton.border", "image", img(W, H, R, CARD, BTN_LINE),
                         ("disabled", img(W, H, R, DISABLED, DISABLED_LINE)),
                         ("pressed", img(W, H, R, BTN_PRESS, ORANGE)),
                         ("active", img(W, H, R, BTN_HOVER, BTN_HOVER_LINE)), **b)
    style.element_create("AButton.border", "image", img(W, H, R, "ACCENT"),
                         ("disabled", img(W, H, R, ACCENT_OFF)),
                         ("pressed", img(W, H, R, "ACCENT_HOT")), ("active", img(W, H, R, "ACCENT_HOT")), **b)
    style.element_create("SButton.border", "image", img(W, H, R, CARD),
                         ("pressed", img(W, H, R, HOVER)), ("active", img(W, H, R, HOVER)), **b)
    for name, element in (("TButton", "RButton.border"), ("Accent.TButton", "AButton.border"),
                          ("Side.TButton", "SButton.border")):
        style.layout(name, [(element, {"sticky": "nsew", "children": [
            ("Button.padding", {"sticky": "nsew", "children": [("Button.label", {"sticky": "nsew"})]})]})])
    # the corners outside the pill show the style's background: keep it the tile's white in every state
    corners = [("disabled", CARD), ("pressed", CARD), ("active", CARD), ("!disabled", CARD)]
    style.configure("TButton", padding=(12, 2), background=CARD, foreground=INK, font=(FONT, 9), width=-4)
    style.map("TButton", background=corners, foreground=[("disabled", DISABLED_INK)])
    style.configure("Accent.TButton", padding=(14, 2), foreground="white", font=(FONT, 9, "bold"),
                    background=CARD)
    style.map("Accent.TButton", foreground=[("disabled", "white")], background=corners)
    style.configure("Side.TButton", padding=(12, 4), foreground=INK, anchor="w", font=(FONT, 10), background=CARD)
    style.map("Side.TButton", foreground=[("active", ORANGE_DARK)], background=corners)

    # Fields: rounded
    FR = 9
    f = dict(border=(FR, FR), padding=(6, 1), sticky="nsew")
    field = img(W, H, FR, FIELD, FIELD_LINE)
    focus = img(W, H, FR, CARD, ORANGE, width=2)
    off = img(W, H, FR, DISABLED, DISABLED_LINE)
    style.element_create("REntry.field", "image", field, ("disabled", off), ("focus", focus), **f)
    style.layout("TEntry", [("REntry.field", {"sticky": "nsew", "children": [
        ("Entry.padding", {"sticky": "nsew", "children": [("Entry.textarea", {"sticky": "nsew"})]})]})])
    style.configure("TEntry", padding=(10, 3), fieldbackground=FIELD)
    style.element_create("RCombo.field", "image", field, ("disabled", off), ("focus", focus), **f)
    style.layout("TCombobox", [("RCombo.field", {"sticky": "nsew", "children": [
        ("Combobox.downarrow", {"side": "right", "sticky": "ns"}),
        ("Combobox.padding", {"expand": "1", "sticky": "nsew", "children": [
            ("Combobox.textarea", {"sticky": "nsew"})]})]})])
    style.configure("TCombobox", padding=(10, 2), arrowsize=12, background=FIELD, arrowcolor=MUTED,
                    fieldbackground=FIELD, bordercolor=FIELD, lightcolor=FIELD, darkcolor=FIELD)
    style.map("TCombobox", background=[("active", FIELD), ("pressed", FIELD)],
              fieldbackground=[("readonly", FIELD)])

    # Segmented selector (radio buttons as pills)
    style.element_create("RSeg.border", "image", img(W, H, R, CARD, BTN_LINE),
                         ("selected", img(W, H, R, "ACCENT")), ("active", img(W, H, R, BTN_HOVER, BTN_HOVER_LINE)), **b)
    style.layout("Seg.TRadiobutton", [("RSeg.border", {"sticky": "nsew", "children": [
        ("Radiobutton.padding", {"sticky": "nsew", "children": [("Radiobutton.label", {"sticky": "nsew"})]})]})])
    style.configure("Seg.TRadiobutton", padding=(12, 2), background=CARD, font=(FONT, 9, "bold"))
    style.map("Seg.TRadiobutton", foreground=[("selected", "white")], background=[("active", CARD)])
    # Smaller pills for toolbars (their own, shorter images)
    w2, h2 = 36, 22
    r2 = h2 // 2 - 1
    b2 = dict(border=(r2, r2), padding=(r2 // 2 + 2, 0), sticky="nsew")
    style.element_create("RSegS.border", "image", img(w2, h2, r2, CARD, BTN_LINE),
                         ("selected", img(w2, h2, r2, "ACCENT")), ("active", img(w2, h2, r2, BTN_HOVER, BTN_HOVER_LINE)),
                         **b2)
    style.layout("SegSm.TRadiobutton", [("RSegS.border", {"sticky": "nsew", "children": [
        ("Radiobutton.padding", {"sticky": "nsew", "children": [("Radiobutton.label", {"sticky": "nsew"})]})]})])
    style.configure("SegSm.TRadiobutton", padding=(10, 1), background=CARD, font=(FONT, 9, "bold"))
    style.map("SegSm.TRadiobutton", foreground=[("selected", "white")], background=[("active", CARD)])
    style.element_create("RButtonS.border", "image", img(w2, h2, r2, CARD, BTN_LINE),
                         ("disabled", img(w2, h2, r2, DISABLED, DISABLED_LINE)),
                         ("pressed", img(w2, h2, r2, BTN_PRESS, ORANGE)),
                         ("active", img(w2, h2, r2, BTN_HOVER, BTN_HOVER_LINE)), **b2)
    style.layout("Small.TButton", [("RButtonS.border", {"sticky": "nsew", "children": [
        ("Button.padding", {"sticky": "nsew", "children": [("Button.label", {"sticky": "nsew"})]})]})])
    style.configure("Small.TButton", padding=(10, 1), background=CARD, foreground=INK, font=(FONT, 9), width=-4)
    style.map("Small.TButton", background=corners, foreground=[("disabled", DISABLED_INK)])

    # Checkboxes: rounded squares with a tick
    def check(on):
        S, s = 30, 3
        im = Image.new("RGBA", (S * s, S * s), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        box = (2 * s, 6 * s, 20 * s, 24 * s)
        if on and NEO:
            g = gradient_rounded(box[2] - box[0], box[3] - box[1], 6 * s, ORANGE, ACCENT2)
            im.alpha_composite(g, (box[0], box[1]))
            d.line([(6 * s, 15 * s), (10 * s, 19 * s), (17 * s, 11 * s)], fill="white", width=int(2.4 * s),
                   joint="curve")
        elif on:
            d.rounded_rectangle(box, radius=6 * s, fill=ORANGE)
            d.line([(6 * s, 15 * s), (10 * s, 19 * s), (17 * s, 11 * s)], fill="white", width=int(2.4 * s),
                   joint="curve")
        else:
            d.rounded_rectangle(box, radius=6 * s, fill=CARD, outline=CHECK_LINE, width=int(1.4 * s))
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
    style.element_create("RThumbV", "image", thumb(10, 40, THUMB), ("active", thumb(10, 40, THUMB_HOVER)),
                         ("pressed", thumb(10, 40, THUMB_PRESS)), border=(4, 8), sticky="nsew")
    style.element_create("RThumbH", "image", thumb(40, 10, THUMB), ("active", thumb(40, 10, THUMB_HOVER)),
                         ("pressed", thumb(40, 10, THUMB_PRESS)), border=(8, 4), sticky="nsew")
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
