# /// script
# dependencies = ["pillow"]
# ///
"""Draw the device frame around simulator captures.

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
BODY = (38, 40, 44)
BEZEL = (18, 18, 20)
KEY_TXT = (170, 174, 180)
ORANGE = (255, 122, 26)
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
    h = SCREEN_Y + SH + 64
    im = Image.new("RGB", (w, h), BODY)
    d = ImageDraw.Draw(im)
    # top label strip
    d.text((PAD, 16), "CARDPUTER AI", font=font(18, True), fill=ORANGE)
    d.text((w - PAD, 16), "TinyTalk 2 · 8M params", font=font(18), fill=KEY_TXT, anchor="ra")
    # screen bezel (screen pixels are pasted/overlaid on top of the black hole)
    d.rounded_rectangle((SCREEN_X - 10, SCREEN_Y - 10, SCREEN_X + SW + 10, SCREEN_Y + SH + 10),
                        radius=12, fill=BEZEL)
    d.rectangle((SCREEN_X, SCREEN_Y, SCREEN_X + SW - 1, SCREEN_Y + SH - 1), fill=(0, 0, 0))
    d.text((w / 2, h - 26), "simulator capture  ·  real firmware UI + model  ·  device speed",
           font=font(16), fill=(130, 134, 140), anchor="mm")
    return im


def draw_banner(device, screen):
    dev = device.copy()
    dev.paste(screen.resize((SW, SH), Image.NEAREST), (SCREEN_X, SCREEN_Y))
    W, H = 1280, 640
    im = Image.new("RGB", (W, H), (14, 16, 20))
    d = ImageDraw.Draw(im)
    s = min(600 / dev.width, (H - 60) / dev.height)
    dev = dev.resize((int(dev.width * s), int(dev.height * s)), Image.LANCZOS)
    im.paste(dev, (W - dev.width - 36, (H - dev.height) // 2))
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
