"""USAGE: work/toolkit/rk.sh tools/arm_underside/strip.py SIDE(L|R) OUTDIR PHOTO [PHOTO ...]      env GAMMA (0.5), TR=traces.json, ZOOM="ya yb da db" ZF (px per mm, 10)
Step 1 of 4 (strip -> snap -> solve -> fit) behind parts/arm_underside.json.
Unrolls one arm's OUTER side face in each photo onto the vertical surface through that arm's own outer top arris
(parts/arms.json left/right outer_top_arris_xyz, triangulated from the overhead photos): column = station y (1 mm, Y0..Y1),
row = d, the drop straight down from the top arris (0.25 mm, D0..D1; d = 0 is the top arris, d > 0 below it). A line on the arm's
outer face (the bottom arris) shows as a curve d(y); a line that sits inboard of that surface moves with the camera's elevation
(parallax), which is what solve.py uses. Beyond the traced arris (y < 66 and y > ~495) the arris is continued straight.
Writes OUTDIR/<SIDE>_<photo>.npy (float32 BGR strip) and .jpg (brightened, 3x wide, 2x tall, ticks every 10 mm in d and y).
TR draws traces {"<curve>@<photo>": [[y, d], ...]} (top cyan, bottom magenta, others orange).
ZOOM writes OUTDIR/<SIDE>_<photo>_zoom.jpg, the part ya..yb, da..db enlarged to ZF px per mm (default 10), for checking by eye."""
import sys, json, os, numpy as np, cv2
sys.path.insert(0, ".")
from rocker.cameras import Cameras
from PIL import Image, ImageOps
side, out = sys.argv[1:3]; photos = sys.argv[3:]; g = float(os.environ.get("GAMMA", 0.5))
Y0, Y1, D0, D1, DD = 50, 520, -20.0, 90.0, 0.25
c = Cameras.load(); A = json.load(open("parts/arms.json"))[{"L": "left", "R": "right"}[side]]
O = np.array(A["outer_top_arris_xyz"]); O = O[np.argsort(O[:, 1])]
def top(y):
    """the outer top arris at stations y (continued as straight lines fitted to the end 40 mm beyond the traced range)"""
    y = np.atleast_1d(np.asarray(y, float)); P = np.stack([np.interp(y, O[:, 1], O[:, i]) for i in range(3)], 1); P[:, 1] = y
    for lo in (True, False):
        m = (y < O[0, 1]) if lo else (y > O[-1, 1]); sel = (O[:, 1] < O[0, 1] + 40) if lo else (O[:, 1] > O[-1, 1] - 40)
        if m.any():
            for i in (0, 2): P[m, i] = np.polyval(np.polyfit(O[sel, 1], O[sel, i], 1), y[m])
    return P
