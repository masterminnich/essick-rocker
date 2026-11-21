"""USAGE: tools/py.sh tools/rear_dominos/overlay.py PHOTO(1502) MODEL.glb MODEL_joinery.json MODEL_edges.json OUT.jpg [HALF_MM 34] [PX_PER_MM 9]
The four Domino ends on the back legs' rear faces (DOMINO_RS* at the seat, DOMINO_RA* at the arm) on ONE photo: for each end a crop
of +-HALF_MM around it, top row the bare photo, bottom row the same crop with the model drawn on it:
  orange = outline of the model Domino's end (convex hull of its vertices within 3 mm of the rear face)
  cyan   = the model's feature edges of the back leg, seat and arm (as traced, before the joints are cut)
Compute: one photo decoded (36 MB), small meshes; < 1 GB, seconds."""
import sys, json; sys.path.insert(0, ".")
import numpy as np, cv2, trimesh
from PIL import Image, ImageOps
from rocker.cameras import Cameras
n, glb, jf, ef, out = sys.argv[1:6]; HALF = float(sys.argv[6]) if len(sys.argv) > 6 else 34.0; PPM = float(sys.argv[7]) if len(sys.argv) > 7 else 9.0
c = Cameras.load(); name = f"IMG_{n}.JPG"; im = np.array(ImageOps.exif_transpose(Image.open(f"drive/{name}")).convert("RGB"))[:, :, ::-1]
G = trimesh.load(glb).geometry; J = json.load(open(jf))["joints"]; E = json.load(open(ef)); cols = []
for key, title in (("DOMINO_RSL", "left leg, at the seat"), ("DOMINO_RSR", "right leg, at the seat"), ("DOMINO_RAL", "left leg, at the arm"), ("DOMINO_RAR", "right leg, at the arm")):
    cen, w = np.array(J[key]["centre_xyz"], float), np.array(J[key]["axis"], float); p0 = c.project_disp(name, cen[None])[0]
    px = np.linalg.norm(c.project_disp(name, (cen + [10.0, 0, 0])[None])[0] - p0) / 10.0; h = HALF * px; x0, y0 = int(p0[0] - h), int(p0[1] - h); sc = PPM / px   # photo px per mm at the end
    crop = np.ascontiguousarray(im[y0:int(p0[1] + h), x0:int(p0[0] + h)]); S = int(round(2 * HALF * PPM)); bare = cv2.resize(crop, (S, S), interpolation=cv2.INTER_CUBIC); mod = bare.copy()
    side = key[-1]
    for e in E:
        if e["name"] not in (f"BLEG_{side}", "SEAT", f"ARM_{side}"): continue
        uv = (c.project_disp(name, np.array(e["points"])) - [x0, y0]) * sc
        if np.abs(uv).max() > 20000: continue
        cv2.line(mod, tuple(int(round(t)) for t in uv[0]), tuple(int(round(t)) for t in uv[1]), (255, 255, 0), 1, cv2.LINE_AA)
    V = np.asarray(G[key].vertices); V = V[(V - cen) @ w < 3.0]; uv = (c.project_disp(name, V) - [x0, y0]) * sc; hull = cv2.convexHull(np.round(uv).astype(np.int32))
    cv2.polylines(mod, [hull], True, (0, 140, 255), 1, cv2.LINE_AA)
    for t, img in ((title, bare), ("model", mod)):
        cv2.rectangle(img, (0, 0), (9 * len(t) + 12, 22), (255, 255, 255), -1); cv2.putText(img, t, (6, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1, cv2.LINE_AA)
    cv2.line(bare, (10, S - 12), (10 + int(round(10 * PPM)), S - 12), (255, 255, 255), 2); cv2.putText(bare, "10 mm", (14, S - 18), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1, cv2.LINE_AA)
    cols.append(np.vstack([bare, np.full((4, S, 3), 255, np.uint8), mod])); print(key, "photo px per mm %.2f" % px, "end hull px", cv2.boundingRect(hull)[2:], "centre", cen.tolist())
gap = np.full((cols[0].shape[0], 4, 3), 255, np.uint8); img = np.hstack([x for col in cols for x in (col, gap)][:-1])
cv2.imwrite(out, img, [cv2.IMWRITE_JPEG_QUALITY, 90]); print("wrote", out, img.shape, name)
