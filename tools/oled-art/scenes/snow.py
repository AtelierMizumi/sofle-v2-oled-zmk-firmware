"""Winter night: bare boughs under snow, a crescent moon, slow snowfall, a bobble hat and a scarf in the wind."""
import math, random
import numpy as np
from .common import *

NAME = "snow"
GAUGE_ON  = ["#.#.#", ".###.", "#####", ".###.", "#.#.#"]
GAUGE_OFF = [".....", "..#..", ".#.#.", "..#..", "....."]

def _boughs():
    img = np.zeros((H, W), np.uint8)
    rnd = random.Random(5)
    segs = []
    def grow(x, y, ang, length, depth):
        x1 = x + math.cos(ang) * length; y1 = y - math.sin(ang) * length
        segs.append((x, y, x1, y1, depth))
        if depth < 3:
            for da in (rnd.uniform(0.35, 0.7), -rnd.uniform(0.3, 0.65)):
                grow(x1, y1, ang + da, length * rnd.uniform(0.62, 0.78), depth + 1)
    grow(29, 46, 2.5, 13, 0)
    grow(29, 30, 2.2, 12, 0)
    grow(30, 18, 2.0, 11, 1)
    for x0, y0, x1, y1, depth in segs:
        line(img, round(x0), round(y0), round(x1), round(y1))
        if depth == 0: line(img, round(x0), round(y0) + 1, round(x1), round(y1) + 1)
    # snow lying on top of every bough: a dark gap, then a lit cap
    snow = np.zeros((H, W), np.uint8)
    for x0, y0, x1, y1, depth in segs:
        n = int(max(abs(x1 - x0), abs(y1 - y0), 1))
        for i in range(n + 1):
            x = round(x0 + (x1 - x0) * i / n); y = round(y0 + (y1 - y0) * i / n)
            if hsh(x, y, 3) > 0.25 and abs(x1 - x0) > abs(y1 - y0) * 0.5:
                put(snow, x, y - 2);
                if hsh(x, y, 4) > 0.5: put(snow, x, y - 3)
    return img | snow

def _moon():
    img = np.zeros((H, W), np.uint8)
    cx, cy, r = 7, 9, 6
    for y in range(cy - r, cy + r + 1):
        for x in range(cx - r, cx + r + 1):
            if (x - cx) ** 2 + (y - cy) ** 2 <= r * r and (x - cx - 3) ** 2 + (y - cy + 1) ** 2 > (r - 0.5) ** 2:
                put(img, x, y)
    return img

def _ground():
    img = np.zeros((H, W), np.uint8)
    for x in range(W):
        top = GROUND_Y - 1 + round(1.2 * math.sin(x / 5.0 + 1.0))
        put(img, x, top)                                  # crest of the drift
        for y in range(top + 1, GROUND_Y + 2):
            if (x + y) % 2 == 0: put(img, x, y)           # soft half-tone snow
    return img

def _flakes():
    rnd = random.Random(8)
    return [dict(x=rnd.uniform(1, 27), phase=rnd.randrange(48), period=[48, 48, 48, 24][i % 4],
                 carry=rnd.uniform(3, 7), wob=rnd.uniform(0, TAU), big=(i % 5 == 0)) for i in range(20)]
FLAKES = _flakes()
def snowfall(img, f):
    for p in FLAKES:
        t = ((f + p["phase"]) % p["period"]) / p["period"]
        y = round(2 + t * (GROUND_Y - 4))
        x = round(p["x"] + p["carry"] * drift(f - 2) + 1.5 * math.sin(t * TAU * 2 + p["wob"]))
        put(img, x, y)
        if p["big"] and (f // 3) % 2 == 0:               # the near flakes glint
            for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]: put(img, x + dx, y + dy)

STARS = [(18, 4), (24, 12), (3, 22), (14, 15), (21, 52), (4, 44), (10, 60), (25, 66)]
def stars(img, f):
    for i, (x, y) in enumerate(STARS):
        if (f + i * 7) % 16 < 12: put(img, x, y)

TRUNK = trunk_layer(top=14)
BOUGHS = _boughs()
MOON = _moon()
GROUND = _ground()

def render(f):
    img = np.zeros((H, W), np.uint8)
    stars(img, f)
    img |= MOON
    snowfall(img, f)
    img[BOUGHS == 1] = 1
    img |= TRUNK
    img |= GROUND
    draw_figure(img, f, feet_y=GROUND_Y - 2, winter=True)
    return finish(img)

def frames():
    return [render(f) for f in range(FRAMES)]
