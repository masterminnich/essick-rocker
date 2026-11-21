"""USAGE: tools/py.sh tools/seat_back/fig_section.py OLD_shapes.glb NEW_shapes.glb [OUT figures/seat_back/section.png] [OLD_LABEL "model v16"]
Three drawings of the seat's back edge from parts/seat_back.json against the old model:
  top    - plan view: the three measured edges (top arris, hard line, bottom arris) between the back legs against the old straight edge
  left   - section on the centre line, looking toward the chair's left: old and new seat outline, and the sparse cloud's points near the centre line
  right  - the lens: height of the hard line above the bottom arris across the chair (design = symmetric; left and right halves as solved on their own)"""
import sys, json, numpy as np, trimesh
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
old, new = sys.argv[1:3]; out = sys.argv[3] if len(sys.argv) > 3 else "figures/seat_back/section.png"; old_lab = sys.argv[4] if len(sys.argv) > 4 else "model v16"
J = json.load(open("parts/seat_back.json")); D = J["design"]; ax_ = np.array(D["abs_x"]); xs = ax_; sym = lambda v: np.array(v)
BLUE, ORANGE, INK, MUTE, GRID, SURF = "#2a78d6", "#eb6834", "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
plt.rcParams.update({"font.size": 10, "axes.edgecolor": MUTE, "axes.labelcolor": MUTE, "xtick.color": MUTE, "ytick.color": MUTE, "text.color": INK, "axes.spines.top": False, "axes.spines.right": False})
fig = plt.figure(figsize=(13.5, 11.6), facecolor=SURF); gs = fig.add_gridspec(2, 2, height_ratios=[1, 1.22], width_ratios=[1.15, 1]); a = fig.add_subplot(gs[0, :]); b = fig.add_subplot(gs[1, 0]); c = fig.add_subplot(gs[1, 1])
for ax in (a, b, c): ax.set_facecolor(SURF); ax.grid(color=GRID, lw=0.6); ax.set_axisbelow(True)
So, Sn = (trimesh.load(f).geometry["SEAT"] for f in (old, new)); Lg = trimesh.load(new).geometry["BLEG_R"]
def zz(S, x, y):
    T = S.triangles; p, q, r = T[:, 0], T[:, 1], T[:, 2]; d = (q[:, 1] - r[:, 1]) * (p[:, 0] - r[:, 0]) + (r[:, 0] - q[:, 0]) * (p[:, 1] - r[:, 1]); d = np.where(np.abs(d) < 1e-9, np.nan, d)
    l1 = ((q[:, 1] - r[:, 1]) * (x - r[:, 0]) + (r[:, 0] - q[:, 0]) * (y - r[:, 1])) / d; l2 = ((r[:, 1] - p[:, 1]) * (x - r[:, 0]) + (p[:, 0] - r[:, 0]) * (y - r[:, 1])) / d
    l3 = 1 - l1 - l2; k = (l1 >= -1e-9) & (l2 >= -1e-9) & (l3 >= -1e-9); z = l1[k] * p[k, 2] + l2[k] * q[k, 2] + l3[k] * r[k, 2]; return (z.max(), z.min()) if k.any() else (np.nan, np.nan)
# --- top: plan
yo = float(So.vertices[:, 1].min()); xo = float(np.abs(So.vertices[np.abs(So.vertices[:, 1] - yo) < 0.5][:, 0]).max()); sec = Lg.section(plane_origin=[0, 0, 335.0], plane_normal=[0, 0, 1]).vertices
for s in (1,):
    lx0, lx1, ly0, ly1 = sec[:, 0].min(), sec[:, 0].max(), sec[:, 1].min(), sec[:, 1].max(); a.fill([s * lx0, s * lx1, s * lx1, s * lx0], [ly0, ly0, ly1, ly1], color=GRID, zorder=1)
    a.text(s * (lx0 + lx1) / 2, 62, "back leg", ha="center", va="center", color=MUTE)
