"""USAGE: uv run --no-project --with pillow python -I tools/sheets.py <src_dir> <sheet_dir> <mid_dir>
Builds labeled contact sheets (12 per sheet) and 1600px orientation-corrected mids."""
import sys, os
from PIL import Image, ImageOps, ImageDraw, ImageFont
src, sd, md = sys.argv[1:4]
names = sorted(os.listdir(src))
T = 640; cols, rows = 4, 3
font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 34)
for s in range(0, len(names), cols*rows):
    sheet = Image.new("RGB", (cols*T, rows*T), (30, 30, 30))
    for k, n in enumerate(names[s:s+cols*rows]):
        im = ImageOps.exif_transpose(Image.open(os.path.join(src, n)))
        mid = im.copy(); mid.thumbnail((1600, 1600)); mid.save(os.path.join(md, n), quality=88)
        im.thumbnail((T-8, T-8))
        x, y = (k % cols)*T, (k//cols)*T
        sheet.paste(im, (x + (T-im.width)//2, y + (T-im.height)//2))
        d = ImageDraw.Draw(sheet); lab = n[4:8]
        d.rectangle([x+4, y+4, x+100, y+46], fill=(0, 0, 0)); d.text((x+10, y+6), lab, fill=(255, 230, 0), font=font)
    sheet.save(os.path.join(sd, f"sheet_{s//(cols*rows)+1:02d}.jpg"), quality=85)
