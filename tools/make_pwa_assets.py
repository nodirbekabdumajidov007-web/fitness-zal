"""One-off generator for the PWA / Google Play image assets. Run locally (needs Pillow, which is NOT a runtime dependency):

    .venv/Scripts/python.exe tools/make_pwa_assets.py

It reads gym/static/img/logo.png and writes the PNGs under gym/static/img/ (committed to git) and the store graphics under docs/play/.
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
IMG = ROOT / "gym" / "static" / "img"
PLAY = ROOT / "docs" / "play"
RED = (214, 48, 31, 255)
DARK = (16, 19, 24, 255)
SIZES = (48, 72, 96, 128, 144, 152, 192, 256, 384, 512)

logo = Image.open(IMG / "logo.png").convert("RGBA")


def placed(size, height_ratio, bg=RED, mark=logo):
    """A square canvas with the shield centred; height_ratio is the shield height relative to the canvas."""
    canvas = Image.new("RGBA", (size, size), bg)
    h = round(size * height_ratio)
    w = round(mark.width * h / mark.height)
    m = mark.resize((w, h), Image.LANCZOS)
    canvas.alpha_composite(m, ((size - w) // 2, (size - h) // 2))
    return canvas


def save(im, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    im.save(path, optimize=True)
    print("wrote", path.relative_to(ROOT), im.size)


for s in SIZES:  # "any": full-bleed brand colour, shield fills most of it
    save(placed(s, 0.76), IMG / f"icon-{s}.png")
for s in (192, 512):  # maskable: everything important inside the central 80% circle (shield height <= 62%)
    save(placed(s, 0.60), IMG / f"icon-maskable-{s}.png")

# monochrome (Android 13 themed icons): the shield silhouette only, transparent around it
alpha = logo.getchannel("A")
sil = Image.new("RGBA", logo.size, (0, 0, 0, 255))
sil.putalpha(alpha)
save(placed(512, 0.64, bg=(0, 0, 0, 0), mark=sil), IMG / "icon-monochrome-512.png")
# notification badge: white silhouette on transparent, small
white = Image.new("RGBA", logo.size, (255, 255, 255, 255))
white.putalpha(alpha)
save(placed(96, 0.8, bg=(0, 0, 0, 0), mark=white), IMG / "badge-96.png")

# iOS home-screen icon (opaque, iOS rounds the corners itself) and favicons
save(placed(180, 0.76), IMG / "apple-touch-icon.png")
for s in (32, 16):
    save(placed(s, 0.9, bg=(0, 0, 0, 0)), IMG / f"favicon-{s}.png")
placed(48, 0.88, bg=(0, 0, 0, 0)).save(IMG / "favicon.ico", sizes=[(16, 16), (32, 32), (48, 48)])
print("wrote favicon.ico")


# shortcut icons (96px): white line glyphs on the brand red
def glyph(name):
    im = Image.new("RGBA", (96, 96), RED)
    d = ImageDraw.Draw(im)
    w = 6
    if name == "dash":  # house
        d.line([(20, 46), (48, 22), (76, 46)], fill="white", width=w, joint="curve")
        d.line([(28, 42), (28, 74), (68, 74), (68, 42)], fill="white", width=w, joint="curve")
    elif name == "card":  # QR finder squares
        for x, y in ((22, 22), (58, 22), (22, 58)):
            d.rectangle([x, y, x + 16, y + 16], outline="white", width=w - 2)
        d.rectangle([60, 60, 74, 74], fill="white")
    elif name == "classes":  # calendar
        d.rounded_rectangle([20, 26, 76, 76], 8, outline="white", width=w - 1)
        d.line([(20, 42), (76, 42)], fill="white", width=w - 1)
        d.line([(34, 18), (34, 32)], fill="white", width=w - 1)
        d.line([(62, 18), (62, 32)], fill="white", width=w - 1)
    elif name == "food":  # flame
        d.polygon([(48, 18), (66, 44), (70, 62), (60, 76), (36, 76), (26, 62), (32, 44), (42, 52)], outline="white", width=w - 1)
        d.ellipse([40, 58, 56, 74], fill="white")
    return im


for n in ("dash", "card", "classes", "food"):
    save(glyph(n), IMG / f"shortcut-{n}.png")

# Google Play: 512 icon (opaque) and 1024x500 feature graphic
save(placed(512, 0.76), PLAY / "icon-512.png")
fg = Image.new("RGBA", (1024, 500), DARK)
d = ImageDraw.Draw(fg)
d.polygon([(560, 0), (1024, 0), (1024, 500), (430, 500)], fill=RED)
h = 400
m = logo.resize((round(logo.width * h / logo.height), h), Image.LANCZOS)
fg.alpha_composite(m, (680, 50))
big = ImageFont.truetype("C:/Windows/Fonts/impact.ttf", 96)
small = ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf", 30)
d.text((60, 150), "FITNES.ZAL", font=big, fill=(238, 240, 243, 255))
d.text((64, 270), "Mashg'ulotlar, a'zo kartasi", font=small, fill=(154, 163, 176, 255))
d.text((64, 314), "va do'kon bir ilovada", font=small, fill=(154, 163, 176, 255))
d.rectangle([64, 130, 184, 138], fill=RED)
save(fg.convert("RGB"), PLAY / "feature-graphic-1024x500.png")
