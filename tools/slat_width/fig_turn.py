"""USAGE: tools/py.sh tools/slat_width/fig_turn.py parts/slat_turn.json OUT.png
Turn and width of the side slats along their height (house style): per 100 mm band, left (blue) and right (orange) fits with
bootstrap se, the centre slat as the control (grey), the design line (ink); below, fitted width minus the v23 model width."""
import sys, json
import numpy as np
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
T = json.load(open(sys.argv[1])); BL, OR, SURF, INK, INK2, GRID = "#2a78d6", "#eb6834", "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
plt.rcParams.update({"font.size": 10, "axes.edgecolor": GRID, "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
                     "axes.facecolor": SURF, "figure.facecolor": SURF, "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8})
fig, (a1, a2) = plt.subplots(2, 1, figsize=(8.2, 7.4), sharex=True, gridspec_kw=dict(height_ratios=[3, 1.6], hspace=0.12))
L, R, C = T["left"], T["right"], T["centre_control"]; z = np.array(L["z_mm"])
for blk, col, lab, dz in ((L, BL, "left slat", -6), (R, OR, "right slat", 6)):
    a1.errorbar(z + dz, blk["turn_deg"], yerr=blk["se_deg"], fmt="o", color=col, ms=6, capsize=3, lw=1.4, label=f"{lab} (photos per band: {min(blk['photos'])}-{max(blk['photos'])})")
a1.errorbar(z, C["turn_deg"], yerr=C["se_deg"], fmt="s", color="#9a9893", ms=4.5, capsize=2, lw=1, label="centre slat, control (flat should read 0)")
a1.plot(T["design"]["z_mm"], T["design"]["turn_deg"], color=INK, lw=2.2, label="design: left/right mean, straight line (measured; not applied yet)")
a1.fill_between(T["design"]["z_mm"], np.array(T["design"]["turn_deg"]) - T["tolerance_deg"], np.array(T["design"]["turn_deg"]) + T["tolerance_deg"],
                color=INK, alpha=0.06, lw=0, label=f"tolerance +-{T['tolerance_deg']} deg")
a1.axhline(0, color=INK2, lw=0.9)
a1.set_ylabel("turn (deg), + = outer edge forward"); a1.set_ylim(-4, 12)
a1.set_title("Side slats are turned about their length, outer edge forward", loc="left", color=INK, fontsize=12.5, pad=22)
a1.text(0, 1.02, "silhouette width of each slat read on single photos (both edges in the same photo, pose-free), fitted per 100 mm band",
        transform=a1.transAxes, color=INK2, fontsize=9)
a1.legend(loc="upper right", frameon=False, fontsize=8.5)
for blk, col, dz in ((L, BL, -6), (R, OR, 6)):
    a2.plot(z + dz, np.array(blk["width_fit_mm"]) - np.array(blk["width_model_v23_mm"]), "o-", color=col, ms=5, lw=1.4)
a2.axhline(0, color=INK2, lw=0.9); a2.set_ylim(-2.5, 2.5)
a2.set_ylabel("width, fit - model (mm)"); a2.set_xlabel("height above the floor, z (mm)  (seat at about 330, crest from about 1000)")
a2.text(0.01, 0.06, "widths agree with model v23 within about 1 mm: not changed", transform=a2.transAxes, color=INK2, fontsize=8.5)
for a in (a1, a2):
    for s in ("top", "right"): a.spines[s].set_visible(False)
fig.savefig(sys.argv[2], dpi=150, bbox_inches="tight"); print(sys.argv[2])
