"""USAGE: work/toolkit/rk.sh tools/seat_scoop/strip.py SIDE(L|R) OUT_PREFIX PHOTO [PHOTO ...]     env GAMMA (0.45), TR=traces_yt.json, ALT, ZOOM
Step 1 of 4 (strip -> snap -> solve -> fit) behind parts/seat_scoop.json.
Unrolls the seat's side edge in each photo: column = station y (1 mm, Y0..Y1), row = t along the straight line from the
triangulated top arris (t = 0) to the triangulated bottom arris (t = 1) at that station, t from T0 to T1. A feature that sits
on the edge shows as a curve t(y); the same curve in every photo = geometry, a curve that moves = reflection (or depth).
Writes OUT_PREFIX_<photo>.npy (float32 BGR strip) and OUT_PREFIX_<photo>.jpg (brightened, 3x wide, ticks at t = 0 and 1,
y labels). TR draws traces {"<name>@<photo>": [[y, t], ...]} on the jpg (keys starting "crescent" magenta, others orange).
ALT="dx0 dz0 dx1 dz1" (mm): the strip runs between the top arris moved by (dx0, dz0) and by (dx1, dz1) instead; used with "-25 0 25 0" for the
photos taken from 44-72 degrees above (1479-1481, 1537-1539), which look along the edge face so the arris-to-arris strip collapses.
ZOOM="ya yb ta tb" with ZF (px per mm, 8) and ZT (extra stretch in t) writes an enlarged part for checking a trace by eye."""
import sys, json, os, numpy as np, cv2
sys.path.insert(0, ".")
from rocker.cameras import Cameras
from PIL import Image, ImageOps
side, pre = sys.argv[1:3]; photos = sys.argv[3:]; g = float(os.environ.get("GAMMA", 0.45))
Y0, Y1, T0, T1, DT = 60, 470, -0.5, 1.5, 0.005
Z = [float(v) for v in os.environ["ZOOM"].split()] if os.environ.get("ZOOM") else None   # ZOOM="ya yb ta tb": enlarged part, 8 px per mm
c = Cameras.load(); E = json.load(open("parts/seat_edge.json"))[{"L": "left", "R": "right"}[side]]
T = np.array(E["top_arris_side_xyz"]); B = np.array(E["bottom_arris_xyz"]); T = T[np.argsort(T[:, 1])]; B = B[np.argsort(B[:, 1])]
ys = np.arange(Y0, Y1 + 1, 1.0); ts = np.arange(T0, T1 + 1e-9, DT)
# beyond the measured range the arrises are continued as straight lines (np.polyfit on the end 60 mm)
def at(A, y):
    out = np.stack([np.interp(y, A[:, 1], A[:, i]) for i in range(3)], 1)
    for lo, sel in ((True, A[:, 1] < A[0, 1] + 60), (False, A[:, 1] > A[-1, 1] - 60)):
        m = (y < A[0, 1]) if lo else (y > A[-1, 1])
        if m.any():
            for i in (0, 2): out[m, i] = np.polyval(np.polyfit(A[sel, 1], A[sel, i], 1), y[m])
            out[m, 1] = y[m]
    return out
Ty, By = at(T, ys), at(B, ys)
if os.environ.get("ALT"):      # ALT="dx0 dz0 dx1 dz1": the strip runs between the top arris moved by (dx0, dz0) (t = 0) and by (dx1, dz1) (t = 1); dx positive = outboard. For steep photos
    _a = [float(v) for v in os.environ["ALT"].split()]; _s = 1.0 if side == "R" else -1.0; By = Ty + np.array([_s * _a[2], 0, _a[3]]); Ty = Ty + np.array([_s * _a[0], 0, _a[1]])
TR = json.load(open(os.environ["TR"])) if os.environ.get("TR") else {}
for n in photos:
    name = f"IMG_{n}.JPG"; im = np.array(ImageOps.exif_transpose(Image.open(f"drive/{name}")).convert("RGB"))[:, :, ::-1].astype(np.float32)
    uT, uB = c.project_disp(name, Ty), c.project_disp(name, By)
    U = uT[None, :, :] + ts[:, None, None] * (uB - uT)[None, :, :]
    S = cv2.remap(im, U[:, :, 0].astype(np.float32), U[:, :, 1].astype(np.float32), cv2.INTER_CUBIC, borderMode=cv2.BORDER_CONSTANT)
    np.save(f"{pre}_{n}.npy", S)
    pxlen = np.linalg.norm(uB - uT, axis=1)
    V = (255 * np.clip(S / 255.0, 0, 1) ** g).astype(np.uint8); V = cv2.resize(V, (V.shape[1] * 3, V.shape[0] * 2), interpolation=cv2.INTER_CUBIC)
    R = lambda y, t: (int(round((y - Y0) * 3)), int(round((t - T0) / DT * 2)))
    for y in range(Y0, Y1 + 1, 10):
        for t in (0.0, 1.0): cv2.circle(V, R(y, t), 1, (0, 255, 255), -1)
    for y in range(100, Y1, 50):
        cv2.line(V, R(y, T0), R(y, T0 + 0.08), (255, 255, 0), 1); cv2.putText(V, str(y), (R(y, T0)[0] + 3, 14), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 255), 1, cv2.LINE_AA)
    for t in np.arange(-0.4, 1.5, 0.2):
        cv2.line(V, R(Y0, t), R(Y0 + 4, t), (255, 255, 0), 1); cv2.putText(V, f"{t:.1f}", (R(Y0 + 5, t)[0], R(Y0, t)[1] + 4), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 255), 1, cv2.LINE_AA)
    cv2.putText(V, f"IMG_{n}  edge {pxlen.min():.0f}-{pxlen.max():.0f} px", (V.shape[1] - 330, V.shape[0] - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1, cv2.LINE_AA)
    for k, v in TR.items():
        if k.endswith("@" + n):
            p = np.array(v, float); col = (255, 0, 255) if k.startswith("crescent") else (0, 128, 255)
            for a, b in zip(p[:-1], p[1:]): cv2.line(V, R(*a), R(*b), col, 1, cv2.LINE_AA)
    if Z:
        a, b = R(Z[0], Z[2]), R(Z[1], Z[3]); V = V[a[1]:b[1], a[0]:b[0]]; ZF = float(os.environ.get('ZF', 8)); f = ZF / 3; fy = f * float(os.environ.get('ZT', 1)); V = cv2.resize(V, (int(V.shape[1] * f), int(V.shape[0] * fy)), interpolation=cv2.INTER_CUBIC)
        for y in range(int(Z[0]) // 10 * 10 + 10, int(Z[1]), 10): cv2.putText(V, str(y), (int((y - Z[0]) * ZF), 12), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 255), 1, cv2.LINE_AA); cv2.line(V, (int((y - Z[0]) * ZF), 14), (int((y - Z[0]) * ZF), 22), (255, 255, 0), 1)
        for t in np.arange(np.ceil(Z[2] * 10) / 10, Z[3], 0.1): yy = int((t - Z[2]) / DT * 2 * fy); cv2.putText(V, f"{t:.1f}", (2, yy + 4), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 255), 1, cv2.LINE_AA); cv2.line(V, (30, yy), (40, yy), (255, 255, 0), 1)
    cv2.imwrite(f"{pre}_{n}.jpg", V, [cv2.IMWRITE_JPEG_QUALITY, 92]); print(f"{pre}_{n}.jpg", V.shape, "edge px", round(float(pxlen.min())), round(float(pxlen.max())), "arris y", T[0, 1].round(), T[-1, 1].round(), B[0, 1].round(), B[-1, 1].round())
