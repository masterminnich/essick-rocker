"""Chart: Domino centre minus the middle of the leg face's two arrises, per photo, against the camera's angle around the leg."""
import json, numpy as np, matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
BLUE, ORANGE, SURF, INK, INK2, GRID = "#2a78d6", "#eb6834", "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
A = json.load(open("work/fdom/analysis.json")); B = json.load(open("work/fdom/dcheck_model_v18.json")); T = json.load(open("work/fdom/dcheck_trial.json"))
fig, ax = plt.subplots(figsize=(9, 4.8), dpi=150); fig.patch.set_facecolor(SURF); ax.set_facecolor(SURF)
for leg, col, name in (("L", BLUE, "left leg"), ("R", ORANGE, "right leg")):
    R = A[leg]["rows"]; u = [r for r in R if r["used"]]; x = [r for r in R if not r["used"]]
    ax.scatter([r["az"] for r in u], [r["offset"] for r in u], s=34, color=col, zorder=3, label=f"{name}: {A[leg]['n_used']} photos, mean {A[leg]['offset_mean']:+.2f}, sd {A[leg]['offset_sd']:.2f} mm")
    ax.scatter([r["az"] for r in x], [r["offset"] for r in x], s=34, facecolors="none", edgecolors=col, alpha=0.6, zorder=3)
    ax.axhline(A[leg]["offset_mean"], color=col, lw=1, ls=":", zorder=2)
ax.axhline(B["R"]["offset"], color=INK2, lw=1.5, ls="--"); ax.text(-57, B["R"]["offset"] + 0.08, f"model v18: {B['R']['offset']:+.2f} mm", color=INK2, fontsize=9)
ax.axhline(T["R"]["offset"], color=INK, lw=1.5); ax.text(-57, T["R"]["offset"] - 0.25, f"after this fix: {T['R']['offset']:+.2f} mm", color=INK, fontsize=9)
ax.axhline(0, color=GRID, lw=1); ax.text(25.5, 0.06, "centred", color=INK2, fontsize=8, ha="right")
ax.set_xlim(-58, 26); ax.set_ylim(-2.6, 2.8); ax.grid(True, color=GRID, lw=0.6); ax.set_axisbelow(True)
for s in ax.spines.values(): s.set_color(GRID)
ax.tick_params(colors=INK2, labelsize=8)
ax.set_xlabel("camera angle around the leg face, deg  (+ = in front of the leg, - = behind)", color=INK2, fontsize=9)
ax.set_ylabel("Domino centre - middle of the two arrises, mm\n(+ = toward the leg's front)", color=INK2, fontsize=9)
ax.set_title(f"Front-leg Domino across the leg face: {A['both']['n']} photos, mean {A['both']['offset_mean']:+.2f} mm (sd {A['both']['offset_sd']:.2f}, se {A['both']['sem']:.2f})", color=INK, fontsize=10.5, loc="left")
ax.legend(loc="upper left", fontsize=8, frameon=False, labelcolor=INK2)
ax.text(25.5, -2.5, "hollow: not used (steep view, faint end, or the edge bands disagree)", color=INK2, fontsize=7.5, ha="right")
fig.tight_layout(); fig.savefig("figures/front_domino/offset_per_photo.png", facecolor=SURF); print("ok")
