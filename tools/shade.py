"""USAGE: python -I tools/shade.py --glb parts/hull_v1.glb --images 1484,1507 [--max-side 1200] [--out-dir work/shade]
Shaded render of a mesh from a photo's solved camera (pinhole, no lens distortion: a look, not a measurement), placed
next to the photo. Simple z-buffer by painter's order on face depth, Lambert shading. One photo at a time; < 1 GB."""
import sys, argparse
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import numpy as np, cv2, trimesh
from PIL import Image, ImageOps
from rocker.cameras import Cameras
ap = argparse.ArgumentParser(); ap.add_argument("--glb", required=True); ap.add_argument("--images", required=True); ap.add_argument("--max-side", type=int, default=1200)
ap.add_argument("--out-dir", default=str(ROOT / "work/shade")); a = ap.parse_args()
cams = Cameras.load(); sc = trimesh.load(a.glb); m = trimesh.util.concatenate(list(sc.geometry.values())) if hasattr(sc, "geometry") else sc
V = np.asarray(m.vertices); F = np.asarray(m.faces); Path(a.out_dir).mkdir(parents=True, exist_ok=True)
for n in a.images.split(","):
    name = f"IMG_{n}.JPG"; v = cams[name]; im = ImageOps.exif_transpose(Image.open(ROOT / "drive" / name)); W0, H0 = im.size; s = a.max_side / max(W0, H0)
    photo = cv2.cvtColor(np.asarray(im.resize((int(W0 * s), int(H0 * s)))), cv2.COLOR_RGB2BGR)
    uv, z = v.project(V, return_depth=True); uvd = cams.raw_to_disp(name, uv) * s
    cam = v.center; fn = np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]]); fn /= np.linalg.norm(fn, axis=1, keepdims=True) + 1e-12
    fc = V[F].mean(1); view = cam - fc; view /= np.linalg.norm(view, axis=1, keepdims=True); lam = np.sum(fn * view, 1)
    front = lam > 0; order = np.argsort(-z[F].mean(1)); order = order[front[order]]
    img = np.full_like(photo, 255); tri = uvd[F].astype(np.int32)
    for i in order:
        c = int(70 + 170 * lam[i]); cv2.fillConvexPoly(img, tri[i], (c, int(c * 0.86), int(c * 0.72)))
    out = Path(a.out_dir) / f"shade_{n}.jpg"; cv2.imwrite(str(out), np.hstack([photo, img]), [cv2.IMWRITE_JPEG_QUALITY, 88]); print(out)
