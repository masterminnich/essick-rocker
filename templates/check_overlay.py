"""USAGE: tools/py.sh templates/check_overlay.py --geom templates/out/rocker_geom.json --out figures/templates/rocker_overlay.jpg
Draw the rocker template outline (and the leg-landing marks) on rectified single photos of both rockers' outer side faces
(work/parts/rocker{L,R}/o_<photo>.png, 0.5 mm/px). Right sheet: the outline is moved into the right rocker's own sheet frame
with the inverse of parts/rocker_profile.json right_vs_left. Output: one full strip per photo plus 3x zooms (nose, back leg,
rest point, front leg, front end). Tiny compute (one 2560x480 sheet at a time)."""
import json, argparse, numpy as np
from PIL import Image, ImageDraw
ap = argparse.ArgumentParser(); ap.add_argument("--geom", required=True); ap.add_argument("--out", required=True)
ap.add_argument("--photos", default="L:1507,L:1506,R:1472,R:1471"); a = ap.parse_args()
G = json.load(open(a.geom)); P = json.load(open("parts/rocker_profile.json")); rv = P["right_vs_left"]
res, ur, vr = 0.5, (-560, 720), (-10, 230)
def to_side(pts, side):
    pts = np.asarray(pts, float)
    if side == "L": return pts
    th = np.radians(rv["rotation_deg"]); c, s = np.cos(th), np.sin(th); q = pts - [rv["shift_u_mm"], rv["shift_v_mm"]]
    return np.stack([c * q[:, 0] + s * q[:, 1], -s * q[:, 0] + c * q[:, 1]], 1)
def px(p): p = np.asarray(p, float); return np.stack([(p[:, 0] - ur[0]) / res, (vr[1] - p[:, 1]) / res], 1)
zooms = [("rear nose", -500, -420), ("back leg", 0, 110), ("rest point", 140, 240), ("front leg", 500, 600), ("front end", 585, 640)]
rows = []
for spec in a.photos.split(","):
    side, ph = spec.split(":")
    im = Image.open(f"work/parts/rocker{side}/o_{ph}.png").convert("RGB"); d = ImageDraw.Draw(im)
    o = px(to_side(G["outline"], side)); d.line([tuple(p) for p in np.vstack([o, o[:1]])], fill=(0, 255, 60), width=1)
    for k, l in G["legs"].items():
        vv = np.array([l["v"] - 3, l["v"] + 40]); uu = l["u"] + l["slope_du_dv"] * (vv - l["v"])
        q = px(to_side(np.stack([uu, vv], 1), side)); d.line([tuple(p) for p in q], fill=(255, 40, 200), width=1)
    W, H = im.size; full = im.resize((W * 3 // 4, H * 3 // 4))
    panels = []
    for name, u0, u1 in zooms:
        x0, x1 = int((u0 - ur[0]) / res), int((u1 - ur[0]) / res)
        vc = np.interp((u0 + u1) / 2, np.array(G["outline"])[:, 0][np.argsort(np.array(G["outline"])[:, 0])], np.array(G["outline"])[:, 1][np.argsort(np.array(G["outline"])[:, 0])])
        y0 = int(max(0, (vr[1] - vc - 45) / res)); y1 = int(min(H, y0 + 160))
        c = im.crop((x0, y0, x1, y1)); c = c.resize((c.size[0] * 3, c.size[1] * 3), Image.NEAREST)
        ImageDraw.Draw(c).text((4, 4), f"{side} IMG_{ph}: {name}", fill=(255, 255, 0)); panels.append(c)
    pw = sum(p.size[0] for p in panels) + 6 * len(panels); ph_ = max(p.size[1] for p in panels)
    row = Image.new("RGB", (max(pw, full.size[0]), full.size[1] + ph_ + 6), "black"); row.paste(full, (0, 0)); x = 0
    for p in panels: row.paste(p, (x, full.size[1] + 6)); x += p.size[0] + 6
    rows.append(row)
out = Image.new("RGB", (max(r.size[0] for r in rows), sum(r.size[1] + 10 for r in rows)), "black"); y = 0
for r in rows: out.paste(r, (0, y)); y += r.size[1] + 10
out.save(a.out, quality=88); print("wrote", a.out, out.size)
