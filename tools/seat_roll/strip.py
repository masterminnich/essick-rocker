"""USAGE: work/toolkit/rk.sh tools/seat_roll/strip.py PHOTO OUTDIR [--line front|back] [--t0 -6 --t1 12] [--pxmm 10]
Unrolled strip of one seat edge in ONE photo, both halves. --line front (default): the front BOTTOM arris, rows |x| 10..244
every 2 mm along the design line (parts/seat_front_face.json bottom_arris_*_of_abs_x, which PR #15 traced); + t = outward =
down / forward off the wood. --line back: the TOP arris of the back edge at the slats, rows |x| 2..170 along
parts/seat_back.json design top_arris (PR #21); + t = outward = up / back off the wood. Columns = t mm along the image normal
square to the line, t = 0 on the line (a + wood edge = the wood reaches beyond the model's line). Each row is the photo (Lab, float) averaged
over +-1 mm along the line; px/mm from projecting a 1 mm step square to the ray. Writes OUTDIR/strip_PHOTO_L/R.npz (lab, t, x,
pxmm, uv, n) and a picture OUTDIR/strip_PHOTO.jpg (left half above, right half below, 10 px/mm, a tick every 1 mm, t = 0 red).
One photo in memory; tiny compute."""
import sys, json, argparse
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]; sys.path.insert(0, str(ROOT))
import numpy as np, cv2
from rocker.cameras import Cameras
ap = argparse.ArgumentParser(); ap.add_argument("photo"); ap.add_argument("out"); ap.add_argument("--t0", type=float, default=-6); ap.add_argument("--t1", type=float, default=12)
ap.add_argument("--pxmm", type=float, default=10); ap.add_argument("--line", default="front", choices=["front", "back"])
a = ap.parse_args(); OUT = Path(a.out); OUT.mkdir(parents=True, exist_ok=True)
cams = Cameras.load(); name = f"IMG_{a.photo}.JPG"; V = cams[name]
if a.line == "front":
    F = json.load(open(ROOT / "parts/seat_front_face.json"))["design"]
    by, bz = np.array(F["bottom_arris_y_of_abs_x"]), np.array(F["bottom_arris_z_of_abs_x"]); XS = np.arange(10, 245, 2.0); OUTW = [0, 0.7, -0.7]; TAG = ""
else:
    F = json.load(open(ROOT / "parts/seat_back.json"))["design"]; ax_ = np.array(F["abs_x"])
    by, bz = np.c_[ax_, F["top_arris"]["y"]], np.c_[ax_, F["top_arris"]["z"]]; XS = np.arange(2, 171, 2.0); OUTW = [0, -0.7, 0.7]; TAG = "back_"
img = cv2.imread(str(ROOT / "drive" / name), cv2.IMREAD_COLOR | cv2.IMREAD_IGNORE_ORIENTATION)
lab = cv2.cvtColor(img.astype(np.float32) / 255.0, cv2.COLOR_BGR2Lab)
T = np.arange(a.t0, a.t1 + 1e-6, 0.1); S = np.array([-1.0, -0.5, 0, 0.5, 1.0])
pics = []
for sd, sg in (("L", -1), ("R", 1)):
    P = np.c_[sg * XS, np.interp(XS, by[:, 0], by[:, 1]), np.interp(XS, bz[:, 0], bz[:, 1])]
    uv = V.project(P); C = V.center
    tg = V.project(P + [sg, 0, 0]) - uv; tg /= np.linalg.norm(tg, axis=1, keepdims=True)
    n = np.c_[-tg[:, 1], tg[:, 0]]
    down = V.project(P + OUTW) - uv; n *= np.where(np.einsum("ij,ij->i", n, down) < 0, -1, 1)[:, None]
    ray = P - C; ray /= np.linalg.norm(ray, axis=1, keepdims=True); q = np.cross(ray, [1.0, 0, 0]); q /= np.linalg.norm(q, axis=1, keepdims=True)
    px = np.linalg.norm(V.project(P + q) - uv, axis=1)
    ok = np.isfinite(uv).all(1) & (uv[:, 0] > 20) & (uv[:, 0] < 4012) & (uv[:, 1] > 20) & (uv[:, 1] < 3004)
    L = np.zeros((len(XS), len(T), 3), np.float32)
    for s in S:
        mx = (uv[:, 0:1] + s * px[:, None] * tg[:, 0:1] + T[None, :] * px[:, None] * n[:, 0:1]).astype(np.float32)
        my = (uv[:, 1:2] + s * px[:, None] * tg[:, 1:2] + T[None, :] * px[:, None] * n[:, 1:2]).astype(np.float32)
        L += cv2.remap(lab, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    L /= len(S); L[~ok] = np.nan
    np.savez_compressed(OUT / f"strip_{TAG}{a.photo}_{sd}.npz", lab=L, t=T, x=XS * sg, pxmm=px, uv=uv, n=n, ok=ok)
    rgb = cv2.cvtColor(np.nan_to_num(L), cv2.COLOR_Lab2BGR); rgb = np.clip(rgb * 255, 0, 255).astype(np.uint8)
    f = a.pxmm / 10.0   # T step 0.1 mm -> 10 px/mm natively along t; rows every 2 mm
    pic = cv2.resize(rgb, (int(len(T) * f), len(XS) * 4), interpolation=cv2.INTER_NEAREST)
    i0 = int(round(-a.t0 / 0.1 * f)); pic[:, i0] = (0, 0, 255)
    for tt in range(int(np.ceil(a.t0)), int(a.t1) + 1): pic[:3, int(round((tt - a.t0) / 0.1 * f))] = (255, 255, 255)
    pics.append(pic); pics.append(np.full((6, pic.shape[1], 3), 255, np.uint8))
    print(sd, f"px/mm {np.median(px[ok]) if ok.any() else float('nan'):.2f}, rows {ok.sum()}")
cv2.imwrite(str(OUT / f"strip_{TAG}{a.photo}.jpg"), np.vstack(pics))
