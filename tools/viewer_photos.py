"""USAGE: work/toolkit/rk.sh tools/viewer_photos.py [--long 1600] [--quality 82] [--only 1485,1502] [--out viewer/photos]
Export every solved photo for the browser viewer (viewer/): undistorted, turned upright (EXIF orientation applied) and
resampled into an ideal pinhole camera with the principal point at the image centre, so a plain three.js
PerspectiveCamera (position C, rotation R, vertical fov from f) reproduces it exactly. Writes
  <out>/IMG_xxxx.jpg            the resampled photo (long side --long px)
  <out>/cameras.json            {"IMG_xxxx": {"w", "h", "f" (px), "C" (camera centre, chair mm), "R" (3x3 rows = camera
                                 x right, y down, z forward, in the chair frame; OpenCV convention)}}
The viewer projects these photos onto its X/Y/Z planes ("rectified" backdrops) on the GPU, and uses them as-is in
photo-match mode. Re-run only when the camera solve or the photo set changes; models do not need it.
Compute: one photo decoded at a time (36 MB) + a remap grid of ~2 MP floats; < 0.5 GB, ~1 s per photo, single thread OK."""
import sys, json, argparse
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import numpy as np, cv2
from rocker.cameras import Cameras
from rocker.ortho import load_raw
from rocker.orientation import raw_to_disp, disp_size

ap = argparse.ArgumentParser(); ap.add_argument("--long", type=int, default=1600); ap.add_argument("--quality", type=int, default=82)
ap.add_argument("--only", default=None); ap.add_argument("--out", default=str(ROOT / "viewer/photos"))
a = ap.parse_args()
cams = Cameras.load(); out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
names = sorted(cams.views) if not a.only else [f"IMG_{n}.JPG" for n in a.only.split(",")]
cj = out / "cameras.json"; table = json.loads(cj.read_text()) if cj.exists() and a.only else {}

for name in names:
    vw = cams[name]
    Wd, Hd = disp_size(vw.orient)                                     # displayed size of the original (e.g. 3024 x 4032)
    s = a.long / max(Wd, Hd); W, H = int(round(Wd * s)), int(round(Hd * s)); f = vw.focal_raw * s
    # display axes expressed in the raw camera frame: d(disp) = J d(raw), J orthogonal -> display x axis = J[0], y = J[1]
    o = raw_to_disp(np.array([[100.0, 100.0], [101.0, 100.0], [100.0, 101.0]]), vw.orient)
    J = np.array([o[1] - o[0], o[2] - o[0]]).T                        # columns = disp delta of raw +x, raw +y
    M = np.eye(3); M[0, :2], M[1, :2] = J[0], J[1]                    # rows: virtual cam axes in raw-cam coords
    if np.linalg.det(M) < 0: raise SystemExit(f"{name}: mirrored EXIF orientation {vw.orient} not supported")
    R = M @ vw.R_chair                                                # chair -> virtual camera
    C = vw.center
    uu, vv = np.meshgrid(np.arange(W) + 0.5, np.arange(H) + 0.5)      # pixel centres, continuous coords
    d = np.stack([(uu - W / 2) / f, (vv - H / 2) / f, np.ones_like(uu)], -1).reshape(-1, 3)
    X = C + (d @ R) * 1000.0                                          # R^T d, 1 m out along each ray
    uv = vw.project(X).reshape(H, W, 2).astype(np.float32)            # raw distorted pixels (index convention)
    raw = load_raw(cams, name)
    img = cv2.remap(raw, uv[..., 0], uv[..., 1], cv2.INTER_AREA if s < 0.5 else cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    if s < 0.5:                                                       # remap has no area filter: pre-blur against aliasing
        img = cv2.remap(cv2.GaussianBlur(raw, (0, 0), 0.5 / s), uv[..., 0], uv[..., 1], cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    del raw
    key = name[:-4]
    cv2.imwrite(str(out / f"{key}.jpg"), img, [cv2.IMWRITE_JPEG_QUALITY, a.quality, cv2.IMWRITE_JPEG_PROGRESSIVE, 1])
    table[key] = {"w": W, "h": H, "f": round(float(f), 3), "C": [round(float(x), 3) for x in C], "R": [[round(float(x), 7) for x in r] for r in R]}
    print(f"{key} {W}x{H} f={f:.1f}", flush=True)

cj.write_text(json.dumps(table, indent=0))
print("wrote", len(table), "cameras ->", cj)
