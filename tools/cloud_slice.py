"""USAGE: python -I tools/cloud_slice.py OUT.jpg CLOUD.npy --axes yz --where "x>60" --range -600 850 -20 1320 [--scale 1.0] [--grid 50]
One orthographic scatter view of a slab of the chair cloud with a labelled mm grid. axes: two of x,y,z (horizontal, vertical).
--where: numpy expression on x,y,z selecting points. Tiny compute."""
import argparse, numpy as np, cv2
ap = argparse.ArgumentParser(); ap.add_argument("out"); ap.add_argument("cloud"); ap.add_argument("--axes", default="yz")
ap.add_argument("--where", default="z>6"); ap.add_argument("--range", nargs=4, type=float, required=True)
ap.add_argument("--scale", type=float, default=1.0); ap.add_argument("--grid", type=int, default=50); ap.add_argument("--polylines", default=None)
a = ap.parse_args()
C = np.load(a.cloud); x, y, z = C[:, 0], C[:, 1], C[:, 2]
P = C[eval(a.where)]
i, j = "xyz".index(a.axes[0]), "xyz".index(a.axes[1]); lo_i, hi_i, lo_j, hi_j = a.range; s = a.scale
W, H = int((hi_i - lo_i) * s), int((hi_j - lo_j) * s); im = np.full((H, W, 3), 255, np.uint8)
for g in range(int(np.ceil(lo_i / a.grid)) * a.grid, int(hi_i), a.grid):
    X = int((g - lo_i) * s); cv2.line(im, (X, 0), (X, H), (200, 200, 200) if g % (2 * a.grid) == 0 else (232, 232, 232), 1)
    if g % (2 * a.grid) == 0: cv2.putText(im, str(g), (X + 2, 11), cv2.FONT_HERSHEY_SIMPLEX, 0.36, (0, 110, 0), 1)
for g in range(int(np.ceil(lo_j / a.grid)) * a.grid, int(hi_j), a.grid):
    Y = H - int((g - lo_j) * s); cv2.line(im, (0, Y), (W, Y), (200, 200, 200) if g % (2 * a.grid) == 0 else (232, 232, 232), 1)
    if g % (2 * a.grid) == 0: cv2.putText(im, str(g), (2, Y - 2), cv2.FONT_HERSHEY_SIMPLEX, 0.36, (0, 110, 0), 1)
px = ((P[:, i] - lo_i) * s).astype(int); py = (H - (P[:, j] - lo_j) * s).astype(int)
ok = (px >= 0) & (px < W - 1) & (py >= 0) & (py < H - 1)
for dx in (0, 1):
    for dy in (0, 1): im[py[ok] + dy, px[ok] + dx] = (40, 40, 40)
if a.polylines:
    import json
    for k, (name, pts) in enumerate(json.load(open(a.polylines)).items()):
        q = np.array(pts, float); q = np.stack([(q[:, 0] - lo_i) * s, H - (q[:, 1] - lo_j) * s], 1).astype(np.int32)
        cv2.polylines(im, [q], False, (0, 0, 255), 1); cv2.putText(im, name, tuple(q[0] + [4, -4]), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1)
cv2.putText(im, f"{a.axes} where {a.where} n={ok.sum()}", (60, H - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 0, 0), 1)
cv2.imwrite(a.out, im); print(im.shape, int(ok.sum()))
