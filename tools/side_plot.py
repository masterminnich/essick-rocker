"""USAGE: python -I tools/side_plot.py parts/side_frame_L.json parts/side_frame_R.json OUT.png
Picture of the triangulated side-frame lines: (left) side elevation, left side mirrored onto the right; (right) member width in
side view against height for both sides, with the tape close-ups and the old median-trace widths for comparison. Tiny compute."""
import json, sys, numpy as np
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
L, R = (json.load(open(p))["lines"] for p in sys.argv[1:3]); out = sys.argv[3]
def perp_width(a, b):                                  # distance from each point of polyline a to polyline b (sheet mm)
    a, b = np.array(a), np.array(b); a = a[(a[:, 1] >= b[:, 1].min() + 5) & (a[:, 1] <= b[:, 1].max() - 5)]; d = []
    for p in a:
        s = b[:-1]; e = b[1:]; t = np.clip(((p - s) * (e - s)).sum(1) / ((e - s) ** 2).sum(1), 0, 1); d.append(np.min(np.linalg.norm(s + t[:, None] * (e - s) - p, axis=1)))
    return a[:, 1], np.array(d)
fig, ax = plt.subplots(1, 2, figsize=(13, 7.5), gridspec_kw={"width_ratios": [1.25, 1]})
kind = {"front": ("tab:green", "front outline (arris)"), "rear": ("tab:orange", "rear ridge of the outer face (soft, +-2 mm)"), "rearfar": ("tab:red", "inner rear arris (far side of the thickness)")}
seen = set()
for D, side, ls in ((L, "L", "--"), (R, "R", "-")):
    for k, l in D.items():
        X = np.array(l["xyz"]); c, lab = kind[k.split("_")[1]]; lab = f"{lab}, {'left (mirrored)' if side == 'L' else 'right'}"
        ax[0].plot(X[:, 1], X[:, 2], ls, color=c, lw=1.6, label=None if lab in seen else lab); seen.add(lab)
ax[0].set_aspect("equal"); ax[0].set_xlabel("y, forward (mm)"); ax[0].set_ylabel("z, height above the table (mm)"); ax[0].grid(alpha=.3)
ax[0].set_title("Side elevation: lines triangulated one by one\n(dashed = left side, solid = right side)"); ax[0].legend(fontsize=8, loc="upper left")
ax[0].text(60, 310, "back leg\n(below the seat)", fontsize=9, ha="center"); ax[0].text(380, 300, "front leg", fontsize=9, ha="center")
for D, side, ls in ((L, "L", "--"), (R, "R", "-")):
    for mem, col in (("fleg", "tab:blue"), ("bleg", "tab:purple")):
        for part in ("lo", "hi"):
            f, r, rf = (D.get(f"{mem}{side}_{n}_{part}") for n in ("front", "rear", "rearfar"))
            if not f: continue
            v, w = perp_width(f["uv"], r["uv"]); ax[1].plot(w, v, ls, color=col, lw=1.5, label=f"{'front' if mem == 'fleg' else 'back'} leg outer face, {side}" if part == "lo" else None)
            v, w = perp_width(f["uv"], rf["uv"]); ax[1].plot(w, v, ls, color=col, lw=1.5, alpha=.45, label=f"{'front' if mem == 'fleg' else 'back'} leg overall, {side}" if part == "lo" else None)
ax[1].errorbar([39.6], [350], xerr=[1.6], fmt="ks", ms=6, capsize=3, label="tape close-up IMG_1497 (39.6 +-1.6)")
ax[1].plot([29.2], [600], "k^", ms=7, label="tape close-up IMG_1498 (29.2)")
ax[1].plot([55.5, 58.6], [150, 300], "rx", ms=9, mew=2, label="old front-leg width (trace on the 8-photo median)")
ax[1].axhspan(370, 470, color="0.85", zorder=0); ax[1].text(61, 420, "seat joint\n(hidden)", fontsize=8, va="center", ha="right")
ax[1].set_xlabel("width in side view (mm)"); ax[1].set_ylabel("height along the sheet, v (mm)"); ax[1].grid(alpha=.3); ax[1].set_xlim(25, 62)
ax[1].set_title("Member width against height"); ax[1].legend(fontsize=7.5, loc="upper right")
fig.tight_layout(rect=[0, 0, 1, 0.98]); fig.savefig(out, dpi=110); print(out)
