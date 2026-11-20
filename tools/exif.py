"""USAGE: uv run --no-project --with pillow python -I tools/exif.py <dir>
Prints EXIF summary per image."""
import sys, os
from PIL import Image, ExifTags
d = sys.argv[1]
for n in sorted(os.listdir(d)):
    try:
        im = Image.open(os.path.join(d, n)); ex = im.getexif(); sub = ex.get_ifd(0x8769)
        g = lambda t: sub.get(t)
        print(n, im.size, ex.get(0x0110), "orient", ex.get(0x0112), "f", g(0x920A), "f35", g(0xA405), "dt", g(0x9003), "lens", g(0xA434), "exp", g(0x829A), "iso", g(0x8827))
    except Exception as e:
        print(n, "ERR", e)
