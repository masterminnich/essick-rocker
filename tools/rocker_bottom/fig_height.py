"""USAGE: tools/py.sh tools/rocker_bottom/fig_height.py [FIT work/rbot/fit4.json] [OUT figures/rocker_bottom/face_height.png]
Face height of the rockers along u -330..572 (top edge to bottom edge, square to the top edge), from tools/rocker_bottom/fit.py:
  top    - left, right (with each station's spread), design (their average), the model before (parts/rocker_profile.json mean_top / mean_bot)
  middle - design minus the model before, the tolerance band (1.6 mm), and the correction the build now reads (parts/rocker_bottom.json)
  bottom - photos per station, each side"""
import sys, json, numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
F = json.load(open(sys.argv[1] if len(sys.argv) > 1 else "work/rbot/fit4.json")); out = sys.argv[2] if len(sys.argv) > 2 else "figures/rocker_bottom/face_height.png"
P = json.load(open("parts/rocker_bottom.json")); SU = np.array(F["stations_u"]); D = F["design"]
BLUE, ORANGE, INK, MUTE, GRID, SURF = "#2a78d6", "#eb6834", "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
plt.rcParams.update({"font.size": 10, "axes.edgecolor": MUTE, "axes.labelcolor": MUTE, "xtick.color": MUTE, "ytick.color": MUTE, "text.color": INK, "axes.spines.top": False, "axes.spines.right": False})
arr = lambda x: np.array([np.nan if v is None else v for v in x], float)
fig, (a, b, c) = plt.subplots(3, 1, figsize=(13.5, 10.6), sharex=True, gridspec_kw={"height_ratios": [1.5, 1.0, 0.55]}, facecolor=SURF)
for ax in (a, b, c): ax.set_facecolor(SURF); ax.grid(color=GRID, lw=0.6); ax.set_axisbelow(True); ax.axvspan(90, 240, color=GRID, alpha=0.5, zorder=0)
hM = arr(D["model_h_mm"]); hD = arr(D["h_mm"])
for S, col, nm in (("L", BLUE, "left"), ("R", ORANGE, "right")):
    h = arr(F[S]["h_mm"]); s = arr(F[S]["spread_mm"]); a.fill_between(SU, h - s, h + s, color=col, alpha=0.13, lw=0); a.plot(SU, h, color=col, lw=1.3, label=f"{nm} rocker, traced (band: spread over the photos)")
a.plot(SU, hM, color=MUTE, lw=1.5, ls=(0, (5, 3)), label="model before (v21): fitted bottom"); a.plot(SU, hD, color=INK, lw=2.2, label="design: left and right averaged")
cu = np.array(P["correction"]["u"]); cdv = np.array(P["correction"]["dv_mm"])
a.set_ylim(22.5, 29.5); a.set_ylabel("face height, mm"); a.legend(loc="lower right", frameon=False, ncol=2)
a.set_title("Face height of the rockers between the two ends: top edge to bottom edge, square to the top edge", loc="left", fontsize=12, color=INK)
a.text(165, 29.1, "contact with the table: the face's lower edge\nmeets the rocker's own shadow", ha="center", va="top", color=MUTE, fontsize=9)
d = arr(D["new_minus_model_mm"]); b.axhspan(-1.6, 1.6, color=GRID, alpha=0.7, zorder=0); b.axhline(0, color=MUTE, lw=0.8)
sD = 0.5 * np.sqrt(np.nan_to_num(arr(F["L"]["spread_mm"])) ** 2 + np.nan_to_num(arr(F["R"]["spread_mm"])) ** 2)
b.fill_between(SU, d - sD, d + sD, color=INK, alpha=0.10, lw=0); b.plot(SU, d, color=INK, lw=1.8, label="design minus model before (band: spread)")
for S, col in (("L", BLUE), ("R", ORANGE)): b.plot(SU, arr(F[S]["h_mm"]) - hM, color=col, lw=0.9, alpha=0.8)
m = (cu >= -330); b.plot(cu[m], -cdv[m], color=ORANGE, lw=0, marker="o", ms=0)
b.plot(SU, -np.interp(SU, cu, cdv, left=0, right=0), color="#0b6e4f", lw=2.0, label="model v22 minus model before (parts/rocker_bottom.json)")
b.text(560, 1.45, "tolerance 1.6 mm", ha="right", va="top", color=MUTE, fontsize=9); b.set_ylim(-3.2, 2.0); b.set_ylabel("face height change, mm"); b.legend(loc="lower right", frameon=False)
i330 = 0; b.annotate(f"tail: {d[i330]:+.1f} at u -330\n(the ends, PR #23: -1.5 at u -320)", (SU[i330], d[i330]), (-300, -2.9), color=INK, va="center", ha="left", fontsize=9, arrowprops=dict(arrowstyle="-", color=MUTE, lw=0.8))
for S, col, off in (("L", BLUE, 0.18), ("R", ORANGE, -0.18)): c.bar(SU + off * 5, F[S]["photos"], width=1.8, color=col, label="left" if S == "L" else "right")
c.axhline(3, color=MUTE, lw=0.8, ls=(0, (3, 3))); c.set_ylim(0, 21); c.text(572, 20.5, "dotted: 3 photos; below this a station counts as not seen (the design then takes the other side)", ha="right", va="top", color=MUTE, fontsize=9)
c.set_ylabel("photos"); c.set_xlabel("u along the rocker, mm (front positive; the tail end starts at -330, the nose at 572)"); c.legend(loc="upper left", frameon=False, ncol=2); c.set_xlim(-340, 580)
fig.tight_layout(); fig.savefig(out, dpi=150, facecolor=SURF); print("wrote", out)
