"""USAGE: tools/py.sh tools/critique/fig_rank.py ITEMS.json OUT.png [--top 24] [--title TEXT]
Overview chart of the phase 6 critique: the ranked fix items (items.py) as bars of their symmetric gap (the part a symmetric
model can fix), with each row's tolerance band, the antisymmetric part (the chair's own left/right difference: shown, not
ranked) and the held-out photos' symmetric value. + = the model sticks out beyond the wood."""
import sys, json, argparse
import numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

ap = argparse.ArgumentParser(); ap.add_argument("items"); ap.add_argument("out"); ap.add_argument("--top", type=int, default=24)
ap.add_argument("--title", default="Model v22 against the photos: where the outline misses the wood, ranked by gap / tolerance")
a = ap.parse_args()
BLUE, ORANGE, INK, MUTE, GRID, SURF = "#2a78d6", "#eb6834", "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
plt.rcParams.update({"font.size": 10, "axes.edgecolor": MUTE, "axes.labelcolor": MUTE, "xtick.color": MUTE, "ytick.color": MUTE,
                     "text.color": INK, "axes.spines.top": False, "axes.spines.right": False})
NAMES = {"FLEG": "front leg", "BLEG": "back leg", "ARM": "arm", "ROCKER": "rocker", "SEAT": "seat", "CREST": "crest", "SLAT_LR": "side slats", "SLAT_C": "centre slat"}
items = json.load(open(a.items))[:a.top]
n = len(items); y = np.arange(n)[::-1]
fig, ax = plt.subplots(figsize=(12.5, 0.36 * n + 2.0), facecolor=SURF); ax.set_facecolor(SURF)
ax.grid(axis="x", color=GRID, lw=0.6); ax.set_axisbelow(True)
for yi, it in zip(y, items):
    t = it["tol_mm"]
    ax.add_patch(plt.Rectangle((-t, yi - 0.42), 2 * t, 0.84, color=GRID, alpha=0.7, lw=0, zorder=1))
    ax.barh(yi, it["symmetric_median"], height=0.5, color=BLUE, zorder=3)
    if it["antisymmetric_range"]:
        an = it["antisymmetric_range"]; mid = 0.5 * (an[0] + an[1])
        ax.plot([an[0], an[1]], [yi, yi], color=ORANGE, lw=1.4, zorder=4); ax.plot([mid], [yi], "D", ms=5, color=ORANGE, mec=SURF, mew=0.8, zorder=5)
    if it["held_out"]:
        ax.plot([float(np.median(it["held_out"]))], [yi], "|", ms=13, mew=2.2, color=INK, zorder=6)
    s = it["symmetric_median"]
    note = f"{s:+.1f}" + ("" if it["antisymmetric_range"] else f"  one side only ({it['one_side'][0] if it['one_side'] else '?'})")
    ends = [s] + ([float(np.median(it["held_out"]))] if it["held_out"] else [])
    xe = max(ends + [0]) + 0.15 if s >= 0 else min(ends + [0]) - 0.15
    ax.text(xe, yi, note, ha="left" if s >= 0 else "right", va="center", fontsize=8.5, color=INK, zorder=7)
lab = [f"{i['rank']}. {NAMES.get(i['member'], i['member'])}  {i['edge']}  {i['axis']} {i['from_mm']}..{i['to_mm']}" for i in items]
ax.set_yticks(y); ax.set_yticklabels(lab, fontsize=9); ax.set_ylim(-0.8, n - 0.3)
lim = max(5.0, max(abs(i["symmetric_median"]) for i in items) + 1.2); ax.set_xlim(-lim, lim)
ax.axvline(0, color=MUTE, lw=0.8, zorder=2)
ax.set_xlabel("gap, mm   (- = the model lies inside the wood,  + = the model sticks out beyond the wood)")
h = [plt.Rectangle((0, 0), 1, 1, color=BLUE), plt.Rectangle((0, 0), 1, 1, color=GRID),
     plt.Line2D([], [], color=ORANGE, marker="D", ms=5, lw=1.4), plt.Line2D([], [], color=INK, marker="|", ms=12, mew=2.2, lw=0)]
ax.legend(h, ["symmetric gap (L+R)/2: fixable, ranked", "tolerance: 0.8 mm at joints, 1.6 mm on free curves",
              "antisymmetric (L-R)/2: the chair's own asymmetry, not ranked", "held-out photos (median)"],
          loc="lower left", bbox_to_anchor=(0, 1.0), ncol=2, frameon=False, fontsize=9)
ax.set_title(a.title, loc="left", fontsize=12.5, color=INK, pad=46)
fig.tight_layout(); fig.savefig(a.out, dpi=150, facecolor=SURF); print("wrote", a.out)
