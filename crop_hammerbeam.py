import re

c_file = "zmk-nice-oled/boards/shields/nice_oled/assets/hammer_beam.c"
with open(c_file, "r") as f:
    content = f.read()

match = re.search(r'hammer_beam_map\[\] = \{(.*?)\};', content, re.DOTALL)
if not match:
    print("Could not find array")
    exit(1)

data_str = match.group(1)
hex_vals = re.findall(r'0x[0-9a-fA-F]{2}', data_str)

palette = hex_vals[:8]
img_data = hex_vals[8:]

img_bytes = [int(x, 16) for x in img_data]

# Parse the 128x32 pixels
pixels = []
for y in range(32):
    row_pixels = []
    for x in range(128):
        byte_idx = (y * 128 + x) // 8
        bit_idx = 7 - (x % 8) # LV_IMG_CF_INDEXED_1BIT: MSB is left-most pixel
        pixel = (img_bytes[byte_idx] >> bit_idx) & 1
        row_pixels.append(pixel)
    pixels.append(row_pixels)

# Crop to 110x32 (keep x from 0 to 109)
cropped = []
for y in range(32):
    cropped.append(pixels[y][:110])

# Rotate 90 degrees clockwise to make it 32 (W) x 110 (H)
# Clockwise: new_x = 31 - y, new_y = x
rotated = [[0]*32 for _ in range(110)]
for y in range(32):
    for x in range(110):
        rotated[x][31 - y] = cropped[y][x]

# Convert back to bytes (Width=32 means 4 bytes per row)
new_img_bytes = []
for y in range(110):
    row_bytes = []
    for b in range(4): # 4 bytes * 8 bits = 32 bits
        byte_val = 0
        for i in range(8):
            bit = rotated[y][b*8 + i]
            byte_val |= (bit << (7 - i))
        row_bytes.append(byte_val)
    new_img_bytes.extend(row_bytes)

new_hex_vals = palette + [f"0x{b:02x}" for b in new_img_bytes]

lines = []
for i in range(0, len(new_hex_vals), 12):
    lines.append("  " + ", ".join(new_hex_vals[i:i+12]) + ",")

out_c_fixed = f"""#include <lvgl.h>

#ifndef LV_ATTRIBUTE_MEM_ALIGN
#define LV_ATTRIBUTE_MEM_ALIGN
#endif

#ifndef LV_ATTRIBUTE_IMG_HAMMER_BEAM_COMPACT
#define LV_ATTRIBUTE_IMG_HAMMER_BEAM_COMPACT
#endif

const LV_ATTRIBUTE_MEM_ALIGN LV_ATTRIBUTE_LARGE_CONST LV_ATTRIBUTE_IMG_HAMMER_BEAM_COMPACT uint8_t hammer_beam_compact_map[] = {{
#if CONFIG_NICE_OLED_WIDGET_INVERTED
        0xff, 0xff, 0xff, 0xff, /*Color of index 0*/
        0x00, 0x00, 0x00, 0xff, /*Color of index 1*/
#else
        0x00, 0x00, 0x00, 0xff, /*Color of index 0*/
        0xff, 0xff, 0xff, 0xff, /*Color of index 1*/
#endif
""" + "\n".join(lines[1:]) + f"""
}};

const lv_img_dsc_t hammer_beam_compact = {{
  .header.cf = LV_IMG_CF_INDEXED_1BIT,
  .header.always_zero = 0,
  .header.reserved = 0,
  .header.w = 32,
  .header.h = 110,
  .data_size = {8 + len(new_img_bytes)},
  .data = hammer_beam_compact_map,
}};
"""

with open("zmk-nice-oled/boards/shields/nice_oled/assets/hammer_beam_compact.c", "w") as f:
    f.write(out_c_fixed)

print("Created rotated hammer_beam_compact.c (32x110)")
