/*
 * Portrait 32x128 1-bit framebuffer for the Sofle's sideways-mounted SSD1306.
 *
 * Callers draw in portrait coordinates (x 0..31, y 0..127). The buffer itself
 * is laid out as the 128x32 landscape image the panel expects (16 bytes per
 * row, MSB first), so it can be handed to LVGL as-is with no runtime rotation.
 */
#pragma once

#include <stdbool.h>
#include <stdint.h>

#define FB_W 32
#define FB_H 128
#define FB_PANEL_W 128
#define FB_PANEL_H 32
#define FB_STRIDE (FB_PANEL_W / 8)
#define FB_BYTES (FB_STRIDE * FB_PANEL_H)

struct fb_sprite {
    uint8_t w;
    uint8_t h;
    const uint8_t *bits; /* rows packed MSB first, each row padded to a byte */
};

/* Turn the picture upside down, for a panel soldered the other way round. */
void fb_set_flip(bool flip);

void fb_clear(uint8_t *buf);
void fb_px(uint8_t *buf, int x, int y, bool on);
bool fb_get(const uint8_t *buf, int x, int y);
void fb_fill(uint8_t *buf, int x, int y, int w, int h, bool on);

/* Draw the sprite's set bits as lit (on = true) or dark (on = false). Clips. */
void fb_blit(uint8_t *buf, const struct fb_sprite *s, int x, int y, bool on);

/* Replace the whole buffer with a full 32x128 portrait bitmap (4 bytes per row). */
void fb_blit_frame(uint8_t *buf, const uint8_t *frame);
