"""USAGE: tools/py.sh -m 2 -t 5 tools/seat_sidebyside.py IMG_1610 [IMG_...]
Original dot photo (left) next to seat/figures/overlay_<name>.jpg (right), labelled -> seat/figures/sbs_<name>.jpg.
Run tools/seat_overlay.py first. Compute: one half-size photo at a time, < 300 MB, ~1 s each."""
import sys; from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent; sys.path.insert(0, str(ROOT))
from PIL import Image, ImageDraw, ImageFont
from rocker.seatcams import load
from rocker.orientation import exif_orientation
cams = load(); F = ROOT / "seat/figures"
try: font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 34)
except OSError: font = ImageFont.load_default()
for n in sys.argv[1:]:
    n = n if n.endswith(".JPG") else n + ".JPG"; ov = Image.open(F / f"overlay_{n[:-4]}.jpg")
    im = Image.open(cams.drive / n); im.draft("RGB", (2016, 1512)); im = im.convert("RGB")
    tr = {3: Image.ROTATE_180, 6: Image.ROTATE_270, 8: Image.ROTATE_90}.get(exif_orientation(str(cams.drive / n)))
    if tr is not None: im = im.transpose(tr)
    im = im.resize(ov.size)
    w, h = ov.size; gap, bar = 16, 60
    out = Image.new("RGB", (2 * w + gap, h + bar), "white"); out.paste(im, (0, bar)); out.paste(ov, (w + gap, bar))
    d = ImageDraw.Draw(out)
    d.text((14, 12), f"{n[:-4]}  original", fill="black", font=font)
    d.text((w + gap + 14, 12), "measured seat surface (depth tint, 5 mm contours, 20 mm grid, dots)", fill="black", font=font)
    s = 1400 / out.width; out = out.resize((1400, round(out.height * s)), Image.LANCZOS)
    out.save(F / f"sbs_{n[:-4]}.jpg", quality=84); print(n, out.size)
