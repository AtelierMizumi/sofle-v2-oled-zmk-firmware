#!/usr/bin/env python3
"""
Hammerbeam Art Converter: 140x68 → 128x32 via Smart Center Crop
No downscaling — keeps original pixel-perfect 1-bit art.
Crops out logo (top), plain area (bottom), and sides to 128x32.

Usage:
    python3 hammerbeam_convert.py
"""

import re
import os
import sys
import math
from pathlib import Path

try:
    from PIL import Image, ImageDraw
    import numpy as np
except ImportError:
    print("Installing required packages...")
    os.system(f"{sys.executable} -m pip install Pillow numpy")
    from PIL import Image, ImageDraw
    import numpy as np

# === Configuration ===
SRC_WIDTH = 140
SRC_HEIGHT = 68
DST_WIDTH = 128
DST_HEIGHT = 32
BYTES_PER_ROW_SRC = math.ceil(SRC_WIDTH / 8)  # 18
PALETTE_SIZE = 8  # 2 colors × 4 bytes (RGBA)

# Crop budget: 12px horizontal (140→128), 36px vertical (68→32)
H_CROP = SRC_WIDTH - DST_WIDTH    # 12 px to remove left+right
V_CROP = SRC_HEIGHT - DST_HEIGHT  # 36 px to remove top+bottom

# Vertical bias: crop slightly above center (subject tends to be upper-center)
# 0.0 = crop from top, 1.0 = crop from bottom, 0.35 = slightly above center
VERTICAL_BIAS = 0.35

ART_C_PATH = Path(__file__).parent.parent / "hammerbeam-slideshow/boards/shields/nice_view_custom/widgets/art.c"
OUTPUT_DIR = Path(__file__).parent.parent / "tools/hammerbeam_output"


# ============================================================
# STEP 1: Parse art.c and extract images
# ============================================================

def parse_art_c(filepath: Path) -> list[tuple[str, list[int]]]:
    """Parse art.c and extract all hammerbeam image byte arrays."""
    content = filepath.read_text(encoding="utf-8", errors="replace")
    content = content.replace("\r\n", "\n")
    images = []

    pattern = r'uint8_t\s+(hammerbeam\d+)_map\[\]\s*=\s*\{(.*?)\};'
    matches = re.findall(pattern, content, re.DOTALL)

    for name, body in matches:
        # Take #else branch (non-inverted)
        body_cleaned = re.sub(
            r'#if\s+CONFIG_NICE_VIEW_WIDGET_INVERTED\s*\n.*?\n.*?\n#else\s*\n(.*?\n.*?\n)#endif',
            r'\1', body, flags=re.DOTALL
        )
        hex_values = re.findall(r'0x([0-9a-fA-F]{2})', body_cleaned)
        byte_data = [int(h, 16) for h in hex_values]
        images.append((name, byte_data))

    return images


