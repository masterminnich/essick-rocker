"""USAGE: work/toolkit/rk.sh tools/seat_roll/view.py PHOTO OUT.jpg --at X Y Z [--half 40] [--pxmm 12] [--lines a.json,...] [--label TEXT]
By-eye check on ONE original photo: a crop around the chair point (X, Y, Z) (mm, chair frame), enlarged to --pxmm pixels per mm
at that point, shown in display orientation, with:
  yellow  the seat front's design lines (parts/seat_front_face.json: top of the roll, bottom arris; both halves),
  cyan    the side-arris underside plane (parts/seat_edge.json bottom_z_of_y) carried forward to the front outline,
  extra   polylines from --lines files ({"name": [[x, y, z], ...], ...}, drawn in orange, blue, green ...),
  a 5 mm scale bar at the crop's px/mm. One photo in memory; tiny compute."""
import sys, json, argparse
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]; sys.path.insert(0, str(ROOT))
import numpy as np, cv2
from PIL import Image, ImageOps
from rocker.cameras import Cameras
ap = argparse.ArgumentParser(); ap.add_argument("photo"); ap.add_argument("out"); ap.add_argument("--at", nargs=3, type=float, required=True)
ap.add_argument("--half", type=float, default=40); ap.add_argument("--pxmm", type=float, default=12); ap.add_argument("--lines", default="")
ap.add_argument("--label", default=None); ap.add_argument("--no-design", action="store_true")
a = ap.parse_args(); cams = Cameras.load(); name = f"IMG_{a.photo}.JPG"; V = cams[name]
P0 = np.array(a.at); u0 = cams.project_disp(name, P0)[0]
ray = P0 - V.center; ray /= np.linalg.norm(ray); q = np.cross(ray, [0, 0, 1.0]); q /= np.linalg.norm(q)
pm = float(np.linalg.norm(cams.project_disp(name, P0 + q)[0] - u0))          # native px per mm at the point, square to the ray
img = np.asarray(ImageOps.exif_transpose(Image.open(ROOT / "drive" / name)).convert("RGB"))[:, :, ::-1]
h = a.half * pm; x0, y0 = int(max(u0[0] - h * 1.6, 0)), int(max(u0[1] - h, 0)); x1, y1 = int(min(u0[0] + h * 1.6, img.shape[1])), int(min(u0[1] + h, img.shape[0]))
sc = a.pxmm / pm; cr = cv2.resize(np.ascontiguousarray(img[y0:y1, x0:x1]), (int((x1 - x0) * sc), int((y1 - y0) * sc)), interpolation=cv2.INTER_CUBIC)
def draw(P, col, th=1):
    uv = (cams.project_disp(name, np.asarray(P, float)) - [x0, y0]) * sc
    if np.isfinite(uv).all(): cv2.polylines(cr, [np.round(uv * 8).astype(np.int32)], False, col, th, cv2.LINE_AA, 3)
F = json.load(open(ROOT / "parts/seat_front_face.json"))["design"]; G = np.array(json.load(open(ROOT / "parts/seat_front.json"))["design"]["front_y_of_abs_x"])
r = F["roll_radius_mm"]["value"]; t = np.array(F["top_of_roll_z_of_abs_x"]); b = np.array(F["bottom_arris_z_of_abs_x"]); by = np.array(F["bottom_arris_y_of_abs_x"])
E = json.load(open(ROOT / "parts/seat_edge.json"))["design"]["bottom_z_of_y"]["poly_in_(y-250)"]
xs = np.linspace(0, 262, 132)
if not a.no_design:
    for sg in (1, -1):
        draw(np.c_[sg * t[:, 0], np.interp(t[:, 0], G[:, 0], G[:, 1]) - r, t[:, 1]], (0, 230, 255))
        draw(np.c_[sg * b[:, 0], by[:, 1], b[:, 1]], (0, 230, 255))
        yy = np.interp(xs, G[:, 0], G[:, 1]); draw(np.c_[sg * xs, yy, np.polyval(E, yy - 250)], (255, 230, 0))
cols = [(30, 120, 235), (214, 120, 42), (60, 190, 60), (200, 200, 200)]
for i, f in enumerate([f for f in a.lines.split(",") if f]):
    for k, P in json.load(open(f)).items(): draw(P, cols[i % len(cols)])
cv2.line(cr, (12, cr.shape[0] - 14), (12 + int(5 * a.pxmm), cr.shape[0] - 14), (255, 255, 255), 3)
cv2.putText(cr, "5 mm", (16 + int(5 * a.pxmm), cr.shape[0] - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1, cv2.LINE_AA)
lab = (a.label or f"IMG_{a.photo}") + f"  native {pm:.1f} px/mm, shown at {a.pxmm:g}"
cv2.putText(cr, lab, (12, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2, cv2.LINE_AA)
cv2.imwrite(a.out, cr, [cv2.IMWRITE_JPEG_QUALITY, 88]); print(a.out, cr.shape, f"{pm:.2f} px/mm")
