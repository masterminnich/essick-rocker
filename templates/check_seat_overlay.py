"""USAGE: tools/py.sh templates/check_seat_overlay.py --geom templates/out/seat_geom.json --out figures/templates/seat_overlay.jpg [--photos 1545,1548,1538]
Draw the seat template's CUT outline on overhead photos rectified onto a plane parallel to the seat's underside, 38 mm above it
(about the rim; rocker/ortho.py). Each 3D outline point (top arris / front roll, from the model mesh) is carried to the sheet along
its own camera ray, so the drawn line lands where the photo shows that point whatever its height (no plane parallax).
Green = template outline, cyan = slat mortise centres (on their bottoms, so hidden: position only). One strip per photo (full + 3x zooms at the front corners,
the scallop hollows, the pommel, the mid sides and the back corners). One photo decoded at a time (36 MB); < 1 GB, seconds."""
import sys, json, argparse
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import numpy as np
from PIL import Image, ImageDraw
from rocker.cameras import Cameras
from rocker.ortho import Plane, ortho, plane_to_pix

ap = argparse.ArgumentParser(); ap.add_argument("--geom", required=True); ap.add_argument("--out", required=True)
ap.add_argument("--photos", default="1545,1548,1538"); ap.add_argument("--w", type=float, default=38.0)
ap.add_argument("--drive", default=None, help="photo folder (default: ./drive, else the coordinator's ../rocking-chair/drive, read only)"); a = ap.parse_args()
G = json.load(open(a.geom)); PL = G["plane"]; V0 = PL["V0"]; O = np.array(PL["origin"]); EV = np.array(PL["ev"]); EN = np.array(PL["en"])
pl = Plane(O + EN * a.w, np.array([1.0, 0, 0]), EV); res = 0.5; ur = (-300.0, 300.0); vr = (V0 - 30.0, V0 + 590.0)
X3 = np.array(G["outline_xyz"]); DRV = Path(a.drive) if a.drive else next((p for p in (ROOT / "drive", ROOT.parent / "rocking-chair" / "drive") if p.exists()), ROOT / "drive")
cams = Cameras.load(drive=DRV)
zooms = [("L front corner", -285, -215, 500, 570), ("L hollow", -170, -90, 490, 560), ("pommel", -40, 40, 510, 580), ("R hollow", 90, 170, 490, 560),
         ("R front corner", 215, 285, 500, 570), ("L side", -290, -220, 230, 300), ("R side", 220, 290, 230, 300), ("L back", -230, -160, -10, 60), ("R back", 160, 230, -10, 60)]
rows = []
for ph in a.photos.split(","):
    nm = f"IMG_{ph}.JPG"; vw = cams[nm]
    im = Image.fromarray(ortho(cams, nm, pl, ur, vr, res)[:, :, ::-1].copy()); d = ImageDraw.Draw(im)
    C = vw.center; uv = pl.intersect(C, X3 - C); px = plane_to_pix(ur, vr, res, uv)
    vis = np.isfinite(px).all(1)
    d.line([tuple(p) for p in np.vstack([px, px[:1]])], fill=(0, 255, 60), width=1)
    for k, m in G["marks"].items():
        if k.startswith("SLAT"):
            u, v, w = m["centre_uvw"]; X = O + np.array([1.0, 0, 0]) * u + EV * v + EN * w; q = plane_to_pix(ur, vr, res, pl.intersect(C, (X - C)[None]))[0]
            d.ellipse([q[0] - 3, q[1] - 3, q[0] + 3, q[1] + 3], outline=(0, 220, 255))
    full = im.resize((im.size[0] // 2, im.size[1] // 2)); ImageDraw.Draw(full).text((6, 6), f"IMG_{ph} (rectified 38 mm above the underside, 1 mm/px here)", fill=(255, 255, 0))
    panels = []
    for name, x0, x1, y0, y1 in zooms:
        c0 = plane_to_pix(ur, vr, res, [[x0, y1 + V0]])[0]; c1 = plane_to_pix(ur, vr, res, [[x1, y0 + V0]])[0]
        c = im.crop((int(c0[0]), int(c0[1]), int(c1[0]), int(c1[1]))); c = c.resize((c.size[0] * 2, c.size[1] * 2), Image.NEAREST)
        ImageDraw.Draw(c).text((3, 3), name, fill=(255, 255, 0)); panels.append(c)
    pw, ph_ = panels[0].size; grid = Image.new("RGB", (3 * pw + 12, 3 * ph_ + 12), "black")
    for i, p in enumerate(panels): grid.paste(p, ((i % 3) * (pw + 6), (i // 3) * (ph_ + 6)))
    row = Image.new("RGB", (full.size[0] + grid.size[0] + 10, max(full.size[1], grid.size[1])), "black"); row.paste(full, (0, 0)); row.paste(grid, (full.size[0] + 10, 0))
    rows.append(row); print(ph, "outline points on the sheet:", int(vis.sum()), "/", len(px)); del im
out = Image.new("RGB", (max(r.size[0] for r in rows), sum(r.size[1] + 10 for r in rows)), "black"); y = 0
for r in rows: out.paste(r, (0, y)); y += r.size[1] + 10
Path(a.out).parent.mkdir(parents=True, exist_ok=True); out.save(a.out, quality=88); print("wrote", a.out, out.size)
