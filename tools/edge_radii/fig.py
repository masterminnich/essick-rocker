"""USAGE: tools/py.sh tools/edge_radii/fig.py [RESULTS work/edge_radii/results.json] [OUTDIR figures/edge_radii]
Figures for phase 6c from run_all.py's results and parts/edge_radii.json:
  bands.png    - each tone-band measurement: a zoomed crop of its single photo with the silhouette (orange) and the B10 line
                 (blue) marked across the edge, and the L* profile with the same two lines
  corners.png  - the corner fits (cornerfit.py overlays): rocker nose end, rocker tail tip in plan
  radii.png    - radius by edge family (parts/edge_radii.json): measured brackets, bounds, assumed and unmeasured"""
import sys, json, numpy as np, cv2
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
R = json.load(open(sys.argv[1] if len(sys.argv) > 1 else "work/edge_radii/results.json"))
OUT = sys.argv[2] if len(sys.argv) > 2 else "figures/edge_radii"
BLUE, ORANGE, INK, MUTE, GRID, SURF = "#2a78d6", "#eb6834", "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
plt.rcParams.update({"font.size": 9, "axes.edgecolor": MUTE, "axes.labelcolor": MUTE, "xtick.color": MUTE, "ytick.color": MUTE,
                     "text.color": INK, "axes.spines.top": False, "axes.spines.right": False})

# ---- bands
B = R["bands"]
fig, axs = plt.subplots(len(B), 2, figsize=(10, 3.4 * len(B)), facecolor=SURF, gridspec_kw=dict(width_ratios=[1, 1.4]))
for (a1, a2), b in zip(axs, B):
    P = json.load(open(f"work/edge_radii/run/{b['id']}.json"))
    p0, p1 = np.array(b["line"][:2], float), np.array(b["line"][2:], float); n = np.array(P["normal"])
    m = (p0 + p1) / 2; e = (p1 - p0) / np.linalg.norm(p1 - p0)
    H = 70; im = cv2.imread(f"drive/IMG_{b['img']}.JPG")
    x0, y0 = int(m[0] - H), int(m[1] - H); crop = cv2.cvtColor(im[y0:y0 + 2 * H, x0:x0 + 2 * H], cv2.COLOR_BGR2RGB)
    a1.imshow(crop, extent=(x0, x0 + 2 * H, y0 + 2 * H, y0)); a1.set_xticks([]); a1.set_yticks([])
    for t, col in ((b["silhouette_t"], ORANGE), (b["t10"], BLUE)):
        q0, q1 = m - e * H * 1.5 + n * t, m + e * H * 1.5 + n * t
        a1.plot([q0[0], q1[0]], [q0[1], q1[1]], color=col, lw=1.2)
    a1.set_xlim(x0, x0 + 2 * H); a1.set_ylim(y0 + 2 * H, y0)
    a1.set_title(f"IMG_{b['img']}  {b['family']}\n{b['pxmm']} px/mm; crop {2 * H} px = {2 * H / b['pxmm']:.1f} mm", fontsize=8.5, loc="left")
    t = np.array(P["t"]) / b["pxmm"]; L = np.array(P["L"]) * 100 / 255
    a2.set_facecolor(SURF); a2.grid(color=GRID, lw=0.6); a2.set_axisbelow(True)
    a2.plot(t, L, color=INK, lw=1.3)
    a2.axvline(b["silhouette_t"] / b["pxmm"], color=ORANGE, lw=1.2, label="silhouette (steepest step)")
    a2.axvline(b["t10"] / b["pxmm"], color=BLUE, lw=1.2, label="band ends (10 % of its extreme)")
    a2.axhline(b["plateau_L"] * 100 / 255, color=MUTE, lw=0.8, ls=(0, (4, 3)), label="flat face")
    a2.set_xlabel("across the edge (mm)"); a2.set_ylabel("lightness L*")
    a2.set_title(f"B10 {b['B10_mm']} mm, B50 {b['B50_mm']} mm, blur {b['step_fwhm_mm']} mm ({b['kind']})\nby eye: " + "\n".join(__import__("textwrap").wrap(b["by_eye"], 78)),
                 fontsize=8.5, loc="left")
    a2.legend(fontsize=7, frameon=False, loc="best")
