"""USAGE: tools/py.sh tools/seat_scoop/fig_lr.py [OUT figures/seat_scoop_left/left_vs_right.png]   (after compare_lr.py and fit.py with the left solve)
Left against right along the seat's side edge (parts/seat_scoop.json, work/seat_scoop_L/compare.json):
  left  - height of the hard line above each side's own underside (the lens), both sides with their jackknife spread, and the design (the mean)
  right - left minus right for the lens and for the edge-face height, with 2 standard errors and the 1.6 mm free-curve tolerance"""
import sys, json, numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
out = sys.argv[1] if len(sys.argv) > 1 else "figures/seat_scoop_left/left_vs_right.png"
S = json.load(open("parts/seat_scoop.json")); K = json.load(open("work/seat_scoop_L/compare.json")); T = K["table"]; ys = np.array(K["stations_y"])
f = lambda k, s: np.array([np.nan if v is None else v for v in T[k][s]], float)
BLUE, ORANGE, INK, MUTE, GRID, SURF = "#2a78d6", "#eb6834", "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
plt.rcParams.update({"font.size": 10, "axes.edgecolor": MUTE, "axes.labelcolor": MUTE, "xtick.color": MUTE, "ytick.color": MUTE, "text.color": INK, "axes.spines.top": False, "axes.spines.right": False})
fig, (a, b) = plt.subplots(1, 2, figsize=(13, 5.6), facecolor=SURF)
for ax in (a, b): ax.set_facecolor(SURF); ax.grid(color=GRID, lw=0.6); ax.set_axisbelow(True)
HR, HL = np.array(S["right"]["height_of_hard_line_above_underside_mm"]), np.array(S["left"]["height_of_hard_line_above_underside_mm"])
D = S["design"]["hard_line_height_above_underside_of_y"]; dy, dh = np.array(D["y"]), np.array(D["height_mm"])
nR, nL = len(K["photos"]["right"]["crescent"]), len(K["photos"]["left"]["crescent"])
for H, k, c, lab in ((HR, "right", BLUE, f"right side ({nR} photos)"), (HL, "left", ORANGE, f"left side ({nL} photos)")):
    g, se = f("g", k), f("g", "se_" + k); a.fill_between(ys, g - 2 * se, g + 2 * se, color=c, alpha=0.15, lw=0)
    a.plot(H[:, 0], H[:, 1], color=c, lw=2, label=lab); i = int(H[:, 1].argmax())
    a.plot(H[i, 0], H[i, 1], "o", ms=7, color=c, mec=SURF, mew=2); a.annotate(f"{H[i, 1]:.1f} at y {H[i, 0]:.0f}", (H[i, 0], H[i, 1]), (H[i, 0] + (14 if k == "right" else 0), H[i, 1] + (1.4 if k == "right" else -4.5)), color=c, ha="left" if k == "right" else "center")
a.plot(dy, dh, color=INK, lw=1.4, ls=(0, (5, 3)), label="design = mean (model v20)")
a.text(410, 25, "bands: 2 standard errors\n(jackknife over photos)", color=MUTE, fontsize=9, ha="center")
a.set_xlim(60, 480); a.set_ylim(-0.8, 29); a.set_xlabel("station y, mm (back leg on the left, front leg on the right)"); a.set_ylabel("hard line above that side's underside, mm")
a.set_title("The lens: the left side is up to 3.8 mm shallower", loc="left", fontsize=11, color=INK); a.legend(loc="upper left", frameon=False, fontsize=9)
b.axhspan(-1.6, 1.6, color=GRID, alpha=0.6, lw=0); b.text(455, 1.25, "±1.6 mm tolerance", color=MUTE, ha="right", va="top", fontsize=9); b.axhline(0, color=MUTE, lw=0.8)
for k, c, lab in (("g", ORANGE, "lens (hard line above underside)"), ("face", BLUE, "edge-face height (top arris to hard line)")):
    d, se = f(k, "left_minus_right"), f(k, "se_diff"); b.fill_between(ys, d - 2 * se, d + 2 * se, color=c, alpha=0.15, lw=0); b.plot(ys, d, color=c, lw=2, label=lab)
    i = int(np.nanargmax(np.abs(d))); b.plot(ys[i], d[i], "o", ms=7, color=c, mec=SURF, mew=2); b.annotate(f"{d[i]:+.1f} at y {ys[i]:.0f}", (ys[i], d[i]), (ys[i] + 12, d[i] + (-0.9 if d[i] < 0 else 0.7)), color=c)
b.set_xlim(100, 460); b.set_ylim(-7, 6.5); b.set_xlabel("station y, mm"); b.set_ylabel("left minus right, mm")
b.set_title("Left minus right, each relative to its own edge", loc="left", fontsize=11, color=INK); b.legend(loc="lower right", frameon=False, fontsize=9)
fig.tight_layout(); fig.savefig(out, dpi=140, facecolor=SURF); print("wrote", out)
