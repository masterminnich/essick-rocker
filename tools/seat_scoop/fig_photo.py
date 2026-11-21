"""USAGE: work/toolkit/rk.sh tools/seat_scoop/fig_photo.py PHOTO OUT.jpg SCALE
A labelled crop of one low photo of the seat's right side edge (edge face, hard line, under-bevel, bottom arris, underside); the arrows are placed from parts/seat_scoop.json at station y 250."""
import sys, json, numpy as np, cv2
sys.path.insert(0, ".")
from rocker.cameras import Cameras
from PIL import Image, ImageOps
n, out, sc = sys.argv[1], sys.argv[2], float(sys.argv[3]); c = Cameras.load(); S = json.load(open("parts/seat_scoop.json")); C = np.array(S["right"]["hard_line_xyz"]); B = np.array(S["right"]["bottom_arris_xyz"])
uv = c.project_disp(f"IMG_{n}.JPG", np.r_[C, B, C + [0, 0, 45], B + [-60, 0, 0]]); x0, y0 = (uv.min(0) - [330, 150]).astype(int); x1, y1 = (uv.max(0) + [80, 60]).astype(int)
im = np.array(ImageOps.exif_transpose(Image.open(f"drive/IMG_{n}.JPG")).convert("RGB"))[:, :, ::-1]; x0, y0 = max(x0, 0), max(y0, 0); cr = (255 * (im[y0:y1, x0:x1] / 255.0) ** 0.6).astype(np.uint8)
cr = cv2.resize(cr, (int(cr.shape[1] * sc), int(cr.shape[0] * sc)), interpolation=cv2.INTER_CUBIC)
def lab(txt, at, to):
    at = tuple(int(v) for v in at); to = tuple(int(v) for v in to); cv2.arrowedLine(cr, at, to, (255, 255, 255), 2, cv2.LINE_AA, tipLength=0.06)
    (w, h), _ = cv2.getTextSize(txt, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2); cv2.rectangle(cr, (at[0] - w // 2 - 6, at[1] - h - 12), (at[0] + w // 2 + 6, at[1] + 2), (255, 255, 255), -1); cv2.putText(cr, txt, (at[0] - w // 2, at[1] - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2, cv2.LINE_AA)
P = lambda X: (c.project_disp(f"IMG_{n}.JPG", np.array([X]))[0] - [x0, y0]) * sc
y = 250.0; ip = lambda A, i: float(np.interp(y, A[:, 1], A[:, i])); h = np.array([ip(C, 0), y, ip(C, 2)]); b = np.array([ip(B, 0), y, ip(B, 2)])
for txt, X, off in (("edge face (vertical)", h + [0, 0, 9], (-200, -190)), ("hard line", h + [0, 60, 6], (190, -150)), ("under-bevel (46 deg)", (h + b) / 2, (-330, 60)), ("bottom arris", b + [0, -40, -6], (-140, 190)), ("underside", b + [-40, 60, -8], (300, 60))):
    p = P(X); lab(txt, p + off, p)
cv2.imwrite(out, cr, [cv2.IMWRITE_JPEG_QUALITY, 90]); print(out, cr.shape)
