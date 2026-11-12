"""Shared drawing helpers, the wind model and the figure used by the scenes.

Canvas: portrait 32x128, 1-bit. Layer values: 0 untouched, 1 lit, 2 forced dark.
"""
import math
import numpy as np

W, H = 32, 128
FRAMES = 48            # 12 s loop at 4 fps
TAU = 2 * math.pi
GROUND_Y = 118         # everything below GROUND_Y + 1 is reserved for the battery gauge
GAUGE_Y = 122

def put(img, x, y, v=1):
    if 0 <= x < W and 0 <= y < H:
        img[y, x] = v

def line(img, x0, y0, x1, y1, v=1):
    n = max(abs(x1 - x0), abs(y1 - y0), 1)
    for i in range(n + 1):
        put(img, round(x0 + (x1 - x0) * i / n), round(y0 + (y1 - y0) * i / n), v)

def hsh(x, y, s=0):
    return ((x * 73856093) ^ (y * 19349663) ^ (s * 83492791)) % 1000 / 1000.0

def stamp(img, rows, x0, y0):
    """'#' lit, 'o' forced dark, anything else untouched."""
    for dy, row in enumerate(rows):
        for dx, ch in enumerate(row):
            if ch == '#': put(img, x0 + dx, y0 + dy, 1)
            elif ch == 'o': put(img, x0 + dx, y0 + dy, 2)

# ---- wind ------------------------------------------------------------------
def wind(f):
    """Wind over the loop, -1 (hard left) .. +1 (hard right), zero mean and periodic.

    A long calm, a gust to the left, a lull, then a shorter puff back to the right:
    everything in a scene reads this one signal (with its own lag), so hair, skirt,
    branches and petals move together instead of each doing its own thing.
    """
    t = TAU * (f % FRAMES) / FRAMES
    return max(-1.0, min(1.0, -(0.62 * math.sin(t) + 0.42 * math.sin(2 * t + 1.0) + 0.16 * math.sin(3 * t + 2.2))))

_cum = np.cumsum([wind(f) for f in range(FRAMES)])
_cum = _cum - _cum.mean()
_cum = _cum / np.abs(_cum).max()
def drift(f):
    """Where the wind has carried a light particle so far (-1..1, periodic)."""
    f = f % FRAMES
    i = int(math.floor(f)); a = f - i
    return float(_cum[i] * (1 - a) + _cum[(i + 1) % FRAMES] * a)

# ---- figure: girl seen from behind -------------------------------------------
HEAD = [
    "...#####...",
    "..#######..",
    ".#########.",
    ".#########.",
    ".###o#####.",
    ".###o#####.",
    ".###o#####.",
    ".###o##o##.",
    ".###o##o##.",
    ".##o###o##.",
]
# Long hair falling down the back: these rows shear sideways with the wind.
HAIR = [
    "o##o###o##o",
    "o##o###o##o",
    "o##o##o###o",
    "o##o##o###o",
    "o#o###o###o",
    "o#o###o###o",
    "o#o##o####o",
    "o#o##o####o",
    "o####o####o",
    ".o###o###o.",
    ".o#######o.",
    ".o##o#o##o.",
    ".o#o###o#o.",
]
# Shoulders, left arm at her side, back. (The right arm is raised: see _arm.)
TORSO = [
    ".##o#########o##",
    "###o#########o##",
    "###o#########o#.",
    "###o#########o..",
    "##.o#########o..",
    "##.o#########o..",
    "##.o#########o..",
    "##.o#########o..",
    "##.o#########o..",
    "##..o#######o...",
    "##..o#######o...",
    ".#..o#######o...",
    "....o#######o...",
    ".....#######....",
]
# Pleated skirt, symmetrical at rest; rows shear with the wind, the hem most.
SKIRT = [
    "....#########....",
    "...###o###o###...",
    "...###o###o###...",
    "..###o#####o###..",
    "..###o#####o###..",
    ".###o###o###o###.",
    ".###o###o###o###.",
    "###o####o####o###",
    "##.o###.o.###o.##",
]
SKIRT_FLUTTER = "#.#o##.#o#.##o#.#"     # alternate hem while the wind is up
LEGS = [
    "##...##",
    "##...##",
    "##...##",
    "##...##",
    "##...##",
    "##...##",
    "oo...oo",
    "##...##",
    "##...##",
    "##...##",
    "###.###",
]
FIG_H = len(HEAD) + len(TORSO) + len(SKIRT) + len(LEGS)

