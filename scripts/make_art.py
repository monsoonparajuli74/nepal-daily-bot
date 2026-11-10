"""Generate the bot's Nepal-themed artwork (profile picture and welcome banner).

Run once whenever the art should change::

    python scripts/make_art.py

Requires Pillow (``pip install pillow``). Outputs are committed, so the running bot
never needs Pillow.
"""

from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parent.parent / "app" / "assets"

CRIMSON_TOP = (225, 55, 74)
CRIMSON = (220, 20, 60)
CRIMSON_DEEP = (150, 12, 40)
BLUE = (0, 56, 147)
BLUE_DEEP = (0, 36, 96)
IVORY = (250, 246, 236)
GOLD = (227, 178, 60)
SNOW = (255, 255, 255)
HILL_FAR = (232, 226, 210)
HILL_MID = (250, 246, 236)

FONT_DIR = Path("C:/Windows/Fonts")
DEV_BOLD = FONT_DIR / "Nirmala.ttc"
SANS_BOLD = FONT_DIR / "arialbd.ttf"
SANS = FONT_DIR / "arial.ttf"


def _font(path: Path, size: int, index: int = 0) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(path), size=size, index=index)


def vertical_gradient(size: tuple[int, int], top: tuple[int, int, int], bottom: tuple[int, int, int]) -> Image.Image:
    width, height = size
    image = Image.new("RGB", size)
    draw = ImageDraw.Draw(image)
    for y in range(height):
        t = y / max(height - 1, 1)
        colour = tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3))
        draw.line([(0, y), (width, y)], fill=colour)
    return image


def crescent_layer(size: tuple[int, int], centre: tuple[int, int], radius: int, offset: tuple[int, int], colour) -> Image.Image:
    """White crescent (flag moon) drawn on a transparent layer."""
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    mask = Image.new("L", size, 0)
    md = ImageDraw.Draw(mask)
    cx, cy = centre
    md.ellipse([cx - radius, cy - radius, cx + radius, cy + radius], fill=255)
    ox, oy = offset
    md.ellipse([cx - radius + ox, cy - radius + oy, cx + radius + ox, cy + radius + oy], fill=0)
    solid = Image.new("RGBA", size, colour)
    layer.paste(solid, (0, 0), mask)
    return layer


def draw_sun(draw: ImageDraw.ImageDraw, centre: tuple[int, int], radius: int, colour) -> None:
    cx, cy = centre
    draw.ellipse([cx - radius, cy - radius, cx + radius, cy + radius], fill=colour)
    for step in range(12):
        angle = math.tau * step / 12
        inner = radius + 5
        outer = radius + 16
        x1 = cx + math.cos(angle) * inner
        y1 = cy + math.sin(angle) * inner
        x2 = cx + math.cos(angle) * outer
        y2 = cy + math.sin(angle) * outer
        draw.line([(x1, y1), (x2, y2)], fill=colour, width=4)


def mountain_layers(
    draw: ImageDraw.ImageDraw,
    width: int,
    height: int,
    base: int,
    colour,
    peaks: list[tuple[float, float, float]],
    snow: tuple[int, int, int] | None = None,
) -> None:
    """Peaks are (relative_x, peak_height_px, width_factor in 0..1 of the width)."""
    points: list[tuple[float, float]] = []
    for rel_x, peak_h, rel_w in peaks:
        peak_x = rel_x * width
        half = rel_w * width / 2
        points.append((peak_x - half, base))
        points.append((peak_x, base - peak_h))
        points.append((peak_x + half, base))
    points.sort(key=lambda p: p[0])
    polygon = [(0, height)] + points + [(width, height)]
    draw.polygon(polygon, fill=colour)

    if snow is not None:
        for rel_x, peak_h, rel_w in peaks:
            if peak_h < 40:
                continue
            peak_x = rel_x * width
            tip = (peak_x, base - peak_h)
            cap_h = peak_h * 0.28
            half = rel_w * width / 2 * (cap_h / max(peak_h, 1))
            draw.polygon(
                [tip, (peak_x + half, base - peak_h + cap_h), (peak_x - half, base - peak_h + cap_h)],
                fill=snow,
            )


def prayer_flags(draw: ImageDraw.ImageDraw, start: tuple[int, int], end: tuple[int, int], size: int) -> None:
    x1, y1 = start
    x2, y2 = end
    colours = [(0, 56, 147), (255, 255, 255), (220, 20, 60), (24, 128, 56), (245, 205, 40)]
    steps = 16
    draw.line([start, end], fill=(255, 255, 255, 90), width=2)
    for i in range(steps):
        t = i / (steps - 1)
        x = x1 + (x2 - x1) * t
        y = y1 + (y2 - y1) * t + math.sin(t * math.pi) * 18
        colour = colours[i % len(colours)]
        draw.polygon([(x - size / 2, y), (x + size / 2, y), (x, y + size)], fill=colour)


