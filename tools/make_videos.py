"""Promo videos for Fitnes Zal: an Instagram reel (1080x1920) and a portfolio demo (1920x1080), with original music,
sound effects and a voice-over.

    .venv\\Scripts\\python.exe tools\\make_videos.py all          # everything: temp DB copy + seed + temp server + capture + render
    .venv\\Scripts\\python.exe tools\\make_videos.py render <work> # re-render from frames captured earlier

Nothing here touches db.sqlite3 or the dev server: a COPY of the database is seeded with fake demo data and served from a
snapshot of the last commit (git archive HEAD) on 127.0.0.1:8770; everything temporary lives in %TEMP%\\fzvideo and is removed.
Needs Pillow, websockets and imageio-ffmpeg in the venv, plus Chrome or Edge."""
import json
import math
import os
import re
import secrets
import shutil
import subprocess
import sys
import time
import urllib.request
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

TOOLS = Path(__file__).resolve().parent
ROOT = TOOLS.parent
sys.path.insert(0, str(TOOLS))
import video_audio as va  # noqa: E402

OUT = ROOT / "docs" / "video"
FPS = 30
BAR = 60  # frames per bar at 120 BPM
DARK, RED, WHITE = (16, 19, 24), (240, 80, 61), (255, 255, 255)
SITE = "fitness-zal-ji76.onrender.com"
FONT = r"C:\Windows\Fonts\bahnschrift.ttf"
EMOJI_FONT = r"C:\Windows\Fonts\seguiemj.ttf"
STATIC = ROOT / "gym" / "static" / "img"


# ======================================================================= helpers
def ffmpeg_exe():
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def ease_out(t):
    return 1 - (1 - clamp(t)) ** 3


def ease_io(t):
    t = clamp(t)
    return 4 * t ** 3 if t < 0.5 else 1 - (-2 * t + 2) ** 3 / 2


def back(t):
    t = clamp(t)
    c = 1.9
    return 1 + (c + 1) * (t - 1) ** 3 + c * (t - 1) ** 2


@lru_cache(maxsize=64)
def font(size, style="Bold Condensed"):
    f = ImageFont.truetype(FONT, size)
    f.set_variation_by_name(style)
    return f


@lru_cache(maxsize=16)
def efont(size):
    return ImageFont.truetype(EMOJI_FONT, size)


def is_emoji(ch):
    o = ord(ch)
    return o >= 0x1F000 or ch in "✅⚡✨❤☀⭐✔✈⏱⌚"


@lru_cache(maxsize=512)
def word_img(word, size, color, style="Bold Condensed"):
    """One word (may contain emoji) as a tight RGBA image."""
    f, ef = font(size, style), efont(int(size * 0.82))
    parts, cur = [], ""
    for ch in word:
        if ch == "\ufe0f":
            continue
        if is_emoji(ch):
            if cur:
                parts.append(("t", cur))
                cur = ""
            parts.append(("e", ch))
        else:
            cur += ch
    if cur:
        parts.append(("t", cur))
    asc, desc = f.getmetrics()
    h = asc + desc
    w = 0
    for kind, s in parts:
        w += int(f.getlength(s)) if kind == "t" else int(size * 0.98)
    img = Image.new("RGBA", (max(1, w + 4), h + 8), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    x = 2
    for kind, s in parts:
        if kind == "t":
            d.text((x, 4), s, font=f, fill=color)
            x += int(f.getlength(s))
        else:
            d.text((x + 2, 4 + int(size * 0.12)), s, font=ef, embedded_color=True)
            x += int(size * 0.98)
    return img


def text_img(text, size, color=WHITE, style="Bold Condensed"):
    """Plain (non-animated) single line."""
    ws = [word_img(w, size, color, style) for w in text.split(" ")]
    sp = int(size * 0.26)
    W = sum(w.width for w in ws) + sp * (len(ws) - 1)
    H = max(w.height for w in ws)
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    x = 0
    for w in ws:
        img.alpha_composite(w, (x, 0))
        x += w.width + sp
    return img


def shadowed(img, radius=10, alpha=170, offset=(0, 6)):
    a = img.getchannel("A").point(lambda v: v * alpha // 255)
    sh = Image.new("RGBA", (img.width + radius * 4, img.height + radius * 4), (0, 0, 0, 0))
    blk = Image.new("RGBA", img.size, (0, 0, 0, 255))
    blk.putalpha(a)
    sh.alpha_composite(blk, (radius * 2 + offset[0], radius * 2 + offset[1]))
    sh = sh.filter(ImageFilter.GaussianBlur(radius))
    sh.alpha_composite(img, (radius * 2, radius * 2))
    return sh, radius * 2


def rounded_mask(size, r):
    m = Image.new("L", size, 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, size[0] - 1, size[1] - 1], radius=r, fill=255)
    return m


def fade_alpha(img, a):
    if a >= 0.999:
        return img
    im = img.copy()
    im.putalpha(im.getchannel("A").point(lambda v: int(v * a)))
    return im


def pill(text, size, fg=WHITE, bg=(0, 0, 0, 170), pad=(22, 10), style="SemiBold", dot=None):
    t = text_img(text, size, fg, style)
    dw = int(size * 0.9) if dot else 0
    W, H = t.width + pad[0] * 2 + dw, t.height + pad[1] * 2
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, W - 1, H - 1], radius=H // 2, fill=bg)
    if dot:
        r = size // 4
        cy = H // 2
        d.ellipse([pad[0], cy - r, pad[0] + 2 * r, cy + r], fill=dot)
    img.alpha_composite(t, (pad[0] + dw, pad[1]))
    return img


def zoom(img, s, cx, cy):
    """Camera zoom by s around (cx, cy) keeping the output size."""
    if abs(s - 1) < 0.0005:
        return img
    W, H = img.size
    # output (x, y) samples input ((x - cx) / s + cx, ...)
    a, e = 1 / s, 1 / s
    c, f = cx - cx / s, cy - cy / s
    return img.transform((W, H), Image.AFFINE, (a, 0, c, 0, e, f), resample=Image.BILINEAR)


