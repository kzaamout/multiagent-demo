"""Pixel comparison with declared masks.

A pixel differs when any channel differs by more than CHANNEL_TOLERANCE. A capture passes
when the differing share of unmasked pixels is at or below MAX_DIFF_RATIO.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw

from tests.visual.masks import MASKS, Rect

CHANNEL_TOLERANCE = 24
MAX_DIFF_RATIO = 0.005


@dataclass
class Result:
    name: str
    ratio: float
    diff_pixels: int
    compared_pixels: int
    passed: bool
    diff_path: Path | None


def compare(name: str, reference: Path, actual: Path, out_dir: Path) -> Result:
    ref = Image.open(reference).convert("RGB")
    act = Image.open(actual).convert("RGB")
    if ref.size != act.size:
        raise ValueError(f"{name}: size {act.size} differs from reference {ref.size}")
    mask = Image.new("L", ref.size, 255)
    draw = ImageDraw.Draw(mask)
    for rect in MASKS.get(name, []):
        draw.rectangle((rect.x0, rect.y0, rect.x1, rect.y1), fill=0)

    diff = ImageChops.difference(ref, act)
    r, g, b = diff.split()
    over = [band.point(lambda v: 255 if v > CHANNEL_TOLERANCE else 0) for band in (r, g, b)]
    changed = ImageChops.lighter(ImageChops.lighter(over[0], over[1]), over[2])
    changed = ImageChops.multiply(changed, mask)
    diff_pixels = sum(1 for v in changed.getdata() if v)
    compared = sum(1 for v in mask.getdata() if v)
    ratio = diff_pixels / compared if compared else 0.0
    passed = ratio <= MAX_DIFF_RATIO

    out_dir.mkdir(parents=True, exist_ok=True)
    overlay = act.copy()
    red = Image.new("RGB", act.size, (255, 0, 0))
    overlay.paste(red, mask=changed)
    shade = ImageDraw.Draw(overlay)
    for rect in MASKS.get(name, []):
        shade.rectangle((rect.x0, rect.y0, rect.x1, rect.y1), outline=(24, 99, 220), width=3)
    diff_path = out_dir / f"{name}-diff.png"
    overlay.save(diff_path)
    return Result(name, ratio, diff_pixels, compared, passed, diff_path)


__all__ = ["compare", "Result", "Rect"]
