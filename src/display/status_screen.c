/*
 * ZMK glue for the custom Sofle OLED screens.
 *
 * All drawing lives in left_screen.c / right_screen.c, which render into a
 * 1-bit buffer that is already in the panel's orientation. This file only
 * owns one LVGL canvas showing that buffer and forwards ZMK state to it.
 */
#include <zephyr/kernel.h>
#include <lvgl.h>

#include <zmk/battery.h>
#include <zmk/display.h>
#include <zmk/event_manager.h>
#include <zmk/events/battery_state_changed.h>

#include "fb.h"
#include "oled_art.h"

#define IS_CENTRAL (!IS_ENABLED(CONFIG_ZMK_SPLIT) || IS_ENABLED(CONFIG_ZMK_SPLIT_ROLE_CENTRAL))

/* Indexed 1-bit canvas: 8 bytes of palette, then FB_BYTES of pixels. */
static uint8_t canvas_buf[LV_CANVAS_BUF_SIZE_INDEXED_1BIT(FB_PANEL_W, FB_PANEL_H)];
#define PIXELS (canvas_buf + 8)
BUILD_ASSERT(sizeof(canvas_buf) >= 8 + FB_BYTES, "canvas buffer too small for the framebuffer");

static lv_obj_t *canvas;

static void present(void) {
    if (canvas != NULL) {
        lv_obj_invalidate(canvas);
    }
}

#if IS_CENTRAL

#include <zmk/endpoints.h>
#include <zmk/events/endpoint_changed.h>
#include <zmk/events/layer_state_changed.h>
#include <zmk/keymap.h>

#if IS_ENABLED(CONFIG_ZMK_BLE)
#include <zmk/ble.h>
#include <zmk/events/ble_active_profile_changed.h>
#endif

#include "left_screen.h"

static uint8_t peripheral_battery = LEFT_BATTERY_UNKNOWN;

static struct left_state left_get_state(const zmk_event_t *eh) {
#if IS_ENABLED(CONFIG_ZMK_SPLIT_BLE_CENTRAL_BATTERY_LEVEL_FETCHING)
    const struct zmk_peripheral_battery_state_changed *pev =
        eh != NULL ? as_zmk_peripheral_battery_state_changed(eh) : NULL;
    if (pev != NULL) {
        peripheral_battery = pev->state_of_charge;
    }
#endif
    return (struct left_state){
        .layer = zmk_keymap_highest_layer_active(),
        .usb = zmk_endpoints_selected().transport == ZMK_TRANSPORT_USB,
#if IS_ENABLED(CONFIG_ZMK_BLE)
        .profile = (uint8_t)zmk_ble_active_profile_index(),
        .ble_connected = zmk_ble_active_profile_is_connected(),
#endif
        .battery = zmk_battery_state_of_charge(),
        .peripheral_battery = peripheral_battery,
    };
}

static void left_update(struct left_state state) {
    left_screen_render(PIXELS, &state);
    present();
}

ZMK_DISPLAY_WIDGET_LISTENER(sofle_left_screen, struct left_state, left_update, left_get_state)
ZMK_SUBSCRIPTION(sofle_left_screen, zmk_layer_state_changed);
ZMK_SUBSCRIPTION(sofle_left_screen, zmk_endpoint_changed);
ZMK_SUBSCRIPTION(sofle_left_screen, zmk_battery_state_changed);
#if IS_ENABLED(CONFIG_ZMK_BLE)
ZMK_SUBSCRIPTION(sofle_left_screen, zmk_ble_active_profile_changed);
#endif
#if IS_ENABLED(CONFIG_ZMK_SPLIT_BLE_CENTRAL_BATTERY_LEVEL_FETCHING)
ZMK_SUBSCRIPTION(sofle_left_screen, zmk_peripheral_battery_state_changed);
#endif

static void screen_start(void) { sofle_left_screen_init(); }

