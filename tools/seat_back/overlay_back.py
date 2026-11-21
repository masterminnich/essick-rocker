"""USAGE: work/toolkit/rk.sh tools/seat_back/overlay_back.py PHOTO OUT.jpg SCALE LABEL=model_edges.json [LABEL=model_edges.json ...]   env GAMMA (0.6), MARGIN (60 px), XLIM (205), HALF (L|R: one half only)
Check figure for the seat's BACK edge: a crop of one photo (displayed pixels x SCALE) around the back edge with the model's SEAT feature edges there drawn in yellow
(from <model>_edges.json; no hidden-line removal, so the far edges of the under-bevel show through the wood), one row per model. The crop is found from
parts/seat_back.json (the measured edges seen through that photo's camera), the same for every row. Nothing measured is drawn: the wood stays visible."""
import sys, json, os, numpy as np, cv2
sys.path.insert(0, ".")
from rocker.cameras import Cameras
from PIL import Image, ImageOps
n, out = sys.argv[1:3]; sc = float(sys.argv[3]); g = float(os.environ.get("GAMMA", 0.6)); mg = int(os.environ.get("MARGIN", 60)); XL = float(os.environ.get("XLIM", 205)); hf = os.environ.get("HALF")
c = Cameras.load(); name = f"IMG_{n}.JPG"; im0 = np.array(ImageOps.exif_transpose(Image.open(f"drive/{name}")).convert("RGB"))[:, :, ::-1]
D = json.load(open("parts/seat_back.json"))["design"]; ax = np.array(D["abs_x"]); ax = ax[ax <= 190]; k = len(ax)
P = np.vstack([np.c_[s * ax, D[e]["y"][:k], D[e]["z"][:k]] for e in ("top_arris", "bottom_arris") for s in ((-1, 1) if not hf else ((1,) if hf == "R" else (-1,)))])
uv = c.project_disp(name, P); x0, y0 = np.floor(uv.min(0) - mg).astype(int); x1, y1 = np.ceil(uv.max(0) + mg).astype(int); x0, y0 = max(x0, 0), max(y0, 0); x1, y1 = min(x1, im0.shape[1]), min(y1, im0.shape[0])
crop = (255 * (im0[y0:y1, x0:x1] / 255.0) ** g).astype(np.uint8); crop = cv2.resize(crop, (int((x1 - x0) * sc), int((y1 - y0) * sc)), interpolation=cv2.INTER_CUBIC); rows = []
for spec in sys.argv[4:]:
    lab, f = spec.split("=", 1); v = crop.copy()
    if f != "none":
        E = [np.array(e["points"]) for e in json.load(open(f)) if e["name"] == "SEAT"]; E = [e for e in E if (np.abs(e[:, 0]) < XL).all() and (e[:, 1] < 75).all() and (not hf or ((1 if hf == "R" else -1) * e[:, 0] > -10).all())]
        for e in E:
            q = (c.project_disp(name, e) - [x0, y0]) * sc; cv2.line(v, tuple(int(round(t)) for t in q[0]), tuple(int(round(t)) for t in q[1]), (0, 255, 255), 1, cv2.LINE_AA)
    cv2.rectangle(v, (0, 0), (14 + 10 * len(lab), 26), (255, 255, 255), -1); cv2.putText(v, lab, (6, 19), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 0), 1, cv2.LINE_AA); rows.append(v)
cv2.imwrite(out, np.vstack(rows), [cv2.IMWRITE_JPEG_QUALITY, 90]); print(out, np.vstack(rows).shape, "crop", x0, y0, x1, y1)
