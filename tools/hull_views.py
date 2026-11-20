"""USAGE: python -I tools/hull_views.py --npz parts/hull_v1.npz --out work/hull_views.jpg [--keep 0.88]
Side / front / top views of the hull vote grid: grey level = how many voxels along the view axis are 'chair'
(so thin parts are light, thick or leaked regions dark). 100 mm grid. Tiny compute."""
import argparse, numpy as np, cv2
ap = argparse.ArgumentParser(); ap.add_argument("--npz", required=True); ap.add_argument("--out", required=True); ap.add_argument("--keep", type=float, default=0.88)
a = ap.parse_args(); z = np.load(a.npz); occ = z["F"] > a.keep; lo = z["lo"]; vox = float(z["voxel"])
def panel(axis, label):
    t = occ.sum(axis).astype(np.float32) * vox                       # thickness in mm along the view axis
    im = 255 - np.clip(t / 120 * 255, 0, 255).astype(np.uint8)
    if axis == 0: im = im.T[::-1]; h0, v0 = lo[1], lo[2]             # side: y right, z up
    elif axis == 1: im = im.T[::-1]; h0, v0 = lo[0], lo[2]           # front: x right, z up
    else: im = im.T[::-1]; h0, v0 = lo[0], lo[1]                     # top: x right, y up
    im = cv2.cvtColor(np.ascontiguousarray(im), cv2.COLOR_GRAY2BGR); H, W = im.shape[:2]
    for g in range(-500, 1200, 100):
        x = int((g - h0) / vox); y = H - int((g - v0) / vox)
        if 0 <= x < W: cv2.line(im, (x, 0), (x, H), (255, 200, 120), 1); cv2.putText(im, str(g), (x + 2, 10), cv2.FONT_HERSHEY_SIMPLEX, 0.3, (200, 80, 0), 1)
        if 0 <= y < H: cv2.line(im, (0, y), (W, y), (255, 200, 120), 1); cv2.putText(im, str(g), (2, y - 2), cv2.FONT_HERSHEY_SIMPLEX, 0.3, (200, 80, 0), 1)
    cv2.putText(im, label, (40, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 220), 1); return im
P = [panel(0, "side"), panel(1, "front"), panel(2, "top")]; H = max(p.shape[0] for p in P)
cv2.imwrite(a.out, np.hstack([cv2.copyMakeBorder(p, 0, H - p.shape[0], 0, 6, cv2.BORDER_CONSTANT, value=(255, 255, 255)) for p in P]))