class Kinetic:
    """A caption whose words pop in one after another (scale with overshoot + fade); *word* = highlighted in brand red."""

    def __init__(self, text, size, color=WHITE, hl=RED, style="Bold Condensed", max_w=980, stagger=4, upper=False):
        self.size, self.stagger = size, stagger
        words = text.split(" ")
        self.items = []  # (img, hl)
        for w in words:
            h = w.startswith("*") and w.endswith("*") and len(w) > 2
            w = w.strip("*")
            if upper:
                w = w.upper()
            self.items.append((word_img(w, size, WHITE if h else color, style), h))
        sp = int(size * 0.26)
        self.lines, line, lw = [], [], 0
        for i, (im, h) in enumerate(self.items):
            if line and lw + sp + im.width > max_w:
                self.lines.append((line, lw))
                line, lw = [], 0
            lw += (sp if line else 0) + im.width
            line.append(i)
        if line:
            self.lines.append((line, lw))
        self.sp, self.hl = sp, hl
        self.lh = int(size * 1.08)
        self.h = self.lh * len(self.lines)

    def draw(self, canvas, cx, y, t, out_t=None, align="center", x0=None):
        """t: frames since start; out_t: frames since exit started (or None)."""
        k = 0
        for li, (idx, lw) in enumerate(self.lines):
            x = (cx - lw // 2) if align == "center" else x0
            for i in idx:
                im, h = self.items[i]
                p = (t - k * self.stagger) / 8
                k += 1
                if p <= 0:
                    x += im.width + self.sp
                    continue
                a = clamp(p * 1.6)
                s = 0.55 + 0.45 * back(p)
                dy = int((1 - ease_out(p)) * 26)
                if out_t is not None:
                    q = clamp(out_t / 7)
                    a *= 1 - q
                    dy -= int(q * 30)
                if a <= 0.01:
                    x += im.width + self.sp
                    continue
                yy = y + li * self.lh + dy
                if h:  # red marker sweep behind the word
                    sw = clamp((t - k * self.stagger) / 7)
                    pad = int(self.size * 0.12)
                    bw = int((im.width + 2 * pad) * ease_out(sw))
                    if bw > 4:
                        box = Image.new("RGBA", (bw, im.height - 2), (*self.hl, int(235 * a)))
                        canvas.alpha_composite(box, (x - pad, yy + 2))
                w2 = max(1, int(im.width * s))
                h2 = max(1, int(im.height * s))
                ims = im.resize((w2, h2), Image.BILINEAR) if abs(s - 1) > 0.01 else im
                ims = fade_alpha(ims, a)
                canvas.alpha_composite(ims, (int(x + (im.width - w2) / 2), int(yy + (im.height - h2) / 2)))
                x += im.width + self.sp
        return self.h


@lru_cache(maxsize=24)
def load_frame(path, size):
    im = Image.open(path).convert("RGB")
    return im.resize(size, Image.LANCZOS) if im.size != size else im


def glow_blob(r, color, alpha=150):
    im = Image.new("RGBA", (r * 4, r * 4), (0, 0, 0, 0))
    ImageDraw.Draw(im).ellipse([r, r, 3 * r, 3 * r], fill=(*color, alpha))
    return im.filter(ImageFilter.GaussianBlur(r * 0.55))


def logo_img(h):
    lg = Image.open(STATIC / "logo.png").convert("RGBA")
    w = int(lg.width * h / lg.height)
    return lg.resize((w, h), Image.LANCZOS)


def light_sweep(img, p):
    """A diagonal light band crossing the image (p 0..1), masked by its alpha."""
    W, H = img.size
    band = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(band)
    x = int(-W * 0.6 + p * W * 2.2)
    d.polygon([(x, 0), (x + W * 0.22, 0), (x + W * 0.22 - H * 0.5, H), (x - H * 0.5, H)], fill=255)
    band = band.filter(ImageFilter.GaussianBlur(W * 0.04))
    m = ImageChops.multiply(band, img.getchannel("A")).point(lambda v: int(v * 0.75))
    white = Image.new("RGBA", (W, H), (255, 255, 255, 0))
    white.putalpha(m)
    out = img.copy()
    out.alpha_composite(white)
    return out


def counter_text(v, fmt):
    return fmt.format(v=v)


# ======================================================================= scene timing
class Clip:
    """Maps scene frames onto captured frames: plays at speed >= 1 to fit, holds the last frame if shorter."""

    def __init__(self, work, cap, scene, n, start=0, speed=None):
        sc = cap[scene]
        self.work = work
        self.frames = sc["frames"][start:]
        self.n = n
        self.speed = speed or max(1.0, len(self.frames) / n)
        self.taps = [dict(t, f=(t["f"] - start) / self.speed) for t in sc["taps"] if t["f"] >= start]
        self.marks = {k: (v - start) / self.speed for k, v in sc["marks"].items()}
        self.meta = sc

    def path(self, i):
        j = min(len(self.frames) - 1, int(i * self.speed))
        return os.path.join(self.work, self.frames[max(0, j)])


def draw_tap(canvas, x, y, age, scale=1.0, color=(255, 255, 255)):
    """Touch ripple: a dot plus an expanding ring, age in frames."""
    if age < 0 or age > 16:
        return
    p = age / 16
    r = int((18 + 46 * ease_out(p)) * scale)
    a = int(200 * (1 - p))
    ov = Image.new("RGBA", (r * 2 + 8, r * 2 + 8), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    d.ellipse([4, 4, 4 + 2 * r, 4 + 2 * r], outline=(*color, a), width=max(2, int(5 * scale)))
    if age < 8:
        rr = int(16 * scale)
        c = r + 4
        d.ellipse([c - rr, c - rr, c + rr, c + rr], fill=(*color, int(150 * (1 - age / 8))))
    canvas.alpha_composite(ov, (int(x - r - 4), int(y - r - 4)))


# ======================================================================= the reel
REEL_W, REEL_H = 1080, 1920
SCR_W, SCR_H, STATUS_H = 600, 1298, 42
PH_X, PH_Y = (REEL_W - SCR_W) // 2, 520  # screen top-left (status bar starts here)

REEL = [  # id, bars, capture scene, title, subtitle, english voice line, music section per bar
    dict(id="hook", bars=2, title="FITNES ZAL", sub="zalingiz endi *telefoningizda* 📱",
         en="Fitnes Zal. Your gym is now in your pocket.", music=["intro", "build"]),
    dict(id="home", bars=2, cap="m_home", title="Zamonaviy *sayt*", sub="har bir a'zo uchun shaxsiy kabinet 💪",
         en="A modern gym website, with a personal space for every member.", music=["drop"] * 2),
    dict(id="plans", bars=2, cap="m_plans", title="Abonement — *onlayn*", sub="Payme · Click · Uzum orqali to'lov",
         en="Choose a plan and pay online in seconds.", music=["drop"] * 2),
    dict(id="card", bars=2, cap="m_card", title="QR *a'zo kartasi*", sub="internetsiz ham ishlaydi ✅",
         en="Your member card is a QR code, and it even works offline.", music=["drop"] * 2),
    dict(id="cal", bars=2, cap="m_cal", title="Kaloriya *hisobi*", sub="«osh» deb yozing — tayyor 🍛",
         en="Count calories: just type osh.", music=["drop"] * 2),
    dict(id="prog", bars=2, cap="m_prog", title="Natijalaringiz *grafikda*", sub="2 oyda –5,8 kg 🔥",
         en="See your progress on clear charts.", music=["break", "build"]),
    dict(id="ai", bars=3, cap="m_ai", title="Murabbiy *yordamchi*", sub="savolingizga 24/7 javob 🤖",
         en="Ask the coach assistant anything, day or night.", music=["drop"] * 3),
    dict(id="support", bars=2, cap="m_support", title="Savol *bormi?*", sub="yordam — bir bosishda 💬",
         en="Got a question? Help is one tap away.", music=["drop"] * 2),
    dict(id="install", bars=2, cap="m_install", title="Ilova kabi *o'rnating*", sub="bosh ekranda, bir bosishda 📲",
         en="Install it like an app, right on your home screen.", music=["drop", "outro"]),
    dict(id="end", bars=3, title="Hoziroq *ro'yxatdan* o'ting", sub=SITE,
         en="Fitnes Zal. Sign up today!", music=["outro", "outro", "end"]),
]


class ReelRenderer:
    def __init__(self, work, cap):
        self.work, self.cap = work, cap
        bg = Image.new("RGB", (REEL_W, REEL_H), DARK)
        g = Image.open(STATIC / "gym-bg.webp").convert("RGB")
        s = max(REEL_W / g.width, REEL_H / g.height) * 1.15
        g = g.resize((int(g.width * s), int(g.height * s)), Image.LANCZOS).filter(ImageFilter.GaussianBlur(14))
        self.bgphoto = g
        self.bg = bg
        self.blob_r = glow_blob(260, RED, 120)
        self.blob_b = glow_blob(220, (60, 90, 200), 70)
        # phone body
        bw = 16
        W, H = SCR_W + 2 * bw, SCR_H + STATUS_H + 2 * bw
        body = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(body)
        d.rounded_rectangle([0, 0, W - 1, H - 1], radius=84, fill=(8, 9, 12, 255), outline=(58, 62, 72, 255), width=3)
        hole = rounded_mask((SCR_W, SCR_H + STATUS_H), 68)
        body.paste((0, 0, 0, 0), (bw, bw), hole)
        self.body, self.bw = body, bw
        sh = Image.new("RGBA", (W + 160, H + 160), (0, 0, 0, 0))
        ImageDraw.Draw(sh).rounded_rectangle([80, 100, 80 + W, 100 + H], radius=84, fill=(0, 0, 0, 200))
        self.shadow = sh.filter(ImageFilter.GaussianBlur(36))
        self.screen_mask = hole
        # status bar
        sb = Image.new("RGB", (SCR_W, STATUS_H), DARK)
        d = ImageDraw.Draw(sb)
        d.text((44, 9), "9:41", font=font(24, "SemiBold"), fill=WHITE)
        d.rounded_rectangle([SCR_W // 2 - 62, 8, SCR_W // 2 + 62, 34], radius=13, fill=(0, 0, 0))
        x = SCR_W - 120
        for i, hgt in enumerate((7, 11, 15, 19)):
            d.rectangle([x + i * 7, 30 - hgt, x + i * 7 + 4, 30], fill=WHITE)
        d.rounded_rectangle([SCR_W - 76, 13, SCR_W - 38, 29], radius=4, outline=WHITE, width=2)
        d.rectangle([SCR_W - 73, 16, SCR_W - 48, 26], fill=WHITE)
        self.statusbar = sb
        self.logo = logo_img(300)
        self.icon = Image.open(STATIC / "icon-512.png").convert("RGBA")

    # --- pieces
    def background(self, f, total):
        im = self.bg.copy()
        t = f / total
        g = self.bgphoto
        ox = int((g.width - REEL_W) * (0.3 + 0.4 * t))
        oy = int((g.height - REEL_H) * 0.5)
        ph = g.crop((ox, oy, ox + REEL_W, oy + REEL_H))
        im = Image.blend(im, ph, 0.22)
        im = im.convert("RGBA")
        bx = int(540 + 380 * math.sin(f / 70))
        by = int(700 + 300 * math.cos(f / 95))
        im.alpha_composite(self.blob_r, (bx - self.blob_r.width // 2, by - self.blob_r.height // 2))
        bx2 = int(540 - 360 * math.sin(f / 85 + 1))
        by2 = int(1500 + 200 * math.sin(f / 60))
        im.alpha_composite(self.blob_b, (bx2 - self.blob_b.width // 2, by2 - self.blob_b.height // 2))
        return im

    def screen(self, clip, i):
        img = load_frame(clip.path(i), (SCR_W, SCR_H))
        return img

    def phone(self, canvas, screen_rgb, dy=0, overlay=None):
        scr = Image.new("RGB", (SCR_W, SCR_H + STATUS_H), DARK)
        scr.paste(self.statusbar, (0, 0))
        scr.paste(screen_rgb, (0, STATUS_H))
        if overlay is not None:
            scr = scr.convert("RGBA")
            scr.alpha_composite(overlay, (0, 0))
            scr = scr.convert("RGB")
        x, y = PH_X - self.bw, PH_Y - self.bw + dy
        canvas.alpha_composite(self.shadow, (x - 80, y - 80))
        canvas.paste(scr, (PH_X, PH_Y + dy), self.screen_mask)
        canvas.alpha_composite(self.body, (x, y))

    # --- special overlays
    def install_overlay(self, t):
        """Generic 'add to home screen' sheet, then the home screen with the new icon (t = frames since the tap)."""
        W, H = SCR_W, SCR_H + STATUS_H
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        if t < 0:
            return None
        if t < 34:  # sheet slides up
            p = ease_out(t / 10)
            ov.paste((0, 0, 0, int(120 * p)), (0, 0, W, H))
            sh_h = 360
            y = int(H - sh_h * p)
            d = ImageDraw.Draw(ov)
            d.rounded_rectangle([0, y, W, H + 40], radius=36, fill=(30, 33, 40, 255))
            d.rounded_rectangle([W // 2 - 40, y + 14, W // 2 + 40, y + 20], radius=3, fill=(90, 95, 105, 255))
            ic = self.icon.resize((96, 96), Image.LANCZOS)
            ov.alpha_composite(ic, (40, y + 52))
            ov.alpha_composite(text_img("Fitnes Zal", 40, WHITE, "SemiBold"), (156, y + 56))
            ov.alpha_composite(text_img(SITE, 24, (170, 175, 185), "Regular"), (158, y + 108))
            d.text((40, y + 172), "Ilovani o'rnatish?", font=font(30, "SemiBold"), fill=(220, 222, 228))
            d.rounded_rectangle([40, y + 238, W // 2 - 12, y + 306], radius=34, outline=(90, 95, 105), width=2)
            d.text((W // 4 + 14, y + 272), "Bekor", font=font(30, "SemiBold"), fill=(220, 222, 228), anchor="mm")
            d.rounded_rectangle([W // 2 + 12, y + 238, W - 40, y + 306], radius=34, fill=RED)
            d.text((3 * W // 4 - 14, y + 272), "O'rnatish", font=font(30, "Bold"), fill=WHITE, anchor="mm")
            if t >= 18:
                draw_tap(ov, 3 * W // 4 - 14, y + 272, t - 18, 1.0)
            return ov
        # home screen
        q = t - 34
        p = ease_out(q / 8)
        hs = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        bg = Image.new("RGBA", (W, H))
        d = ImageDraw.Draw(bg)
        for yy in range(H):
            k = yy / H
            d.line([(0, yy), (W, yy)], fill=(int(40 + 60 * k), int(28 + 10 * k), int(60 + 30 * (1 - k)), 255))
        d.text((W // 2, 150), "9:41", font=font(110, "SemiBold"), fill=(255, 255, 255, 230), anchor="mm")
        d.text((W // 2, 225), "Chorshanba, 11-noyabr", font=font(28, "Regular"), fill=(255, 255, 255, 200), anchor="mm")
        cols, size, gap = 4, 104, 34
        x0 = (W - (cols * size + (cols - 1) * gap)) // 2
        tints = [(88, 160, 255), (255, 186, 73), (90, 200, 120), (180, 120, 255), (255, 120, 140), (80, 200, 210), (140, 140, 160),
                 (250, 210, 90), (120, 170, 120), (200, 120, 90), (110, 130, 230)]
        k = 0
        for r_ in range(3):
            for c in range(cols):
                x, y = x0 + c * (size + gap), 360 + r_ * (size + 70)
                if r_ == 2 and c == 3:
                    continue
                d.rounded_rectangle([x, y, x + size, y + size], radius=26, fill=(*tints[k % len(tints)], 210))
                d.rounded_rectangle([x + 22, y + 92 + 22, x + size - 22, y + 92 + 32], radius=5, fill=(255, 255, 255, 110))
                k += 1
        hs.alpha_composite(bg)
        # the new app icon pops in
        x, y = x0 + 3 * (size + gap), 360 + 2 * (size + 70)
        s = back(clamp((q - 6) / 12))
        if s > 0.02:
            ic = self.icon.resize((max(1, int(size * s)), max(1, int(size * s))), Image.LANCZOS)
            m = rounded_mask(ic.size, int(26 * s))
            ic.putalpha(ImageChops.multiply(ic.getchannel("A"), m))
            hs.alpha_composite(ic, (x + (size - ic.width) // 2, y + (size - ic.height) // 2))
            lab = text_img("Fitnes Zal", 22, WHITE, "SemiBold")
            hs.alpha_composite(fade_alpha(lab, clamp((q - 12) / 6)), (x + size // 2 - lab.width // 2, y + size + 8))
            if q > 14:
                ring = Image.new("RGBA", (size + 60, size + 60), (0, 0, 0, 0))
                rp = clamp((q - 14) / 18)
                ImageDraw.Draw(ring).rounded_rectangle([30 - int(24 * rp), 30 - int(24 * rp), size + 30 + int(24 * rp), size + 30 + int(24 * rp)],
                                                       radius=34, outline=(255, 255, 255, int(220 * (1 - rp))), width=4)
                hs.alpha_composite(ring, (x - 30, y - 30))
        d2 = ImageDraw.Draw(hs)
        d2.rounded_rectangle([30, H - 160, W - 30, H - 40], radius=40, fill=(255, 255, 255, 60))
        return fade_alpha(hs, p)

    # --- the main loop
    def frames(self, voice_en=True, subtitles=True, events=None):
        total = sum(s["bars"] for s in REEL) * BAR
        caps = {}
        start = 0
        timeline = []
        for s in REEL:
            n = s["bars"] * BAR
            clip = Clip(self.work, self.cap, s["cap"], n) if s.get("cap") else None
            timeline.append((s, start, n, clip))
            caps[s["id"]] = (Kinetic(s["title"], 104, upper=False, max_w=960), Kinetic(s["sub"], 54, (225, 228, 235), style="SemiBold",
                                                                                           max_w=960, stagger=3))
            start += n
        self.timeline = timeline
        end_k = Kinetic("Hoziroq *ro'yxatdan* o'ting", 96, max_w=940)
        for si, (s, st, n, clip) in enumerate(timeline):
            prev = timeline[si - 1] if si else None
            for i in range(n):
                f = st + i
                canvas = self.background(f, total)
                sid = s["id"]
                if sid == "hook":
                    self.draw_hook(canvas, i, n)
                elif sid == "end":
                    self.draw_end(canvas, i, n, end_k)
                else:
                    # phone with the clip; slide-in transition from the previous phone scene
                    scr = self.screen(clip, i)
                    trans = 9
                    if prev and prev[3] is not None and i < trans:
                        p = ease_io(i / trans)
                        old = self.screen(prev[3], prev[2] - 1)
                        both = Image.new("RGB", (SCR_W, SCR_H))
                        off = int(SCR_W * p)
                        both.paste(old, (-off, 0))
                        both.paste(scr, (SCR_W - off, 0))
                        scr = both
                    ov = None
                    if sid == "install" and "install" in clip.marks:
                        ov = self.install_overlay(i - clip.marks["install"] - 4)
                    dy = 0
                    if sid == "home" and i < 16:  # phone flies in on the drop
                        dy = int((1 - back(i / 16)) * 900)
                    sc = Image.new("RGBA", (REEL_W, REEL_H), (0, 0, 0, 0))
                    self.phone(sc, scr, dy, ov)
                    # taps (screen space -> canvas)
                    if ov is None:
                        for tp in clip.taps:
                            age = i - tp["f"]
                            if 0 <= age <= 16:
                                k = SCR_W / 780
                                draw_tap(sc, PH_X + tp["x"] * k, PH_Y + STATUS_H + tp["y"] * k + dy, age, 0.9)
                    # camera: slow push-in plus a soft beat bounce in drop sections
                    sec = s["music"][min(len(s["music"]) - 1, i // BAR)]
                    bounce = 0.012 * math.exp(-(i % 30) / 6) if sec == "drop" else 0
                    zs = 1.0 + 0.035 * ease_io(i / n) + bounce
                    fy = PH_Y + 700
                    if sid == "card" and "offline" in clip.marks and i >= clip.marks["offline"]:
                        zs += 0.08 * ease_out((i - clip.marks["offline"]) / 20)
                        fy = PH_Y + 500
                    sc = zoom(sc, zs, REEL_W / 2, fy)
                    canvas.alpha_composite(sc)
                    self.badges(canvas, sid, i, n, clip)
                # captions (top safe area)
                if sid not in ("hook", "end"):
                    tk, sk = caps[sid]
                    out = i - (n - 8) if i >= n - 8 else None
                    tk.draw(canvas, REEL_W // 2, 262, i - 2, out)
                    sk.draw(canvas, REEL_W // 2, 262 + tk.h + 14, i - 12, out)
                # beat flash on cuts
                if i < 5 and si > 0:
                    fl = Image.new("RGBA", (REEL_W, REEL_H), (255, 255, 255, int(70 * (1 - i / 5))))
                    canvas.alpha_composite(fl)
                # progress bar
                d = ImageDraw.Draw(canvas)
                d.rectangle([0, 0, REEL_W, 7], fill=(255, 255, 255, 40))
                d.rectangle([0, 0, int(REEL_W * (f + 1) / total), 7], fill=RED)
                if subtitles:
                    self.subtitle(canvas, f)
                yield canvas.convert("RGB")

    def badges(self, canvas, sid, i, n, clip):
        """Stat counters / success badges that pop next to the phone."""
        def badge(text, at, y, color=RED, x=None):
            if i < at:
                return
            p = back((i - at) / 10)
            b = pill(text, 40, WHITE, (*color, 240), pad=(26, 14), style="Bold")
            w, h = max(1, int(b.width * p)), max(1, int(b.height * p))
            b = b.resize((w, h), Image.BILINEAR)
            sb, o = shadowed(b, 8, 150, (0, 4))
            xx = (x if x is not None else REEL_W - 70 - b.width) - o
            canvas.alpha_composite(sb, (int(xx), int(y - h / 2 - o)))
        if sid == "card" and "offline" in clip.marks:
            badge("📶 Offline ✅", clip.marks["offline"] + 6, 1180, (34, 160, 90), x=70)
        if sid == "prog":
            v = int(58 * ease_out((i - 20) / 40)) if i > 20 else 0
            badge(f"–{v // 10},{v % 10} kg 🔥", 20, 1250, RED, x=70)
        if sid == "ai":
            v = int(932 * ease_out((i - 24) / 45)) if i > 24 else 0
            badge(f"{v} ta tayyor javob", 24, 1330, RED)
        if sid == "plans":
            badge("Payme ✅", 70, 1240, (0, 170, 170), x=70)
        if sid == "cal":
            badge("600+ taom 🍛", 40, 1300, RED)

    def subtitle(self, canvas, f):
        for t0, t1, text in getattr(self, "subs", []):
            if t0 <= f < t1:
                a = clamp(min((f - t0) / 5, (t1 - f) / 5))
                p = pill(text, 32, WHITE, (0, 0, 0, 175), pad=(24, 12), style="SemiBold")
                if p.width > REEL_W - 120:
                    p = p.resize((REEL_W - 120, int(p.height * (REEL_W - 120) / p.width)), Image.LANCZOS)
                canvas.alpha_composite(fade_alpha(p, a), ((REEL_W - p.width) // 2, 1440))

    def draw_hook(self, canvas, i, n):
        # logo pops + glow + light sweep; title letters punch in; build-up feel
        p = back(i / 18)
        lg = self.logo
        s = 0.4 + 0.6 * p + 0.04 * ease_io(i / n)
        w, h = int(lg.width * s), int(lg.height * s)
        im = lg.resize((max(1, w), max(1, h)), Image.LANCZOS)
        im = light_sweep(im, clamp((i - 20) / 40))
        glow = glow_blob(int(170 + 30 * math.sin(i / 6)), RED, int(160 * clamp(i / 12)))
        canvas.alpha_composite(glow, (REEL_W // 2 - glow.width // 2, 700 - glow.height // 2))
        canvas.alpha_composite(fade_alpha(im, clamp(i / 8)), (REEL_W // 2 - w // 2, 700 - h // 2))
        title = word_img("FITNES ZAL", 170, WHITE)
        tp = back((i - 14) / 12)
        if tp > 0:
            tw, th = int(title.width * (1.8 - 0.8 * tp)), int(title.height * (1.8 - 0.8 * tp))
            t2 = fade_alpha(title.resize((tw, th), Image.BILINEAR), clamp((i - 14) / 6))
            sh, o = shadowed(t2, 12, 200)
            canvas.alpha_composite(sh, (REEL_W // 2 - tw // 2 - o, 1000 - th // 2 - o))
        k = Kinetic(REEL[0]["sub"], 60, (230, 232, 238), style="SemiBold", max_w=900, stagger=5)
        k.draw(canvas, REEL_W // 2, 1110, i - 30)
        # red underline sweep
        if i > 22:
            q = ease_out((i - 22) / 14)
            d = ImageDraw.Draw(canvas)
            d.rounded_rectangle([REEL_W // 2 - int(220 * q), 1088, REEL_W // 2 + int(220 * q), 1096], radius=4, fill=RED)
        # build-up: tighten zoom + darkening pulse in the last bar
        if i > n - 20:
            fl = Image.new("RGBA", (REEL_W, REEL_H), (255, 255, 255, int(120 * ((i - (n - 20)) / 20) ** 3)))
            canvas.alpha_composite(fl)

    def draw_end(self, canvas, i, n, k):
        lg = self.logo
        p = back(i / 16)
        s = 0.5 + 0.5 * p
        h = int(260 * s)
        w = int(lg.width * h / lg.height)
        im = light_sweep(lg.resize((max(1, w), max(1, h)), Image.LANCZOS), clamp((i - 30) / 40))
        glow = glow_blob(190, RED, 150)
        canvas.alpha_composite(glow, (REEL_W // 2 - glow.width // 2, 520 - glow.height // 2))
        canvas.alpha_composite(fade_alpha(im, clamp(i / 6)), (REEL_W // 2 - w // 2, 520 - h // 2))
        t = word_img("FITNES ZAL", 120, WHITE)
        if i > 8:
            canvas.alpha_composite(fade_alpha(t, clamp((i - 8) / 8)), (REEL_W // 2 - t.width // 2, 700))
        k.draw(canvas, REEL_W // 2, 860, i - 16)
        # URL pill
        if i > 34:
            q = back((i - 34) / 12)
            u = pill("🌐 " + SITE, 42, WHITE, (*RED, 245), pad=(34, 20), style="Bold")
            uw, uh = max(1, int(u.width * q)), max(1, int(u.height * q))
            u2 = u.resize((uw, uh), Image.BILINEAR)
            sh, o = shadowed(u2, 10, 170)
            canvas.alpha_composite(sh, (REEL_W // 2 - uw // 2 - o, 1110 - uh // 2 - o))
        # counters row
        stats = [("932", " ta javob"), ("24/7", " yordamchi"), ("3", " tilda")]
        for j, (v, lab) in enumerate(stats):
            at = 50 + j * 8
            if i < at:
                continue
            q = ease_out((i - at) / 12)
            if v.isdigit():
                v = str(int(int(v) * ease_out((i - at) / 30)))
            col = Image.new("RGBA", (300, 150), (0, 0, 0, 0))
            num = word_img(v, 84, RED)
            col.alpha_composite(num, (150 - num.width // 2, 0))
            lb = text_img(lab.strip(), 34, (210, 213, 220), "SemiBold")
            col.alpha_composite(lb, (150 - lb.width // 2, 98))
            canvas.alpha_composite(fade_alpha(col, q), (60 + j * 320, int(1270 + (1 - q) * 30)))


# ======================================================================= the demo (16:9)
DEMO_W, DEMO_H = 1920, 1080
WIN_W, WIN_H, BAR_H = 1472, 920, 40
WIN_X, WIN_Y = (DEMO_W - WIN_W) // 2, 112

DEMO = [
    dict(id="intro", bars=2, kind="title", en="Fitnes Zal: a complete platform for a modern gym.", music=["intro", "build"]),
    dict(id="ch1", bars=1, kind="chapter", num="01", title="Ochiq sayt", sub="mehmonlar va yangi a'zolar uchun", music=["groove"]),
    dict(id="d_home", bars=3, cap="d_home", path="/", label="Bosh sahifa: jadval, narxlar, xarita",
         en="The public site shows the gym, today's classes, prices and location at a glance.", music=["groove"] * 3),
    dict(id="d_plans", bars=2, cap="d_plans", path="/plans/", label="Abonementlar + onlayn to'lov (Payme, Click, Uzum)",
         en="Membership plans with online payment.", music=["groove"] * 2),
    dict(id="d_shop", bars=2, cap="d_shop", path="/shop/", label="Do'kon: savat va yetkazib berish",
         en="A shop for drinks and supplements, with delivery.", music=["groove"] * 2),
    dict(id="d_classes", bars=2, cap="d_classes", path="/classes/", label="Guruh mashg'ulotlari: bir bosishda band qilish",
         en="Group classes can be booked in one click.", music=["groove"] * 2),
    dict(id="d_tools", bars=2, cap="d_tools", path="/tools/", label="Kalkulyatorlar: tana, ovqat, mashq",
         en="And free fitness calculators.", music=["groove", "build"]),
    dict(id="ch2", bars=1, kind="chapter", num="02", title="A'zo kabineti", sub="shaxsiy kabinet, treker va jamoa", music=["drop"]),
    dict(id="d_login", bars=1, cap="d_login", path="/login/", label="Kirish: login, telefon yoki Google",
         en="Members sign in.", music=["drop"]),
    dict(id="d_dash", bars=4, cap="d_dash", path="/dashboard/", label="Kabinet: seriya, tashriflar, keyingi mashg'ulot",
         label2=("dark", "Tungi rejim 🌙"),
         en="Every member gets a personal dashboard with streaks, visits, the next class, and a dark mode.", music=["drop"] * 4),
    dict(id="d_prog", bars=3, cap="d_prog", path="/progress/", label="Fitnes treker: vazn, o'lchamlar, hajm grafiklari",
         en="The tracker charts weight, body measurements and training volume.", music=["drop"] * 3),
    dict(id="d_cal", bars=2, cap="d_cal", path="/calories/", label="Kaloriya hisobi: 600+ o'zbek taomlari",
         en="The calorie counter knows hundreds of Uzbek dishes.", music=["drop"] * 2),
    dict(id="d_work", bars=2, cap="d_work", path="/workouts/", label="Tayyor mashq dasturlari",
         en="Ready-made training programs.", music=["drop"] * 2),
    dict(id="d_chat", bars=3, cap="d_chat", path="/chat/1/", label="Real-time chat (WebSocket): reaksiyalar 👏",
         en="And a real-time community chat, with reactions.", music=["drop", "drop", "build"]),
    dict(id="ch3", bars=1, kind="chapter", num="03", title="Admin panel", sub="qabulxona, analitika va AI", music=["groove"]),
    dict(id="a_desk", bars=3, cap="a_desk", path="/django-admin/desk/", label="Qabulxona: qidirish va bir bosishda kirgizish",
         en="At the front desk, staff find a member and check them in within seconds.", music=["groove"] * 3),
    dict(id="a_analytics", bars=3, cap="a_analytics", path="/django-admin/analytics/", label="AI Analitika: xulosalar, grafiklar, issiqlik xaritasi",
         en="AI analytics turns the data into insights, charts and a heat map.", music=["groove"] * 3),
    dict(id="a_ai", bars=4, cap="a_ai", path="/django-admin/analytics/", label="AI yordamchi — internetsiz, o'z bazasidan javob",
         en="And the built-in AI assistant answers questions like: how much revenue did we make this month?", music=["drop"] * 4),
    dict(id="a_ig", bars=2, cap="a_ig", path="/django-admin/instagram/", label="Instagram Direct: bitta inbox + avto-javob bot",
         en="Instagram messages land in one inbox, with an auto-reply bot.", music=["drop", "build"]),
    dict(id="mobile", bars=4, kind="mobile", label="PWA: telefonga o'rnatiladi, Web Push, offline QR",
         en="On phones it installs like an app, with push notifications and an offline QR card.", music=["drop"] * 4),
    dict(id="outro", bars=4, kind="outro",
         en="Built with Django, Channels and PostgreSQL, and covered by more than seven hundred eighty tests.",
         music=["outro", "outro", "outro", "end"]),
]

TECH = ["Django 5.2", "Channels / WebSocket", "PostgreSQL", "PWA + Web Push", "Offline AI yordamchi", "780+ test"]


class DemoRenderer:
    def __init__(self, work, cap, mcap, mwork):
        self.work, self.cap, self.mcap, self.mwork = work, cap, mcap, mwork
        bg = Image.new("RGBA", (DEMO_W, DEMO_H), (*DARK, 255))
        bg.alpha_composite(glow_blob(420, RED, 90), (-300, -500))
        bg.alpha_composite(glow_blob(380, (60, 90, 200), 60), (DEMO_W - 1200, DEMO_H - 1100))
        self.bg = bg
        self.logo = logo_img(220)
        self.icon = Image.open(STATIC / "icon-512.png").convert("RGBA")
        sh = Image.new("RGBA", (WIN_W + 200, WIN_H + BAR_H + 200), (0, 0, 0, 0))
        ImageDraw.Draw(sh).rounded_rectangle([100, 120, 100 + WIN_W, 120 + WIN_H + BAR_H], radius=18, fill=(0, 0, 0, 210))
        self.shadow = sh.filter(ImageFilter.GaussianBlur(40))
        self.win_mask = rounded_mask((WIN_W, WIN_H + BAR_H), 16)
        self.reel = ReelRenderer(mwork, mcap)  # phone mockups for the mobile scene

    def chrome(self, path):
        bar = Image.new("RGB", (WIN_W, BAR_H), (32, 35, 42))
        d = ImageDraw.Draw(bar)
        for k, c in enumerate([(255, 95, 87), (254, 188, 46), (40, 200, 64)]):
            d.ellipse([18 + k * 24, 14, 30 + k * 24, 26], fill=c)
        d.rounded_rectangle([WIN_W // 2 - 330, 7, WIN_W // 2 + 330, 33], radius=13, fill=(20, 22, 27))
        d.text((WIN_W // 2 - 310, 20), "🔒", font=efont(14), embedded_color=True, anchor="lm")
        d.text((WIN_W // 2 - 288, 20), SITE + path, font=font(17, "Regular"), fill=(200, 203, 210), anchor="lm")
        return bar

    def window(self, canvas, content, path):
        win = Image.new("RGB", (WIN_W, WIN_H + BAR_H))
        win.paste(self.chrome(path), (0, 0))
        win.paste(content, (0, BAR_H))
        canvas.alpha_composite(self.shadow, (WIN_X - 100, WIN_Y - 100))
        canvas.paste(win, (WIN_X, WIN_Y), self.win_mask)

    def frames(self, subtitles=True):
        total = sum(s["bars"] for s in DEMO) * BAR
        tl, st = [], 0
        for s in DEMO:
            n = s["bars"] * BAR
            clip = Clip(self.work, self.cap, s["cap"], n) if s.get("cap") else None
            tl.append((s, st, n, clip))
            st += n
        self.timeline = tl
        chapter = None
        for si, (s, st, n, clip) in enumerate(tl):
            if s.get("kind") == "chapter":
                chapter = f"{s['num']} · {s['title']}"
            for i in range(n):
                f = st + i
                canvas = self.bg.copy()
                kind = s.get("kind")
                if kind == "title":
                    self.draw_title(canvas, i, n)
                elif kind == "chapter":
                    self.draw_chapter(canvas, s, i, n)
                elif kind == "mobile":
                    self.draw_mobile(canvas, s, i, n)
                elif kind == "outro":
                    self.draw_outro(canvas, i, n)
                else:
                    content = load_frame(clip.path(i), (WIN_W, WIN_H))
                    prev = tl[si - 1]
                    if prev[3] is not None and i < 10:  # cross-dissolve from the previous page
                        old = load_frame(prev[3].path(prev[2] - 1), (WIN_W, WIN_H))
                        content = Image.blend(old, content, ease_io(i / 10))
                    sc = Image.new("RGBA", (DEMO_W, DEMO_H), (0, 0, 0, 0))
                    self.window(sc, content, s["path"])
                    k = WIN_W / 2160
                    for tp in clip.taps:
                        draw_tap(sc, WIN_X + tp["x"] * k, WIN_Y + BAR_H + tp["y"] * k, i - tp["f"], 0.7, (240, 80, 61))
                    zs, fx, fy = 1.0 + 0.03 * ease_io(i / n), DEMO_W / 2, DEMO_H / 2
                    if s["id"] == "a_ai" and "asked" in clip.marks:  # push in on the answer
                        q = ease_io((i - clip.marks["asked"] + 10) / 30)
                        zs += 0.42 * q
                        fx, fy = WIN_X + WIN_W - 190, WIN_Y + 420
                    if s["id"] == "a_desk" and "checkin" in clip.marks:
                        q = ease_io((i - clip.marks["checkin"] + 6) / 24)
                        zs += 0.22 * q
                        fx, fy = WIN_X + 520, WIN_Y + 260
                    canvas.alpha_composite(zoom(sc, zs, fx, fy))
                    self.labels(canvas, s, i, n, clip, chapter)
                if si > 0 and i < 4:
                    canvas.alpha_composite(Image.new("RGBA", (DEMO_W, DEMO_H), (255, 255, 255, int(50 * (1 - i / 4)))))
                if subtitles:
                    self.subtitle(canvas, f)
                yield canvas.convert("RGB")

    def labels(self, canvas, s, i, n, clip, chapter):
        cw = 0
        if chapter:
            c = pill(chapter.upper(), 24, WHITE, (*RED, 235), pad=(18, 10), style="Bold")
            canvas.alpha_composite(c, (WIN_X, 62 - c.height // 2))
            cw = c.width + 16
            lg = self.logo.resize((int(self.logo.width * 54 / self.logo.height), 54), Image.LANCZOS)
            canvas.alpha_composite(lg, (DEMO_W - WIN_X - lg.width, 35))
        if i > 6:
            p = ease_out((i - 6) / 12)
            out = clamp((i - (n - 10)) / 8) if i > n - 10 else 0
            lab = pill(s["label"], 26, WHITE, (40, 44, 54, 240), pad=(20, 10), style="SemiBold", dot=RED)
            x = int(WIN_X + cw - (1 - p) * 40)
            canvas.alpha_composite(fade_alpha(lab, p * (1 - out)), (x, 62 - lab.height // 2))
        if s.get("label2") and s["label2"][0] in clip.marks:
            at = clip.marks[s["label2"][0]] + 6
            if i > at:
                p = back((i - at) / 10)
                lab = pill(s["label2"][1], 30, WHITE, (*RED, 240), pad=(22, 12), style="Bold")
                lab = lab.resize((max(1, int(lab.width * p)), max(1, int(lab.height * p))), Image.BILINEAR)
                canvas.alpha_composite(lab, (WIN_X + WIN_W - 60 - lab.width, WIN_Y + 90))

    def subtitle(self, canvas, f):
        for t0, t1, text in getattr(self, "subs", []):
            if t0 <= f < t1:
                a = clamp(min((f - t0) / 5, (t1 - f) / 5))
                p = pill(text, 26, WHITE, (0, 0, 0, 190), pad=(20, 10), style="SemiBold")
                canvas.alpha_composite(fade_alpha(p, a), ((DEMO_W - p.width) // 2, DEMO_H - 62))

    def draw_title(self, canvas, i, n):
        p = back(i / 18)
        h = int(260 * (0.5 + 0.5 * p))
        lg = self.logo.resize((int(self.logo.width * h / self.logo.height), h), Image.LANCZOS)
        lg = light_sweep(lg, clamp((i - 16) / 40))
        canvas.alpha_composite(glow_blob(200, RED, int(140 * clamp(i / 10))), (DEMO_W // 2 - 400, 330 - 400))
        canvas.alpha_composite(fade_alpha(lg, clamp(i / 6)), (DEMO_W // 2 - lg.width // 2, 330 - h // 2))
        k = Kinetic("FITNES ZAL", 150, max_w=1600)
        k.draw(canvas, DEMO_W // 2, 520, i - 12)
        k2 = Kinetic("zamonaviy zal uchun *to'liq* platforma", 56, (220, 223, 230), style="SemiBold", max_w=1600)
        k2.draw(canvas, DEMO_W // 2, 700, i - 26)
        if i > n - 16:
            canvas.alpha_composite(Image.new("RGBA", (DEMO_W, DEMO_H), (255, 255, 255, int(110 * ((i - (n - 16)) / 16) ** 3))))

    def draw_chapter(self, canvas, s, i, n):
        p = ease_out(i / 10)
        num = word_img(s["num"], 260, RED)
        canvas.alpha_composite(fade_alpha(num, p * 0.9), (int(260 - (1 - p) * 80), 300))
        k = Kinetic(s["title"].upper(), 140, max_w=1300)
        k.draw(canvas, 0, 340, i - 4, None, align="left", x0=640)
        k2 = Kinetic(s["sub"], 50, (205, 208, 216), style="SemiBold", max_w=1200, stagger=2)
        k2.draw(canvas, 0, 520, i - 12, None, align="left", x0=646)
        d = ImageDraw.Draw(canvas)
        d.rectangle([646, 500, 646 + int(500 * ease_out((i - 8) / 14)), 506], fill=RED)

    def draw_mobile(self, canvas, s, i, n):
        """Three phones (scaled from the reel mockup) showing the mobile app: AI, offline card, install."""
        R = self.reel
        picks = [("m_card", "offline"), ("m_ai", None), ("m_install", None)]
        titles = ["Offline QR karta ✅", "Murabbiy yordamchi 🤖", "Ilova kabi o'rnatish 📲"]
        sc = 0.62
        for k, (scene, mk) in enumerate(picks):
            clip = Clip(self.mwork, self.mcap, scene, n)
            j = i
            if mk and mk in clip.marks:
                j = int(clip.marks[mk] + i * 0.5)
            scr = R.screen(clip, min(j, n - 1))
            ov = None
            if scene == "m_install" and "install" in clip.marks:
                ov = R.install_overlay(i - int(clip.marks["install"]) - 4)
            ph = Image.new("RGBA", (REEL_W, REEL_H), (0, 0, 0, 0))
            R.phone(ph, scr, 0, ov)
            ph = ph.crop((PH_X - 110, PH_Y - 110, PH_X + SCR_W + 110, PH_Y + SCR_H + STATUS_H + 110))
            ph = ph.resize((int(ph.width * sc), int(ph.height * sc)), Image.LANCZOS)
            at = k * 8
            p = back((i - at) / 16)
            if p <= 0:
                continue
            x = DEMO_W // 2 - ph.width // 2 + (k - 1) * 520
            y = 120 + int((1 - p) * 500)
            canvas.alpha_composite(fade_alpha(ph, clamp((i - at) / 6)), (x, y))
            t = pill(titles[k], 28, WHITE, (*RED, 235), pad=(20, 10), style="Bold")
            canvas.alpha_composite(fade_alpha(t, clamp((i - at - 10) / 8)), (x + ph.width // 2 - t.width // 2, 70))
        lab = pill(s["label"], 30, WHITE, (12, 14, 18, 225), pad=(24, 14), style="SemiBold", dot=RED)
        canvas.alpha_composite(fade_alpha(lab, clamp((i - 30) / 10)), (DEMO_W // 2 - lab.width // 2, DEMO_H - 150))

    def draw_outro(self, canvas, i, n):
        h = 170
        lg = self.logo.resize((int(self.logo.width * h / self.logo.height), h), Image.LANCZOS)
        lg = light_sweep(lg, clamp((i - 10) / 40))
        canvas.alpha_composite(glow_blob(150, RED, 120), (DEMO_W // 2 - 300, 190 - 300))
        canvas.alpha_composite(fade_alpha(lg, clamp(i / 8)), (DEMO_W // 2 - lg.width // 2, 190 - h // 2))
        k = Kinetic("Texnologiyalar", 72, max_w=1600)
        k.draw(canvas, DEMO_W // 2, 300, i - 6)
        # tech chips pop on beats (every 15 frames)
        chips = [pill(t, 36, WHITE, (34, 38, 46, 255), pad=(28, 16), style="SemiBold", dot=RED) for t in TECH]
        rows = [chips[:3], chips[3:]]
        for r_, row in enumerate(rows):
            W = sum(c.width for c in row) + 24 * (len(row) - 1)
            x = DEMO_W // 2 - W // 2
            for c_, c in enumerate(row):
                at = 20 + (r_ * 3 + c_) * 15
                p = back((i - at) / 10)
                if p > 0:
                    cc = c.resize((max(1, int(c.width * p)), max(1, int(c.height * p))), Image.BILINEAR)
                    canvas.alpha_composite(cc, (x + (c.width - cc.width) // 2, 430 + r_ * 100 + (c.height - cc.height) // 2))
                x += c.width + 24
        stats = [("780+", "avtomatik test"), ("932", "tayyor javob"), ("3", "til: uz · ru · en")]
        for j, (v, lab) in enumerate(stats):
            at = 120 + j * 10
            if i < at:
                continue
            q = ease_out((i - at) / 14)
            vv = v
            if v.rstrip("+").isdigit():
                vv = str(int(int(v.rstrip("+")) * ease_out((i - at) / 30))) + ("+" if v.endswith("+") else "")
            num = word_img(vv, 96, RED)
            lb = text_img(lab, 32, (210, 213, 220), "SemiBold")
            cx = DEMO_W // 2 + (j - 1) * 420
            canvas.alpha_composite(fade_alpha(num, q), (cx - num.width // 2, 690))
            canvas.alpha_composite(fade_alpha(lb, q), (cx - lb.width // 2, 800))
        if i > 170:
            q = back((i - 170) / 12)
            u = pill("🌐 " + SITE, 40, WHITE, (*RED, 245), pad=(30, 16), style="Bold")
            u = u.resize((max(1, int(u.width * q)), max(1, int(u.height * q))), Image.BILINEAR)
            canvas.alpha_composite(u, (DEMO_W // 2 - u.width // 2, 900))


# ======================================================================= audio + encoding
def music_sections(spec):
    out = []
    for s in spec:
        out += s["music"][: s["bars"]] + [s["music"][-1]] * (s["bars"] - len(s["music"]))
    return out


def build_audio(work, name, spec, timeline, voice, sub_holder, voice_on=True):
    """Returns (mix_with_voice.wav or None, music_only_mix.wav). Also fills sub_holder.subs for subtitles."""
    fx = ffmpeg_exe()
    adir = os.path.join(work, "audio_" + name)
    os.makedirs(adir, exist_ok=True)
    total_sec = sum(s["bars"] for s in spec) * BAR / FPS
    L, R = va.song(music_sections(spec))
    music = va.write_wav(os.path.join(adir, "music.wav"), L, R, peak=0.8)
    events = []
    for s, st, n, clip in timeline:
        t0 = st / FPS
        if st:
            events.append((max(0, t0 - 0.28), "whoosh", 0.55))
        events.append((t0 + 2 / FPS, "pop", 0.5))
        if clip:
            for tp in clip.taps:
                events.append((t0 + tp["f"] / FPS + 0.02, "click", 0.6))
            for k in ("offline", "checkin"):
                if k in clip.marks:
                    events.append((t0 + clip.marks[k] / FPS + 0.15, "chime", 0.7))
            for k in ("sent", "asked"):
                if k in clip.marks:
                    events.append((t0 + clip.marks[k] / FPS + 1.0, "chime", 0.45))
            # typing ticks: whenever a new unique frame appears right after a tap into a field, roughly
        if s["id"] == "install":
            mk = clip.marks.get("install", 0)
            events.append((t0 + (mk + 4 + 18) / FPS, "click", 0.6))
            events.append((t0 + (mk + 4 + 46) / FPS, "chime", 0.6))
    sfx = va.sfx_track(events, total_sec)
    sfx_path = va.write_wav(os.path.join(adir, "sfx.wav"), sfx, sfx, peak=0.7)
    music_only = va.mix(fx, music, sfx_path, None, os.path.join(adir, "mix_music.wav"))
    if not voice_on:
        return None, music_only
    lines = {s["id"]: s["en"] for s in spec if s.get("en")}
    paths = va.tts(lines, os.path.join(adir, "voice"), voice=voice, rate=1)
    clips, subs = [], []
    for s, st, n, clip in timeline:
        if s["id"] not in paths:
            continue
        x = va.trim_silence(va.read_wav_mono(paths[s["id"]]))
        t0 = st / FPS + 0.35
        dur = len(x) / va.SR
        if dur > n / FPS - 0.2:
            print(f"  ! voice line for {s['id']} is {dur:.1f}s, scene {n / FPS:.1f}s")
        clips.append((t0, x))
        subs.append((int(t0 * FPS), int((t0 + dur + 0.25) * FPS), s["en"]))
    sub_holder.subs = subs
    vt = va.voice_track(clips, total_sec)
    vpath = va.write_wav(os.path.join(adir, "voice.wav"), vt, vt, peak=0.95)
    with_voice = va.mix(fx, music, sfx_path, vpath, os.path.join(adir, "mix_voice.wav"))
    return with_voice, music_only


def encode(frames, size, out_mp4, audio=None, extra_audio_outputs=(), crf=20):
    """Pipe RGB frames into x264; then mux each audio into its own mp4 (video stream copied)."""
    fx = ffmpeg_exe()
    silent = out_mp4.with_suffix(".video.mp4")
    p = subprocess.Popen([fx, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{size[0]}x{size[1]}",
                          "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", str(crf), "-pix_fmt", "yuv420p",
                          "-profile:v", "high", "-movflags", "+faststart", str(silent)], stdin=subprocess.PIPE)
    t0, n = time.time(), 0
    for img in frames:
        p.stdin.write(img.tobytes())
        n += 1
        if n % 150 == 0:
            print(f"  {out_mp4.name}: {n} frames, {time.time() - t0:.0f}s")
    p.stdin.close()
    if p.wait():
        raise RuntimeError("ffmpeg failed")
    outs = [(out_mp4, audio)] + list(extra_audio_outputs)
    for dst, a in outs:
        if a:
            subprocess.run([fx, "-y", "-loglevel", "error", "-i", str(silent), "-i", a, "-map", "0:v", "-map", "1:a", "-c:v", "copy",
                            "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", str(dst)], check=True)
        else:
            shutil.copy(silent, dst)
    silent.unlink()
    return n


def save_cover(frames, at, path):
    for k, img in enumerate(frames):
        if k == at:
            img.save(path)
            return


def render(work, only=None):
    OUT.mkdir(parents=True, exist_ok=True)
    mwork, dwork = os.path.join(work, "cap_m"), os.path.join(work, "cap_d")
    mcap = json.load(open(os.path.join(mwork, "scenes.json"), encoding="utf-8"))
    dcap = json.load(open(os.path.join(dwork, "scenes.json"), encoding="utf-8"))
    if only in (None, "reel"):
        rr = ReelRenderer(mwork, mcap)
        next(rr.frames())  # builds the timeline
        print("reel: audio")
        with_voice, music_only = build_audio(work, "reel", REEL, rr.timeline, "Microsoft Zira Desktop", rr)
        print("reel: video (voice-over + English subtitles)")
        n = encode(rr.frames(subtitles=True), (REEL_W, REEL_H), OUT / "fitnes-zal-reel.mp4", with_voice)
        print("reel: video (music only, no subtitles)")
        encode(rr.frames(subtitles=False), (REEL_W, REEL_H), OUT / "fitnes-zal-reel-music.mp4", music_only)
        save_cover(rr.frames(subtitles=False), 56, OUT / "fitnes-zal-reel-cover.png")
        print(f"reel: {n} frames")
    if only in (None, "demo"):
        dr = DemoRenderer(dwork, dcap, mcap, mwork)
        next(dr.frames())
        print("demo: audio")
        with_voice, music_only = build_audio(work, "demo", DEMO, dr.timeline, "Microsoft David Desktop", dr)
        print("demo: video")
        n = encode(dr.frames(subtitles=True), (DEMO_W, DEMO_H), OUT / "fitnes-zal-demo.mp4", with_voice)
        save_cover(dr.frames(subtitles=False), 70, OUT / "fitnes-zal-demo-cover.png")
        print(f"demo: {n} frames")


# ======================================================================= orchestration
def run_all():
    import video_capture as vc
    tmp = Path(os.environ["TEMP"]) / "fzvideo"
    if tmp.exists():
        shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True)
    db, media, src = tmp / "demo.sqlite3", tmp / "media", tmp / "src"
    shutil.copy(ROOT / "db.sqlite3", db)
    media.mkdir()
    src.mkdir()
    # serve the last COMMITTED code (the working tree may be mid-edit)
    arch = subprocess.run(["git", "-C", str(ROOT), "archive", "HEAD"], check=True, capture_output=True).stdout
    import io
    import tarfile
    tarfile.open(fileobj=io.BytesIO(arch)).extractall(src, filter="data")
    env = dict(os.environ, FZ_DB=str(db), FZ_MEDIA_DIR=str(media), DJANGO_DEBUG="1", PYTHONIOENCODING="utf-8", FZ_CODE_ROOT=str(src))
    mp, ap = "Demo" + secrets.token_hex(5), "Adm" + secrets.token_hex(5)
    py = sys.executable
    subprocess.run([py, str(TOOLS / "video_seed.py"), mp, ap], check=True, env=env, cwd=str(src))
    log = open(tmp / "server.log", "w")
    srv = subprocess.Popen([py, "-m", "uvicorn", "config.asgi:application", "--host", "127.0.0.1", "--port", "8770"], cwd=str(src), env=env,
                           stdout=log, stderr=subprocess.STDOUT)
    try:
        for _ in range(60):
            try:
                urllib.request.urlopen("http://127.0.0.1:8770/healthz", timeout=1)
                break
            except Exception:
                time.sleep(0.5)
        base = "http://127.0.0.1:8770"
        print("capture: mobile")
        vc.capture_mobile(str(tmp / "cap_m"), base, mp)
        print("capture: desktop")
        vc.capture_desktop(str(tmp / "cap_d"), base, mp, ap)
    finally:
        srv.terminate()
        try:
            srv.wait(10)
        except Exception:
            srv.kill()
        log.close()
    render(str(tmp))
    shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "all"
    if cmd == "all":
        run_all()
    elif cmd == "render":
        render(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
