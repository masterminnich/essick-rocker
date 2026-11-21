"""USAGE: tools/py.sh -t 15 tools/edge_radii/pairs.py parts/model_vN.glb work/critique/vN OUT.npz
Phase 6c: pose-free silhouette PAIRS from the critique's per-point gaps (tools/critique/measure.py output).

In one photo, the two silhouettes of a part at the same station lie on opposite arrises (their outline normals m point
opposite ways). A pose error moves both the same way in the image, so the SUM of the two gaps does not depend on the pose:
    S = gap_a + gap_b = (model width - wood width) seen square to the line of sight at that station.
For a section whose arrises are rounded with radius r (the model's are sharp), the silhouette of each arris lies r*k inside
the sharp corner, where k is the critique's ease factor (measure.py: k = m.(n1+n2)/(1+n1.n2) - 1, 0 when looking along a
face, sqrt(2)-1 = 0.41 on the diagonal of a square corner). A size error along an axis g (the model's width minus the wood's,
across the two faces of class group g) adds dW_g * (|m_a.n_a,g| + |m_b.n_b,g|) / 2. So per pair
    S = sum_g dW_g * c_g + r * (k_a + k_b)
Writes one record per pair (photo, part, station): S, K = k_a + k_b, c_g for the three class groups (outer/inner,
front/back, top/bottom), the station, the arris classes, px/mm, and the points used.
Memory: the joined model + its static outline (~0.6 GB) and one photo's npz at a time."""
import sys, json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "critique"))
from common import PARTS, CLASSES, load_model, static_outline  # noqa
import numpy as np

glb, run, out = sys.argv[1], Path(sys.argv[2]), sys.argv[3]
BIN = 20.0
GROUP = {0: 2, 1: 2, 2: 0, 3: 0, 4: 1, 5: 1}      # class -> group: 0 outer/inner, 1 front/back, 2 top/bottom
meshes = load_model(glb)
S = static_outline(meshes)
HO = set(json.load(open(ROOT / "tools/critique/holdout.json"))["held_out"])
rec = {k: [] for k in ("photo", "held", "part", "station", "S", "K", "c", "ca", "cb", "ka", "kb", "pxmm", "npts", "mdot")}
for f in sorted(run.glob("IMG_*.npz")):
    R = dict(np.load(f))
    ok = (R["st"] == 0) & (R["kind"] == 1) & R["sharp"]
    if not ok.any(): continue
    q = np.nonzero(ok)[0]
    for pi in np.unique(R["part"][q]):
        p = PARTS[pi]; s = S[p]
        j = q[R["part"][q] == pi]
        ei = s["ei"][R["si"][j]]
        f1, f2 = s["adj"][ei, 0], s["adj"][ei, 1]
        cl1, cl2 = s["fc"][f1], s["fc"][f2]
        n1, n2 = s["fn"][f1], s["fn"][f2]
        m = R["m"][j].astype(float)
        st = np.floor(R["along"][j] / BIN).astype(int)
        lo = np.minimum(cl1, cl2); hi = np.maximum(cl1, cl2)
        arr = lo * 10 + hi
        good = np.vectorize(GROUP.get)(lo) != np.vectorize(GROUP.get)(hi)   # a corner between two class groups
        # projections |m.n| per group (each corner has one face of each of its two groups)
        cg = np.zeros((len(j), 3))
        for nn, cc in ((n1, cl1), (n2, cl2)):
            g = np.vectorize(GROUP.get)(cc)
            cg[np.arange(len(j)), g] = np.abs(np.einsum("ij,ij->i", m, nn))
        for b in np.unique(st):
            sel = (st == b) & good
            arrs = np.unique(arr[sel])
            if len(arrs) < 2: continue
            G = []
            for a_ in arrs:
                t = sel & (arr == a_)
                if t.sum() < 2: continue
                mm = m[t].mean(0); mm /= np.linalg.norm(mm)
                G.append((a_, t, mm))
            best = None
            for i1 in range(len(G)):
                for i2 in range(i1 + 1, len(G)):
                    d = float(G[i1][2] @ G[i2][2])
                    if d < -0.8 and (best is None or d < best[0]): best = (d, G[i1], G[i2])
            if best is None: continue
            d, A, B = best
            ga, gb = np.median(R["gap"][j][A[1]]), np.median(R["gap"][j][B[1]])
            ka, kb = np.median(R["k"][j][A[1]]), np.median(R["k"][j][B[1]])
            c = (np.median(cg[A[1]], 0) + np.median(cg[B[1]], 0)) / 2
            rec["photo"].append(f.stem); rec["held"].append(f.stem + ".JPG" in HO); rec["part"].append(p)
            rec["station"].append((b + 0.5) * BIN); rec["S"].append(ga + gb); rec["K"].append(ka + kb); rec["c"].append(c)
            rec["ca"].append(int(A[0])); rec["cb"].append(int(B[0])); rec["ka"].append(ka); rec["kb"].append(kb)
            rec["pxmm"].append(float(np.median(R["pxmm"][j][A[1] | B[1]]))); rec["npts"].append(int(A[1].sum() + B[1].sum()))
            rec["mdot"].append(d)
    print(f.stem, len(rec["S"]), flush=True)
np.savez_compressed(out, **{k: np.array(v) for k, v in rec.items()})
print("pairs", len(rec["S"]))
