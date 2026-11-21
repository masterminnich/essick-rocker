"""USAGE: python -I tools/before_after.py BEFORE.jpg AFTER.jpg OUT.jpg [--crop X0 Y0 X1 Y1] [--labels "model v3" "model v5"] [--width 2400] [--title TEXT] [--stack]
Put two pictures of the same photo side by side (e.g. two tools/overlay_sil.py outputs) with a label on each, for progress
reports and pull requests. --crop is in pixels of the inputs. --stack puts them one above the other (for wide crops, so nothing is
shrunk). Tiny compute."""
import argparse
from PIL import Image, ImageDraw, ImageFont
ap = argparse.ArgumentParser(); ap.add_argument("before"); ap.add_argument("after"); ap.add_argument("out")
ap.add_argument("--crop", nargs=4, type=int); ap.add_argument("--labels", nargs=2, default=["before", "after"]); ap.add_argument("--width", type=int, default=2400)
ap.add_argument("--title", default=None); ap.add_argument("--quality", type=int, default=82); ap.add_argument("--stack", action="store_true")
a = ap.parse_args()
ims = [Image.open(p).convert("RGB") for p in (a.before, a.after)]
if a.crop: ims = [im.crop(tuple(a.crop)) for im in ims]
try: font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 34)
except OSError: font = ImageFont.load_default()
gap = 12; bar = 52; w = a.width if a.stack else (a.width - gap) // 2; ims = [im.resize((w, round(im.height * w / im.width)), Image.LANCZOS) for im in ims]
H = 2 * (ims[0].height + bar) if a.stack else ims[0].height + bar; out = Image.new("RGB", (a.width, H), (255, 255, 255)); d = ImageDraw.Draw(out)
for k, (im, lab) in enumerate(zip(ims, a.labels)):
    x, y = (0, k * (ims[0].height + bar)) if a.stack else (k * (w + gap), 0); out.paste(im, (x, y + bar)); d.text((x + 10, y + 8), lab + (("   " + a.title) if a.title and k == 0 else ""), fill=(0, 0, 0), font=font)
out.save(a.out, quality=a.quality); print(a.out, out.size)