a.plot([0, xo], [yo, yo], color=MUTE, lw=1.6, ls=(0, (5, 3)), label=f"{old_lab}: one straight edge at y {yo:.1f}", zorder=3)
a.plot(xs, sym(D["bottom_arris"]["y"]), color=BLUE, lw=1.2, zorder=3); a.plot(xs, sym(D["hard_line"]["y"]), color=BLUE, lw=1.2, zorder=3); a.plot(xs, sym(D["top_arris"]["y"]), color=BLUE, lw=2.2, label="measured: the three edges of the back edge (symmetric solves)", zorder=4)
yT0, yH0, yB0 = D["top_arris"]["y"][0], D["hard_line"]["y"][0], D["bottom_arris"]["y"][0]
a.text(70, np.interp(70, ax_, D["top_arris"]["y"]) - 3.4, "top arris", ha="center", va="center", color=INK); a.text(70, np.interp(70, ax_, D["bottom_arris"]["y"]) + 3.2, "bottom arris (under the seat)", ha="center", va="center", color=INK)
a.text(70, np.interp(70, ax_, D["hard_line"]["y"]) + 3.0, "hard line", ha="center", va="center", color=INK)
a.annotate("", (8, np.interp(8, ax_, D["top_arris"]["y"])), (8, yo), arrowprops=dict(arrowstyle="<->", color=ORANGE, lw=1.4, shrinkA=0, shrinkB=0)); a.text(11, yo - 4.4, f"{yo - yT0:.1f} mm", va="center", color=INK)
a.set_aspect("equal"); a.set_xlim(0, 240); a.set_ylim(72, -14); a.set_xlabel("x, mm from the centre line (right half shown, the left is its mirror; seen from above, the chair's back at the top)"); a.set_ylabel("y, mm (forward is down)")
a.set_title("Plan: the back edge is a bow between the legs, not a straight line", loc="left", fontsize=11, color=INK); a.legend(loc="lower left", frameon=False, fontsize=9, bbox_to_anchor=(0.02, 0.04))
# --- left: section on the centre line
yy = np.arange(-6.0, 112.0, 1.0); x0 = 0.31
def prof(S):
    Z = np.array([zz(S, x0, y + 0.017) for y in yy]); k = np.isfinite(Z[:, 0]); return np.r_[np.c_[yy[k], Z[k, 0]], np.c_[yy[k], Z[k, 1]][::-1], [[yy[k][0], Z[k][0, 0]]]]
Po, Pn = prof(So), prof(Sn); b.plot(Po[:, 0], Po[:, 1], color=MUTE, lw=1.6, ls=(0, (5, 3)), label=old_lab); b.plot(Pn[:, 0], Pn[:, 1], color=BLUE, lw=2, label="new model = measured edge", solid_joinstyle="round")
C = np.load("work/dense/chair_dense.npy")[:, :3]; k = (np.abs(C[:, 0]) < 30) & (C[:, 1] > -8) & (C[:, 1] < 34) & (C[:, 2] > 318) & (C[:, 2] < 336); b.plot(C[k, 1], C[k, 2], "o", ms=4, color=INK, alpha=0.55, mec="none", label="sparse cloud points within 30 mm of the centre line")
T, H, B = (np.array([D[e]["y"][0], D[e]["z"][0]]) for e in ("top_arris", "hard_line", "bottom_arris"))
for p, lab, dx, dy, ha in ((T, "top arris", -2.5, 1.5, "right"), (H, "hard line", -2.5, 0, "right"), (B, "bottom arris", 2.0, -3.2, "left")):
    b.plot(*p, "o", ms=8, color=BLUE, mec=SURF, mew=2); b.annotate(lab, p, (p[0] + dx, p[1] + dy), ha=ha, va="center", color=INK)