def _arm(layer, cx, top, f):
    """Right arm held out, palm up; it lifts a pixel now and then."""
    bob = 1 if (f // 8) % 3 == 0 else 0
    sx, sy = cx + 6, top + 11
    ex, ey = cx + 12, top + 7 - bob
    pts = [(round(sx + (ex - sx) * t / 12), round(sy + (ey - sy) * t / 12)) for t in range(13)]
    for x, y in pts[3:]:                                   # dark edge, but not where it joins the shoulder
        for dx, dy in [(0, -1), (1, -1), (0, 2), (-1, 2)]: put(layer, x + dx, y + dy, 2)
    for x, y in pts:
        put(layer, x, y); put(layer, x, y + 1)
    put(layer, ex + 1, ey - 1); put(layer, ex + 2, ey - 1); put(layer, ex + 1, ey)   # open hand

def _loose_strands(layer, cx, top, w):
    """Strands that only lift off once the wind picks up, on the downwind side."""
    strength = abs(w)
    if strength < 0.3:
        return
    sgn = 1 if w > 0 else -1
    edge = cx + sgn * 5
    for ry, reach, lift in [(3, 9, 3.0), (7, 8, 2.0), (12, 6, 1.0)]:
        length = int(round(reach * min(1.0, (strength - 0.2) / 0.6)))
        for s in range(1, length + 1):
            t = s / reach
            x = edge + sgn * s
            y = round(top + ry + 2.5 * t * t - lift * strength * t)
            put(layer, x, y - 1, 2)
            put(layer, x, y, 1)
            if s <= length // 2: put(layer, x, y + 1, 1)

def _winter(layer, cx, top, w, f):
    """Winter scene: a bobble hat, and a scarf end that hangs at her side and swings out with the wind."""
    stamp(layer, [".#.", "###", ".#."], cx - 1, top - 3)          # bobble
    for x in range(cx - 4, cx + 5):
        put(layer, x, top + 3, 2)                                  # hat band
    for x in range(cx - 4, cx + 5):
        put(layer, x, top + 9, 2)                                  # scarf wrapped at the neck
    ang = max(-1.2, min(1.2, w * 1.3))                             # 0 = hanging straight down
    ax, ay = cx + 6, top + 10
    for s in range(10):
        ripple = 0.8 * math.sin(s * 0.9 - f * 1.4) * (s / 9.0) * min(1.0, abs(w) * 2)
        x = round(ax + math.sin(ang) * s + math.cos(ang) * ripple)
        y = round(ay + math.cos(ang) * s - math.sin(ang) * ripple)
        for dx in (-1, 2): put(layer, x + dx, y, 2)
        put(layer, x, y, 1); put(layer, x + 1, y, 1)
    put(layer, x, y + 1, 1)                                        # fringe

def draw_figure(img, f, cx=13, feet_y=GROUND_Y - 1, winter=False):
    """Composite the figure onto img with a one-pixel dark halo so nothing merges into her."""
    top = feet_y - FIG_H + 1
    layer = np.zeros((H, W), np.uint8)
    w_hair, w_skirt = wind(f - 2), wind(f - 1)       # cloth and hair answer a beat late

    stamp(layer, TORSO, cx - 8, top + len(HEAD))
    n = len(HAIR)
    for i, row in enumerate(HAIR):                    # hair hangs straight when calm, swings out in a gust
        stamp(layer, [row], cx - 5 + round(w_hair * 3.2 * (i / (n - 1)) ** 1.6), top + len(HEAD) + i)
    stamp(layer, HEAD, cx - 5, top)
    _loose_strands(layer, cx, top, w_hair)
    if winter:
        _winter(layer, cx, top, wind(f - 1), f)      # hands down in the cold; the scarf does the moving
    else:
        _arm(layer, cx, top, f)

    sy = top + len(HEAD) + len(TORSO)
    m = len(SKIRT)
    for i, row in enumerate(SKIRT):
        if i == m - 1 and abs(w_skirt) > 0.35 and f % 2:
            row = SKIRT_FLUTTER
        stamp(layer, [row], cx - 8 + round(w_skirt * 2.6 * (i / (m - 1)) ** 2), sy + i)
    stamp(layer, LEGS, cx - 3, sy + m)

    solid = layer > 0
    halo = solid.copy()
    for dy, dx in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
        halo |= np.roll(np.roll(solid, dy, 0), dx, 1)
    img[halo] = 0
    img[layer == 1] = 1

def trunk_layer(top=22, lean=1.0):
    """Tree trunk hugging the right edge: lit edge, half-tone bark."""
    img = np.zeros((H, W), np.uint8)
    for y in range(top, GROUND_Y + 1):
        left = int(round(28.0 + lean * math.sin((y - 22) / 26.0) - max(0, y - 112) * 0.4))
        for x in range(left, W):
            if x == left or ((x + y) % 2 == 0 and hsh(x, y // 3, 5) > 0.18):
                put(img, x, y)
    return img

def finish(img):
    img[GROUND_Y + 2:] = 0        # keep the gauge strip clean; the firmware draws there
    return img
