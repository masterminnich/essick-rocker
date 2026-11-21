"""USAGE: python -I tools/seat_front_face_plot.py OUT.png
Front elevation and plan of the seat's front edge from parts/seat_front_face.json: right and left halves as triangulated, the
symmetric design, and what model v10 had (parts/model_v10_params.json). Tiny compute."""
import sys, json
from pathlib import Path
import numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
ROOT = Path(__file__).resolve().parent.parent
F = json.load(open(ROOT / "parts/seat_front_face.json")); D = F["design"]; G = np.array(json.load(open(ROOT / "parts/seat_front.json"))["design"]["front_y_of_abs_x"])
V = json.load(open(ROOT / "parts/model_v10_params.json"))["parts"]["seat"]["front_edge"]; vx = np.array([int(k[1:]) for k in V["top_z_along_front_edge"]]); vt = np.array(list(V["top_z_along_front_edge"].values())); vb = vt - np.array(list(V["front_edge_height_top_to_underside_mm"].values()))
a = lambda k, S=D: np.array(S[k]); CR, CL, CD, CV = "#c2410c", "#0f766e", "#111827", "#9ca3af"
fig, ax = plt.subplots(2, 1, figsize=(12, 9.6), dpi=150, gridspec_kw={"height_ratios": [78, 46]})
for sg in (1, -1):
    for key, lab in (("top_of_roll_z_of_abs_x", "design (left/right mean)"), ("bottom_arris_z_of_abs_x_with_corner", None)):
        t = a(key); ax[0].plot(sg * t[:, 0], t[:, 1], color=CD, lw=2.2, label=lab if sg == 1 else None, zorder=3)
    ax[0].plot(sg * vx, vt, color=CV, lw=1.4, ls="--", marker="o", ms=3, label="model v10 (7 stations)" if sg == 1 else None); ax[0].plot(sg * vx, vb, color=CV, lw=1.4, ls="--", marker="o", ms=3)
    by = a("bottom_arris_y_of_abs_x"); ax[1].plot(sg * G[:, 0], G[:, 1], color=CD, lw=2.2, label="top edge, plan outline (parts/seat_front.json)" if sg == 1 else None, zorder=3)
    ax[1].plot(sg * by[:, 0], by[:, 1], color=CD, lw=1.6, ls=":", label="bottom arris, design" if sg == 1 else None, zorder=3)
for side, sg, c in (("right", 1, CR), ("left", -1, CL)):
    S = F[side]
    for k in ("top_of_roll_z", "bottom_arris_z"): t = a(k, S); ax[0].plot(sg * t[:, 0], t[:, 1], color=c, lw=1.2, marker=".", ms=4, label=f"{side} half as triangulated" if k == "top_of_roll_z" else None)
    t = a("top_plan_outline_y", S); ax[1].plot(sg * t[:, 0], t[:, 1], color=c, lw=1.2, marker=".", ms=4, label=f"{side}: top edge, this solve"); t = a("bottom_arris_y", S); ax[1].plot(sg * t[:, 0], t[:, 1], color=c, lw=1.2, ls=":", marker="x", ms=4, label=f"{side}: bottom arris")
ax[0].set_title("Seat front edge, seen from the front: top of the rolled edge and bottom arris of the front face (heights drawn 3x)", loc="left", fontsize=11); ax[0].set_ylabel("height above the table Z (mm)")
ax[0].annotate("top of the roll", (135, 402.3), (135, 412), ha="center", fontsize=9, arrowprops=dict(arrowstyle="-", color="#6b7280")); ax[0].annotate("bottom arris", (135, 381.7), (135, 373), ha="center", fontsize=9, arrowprops=dict(arrowstyle="-", color="#6b7280"))
ax[1].set_title("The same edge in plan (from above): the bottom arris sits under the top edge within 2 mm for |x| < 240 (Y drawn 3x)", loc="left", fontsize=11); ax[1].set_ylabel("forward Y (mm)"); ax[1].set_xlabel("X (mm); chair's left is negative, chair's right positive")
for q in ax: q.set_aspect(3); q.grid(True, color="#e5e7eb", lw=0.6); q.set_xlim(-280, 280); q.legend(fontsize=8.5, frameon=False, ncol=4, loc="upper center", bbox_to_anchor=(0.5, -0.12)); [s.set_visible(False) for s in (q.spines["top"], q.spines["right"])]
ax[0].set_ylim(368, 446); ax[1].set_ylim(506, 552); fig.tight_layout(); fig.savefig(sys.argv[1]); print(sys.argv[1])
