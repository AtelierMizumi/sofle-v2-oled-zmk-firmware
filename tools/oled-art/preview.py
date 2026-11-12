#!/usr/bin/env python3
"""Render previews of every wallpaper: preview/<name>.gif and preview/review.png."""
from pathlib import Path
import numpy as np
from PIL import Image
from scenes import SCENES
from scenes.common import W, H, GAUGE_Y, stamp

OUT = Path(__file__).parent / "preview"

def with_gauge(img, scene, level=70):
    img = img.copy()
    for i in range(5):                                   # same rule as right_screen.c
        stamp(img, scene.GAUGE_ON if level > i * 20 else scene.GAUGE_OFF, 1 + i * 6, GAUGE_Y)
    return (img == 1).astype(np.uint8)

def png(img, scale):
    return Image.fromarray(img * 255).convert("L").resize((W * scale, H * scale), Image.NEAREST)

if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    pick = [0, 8, 16, 24, 32, 40]
    rows = []
    for scene in SCENES:
        fs = [with_gauge(f, scene) for f in scene.frames()]
        gif = [png(f, 5).convert("P") for f in fs]
        gif[0].save(OUT / f"{scene.NAME}.gif", save_all=True, append_images=gif[1:], duration=250, loop=0)
        row = Image.new("L", (len(pick) * (W * 4 + 8) + 8, H * 4 + 16), 60)
        for i, f in enumerate(pick):
            row.paste(png(fs[f], 4), (8 + i * (W * 4 + 8), 8))
        rows.append(row)
        print(scene.NAME, "lit px frame 0:", int(fs[0].sum()))
    sheet = Image.new("L", (sum(r.width for r in rows), rows[0].height), 60)
    x = 0
    for r in rows:
        sheet.paste(r, (x, 0)); x += r.width
    sheet.save(OUT / "review.png")