fig.tight_layout(); fig.savefig(f"{OUT}/bands.png", dpi=110, facecolor=SURF); plt.close(fig)

# ---- corners
C = [c for c in R["corners"] if c["id"] in ("rocker_nose_top_outer", "rocker_tail_plan_ur", "rocker_tail_plan_ll")]
fig, axs = plt.subplots(1, len(C), figsize=(5.0 * len(C), 5.2), facecolor=SURF)
for ax, c in zip(axs, C):
    arm = list(c["R_mm_by_arm"])[1]
    ov = cv2.cvtColor(cv2.imread(f"work/edge_radii/run/{c['id']}_arm{arm}.jpg"), cv2.COLOR_BGR2RGB)
    sx, sy = (c["seed"][0] - c["box"][0]) * 4, (c["seed"][1] - c["box"][1]) * 4; Hh = 360
    ys, xs = max(0, int(sy - Hh)), max(0, int(sx - Hh))
    ax.imshow(ov[ys:ys + 2 * Hh, xs:xs + 2 * Hh]); ax.set_xticks([]); ax.set_yticks([])
    ax.set_title(f"IMG_{c['img']}  {c['family']}\nR {c['R_mm_range'][0]}-{c['R_mm_range'][1]} mm (arms {', '.join(c['R_mm_by_arm'])} px); "
                 f"{c['pxmm']} px/mm; crop {2 * Hh / 4 / c['pxmm']:.1f} mm", fontsize=8.5, loc="left")
fig.suptitle("cyan: the outline (Otsu, smoothed 2 px); orange: the middle 70 % of the turn the radius is taken over", fontsize=9, color=MUTE, y=0.995)
fig.tight_layout(rect=[0, 0, 1, 0.94]); fig.savefig(f"{OUT}/corners.png", dpi=110, facecolor=SURF); plt.close(fig)

# ---- radius by family
F = json.load(open("parts/edge_radii.json"))["families"]
names = list(F)[::-1]
fig, ax = plt.subplots(figsize=(11.5, 0.42 * len(names) + 1.6), facecolor=SURF); ax.set_facecolor(SURF)
ax.grid(color=GRID, lw=0.6, axis="x"); ax.set_axisbelow(True)
for i, k in enumerate(names):
    f = F[k]; st = f["status"]
    if st == "measured":
        lo, hi = f["radius_mm"] - f["tol_mm"], f["radius_mm"] + f["tol_mm"]
        ax.plot([lo, hi], [i, i], color=BLUE, lw=5, solid_capstyle="butt"); ax.plot(f["radius_mm"], i, "o", color=INK, ms=4)
    elif st == "upper bound":
        ax.plot([0, f["radius_mm"]], [i, i], color=BLUE, lw=5, alpha=0.45, solid_capstyle="butt")
        ax.plot(f["radius_mm"], i, "|", color=INK, ms=10)
    elif st in ("assumed", "lower bound"):
        ax.plot(f["radius_mm"], i, "D" if st == "assumed" else ">", color=ORANGE, ms=6)
    ax.text(12.3, i, f["short"], va="center", fontsize=7.5, color=MUTE)
ax.set_yticks(range(len(names))); ax.set_yticklabels([F[k]["label"] for k in names], fontsize=8.5)
ax.set_xlim(0, 12); ax.set_xlabel("radius of the eased edge (mm)")
ax.axvline(1.6, color=MUTE, lw=0.8, ls=(0, (4, 3))); ax.text(1.7, -0.6, "1.6 mm free-curve tolerance", fontsize=7, color=MUTE)
ax.set_title("Edge radii by family (parts/edge_radii.json)\nblue bar = measured range, pale bar = upper bound, orange diamond = assumed, "
             "orange triangle = lower bound only, blank = not measured", fontsize=8.5, loc="left")
ax.set_ylim(-0.9, len(names) - 0.5)
fig.tight_layout(); fig.savefig(f"{OUT}/radii.png", dpi=120, facecolor=SURF); plt.close(fig)
print("wrote", OUT)
