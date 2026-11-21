"""USAGE: work/toolkit/rk.sh tools/edge_radii/cornerfit.py IMG X0 Y0 X1 Y1 SEEDX SEEDY ARM_PX PXMM OUT.jpg [--dark|--light] [--thr L]
Phase 6c: radius of a rounded CORNER of an outline seen square-on (e.g. the rocker's tail tip in plan from above, with a
tape on the same face for the scale). Display orientation (EXIF applied), pixel coordinates of that image.
1. In the box X0..X1, Y0..Y1 the part is the dark (default) or light region of L* (Otsu threshold, or --thr); its outline is
   the largest contour, smoothed (Gaussian, sigma 2 px).
2. The outline point nearest (SEEDX, SEEDY) is the corner; the tangent direction is averaged over ARM/2..ARM px of outline
   on each side (the two straight-ish sides); the corner turns by THETA between them.
3. The middle 70 % of that turn (from 15 % to 85 %) happens over an arc length s: R = s / (0.7 THETA). A sharp corner gives
   R ~ the blur; a true round gives its radius; a corner that tightens toward its middle gives the middle's mean radius.
Writes OUT.jpg (the box, 4x, outline in cyan, the 15-85 % arc in orange) for the by-eye check."""
import sys, json, argparse
import numpy as np, cv2
from scipy.ndimage import gaussian_filter1d

ap = argparse.ArgumentParser()
ap.add_argument("img"); [ap.add_argument(k, type=float) for k in ("x0", "y0", "x1", "y1", "sx", "sy", "arm", "pxmm")]
ap.add_argument("out"); ap.add_argument("--light", action="store_true"); ap.add_argument("--dark", action="store_true")
ap.add_argument("--thr", type=float, default=None)
a = ap.parse_args()
im = cv2.imread(f"drive/IMG_{a.img}.JPG")
x0, y0, x1, y1 = map(int, (a.x0, a.y0, a.x1, a.y1))
box = im[y0:y1, x0:x1]
L = cv2.GaussianBlur(cv2.cvtColor(box, cv2.COLOR_BGR2Lab)[..., 0], (5, 5), 1.0)
if a.thr is None:
    thr, _ = cv2.threshold(L, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
else:
    thr = a.thr
mask = ((L > thr) if a.light else (L < thr)).astype(np.uint8)
mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
cs, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
c = max(cs, key=cv2.contourArea)[:, 0, :].astype(float)
c = np.c_[gaussian_filter1d(c[:, 0], 2, mode="wrap"), gaussian_filter1d(c[:, 1], 2, mode="wrap")]
ds = np.linalg.norm(np.diff(c, axis=0, append=c[:1]), axis=1); s = np.concatenate([[0], np.cumsum(ds)[:-1]]); P = s[-1] + ds[-1]
i0 = int(np.argmin(np.linalg.norm(c - [a.sx - x0, a.sy - y0], axis=1)))
d = np.roll(c, -1, 0) - np.roll(c, 1, 0); ang = np.unwrap(np.arctan2(d[:, 1], d[:, 0]))
rel = (s - s[i0] + P / 2) % P - P / 2          # signed arc length from the corner
ang = np.unwrap(np.roll(ang, -i0)); rel_r = np.roll(rel, -i0); ang = ang - ang[0]
order = np.argsort(rel_r); rr, aa = rel_r[order], ang[order]
aa = np.unwrap(aa)
A = a.arm
th_a = aa[(rr > -A) & (rr < -A / 2)].mean(); th_b = aa[(rr > A / 2) & (rr < A)].mean()
TH = th_b - th_a
win = (rr > -A / 2) & (rr < A / 2)
f = (aa[win] - th_a) / TH
r15 = np.interp(0.15, f if f[-1] > f[0] else f[::-1], rr[win] if f[-1] > f[0] else rr[win][::-1])
r85 = np.interp(0.85, f if f[-1] > f[0] else f[::-1], rr[win] if f[-1] > f[0] else rr[win][::-1])
R = abs(r85 - r15) / (0.7 * abs(TH))
vis = cv2.resize(box, None, fx=4, fy=4, interpolation=cv2.INTER_CUBIC)
for p in c: cv2.circle(vis, tuple(int(v * 4) for v in p), 1, (255, 255, 0), -1)
arc = np.roll(c, -i0, 0)[order][(rr >= min(r15, r85)) & (rr <= max(r15, r85))]
for p in arc: cv2.circle(vis, tuple(int(v * 4) for v in p), 2, (0, 128, 255), -1)
cv2.imwrite(a.out, vis)
print(json.dumps(dict(img=a.img, seed=[a.sx, a.sy], arm_px=A, threshold=float(thr), turn_deg=round(float(np.degrees(TH)), 1),
                      arc15_85_px=round(float(abs(r85 - r15)), 1), R_px=round(float(R), 1), R_mm=round(float(R / a.pxmm), 2),
                      pxmm=a.pxmm)))
