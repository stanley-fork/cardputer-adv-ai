# /// script
# dependencies = ["pillow"]
# ///
"""Draw the stylized Cardputer frame around simulator captures.

    uv run tools/sim/frame.py OUT_DIR SCREEN.png

Writes OUT_DIR/frame.png (the device body; the screen goes at SCREEN_X/Y,
printed on stdout for ffmpeg) and OUT_DIR/banner.png (a 1280x640 social card
built from SCREEN.png). It's a flat illustration, not a photo of the device.
"""
import sys
from PIL import Image, ImageDraw, ImageFont

SCALE = 3                       # 240x135 screen -> 720x405
SW, SH = 240 * SCALE, 135 * SCALE
PAD = 44
KEY_H, KEY_GAP = 50, 8
BODY = (38, 40, 44)
BEZEL = (18, 18, 20)
KEY = (60, 63, 69)
KEY_TXT = (170, 174, 180)
ORANGE = (255, 122, 26)
ROWS = [
    ["`", "1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "-", "=", "del"],
    ["tab", "q", "w", "e", "r", "t", "y", "u", "i", "o", "p", "[", "]", "\\"],
    ["fn", "aa", "a", "s", "d", "f", "g", "h", "j", "k", "l", ";", "'", "ok"],
    ["ctrl", "opt", "alt", "z", "x", "c", "v", "b", "n", "m", ",", ".", "/", "_"],
]
SCREEN_X, SCREEN_Y = PAD, PAD + 26


def font(size, bold=False):
    for path in ["/System/Library/Fonts/HelveticaNeue.ttc",
                 "/System/Library/Fonts/Helvetica.ttc",
                 "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]:
        try:
            return ImageFont.truetype(path, size, index=1 if bold else 0)
        except OSError:
            continue
    return ImageFont.load_default()


def draw_device():
    w = SW + 2 * PAD
    kb_h = 4 * KEY_H + 3 * KEY_GAP
    h = SCREEN_Y + SH + 34 + kb_h + 54
    im = Image.new("RGB", (w, h), BODY)
    d = ImageDraw.Draw(im)
    # top label strip
    d.text((PAD, 16), "CARDPUTER AI", font=font(18, True), fill=ORANGE)
    d.text((w - PAD, 16), "TinyTalk 2 · 8M params", font=font(18), fill=KEY_TXT, anchor="ra")
    # screen bezel (screen pixels are pasted/overlaid on top of the black hole)
    d.rounded_rectangle((SCREEN_X - 10, SCREEN_Y - 10, SCREEN_X + SW + 10, SCREEN_Y + SH + 10),
                        radius=12, fill=BEZEL)
    d.rectangle((SCREEN_X, SCREEN_Y, SCREEN_X + SW - 1, SCREEN_Y + SH - 1), fill=(0, 0, 0))
    # keyboard
    ky = SCREEN_Y + SH + 34
    kw = (SW - 13 * KEY_GAP) / 14
    f, fs = font(15), font(12)
    for r, row in enumerate(ROWS):
        for c, label in enumerate(row):
            x0 = PAD + c * (kw + KEY_GAP)
            y0 = ky + r * (KEY_H + KEY_GAP)
            fill = ORANGE if label in ("ok",) else KEY
            d.rounded_rectangle((x0, y0, x0 + kw, y0 + KEY_H), radius=9, fill=fill)
            txt = {"ok": "enter", "_": "space", "aa": "aA"}.get(label, label)
            d.text((x0 + kw / 2, y0 + KEY_H / 2), txt, font=f if len(txt) < 4 else fs,
                   fill=(30, 30, 30) if label == "ok" else KEY_TXT, anchor="mm")
    d.text((w / 2, h - 26), "simulator capture  ·  real firmware UI + model  ·  device speed",
           font=font(16), fill=(130, 134, 140), anchor="mm")
    return im


def draw_banner(device, screen):
    dev = device.copy()
    dev.paste(screen.resize((SW, SH), Image.NEAREST), (SCREEN_X, SCREEN_Y))
    W, H = 1280, 640
    im = Image.new("RGB", (W, H), (14, 16, 20))
    d = ImageDraw.Draw(im)
    s = (H - 60) / dev.height
    dev = dev.resize((int(dev.width * s), int(dev.height * s)), Image.LANCZOS)
    im.paste(dev, (W - dev.width - 30, 30))
    x = 56
    d.text((x, 118), "A real chatbot", font=font(64, True), fill=(255, 255, 255))
    d.text((x, 192), "on a microchip.", font=font(64, True), fill=ORANGE)
    lines = ["8 million parameters", "512 KB of RAM", "no internet, no cloud", "writes simple, coherent English"]
    for i, t in enumerate(lines):
        y = 312 + i * 44
        d.ellipse((x, y + 9, x + 12, y + 21), fill=ORANGE)
        d.text((x + 26, y), t, font=font(28), fill=(205, 208, 214))
    d.text((x, 540), "github.com/therezor/cardputer-ai", font=font(22), fill=(120, 124, 130))
    return im


if __name__ == "__main__":
    out, screen_png = sys.argv[1], sys.argv[2]
    dev = draw_device()
    dev.save(f"{out}/frame.png")
    draw_banner(dev, Image.open(screen_png).convert("RGB")).save(f"{out}/banner.png")
    print(SCREEN_X, SCREEN_Y, dev.width, dev.height)
