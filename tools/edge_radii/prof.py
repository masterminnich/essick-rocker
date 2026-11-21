"""USAGE: work/toolkit/rk.sh tools/edge_radii/prof.py IMG X0 Y0 X1 Y1 HALF OUT_PREFIX [--side +1|-1]
Phase 6c: tone profile ACROSS an edge in one photo (display orientation, EXIF applied; pixel coordinates of that image).
(X0,Y0)-(X1,Y1) is a line drawn ALONG the edge (by eye, on a gridded crop); the profile is sampled square to it from -HALF
to +HALF px in 0.25 px steps and averaged along the line (every 0.5 px). --side +1 means the part lies on the + side
(left of the direction X0->X1 when y points down... simply: the side the wood is on, checked on the crop it writes).
Writes OUT_PREFIX.json (t px, L*, a*, b* and |d Lab/dt|, Gaussian sigma 1 px) and OUT_PREFIX_crop.jpg (the straightened
strip, 8x, with the t axis ticks every 10 px)."""
import sys, json, argparse
import numpy as np, cv2
from scipy.ndimage import gaussian_filter1d

ap = argparse.ArgumentParser()
ap.add_argument("img"); ap.add_argument("x0", type=float); ap.add_argument("y0", type=float)
ap.add_argument("x1", type=float); ap.add_argument("y1", type=float); ap.add_argument("half", type=float)
ap.add_argument("out")
a = ap.parse_args()
im = cv2.imread(f"drive/IMG_{a.img}.JPG")
lab = cv2.cvtColor(im, cv2.COLOR_BGR2Lab).astype(np.float32)
p0, p1 = np.array([a.x0, a.y0]), np.array([a.x1, a.y1])
L = np.linalg.norm(p1 - p0); e = (p1 - p0) / L; n = np.array([-e[1], e[0]])
s = np.arange(0, L, 0.5); t = np.arange(-a.half, a.half + 1e-6, 0.25)
mx = (p0[0] + s[:, None] * e[0] + t[None, :] * n[0]).astype(np.float32)
my = (p0[1] + s[:, None] * e[1] + t[None, :] * n[1]).astype(np.float32)
P = cv2.remap(lab, mx, my, cv2.INTER_LINEAR)            # (len s, len t, 3)
prof = P.mean(0)
g = np.linalg.norm(gaussian_filter1d(prof, 4.0, axis=0, order=1), axis=1) / 0.25
json.dump(dict(img=a.img, line=[a.x0, a.y0, a.x1, a.y1], normal=n.tolist(), t=t[::2].round(2).tolist(),
               L=prof[::2, 0].round(1).tolist(), a=prof[::2, 1].round(1).tolist(), b=prof[::2, 2].round(1).tolist(),
               grad=g[::2].round(2).tolist()), open(a.out + ".json", "w"))
strip = cv2.cvtColor(P[:120].astype(np.uint8), cv2.COLOR_Lab2BGR)
strip = cv2.resize(strip, (strip.shape[1] * 2, strip.shape[0] * 2), interpolation=cv2.INTER_NEAREST)   # t: 0.25 px -> 2 px
for tt in range(int(-a.half), int(a.half) + 1, 10):
    X = int((tt + a.half) / 0.25 * 2)
    cv2.line(strip, (X, 0), (X, 12), (0, 255, 255), 1); cv2.putText(strip, str(tt), (X + 2, 24), 0, 0.4, (0, 255, 255), 1)
cv2.imwrite(a.out + "_crop.jpg", strip)
print(f"normal (display px) {n.round(3).tolist()}, length {L:.0f} px, profile {len(t)} samples")
