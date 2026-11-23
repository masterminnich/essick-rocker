"""USAGE: python -I tools/flush_fig.py BEFORE_pts.npz [AFTER_pts.npz] OUT.png [JOINT ...]
Gap maps of the joints from tools/flush_audit.py --points: each joint's end face seen square on (the plane of its contact
patch), contact in grey, open gap coloured 0-5 mm. With two files: before (top row) and after (bottom row).
Matplotlib only, seconds."""
import sys
import numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

args = [a for a in sys.argv[1:]]
files = [a for a in args if a.endswith(".npz")]; out = [a for a in args if a.endswith(".png")][0]
D = [np.load(f) for f in files]
want = [a for a in args if not a.endswith((".npz", ".png"))] or ["ARM_R__BLEG_R", "ARM_R__FLEG_R", "FLEG_R__ARM_R", "CREST__BLEG_R", "SEAT__BLEG_R", "SEAT__FLEG_R"]
TITLE = {"ARM__BLEG": "arm end on the back leg", "ARM__FLEG": "arm underside on the front leg", "FLEG__ARM": "front-leg top under the arm",
         "CREST__BLEG": "crest end on the back leg", "SEAT__BLEG": "seat edge on the back leg", "SEAT__FLEG": "seat edge in the front-leg lap",
         "BLEG__ROCKER": "back foot on the rocker", "FLEG__ROCKER": "front foot on the rocker"}
def title(k):
    side = "right" if k.endswith("_R") else "left" if k.endswith("_L") else ""
    base = "__".join(x[:-2] if x.endswith(("_R", "_L")) else x for x in k.split("__"))
    return f"{TITLE.get(base, k)}{f' ({side})' if side else ''}"
fig, ax = plt.subplots(len(D), len(want), figsize=(3.0 * len(want) + 1.2, 3.3 * len(D)), squeeze=False, constrained_layout=True)
for j, k in enumerate(want):
    ref = D[0][k]; c0 = ref[ref[:, 3] <= 0.15, :3]; o = c0.mean(0); _, _, vt = np.linalg.svd(c0 - o)   # plane of the contact patch (first file)
    for i, d in enumerate(D):
        a = ax[i, j]; X = d[k]; P = (X[:, :3] - o) @ vt[:2].T; g = X[:, 3]; c = g <= 0.15
        a.scatter(P[c, 0], P[c, 1], s=0.4, c="0.75", lw=0)
        sc = a.scatter(P[~c, 0], P[~c, 1], s=1.2, c=g[~c], cmap="inferno_r", vmin=0, vmax=5, lw=0)
        op = (~c).sum() / max(len(c), 1) * 100
        a.set_title(f"{title(k)}\n{'v24' if i == 0 else 'v25'}: {op:.0f}% of the face open", fontsize=8)
        a.set_aspect("equal"); a.tick_params(labelsize=6)
fig.colorbar(sc, ax=ax, shrink=0.6, label="gap to the other part, mm (grey = touching)")
fig.savefig(out, dpi=130); print(out)
