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

# The original is 128x32
# We want to crop it to 112x32 (perfectly byte-aligned, 14 bytes per row)
# This perfectly avoids any bit-shifting artifacts in LVGL!

new_img_bytes = []
for row in range(32):
    row_bytes = img_bytes[row*16 : (row+1)*16]
    # take the first 14 bytes
    new_img_bytes.extend(row_bytes[:14])

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
  .header.w = 112,
  .header.h = 32,
  .data_size = {8 + len(new_img_bytes)},
  .data = hammer_beam_compact_map,
}};
"""

with open("zmk-nice-oled/boards/shields/nice_oled/assets/hammer_beam_compact.c", "w") as f:
    f.write(out_c_fixed)

print("Created hammer_beam_compact.c (112x32 landscape)")
