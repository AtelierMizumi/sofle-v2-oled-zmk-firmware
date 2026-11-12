#!/usr/bin/env bash
# Host-side tests for the OLED rendering code (no Zephyr, no hardware).
#   tests/host/run.sh            run the tests
#   tests/host/run.sh --dump     also write PBM screenshots to tests/host/out/
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/../.."
out=tests/host/out; mkdir -p "$out"
gcc -std=c11 -Wall -Wextra -Werror -fsanitize=address,undefined -g \
    -Isrc/display -Isrc/display/generated \
    tests/host/test_fb.c src/display/fb.c src/display/left_screen.c src/display/right_screen.c \
    src/display/generated/art_left.c \
    src/display/generated/art_frames.c \
    -o "$out/test_fb"
if [ "${1:-}" = "--dump" ]; then "$out/test_fb" "$out"; else "$out/test_fb"; fi
