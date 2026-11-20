"""USAGE: python -I tools/sheet_ortho.py --profile parts/back_profile.json --key slats --side back|front --urange -330 330
            [--res 0.5] [--offset 0] [--sweep A B STEP] [--max-angle 30] [--max-photos 7] [--photos 1501,1502] --out PREFIX
"Unrolled" orthophoto of a part that is curved in side view (slats, back legs): the surface is the side profile y = f(z)
extruded across the chair (x). Image axes: u = x (mm, chair's right positive), v = arc length up the profile (mm), so the
picture is the part laid flat, i.e. its bending-form / flat template view. --offset moves the sheet along its normal
(positive = towards the back of the chair); --sweep scores photo consistency per offset to find the real face.
Profile JSON: {"<key>": {"coef": [...polynomial y(z), highest power first...], "z": [z0, z1]}}.
Writes PREFIX_median.png, PREFIX_spread.png, PREFIX_<photo>.png, PREFIX_plane.json (res/urange/vrange for the viewers
and tracers; plus the profile so plane coordinates can be mapped back to 3D).
Compute: <= 7 photos decoded (36 MB each), outputs ~1.5 MP; < 1 GB, seconds."""
import sys, json, argparse
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import numpy as np, cv2
from rocker.cameras import Cameras
from rocker.ortho import ortho, load_raw
ap = argparse.ArgumentParser(); ap.add_argument("--profile", required=True); ap.add_argument("--key", required=True); ap.add_argument("--side", default="back")
ap.add_argument("--urange", nargs=2, type=float, required=True); ap.add_argument("--res", type=float, default=0.5); ap.add_argument("--offset", type=float, default=0)
ap.add_argument("--sweep", nargs=3, type=float, default=None); ap.add_argument("--max-angle", type=float, default=30); ap.add_argument("--max-photos", type=int, default=7)
ap.add_argument("--photos", default="auto"); ap.add_argument("--out", required=True)
a = ap.parse_args(); cams = Cameras.load()
pr = json.load(open(a.profile))[a.key]; coef = np.array(pr["coef"]); z0, z1 = pr["z"]; dcoef = np.polyder(coef)
zt = np.linspace(z0, z1, 2000); st = np.r_[0, np.cumsum(np.hypot(np.diff(zt), np.diff(np.polyval(coef, zt))))]; vrange = [0.0, float(st[-1])]

class Sheet:
    def __init__(self, offset): self.offset = offset
    def to3d(self, uv):
        uv = np.atleast_2d(uv); z = np.interp(uv[:, 1], st, zt); y = np.polyval(coef, z); d = np.polyval(dcoef, z); nrm = np.hypot(1, d)
        return np.c_[uv[:, 0], y - self.offset / nrm, z + self.offset * d / nrm]          # n_back = (0, -1, f') / |.|

zc = (z0 + z1) / 2; dc = np.polyval(dcoef, zc); nb = np.array([0, -1, dc]) / np.hypot(1, dc); cen = np.array([0, np.polyval(coef, zc), zc])
nview = nb if a.side == "back" else -nb
if a.photos != "auto": photos = [f"IMG_{x}.JPG" for x in a.photos.split(",")]
else:
    sh = Sheet(a.offset); corners = sh.to3d([[a.urange[0], 0], [a.urange[1], 0], [a.urange[0], vrange[1]], [a.urange[1], vrange[1]]]); cand = []
    for name, vw in cams.views.items():
        d = vw.center - cen; dist = np.linalg.norm(d); ang = np.degrees(np.arccos(np.clip(d @ nview / dist, -1, 1)))
        if ang > a.max_angle or dist > 3500 or dist < 500: continue
        if not vw.in_image(vw.project(corners), margin=-20).all(): continue
        cand.append((ang, name))
    photos = [nm for _, nm in sorted(cand)[:a.max_photos]]
print("photos:", " ".join(p[4:8] for p in photos), "| sheet length", round(vrange[1], 1), "mm")
raws = {nm: load_raw(cams, nm) for nm in photos}
def stack(off): return [ortho(cams, nm, Sheet(off), a.urange, vrange, a.res, raw=raws[nm]) for nm in photos]
def norm_gray(im):
    g = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY).astype(np.float32); hp = g - cv2.GaussianBlur(g, (0, 0), 6 / a.res)
    return hp / (np.sqrt(cv2.GaussianBlur(hp * hp, (0, 0), 6 / a.res)) + 2.0)
def score(ims):
    G = np.stack([norm_gray(i) for i in ims]); valid = np.all(np.stack([i.sum(2) > 0 for i in ims]), 0); sp = G.std(0); sp[~valid] = np.nan
    vals = np.sort(sp[valid]); return float(vals[:max(1, int(0.3 * len(vals)))].mean()), sp
if a.sweep:
    best = None
    for off in np.arange(a.sweep[0], a.sweep[1] + 1e-9, a.sweep[2]):
        s, _ = score(stack(off)); print(f"offset {off:7.2f}  score {s:.4f}")
        if best is None or s < best[0]: best = (s, off)
    a.offset = float(best[1]); print("best offset", a.offset)
ims = stack(a.offset)
for nm, im in zip(photos, ims): cv2.imwrite(f"{a.out}_{nm[4:8]}.png", im)
cv2.imwrite(f"{a.out}_median.png", np.median(np.stack(ims), 0).astype(np.uint8))
s, sp = score(ims); cv2.imwrite(f"{a.out}_spread.png", np.clip(np.nan_to_num(sp, nan=2.0) * 160, 0, 255).astype(np.uint8))
json.dump({"kind": "sheet", "profile_key": a.key, "coef": coef.tolist(), "z": [z0, z1], "offset": a.offset, "side": a.side, "urange": a.urange, "vrange": vrange,
           "res": a.res, "photos": photos, "score": s}, open(f"{a.out}_plane.json", "w"), indent=1)
print("score", round(s, 4), "offset", a.offset)
