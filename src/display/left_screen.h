/* Left (central) half: compact status on top, signature below. Pure C, no Zephyr. */
#pragma once

#include <stdbool.h>
#include <stdint.h>

#define LEFT_BATTERY_UNKNOWN 255

/* Layout rows (portrait y). */
#define LEFT_OUTPUT_Y 0
#define LEFT_BATTERY_Y 13
#define LEFT_PERIPHERAL_BATTERY_Y 23
#define LEFT_LAYER_Y 35
#define LEFT_SIGNATURE_Y 67

struct left_state {
    uint8_t layer;              /* highest active keymap layer index */
    bool usb;                   /* keystrokes are going out over USB */
    uint8_t profile;            /* selected BLE profile, 0-based */
    bool ble_connected;         /* selected profile has a live connection */
    uint8_t battery;            /* this half, percent */
    uint8_t peripheral_battery; /* right half, percent, or LEFT_BATTERY_UNKNOWN */
};

void left_screen_render(uint8_t *buf, const struct left_state *st);
