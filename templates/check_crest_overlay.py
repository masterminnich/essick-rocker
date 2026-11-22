"""USAGE: tools/py.sh templates/check_crest_overlay.py --geom templates/out/crest_geom.json --out figures/templates/crest_overlay.jpg [--photos 1545,1548,1502,1501]
Project the crest template's geometry (the four arrises, the shoulders on the back legs' inner faces, the arch carried over the
leg tops and the slat mortise lines on the bottom face) into single photos with the solved cameras (work/solve/model +
solve/metric_frame.json; raw photos from the coordinator's drive/, found through the work/solve symlink), so there is no plane
parallax. Green = arrises, red = shoulders / arch over the legs, yellow = slat back/front faces at the crest's bottom face.
Output per photo: the crest crop plus 3x zooms of both ends and the centre. Tiny compute (one photo decoded at a time)."""
import json, argparse, sys, os, numpy as np
from pathlib import Path
from PIL import Image, ImageDraw
ROOT = Path(__file__).resolve().parent.parent; sys.path.insert(0, str(ROOT))
from rocker.cameras import Cameras
ap = argparse.ArgumentParser(); ap.add_argument("--geom", required=True); ap.add_argument("--out", required=True)
ap.add_argument("--photos", default="1545,1548,1502,1501"); a = ap.parse_args()
G = json.load(open(a.geom))
drive = (ROOT / "work/solve").resolve().parent.parent / "drive"
cams = Cameras.load(ROOT / "work/solve/model", metric=ROOT / "solve/metric_frame.json", drive=drive)
lines = [(np.array(v), (0, 255, 60)) for v in G["arrises"].values()]
for v in G["arch_over_leg"].values(): lines.append((np.array(v), (255, 40, 40)))
A = {k: np.array(v) for k, v in G["arrises"].items()}
for sg in (-1, 1):                                       # shoulder: leg inner face x(z) on the crest's back and front faces
    zx = np.array(G["shoulders"]["leg_inner_face_z_x"])
    for kb, kt in (("bottom_rear", "top_rear"), ("bottom_front", "top_front")):
        i = np.argmin(np.abs(A[kb][:, 0] - sg * G["shoulders"]["top"])); pb, pt = A[kb][i], A[kt][i]
        t = np.linspace(0, 1, 12)[:, None]; P = pb + t * (pt - pb); P[:, 0] = sg * np.interp(P[:, 2], zx[:, 0], zx[:, 1]); lines.append((P, (255, 40, 40)))
for k, s in G["slats"].items():
    for key in ("bottom_back", "bottom_front"): lines.append((np.array(s[key]), (255, 230, 0)))
allP = np.vstack([l for l, _ in lines])
rows = []
for ph in a.photos.split(","):
    nm = f"IMG_{ph}.JPG"; vw = cams[nm]; im = Image.open(drive / nm).convert("RGB"); d = ImageDraw.Draw(im)
    uv_all = vw.project(allP); lo, hi = np.nanmin(uv_all, 0) - 120, np.nanmax(uv_all, 0) + 120
    for P, col in lines:
        uv = vw.project(P); d.line([tuple(p) for p in uv], fill=col, width=3)
    box = tuple(int(v) for v in (*np.maximum(lo, 0), *np.minimum(hi, im.size)))
    dx = vw.project(np.array([[100.0, -180, 1040], [-100.0, -180, 1040]])); dx = dx[0] - dx[1]
    k = int(round(np.degrees(np.arctan2(dx[1], dx[0])) / 90)) % 4          # quarter turns that bring the chair's +x to the right
    rot = lambda I: I.transpose([None, Image.ROTATE_90, Image.ROTATE_180, Image.ROTATE_270][k]) if k else I
    crop = rot(im.crop(box)); sc = 1400 / crop.size[0]; full = crop.resize((1400, int(crop.size[1] * sc)))
    ImageDraw.Draw(full).text((6, 6), f"IMG_{ph}", fill=(255, 255, 0))
    zooms = []
    for lab, X in (("left end", A["top_rear"][0]), ("centre", A["top_rear"][len(A["top_rear"]) // 2]), ("right end", A["top_rear"][-1])):
        c = vw.project(X[None] + [0, 10, -35])[0]; r = 150
        z = rot(im.crop((int(c[0] - r), int(c[1] - r), int(c[0] + r), int(c[1] + r)))).resize((450, 450), Image.LANCZOS)
        ImageDraw.Draw(z).text((4, 4), f"IMG_{ph} {lab}", fill=(255, 255, 0)); zooms.append(z)
    W = max(1400, 3 * 450 + 12); row = Image.new("RGB", (W, full.size[1] + 460), "black"); row.paste(full, (0, 0))
    for j, z in enumerate(zooms): row.paste(z, (j * 456, full.size[1] + 6))
    rows.append(row); del im
out = Image.new("RGB", (max(r.size[0] for r in rows), sum(r.size[1] + 10 for r in rows)), "black"); y = 0
for r in rows: out.paste(r, (0, y)); y += r.size[1] + 10
os.makedirs(os.path.dirname(a.out), exist_ok=True); out.save(a.out, quality=85); print("wrote", a.out, out.size)
