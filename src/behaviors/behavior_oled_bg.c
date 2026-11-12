/*
 * &oled_bg: switch the right-half OLED wallpaper.
 *
 * The keymap runs on the left (central) half, but the wallpaper lives on the
 * right (peripheral). Global locality makes ZMK relay the key press to every
 * half, the same way &ext_power and &rgb_ug work; each half then decides
 * whether it has anything to do.
 */
#define DT_DRV_COMPAT sofle_behavior_oled_bg

#include <zephyr/device.h>
#include <drivers/behavior.h>
#include <zmk/behavior.h>

#include <dt-bindings/sofle/oled_bg.h>

#include "oled_art.h"

#if DT_HAS_COMPAT_STATUS_OKAY(DT_DRV_COMPAT)

static int on_keymap_binding_pressed(struct zmk_behavior_binding *binding,
                                     struct zmk_behavior_binding_event event) {
    ARG_UNUSED(event);
#if IS_ENABLED(CONFIG_SOFLE_OLED_ART)
    sofle_oled_art_step(binding->param1 == OLED_BG_PREV ? -1 : 1);
#endif
    return ZMK_BEHAVIOR_OPAQUE;
}

static int on_keymap_binding_released(struct zmk_behavior_binding *binding,
                                      struct zmk_behavior_binding_event event) {
    ARG_UNUSED(binding);
    ARG_UNUSED(event);
    return ZMK_BEHAVIOR_OPAQUE;
}

static const struct behavior_driver_api behavior_oled_bg_driver_api = {
    .binding_pressed = on_keymap_binding_pressed,
    .binding_released = on_keymap_binding_released,
    .locality = BEHAVIOR_LOCALITY_GLOBAL,
};

BEHAVIOR_DT_INST_DEFINE(0, NULL, NULL, NULL, NULL, POST_KERNEL, CONFIG_KERNEL_INIT_PRIORITY_DEFAULT,
                        &behavior_oled_bg_driver_api);

#endif /* DT_HAS_COMPAT_STATUS_OKAY(DT_DRV_COMPAT) */
