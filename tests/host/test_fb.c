/* Host tests for the framebuffer and screen composition. Build: tests/host/run.sh */
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "art_assets.h"
#include "fb.h"
#include "left_screen.h"
#include "right_screen.h"

static int lit(const uint8_t *buf) {
    int n = 0;
    for (int i = 0; i < FB_BYTES; i++) n += __builtin_popcount(buf[i]);
    return n;
}

/* Raw panel pixel, independent of fb.c: landscape X 0..127, Y 0..31. */
static int panel(const uint8_t *buf, int X, int Y) {
    return (buf[Y * 16 + X / 8] >> (7 - X % 8)) & 1;
}

static void test_px_rotation(void) {
    uint8_t buf[FB_BYTES];

    /* Default: portrait is the panel image turned 90 degrees clockwise. */
    fb_set_flip(false);
    fb_clear(buf);
    fb_px(buf, 0, 0, true);    /* portrait top-left  -> panel top-right   */
    assert(panel(buf, 127, 0) == 1 && lit(buf) == 1);
    fb_clear(buf);
    fb_px(buf, 31, 127, true); /* portrait bottom-right -> panel bottom-left */
    assert(panel(buf, 0, 31) == 1 && lit(buf) == 1);
    fb_clear(buf);
    fb_px(buf, 5, 100, true);
    assert(panel(buf, 27, 5) == 1 && lit(buf) == 1);
    assert(fb_get(buf, 5, 100) && !fb_get(buf, 5, 101));

    /* Flipped: the same picture turned upside down. */
    fb_set_flip(true);
    fb_clear(buf);
    fb_px(buf, 0, 0, true);
    assert(panel(buf, 0, 31) == 1 && lit(buf) == 1);
    fb_clear(buf);
    fb_px(buf, 5, 100, true);
    assert(panel(buf, 100, 26) == 1 && lit(buf) == 1);
    assert(fb_get(buf, 5, 100));
    fb_set_flip(false);
}

static void test_px_clips_and_clears(void) {
    uint8_t buf[FB_BYTES + 2];
    memset(buf, 0, sizeof(buf));
    buf[FB_BYTES] = 0xA5; /* canary */
    fb_px(buf, -1, 0, true);
    fb_px(buf, 32, 0, true);
    fb_px(buf, 0, -1, true);
    fb_px(buf, 0, 128, true);
    assert(lit(buf) == 0 && buf[FB_BYTES] == 0xA5);
    fb_px(buf, 3, 3, true);
    fb_px(buf, 3, 3, false);
    assert(lit(buf) == 0);
    assert(!fb_get(buf, -1, 0) && !fb_get(buf, 0, 128));
}

static void test_fill_and_blit(void) {
    uint8_t buf[FB_BYTES];
    static const uint8_t bits[] = {0xA0, 0x40}; /* 3x2:  #.#  /  .#.  */
    const struct fb_sprite s = {.w = 3, .h = 2, .bits = bits};

    fb_clear(buf);
    fb_fill(buf, 2, 4, 5, 3, true);
    assert(lit(buf) == 15 && fb_get(buf, 2, 4) && fb_get(buf, 6, 6) && !fb_get(buf, 7, 6));
    fb_fill(buf, 28, 126, 10, 10, true); /* clipped to 4x2 */
    assert(lit(buf) == 15 + 8);

    fb_clear(buf);
    fb_blit(buf, &s, 10, 20, true);
    assert(lit(buf) == 3 && fb_get(buf, 10, 20) && !fb_get(buf, 11, 20) && fb_get(buf, 12, 20) &&
           fb_get(buf, 11, 21));
    fb_blit(buf, &s, 31, 127, true); /* only its top-left pixel is on screen */
    assert(lit(buf) == 4 && fb_get(buf, 31, 127));

    /* Dark blit carves the sprite out of a lit area and touches nothing else. */
    fb_clear(buf);
    fb_fill(buf, 0, 0, 8, 8, true);
    fb_blit(buf, &s, 1, 1, false);
    assert(lit(buf) == 64 - 3 && !fb_get(buf, 1, 1) && fb_get(buf, 2, 1));
}

