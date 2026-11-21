"""USAGE: python -I tools/audit_figs.py -- composites for figures/model_audit/ from renders and crops in work/audit/ (Blender renders of model_v9, photo crops by tools/audit_crop.py)."""
from PIL import Image, ImageDraw, ImageFont
A = "work/audit/"; F = "figures/model_audit/"
try: font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 30); small = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 24)
except Exception: font = small = ImageFont.load_default()
def label(im, t, pos=(12, 10), f=None):
    d = ImageDraw.Draw(im); f = f or font; x, y = pos; b = d.textbbox((x, y), t, font=f); d.rectangle((b[0] - 6, b[1] - 4, b[2] + 6, b[3] + 4), fill=(255, 255, 255)); d.text((x, y), t, fill=(20, 20, 20), font=f); return im
def fit(im, w, h):
    im = im.convert("RGB"); im.thumbnail((w, h)); c = Image.new("RGB", (w, h), (172, 172, 172) if im.getpixel((2, 2))[0] in range(160, 185) else (255, 255, 255)); c.paste(im, ((w - im.width) // 2, (h - im.height) // 2)); return c
def grid(items, cols, w, h, out, bg=(255, 255, 255)):
    rows = (len(items) + cols - 1) // cols; G = Image.new("RGB", (cols * w, rows * h), bg)
    for i, (p, t) in enumerate(items):
        im = fit(Image.open(p), w - 8, h - 8); label(im, t, f=small); G.paste(im, ((i % cols) * w + 4, (i // cols) * h + 4))
    G.save(out, quality=86); print(out, G.size)
grid([(A + "v9_front.png", "front"), (A + "v9_back.png", "back"), (A + "v9_top.png", "top (front at bottom)"),
      (A + "v9_34_front.png", "front right"), (A + "v9_34_back.png", "back left"), (A + "v9_right.png", "right side")], 3, 640, 640, F + "overview_v9.jpg")
grid([(A + "z_bleg_side.png", "model v9: back leg, side view"), (A + "crops/1471_bleg_raw.jpg", "IMG_1471: the real leg"), (A + "ovz_1471/sil_1471.jpg", "IMG_1471 + model outline (magenta)")], 3, 620, 900, F + "back_leg_model_vs_photo.jpg")
# dominos: annotate the 1519 crop
im = Image.open(A + "crops/1519_dominos.jpg").convert("RGB"); d = ImageDraw.Draw(im)
for (cx, cy, rx, ry, t) in ((240, 276, 62, 30, "front leg"), (1236, 470, 52, 28, "back leg")):
    d.ellipse((cx - rx, cy - ry, cx + rx, cy + ry), outline=(255, 210, 0), width=5); label(im, f"Domino end, {t}", (cx - 110, cy + ry + 14), small)
label(im, "IMG_1519 (left side): through-Domino ends on the legs' outer faces, at seat-edge height")
im.save(F + "dominos_IMG_1519.jpg", quality=88)
im = Image.open(A + "crops/1572_fleg_domino.jpg").convert("RGB"); label(im, "IMG_1572: front-leg Domino end, square on (about 3.4 : 1 long : thick)", f=small); im.save(F + "domino_close_IMG_1572.jpg", quality=88)
grid([(A + "z_bleg_seat_in.png", "1 back leg / seat (inside): kink + step, no joint face"), (A + "z_bleg_seat_out.png", "2 back leg / seat (outside): seat edge runs through the leg"),
      (A + "z_fleg_rocker.png", "3 front leg on rocker: 0.8 mm air gap, no joint"), (A + "z_bleg_rocker.png", "4 back leg on rocker: 1.7 mm air gap, no joint"),
      (A + "z_arm_front.png", "5 arm on front leg: butt, 0.3 mm, no tenon"), (A + "z_arm_rear.png", "6 arm into back leg: pokes 4.6 mm in"),
      (A + "z_crest_leg.png", "7 crest to back leg: 3.6 mm overlap; slats 15 mm into crest")], 2, 760, 640, F + "joints_model_v9.jpg")
grid([(A + "crops/1528_arm_front.jpg", "IMG_1528: round end grain on the arm top, over the leg"), (A + "crops/1494.jpg", "IMG_1494: back leg on the rocker, flush, no fastener seen"),
      (A + "crops/1495.jpg", "IMG_1495: front leg on the rocker"), (A + "crops/1556.jpg", "IMG_1556: crest meets the back leg at its top"),
      (A + "crops/1553.jpg", "IMG_1553: centre slat into the crest underside")], 2, 760, 640, F + "joints_real.jpg")
