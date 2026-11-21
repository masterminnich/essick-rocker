"""USAGE: work/toolkit/rk.sh tools/seat_scoop/snap.py SIDE(L|R) STRIP_PREFIX SEEDS.json OUT_PREFIX [BAND 0.08]     env ALT as for strip.py
Step 2 of 4. Snaps by-eye seeds to the tone edge in the unrolled strips written by tools/seat_scoop/strip.py.
SEEDS.json: {"crescent@1488": [[y, t], ...], "bottom@1488": [...]} (station y in mm, t between the two triangulated arrises).
For each seed curve: corridor of +-BAND in t around the seed polyline, edge signal = change of colour along t projected on
(colour just past the seed line - colour just before it), path by dynamic programming (smooth, may not jump), sub-row refinement.
Writes OUT_PREFIX_yt.json (same keys, [[y, t]] every mm, for strip.py TR=) and OUT_PREFIX_px.json ([[u, v]] displayed pixels of
the photo, for the solver), and prints for each curve the mean edge strength and the shift from the seed."""
import sys, json, os, numpy as np, cv2
sys.path.insert(0, ".")
from rocker.cameras import Cameras
from scipy.ndimage import gaussian_filter, gaussian_filter1d
side, spre, seedf, opre = sys.argv[1:5]; band = float(sys.argv[5]) if len(sys.argv) > 5 else 0.08
Y0, Y1, T0, T1, DT = 60, 470, -0.5, 1.5, 0.005
c = Cameras.load(); E = json.load(open("parts/seat_edge.json"))[{"L": "left", "R": "right"}[side]]
T = np.array(E["top_arris_side_xyz"]); B = np.array(E["bottom_arris_xyz"]); T = T[np.argsort(T[:, 1])]; B = B[np.argsort(B[:, 1])]
def at(A, y):
    y = np.atleast_1d(np.asarray(y, float)); out = np.stack([np.interp(y, A[:, 1], A[:, i]) for i in range(3)], 1)
    for lo, sel in ((True, A[:, 1] < A[0, 1] + 60), (False, A[:, 1] > A[-1, 1] - 60)):
        m = (y < A[0, 1]) if lo else (y > A[-1, 1])
        if m.any():
            for i in (0, 2): out[m, i] = np.polyval(np.polyfit(A[sel, 1], A[sel, i], 1), y[m])
            out[m, 1] = y[m]
    return out
S = json.load(open(seedf)); YT, PX, ST = {}, {}, {}
for key, seed in S.items():
    n = key.split("@")[1]; seed = np.array(seed, float); seed = seed[np.argsort(seed[:, 0])]
    A = np.load(f"{spre}_{n}.npy"); lab = cv2.cvtColor((np.clip(A, 0, 255) / 255.0).astype(np.float32), cv2.COLOR_BGR2Lab)
    lab = np.stack([gaussian_filter(lab[:, :, i], (2.0, 3.0)) for i in range(3)], 2)
    ys = np.arange(np.ceil(seed[0, 0]), np.floor(seed[-1, 0]) + 1); cols = (ys - Y0).astype(int); ts = np.interp(ys, seed[:, 0], seed[:, 1]); rows0 = (ts - T0) / DT
    h = int(round(band / DT)); off = np.arange(-h, h + 1); R = np.clip(np.round(rows0)[:, None] + off[None, :], 3, lab.shape[0] - 4).astype(int)
    g = (lab[R + 2, cols[:, None]] - lab[R - 2, cols[:, None]])                     # change along t at every corridor cell
    k = int(round(0.03 / DT)); inner = slice(len(ys) // 5, len(ys) - len(ys) // 5)
    r0 = np.round(rows0).astype(int); d = (lab[np.clip(r0 + k, 0, lab.shape[0] - 1), cols] - lab[np.clip(r0 - k, 0, lab.shape[0] - 1), cols])[inner].mean(0); d /= np.linalg.norm(d) + 1e-9
    sig = g @ d; sig = np.maximum(sig, 0)
    # dynamic programming: maximise the edge signal, step of at most 2 rows per mm, small penalty on steps relative to the seed's own slope
    lam = 0.15 * np.percentile(sig, 90); N, M = sig.shape; cost = np.full((N, M), -1e18); back = np.zeros((N, M), int); cost[0] = sig[0]
    for i in range(1, N):
        best = np.full(M, -1e18); arg = np.zeros(M, int)
        for dj in (-2, -1, 0, 1, 2):
            src = np.arange(M) - dj; ok = (src >= 0) & (src < M); v = np.full(M, -1e18); v[ok] = cost[i - 1, src[ok]] - lam * abs(dj)
            upd = v > best; best[upd] = v[upd]; arg[upd] = src[upd]
        cost[i] = best + sig[i]; back[i] = arg
    j = int(np.argmax(cost[-1])); path = np.zeros(N, int)
    for i in range(N - 1, -1, -1): path[i] = j; j = back[i, j]
    sub = np.zeros(N)
    for i in range(N):
        j = path[i]
        if 0 < j < M - 1:
            a, b, cc = sig[i, j - 1], sig[i, j], sig[i, j + 1]; den = a - 2 * b + cc; sub[i] = 0.5 * (a - cc) / den if den < 0 else 0.0
    rows = np.round(rows0) + off[path] + np.clip(sub, -1, 1); t = T0 + rows * DT; t = gaussian_filter1d(t, 4.0, mode="nearest")
    st = sig[np.arange(N), path]; edge_hit = np.mean((path <= 1) | (path >= M - 2))
    Ty, By = at(T, ys), at(B, ys)
    if os.environ.get("ALT"):
        _a = [float(v) for v in os.environ["ALT"].split()]; _s = 1.0 if side == "R" else -1.0; By = Ty + np.array([_s * _a[2], 0, _a[3]]); Ty = Ty + np.array([_s * _a[0], 0, _a[1]])
    uT, uB = c.project_disp(f"IMG_{n}.JPG", Ty), c.project_disp(f"IMG_{n}.JPG", By); uv = uT + t[:, None] * (uB - uT)
    YT[key] = np.c_[ys, t].round(4).tolist(); PX[key] = uv.round(2).tolist(); ST[key] = np.c_[ys, st / (np.percentile(sig, 90) + 1e-9)].round(2).tolist()
    print(f"{key:16s} y {ys[0]:.0f}-{ys[-1]:.0f}  strength {st.mean():.2f} (p90 of corridor {np.percentile(sig, 90):.2f})  shift from seed rms {np.sqrt(np.mean((t - ts) ** 2)):.3f} t, max {np.abs(t - ts).max():.3f}  at corridor wall {100 * edge_hit:.0f} %")
json.dump(YT, open(opre + "_yt.json", "w")); json.dump(PX, open(opre + "_px.json", "w")); json.dump(ST, open(opre + "_strength.json", "w"))
