"""Crop and upscale a region of a screenshot, so small UI detail is readable."""
import sys

from PIL import Image

src, out = sys.argv[1], sys.argv[2]
x0, y0, x1, y1 = (int(v) for v in sys.argv[3:7])
scale = int(sys.argv[7]) if len(sys.argv) > 7 else 3
im = Image.open(src).crop((x0, y0, x1, y1))
im = im.resize((im.width * scale, im.height * scale), Image.LANCZOS)
im.save(out)
print(out, im.size)