ys = np.arange(Y0, Y1 + 1, 1.0); ds = np.arange(D0, D1 + 1e-9, DD)
if __name__ == "__main__":
    TR = json.load(open(os.environ["TR"])) if os.environ.get("TR") else {}
    Z = [float(v) for v in os.environ["ZOOM"].split()] if os.environ.get("ZOOM") else None
    P0 = top(ys)
    for n in photos:
        name = f"IMG_{n}.JPG"; im = np.array(ImageOps.exif_transpose(Image.open(f"drive/{name}")).convert("RGB"))[:, :, ::-1].astype(np.float32)
        X = P0[None, :, :] - ds[:, None, None] * np.array([0, 0, 1.0])
        U = c.project_disp(name, X.reshape(-1, 3)).reshape(len(ds), len(ys), 2)
        S = cv2.remap(im, U[:, :, 0].astype(np.float32), U[:, :, 1].astype(np.float32), cv2.INTER_CUBIC, borderMode=cv2.BORDER_CONSTANT)
        np.save(f"{out}/{side}_{n}.npy", S)
        pxmm = np.linalg.norm(U[-1] - U[0], axis=1) / (D1 - D0)
        V = (255 * np.clip(S / 255.0, 0, 1) ** g).astype(np.uint8); V = cv2.resize(V, (V.shape[1] * 3, V.shape[0] * 2), interpolation=cv2.INTER_CUBIC)
        R = lambda y, d: (int(round((y - Y0) * 3)), int(round((d - D0) / DD * 2)))
        for y in range(Y0, Y1 + 1, 10):
            for d in range(-10, 61, 10): cv2.circle(V, R(y, d), 1, (0, 255, 255), -1)
        for y in range(100, Y1, 50): cv2.line(V, R(y, D0), R(y, D0 + 3), (255, 255, 0), 1); cv2.putText(V, str(y), (R(y, D0)[0] + 3, 14), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 255), 1, cv2.LINE_AA)
        for d in range(-10, 61, 10): cv2.line(V, R(Y0, d), R(Y0 + 4, d), (255, 255, 0), 1); cv2.putText(V, str(d), (R(Y0 + 5, d)[0], R(Y0, d)[1] + 4), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 255), 1, cv2.LINE_AA)
        cv2.putText(V, f"IMG_{n} {side} arm  {pxmm.min():.1f}-{pxmm.max():.1f} px/mm", (V.shape[1] - 360, V.shape[0] - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1, cv2.LINE_AA)
        for k, v in TR.items():
            if k.endswith("@" + n):
                p = np.array(v, float); col = (255, 255, 0) if k.startswith("top") else (255, 0, 255) if k.startswith("bot") else (0, 128, 255)
                for a_, b_ in zip(p[:-1], p[1:]): cv2.line(V, R(*a_), R(*b_), col, 1, cv2.LINE_AA)
        cv2.imwrite(f"{out}/{side}_{n}.jpg", V, [cv2.IMWRITE_JPEG_QUALITY, 92])
        if Z:
            ZF = float(os.environ.get("ZF", 10)); c0, c1 = int(Z[0] - Y0), int(Z[1] - Y0); r0, r1 = int((Z[2] - D0) / DD), int((Z[3] - D0) / DD)
            W_ = (255 * np.clip(S[r0:r1, c0:c1] / 255.0, 0, 1) ** g).astype(np.uint8); W_ = cv2.resize(W_, (int((c1 - c0) * ZF), int((r1 - r0) * DD * ZF)), interpolation=cv2.INTER_CUBIC)
            Rz = lambda y, d: (int(round((y - Z[0]) * ZF)), int(round((d - Z[2]) * ZF)))
            for k, v in TR.items():
                if k.endswith("@" + n):
                    p = np.array(v, float); col = (255, 255, 0) if k.startswith("top") else (255, 0, 255) if k.startswith("bot") else (0, 128, 255)
                    p = p[(p[:, 0] >= Z[0]) & (p[:, 0] <= Z[1])]
                    for a_, b_ in zip(p[:-1], p[1:]): cv2.line(W_, Rz(*a_), Rz(*b_), col, 1, cv2.LINE_AA)
            for y in range(int(np.ceil(Z[0] / 10) * 10), int(Z[1]), 10): cv2.line(W_, Rz(y, Z[2]), (Rz(y, Z[2])[0], 10), (255, 255, 0), 1); cv2.putText(W_, str(y), (Rz(y, Z[2])[0] + 2, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 255), 1, cv2.LINE_AA)
            for d in range(int(np.ceil(Z[2] / 5) * 5), int(Z[3]), 5): cv2.line(W_, (0, Rz(Z[0], d)[1]), (10, Rz(Z[0], d)[1]), (255, 255, 0), 1); cv2.putText(W_, str(d), (12, Rz(Z[0], d)[1] + 4), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 255), 1, cv2.LINE_AA)
            cv2.imwrite(f"{out}/{side}_{n}_zoom.jpg", W_, [cv2.IMWRITE_JPEG_QUALITY, 92])
        print(f"{out}/{side}_{n}.jpg", "px/mm", round(float(pxmm.min()), 2), round(float(pxmm.max()), 2))
