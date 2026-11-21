"""USAGE: tools/py.sh templates/check_slat_overlay.py --geom templates/out/slats_geom.json --out figures/templates/slat_overlay.jpg [--photos 1502,1501,1503]
Draw the slat template outlines (green; dashed-allowance not drawn) on the rectified single photos of the unrolled back view:
centre slat on work/parts/back/f/sc_<photo>.png, both outer slats (right as drawn, left mirrored) on so_<photo>.png. The template is
in the symmetric (centre-plane) frame; the sheets carry the slat set's +set_offset_u_mm placement, added back here.
Output per photo: centre + outer sheet side by side (half size), plus 3x zooms of the seat ends and the crest ends. Tiny compute."""
import json, argparse, numpy as np
from PIL import Image, ImageDraw
ap = argparse.ArgumentParser(); ap.add_argument("--geom", required=True); ap.add_argument("--out", required=True)
ap.add_argument("--photos", default="1502,1501,1503"); a = ap.parse_args()
G = json.load(open(a.geom)); off = G["set_offset_u_mm"]
def sheet(key):
    pl = json.load(open(f"work/parts/back/f/{key}_plane.json")); return pl["res"], pl["urange"], pl["vrange"]
def draw(im, key, polys):
    res, ur, vr = sheet(key); d = ImageDraw.Draw(im)
    for P in polys:
        P = np.asarray(P, float); q = np.stack([(P[:, 0] + off - ur[0]) / res, (vr[1] - P[:, 1]) / res], 1)
        d.line([tuple(p) for p in np.vstack([q, q[:1]])], fill=(0, 255, 60), width=1)
    return res, ur, vr
C = np.array(G["centre"]); O = np.array(G["outer_right"]); OL = O * [-1, 1]
rows = []
for ph in a.photos.split(","):
    ims = []
    for key, polys in (("sc", [C]), ("so", [O, OL])):
        im = Image.open(f"work/parts/back/f/{key}_{ph}.png").convert("RGB"); res, ur, vr = draw(im, key, polys); ims.append((key, im, res, ur, vr))
    full = [im.resize((im.size[0] // 2, im.size[1] // 2)) for _, im, *_ in ims]
    panels = []
    for key, im, res, ur, vr in ims:
        for name, u0, u1, v0, v1 in (("seat", -130, 130, 0, 45), ("crest", -130, 130, 695, 740)):
            box = (int((u0 - ur[0]) / res), int((vr[1] - v1) / res), int((u1 - ur[0]) / res), int((vr[1] - v0) / res))
            c = im.crop(box); c = c.resize((c.size[0] * 2, c.size[1] * 2), Image.NEAREST)
            ImageDraw.Draw(c).text((4, 4), f"IMG_{ph} {key} {name}", fill=(255, 255, 0)); panels.append(c)
    W = sum(f.size[0] for f in full) + 6; H = max(f.size[1] for f in full)
    pw = max(p.size[0] for p in panels); colh = sum(p.size[1] + 4 for p in panels)
    row = Image.new("RGB", (W + pw + 6, max(H, colh)), "black"); x = 0
    for f in full: row.paste(f, (x, 0)); x += f.size[0] + 6
    y = 0
    for p in panels: row.paste(p, (x, y)); y += p.size[1] + 4
    rows.append(row)
out = Image.new("RGB", (max(r.size[0] for r in rows), sum(r.size[1] + 10 for r in rows)), "black"); y = 0
for r in rows: out.paste(r, (0, y)); y += r.size[1] + 10
out.save(a.out, quality=88); print("wrote", a.out, out.size)
