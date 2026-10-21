"""Draw the GOLD Express logo: assets/logo.png (512 px), assets/logo_<size>.png and gold_express.ico.

A rounded tile in a warm orange gradient with a white "G" ring whose crossbar ends in an arrow
(orders moving forward) and a small spark (Express). Run: python tools/make_logo.py
"""
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
S = 2048  # drawn large, scaled down smoothly


def gradient(size, stops):
    """Diagonal gradient (top-left -> bottom-right) through the colour stops."""
    w, h = size
    base = Image.new("RGB", (256, 1))
    px = base.load()
    for x in range(256):
        t = x / 255
        for (t0, c0), (t1, c1) in zip(stops, stops[1:]):
            if t0 <= t <= t1:
                k = (t - t0) / (t1 - t0) if t1 > t0 else 0
                px[x, 0] = tuple(round(a + (b - a) * k) for a, b in zip(c0, c1))
                break
    diag = int(math.hypot(w, h)) + 2
    img = base.resize((diag, diag)).rotate(-45, resample=Image.BICUBIC)
    left = (diag - w) // 2
    return img.crop((left, left, left + w, left + h))


def logo():
    tile = gradient((S, S), [(0.0, (255, 184, 77)), (0.5, (255, 121, 0)), (1.0, (226, 74, 0))])
    mask = Image.new("L", (S, S), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, S - 1, S - 1), radius=int(S * 0.24), fill=255)
    out = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    out.paste(tile, (0, 0), mask)

    # soft highlight in the top-left corner
    glow = Image.new("L", (S, S), 0)
    ImageDraw.Draw(glow).ellipse((-S * 0.35, -S * 0.45, S * 0.75, S * 0.45), fill=70)
    glow = glow.filter(ImageFilter.GaussianBlur(S * 0.08))
    white = Image.new("RGBA", (S, S), (255, 255, 255, 255))
    out = Image.composite(white, out, Image.eval(glow, lambda v: v)).copy()
    out.putalpha(mask)

    d = ImageDraw.Draw(out)
    cx, cy, r, w = S * 0.47, S * 0.52, S * 0.27, S * 0.105
    box = (cx - r, cy - r, cx + r, cy + r)
    # "G" ring: open on the right between -40 and +30 degrees (PIL angles: 0 = 3 o'clock, clockwise)
    d.arc(box, start=30, end=320, fill="white", width=int(w))
    # rounded ends of the ring
    for ang in (30, 320):
        a = math.radians(ang)
        ex, ey = cx + (r - w / 2) * math.cos(a), cy + (r - w / 2) * math.sin(a)
        d.ellipse((ex - w / 2, ey - w / 2, ex + w / 2, ey + w / 2), fill="white")
    # crossbar going right, ending in an arrow head (forward / express)
    y = cy + w * 0.05
    x0, x1 = cx, cx + r + S * 0.13
    d.rounded_rectangle((x0, y - w / 2, x1 - S * 0.06, y + w / 2), radius=int(w / 2), fill="white")
    ah = S * 0.11
    d.polygon([(x1 - S * 0.09, y - ah), (x1 + S * 0.035, y), (x1 - S * 0.09, y + ah)], fill="white")
    # spark (four-point star) top right
    sx, sy, sr = S * 0.775, S * 0.235, S * 0.075
    d.polygon([(sx, sy - sr), (sx + sr * 0.28, sy - sr * 0.28), (sx + sr, sy), (sx + sr * 0.28, sy + sr * 0.28),
               (sx, sy + sr), (sx - sr * 0.28, sy + sr * 0.28), (sx - sr, sy), (sx - sr * 0.28, sy - sr * 0.28)],
              fill="white")
    return out


def main():
    ASSETS.mkdir(exist_ok=True)
    big = logo()
    big.resize((512, 512), Image.LANCZOS).save(ASSETS / "logo.png")
    for size in (28, 36, 48, 64, 96):
        big.resize((size, size), Image.LANCZOS).save(ASSETS / f"logo_{size}.png")
    big.resize((256, 256), Image.LANCZOS).save(ROOT / "gold_express.ico",
                                               sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64),
                                                      (128, 128), (256, 256)])
    print("logo written to", ASSETS)


if __name__ == "__main__":
    main()
