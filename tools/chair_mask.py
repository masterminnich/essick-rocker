"""USAGE: python -I tools/chair_mask.py --images 1507,1502 | --all  [--out-dir work/masks] [--scale 0.5] [--preview]
Segment the chair in each photo (GrabCut), seeded from 3D knowledge instead of hand marks:
  sure foreground = small discs at the projections of the triangulated chair points (work/dense/chair_dense.npy)
  sure background = everything farther than --bg-mm from the projected first model (parts/model_v1.glb)
  undecided       = the band in between; GrabCut decides it from colour.
Writes <out-dir>/IMG_xxxx.png (255 = chair) in RAW sensor orientation at --scale, plus optional preview jpgs.
Compute: one photo at half resolution, cropped to the chair; GrabCut 5 iterations; ~5-10 s and < 1 GB per photo."""
import sys, argparse
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import numpy as np, cv2, trimesh
from PIL import Image
from rocker.cameras import Cameras
ap = argparse.ArgumentParser(); g = ap.add_mutually_exclusive_group(required=True); g.add_argument("--images"); g.add_argument("--all", action="store_true")
ap.add_argument("--out-dir", default=str(ROOT / "work/masks")); ap.add_argument("--scale", type=float, default=0.5); ap.add_argument("--bg-mm", type=float, default=45)
ap.add_argument("--fg-mm", type=float, default=2.5); ap.add_argument("--preview", action="store_true"); ap.add_argument("--glb", default=str(ROOT / "parts/model_v1.glb"))
a = ap.parse_args(); cv2.setNumThreads(2)
cams = Cameras.load(); S = a.scale; out = Path(a.out_dir); out.mkdir(parents=True, exist_ok=True)
C = np.load(ROOT / "work/dense/chair_dense.npy"); C = C[(C[:, 2] > 8) & (C[:, 6] >= 3) & (C[:, 7] < 1.5)][:, :3]
geoms = list(trimesh.load(a.glb).geometry.values())
names = cams.names() if a.all else [f"IMG_{n}.JPG" for n in a.images.split(",")]
for name in names:
    dst = out / (name[:-4] + ".png")
    if dst.exists(): continue
    v = cams[name]; W, H = int(4032 * S), int(3024 * S)
    model = np.zeros((H, W), np.uint8); zs = []
    for gm in geoms:
        uv, z = v.project(np.asarray(gm.vertices), return_depth=True)
        if not np.isfinite(uv).all(): continue
        cv2.fillPoly(model, list((uv[np.asarray(gm.faces)] * S).astype(np.int32)), 255); zs.append(np.median(z))
    if model.sum() < 255 * 2000: continue
    px_per_mm = v.focal_raw * S / float(np.median(zs))
    ys, xs = np.nonzero(model); pad = int(a.bg_mm * px_per_mm) + 20
    x0, x1, y0, y1 = max(xs.min() - pad, 0), min(xs.max() + pad, W), max(ys.min() - pad, 0), min(ys.max() + pad, H)
    if (x1 - x0) * (y1 - y0) < 0.02 * W * H: continue
    raw = np.asarray(Image.open(ROOT / "drive" / name).convert("RGB")); img = cv2.cvtColor(cv2.resize(raw, (W, H), interpolation=cv2.INTER_AREA), cv2.COLOR_RGB2BGR)[y0:y1, x0:x1]
    del raw
    r = max(3, int(a.bg_mm * px_per_mm)) | 1
    near = cv2.dilate(model, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1)))[y0:y1, x0:x1]
    gc = np.where(near > 0, cv2.GC_PR_BGD, cv2.GC_BGD).astype(np.uint8)
    core = cv2.erode(model, np.ones((int(8 * px_per_mm) | 1,) * 2, np.uint8))[y0:y1, x0:x1]; gc[core > 0] = cv2.GC_PR_FGD
    uv, z = v.project(C, return_depth=True); ok = np.isfinite(uv).all(1); p = (uv[ok] * S - [x0, y0]).astype(int)
    ok2 = (p[:, 0] >= 0) & (p[:, 1] >= 0) & (p[:, 0] < x1 - x0) & (p[:, 1] < y1 - y0); fr = max(1, int(a.fg_mm * px_per_mm))
    seed = np.zeros(gc.shape, np.uint8)
    for q in p[ok2]: cv2.circle(seed, (int(q[0]), int(q[1])), fr, 255, -1)
    gc[seed > 0] = cv2.GC_FGD
    bgd, fgd = np.zeros((1, 65)), np.zeros((1, 65))
    cv2.grabCut(img, gc, None, bgd, fgd, 5, cv2.GC_INIT_WITH_MASK)
    m = ((gc == cv2.GC_FGD) | (gc == cv2.GC_PR_FGD)).astype(np.uint8) * 255
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    full = np.zeros((H, W), np.uint8); full[y0:y1, x0:x1] = m; cv2.imwrite(str(dst), full)
    if a.preview:
        pv = img.copy(); cs, _ = cv2.findContours(m, cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE); cv2.drawContours(pv, cs, -1, (0, 255, 0), 1)
        pv[m == 0] = (pv[m == 0] * 0.45).astype(np.uint8)
        k = {6: cv2.ROTATE_90_CLOCKWISE, 3: cv2.ROTATE_180, 8: cv2.ROTATE_90_COUNTERCLOCKWISE}.get(v.orient)
        if k is not None: pv = cv2.rotate(pv, k)
        cv2.imwrite(str(out / (name[:-4] + "_pv.jpg")), pv, [cv2.IMWRITE_JPEG_QUALITY, 85])
    print(name, "mask px", int(m.sum() // 255), "crop", img.shape[:2], flush=True)
