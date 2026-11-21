"""USAGE: tools/py.sh tools/seat_side_ends/fig_ends.py MODEL_OUTLINE.json OUT.png [MODEL_LABEL "model v22"]
Chart: the seat's plan outline (top-arris half-width) measured minus the model, at the two ends of the side edge, toward the back leg and
toward the front leg. Blue = left/right mean minus the model with the leave-one-photo-out band; thin lines = each side on its own, shifted
by its own offset at the end of the old design range (y 110 / 400), i.e. its SHAPE against the model's (the chair leans 3-4 mm L/R).
Grey band = the free-curve tolerance (1.6 mm). The model beyond y 110 / 400 was extrapolated; inside, it is parts/seat_edge.json's design."""
import sys, json, glob, numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
mo_f, out = sys.argv[1:3]; lab = sys.argv[3] if len(sys.argv) > 3 else "model v22"
BLUE, ORANGE, INK, MUTE, GRID, SURF = "#2a78d6", "#eb6834", "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
plt.rcParams.update({"font.size": 10, "axes.edgecolor": MUTE, "axes.labelcolor": MUTE, "xtick.color": MUTE, "ytick.color": MUTE, "text.color": INK, "axes.spines.top": False, "axes.spines.right": False})
mo = json.load(open(mo_f)); my = np.array([r["y"] for r in mo]); model = lambda y: np.interp(y, my, (np.array([r["xR"] for r in mo]) - np.array([r["xL"] for r in mo])) / 2)
line = lambda f, s: (lambda P: P[np.argsort(P[:, 1])])(np.array(json.load(open(f))[f"seat{s}_plan_xyz"]))
hw = lambda P, y: np.interp(y, P[:, 1], np.abs(P[:, 0]), left=np.nan, right=np.nan)
fig, axs = plt.subplots(1, 2, figsize=(13, 4.8), facecolor=SURF, gridspec_kw={"width_ratios": [1, 1.2]})
for ax, (y0, y1, yref, title) in zip(axs, ((80, 140, 110.0, "Toward the back leg"), (370, 440, 400.0, "Toward the front leg"))):
    ax.set_facecolor(SURF); ax.grid(color=GRID, lw=0.6); ax.set_axisbelow(True); ys = np.arange(y0, y1 + 0.1, 1.0)
    ax.axhspan(-1.6, 1.6, color=GRID, alpha=0.55, lw=0); ax.axhline(0, color=MUTE, lw=0.8)
    H = {}; SE = {}
    for s in "RL":
        H[s] = hw(line(f"work/seatside/{s}_ext.json", s), ys)
        J = np.array([hw(line(f, s), ys) for f in sorted(glob.glob(f"work/seatside/jk/{s}_*.json")) if not f.endswith("_dump.json")]); n = len(J)
        SE[s] = np.sqrt((n - 1) / n * np.nansum((J - np.nanmean(J, 0)) ** 2, 0))
    m = (H["R"] + H["L"]) / 2 - model(ys); se = 0.5 * np.hypot(SE["R"], SE["L"])
    ax.fill_between(ys, m - se, m + se, color=BLUE, alpha=0.18, lw=0); ax.plot(ys, m, color=BLUE, lw=2.2, label="left/right mean minus %s" % lab)
    mref = model(yref)
    for s, ls, nm in (("R", "-", "right"), ("L", (0, (4, 2)), "left")):
        r = H[s] - np.interp(yref, ys, H[s]) - (model(ys) - mref); ax.plot(ys, r, color=MUTE, lw=1.1, ls=ls, label=f"{nm} side alone, own offset at y {yref:.0f} removed")
    ext = (ys < 110) if yref == 110 else (ys > 400)
    ax.axvspan(ys[ext][0], ys[ext][-1], color=ORANGE, alpha=0.07, lw=0)
    ax.text(ys[ext].mean(), 2.05, "extrapolated in the model\n(now traced)", ha="center", va="bottom", color=ORANGE, fontsize=9)
    leg_y = 78.0 if yref == 110 else 446.0   # the model legs' faces at the top arris's height (v22 sections: BLEG_R y 77.5 at z 350, FLEG_R y 445.8 at z 410)
    ax.axvline(leg_y, color=INK, lw=1.0); ax.text(leg_y + (1 if yref == 110 else -1), -2.35, "back leg face (model)" if yref == 110 else "front leg face (model)", ha="left" if yref == 110 else "right", color=INK, fontsize=9)
    ax.text(ys[0] + 1 if yref == 400 else ys[-1] - 1, 1.45, "±1.6 mm tolerance", ha="left" if yref == 400 else "right", va="top", color=MUTE, fontsize=9)
    ax.set_xlim(y0 - 4, y1 + 8); ax.set_ylim(-2.6, 2.9); ax.set_xlabel("y, mm (forward to the right)"); ax.set_title(title, loc="left", fontsize=11, color=INK)
axs[0].set_ylabel("half-width, measured minus model, mm"); axs[1].legend(loc="lower left", frameon=False, fontsize=9)
fig.suptitle("Seat side edge in plan at its two ends: the model's extrapolation sits on the wood (within 0.5 mm)", x=0.01, ha="left", fontsize=12, color=INK)
fig.tight_layout(); fig.savefig(out, dpi=130, facecolor=SURF); print(out)
