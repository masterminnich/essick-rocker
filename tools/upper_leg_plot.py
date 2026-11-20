"""USAGE: python -I tools/upper_leg_plot.py OUT.png
Picture of the back leg above the arm, traced in side view (parts/side_frame_ub_L.json, _R.json): (left) side elevation of both
sides with the left mirrored onto the right, plus the rear arris from the back views where it is on disk; (right) width square to
the leg against height, left, right and the two earlier models' widths. Tiny compute."""
import json, sys, os, numpy as np
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
L, R = (json.load(open(f"parts/side_frame_ub_{s}.json"))["lines"] for s in "LR"); out = sys.argv[1]
def perp_width(a, b):                                  # distance from each point of polyline a to polyline b (sheet mm)
    a, b = np.array(a), np.array(b); a = a[(a[:, 1] >= b[:, 1].min() + 5) & (a[:, 1] <= b[:, 1].max() - 5)]; d = []
    for p in a:
        s = b[:-1]; e = b[1:]; t = np.clip(((p - s) * (e - s)).sum(1) / ((e - s) ** 2).sum(1), 0, 1); d.append(np.min(np.linalg.norm(s + t[:, None] * (e - s) - p, axis=1)))
    return a[:, 1], np.array(d)
fig, ax = plt.subplots(1, 2, figsize=(12.5, 9), gridspec_kw={"width_ratios": [1.1, 1]})
for D, s, ls in ((L, "L", "--"), (R, "R", "-")):
    for k, c, lab in (("front", "tab:green", "front outline, 4 cameras behind the leg"), ("rear", "tab:red", "rear edge, 2 cameras in front of the leg")):
        X = np.array(D[f"bleg{s}_{k}_hi"]["xyz"]); ax[0].plot(X[:, 1], X[:, 2], ls, color=c, lw=1.7, label=f"{lab}, {'left (mirrored)' if s == 'L' else 'right'}")
    f = f"work/parts/back/t/bleg{s}_out.json"
    if os.path.exists(f):
        X = np.array(json.load(open(f))[f"bleg{s}_out_xyz"]); X = X[(X[:, 2] > 600) & (X[:, 2] < 1040)]
        ax[0].plot(X[:, 1], X[:, 2], ls, color="0.45", lw=1.0, label=f"rear arris from the BACK views (fore-aft is their weak direction), {'left' if s == 'L' else 'right'}")
ax[0].set_aspect("equal"); ax[0].set_xlabel("y, forward (mm)"); ax[0].set_ylabel("z, height above the table (mm)"); ax[0].grid(alpha=.3); ax[0].set_ylim(590, 1050); ax[0].set_xlim(-200, 20)
ax[0].set_title("Back leg above the arm, side elevation\n(dashed = left side mirrored, solid = right side)"); ax[0].legend(fontsize=7.5, loc="upper center", bbox_to_anchor=(0.5, -0.09))
for D, s, ls in ((L, "L", "--"), (R, "R", "-")):
    v, w = perp_width(D[f"bleg{s}_front_hi"]["uv"], D[f"bleg{s}_rear_hi"]["uv"]); ax[1].plot(w, v, ls, color="tab:blue", lw=1.8, label=f"traced in side view, {'left' if s == 'L' else 'right'}")
for name, mk, col in (("v5", "x", "tab:red"), ("v6", "o", "k")):
    p = f"parts/model_{name}_params.json"
    if not os.path.exists(p): continue
    J = json.load(open(p)); B = J["back_leg"] if "back_leg" in J else next(v["back_leg"] for v in J.values() if isinstance(v, dict) and "back_leg" in v)
    zs = [(int(k[1:]), w) for k, w in B["width_side_view_mm"].items() if int(k[1:]) >= 600]
    if name == "v6": zs += [(int(k[1:]), w) for k, w in B["upper_side_view"]["width_square_to_leg_mm"].items()]
    ax[1].plot([w for _, w in zs], [z for z, _ in zs], mk, color=col, ms=8, mew=2, mfc="none", label="model v5 (point-cloud extents)" if name == "v5" else "model v6 (mean of left and right)")
ax[1].set_xlabel("width square to the leg, side view (mm)"); ax[1].set_ylabel("height (sheet v for the traces, z for the models; mm)"); ax[1].grid(alpha=.3); ax[1].set_xlim(20, 52)
ax[1].set_title("Width against height: the leg tapers to the crest"); ax[1].legend(fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.09))
fig.tight_layout(rect=[0, 0, 1, 0.98]); fig.savefig(out, dpi=110); print(out)
