"""USAGE: python -I tools/seat_front_lines.py PHOTO OUT.jpg [--crop X0 Y0 X1 Y1] [--zoom 1.0] [--no-raw] [--glb parts/model_vN.glb]
Draw the measured lines of the seat's front edge (parts/seat_front_face.json) on an ORIGINAL photo through the solved camera:
  yellow   symmetric design: top of the rolled edge and bottom arris of the front face (same line mirrored left and right)
  cyan     the right and left halves as triangulated (before averaging)
  --glb    also the SEAT silhouette of a model, white
A silhouette alone cannot show the bottom arris: from a level camera the pitched underside is in view below it, so the seat's
outline runs along the underside further back. --crop is in displayed pixels (EXIF applied). One photo in memory; tiny compute."""
import sys, json, argparse
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import numpy as np, cv2
from PIL import Image, ImageOps
from rocker.cameras import Cameras
ap = argparse.ArgumentParser(); ap.add_argument("photo"); ap.add_argument("out"); ap.add_argument("--crop", nargs=4, type=int); ap.add_argument("--zoom", type=float, default=1.0)
ap.add_argument("--no-raw", action="store_true"); ap.add_argument("--glb", default=None); ap.add_argument("--label", default=None)
a = ap.parse_args(); cams = Cameras.load(); name = f"IMG_{a.photo}.JPG"
F = json.load(open(ROOT / "parts/seat_front_face.json")); D = F["design"]; r = D["roll_radius_mm"]["value"]; G = np.array(json.load(open(ROOT / "parts/seat_front.json"))["design"]["front_y_of_abs_x"])
img = cv2.cvtColor(np.asarray(ImageOps.exif_transpose(Image.open(ROOT / "drive" / name))), cv2.COLOR_RGB2BGR)
x0, y0, x1, y1 = a.crop or (0, 0, img.shape[1], img.shape[0]); img = cv2.resize(img[y0:y1, x0:x1], None, fx=a.zoom, fy=a.zoom, interpolation=cv2.INTER_CUBIC)


def draw(P, col, th):
    uv = (cams.project_disp(name, np.asarray(P, float)) - [x0, y0]) * a.zoom
    if np.isfinite(uv).all(): cv2.polylines(img, [np.round(uv * 8).astype(np.int32)], False, col, th, cv2.LINE_AA, 3)


if a.glb:
    import trimesh
    g = trimesh.load(a.glb).geometry["SEAT"]; uv = (cams.project_disp(name, np.asarray(g.vertices)) - [x0, y0]) * a.zoom; m = np.zeros(img.shape[:2], np.uint8)
    for tr in np.round(uv[np.asarray(g.faces)]).astype(np.int32): cv2.fillConvexPoly(m, tr, 255)     # one by one: fillPoly on a list fills by the even-odd rule
    cs, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE); cv2.drawContours(img, cs, -1, (255, 255, 255), 1, cv2.LINE_AA)
if not a.no_raw:
    for side, sg in (("right", 1), ("left", -1)):
        S = F[side]; t = np.array(S["top_of_roll_z"]); ty = np.array(S["top_plan_outline_y"]); b = np.array(S["bottom_arris_z"]); by = np.array(S["bottom_arris_y"])
        draw(np.c_[sg * t[:, 0], ty[:, 1] - r, t[:, 1]], (255, 255, 0), 1); draw(np.c_[sg * b[:, 0], by[:, 1], b[:, 1]], (255, 255, 0), 1)
t = np.array(D["top_of_roll_z_of_abs_x"]); b = np.array(D["bottom_arris_z_of_abs_x"]); by = np.array(D["bottom_arris_y_of_abs_x"])
for sg in (1, -1):
    draw(np.c_[sg * t[:, 0], np.interp(t[:, 0], G[:, 0], G[:, 1]) - r, t[:, 1]], (0, 255, 255), 2); draw(np.c_[sg * b[:, 0], by[:, 1], b[:, 1]], (0, 255, 255), 2)
if a.label: cv2.putText(img, a.label, (12, 34), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2, cv2.LINE_AA)
cv2.imwrite(a.out, img, [cv2.IMWRITE_JPEG_QUALITY, 86]); print(a.out, img.shape)