static void test_blit_frame_matches_generator(void) {
    /* The generator stores what it drew; the firmware path must reproduce it pixel for pixel. */
    uint8_t buf[FB_BYTES];
    for (int flip = 0; flip < 2; flip++) {
        fb_set_flip(flip);
        for (unsigned s = 0; s < ART_SCENE_COUNT; s++) {
            assert(art_scenes[s].frame_count > 0);
            for (unsigned f = 0; f < art_scenes[s].frame_count; f += 7) {
                const uint8_t *src = art_scenes[s].frames[f];
                memset(buf, 0xFF, sizeof(buf));
                fb_blit_frame(buf, src);
                for (int y = 0; y < FB_H; y++)
                    for (int x = 0; x < FB_W; x++)
                        assert(fb_get(buf, x, y) == ((src[y * 4 + x / 8] >> (7 - x % 8)) & 1));
            }
        }
    }
    fb_set_flip(false);
}

static int region_lit(const uint8_t *buf, int y0, int y1) {
    int n = 0;
    for (int y = y0; y < y1; y++)
        for (int x = 0; x < FB_W; x++) n += fb_get(buf, x, y);
    return n;
}

static void test_left_screen(void) {
    uint8_t a[FB_BYTES], b[FB_BYTES];
    struct left_state st = {.layer = 0, .usb = true, .battery = 80, .peripheral_battery = 40};

    left_screen_render(a, &st);
    assert(region_lit(a, LEFT_SIGNATURE_Y, FB_H) > 200); /* signature is present */

    /* Every layer draws a different label, and only the layer area changes. */
    for (uint8_t l = 1; l < ART_LAYER_COUNT; l++) {
        st.layer = l;
        left_screen_render(b, &st);
        int diff = 0;
        for (int y = 0; y < FB_H; y++)
            for (int x = 0; x < FB_W; x++)
                if (fb_get(a, x, y) != fb_get(b, x, y)) {
                    diff++;
                    assert(y >= LEFT_LAYER_Y && y < LEFT_SIGNATURE_Y);
                }
        assert(diff > 20);
    }
    /* A layer the art does not know about must not read out of bounds. */
    st.layer = 200;
    left_screen_render(b, &st);
    st.layer = 0;

    /* Battery bars grow with charge. */
    st.battery = 10;
    left_screen_render(a, &st);
    st.battery = 100;
    left_screen_render(b, &st);
    assert(region_lit(b, LEFT_BATTERY_Y, LEFT_BATTERY_Y + 8) > region_lit(a, LEFT_BATTERY_Y, LEFT_BATTERY_Y + 8) + 30);
    st.battery = 250; /* garbage in: clamp, do not overflow the bar */
    left_screen_render(a, &st);
    assert(memcmp(a, b, FB_BYTES) == 0);

    /* Unknown peripheral battery is drawn differently from an empty one. */
    st.peripheral_battery = LEFT_BATTERY_UNKNOWN;
    left_screen_render(a, &st);
    st.peripheral_battery = 0;
    left_screen_render(b, &st);
    assert(memcmp(a, b, FB_BYTES) != 0);

    /* Output row: USB vs each BLE profile vs connection state are all distinct. */
    st.usb = false;
    st.ble_connected = true;
    st.profile = 0;
    left_screen_render(a, &st);
    st.profile = 3;
    left_screen_render(b, &st);
    assert(memcmp(a, b, FB_BYTES) != 0);
    st.ble_connected = false;
    left_screen_render(a, &st);
    assert(memcmp(a, b, FB_BYTES) != 0);
}

