"""Weeping cherry in spring: sprays sway, petals ride the wind, a girl holds out her hand."""
import math, random
import numpy as np
from .common import *

NAME = "sakura"
GAUGE_ON  = ["..#..", ".###.", "##.##", ".###.", "..#.."]
GAUGE_OFF = [".....", "..#..", ".#.#.", "..#..", "....."]

CLUMPS = [(5, 3, 9, 6), (19, 2, 10, 6), (29, 8, 6, 8), (12, 10, 8, 5),
          (2, 15, 5, 5), (22, 16, 7, 5), (9, 21, 6, 4), (29, 24, 5, 5), (17, 26, 5, 3)]

def _in_clump(x, y, ci):
    cx, cy, rx, ry = CLUMPS[ci]
    return ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 + 0.22 * (hsh(x // 2, y // 2, ci) - 0.5) <= 1.0

def canopy(img, shimmer):
    """Blossom masses, back to front: sun-lit top, half-tone middle, shaded underside."""
    for ci, (cx, cy, rx, ry) in enumerate(CLUMPS):
        for y in range(max(0, cy - ry - 1), cy + ry + 2):
            for x in range(max(0, cx - rx - 1), min(W, cx + rx + 2)):
                if not _in_clump(x, y, ci): continue
                v = (y - (cy - ry)) / (2.0 * ry)
                if v < 0.5:   lit = hsh(x, y, ci + shimmer) > 0.07
                elif v < 0.8: lit = (x + y) % 2 == 0
                else:         lit = (x + y) % 2 == 0 and x % 4 < 2
                put(img, x, y, 1 if lit else 0)

SPRAYS = [(3, 19, 30, 0), (8, 24, 22, 2), (13, 27, 31, 1), (19, 28, 20, 3), (23, 21, 34, 2), (26, 28, 16, 4)]
def sprays(img, f):
    for x0, y0, length, lag in SPRAYS:
        w = wind(f - 2 - lag)                       # the gust reaches each spray a little later
        for s in range(length):
            t = s / length
            x = round(x0 + 4.5 * t * t * w + 0.6 * t * math.sin(TAU * f / 12 + x0))
            y = y0 + s
            k = (s + x0) % 6
            if k == 0:   put(img, x, y); put(img, x + 1, y); put(img, x, y + 1); put(img, x + 1, y + 1)
            elif k == 3: put(img, x, y); put(img, x - 1, y + 1)
            elif k in (2, 5): put(img, x, y)

def _petals():
    rnd = random.Random(21)
    return [dict(x=rnd.uniform(3, 25), phase=rnd.randrange(48), period=[48, 48, 24][i % 3],
                 carry=rnd.uniform(4, 9), wob=rnd.uniform(0, TAU), kind=i % 3) for i in range(12)]
PETALS = _petals()
SHAPES = {0: [[(0, 0)], [(0, 0)]],
          1: [[(0, 0), (1, 0)], [(0, 0), (0, 1)]],
          2: [[(0, 0), (1, 0), (1, 1)], [(0, 0), (0, 1), (-1, 1)]]}
def petals(img, f):
    for p in PETALS:
        t = ((f + p["phase"]) % p["period"]) / p["period"]
        y = round(44 + t * (GROUND_Y - 45))
        x = round(p["x"] + p["carry"] * drift(f - 1) + 1.2 * math.sin(t * TAU * 3 + p["wob"]))
        if x >= 27: continue
        for dx, dy in SHAPES[p["kind"]][(f // 2 + p["kind"]) % 2]:
            put(img, x + dx, y + dy)

SPARK = [(6, 64, 0), (18, 58, 11), (12, 68, 23), (23, 66, 35), (3, 100, 41)]
def sparkles(img, f):
    for x, y, start in SPARK:
        k = (f - start) % FRAMES
        if k in (0, 4): put(img, x, y)
        elif k in (1, 3):
            for dx, dy in [(0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)]: put(img, x + dx, y + dy)
        elif k == 2:
            for d in range(-2, 3): put(img, x + d, y); put(img, x, y + d)

def _ground():
    img = np.zeros((H, W), np.uint8)
    for x in range(W):
        if x % 9 != 4: put(img, x, GROUND_Y + (1 if 9 < x < 20 else 0))
    for x, h in [(0, 2), (1, 1), (23, 2), (24, 1), (5, 1)]:
        for k in range(1, h + 1): put(img, x, GROUND_Y - k)
    return img

TRUNK = trunk_layer()
line(TRUNK, 28, 34, 22, 28); line(TRUNK, 22, 28, 15, 27); line(TRUNK, 28, 46, 23, 41)
GROUND = _ground()

def render(f):
    img = np.zeros((H, W), np.uint8)
    img |= GROUND
    img |= TRUNK
    sprays(img, f)
    petals(img, f)
    sparkles(img, f)
    canopy(img, f // 6)
    draw_figure(img, f)
    return finish(img)

def frames():
    return [render(f) for f in range(FRAMES)]
