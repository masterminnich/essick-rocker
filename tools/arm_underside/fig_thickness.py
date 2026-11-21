"""USAGE: tools/py.sh tools/arm_underside/fig_thickness.py [OUT figures/arm_underside/thickness.png]      (after fit.py)
The arms' thickness along their length from parts/arm_underside.json:
  left  - vertical thickness at the OUTER face (outer top arris to outer bottom arris): right arm, left arm (2 se bands, jackknife over
          photos), the design (their mean) and the old model (25 mm square to the top); the stretches not seen are drawn thin
  right - the underside across the arm: how much lower its inner bottom arris sits than the outer one, right and left, and the design"""
import sys, json, numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
out = sys.argv[1] if len(sys.argv) > 1 else "figures/arm_underside/thickness.png"
J = json.load(open("parts/arm_underside.json")); D = J["design"]; y = np.array(D["y"])
A = lambda v: np.array([np.nan if x is None else x for x in v], float)
BLUE, ORANGE, INK, MUTE, GRID, SURF = "#2a78d6", "#eb6834", "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
plt.rcParams.update({"font.size": 10, "axes.edgecolor": MUTE, "axes.labelcolor": MUTE, "xtick.color": MUTE, "ytick.color": MUTE, "text.color": INK, "axes.spines.top": False, "axes.spines.right": False})
fig, (a, b) = plt.subplots(1, 2, figsize=(13, 5.6), facecolor=SURF, gridspec_kw={"width_ratios": [1.45, 1]})
for ax in (a, b): ax.set_facecolor(SURF); ax.grid(color=GRID, lw=0.6); ax.set_axisbelow(True)
for k, c, lab in (("right", BLUE, "right arm"), ("left", ORANGE, "left arm")):
    S = J[k]; h, se = A(S["h_outer_mm"]), A(S["h_outer_se_mm"]); m = np.isfinite(se); n = len(S["photos_above"])
    a.fill_between(y[m], (h - 2 * se)[m], (h + 2 * se)[m], color=c, alpha=0.18, lw=0)
    a.plot(np.where(m, y, np.nan), h, color=c, lw=2, label=f"{lab} ({n} photos)"); a.plot(y, h, color=c, lw=0.8, alpha=0.6)
hd, old = A(D["h_outer_mm"]), A(D["old_model_vertical_mm"])
a.plot(y, hd, color=INK, lw=1.4, ls=(0, (5, 3)), label="design = mean (parts/arm_underside.json)")
a.plot(y, old, color=MUTE, lw=1.6, ls=(0, (1, 2)), label="old model: 25 mm square to the top (assumed)")
for yy in (60, 200, 300, 440):
    i = int(np.argmin(np.abs(y - yy))); a.plot(y[i], hd[i], "o", ms=6, color=INK, mec=SURF, mew=2)
    a.annotate(f"{hd[i]:.1f}", (y[i], hd[i]), (y[i] + 6, hd[i] + 1.0), color=INK, fontsize=9)
a.axvspan(40, 60, color=GRID, alpha=0.5, lw=0); a.axvspan(490, 510, color=GRID, alpha=0.5, lw=0)
a.text(50, 18.6, "not seen\n(back leg)", ha="center", color=MUTE, fontsize=8.5); a.text(500, 18.6, "not\nseen", ha="center", color=MUTE, fontsize=8.5)
a.text(430, 33, "front leg at y 439", color=MUTE, fontsize=9, ha="center"); a.axvline(439, color=MUTE, lw=0.6, ls=":")
a.set_xlim(40, 510); a.set_ylim(17.5, 40.5); a.set_xlabel("station y along the arm, mm (back leg on the left, front end on the right)")
a.set_ylabel("thickness at the outer face, vertical, mm"); a.legend(loc="upper right", frameon=False, fontsize=9)
a.set_title("Thick at the back leg, thinner than assumed from mid-arm forward", loc="left", fontsize=11, color=INK)
for k, c, lab in (("right", BLUE, "right (3 photos from below)"), ("left", ORANGE, "left (1 photo, IMG_1519)")):
    b.plot(y, A(J[k]["cross_drop_inner_minus_outer_mm"]), color=c, lw=2, label=lab)
b.plot(y, A(D["h_inner_mm"]) - hd, color=INK, lw=1.4, ls=(0, (5, 3)), label="design = mean (held at its end values)")
b.axhline(0, color=MUTE, lw=0.8); b.set_xlim(40, 510); b.set_ylim(-1.5, 11); b.set_xlabel("station y, mm")
b.set_ylabel("inner bottom arris lower than the outer one, mm"); b.legend(loc="upper right", frameon=False, fontsize=9)
b.set_title("Across the underside (arm 34-76 mm wide in plan)", loc="left", fontsize=11, color=INK)
fig.tight_layout(); fig.savefig(out, dpi=140, facecolor=SURF); print("wrote", out)
