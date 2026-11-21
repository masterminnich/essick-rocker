"""USAGE: work/toolkit/rk.sh tools/arm_underside/snap.py SIDE(L|R) STRIPDIR SEEDS.json OUT.json [BAND 4.0]
Step 2 of 4 (strip -> snap -> solve -> fit). Snaps by-eye seeds to the arm's edges in the unrolled strips of tools/arm_underside/strip.py.
SEEDS.json: {"top@1472": {"seed": [[y, d], ...], "range": [[ya, yb], ...]}, "bot@1472": {...}, ...}; or {"seed": "bot_R"} to use the
shared seed of that name in SEEDS.json "_seeds" (with "shift": mm added to it). "range" = the stretches of y that are traced (checked by eye).
The wood: for each column, the median colour (Lab) of a 4 mm band INSIDE the wood next to the seed (above it for the lower lines "bot", "obot", "ibot"; below it for "top").
"Unlike" = colour distance from that. The edge is where "unlike" rises fastest going OUT of the wood (down for the lower lines, up for top), searched
within +-BAND mm of the seed, as one smooth path (dynamic programming, at most 0.5 mm of d per mm of y), refined to a quarter row.
Writes OUT.json: {key: {"yd": [[y, d], ...] every mm inside range, "strength": [...] (rise of unlike per mm), "seed_shift_rms": mm}}."""
import sys, json, numpy as np, cv2
from scipy.ndimage import gaussian_filter, gaussian_filter1d
side, sd, seedf, outf = sys.argv[1:5]; BAND = float(sys.argv[5]) if len(sys.argv) > 5 else 4.0
Y0, Y1, D0, D1, DD = 50, 520, -20.0, 90.0, 0.25
S = json.load(open(seedf)); SH = S.pop("_seeds", {}); OUT = {}
for key, spec in S.items():
    n = key.split("@")[1]; kind = key.split("@")[0]
    seed = spec["seed"]
    seed = np.array(SH[seed] if isinstance(seed, str) else seed, float); seed = seed[np.argsort(seed[:, 0])]; seed[:, 1] += spec.get("shift", 0.0)
    A = np.load(f"{sd}/{side}_{n}.npy"); lab = cv2.cvtColor((np.clip(A, 0, 255) / 255.0).astype(np.float32), cv2.COLOR_BGR2Lab)
    lab = np.stack([gaussian_filter(lab[:, :, i], (1.2, 1.5)) for i in range(3)], 2)
    ys = np.arange(Y0, Y1 + 1, 1.0); cols = np.arange(len(ys)); ds = np.interp(ys, seed[:, 0], seed[:, 1]); r0 = (ds - D0) / DD
    out_sign = -1 if kind.startswith("top") else 1          # direction OUT of the wood, in d (down for every curve but the top arris)
    # wood colour per column: median of the 4 mm band inside the wood, 1.5..5.5 mm from the seed
    inside = np.round(r0[:, None] - out_sign * np.arange(6, 22)[None, :]).astype(int).clip(0, lab.shape[0] - 1)
    wood = np.median(lab[inside, cols[:, None]], 1); wood = np.stack([gaussian_filter1d(wood[:, i], 8, mode="nearest") for i in range(3)], 1)
    h = int(round(BAND / DD)); off = np.arange(-h, h + 1); R = np.clip(np.round(r0)[:, None] + off[None, :], 3, lab.shape[0] - 4).astype(int)
    unl = lambda rr: np.linalg.norm(lab[rr, cols[:, None]] - wood[:, None, :], axis=2)
    sig = (unl(R + 2 * out_sign) - unl(R - 2 * out_sign)) / (4 * DD)      # rise of unlike per mm going out of the wood
    sig = np.maximum(sig, 0)
    N, M = sig.shape; lam = 0.15 * np.percentile(sig, 90); cost = np.full((N, M), -1e18); back = np.zeros((N, M), int); cost[0] = sig[0]
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
    d = D0 + (np.round(r0) + off[path] + np.clip(sub, -1, 1)) * DD; d = gaussian_filter1d(d, 1.5, mode="nearest"); st = sig[np.arange(N), path]
    keep = np.zeros(N, bool)
    for a_, b_ in spec.get("range", [[Y0, Y1]]): keep |= (ys >= a_) & (ys <= b_)
    wall = np.mean(((path <= 1) | (path >= M - 2))[keep])
    OUT[key] = {"yd": np.c_[ys, d][keep].round(3).tolist(), "strength": st[keep].round(2).tolist(), "seed_shift_rms": round(float(np.sqrt(np.mean((d - ds)[keep] ** 2))), 2)}
    print(f"{key:12s} y {ys[keep][0]:.0f}-{ys[keep][-1]:.0f}  strength median {np.median(st[keep]):.1f}  shift from seed rms {OUT[key]['seed_shift_rms']:.2f} mm  at band wall {100 * wall:.0f}%")
json.dump(OUT, open(outf, "w"))