S_ = J["section"]; b.text(14.0, (T[1] + H[1]) / 2 - 1, "back face\nleans %.0f°" % np.degrees(np.arctan2(H[0] - T[0], T[1] - H[1])), va="center", color=MUTE); b.text((H[0] + B[0]) / 2 + 6, (H[1] + B[1]) / 2 + 2.5, "under-bevel\n%.0f°" % np.degrees(np.arctan2(H[1] - B[1], B[0] - H[0])), va="center", color=MUTE)
b.text(86, zz(Sn, x0, 86.0)[0] + 2.2, "seat top", color=MUTE, ha="center"); b.text(86, zz(Sn, x0, 86.0)[1] - 2.2, "underside", color=MUTE, ha="center", va="top")
b.axvline(63.6, color=GRID, lw=1.2); b.text(64.6, 364, "tape dots on the\nseat top start here", color=MUTE, va="top", fontsize=9)
b.set_aspect("equal"); b.set_xlim(-22, 112); b.set_ylim(280, 368); b.set_xlabel("y, mm (the chair's back on the left)"); b.set_ylabel("height z, mm")
b.set_title("Section on the centre line:\nthe old top climbed toward the back, the real one falls to the arris", loc="left", fontsize=11, color=INK); b.legend(loc="upper left", frameon=False, fontsize=9, bbox_to_anchor=(0.0, 1.0))
# --- right: the lens
M = J["measured"]; Hf, Bf = np.array(M["hard"]["free_xyz"]), np.array(M["bottom"]["free_xyz"]); xh = np.arange(0.0, 165.0 + 1e-9, 2.5); tip = D["lens_tip_abs_x"]
for s, lab, ls in ((-1, "left half", (0, (1, 2))), (1, "right half", (0, (6, 2)))):
    h = np.interp(s * xh, Hf[:, 0], Hf[:, 2]) - np.interp(s * xh, Bf[:, 0], Bf[:, 2]); c.plot(xh, h, color=MUTE, lw=1.3, ls=ls, label=f"{lab}, solved on its own")
hd = np.array(D["hard_line"]["z"]) - np.array(D["bottom_arris"]["z"]); m = ax_ <= 165; c.plot(ax_[m], hd[m], color=BLUE, lw=2.2, label="design (symmetric solve), measured to |x| 165")
c.plot([165, tip], [np.interp(165, ax_, hd), 0], color=BLUE, lw=2.2, ls=(0, (2, 2)), label="straight continuation to the tip (fitted)")
c.plot(0, hd[0], "o", ms=8, color=BLUE, mec=SURF, mew=2); c.annotate(f"{hd[0]:.1f} mm on the centre line", (0, hd[0]), (6, hd[0] + 1.0), va="bottom"); c.plot(tip, 0, "o", ms=8, color=BLUE, mec=SURF, mew=2); c.annotate(f"tip\n|x| {tip:.0f}", (tip, 0), (tip + 2.5, 0.5), ha="left", va="bottom")
c.axvline(188.0, color=GRID, lw=1.2); c.text(189.5, 19.0, "leg's inner face", color=MUTE, ha="left", va="top", fontsize=9, rotation=90)
c.set_xlim(0, 199); c.set_ylim(-0.6, 19.5); c.set_xlabel("|x|, mm from the centre line"); c.set_ylabel("height of the hard line above the bottom arris, mm")
c.set_title("The under-bevel is a lens:\ndeepest on the centre line, nothing at the legs", loc="left", fontsize=11, color=INK); c.legend(loc="lower left", frameon=False, fontsize=9)
fig.tight_layout(); fig.savefig(out, dpi=140, facecolor=SURF)
print("wrote", out, "| old edge y %.1f half-width %.1f; bow at centre %.1f mm behind the old edge; old top at (0, %.0f): %.1f, new %.1f" % (yo, xo, yo - yT0, yo + 3, zz(So, x0, yo + 3)[0], zz(Sn, x0, yo + 3)[0]), "| cloud points drawn:", int(k.sum()))
