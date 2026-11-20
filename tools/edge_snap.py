"""USAGE: python -I tools/edge_snap.py PREFIX --seed "u,v u,v ..." [--band 3] [--step 1] [--name NAME] [--out FILE.json] [--img median]
Trace ONE edge the way a person would: the seed is the edge itself, placed by eye on a zoomed gridded view (tools/ortho_view.py,
+-2 mm is fine); this tool only refines it, looking for the strongest colour change within +-band mm of the seed line
(dynamic-programming path, so it stays continuous). It cannot wander off to background clutter or a neighbouring line the
way a wide search can. Prints how far the refined edge moved from the seed (large moves = look again).
Output JSON {"<name>": [[u, v], ...], "<name>_seed": [...], "<name>_moved_mm": [...]}. Tiny compute."""
import json, argparse, numpy as np, cv2
ap = argparse.ArgumentParser(); ap.add_argument("prefix"); ap.add_argument("--seed", required=True); ap.add_argument("--band", type=float, default=3.0)
ap.add_argument("--step", type=float, default=1.0); ap.add_argument("--name", default="edge"); ap.add_argument("--out", default=None); ap.add_argument("--img", default="median")
ap.add_argument("--lam", type=float, default=1.5)
a = ap.parse_args()
pj = json.load(open(a.prefix + "_plane.json")); res = pj["res"]; (u0, u1), (v0, v1) = pj["urange"], pj["vrange"]
lab = cv2.GaussianBlur(cv2.cvtColor(cv2.imread(f"{a.prefix}_{a.img}.png"), cv2.COLOR_BGR2LAB).astype(np.float32), (0, 0), 0.8)
S = np.array([[float(x) for x in p.split(",")] for p in a.seed.split()])
seg = np.r_[0, np.cumsum(np.linalg.norm(np.diff(S, axis=0), axis=1))]; sta = np.arange(0, seg[-1] + 1e-9, a.step)
P = np.c_[np.interp(sta, seg, S[:, 0]), np.interp(sta, seg, S[:, 1])]
T = np.gradient(P, axis=0); T /= np.linalg.norm(T, axis=1, keepdims=True); N = np.c_[-T[:, 1], T[:, 0]]
dt = res / 2; offs = np.arange(-a.band, a.band + 1e-9, dt)
UV = P[:, None, :] + offs[None, :, None] * N[:, None, :]
prof = cv2.remap(lab, ((UV[..., 0] - u0) / res).astype(np.float32), ((v1 - UV[..., 1]) / res).astype(np.float32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
G = cv2.GaussianBlur(np.linalg.norm(np.gradient(prof, axis=1), axis=2), (1, 7), 0); Gn = G / (np.percentile(G, 95) + 1e-6)
n, m = Gn.shape; cost = np.full((n, m), -np.inf); back = np.zeros((n, m), int); cost[0] = Gn[0]; idx = np.arange(m)
for i in range(1, n):
    best = np.full(m, -np.inf); arg = np.zeros(m, int)
    for d in (-1, 0, 1):
        j = idx + d; ok = (j >= 0) & (j < m); val = np.full(m, -np.inf); val[ok] = cost[i - 1, j[ok]] - a.lam * abs(d) * dt
        upd = val > best; best[upd] = val[upd]; arg[upd] = j[upd]
    cost[i] = best + Gn[i]; back[i] = arg
path = np.zeros(n, int); path[-1] = int(np.argmax(cost[-1]))
for i in range(n - 1, 0, -1): path[i - 1] = back[i, path[i]]
off = offs[path]; E = P + off[:, None] * N
fn = a.out or f"{a.prefix}_{a.name}.json"; json.dump({a.name: E.tolist(), a.name + "_seed": P.tolist(), a.name + "_moved_mm": off.tolist()}, open(fn, "w"))
edge_hits = float(np.mean(np.abs(off) > a.band - dt))
print(f"{a.name}: {n} stations | moved from seed: median {np.median(off):+.2f} mm, 5th..95th pct {np.percentile(off, 5):+.2f} .. {np.percentile(off, 95):+.2f} | pinned at band limit {edge_hits:.0%}")
