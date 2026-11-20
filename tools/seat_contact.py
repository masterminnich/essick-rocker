"""USAGE: tools/py.sh tools/seat_contact.py OUT.jpg IMG... 
Contact sheet (EXIF orientation applied for viewing) + prints EXIF 35mm focal, orientation, time.
Light: one photo decoded at a time via PIL draft mode (~1/8 scale). Peak <300 MB."""
import sys
from PIL import Image, ImageDraw, ImageOps
out, paths = sys.argv[1], sys.argv[2:]
W = 480; cols = 5; thumbs = []
for p in paths:
    im = Image.open(p); ex = im.getexif(); sub = ex.get_ifd(0x8769)
    print(p.split('/')[-1], 'f35=', sub.get(0xA405), 'orient=', ex.get(0x0112), 'time=', sub.get(0x9003) or ex.get(0x0132), 'size=', im.size)
    im.draft('RGB', (W * 2, W * 2)); t = ImageOps.exif_transpose(im).convert('RGB'); t.thumbnail((W, W))
    d = ImageDraw.Draw(t); d.rectangle([0, 0, 120, 22], fill='black'); d.text((4, 4), p.split('/')[-1], fill='white')
    thumbs.append(t)
rows = (len(thumbs) + cols - 1) // cols
sheet = Image.new('RGB', (cols * W, rows * W), 'gray')
for i, t in enumerate(thumbs): sheet.paste(t, ((i % cols) * W, (i // cols) * W))
sheet.save(out, quality=85)
