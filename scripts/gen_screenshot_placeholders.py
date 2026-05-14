#!/usr/bin/env python3
"""Regenerate doc/Screenshots/*.png placeholder slides (large text, high contrast)."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "doc" / "Screenshots"

FILES = [
    "AI-review-HITL.png",
    "Deafult-live-page-1.png",
    "Default-live-page-2.png",
    "Final_Fraud_memory_and_audit.png",
    "HITL-Final-Design.png",
    "Paralle-Agents-Result.png",
    "Walk-thorugh-defalut-page.png",
]

FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
]


def _load_fonts() -> tuple[ImageFont.FreeTypeFont | ImageFont.ImageFont, ImageFont.FreeTypeFont | ImageFont.ImageFont]:
    for path in FONT_CANDIDATES:
        p = Path(path)
        if p.is_file():
            return ImageFont.truetype(str(p), 48), ImageFont.truetype(str(p), 30)
    return ImageFont.load_default(size=40), ImageFont.load_default(size=26)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    font_title, font_body = _load_fonts()
    w, h = 1280, 720

    for fn in FILES:
        img = Image.new("RGB", (w, h), (15, 23, 42))
        draw = ImageDraw.Draw(img)
        draw.rectangle([0, 0, w, 10], fill=(56, 189, 248))

        label = fn.replace(".png", "").replace("_", " ")
        lines = [
            "Agentic AI Fraud Investigator",
            label,
            "Placeholder — replace with a real UI capture",
            f"doc/Screenshots/{fn}",
        ]
        y = 100
        colors = [(248, 250, 252), (125, 211, 252), (203, 213, 225), (148, 163, 184)]
        fonts = [font_title, font_title, font_body, font_body]
        for line, fill, font in zip(lines, colors, fonts, strict=True):
            bbox = draw.textbbox((0, 0), line, font=font)
            tw = bbox[2] - bbox[0]
            x = max(32, (w - tw) // 2)
            draw.text((x, y), line, font=font, fill=fill)
            y += (bbox[3] - bbox[1]) + 36

        dest = OUT / fn
        img.save(dest, format="PNG", optimize=True)
        print("wrote", dest.relative_to(ROOT))


if __name__ == "__main__":
    main()
