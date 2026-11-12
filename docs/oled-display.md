# Sofle OLED screens

Custom screens for the two SSD1306 OLEDs (128x32, mounted sideways, so they are
used as 32x128 portrait, 1-bit).

| Half | Shows |
| --- | --- |
| Left (central) | Output (USB, or Bluetooth profile and link state), battery of both halves, **active layer**, vertical signature 水海 |
| Right (peripheral) | 48-frame loop at 4 fps: a girl seen from behind under a weeping cherry, petals in the wind. The five blossoms at the bottom are the battery gauge (one per 20 %) |

The layer label is plain text between two rules on BASE and a solid block on
every other layer, so an unexpected layer is visible at a glance.

## Why it is built this way

Earlier attempts (zmk-nice-oled, hammerbeam-slideshow, a port to ZMK `main`)
kept breaking in CI or on the device. The causes were art drawn for another
resolution, runtime rotation through LVGL canvas transforms, and the LVGL 8 to 9
change on ZMK `main`. This design removes each of those:

- **ZMK is pinned to `v0.3.0`** (`config/west.yml`, and the workflow in
  `.github/workflows/build.yml`). That release ships LVGL 8. Moving to a newer
  ZMK means porting `src/display/status_screen.c` to LVGL 9 first.
- **No external display modules.** This repo is itself the ZMK module
  (`zephyr/module.yml`, `Kconfig`, `CMakeLists.txt`).
- **LVGL does almost nothing.** There is one canvas showing one 512-byte
  buffer. All drawing is plain C in `src/display/` writing bits into that
  buffer, already in the panel's orientation. No fonts, no LVGL rotation.
- **Art is generated ahead of time** by `tools/oled-art/` into
  `src/display/generated/`, which is committed. CI needs no Python or fonts.
- **Everything is checked locally before pushing** (see below).

## Layout of the code

```
src/display/fb.[ch]            portrait framebuffer; the only place that knows the rotation
src/display/left_screen.[ch]   left screen layout   (pure C, host-tested)
src/display/right_screen.[ch]  right screen: frame + battery row (pure C, host-tested)
src/display/status_screen.c    ZMK/LVGL glue: events in, canvas out
src/display/generated/         output of tools/oled-art/gen.py - do not edit
tools/oled-art/scene.py        the animation, as code
tools/oled-art/gen.py          fonts, icons, layer names, signature -> C
tests/host/                    host tests and screenshot dump
tools/build-local.sh           local firmware build in the CI container
```

## Changing things

| To change | Edit | Then |
| --- | --- | --- |
| Layer names | `LAYERS` in `tools/oled-art/gen.py` (same order as the `#define`s in `config/sofle.keymap`) | regenerate |
| Signature text or font | `SIGNATURE`, `SIGNATURE_FONT` in `gen.py` | regenerate |
| The animation | `tools/oled-art/scene.py`; `python3 tools/oled-art/scene.py` writes `preview/loop.gif` and `preview/review.png` | regenerate |
| Animation speed | `CONFIG_SOFLE_OLED_ART_FRAME_MS` (default 250) in `config/sofle.conf` | rebuild |
| A screen that is upside down | `CONFIG_SOFLE_OLED_ART_FLIP=y` in `config/sofle_left.conf` or `config/sofle_right.conf` (create the file) | rebuild |
| Back to the stock ZMK screen | remove `CONFIG_ZMK_DISPLAY_STATUS_SCREEN_CUSTOM=y` from `config/sofle.conf` | rebuild |

Regenerate, test, and look at the result:

```sh
python3 tools/oled-art/gen.py      # needs Pillow, numpy, and the IPA Mincho font
tests/host/run.sh --dump           # runs the tests, writes tests/host/out/*.pbm
```

`tests/host/out/left_*.pbm` and `right_*.pbm` are rendered by the same C code
the keyboard runs, so they show exactly what the panel will show.

## Building locally

```sh
tools/build-local.sh               # left + right  -> firmware/sofle_{left,right}.uf2
tools/build-local.sh reset         # settings_reset
```

- Needs Docker. Uses `zmkfirmware/zmk-build-arm:stable`, the image the v0.3.0
  CI workflow uses (about 3 GB, stored under Docker's root on `/`).
- The west workspace (Zephyr, ZMK, HALs; about 2.5 GB) goes to
  `/mnt/500GBext4/zmk-build/sofle-v0.3.0`, on the external ext4 drive. The drive
  must be mounted; set `ZMK_WS=/some/other/dir` to build elsewhere. Do not use
  an NTFS or exFAT drive: west and git need symlinks and POSIX permissions.
- First run downloads the workspace (several minutes). After that a full build
  of both halves takes about one minute.
- If a build behaves strangely after changing `west.yml` or the image, delete
  `$ZMK_WS/build` and run again.

Flash: double-tap reset on a half, copy the matching `.uf2` to the `NICENANO`
drive. Flash both halves.

## Facts worth remembering

- The Sofle shield sets `inversion-on` on the SSD1306. In LVGL terms **black is
  a lit pixel** and white is dark. `status_screen.c` sets the canvas palette
  accordingly; framebuffer bit 1 always means "lit".
- Portrait is the panel image turned 90 degrees clockwise, the direction
  zmk-nice-oled used on this hardware. `fb.c: locate()` is the one function
  that encodes this.
- The right half cannot know the layer or the output; ZMK only gives a
  peripheral its own battery and link state.
- The right battery shown on the left stays at its last value if the right half
  disconnects; ZMK v0.3.0 raises no event for that.
- ZMK blanks both screens after 5 minutes without a key press
  (`CONFIG_ZMK_IDLE_TIMEOUT`), which also protects the OLED from burn-in.

## Not verified on hardware yet

The firmware compiles and the rendering code is tested on the host, but the
first flash still has to confirm: the picture is the right way up on each half,
lit and dark are not swapped, and the animation runs smoothly.
