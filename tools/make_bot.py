"""Cut the Friendly GOLD bot out of its picture: assets/bot.png (transparent, bot only) and small avatars
assets/bot_<size>.png. The app animates it (float + shadow). Run: python tools/make_bot.py <picture>"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"


def cut_out(path):
    im = Image.open(path).convert("RGB")
    w, h = im.size
    # The background is white: flood it from the corners (inner white parts, e.g. the tooth, stay).
    marked = im.copy()
    for corner in ((0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)):
        ImageDraw.floodfill(marked, corner, (255, 0, 255), thresh=18)
    bg = Image.eval(marked.convert("RGB"), lambda v: v).load()
    mask = Image.new("L", (w, h), 255)
    mpx = mask.load()
    for y in range(h):
        for x in range(w):
            if bg[x, y] == (255, 0, 255):
                mpx[x, y] = 0
    # drop the floor shadow (a light-blue ellipse below the bot): keep only the largest blob's rows
    rows = [sum(1 for x in range(0, w, 4) if mpx[x, y]) for y in range(h)]
    gap_start = None
    top = next(y for y in range(h) if rows[y])
    for y in range(top, h):
        if rows[y] == 0:
            gap_start = y
            break
    if gap_start:
        ImageDraw.Draw(mask).rectangle((0, gap_start, w, h), fill=0)
    mask = mask.filter(ImageFilter.GaussianBlur(0.8))  # soft edge
    out = im.convert("RGBA")
    out.putalpha(mask)
    return out.crop(out.getbbox())


def main():
    src = sys.argv[1]
    ASSETS.mkdir(exist_ok=True)
    bot = cut_out(src)
    scale = 420 / bot.height
    bot.resize((round(bot.width * scale), 420), Image.LANCZOS).save(ASSETS / "bot.png")
    for size in (24, 28, 36, 48, 64):
        canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        small = bot.copy()
        small.thumbnail((size, size), Image.LANCZOS)
        canvas.alpha_composite(small, ((size - small.width) // 2, (size - small.height) // 2))
        canvas.save(ASSETS / f"bot_{size}.png")
    print("bot written:", bot.size, "->", ASSETS / "bot.png")


if __name__ == "__main__":
    main()
