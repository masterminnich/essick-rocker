"""USAGE: python -I tools/cloud_views.py OUT.jpg CLOUD.npy [CLOUD2.npy ...] [--scale 1.0] [--zmin 6]
Three orthographic scatter views (side: Y-Z, front: X-Z, top: X-Y) of chair-frame point clouds (rows X Y Z R G B ...),
with a 100 mm grid, for looking at the reconstruction. Tiny compute."""
import sys, argparse, numpy as np, cv2
ap = argparse.ArgumentParser(); ap.add_argument("out"); ap.add_argument("clouds", nargs="+"); ap.add_argument("--scale", type=float, default=1.0)
ap.add_argument("--zmin", type=float, default=6); ap.add_argument("--mono", action="store_true")
a = ap.parse_args()
P = np.vstack([np.load(c)[:, :6] for c in a.clouds]); P = P[P[:, 2] > a.zmin]
s = a.scale
def panel(i, j, lo_i, hi_i, lo_j, hi_j, label):
    W, H = int((hi_i - lo_i) * s), int((hi_j - lo_j) * s); im = np.full((H, W, 3), 255, np.uint8)
    for g in range(int(np.ceil(lo_i / 100)) * 100, int(hi_i), 100):
        cv2.line(im, (int((g - lo_i) * s), 0), (int((g - lo_i) * s), H), (225, 225, 225) if g else (160, 160, 255), 1)
        cv2.putText(im, str(g), (int((g - lo_i) * s) + 2, H - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (150, 150, 150), 1)
    for g in range(int(np.ceil(lo_j / 100)) * 100, int(hi_j), 100):
        cv2.line(im, (0, H - int((g - lo_j) * s)), (W, H - int((g - lo_j) * s)), (225, 225, 225) if g else (160, 160, 255), 1)
        cv2.putText(im, str(g), (2, H - int((g - lo_j) * s) - 2), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (150, 150, 150), 1)
    x = ((P[:, i] - lo_i) * s).astype(int); y = (H - (P[:, j] - lo_j) * s).astype(int)
    ok = (x >= 0) & (x < W) & (y >= 0) & (y < H)
    col = np.zeros((ok.sum(), 3), np.uint8) if a.mono else (P[ok][:, [5, 4, 3]] * 0.7).astype(np.uint8)
    im[y[ok], x[ok]] = col
    for dx, dy in ((1, 0), (0, 1)):
        xx = np.clip(x[ok] + dx, 0, W - 1); yy = np.clip(y[ok] + dy, 0, H - 1); im[yy, xx] = col
    cv2.putText(im, label, (8, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 200), 2)
    return im
A = panel(1, 2, -600, 850, -20, 1320, "side: Y (front ->) vs Z"); B = panel(0, 2, -450, 450, -20, 1320, "front: X (right ->) vs Z")
C = panel(0, 1, -450, 450, -600, 850, "top: X vs Y (front up)")
H = max(A.shape[0], B.shape[0], C.shape[0])
pad = lambda im: cv2.copyMakeBorder(im, 0, H - im.shape[0], 0, 6, cv2.BORDER_CONSTANT, value=(255, 255, 255))
cv2.imwrite(a.out, np.hstack([pad(A), pad(B), pad(C)])); print(len(P), "points drawn")
