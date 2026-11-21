"""USAGE: python -I tools/audit_crop.py NNNN x0 y0 x1 y1 out.jpg [maxside] -- crop drive/IMG_NNNN.JPG (upright, fractions 0-1)."""
import sys
from PIL import Image, ImageOps
# crop.py IMG x0 y0 x1 y1 out [maxside]  (coords as fractions 0-1 of the upright photo)
n, x0, y0, x1, y1, out = sys.argv[1], *map(float, sys.argv[2:6]), sys.argv[6]
ms = int(sys.argv[7]) if len(sys.argv) > 7 else 1100
im = ImageOps.exif_transpose(Image.open(f"drive/IMG_{n}.JPG")); W, H = im.size
c = im.crop((int(x0 * W), int(y0 * H), int(x1 * W), int(y1 * H))); c.thumbnail((ms, ms)); c.save(out, quality=88)
