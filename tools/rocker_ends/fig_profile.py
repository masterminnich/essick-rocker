"""USAGE: tools/py.sh tools/rocker_ends/fig_profile.py [OUT figures/rocker_ends/profile.png]
Drawing of the two rocker ends from parts/rocker_ends.json, in the frame of parts/rocker_profile.json (left side plane, the right rocker carried onto the left):
  top    - the tail: the model before (ends cut square), the left and right rockers as traced (each set on the profile), the design (their average)
  left   - the nose, the same four outlines
  right  - face height (top edge to bottom edge, straight up) along the tail: old profile, left, right, design"""
import sys, json, numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
out = sys.argv[1] if len(sys.argv) > 1 else "figures/rocker_ends/profile.png"; E = json.load(open("parts/rocker_ends.json")); RP = json.load(open("parts/rocker_profile.json")); U = np.array(RP["u"]); D, A = E["design"], E["as_averaged"]
BLUE, ORANGE, INK, MUTE, GRID, SURF = "#2a78d6", "#eb6834", "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
plt.rcParams.update({"font.size": 10, "axes.edgecolor": MUTE, "axes.labelcolor": MUTE, "xtick.color": MUTE, "ytick.color": MUTE, "text.color": INK, "axes.spines.top": False, "axes.spines.right": False})
fig = plt.figure(figsize=(13.5, 10.4), facecolor=SURF); gs = fig.add_gridspec(2, 2, height_ratios=[1, 1.45], width_ratios=[1, 1.05]); a = fig.add_subplot(gs[0, :]); b = fig.add_subplot(gs[1, 0]); c = fig.add_subplot(gs[1, 1])
for ax in (a, b, c): ax.set_facecolor(SURF); ax.grid(color=GRID, lw=0.6); ax.set_axisbelow(True)
old = np.r_[np.c_[U, RP["mean_top"]], np.c_[U, RP["mean_bot"]][::-1], [[U[0], RP["mean_top"][0]]]]
def draw(ax, end, lab):
    ax.plot(old[:, 0], old[:, 1], color=MUTE, lw=1.4, ls=(0, (5, 3)), label="model before (v17): ends cut square" if lab else None, zorder=2)
    for side, col in (("left", BLUE), ("right", ORANGE)):
        T_, B_ = (np.array(A[end][side][k]) for k in ("top", "bot")); sg = -1 if end == "tail" else 1; T_, B_ = (q[np.argmax(sg * q[:, 0] >= sg * D[end]["blend_u"][0]):] for q in (T_, B_))      # from where the design starts to use them
        P = np.r_[T_, B_[::-1]]; ax.plot(P[:, 0], P[:, 1], color=col, lw=1.3, label=f"{side} rocker as traced" + (" (carried onto the left)" if side == "right" else "") if lab else None, zorder=3)
    P = np.r_[np.array(D[end]["top"]), np.array(D[end]["bot"])[::-1]]; ax.plot(P[:, 0], P[:, 1], color=INK, lw=2.2, label="design (v18): left and right averaged" if lab else None, zorder=4)
    for (u, v), col in zip(D[end]["landmark_left_right_uv"], (BLUE, ORANGE)): ax.plot([u], [v], "o", ms=6, color=col, mec=SURF, mew=1.5, zorder=5)
    ax.plot(*D[end]["landmark_uv"], "o", ms=7, color=INK, mec=SURF, mew=1.5, zorder=6); ax.set_aspect("equal"); ax.set_xlabel("u along the rocker, mm (front positive)"); ax.set_ylabel("v up, mm")
