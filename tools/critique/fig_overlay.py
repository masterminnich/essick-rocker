"""USAGE: tools/py.sh tools/critique/fig_overlay.py RUNDIR PHOTO PART OUT.jpg [--near X Y Z] [--radius MM] [--pxmm 10] [--title TEXT]
By-eye check of the critique on ONE photo: a crop of the photo around the chosen outline stretch, enlarged to --pxmm pixels
per mm at the part, with every outline point of PART within --radius mm of --near (default: all of the part's measured
points; then the crop covers them):
  white dot + short white tick   the model's outline point and its outward normal (the tick is 2 mm long),
  blue dot                       the wood edge the tool found (accepted point), joined to its model point,
  orange dot                     a found edge the tool rejected (low contrast / ambiguous / at the band's end),
  grey dot                       a model point dropped before the search (hidden, not clean, oblique, too few px/mm).
Shown in the photo's display orientation. Gap legend: + = model outside the wood."""
import sys, argparse
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, PARTS  # noqa
import numpy as np, cv2
from PIL import Image, ImageOps
from rocker.cameras import Cameras

ap = argparse.ArgumentParser(); ap.add_argument("run"); ap.add_argument("photo"); ap.add_argument("part"); ap.add_argument("out")
ap.add_argument("--near", nargs=3, type=float); ap.add_argument("--radius", type=float, default=40); ap.add_argument("--pxmm", type=float, default=10)
ap.add_argument("--title", default=None); ap.add_argument("--kind", default="all")
a = ap.parse_args()
name = f"IMG_{a.photo}.JPG" if a.photo.isdigit() else a.photo
R = dict(np.load(Path(a.run) / f"{name[:-4]}.npz"))
cams = Cameras.load()
sel = R["part"] == PARTS.index(a.part)
if a.kind != "all": sel &= R["kind"] == {"sil": 1, "crease": 2}[a.kind]
if a.near: sel &= np.linalg.norm(R["X"] - np.array(a.near), axis=1) < a.radius
else: sel &= R["st"] == 0
idx = np.nonzero(sel)[0]
if not len(idx): sys.exit(f"no points of {a.part} there in {name}")
uv = R["uv"][idx].astype(float); nn = R["nimg"][idx].astype(float); px = R["pxmm"][idx].astype(float); st = R["st"][idx]; gap = R["gap"][idx]
found = uv - (gap * px)[:, None] * nn                      # gap = -t  ->  edge at uv + t*px*n
tick = uv + (2.0 * px)[:, None] * nn
D = lambda p: cams.raw_to_disp(name, p)
U, F, Tk = D(uv), D(found), D(tick)
pm = float(np.median(px)); sc = a.pxmm / pm; pad = 12 * pm
im = np.array(ImageOps.exif_transpose(Image.open(ROOT / "drive" / name)).convert("RGB"))[:, :, ::-1]
x0, y0 = np.maximum((U.min(0) - pad).astype(int), 0); x1, y1 = (U.max(0) + pad).astype(int); x1, y1 = min(x1, im.shape[1]), min(y1, im.shape[0])
cr = cv2.resize(im[y0:y1, x0:x1], (int((x1 - x0) * sc), int((y1 - y0) * sc)), interpolation=cv2.INTER_CUBIC)
P = lambda p: tuple(np.round((p - [x0, y0]) * sc).astype(int))
WHITE, BLUE, ORANGE, GREY = (250, 250, 250), (214, 120, 42), (52, 104, 235), (150, 150, 150)
for i in range(len(idx)):
    if st[i] >= 10:
        cv2.circle(cr, P(U[i]), 3, GREY, -1, cv2.LINE_AA); continue
    cv2.line(cr, P(U[i]), P(Tk[i]), WHITE, 1, cv2.LINE_AA)
    col = BLUE if st[i] == 0 else ORANGE
    cv2.line(cr, P(U[i]), P(F[i]), col, 1, cv2.LINE_AA)
    cv2.circle(cr, P(F[i]), 4, col, -1, cv2.LINE_AA); cv2.circle(cr, P(U[i]), 3, WHITE, -1, cv2.LINE_AA)
ok = st == 0
title = a.title or f"{name[:-4]}  {a.part}"
info = f"{ok.sum()} measured / {(st < 10).sum()} searched / {len(idx)} outline points;  median gap {np.nanmedian(gap[ok]) if ok.any() else float('nan'):+.2f} mm (+ = model outside the wood);  photo {pm:.1f} px/mm, shown at {a.pxmm:.0f}"
H = 92; W = max(cr.shape[1], 1500)
head = np.full((H, W, 3), (251, 252, 252), np.uint8)
cv2.putText(head, title, (14, 36), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (11, 11, 11), 2, cv2.LINE_AA)
cv2.putText(head, info, (14, 74), cv2.FONT_HERSHEY_SIMPLEX, 0.62, (82, 81, 78), 1, cv2.LINE_AA)
leg = [("model outline (tick = outward, 2 mm)", WHITE), ("wood edge found", BLUE), ("found, rejected", ORANGE), ("not searched", GREY)]
x = W - 10
for t, c in leg[::-1]:
    w = cv2.getTextSize(t, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 1)[0][0]; x -= w + 30
    cv2.circle(head, (x, 30), 7, c if c != WHITE else (60, 60, 60), -1, cv2.LINE_AA); cv2.putText(head, t, (x + 12, 36), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (11, 11, 11), 1, cv2.LINE_AA)
body = np.full((cr.shape[0], W, 3), 252, np.uint8); body[:, :cr.shape[1]] = cr
cv2.imwrite(a.out, np.vstack([head, body]), [cv2.IMWRITE_JPEG_QUALITY, 88]); print(a.out, cr.shape, f"median gap {np.nanmedian(gap[ok]) if ok.any() else float('nan'):+.2f}")
