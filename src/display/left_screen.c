#include "left_screen.h"

#include "art_assets.h"
#include "fb.h"

#define BAR_X 8
#define BAR_W 20 /* outline, plus a 2 px terminal nub to its right */
#define BAR_H 8

static void draw_output(uint8_t *buf, const struct left_state *st) {
    if (st->usb) {
        fb_blit(buf, &art_usb, (FB_W - art_usb.w) / 2, LEFT_OUTPUT_Y + 1, true);
        return;
    }
    fb_blit(buf, &art_bt, 3, LEFT_OUTPUT_Y, true);
    if (st->profile < ART_PROFILE_COUNT) {
        fb_blit(buf, art_digits[st->profile], 14, LEFT_OUTPUT_Y + 1, true);
    }
    fb_blit(buf, st->ble_connected ? &art_link_on : &art_link_off, 24, LEFT_OUTPUT_Y + 3, true);
}

static void draw_battery(uint8_t *buf, int y, const struct fb_sprite *label, uint8_t level) {
    fb_blit(buf, label, 1, y, true);

    fb_fill(buf, BAR_X, y, BAR_W, BAR_H, true);
    fb_fill(buf, BAR_X + 1, y + 1, BAR_W - 2, BAR_H - 2, false);
    fb_fill(buf, BAR_X + BAR_W, y + 2, 2, BAR_H - 4, true);

    if (level == LEFT_BATTERY_UNKNOWN) {
        fb_blit(buf, &art_cross, BAR_X + (BAR_W - art_cross.w) / 2, y + 1 + (BAR_H - 2 - art_cross.h) / 2,
                true);
        return;
    }
    if (level > 100) {
        level = 100;
    }
    const int inner = BAR_W - 4;
    const int fill = (level * inner + 50) / 100;
    fb_fill(buf, BAR_X + 2, y + 2, fill, BAR_H - 4, true);
}

static void draw_layer(uint8_t *buf, uint8_t layer) {
    const struct fb_sprite *name = layer < ART_LAYER_COUNT ? art_layers[layer] : &art_layer_unknown;
    const int box_y = LEFT_LAYER_Y;
    const int box_h = 22;
    const int text_x = (FB_W - name->w) / 2;
    const int text_y = box_y + (box_h - name->h) / 2;

    if (layer == 0) {
        /* Home layer: quiet. Text between two rules. */
        fb_fill(buf, 0, box_y, FB_W, 1, true);
        fb_fill(buf, 0, box_y + box_h - 1, FB_W, 1, true);
        fb_blit(buf, name, text_x, text_y, true);
    } else {
        /* Any other layer: a solid block, so it is obvious at a glance. */
        fb_fill(buf, 0, box_y, FB_W, box_h, true);
        fb_px(buf, 0, box_y, false);
        fb_px(buf, FB_W - 1, box_y, false);
        fb_px(buf, 0, box_y + box_h - 1, false);
        fb_px(buf, FB_W - 1, box_y + box_h - 1, false);
        fb_blit(buf, name, text_x, text_y, false);
    }

    /* One tick per layer; the active one is a bar. */
    const int ticks_y = box_y + box_h + 3;
    const int pitch = FB_W / ART_LAYER_COUNT;
    for (int i = 0; i < ART_LAYER_COUNT; i++) {
        const int x = i * pitch + (pitch - 3) / 2;
        if (i == layer) {
            fb_fill(buf, x - 1, ticks_y, 5, 3, true);
        } else {
            fb_px(buf, x + 1, ticks_y + 1, true);
        }
    }
}

void left_screen_render(uint8_t *buf, const struct left_state *st) {
    fb_clear(buf);
    draw_output(buf, st);
    draw_battery(buf, LEFT_BATTERY_Y, &art_letter_l, st->battery);
    draw_battery(buf, LEFT_PERIPHERAL_BATTERY_Y, &art_letter_r, st->peripheral_battery);
    draw_layer(buf, st->layer);
    fb_blit(buf, &art_signature, 0, LEFT_SIGNATURE_Y, true);
}