draw(a, "tail", True); a.set_xlim(-502, -296); a.set_ylim(108, 190); a.legend(loc="lower left", frameon=False, ncol=2)
lt, rt = D["tail"]["landmark_left_right_uv"]; dt = D["tail"]["landmark_uv"]; b0, b1 = D["tail"]["blend_u"]
a.set_title("Tail: thins to a slim rounded tip", loc="left", fontsize=12, color=INK)
a.annotate(f"tip, design: u {dt[0]:.1f}\nleft {lt[0]:.1f}, right {rt[0]:.1f}\n(right ends {rt[0] - lt[0]:.1f} mm short of left)", dt, (-500, 131), color=INK, va="center", ha="left", arrowprops=dict(arrowstyle="-", color=MUTE, lw=0.8))
a.axvspan(b1, b0, color=GRID, alpha=0.55, zorder=0); a.text((b0 + b1) / 2, 186.5, "old profile blends into the traced end", ha="center", va="center", color=MUTE)
a.text(-466, 150, "the old end:\nsquare at u -480,\nface 20 mm high", color=MUTE, va="center", ha="left")
draw(b, "nose", False); b.set_xlim(562, 640); b.set_ylim(64, 136); ln, rn = D["nose"]["landmark_left_right_uv"]; dn = D["nose"]["landmark_uv"]; ext = max(np.array(D["nose"]["bot"])[:, 0])
b.set_title("Nose: a round end, proud of the top corner", loc="left", fontsize=12, color=INK)
b.annotate(f"top corner, design: u {dn[0]:.1f}\nleft {ln[0]:.1f}, right {rn[0]:.1f}", dn, (dn[0] - 30, dn[1] + 4), color=INK, va="bottom", ha="left", arrowprops=dict(arrowstyle="-", color=MUTE, lw=0.8))
b.annotate(f"end reaches u {ext:.1f}", (ext, np.array(D["nose"]["bot"])[np.argmax(np.array(D["nose"]["bot"])[:, 0]), 1]), (586, 97), color=INK, va="center", ha="left", arrowprops=dict(arrowstyle="-", color=MUTE, lw=0.8))
b.text(619, 75, "the old end:\nsquare at u 620", color=MUTE, va="center", ha="right")
def height(top, bot, us):
    top, bot = np.array(top), np.array(bot); jt = int(np.argmax(np.diff(-top[:, 0]) <= 0)) or len(top) - 1; jb = int(np.argmax(np.diff(-bot[:, 0]) <= 0)) or len(bot) - 1
    ok = (us >= max(top[jt - 1, 0], bot[jb - 1, 0])) & (us <= min(top[0, 0], bot[0, 0])); return us[ok], np.interp(-us[ok], -top[:jt, 0], top[:jt, 1]) - np.interp(-us[ok], -bot[:jb, 0], bot[:jb, 1])
us = np.arange(-485.0, -315.9, 1.0); uo = us[us >= -480]; c.plot(uo, np.interp(uo, U, RP["mean_top"]) - np.interp(uo, U, RP["mean_bot"]), color=MUTE, lw=1.4, ls=(0, (5, 3)))
for side, col in (("left", BLUE), ("right", ORANGE)): x, h = height(A["tail"][side]["top"], A["tail"][side]["bot"], us); c.plot(x, h, color=col, lw=1.3); c.text(x[-1] + 2, h[-1] + (0.7 if side == "left" else -0.7), side, color=INK, ha="left", va="center")
x, h = height(D["tail"]["top"], D["tail"]["bot"], np.arange(-485.0, b0 + 0.1, 1.0)); c.plot(x, h, color=INK, lw=2.2); c.axvspan(b1, b0, color=GRID, alpha=0.55, zorder=0)
c.text(-476, 21.6, "model before", color=MUTE, ha="left", va="bottom"); c.text(-436, 17.5, "design", color=INK, ha="left", va="center"); c.set_xlim(-502, -298); c.set_ylim(0, 30)
c.set_title("Tail: height of the side face", loc="left", fontsize=12, color=INK); c.set_xlabel("u along the rocker, mm"); c.set_ylabel("top edge to bottom edge, mm")
hl, hr = (dict(zip(*height(A["tail"][s_]["top"], A["tail"][s_]["bot"], np.array([-320.0]))))[-320.0] for s_ in ("left", "right")); ho = float(np.interp(-320, U, RP["mean_top"]) - np.interp(-320, U, RP["mean_bot"]))
c.annotate(f"at u -320 the traced face is {hl:.1f} (left) and {hr:.1f} (right);\nthe old profile says {ho:.1f} (a fitted height): open,\nsee 'rocker bottom edge traced directly'", (-320, (hl + hr) / 2), (-412, 9.0), color=INK, va="center", ha="left", arrowprops=dict(arrowstyle="-", color=MUTE, lw=0.8))
fig.suptitle("Rocker ends as traced in the photos (parts/rocker_ends.json), against the square-cut ends of model v17", x=0.012, ha="left", fontsize=13.5, color=INK)
fig.tight_layout(rect=(0, 0, 1, 0.97)); fig.savefig(out, dpi=150, facecolor=SURF); print("wrote", out)