def make_avatar() -> Path:
    size = 512
    base = vertical_gradient((size, size), CRIMSON_TOP, CRIMSON_DEEP)
    canvas = base.convert("RGBA")
    draw = ImageDraw.Draw(canvas)

    # soft prayer-flag garland behind the mountains
    flags = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    fdraw = ImageDraw.Draw(flags)
    prayer_flags(fdraw, (10, 120), (size - 10, 96), 26)
    canvas = Image.alpha_composite(canvas, flags)
    draw = ImageDraw.Draw(canvas)

    draw_sun(draw, (386, 176), 40, GOLD)
    canvas.alpha_composite(crescent_layer((size, size), (132, 170), 52, (34, 26), SNOW + (255,)))
    draw = ImageDraw.Draw(canvas)

    mountain_layers(
        draw,
        size,
        size,
        base=372,
        colour=HILL_FAR,
        peaks=[(0.18, 190, 0.5), (0.5, 132, 0.42), (0.84, 220, 0.55)],
    )
    mountain_layers(
        draw,
        size,
        size,
        base=452,
        colour=SNOW,
        peaks=[(0.3, 250, 0.5), (0.68, 200, 0.46), (0.95, 150, 0.4)],
        snow=IVORY,
    )
    mountain_layers(
        draw,
        size,
        size,
        base=512,
        colour=BLUE,
        peaks=[(0.1, 140, 0.6), (0.6, 112, 0.7)],
    )

    # outer blue ring, kept inside the circular crop
    draw.ellipse([6, 6, size - 6, size - 6], outline=BLUE, width=12)

    out = OUT / "avatar.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    canvas.convert("RGB").save(out, "PNG")
    return out


def make_welcome() -> Path:
    width, height = 1200, 630
    canvas = vertical_gradient((width, height), CRIMSON_TOP, CRIMSON_DEEP).convert("RGBA")

    texture = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    tdraw = ImageDraw.Draw(texture)
    for offset in range(-height, width, 46):
        tdraw.line([(offset, 0), (offset + height, height)], fill=(255, 255, 255, 14), width=2)
    canvas = Image.alpha_composite(canvas, texture)

    draw = ImageDraw.Draw(canvas)
    prayer_flags(draw, (-30, 60), (width + 30, 40), 34)
    draw_sun(draw, (125, 210), 46, GOLD)
    canvas.alpha_composite(crescent_layer((width, height), (1075, 150), 54, (36, 28), SNOW + (255,)))
    draw = ImageDraw.Draw(canvas)

    panel = [196, 140, width - 196, 470]
    draw.rounded_rectangle(panel, radius=36, fill=IVORY, outline=GOLD, width=4)

    dev = _font(DEV_BOLD, 84, index=0)
    sans_big = _font(SANS_BOLD, 58)
    sans_small = _font(SANS, 26)
    dev_small = _font(DEV_BOLD, 26, index=0)

    _centre_text(draw, width, 168, "नमस्ते", dev, CRIMSON)
    _centre_text(draw, width, 288, "SAJILO NEPAL", sans_big, BLUE)
    _centre_text(draw, width, 372, "Daily essentials, one tap away", sans_small, (96, 88, 74))
    _centre_text(draw, width, 410, "दैनिक जानकारी, एक ट्यापमा", dev_small, (96, 88, 74))

    mountain_layers(
        draw,
        width,
        height,
        base=560,
        colour=HILL_FAR,
        peaks=[(0.14, 74, 0.4), (0.42, 62, 0.36), (0.72, 84, 0.44), (0.94, 70, 0.4)],
    )
    mountain_layers(
        draw,
        width,
        height,
        base=590,
        colour=SNOW,
        peaks=[(0.26, 104, 0.42), (0.62, 86, 0.4), (0.9, 96, 0.44)],
        snow=IVORY,
    )
    mountain_layers(
        draw,
        width,
        height,
        base=615,
        colour=BLUE_DEEP,
        peaks=[(0.08, 126, 0.6), (0.55, 110, 0.7), (0.92, 120, 0.55)],
    )

    draw.rectangle([0, height - 26, width, height], fill=BLUE)
    draw.rectangle([0, height - 34, width, height - 26], fill=GOLD)

    out = OUT / "welcome.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    canvas.convert("RGB").save(out, "PNG")
    return out


def _centre_text(draw: ImageDraw.ImageDraw, width: int, y: int, text: str, font, colour) -> None:
    left, _top, right, _bottom = draw.textbbox((0, 0), text, font=font)
    x = (width - (right - left)) / 2 - left
    draw.text((x, y), text, font=font, fill=colour)


def main() -> int:
    avatar = make_avatar()
    welcome = make_welcome()
    print(f"wrote {avatar}")
    print(f"wrote {welcome}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
