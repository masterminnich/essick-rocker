"""USAGE: python -I tools/residual.py --glb parts/model_v1.glb --images 1507,1471,... [--out work/resid_v1.json] [--search-mm 12]
Numeric model-vs-photo check. For every part and photo: project the part, take its outline, and at each outline point
(not hidden behind another part) search along the outline normal for the strongest image edge within +-search-mm.
Offsets are converted to millimetres at the part's distance. Reported per part: median signed offset (+ = the real edge is
outside the model outline, i.e. model too small), median |offset|, and the share of outline points with an edge found.
Background clutter adds false edges, so medians over many photos are the meaningful numbers.
Compute: one photo at half resolution in memory at a time; < 1 GB; ~1 s per photo."""
import sys, json, argparse
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import numpy as np, cv2, trimesh
from PIL import Image
from rocker.cameras import Cameras
ap = argparse.ArgumentParser(); ap.add_argument("--glb", required=True); ap.add_argument("--images", required=True); ap.add_argument("--out", default=None)
ap.add_argument("--search-mm", type=float, default=12); ap.add_argument("--quiet", action="store_true")
a = ap.parse_args()
cams = Cameras.load(); sc = trimesh.load(a.glb); geoms = dict(sc.geometry.items()); S = 0.5
rows = {k: [] for k in geoms}
for n in a.images.split(","):
    name = f"IMG_{n}.JPG"; v = cams[name]
    raw = np.asarray(Image.open(ROOT / "drive" / name).convert("RGB")); small = cv2.resize(raw, None, fx=S, fy=S, interpolation=cv2.INTER_AREA)
    lab = cv2.GaussianBlur(cv2.cvtColor(small, cv2.COLOR_RGB2LAB).astype(np.float32), (0, 0), 1.0); H, W = lab.shape[:2]
    masks, depth = {}, {}
    for k, g in geoms.items():
        uv, z = v.project(np.asarray(g.vertices), return_depth=True)
        if not np.isfinite(uv).all(): continue
        m = np.zeros((H, W), np.uint8); cv2.fillPoly(m, list((uv[np.asarray(g.faces)] * S).astype(np.int32)), 255); masks[k] = m; depth[k] = float(np.median(z))
    for k, m in masks.items():
        if m.sum() < 255 * 400: continue
        cs, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        c = max(cs, key=len).reshape(-1, 2).astype(float)
        if len(c) < 60: continue
        # hidden where a nearer part covers the outline (or touches it: joints)
        occ = np.zeros((H, W), np.uint8)
        for k2, m2 in masks.items():
            if k2 != k: occ |= m2
        occ = cv2.dilate(occ, np.ones((9, 9), np.uint8))
        t = np.roll(c, -4, 0) - np.roll(c, 4, 0); t /= np.linalg.norm(t, axis=1, keepdims=True) + 1e-9; nrm = np.c_[t[:, 1], -t[:, 0]]
        inside = m[np.clip((c[:, 1] - 3 * nrm[:, 1]).astype(int), 0, H - 1), np.clip((c[:, 0] - 3 * nrm[:, 0]).astype(int), 0, W - 1)] > 0
        nrm[~inside] *= -1                                         # make normals point outward
        mm_per_px = depth[k] / (v.focal_raw * S); R = int(np.ceil(a.search_mm / mm_per_px)); offs = np.arange(-R, R + 1)
        idx = np.arange(0, len(c), 3); cc, nn = c[idx], nrm[idx]
        ok = (cc[:, 0] > R + 2) & (cc[:, 0] < W - R - 2) & (cc[:, 1] > R + 2) & (cc[:, 1] < H - R - 2)
        ok &= occ[np.clip(cc[:, 1].astype(int), 0, H - 1), np.clip(cc[:, 0].astype(int), 0, W - 1)] == 0
        cc, nn = cc[ok], nn[ok]
        if len(cc) < 20: continue
        px = (cc[:, None, 0] + offs[None, :] * nn[:, None, 0]).astype(np.float32); py = (cc[:, None, 1] + offs[None, :] * nn[:, None, 1]).astype(np.float32)
        prof = cv2.remap(lab, px, py, cv2.INTER_LINEAR); g = np.linalg.norm(np.gradient(prof, axis=1), axis=2)
        strength = g.max(1); found = strength > 6.0
        # nearest significant edge (local maximum at least half as strong as the strongest), not the strongest one:
        pk = (g >= np.roll(g, 1, 1)) & (g >= np.roll(g, -1, 1)) & (g > 0.5 * strength[:, None]) & (g > 6.0)
        pk[:, 0] = pk[:, -1] = False
        cost = np.where(pk, np.abs(offs)[None, :], 10 ** 6); j = cost.argmin(1); found &= cost.min(1) < 10 ** 6
        rows[k] += [(float(o * mm_per_px), n) for o in offs[j][found]] + [(np.nan, n)] * int((~found).sum())
    del raw, small, lab
out = {}
print(f"{'part':10s} {'n':>6s} {'found':>6s} {'median':>8s} {'med|.|':>8s} {'p90|.|':>8s}   (mm; + = real edge outside the model outline)")
for k in sorted(rows):
    r = np.array([x[0] for x in rows[k]], float)
    if len(r) == 0: continue
    f = np.isfinite(r); rr = r[f]
    if len(rr) < 10: continue
    out[k] = {"n": int(len(r)), "found": float(f.mean()), "median_mm": float(np.median(rr)), "median_abs_mm": float(np.median(np.abs(rr))), "p90_abs_mm": float(np.percentile(np.abs(rr), 90))}
    print(f"{k:10s} {len(r):6d} {f.mean():6.2f} {np.median(rr):8.2f} {np.median(np.abs(rr)):8.2f} {np.percentile(np.abs(rr), 90):8.2f}")
allr = np.concatenate([np.array([x[0] for x in rows[k]], float) for k in rows if rows[k]]); allr = allr[np.isfinite(allr)]
out["ALL"] = {"median_abs_mm": float(np.median(np.abs(allr))), "p90_abs_mm": float(np.percentile(np.abs(allr), 90))}
print(f"{'ALL':10s} {len(allr):6d} {'':6s} {np.median(allr):8.2f} {np.median(np.abs(allr)):8.2f} {np.percentile(np.abs(allr), 90):8.2f}")
if a.out: json.dump(out, open(a.out, "w"), indent=1)