void sofle_oled_art_step(int dir) { ARG_UNUSED(dir); /* the wallpapers are on the other half */ }

#else /* peripheral */

#include <zephyr/settings/settings.h>
#include <zephyr/sys/atomic.h>

#include "right_screen.h"

static unsigned frame;
static uint8_t battery;
static atomic_t scene; /* written from the behavior (system work queue), read while drawing */

static void right_draw(void) {
    right_screen_render(PIXELS, (uint8_t)atomic_get(&scene), frame, battery);
    present();
}

static void right_tick(lv_timer_t *timer) {
    ARG_UNUSED(timer);
    frame++;
    right_draw();
}

static uint8_t right_get_state(const zmk_event_t *eh) {
    ARG_UNUSED(eh);
    return zmk_battery_state_of_charge();
}

static void right_update(uint8_t level) {
    battery = level;
    right_draw();
}

ZMK_DISPLAY_WIDGET_LISTENER(sofle_right_screen, uint8_t, right_update, right_get_state)
ZMK_SUBSCRIPTION(sofle_right_screen, zmk_battery_state_changed);

#if IS_ENABLED(CONFIG_SETTINGS)
#define SCENE_SETTING_TREE "sofle_art"
#define SCENE_SETTING SCENE_SETTING_TREE "/scene"

static int scene_settings_set(const char *name, size_t len, settings_read_cb read_cb, void *cb_arg) {
    uint8_t saved;
    if (settings_name_steq(name, "scene", NULL) && len == sizeof(saved) &&
        read_cb(cb_arg, &saved, sizeof(saved)) == sizeof(saved)) {
        atomic_set(&scene, saved);
        return 0;
    }
    return -ENOENT;
}
SETTINGS_STATIC_HANDLER_DEFINE(sofle_art, SCENE_SETTING_TREE, NULL, scene_settings_set, NULL, NULL);

static void scene_save_cb(struct k_work *work) {
    ARG_UNUSED(work);
    const uint8_t value = (uint8_t)atomic_get(&scene);
    settings_save_one(SCENE_SETTING, &value, sizeof(value));
}
/* Flipping through several wallpapers in a row costs one flash write, not one per press. */
static K_WORK_DELAYABLE_DEFINE(scene_save_work, scene_save_cb);
#endif /* CONFIG_SETTINGS */

void sofle_oled_art_step(int dir) {
    atomic_set(&scene, right_scene_step((uint8_t)atomic_get(&scene), dir));
    /* The next animation tick (at most one frame away) shows it. */
#if IS_ENABLED(CONFIG_SETTINGS)
    k_work_reschedule(&scene_save_work, K_SECONDS(3));
#endif
}

static void screen_start(void) {
#if IS_ENABLED(CONFIG_SETTINGS)
    settings_load_subtree(SCENE_SETTING_TREE);
#endif
    sofle_right_screen_init();
    lv_timer_create(right_tick, CONFIG_SOFLE_OLED_ART_FRAME_MS, NULL);
}

#endif

lv_obj_t *zmk_display_status_screen(void) {
    lv_obj_t *screen = lv_obj_create(NULL);

    fb_set_flip(IS_ENABLED(CONFIG_SOFLE_OLED_ART_FLIP));
    fb_clear(PIXELS);

    canvas = lv_canvas_create(screen);
    lv_canvas_set_buffer(canvas, canvas_buf, FB_PANEL_W, FB_PANEL_H, LV_IMG_CF_INDEXED_1BIT);
    /*
     * The Sofle shield sets `inversion-on` on its SSD1306, so LVGL black is a
     * lit pixel and LVGL white is dark. Framebuffer bit 1 means "lit".
     */
    lv_canvas_set_palette(canvas, 0, lv_color_white());
    lv_canvas_set_palette(canvas, 1, lv_color_black());
    lv_obj_align(canvas, LV_ALIGN_TOP_LEFT, 0, 0);

    screen_start();
    return screen;
}
