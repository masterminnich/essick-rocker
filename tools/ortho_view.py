"""USAGE: python -I tools/ortho_view.py PREFIX [--img median|spread|<photo>] [--scale 1.0] [--grid 50] [--window U0 U1 V0 V1]
            [--curves FILE.json] [--out PATH]
View a face orthophoto (from tools/face_ortho.py) with a grid labelled in plane millimetres (u right, v up), optionally
with traced curves drawn (JSON: {"name": [[u, v], ...], ...}). For reading coordinates and checking traces. Tiny compute."""
import json, argparse, numpy as np, cv2
ap = argparse.ArgumentParser(); ap.add_argument("prefix"); ap.add_argument("--img", default="median"); ap.add_argument("--scale", type=float, default=1.0)
ap.add_argument("--grid", type=float, default=50); ap.add_argument("--window", nargs=4, type=float, default=None); ap.add_argument("--curves", default=None)
ap.add_argument("--out", default=None); ap.add_argument("--thick", type=int, default=1)
a = ap.parse_args()
pj = json.load(open(a.prefix + "_plane.json")); res = pj["res"]; (u0, u1), (v0, v1) = pj["urange"], pj["vrange"]
im = cv2.imread(f"{a.prefix}_{a.img}.png")
W = a.window or [u0, u1, v0, v1]
c0, c1 = int((W[0] - u0) / res), int((W[1] - u0) / res); r0, r1 = int((v1 - W[3]) / res), int((v1 - W[2]) / res)
im = im[max(r0, 0):r1, max(c0, 0):c1]
s = a.scale; im = cv2.resize(im, None, fx=s, fy=s, interpolation=cv2.INTER_AREA if s < 1 else cv2.INTER_CUBIC)
def px(u, v): return int(round((u - W[0]) / res * s)), int(round((W[3] - v) / res * s))
g = a.grid
for uu in np.arange(np.ceil(W[0] / g) * g, W[1], g):
    x, _ = px(uu, 0); cv2.line(im, (x, 0), (x, im.shape[0]), (255, 255, 0), 1); cv2.putText(im, f"{uu:g}", (x + 2, 12), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 255), 1)
for vv in np.arange(np.ceil(W[2] / g) * g, W[3], g):
    _, y = px(0, vv); cv2.line(im, (0, y), (im.shape[1], y), (255, 255, 0), 1); cv2.putText(im, f"{vv:g}", (2, y - 2), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 255), 1)
if a.curves:
    cols = [(0, 0, 255), (0, 255, 0), (255, 0, 255), (0, 165, 255), (255, 0, 0)]
    for k, (name, pts) in enumerate(json.load(open(a.curves)).items()):
        if not isinstance(pts, list) or not pts or not isinstance(pts[0], list): continue
        q = np.array([px(u, v) for u, v in pts], np.int32); cv2.polylines(im, [q], False, cols[k % len(cols)], a.thick)
out = a.out or f"{a.prefix}_view.jpg"; cv2.imwrite(out, im); print(out, im.shape)
