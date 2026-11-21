"""USAGE: work/toolkit/rk.sh tools/seat_scoop/overlay_edge.py PHOTO OUT.jpg "X0 Y0 X1 Y1" SCALE LABEL=model_edges.json [LABEL=model_edges.json ...]   env SIDE (R), GAMMA (0.6), MEAS=parts/seat_scoop.json
Check figure for the seat's side edge: a crop of one photo (full-resolution displayed pixels) with the model's SEAT feature edges on that side drawn (yellow, from
<model>_edges.json, no hidden-line removal), one row per model. With MEAS the measured hard line (magenta dots) and bottom arris (orange dots) are added: with SIDE=L the left side's own ("left", PR #26), else the right side (mirrored for SIDE=L)."""
import sys, json, os, numpy as np, cv2
sys.path.insert(0, ".")
from rocker.cameras import Cameras
from PIL import Image, ImageOps
n, out = sys.argv[1:3]; x0, y0, x1, y1 = [int(v) for v in sys.argv[3].split()]; sc = float(sys.argv[4]); side = os.environ.get("SIDE", "R"); sg = 1 if side == "R" else -1; g = float(os.environ.get("GAMMA", 0.6))
c = Cameras.load(); name = f"IMG_{n}.JPG"; im0 = np.array(ImageOps.exif_transpose(Image.open(f"drive/{name}")).convert("RGB"))[:, :, ::-1]
crop = (255 * (im0[y0:y1, x0:x1] / 255.0) ** g).astype(np.uint8); crop = cv2.resize(crop, (int((x1 - x0) * sc), int((y1 - y0) * sc)), interpolation=cv2.INTER_CUBIC); rows = []
MJ = json.load(open(os.environ["MEAS"])) if os.environ.get("MEAS") else None; mk = "left" if side == "L" and MJ and "left" in MJ else "right"; M = MJ[mk] if MJ else None   # the left side is stored in the chair frame (x negative)
for spec in sys.argv[5:]:
    lab, f = spec.split("=", 1); v = crop.copy(); E = [np.array(e["points"]) for e in json.load(open(f)) if e["name"] == "SEAT"]
    E = [e for e in E if (sg * e[:, 0] > 150).all() and (e[:, 1] > 60).all() and (e[:, 1] < 480).all()]
    for e in E:
        uv = (c.project_disp(name, e) - [x0, y0]) * sc; cv2.line(v, tuple(int(round(t)) for t in uv[0]), tuple(int(round(t)) for t in uv[1]), (0, 255, 255), 1, cv2.LINE_AA)
    if M:
        for key, col in (("hard_line_xyz", (255, 0, 255)), ("bottom_arris_xyz", (0, 128, 255))):
            P = np.array(M[key])[::2] * ([1, 1, 1] if mk == "left" else [sg, 1, 1])
            for p in (c.project_disp(name, P) - [x0, y0]) * sc: cv2.circle(v, (int(round(p[0])), int(round(p[1]))), 2, col, -1, cv2.LINE_AA)
    cv2.rectangle(v, (0, 0), (14 + 10 * len(lab), 26), (255, 255, 255), -1); cv2.putText(v, lab, (6, 19), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 0), 1, cv2.LINE_AA); rows.append(v)
cv2.imwrite(out, np.vstack(rows), [cv2.IMWRITE_JPEG_QUALITY, 90]); print(out, np.vstack(rows).shape)
