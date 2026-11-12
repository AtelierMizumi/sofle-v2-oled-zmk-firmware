"""Moon over the sea (水海): twinkling stars, a shooting star, moonlight breaking on the swell."""
import math
import numpy as np
from .common import *

NAME = "sea"
GAUGE_ON  = ["..#..", "..#..", "#####", "..#..", "..#.."]
GAUGE_OFF = [".....", ".....", "..#..", ".....", "....."]

HORIZON = 72
MOON = (16, 30, 11)

def moon(img):
    cx, cy, r = MOON
    craters = [(-3, -3, 4), (5, 4, 2), (6, -4, 1), (-5, 6, 1)]
    for y in range(cy - r, cy + r + 1):
        for x in range(cx - r, cx + r + 1):
            d2 = (x - cx) ** 2 + (y - cy) ** 2
            if d2 > r * r + 2: continue
            lit = True
            for ox, oy, cr in craters:                    # maria: half-tone patches
                if (x - cx - ox) ** 2 + (y - cy - oy) ** 2 <= cr * cr and (x + y) % 2 == 0:
                    lit = False
            put(img, x, y, 1 if lit else 0)

STARS = [(3, 5), (27, 3), (9, 12), (22, 14), (1, 22), (30, 24), (5, 40), (28, 44),
         (2, 52), (25, 58), (12, 62), (30, 64), (7, 66), (19, 6), (14, 50)]
def stars(img, f):
    for i, (x, y) in enumerate(STARS):
        k = (f + i * 5) % 24
        if k < 17: put(img, x, y)
        if i % 4 == 0 and k in (6, 7, 8):                 # a few of them flare
            for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]: put(img, x + dx, y + dy)

def shooting_star(img, f):
    k = f - 31
    if 0 <= k < 6:
        for s in range(5):
            put(img, 29 - 3 * k - s, 46 + 2 * k + (s * 2) // 3)

def boat(img, f):
    bob = 1 if math.sin(TAU * f / 24) > 0.3 else 0
    x, y = 4, HORIZON - 1 + bob
    for dx in range(5): put(img, x + dx, y)               # hull
    put(img, x + 1, y + 1); put(img, x + 2, y + 1); put(img, x + 3, y + 1)
    for i in range(5):                                    # sail
        for dx in range(i // 2 + 1): put(img, x + 2 + dx, y - 6 + i)

def sea(img, f):
    for x in range(W):
        if not (3 <= x <= 9): put(img, x, HORIZON)        # horizon, broken behind the boat
    for y in range(HORIZON + 2, GROUND_Y + 2):
        depth = y - HORIZON
        if depth % 2: continue                            # dark troughs between the lit crests
        row = depth // 2
        half = 1.5 + depth * 0.2                          # the glitter path widens towards the viewer
        speed = 1 + row % 3                               # crests slide at different rates, both ways
        phase = TAU * f * speed / 48 * (1 if row % 2 else -1) + hsh(row, 7, 1) * TAU
        k = 1.25 - depth * 0.012                          # longer dashes closer to the viewer
        edge = half + 1.5 * math.sin(row * 1.3 + TAU * f / 16)
        for x in range(W):
            wave = math.sin(x * k + phase)
            if abs(x - 15.5) <= edge:
                if wave > -0.35: put(img, x, y)           # moonlight on the crests
            elif wave > 0.86 and row % 2 == 0:
                put(img, x, y)                            # stray glints on the dark swell

def render(f):
    img = np.zeros((H, W), np.uint8)
    stars(img, f)
    shooting_star(img, f)
    moon(img)
    sea(img, f)
    boat(img, f)
    return finish(img)

def frames():
    return [render(f) for f in range(FRAMES)]
