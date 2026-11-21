"""USAGE: tools/py.sh tools/rocker_top/fig_top.py OUTDIR
Figure for the rocker top edge (critique v24 #20) and the arm underside's inner edge (#17):
  a  each rocker's top edge in single photos (PR #29 ribbons, work/rbot/trace3.json) against that side's own traced top
     (parts/rocker_profile.json), after removing each photo's own shift + rotation over u -344..589: median and spread over photos
  b  the critique's top edge on each rocker, per photo, fitted as a line along y: its slope (pitch, mm per m)
  c  arm inner bottom arris, per photo and stretch, made pose-free against the same photo's outer top arris (tools/arm_underside/critique_inner.py)
Inputs: work/rbot/trace3.json, work/hub_rtop/pitch_v24.json (tools/rocker_top/pitch.py), work/hub_rtop/arminner_v24.json."""
import sys, json, numpy as np
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
out = sys.argv[1] if len(sys.argv) > 1 else "figures/rocker_top"
BLUE, ORANGE, INK, MUTE, GRID, SURF = "#2a78d6", "#eb6834", "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
plt.rcParams.update({"font.size": 10, "axes.edgecolor": MUTE, "axes.labelcolor": MUTE, "xtick.color": MUTE, "ytick.color": MUTE, "text.color": INK, "axes.spines.top": False, "axes.spines.right": False})
T = json.load(open("work/rbot/trace3.json")); PI = json.load(open("work/hub_rtop/pitch_v24.json")); AI = json.load(open("work/hub_rtop/arminner_v24.json"))
COL = {"L": BLUE, "R": ORANGE}; NAME = {"L": "left", "R": "right"}
fig = plt.figure(figsize=(13.5, 9.6), facecolor=SURF); gs = fig.add_gridspec(2, 2, height_ratios=[1, 1]); a = fig.add_subplot(gs[0, :]); b = fig.add_subplot(gs[1, 0]); c = fig.add_subplot(gs[1, 1])
for ax in (a, b, c): ax.set_facecolor(SURF); ax.grid(color=GRID, lw=0.6); ax.set_axisbelow(True)
# a: pose-free shape
edges = np.arange(-345, 600, 15.0)
for S in "LR":
    u = np.array(T[S]["u"]); R = []
    for ph, P in T[S]["photos"].items():
        t = np.array([np.nan if v is None else v for v in P["top_t"]], float); ok = np.array(P["top_ok"], bool) & np.isfinite(t)
        if ok.sum() < 300: continue
        cf = np.polyfit(u[ok], t[ok], 1); r = np.where(ok, t - np.polyval(cf, u), np.nan)
        R.append([np.nanmedian(r[(u >= e) & (u < e + 15)]) if np.isfinite(r[(u >= e) & (u < e + 15)]).sum() >= 5 else np.nan for e in edges])
    R = np.array(R); n = np.isfinite(R).sum(0); m = np.nanmedian(R, 0); q1, q3 = np.nanpercentile(R, 25, 0), np.nanpercentile(R, 75, 0); x = edges + 7.5; k = n >= 3
    a.fill_between(x[k], q1[k], q3[k], color=COL[S], alpha=0.15, lw=0); a.plot(x[k], m[k], color=COL[S], lw=2, label=f"{NAME[S]} rocker: median of {len(R)} photos (band: middle half)")
a.axhspan(-1.6, 1.6, color=GRID, alpha=0.6, zorder=0); a.axhline(0, color=MUTE, lw=0.8)
a.set_xlim(-360, 600); a.set_ylim(-3, 3); a.set_xlabel("u along the rocker on its own side plane, mm (front positive; the nose top corner is near u 590)"); a.set_ylabel("wood top minus own traced top, mm")
a.set_title("a  Each rocker's top edge in single photos, against its own traced profile, each photo's shift and rotation removed", loc="left", fontsize=12, color=INK)
a.text(-350, 2.55, "grey band: ±1.6 mm, the tolerance on a free curve. Each side's top keeps its own traced shape within 1.2 mm from tail to nose:\nthe −2 at the nose and +2 at the tail in the critique are the rocker's tilt in 3D, not its shape.", color=MUTE, va="top")
a.legend(loc="lower right", frameon=False)
# b: critique pitch per photo
for i, S in enumerate("LR"):
    for grp, mk in ((False, "o"), (True, "D")):
        v = [q["slope"] for q in PI[S] if q["held"] == grp]; y = i + (0.18 if grp else -0.12) + np.linspace(-0.06, 0.06, len(v))
        b.plot(v, y, mk, ms=6, color=COL[S], mfc=COL[S] if not grp else SURF, mew=1.4, label=("ranking photos" if not grp else "held-out photos") if S == "L" else None)
    allv = [q["slope"] for q in PI[S]]; b.plot([np.median(allv)] * 2, [i - 0.3, i + 0.3], color=INK, lw=2.2); b.text(np.median(allv), i + 0.36, f"median {np.median(allv):+.1f}", ha="center", color=INK)
b.axvline(0, color=MUTE, lw=0.8); b.set_yticks([0, 1]); b.set_yticklabels(["left", "right"]); b.set_ylim(-0.5, 1.6); b.set_xlim(-17, 11)
b.set_xlabel("pitch of the model's top edge against the wood, mm per m of length (− = model nose-down)"); b.legend(loc="lower left", frameon=False, fontsize=9)
b.set_title("b  The critique's rocker top, one line per photo", loc="left", fontsize=12, color=INK)
b.text(-16.5, 1.55, "left −3.8 mm/m over the 1.1 m rocker = about ±2 mm at the ends.\nPhoto to photo the tilt scatters 3-4 mm/m; the left rocker's\nranking photos mostly look across from the right side.", color=MUTE, va="top", fontsize=9)
# c: arm inner drop
bins = [(50, 100), (100, 200), (200, 300), (300, 400), (400, 450)]
for S, dx in (("L", -6), ("R", 6)):
    for j, (y0, y1) in enumerate(bins):
        for grp, mk in ((False, "o"), (True, "D")):
            v = [q["err"] for q in AI if q["side"] == S and q["y"] == [y0, y1] and q["held"] == grp and q["err"] is not None]
            c.plot([(y0 + y1) / 2 + dx] * len(v), v, mk, ms=4.5, color=COL[S], mfc=COL[S] if not grp else SURF, mew=1.2, alpha=0.75)
        v = [q["err"] for q in AI if q["side"] == S and q["y"] == [y0, y1] and q["err"] is not None]
        if v: c.plot([(y0 + y1) / 2 + dx - 9, (y0 + y1) / 2 + dx + 9], [np.median(v)] * 2, color=COL[S], lw=3)
c.axhline(0, color=MUTE, lw=0.8); c.set_ylim(-7, 7); c.set_xlim(40, 460)
c.set_xlabel("y along the arm, mm"); c.set_ylabel("model's inner drop minus the wood's, mm (+ = model too deep)")
c.set_title("c  Arm underside, inner edge, per photo (pose-free)", loc="left", fontsize=12, color=INK)
c.text(48, 6.6, "dots: one photo (open = held-out); bars: median.\nleft (blue) reads −0.6, right (orange) +0.8 over all stretches;\n1.6-2.3 px/mm, spread 1-2.5 mm per stretch.", color=MUTE, va="top", fontsize=9)
fig.tight_layout(); fig.savefig(f"{out}/top_and_arm.png", dpi=110, facecolor=SURF); print("wrote", f"{out}/top_and_arm.png")