def bytes_to_image(byte_data: list[int], width: int, height: int) -> Image.Image:
    """Convert LVGL CF_INDEXED_1BIT byte array to PIL Image."""
    pixel_data = byte_data[PALETTE_SIZE:]
    bytes_per_row = math.ceil(width / 8)

    img = Image.new("1", (width, height), 1)
    pixels = img.load()

    for y in range(height):
        for x in range(width):
            byte_idx = y * bytes_per_row + (x // 8)
            bit_idx = 7 - (x % 8)
            if byte_idx < len(pixel_data):
                pixels[x, y] = (pixel_data[byte_idx] >> bit_idx) & 1

    return img


# ============================================================
# STEP 2: Smart Center Crop with per-image analysis
# ============================================================

def analyze_row_interest(img: Image.Image) -> np.ndarray:
    """Score each row by how 'interesting' it is (edge transitions, detail)."""
    arr = np.array(img.convert("L"), dtype=np.float64) / 255.0
    h, w = arr.shape
    scores = np.zeros(h)

    for y in range(h):
        row = arr[y]
        # Count transitions (black→white, white→black)
        transitions = np.sum(np.abs(np.diff(row)))
        # Avoid rows that are all-white or all-black (plain/boring)
        black_ratio = 1.0 - np.mean(row)
        balance = 1.0 - abs(black_ratio - 0.5) * 2  # Best at 50% fill
        scores[y] = transitions * 0.7 + balance * 0.3 * w

    return scores


def smart_center_crop(img: Image.Image, name: str) -> tuple[Image.Image, dict]:
    """Find the best 128x32 crop region, biased slightly above center.
    
    Strategy:
    - Horizontal: center crop (6px each side) — simple since only 12px to remove
    - Vertical: find the most interesting 32-row band, biased toward upper-center
      to skip logo (top ~5-8 rows) and plain ground (bottom ~5-10 rows)
    """
    arr = np.array(img.convert("L"), dtype=np.float64) / 255.0
    h, w = arr.shape

    # --- Horizontal crop: center ---
    x_start = H_CROP // 2  # 6
    x_end = x_start + DST_WIDTH  # 134

    # --- Vertical crop: analyze interest per row ---
    row_scores = analyze_row_interest(img)

    # Score each possible 32-row window
    best_y = 0
    best_score = -1

    for y in range(V_CROP + 1):  # 37 possible positions
        window_score = np.sum(row_scores[y:y + DST_HEIGHT])

        # Bias: prefer slightly above center (VERTICAL_BIAS=0.35)
        # The center of the window at position y is at (y + DST_HEIGHT/2)
        ideal_center = VERTICAL_BIAS * SRC_HEIGHT
        window_center = y + DST_HEIGHT / 2
        position_bonus = 1.0 / (1.0 + abs(window_center - ideal_center) * 0.15)

        # Penalize extreme positions (skip logo at very top, plain at very bottom)
        if y < 3:  # Too close to top logo
            position_bonus *= 0.7
        if y > V_CROP - 3:  # Too close to bottom edge
            position_bonus *= 0.8

        total_score = window_score * position_bonus

        if total_score > best_score:
            best_score = total_score
            best_y = y

    crop_box = (x_start, best_y, x_end, best_y + DST_HEIGHT)
    cropped = img.crop(crop_box)

    info = {
        "crop_box": crop_box,
        "top_removed": best_y,
        "bottom_removed": SRC_HEIGHT - (best_y + DST_HEIGHT),
        "left_removed": x_start,
        "right_removed": SRC_WIDTH - x_end,
        "window_score": best_score,
    }

    return cropped, info


# ============================================================
# STEP 3: Generate LVGL C array
# ============================================================

def image_to_lvgl_c_array(img_1bit: Image.Image, name: str) -> str:
    """Convert a 1-bit PIL image to LVGL CF_INDEXED_1_BIT C array string."""
    width, height = img_1bit.size
    bytes_per_row = math.ceil(width / 8)
    pixels = img_1bit.convert("1").load()

    data_bytes = []
    for y in range(height):
        for byte_idx in range(bytes_per_row):
            byte_val = 0
            for bit in range(8):
                x = byte_idx * 8 + bit
                if x < width:
                    pixel = 1 if pixels[x, y] else 0
                    byte_val |= (pixel << (7 - bit))
            data_bytes.append(byte_val)

    total_size = PALETTE_SIZE + len(data_bytes)

    lines = []
    lines.append(f"#ifndef LV_ATTRIBUTE_IMG_{name.upper()}")
    lines.append(f"#define LV_ATTRIBUTE_IMG_{name.upper()}")
    lines.append(f"#endif")
    lines.append(f"")
    lines.append(f"const LV_ATTRIBUTE_MEM_ALIGN LV_ATTRIBUTE_LARGE_CONST LV_ATTRIBUTE_IMG_{name.upper()} uint8_t {name}_map[] = {{")
    lines.append(f"#if CONFIG_NICE_OLED_CUSTOM_WIDGET_INVERTED")
    lines.append(f"        0xff, 0xff, 0xff, 0xff, /*Color of index 0*/")
    lines.append(f"        0x00, 0x00, 0x00, 0xff, /*Color of index 1*/")
    lines.append(f"#else")
    lines.append(f"        0x00, 0x00, 0x00, 0xff, /*Color of index 0*/")
    lines.append(f"        0xff, 0xff, 0xff, 0xff, /*Color of index 1*/")
    lines.append(f"#endif")
    lines.append(f"")

    for y in range(height):
        row_start = y * bytes_per_row
        row_bytes = data_bytes[row_start:row_start + bytes_per_row]
        hex_str = ", ".join(f"0x{b:02x}" for b in row_bytes)
        lines.append(f"  {hex_str}, ")

    lines.append(f"}};")
    lines.append(f"")
    lines.append(f"const lv_img_dsc_t {name} = {{")
    lines.append(f"  .header.cf = LV_IMG_CF_INDEXED_1BIT,")
    lines.append(f"  .header.always_zero = 0,")
    lines.append(f"  .header.reserved = 0,")
    lines.append(f"  .header.w = {width},")
    lines.append(f"  .header.h = {height},")
    lines.append(f"  .data_size = {total_size},")
    lines.append(f"  .data = {name}_map,")
    lines.append(f"}};")
    lines.append(f"")
    return "\n".join(lines)


# ============================================================
# STEP 4: Generate comparison strips
# ============================================================

def generate_comparison(name: str, original: Image.Image, cropped: Image.Image,
                       info: dict, output_dir: Path):
    """Generate a side-by-side comparison image."""
    comp_dir = output_dir / "comparison"
    comp_dir.mkdir(parents=True, exist_ok=True)

    # Create comparison: original with crop box highlighted + cropped result
    margin = 4
    orig_display = original.convert("RGB")
    draw = ImageDraw.Draw(orig_display)
    box = info["crop_box"]
    # Draw crop rectangle in red
    draw.rectangle([box[0], box[1], box[2]-1, box[3]-1], outline=(255, 0, 0), width=1)

    comp_w = SRC_WIDTH + margin + DST_WIDTH
    comp_h = max(SRC_HEIGHT, DST_HEIGHT) + 20
    comp = Image.new("RGB", (comp_w, comp_h), (200, 200, 200))
    comp.paste(orig_display, (0, 0))
    comp.paste(cropped.convert("RGB"), (SRC_WIDTH + margin, 0))

    draw2 = ImageDraw.Draw(comp)
    draw2.text((0, SRC_HEIGHT + 2), f"Original {SRC_WIDTH}x{SRC_HEIGHT}", fill=(0, 0, 0))
    draw2.text((SRC_WIDTH + margin, DST_HEIGHT + 2),
               f"Crop {DST_WIDTH}x{DST_HEIGHT} (top-{info['top_removed']} bot-{info['bottom_removed']})",
               fill=(0, 0, 0))

    comp.save(comp_dir / f"{name}_crop.png")


# ============================================================
# Main
# ============================================================

def main():
    print("=" * 60)
    print("Hammerbeam Art Converter: Smart Center Crop")
    print(f"  {SRC_WIDTH}×{SRC_HEIGHT} → {DST_WIDTH}×{DST_HEIGHT}")
    print(f"  Vertical bias: {VERTICAL_BIAS} (0=top, 0.5=center, 1=bottom)")
    print("=" * 60)

    # Create output dirs
    orig_dir = OUTPUT_DIR / "original_140x68"
    crop_dir = OUTPUT_DIR / "cropped_128x32"
    orig_dir.mkdir(parents=True, exist_ok=True)
    crop_dir.mkdir(parents=True, exist_ok=True)

    # Step 1: Extract
    print("\n[Step 1] Extracting images from art.c...")
    images_data = parse_art_c(ART_C_PATH)
    print(f"  Found {len(images_data)} images")

    images = []
    for name, byte_data in images_data:
        img = bytes_to_image(byte_data, SRC_WIDTH, SRC_HEIGHT)
        img.save(orig_dir / f"{name}.png")
        images.append((name, img))

    # Step 2: Smart crop each image
    print("\n[Step 2] Smart center cropping...")
    cropped_images = []

    for name, img in images:
        cropped, info = smart_center_crop(img, name)
        cropped.save(crop_dir / f"{name}.png")
        cropped_images.append((name, cropped))
        generate_comparison(name, img, cropped, info, OUTPUT_DIR)

        print(f"  {name}: crop y={info['top_removed']}..{SRC_HEIGHT - info['bottom_removed']} "
              f"(skip top {info['top_removed']}px, bottom {info['bottom_removed']}px)")

    # Step 3: Generate art.c
    print("\n[Step 3] Generating art.c for nice_oled_custom...")
    art_c_path = (Path(__file__).parent.parent /
                  "hammerbeam-slideshow/boards/shields/nice_oled_custom/widgets/art.c")

    header = """/*
 *
 * Copyright (c) 2023 Collin Hodge (original Hammerbeam art)
 * Copyright (c) 2024 Center-cropped for 128x32 OLED
 * SPDX-License-Identifier: MIT
 *
 */

#include <lvgl.h>

"""
    parts = [header]
    for name, img in cropped_images:
        parts.append(image_to_lvgl_c_array(img, name))
        parts.append("\n")

    art_c_path.write_text("\n".join(parts))

    # Summary
    print(f"\n{'=' * 60}")
    print(f"DONE! Generated {len(cropped_images)} cropped images")
    print(f"  Originals:    {orig_dir}/")
    print(f"  Cropped:      {crop_dir}/")
    print(f"  Comparisons:  {OUTPUT_DIR}/comparison/")
    print(f"  art.c:        {art_c_path}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
