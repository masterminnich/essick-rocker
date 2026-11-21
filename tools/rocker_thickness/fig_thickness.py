"""USAGE: tools/py.sh tools/rocker_thickness/fig_thickness.py [OUT figures/rocker_thickness/thickness.png]
The rockers' thickness across along their length (parts/rocker_section.json):
  top    - thickness: left, right (outboard photos, median and spread per station), the design (their mean, smoothed), the old model (31 mm),
           the tape at the tail tip (IMG_1493: 1.20 in +-1/16) with its error bar
  middle - where the faces sit across (inward from the old model's outer face): each side's outer and inner arris, the design's two faces
  bottom - photos per station, left and right"""
import sys, json, numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
out = sys.argv[1] if len(sys.argv) > 1 else "figures/rocker_thickness/thickness.png"; S = json.load(open("parts/rocker_section.json")); D = S["design"]
BLUE, ORANGE, INK, MUTE, GRID, SURF = "#2a78d6", "#eb6834", "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
plt.rcParams.update({"font.size": 10, "axes.edgecolor": MUTE, "axes.labelcolor": MUTE, "xtick.color": MUTE, "ytick.color": MUTE, "text.color": INK, "axes.spines.top": False, "axes.spines.right": False})
fig = plt.figure(figsize=(13.5, 11.0), facecolor=SURF); gs = fig.add_gridspec(3, 1, height_ratios=[1.35, 1.25, 0.45], hspace=0.32)
a, b, c = (fig.add_subplot(gs[i]) for i in range(3))
for ax in (a, b, c): ax.set_facecolor(SURF); ax.grid(color=GRID, lw=0.6); ax.set_axisbelow(True); ax.set_xlim(-500, 670)
legs = [(23, 67, "back leg"), (524, 568, "front leg")]
for ax in (a, b, c):
    for u0, u1, _ in legs: ax.axvspan(u0, u1, color=GRID, alpha=0.6, zorder=0)
u = np.array(D["u"]); off = {"left": -2.5, "right": 2.5}
for side, key, col in (("left", "left", BLUE), ("right", "right", ORANGE)):
    R = S[key]; uu = np.array([float(k) for k in R]); T = np.array([R[k]["T"] for k in R]); sp = np.array([R[k]["spread"] for k in R]); kp = np.array([R[k]["kept"] for k in R])
    a.errorbar(uu[kp] + off[side], T[kp], yerr=sp[kp], fmt="o", ms=3.6, color=col, ecolor=col, elinewidth=0.8, capsize=0, label=f"{side} rocker: median of the outboard photos, bar = spread", zorder=3)
    a.plot(uu[~kp] + off[side], np.clip(T[~kp], 27.2, 40), "x", ms=5, color=col, mew=1.1, zorder=3, label=f"{side}: dropped (spread > 2 mm, a leg's shadow)" )
    do = np.array([R[k]["d_out"] for k in R]); di = np.array([R[k]["d_in"] for k in R])
    b.plot(uu[kp], do[kp], "o", ms=3.2, color=col, zorder=3); b.plot(uu[kp], di[kp], "o", ms=3.2, color=col, zorder=3, mfc=SURF)
    n = np.array([R[k]["n"] for k in R]); c.bar(uu + off[side] * 1.6, n, width=7.5, color=col, label=f"{side}")
a.plot(u, D["T_mm"], color=INK, lw=2.2, label="design (v23): left and right averaged, smoothed", zorder=4)
a.plot([-488.2, 660], [31, 31], color=MUTE, lw=1.4, ls=(0, (5, 3)), label="model before (v22): 31 mm, tape value assumed constant", zorder=2)
a.errorbar([-468], [30.48], yerr=[1.59], fmt="s", ms=6, color=INK, mfc=SURF, mew=1.5, capsize=4, elinewidth=1.3, zorder=5)
a.annotate("tape at the tail tip (IMG_1493):\n1.20 in = 30.5 mm, +-1/16 in", (-468, 30.48), (-440, 27.9), color=INK, va="center", ha="left", arrowprops=dict(arrowstyle="-", color=MUTE, lw=0.8))
for u0, u1, t in legs: a.text((u0 + u1) / 2, 39.6, t, ha="center", va="top", color=MUTE, fontsize=9)
a.set_ylim(27, 40); a.set_ylabel("thickness across, mm"); a.legend(loc="upper left", frameon=False, ncol=2, fontsize=9, bbox_to_anchor=(0, 0.93))
a.set_title("Thickness across the rocker, outer face to inner face, measured on the top face", loc="left", fontsize=12, color=INK)
d0 = np.array(D["d_outer_mm"]); a_ = d0 + np.array(D["T_mm"])
b.plot(u, d0, color=INK, lw=2.2); b.plot(u, a_, color=INK, lw=2.2); b.axhline(0, color=MUTE, lw=1.4, ls=(0, (5, 3))); b.axhline(31, color=MUTE, lw=1.4, ls=(0, (5, 3)))
b.text(-490, 0.8, "old outer face", color=MUTE, ha="left", va="top"); b.text(-490, 25.5, "old inner face (31)", color=MUTE, ha="left", va="center")
b.text(-330, -6.5, "design outer face", color=INK, ha="left", va="center"); b.text(60, 39.5, "design inner face (outer face + thickness)", color=INK, ha="left", va="center")
b.plot([], [], "o", ms=4, color=MUTE, label="outer arris (filled)"); b.plot([], [], "o", ms=4, color=MUTE, mfc=SURF, label="inner arris (open)")
b.legend(loc="center right", frameon=False, fontsize=9); b.set_ylim(-9, 43); b.invert_yaxis()
b.set_ylabel("inward from the old outer face, mm (outward up)"); b.set_title("Where the faces sit across: left (blue) and right (orange) as each photo's pose puts them; the design takes their mean", loc="left", fontsize=12, color=INK)
c.set_ylabel("photos"); c.set_xlabel("u along the rocker, mm (tail tip -488, nose top corner 627)"); c.legend(loc="upper left", frameon=False, ncol=2, fontsize=9)
c.set_title("Outboard photos per station", loc="left", fontsize=11, color=INK)
fig.suptitle("Rocker thickness across: 29.7 mm at the tail tip, 33-34 at the back leg, 36 between the legs, 34 at the front leg (v22: 31 throughout)", x=0.012, ha="left", fontsize=13, color=INK)
fig.subplots_adjust(left=0.06, right=0.985, top=0.94, bottom=0.05); fig.savefig(out, dpi=150, facecolor=SURF); print("wrote", out)