static void test_right_screen(void) {
    uint8_t a[FB_BYTES], b[FB_BYTES];

    assert(ART_SCENE_COUNT >= 2); /* there is something to switch between */

    for (uint8_t s = 0; s < ART_SCENE_COUNT; s++) {
        const unsigned n = art_scenes[s].frame_count;

        right_screen_render(a, s, 0, 100);
        right_screen_render(b, s, 1, 100);
        assert(memcmp(a, b, FB_BYTES) != 0); /* it animates */
        right_screen_render(b, s, n, 100);
        assert(memcmp(a, b, FB_BYTES) == 0); /* and loops instead of running off the table */

        /* Battery gauge: more charge, more lit pixels in the bottom strip only. */
        right_screen_render(a, s, 5, 0);
        right_screen_render(b, s, 5, 100);
        assert(region_lit(b, RIGHT_BATTERY_Y, FB_H) > region_lit(a, RIGHT_BATTERY_Y, FB_H));
        assert(region_lit(a, 0, RIGHT_BATTERY_Y) == region_lit(b, 0, RIGHT_BATTERY_Y));
        right_screen_render(a, s, 5, 255); /* clamp */
        assert(memcmp(a, b, FB_BYTES) == 0);
    }

    /* Wallpapers really are different pictures. */
    right_screen_render(a, 0, 0, 50);
    right_screen_render(b, 1, 0, 50);
    assert(memcmp(a, b, FB_BYTES) != 0);

    /* A stale or corrupt saved index must not read out of bounds: it wraps. */
    right_screen_render(b, ART_SCENE_COUNT, 0, 50);
    assert(memcmp(a, b, FB_BYTES) == 0);
    right_screen_render(b, 255, 0, 50);
}

static void test_scene_step(void) {
    /* Next and previous walk every wallpaper and wrap at both ends. */
    assert(right_scene_step(0, 1) == 1);
    assert(right_scene_step(ART_SCENE_COUNT - 1, 1) == 0);
    assert(right_scene_step(0, -1) == ART_SCENE_COUNT - 1);
    assert(right_scene_step(1, -1) == 0);
    uint8_t s = 0;
    for (unsigned i = 0; i < ART_SCENE_COUNT; i++) s = right_scene_step(s, 1);
    assert(s == 0);
    assert(right_scene_step(250, 1) < ART_SCENE_COUNT); /* garbage in, valid index out */
    assert(right_scene_step(250, -1) < ART_SCENE_COUNT);
}

static void dump(const char *path, const uint8_t *buf) {
    FILE *f = fopen(path, "w");
    if (!f) return;
    fprintf(f, "P1\n%d %d\n", FB_W, FB_H);
    for (int y = 0; y < FB_H; y++) {
        for (int x = 0; x < FB_W; x++) fputc(fb_get(buf, x, y) ? '1' : '0', f);
        fputc('\n', f);
    }
    fclose(f);
}

int main(int argc, char **argv) {
    test_px_rotation();
    test_px_clips_and_clears();
    test_fill_and_blit();
    test_blit_frame_matches_generator();
    test_left_screen();
    test_right_screen();
    test_scene_step();
    puts("all host tests passed");

    if (argc > 1) { /* optional: dump screens as PBM for eyeballing */
        uint8_t buf[FB_BYTES];
        char path[256];
        struct left_state shots[] = {
            {.layer = 0, .usb = true, .battery = 100, .peripheral_battery = 70},
            {.layer = 1, .usb = false, .profile = 0, .ble_connected = true, .battery = 55, .peripheral_battery = 30},
            {.layer = 2, .usb = false, .profile = 2, .ble_connected = false, .battery = 20, .peripheral_battery = LEFT_BATTERY_UNKNOWN},
            {.layer = 3, .usb = true, .battery = 5, .peripheral_battery = 100},
            {.layer = 4, .usb = true, .battery = 90, .peripheral_battery = 90},
            {.layer = 5, .usb = false, .profile = 4, .ble_connected = true, .battery = 60, .peripheral_battery = 10},
        };
        for (unsigned i = 0; i < sizeof(shots) / sizeof(shots[0]); i++) {
            left_screen_render(buf, &shots[i]);
            snprintf(path, sizeof(path), "%s/left_%u.pbm", argv[1], i);
            dump(path, buf);
        }
        for (unsigned sc = 0; sc < ART_SCENE_COUNT; sc++) {
            for (unsigned f = 0; f < art_scenes[sc].frame_count; f += 6) {
                right_screen_render(buf, sc, f, (f * 100) / art_scenes[sc].frame_count);
                snprintf(path, sizeof(path), "%s/right_%u_%02u.pbm", argv[1], sc, f);
                dump(path, buf);
            }
        }
    }
    return 0;
}
