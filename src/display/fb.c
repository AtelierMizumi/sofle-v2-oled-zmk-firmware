#include "fb.h"

#include <string.h>

static bool flipped;

void fb_set_flip(bool flip) { flipped = flip; }

void fb_clear(uint8_t *buf) { memset(buf, 0, FB_BYTES); }

/*
 * The one place that knows how the panel is mounted. Portrait (x, y) is the
 * panel image turned 90 degrees clockwise; flipped is the same turned 180.
 */
static inline bool locate(int x, int y, unsigned *byte, uint8_t *mask) {
    if (x < 0 || x >= FB_W || y < 0 || y >= FB_H) {
        return false;
    }
    int px = flipped ? y : (FB_PANEL_W - 1 - y);
    int py = flipped ? (FB_PANEL_H - 1 - x) : x;
    *byte = (unsigned)(py * FB_STRIDE + px / 8);
    *mask = (uint8_t)(0x80 >> (px % 8));
    return true;
}

void fb_px(uint8_t *buf, int x, int y, bool on) {
    unsigned byte;
    uint8_t mask;
    if (!locate(x, y, &byte, &mask)) {
        return;
    }
    if (on) {
        buf[byte] |= mask;
    } else {
        buf[byte] &= (uint8_t)~mask;
    }
}

bool fb_get(const uint8_t *buf, int x, int y) {
    unsigned byte;
    uint8_t mask;
    return locate(x, y, &byte, &mask) && (buf[byte] & mask);
}

void fb_fill(uint8_t *buf, int x, int y, int w, int h, bool on) {
    for (int dy = 0; dy < h; dy++) {
        for (int dx = 0; dx < w; dx++) {
            fb_px(buf, x + dx, y + dy, on);
        }
    }
}

void fb_blit(uint8_t *buf, const struct fb_sprite *s, int x, int y, bool on) {
    const int stride = (s->w + 7) / 8;
    for (int dy = 0; dy < s->h; dy++) {
        const uint8_t *row = s->bits + dy * stride;
        for (int dx = 0; dx < s->w; dx++) {
            if (row[dx / 8] & (0x80 >> (dx % 8))) {
                fb_px(buf, x + dx, y + dy, on);
            }
        }
    }
}

void fb_blit_frame(uint8_t *buf, const uint8_t *frame) {
    const struct fb_sprite full = {.w = FB_W, .h = FB_H, .bits = frame};
    fb_clear(buf);
    fb_blit(buf, &full, 0, 0, true);
}
