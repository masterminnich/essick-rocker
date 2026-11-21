"""USAGE: work/toolkit/rk.sh tools/seat_side_ends/check.py SIDE(L|R) TAG Y0 Y1 OUT.jpg PHOTO [PHOTO ...]   env PXMM (12), GAMMA (0.6), MODEL (work/seatside/v22_outline.json)
By-eye check of the seat's side-edge top arris (plan outline) at one END of the side, on SINGLE photos at PXMM displayed px per mm:
a crop of the original photo around the stretch y Y0..Y1, with
  orange = this photo's own trace (tools/edge_tri.py --dump, sheet point projected back: exactly the pixels it picked),
  cyan dots = the triangulated arris (TAG.json, all photos), every 2 mm, ticks every 10 mm of y,
  yellow = the model's plan outline (MODEL: max |x| of the SEAT section per y, at that point's z).
One panel per photo, side by side. Tiny compute (one photo decoded at a time)."""
import sys, json, os, numpy as np, cv2
sys.path.insert(0, ".")
from rocker.cameras import Cameras
from rocker.surface import load_surface
from PIL import Image, ImageOps
side, tag, y0, y1, out = sys.argv[1], sys.argv[2], float(sys.argv[3]), float(sys.argv[4]), sys.argv[5]; photos = sys.argv[6:]
pxmm = float(os.environ.get("PXMM", 12)); g = float(os.environ.get("GAMMA", 0.6)); sg = 1 if side == "R" else -1
c = Cameras.load(); pj = json.load(open(f"work/parts/side{side}/sp_plane.json")); S = load_surface(pj)
R = json.load(open(f"work/seatside/{tag}.json")); X = np.array(R[f"seat{side}_plan_xyz"]); X = X[np.argsort(X[:, 1])]
D = json.load(open(f"work/seatside/{tag}_dump.json"))
mo = json.load(open(os.environ.get("MODEL", "work/seatside/v22_outline.json"))); M = np.array([[r["x" + side], r["y"], r["z" + side]] for r in mo])
sel = lambda A: A[(A[:, 1] >= y0 - 3) & (A[:, 1] <= y1 + 3)]
panels = []
for n in photos:
    name = f"IMG_{n}.JPG"; k = f"seat{side}_plan@{n}"
    if k not in D: continue
    T3 = S.to3d(np.array(D[k])); T3 = sel(T3); Xs = sel(X); Ms = sel(M)
    uX = c.project_disp(name, Xs); uT = c.project_disp(name, T3); uM = c.project_disp(name, Ms)
    mmpx = np.median(np.linalg.norm(np.diff(uX, axis=0), axis=1) / np.linalg.norm(np.diff(Xs, axis=0), axis=1)); sc = pxmm / mmpx
    lo = np.r_[uX, uM].min(0) - 12 / mmpx * 0 - 40; hi = np.r_[uX, uM].max(0) + 40
    im = np.array(ImageOps.exif_transpose(Image.open(f"drive/{name}")).convert("RGB"))[:, :, ::-1]
    x0, yy0 = [int(max(v, 0)) for v in lo]; x1, yy1 = int(min(hi[0], im.shape[1])), int(min(hi[1], im.shape[0]))
    cr = (255 * (im[yy0:yy1, x0:x1] / 255.0) ** g).astype(np.uint8); cr = cv2.resize(cr, (int((x1 - x0) * sc), int((yy1 - yy0) * sc)), interpolation=cv2.INTER_CUBIC)
    P = lambda u: [tuple(int(round(t)) for t in p) for p in (u - [x0, yy0]) * sc]
    for a, b in zip(P(uM)[:-1], P(uM)[1:]): cv2.line(cr, a, b, (0, 230, 255), 1, cv2.LINE_AA)
    for a, b in zip(P(uT)[:-1], P(uT)[1:]): cv2.line(cr, a, b, (0, 128, 255), 1, cv2.LINE_AA)
    for i, p in enumerate(P(uX)):
        if i % 2 == 0: cv2.circle(cr, p, 2, (255, 255, 0), -1, cv2.LINE_AA)
    for yt in np.arange(np.ceil(y0 / 10) * 10, y1 + 1, 10):
        p = P(c.project_disp(name, np.array([[np.interp(yt, X[:, 1], X[:, 0]), yt, np.interp(yt, X[:, 1], X[:, 2])]])))[0]
        cv2.putText(cr, f"y{yt:.0f}", (p[0] + 6, p[1] - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1, cv2.LINE_AA)
    cv2.putText(cr, f"IMG_{n} {pxmm:.0f} px/mm", (6, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2, cv2.LINE_AA)
    panels.append(cr)
h = max(p.shape[0] for p in panels); panels = [cv2.copyMakeBorder(p, 0, h - p.shape[0], 0, 8, cv2.BORDER_CONSTANT, value=(40, 40, 40)) for p in panels]
img = np.hstack(panels)
if os.environ.get("LEGEND", "1") == "1":   # key strip under the panels
    bar = np.full((34, img.shape[1], 3), 40, np.uint8); x = 10
    for col, txt, dot in (((0, 128, 255), "this photo's own trace", 0), ((255, 255, 0), "triangulated arris, all photos (every 2 mm)", 1), ((0, 230, 255), "model v22 plan outline", 0)):
        if dot: cv2.circle(bar, (x + 12, 17), 3, col, -1, cv2.LINE_AA)
        else: cv2.line(bar, (x, 17), (x + 24, 17), col, 2, cv2.LINE_AA)
        cv2.putText(bar, txt, (x + 32, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (235, 235, 235), 1, cv2.LINE_AA); x += 32 + 9 * len(txt) + 30
    img = np.vstack([img, bar])
cv2.imwrite(out, img, [cv2.IMWRITE_JPEG_QUALITY, 88]); print(out, img.shape)
