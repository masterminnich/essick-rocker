"""USAGE: tools/py.sh tools/seat_scoop/fig_section.py [OUT figures/seat_scoop/section.png]
Two drawings of the seat's side edge from parts/seat_scoop.json (right side, as measured):
  left  - the cross-section at station y 250, looking forward: old straight wall against the measured edge face, hard line and under-bevel
  right - the height of the hard line above the underside along the edge (the lens), with the straight continuation to the two tips"""
import sys, json, numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
out = sys.argv[1] if len(sys.argv) > 1 else "figures/seat_scoop/section.png"
S = json.load(open("parts/seat_scoop.json")); E = json.load(open("parts/seat_edge.json"))["right"]
ip = lambda A, y, i: (lambda A: float(np.interp(y, A[:, 1], A[:, i])))(np.array(sorted(A, key=lambda p: p[1])))
C, B = S["right"]["hard_line_xyz"], S["right"]["bottom_arris_xyz"]; Tp, Ts, Bo = E["top_arris_plan_xyz"], E["top_arris_side_xyz"], E["bottom_arris_xyz"]
BLUE, ORANGE, INK, MUTE, GRID, SURF = "#2a78d6", "#eb6834", "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
plt.rcParams.update({"font.size": 10, "axes.edgecolor": MUTE, "axes.labelcolor": MUTE, "xtick.color": MUTE, "ytick.color": MUTE, "text.color": INK, "axes.spines.top": False, "axes.spines.right": False})
fig, (a, b) = plt.subplots(1, 2, figsize=(13, 5.6), facecolor=SURF, gridspec_kw={"width_ratios": [1, 1.25]})
for ax in (a, b): ax.set_facecolor(SURF); ax.grid(color=GRID, lw=0.6); ax.set_axisbelow(True)
# --- left: section at y 250
y = 250.0; t = np.array([ip(Tp, y, 0), ip(Tp, y, 2)]); h = np.array([ip(C, y, 0), ip(C, y, 2)]); bt = np.array([ip(B, y, 0), ip(B, y, 2)])
to, bo = np.array([ip(Ts, y, 0), ip(Ts, y, 2)]), np.array([ip(Bo, y, 0), ip(Bo, y, 2)])
ang = S["design"]["bevel_angle_deg"]["value"]; und = bt + np.array([-22.0, 0.0])     # the underside is level across within this drawing (flat across: reflection evidence only)
a.plot([to[0], bo[0]], [to[1], bo[1]], color=MUTE, lw=1.6, ls=(0, (5, 3)), label="model v15: one straight wall")
a.plot([t[0] - 22, t[0], h[0], bt[0], und[0]], [t[1], t[1], h[1], bt[1], und[1]], color=BLUE, lw=2, label="measured, right side", solid_joinstyle="round")
for p, lab, dx, dy, ha in ((t, "top arris (eased)", 2.5, 1.0, "left"), (h, "hard line", 2.5, -0.5, "left"), (bt, "bottom arris", -1.0, -4.2, "center")):
    a.plot(*p, "o", ms=8, color=BLUE, mec=SURF, mew=2); a.annotate(lab, p, (p[0] + dx, p[1] + dy), ha=ha, va="center", color=INK)
_u, _v = bo - to, h - to; gap = float((_u[0] * _v[1] - _u[1] * _v[0]) / np.linalg.norm(_u))
foot = to + (bo - to) * float(np.dot(h - to, bo - to) / np.dot(bo - to, bo - to))
a.annotate("", h, foot, arrowprops=dict(arrowstyle="<->", color=ORANGE, lw=1.4))
a.text(foot[0] - 2.5, foot[1] + 1.0, f"{abs(gap):.1f} mm of wood\nmissing in v15", ha="right", va="bottom", color=INK)
a.text(h[0] + 2.5, (t[1] + h[1]) / 2, f"edge face\nvertical, {t[1] - h[1]:.0f} mm", va="center", color=MUTE); a.text((h[0] + bt[0]) / 2 + 4.5, (h[1] + bt[1]) / 2 - 3.5, f"under-bevel\n{ang:.1f}°, {h[1] - bt[1]:.0f} mm high", va="center", color=MUTE)
a.text(und[0] + 1, und[1] - 2.4, "underside", color=MUTE, va="top"); a.text(t[0] - 21, t[1] - 1.6, "seat top", color=MUTE, va="top")
a.set_aspect("equal"); a.set_xlim(bt[0] - 36, t[0] + 26); a.set_ylim(bt[1] - 9, t[1] + 9); a.set_xlabel("x, mm from the centre line (outboard to the right)"); a.set_ylabel("height z, mm")
a.set_title("Section of the right side edge at station y 250, looking forward", loc="left", fontsize=11, color=INK); a.legend(loc="upper left", frameon=False, fontsize=9)
# --- right: the lens
H = np.array(S["right"]["height_of_hard_line_above_underside_mm"]); D = S["design"]["hard_line_height_above_underside_of_y"]; dy, dh = np.array(D["y"]), np.array(D["height_mm"]); y0, y1 = H[0, 0], H[-1, 0]
b.plot(dy[dy <= y0], dh[dy <= y0], color=BLUE, lw=2, ls=(0, (2, 2))); b.plot(dy[dy >= y1], dh[dy >= y1], color=BLUE, lw=2, ls=(0, (2, 2)), label="straight continuation to the tips (fitted)")
b.plot(H[:, 0], H[:, 1], color=BLUE, lw=2, label=f"measured, right side, y {y0:.0f} to {y1:.0f} (14 photos)")
i = int(H[:, 1].argmax()); b.plot(H[i, 0], H[i, 1], "o", ms=8, color=BLUE, mec=SURF, mew=2); b.annotate(f"{H[i, 1]:.1f} mm at y {H[i, 0]:.0f}", (H[i, 0], H[i, 1]), (H[i, 0], H[i, 1] + 1.6), ha="center")
for yt, lab, ha in ((dy[0], f"back tip\ny {dy[0]:.0f}", "right"), (dy[-1], f"front tip\ny {dy[-1]:.0f}", "left")):
    b.plot(yt, 0, "o", ms=8, color=BLUE, mec=SURF, mew=2); b.annotate(lab, (yt, 0), (yt + (6 if ha == "left" else -6), 0.3), ha=ha, va="bottom", color=INK)
b.set_xlim(30, 510); b.set_ylim(-0.8, 29); b.set_xlabel("station y, mm (back leg on the left, front leg on the right)"); b.set_ylabel("height of the hard line above the underside, mm")
b.set_title("The under-bevel is a lens: deepest at mid-length, nothing at the legs", loc="left", fontsize=11, color=INK); b.legend(loc="lower center", frameon=False, fontsize=9, bbox_to_anchor=(0.5, 0.12))
fig.tight_layout(); fig.savefig(out, dpi=140, facecolor=SURF); print("wrote", out, "gap at y 250: %.2f mm; face %.1f mm; bevel height %.1f mm" % (abs(gap), t[1] - h[1], h[1] - bt[1]))
