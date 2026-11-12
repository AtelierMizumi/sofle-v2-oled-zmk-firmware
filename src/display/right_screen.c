#include "right_screen.h"

#include "art_assets.h"
#include "fb.h"

#define GAUGE_STEPS 5

void right_screen_render(uint8_t *buf, uint8_t scene, unsigned frame, uint8_t battery) {
    const struct art_scene *s = &art_scenes[scene % ART_SCENE_COUNT];

    fb_blit_frame(buf, s->frames[frame % s->frame_count]);

    if (battery > 100) {
        battery = 100;
    }
    /* One icon per 20 %; the first one stays lit until the battery is empty. */
    for (int i = 0; i < GAUGE_STEPS; i++) {
        const struct fb_sprite *icon = battery > i * (100 / GAUGE_STEPS) ? &s->gauge_on : &s->gauge_off;
        fb_blit(buf, icon, 1 + i * 6, RIGHT_BATTERY_Y, true);
    }
}

uint8_t right_scene_step(uint8_t scene, int dir) {
    const int n = ART_SCENE_COUNT;
    return (uint8_t)(((scene % n) + (dir < 0 ? n - 1 : 1)) % n);
}
