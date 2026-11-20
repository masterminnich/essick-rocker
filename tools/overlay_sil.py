"""USAGE: python -I tools/overlay_sil.py --glb parts/model_v1.glb --images 1507,1502 [--max-side 1800] [--crop X0 Y0 X1 Y1] [--out-dir DIR]
Draw each model part's projected OUTLINE (silhouette, 1 px) on photos, through the solved cameras with lens distortion.
Unlike tools/overlay.py this shows what the part should look like in the photo, so a mismatch is a visible gap between
the coloured outline and the wood. --crop is in displayed pixels at max-side scale. One photo in memory at a time; < 1 GB."""
import sys, argparse
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import numpy as np, cv2, trimesh
from PIL import Image, ImageOps
from rocker.cameras import Cameras
ap = argparse.ArgumentParser(); ap.add_argument("--glb", required=True); ap.add_argument("--images", required=True); ap.add_argument("--max-side", type=int, default=1800)
ap.add_argument("--crop", nargs=4, type=int, default=None); ap.add_argument("--out-dir", default=str(ROOT / "work/overlay")); ap.add_argument("--parts", default=None)
ap.add_argument("--thick", type=int, default=1)
a = ap.parse_args()
cams = Cameras.load(); sc = trimesh.load(a.glb)
geoms = {k: g for k, g in sc.geometry.items() if (a.parts is None or k in a.parts.split(","))}
COL = {"ROCKER": (255, 200, 0), "FLEG": (0, 255, 0), "BLEG": (255, 0, 255), "SEAT": (0, 255, 255), "ARM": (0, 128, 255), "CREST": (255, 255, 255), "SLAT": (80, 80, 255)}
Path(a.out_dir).mkdir(parents=True, exist_ok=True)
for n in a.images.split(","):
    name = f"IMG_{n}.JPG"; im = ImageOps.exif_transpose(Image.open(ROOT / "drive" / name)); W0, H0 = im.size
    s = a.max_side / max(W0, H0); img = cv2.cvtColor(np.asarray(im.resize((int(W0 * s), int(H0 * s)))), cv2.COLOR_RGB2BGR)
    for k, g in geoms.items():
        uv = cams.project_disp(name, np.asarray(g.vertices)) * s
        if not np.isfinite(uv).all(): continue
        mask = np.zeros(img.shape[:2], np.uint8); tri = uv[np.asarray(g.faces)].astype(np.int32)
        cv2.fillPoly(mask, list(tri), 255)
        cs, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        col = next((c for p, c in COL.items() if k.startswith(p)), (0, 0, 255))
        cv2.drawContours(img, cs, -1, col, a.thick, cv2.LINE_AA)
    if a.crop: img = img[a.crop[1]:a.crop[3], a.crop[0]:a.crop[2]]
    out = Path(a.out_dir) / f"sil_{n}.jpg"; cv2.imwrite(str(out), img, [cv2.IMWRITE_JPEG_QUALITY, 90]); print(out, img.shape)
