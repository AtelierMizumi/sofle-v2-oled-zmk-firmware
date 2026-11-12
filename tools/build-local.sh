#!/usr/bin/env bash
# Build the firmware locally in the container CI uses (the v0.3.0 workflow pulls
# zmk-build-arm:stable), so display and keymap changes are verified in about a
# minute before anything is pushed.
#
#   tools/build-local.sh            # build left + right
#   tools/build-local.sh left       # one target: left | right | reset
#   ZMK_WS=/path tools/build-local.sh   # put the west workspace elsewhere
#
# The west workspace (Zephyr + modules, ~5 GB) lives outside the repo.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WS="${ZMK_WS:-/mnt/500GBext4/zmk-build/sofle-v0.3.0}"
IMAGE="${ZMK_IMAGE:-zmkfirmware/zmk-build-arm:stable}"
BOARD="nice_nano_v2"
OUT="$REPO/firmware"

declare -A SHIELDS=([left]="sofle_left" [right]="sofle_right" [reset]="settings_reset")
targets=("$@"); [ ${#targets[@]} -eq 0 ] && targets=(left right)

mkdir -p "$WS" "$OUT"
# CI builds from a copy of config/; mirror that so west never writes into the repo.
rm -rf "$WS/config"; cp -r "$REPO/config" "$WS/config"

run() { docker run --rm -u "$(id -u):$(id -g)" -e HOME=/ws/.home \
          -v "$WS":/ws -v "$REPO":/repo:ro -w /ws "$IMAGE" bash -c "$1"; }

if [ ! -d "$WS/.west" ]; then run "west init -l config"; fi
# Re-sync only when the manifest changed.
if ! cmp -s "$REPO/config/west.yml" "$WS/.west.yml.synced" 2>/dev/null; then
  run "west update --fetch-opt=--filter=tree:0 && west zephyr-export"
  cp "$REPO/config/west.yml" "$WS/.west.yml.synced"
fi

for t in "${targets[@]}"; do
  shield="${SHIELDS[$t]:?unknown target '$t' (left|right|reset)}"
  echo "=== building $t ($shield) ==="
  run "west build -s zmk/app -d build/$t -b $BOARD -- \
        -DZMK_CONFIG=/ws/config -DSHIELD='$shield' -DZMK_EXTRA_MODULES=/repo"
  cp "$WS/build/$t/zephyr/zmk.uf2" "$OUT/sofle_$t.uf2"
  echo "-> $OUT/sofle_$t.uf2"
done
