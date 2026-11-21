"""USAGE: tools/py.sh tools/arm_underside/fig_joint_section.py OLD.glb NEW.glb OUT.png [x1 x2 ...]
Vertical sections (plane x = const, right side) of the arm / back-leg joint in two BUILT chairs: outlines of BLEG_R, ARM_R and the
rear arm Domino DOMINO_RAR in the y-z plane, one row per x, old model left, new right. A sliver or a gap between the Domino and its
mortises would show as a second outline line alongside the Domino's."""
import sys, numpy as np, trimesh, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
old, new, out = sys.argv[1:4]; xs = [float(v) for v in sys.argv[4:]] or [211.0, 203.0]
INK, INK2, GRID, SURF = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
COL = {"BLEG_R": INK2, "ARM_R": "#2a78d6", "DOMINO_RAR": "#eb6834"}
G = {t: trimesh.load(p).geometry for t, p in (("old", old), ("new", new))}
fig, ax = plt.subplots(len(xs), 2, figsize=(11, 5.2 * len(xs)), facecolor=SURF, squeeze=False)
for r, x in enumerate(xs):
    for c, (t, lab) in enumerate((("old", old), ("new", new))):
        a = ax[r, c]; a.set_facecolor(SURF)
        for k, col in COL.items():
            s = G[t][k].section(plane_origin=[x, 0, 0], plane_normal=[1, 0, 0])
            if s is None: continue
            for d in s.discrete: a.plot(d[:, 1], d[:, 2], color=col, lw=1.6 if k != "DOMINO_RAR" else 1.2, label=k)
        h, l = a.get_legend_handles_labels(); u = dict(zip(l, h)); a.legend(u.values(), u.keys(), loc="lower right", frameon=False, fontsize=9)
        a.set_xlim(-12, 90); a.set_ylim(440, 540); a.set_aspect("equal"); a.grid(color=GRID, lw=0.6)
        a.set_title(f"{lab.split('/')[-1]}   section x = {x:.0f} mm", color=INK, fontsize=11, loc="left")
        a.set_xlabel("y (mm, back to front)", color=INK2); a.set_ylabel("z (mm)", color=INK2)
        for sp in a.spines.values(): sp.set_color(GRID)
fig.tight_layout(); fig.savefig(out, dpi=130, facecolor=SURF); print(out)
