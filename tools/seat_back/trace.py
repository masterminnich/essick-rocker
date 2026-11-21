"""USAGE: work/toolkit/rk.sh tools/seat_back/trace.py SHEET_PREFIX GUESS.json EDGE OUT_PREFIX [BAND 3] [HALF 10]
Step 2 of 4 (sheet -> trace -> solve -> fit) for the seat's BACK EDGE. Traces ONE edge of the back edge (top arris, hard line or
bottom arris) in every photo listed for it, each photo on its own:
  1. the seed is a 3D curve X(x) = (x, y(x), z(x)) (GUESS.json: first by eye from two photos, afterwards the previous solve),
     drawn through each photo's own camera onto the rear sheet (tools/face_ortho.py, plane y = const, u = chair x, v = height);
  2. tools/edge_snap.py refines it inside +-BAND mm (strongest colour change, continuous path), nothing wider;
  3. a strip figure for the check by eye: one row per photo, the sheet straightened along the seed (+-HALF mm, 4 px per mm), seed =
     the two ticks at each end, snapped trace = dots every 5 mm (the edge itself stays visible between them).
GUESS.json: {"<edge>": {"xyz": [[x, y, z], ...]  (any spacing; interpolated in x),
                         "photos": {"1502": [[x0, x1], ...], ...}  (stretches of x where that photo shows the edge clearly)}}
Writes OUT_PREFIX_<edge>.json  {"<edge>@<photo>": [[u, v], ...] every mm (sheet mm), "<edge>@<photo>_moved_mm": [...]} : the traces
tools/curve_tri.py reads, and OUT_PREFIX_<edge>_strips.jpg (env GAIN=3 brightens the figure for dark faces; the trace is not affected). Tiny compute: one small sheet image at a time."""
import sys, json, subprocess, os, numpy as np, cv2
sys.path.insert(0, ".")
from rocker.cameras import Cameras
pre, gf, edge, opre = sys.argv[1:5]; band = float(sys.argv[5]) if len(sys.argv) > 5 else 3.0; half = float(sys.argv[6]) if len(sys.argv) > 6 else 10.0
G = json.load(open(gf)); G = G.get("edges", G)[edge]; X0 = np.array(G["xyz"], float); X0 = X0[np.argsort(X0[:, 0])]; pj = json.load(open(pre + "_plane.json")); cams = Cameras.load()
o, U, V, n = (np.array(pj[k], float) for k in ("origin", "u", "v", "n")); res = pj["res"]; (u0, u1), (v0, v1) = pj["urange"], pj["vrange"]
def onsheet(C, X):
    d = X - C; t = ((o - C) @ n) / (d @ n); P = C + t[:, None] * d - o; return np.c_[P @ U, P @ V]
out = {}; rows = []; Z = 4; GAIN = float(os.environ.get("GAIN", 1))            # GAIN brightens the strip figure only (dark faces)
for ph, ranges in G["photos"].items():
    C = np.asarray(cams.views[f"IMG_{ph}.JPG"].center, float); img = cv2.imread(f"{pre}_{ph}.png"); tr = []; mv = []; segs = []
    for xa, xb in ranges:
        xs = np.arange(xa, xb + 1e-9, 5.0); Xs = np.c_[xs, np.interp(xs, X0[:, 0], X0[:, 1]), np.interp(xs, X0[:, 0], X0[:, 2])]; S = onsheet(C, Xs)
        tmp = f"{opre}_{edge}_{ph}_tmp.json"
        r = subprocess.run([sys.executable, "-I", "tools/edge_snap.py", pre, "--seed", " ".join(f"{a:.2f},{b:.2f}" for a, b in S), "--band", str(band), "--img", ph, "--name", "e", "--out", tmp], capture_output=True, text=True)
        assert r.returncode == 0, r.stderr[-400:]
        E = json.load(open(tmp)); os.remove(tmp); tr += E["e"]; mv += E["e_moved_mm"]; segs.append((np.array(E["e_seed"]), np.array(E["e_moved_mm"])))
    out[f"{edge}@{ph}"] = tr; out[f"{edge}@{ph}_moved_mm"] = [round(m, 2) for m in mv]; m = np.array(mv)
    print(f"{edge}@{ph}: {len(tr)} points, moved from the seed median {np.median(m):+.2f}, 5-95% {np.percentile(m, 5):+.2f}..{np.percentile(m, 95):+.2f} mm, at the band limit {np.mean(np.abs(m) > band - res):.0%}")
    # strip: straightened along the seed over the full x range of the guess (so rows line up); columns = chair x of the seed
    xs = np.arange(X0[0, 0], X0[-1, 0] + 1e-9, 1.0 / Z); Xs = np.c_[xs, np.interp(xs, X0[:, 0], X0[:, 1]), np.interp(xs, X0[:, 0], X0[:, 2])]; P = onsheet(C, Xs)
    T = np.gradient(P, axis=0); T /= np.linalg.norm(T, axis=1, keepdims=True); N = np.c_[-T[:, 1], T[:, 0]]; offs = np.arange(half, -half - 1e-9, -1.0 / Z)
    UV = P[None] + offs[:, None, None] * N[None]; st = cv2.remap(img, ((UV[..., 0] - u0) / res).astype(np.float32), ((v1 - UV[..., 1]) / res).astype(np.float32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
    st = np.ascontiguousarray(np.clip(st.astype(np.float32) * GAIN, 0, 255).astype(np.uint8)); mid = int(round(half * Z))
    for Sd, md in segs:
        xcol = np.interp(Sd[:, 0], P[:, 0], np.arange(len(P)))                           # seed station -> strip column
        for j in range(0, len(Sd), 5): cv2.circle(st, (int(round(xcol[j])), int(round(mid - md[j] * Z))), 1, (0, 255, 255), -1)
        for cx in (xcol[0], xcol[-1]): cv2.line(st, (int(cx), 0), (int(cx), st.shape[0]), (255, 255, 0), 1)
    cv2.line(st, (0, mid), (6, mid), (0, 255, 0), 1); cv2.line(st, (st.shape[1] - 7, mid), (st.shape[1] - 1, mid), (0, 255, 0), 1)
    for xg in range(int(np.ceil(X0[0, 0] / 20) * 20), int(X0[-1, 0]) + 1, 20):
        cg = int(round((xg - X0[0, 0]) * Z)); cv2.line(st, (cg, 0), (cg, 5), (255, 255, 255), 1); cv2.putText(st, str(xg), (cg + 2, 10), cv2.FONT_HERSHEY_SIMPLEX, 0.3, (255, 255, 255), 1)
    cv2.putText(st, ph, (4, st.shape[0] - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 0), 1, cv2.LINE_AA); rows.append(st); rows.append(np.full((3, st.shape[1], 3), 255, np.uint8))
json.dump(out, open(f"{opre}_{edge}.json", "w")); cv2.imwrite(f"{opre}_{edge}_strips.jpg", np.vstack(rows), [cv2.IMWRITE_JPEG_QUALITY, 92]); print("wrote", f"{opre}_{edge}.json", f"{opre}_{edge}_strips.jpg", np.vstack(rows).shape)
