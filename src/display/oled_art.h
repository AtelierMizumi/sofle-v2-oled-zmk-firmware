/* Entry points other code may call into the OLED screens. */
#pragma once

/*
 * Show the next (dir > 0) or previous (dir < 0) wallpaper on this half and
 * remember the choice across power cycles. Safe to call from any thread.
 * Does nothing on a half that has no wallpapers (the central).
 */
void sofle_oled_art_step(int dir);
