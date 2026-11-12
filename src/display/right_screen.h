/* Right (peripheral) half: a looping wallpaper with a battery row. Pure C, no Zephyr. */
#pragma once

#include <stdint.h>

#define RIGHT_BATTERY_Y 122

/*
 * scene and frame may be any value; both wrap. battery is a percentage (clamped).
 */
void right_screen_render(uint8_t *buf, uint8_t scene, unsigned frame, uint8_t battery);

/* The wallpaper after (dir > 0) or before (dir < 0) scene, wrapping at both ends. */
uint8_t right_scene_step(uint8_t scene, int dir);
