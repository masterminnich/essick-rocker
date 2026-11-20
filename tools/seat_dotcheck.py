"""USAGE: tools/py.sh -t 5 tools/seat_dotcheck.py IMG_1604 [IMG_...]
Check view: detections in a dot photo, GREEN = used by a triangulated dot (with the dot id), RED = not used;
cyan cross = the dot's 3D position projected back; magenta = dots that did not use this photo, projected. Half size, displayed orientation -> work/seat/det/use_<name>.jpg"""
import sys, csv; from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent; sys.path.insert(0, str(ROOT))
import numpy as np, cv2
from PIL import Image
from scipy.spatial import cKDTree
from rocker.seatcams import load
from rocker.orientation import exif_orientation
cams = load(); R = list(csv.DictReader(open(ROOT / "seat/dots.csv")))
X = np.array([[float(r[k]) for k in ("x_mm", "y_mm", "z_mm")] for r in R])
for n in sys.argv[1:]:
    n = n if n.endswith(".JPG") else n + ".JPG"; v = cams[n]
    d = np.load(ROOT / f"work/seat/det/{n[:-4]}.npz")["uv"]
    use = [i for i, r in enumerate(R) if n[4:8] in r["photos"].split()]
    uv = v.project(X)
    j = cKDTree(d).query(uv[use])[1] if len(use) else []
    used = set(int(x) for x in j)
    im = Image.open(cams.drive / n); im.draft("RGB", (2016, 1512)); im = np.asarray(im.convert("RGB"))[:, :, ::-1].copy()
    s = im.shape[1] / 4032
    for k, p in enumerate(d):
        c = (0, 220, 0) if k in used else (0, 0, 255); cv2.circle(im, tuple((p * s).astype(int)), 10, c, 2)
    allv = [i for i in range(len(X)) if i not in use and v.in_image(uv[i][None])[0]]
    for i in allv:      # dots NOT using this photo: magenta cross where they project
        p = (uv[i] * s).astype(int); cv2.drawMarker(im, tuple(p), (255, 0, 255), cv2.MARKER_CROSS, 10, 2)
        cv2.putText(im, str(i), (p[0] + 10, p[1] + 14), 0, 0.45, (255, 0, 255), 1)
    for i in use:
        p = (uv[i] * s).astype(int); cv2.drawMarker(im, tuple(p), (255, 255, 0), cv2.MARKER_CROSS, 8, 1)
        cv2.putText(im, str(i), (p[0] + 10, p[1] + 14), 0, 0.45, (255, 255, 0), 1)
    img = Image.fromarray(im[:, :, ::-1]); tr = {3: Image.ROTATE_180, 6: Image.ROTATE_270, 8: Image.ROTATE_90}.get(exif_orientation(str(cams.drive / n)))
    if tr is not None: img = img.transpose(tr)
    img.save(ROOT / f"work/seat/det/use_{n[:-4]}.jpg", quality=85); print(n, "detections", len(d), "used", len(used))
