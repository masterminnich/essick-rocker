"""USAGE: tools/py.sh -t 5 tools/seat_cloudcheck.py IMG_1614 [crop x0 y0 x1 y1 in displayed px at 1/2]
Draw the chair cloud (work/dense/chair_dense.npy) into a registered dot photo (rocker.seatcams) at half size, displayed
orientation -> work/seat/check_<name>.jpg. Points sitting on the wood = pose + chair position agree. Light (<300 MB)."""
import sys; from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent; sys.path.insert(0, str(ROOT))
import numpy as np, cv2
from PIL import Image, ImageOps
from rocker.seatcams import load
cams = load(); n = sys.argv[1]; n = n if n.endswith(".JPG") else n + ".JPG"; v = cams[n]
C = np.load(ROOT / "work/dense/chair_dense.npy"); X = C[:, :3]
uv = v.project_disp(X) / 2; ok = np.isfinite(uv).all(1)
im = Image.open(cams.drive / n); im.draft("RGB", (2016, 2016)); im = ImageOps.exif_transpose(im.convert("RGB"))
im = np.ascontiguousarray(np.asarray(im.resize((im.width * 1008 // max(im.size) * 2, im.height * 1008 // max(im.size) * 2)))[:, :, ::-1])
for (x, y) in uv[ok].astype(int):
    if 0 <= x < im.shape[1] and 0 <= y < im.shape[0]: cv2.circle(im, (x, y), 1, (0, 255, 255), -1)
if len(sys.argv) > 2:
    x0, y0, x1, y1 = map(int, sys.argv[2:6]); im = im[y0:y1, x0:x1]
cv2.imwrite(str(ROOT / f"work/seat/check_{n[:-4]}.jpg"), im, [cv2.IMWRITE_JPEG_QUALITY, 85]); print(im.shape)
