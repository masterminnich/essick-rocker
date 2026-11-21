"""USAGE: tools/py.sh tools/seat_roll/fig_front.py PICK.json OLD_stats.json NEW_stats.json OUT.png [--summary OUT.json]
The seat front's underside edge, two panels in the house style:
  left  - the direct trace (tools/seat_roll/strip.py + pick.py, single photos): how far the wood's outline reaches beyond model
          v23's bottom arris, left/right mean per photo along |x|; the median over photos; the two 6 px/mm photos; and the
          0.94 mm by which v24 lowers the line (the tube's radius, see parts/seat_front_face.json design.bottom_arris.from_tube)
  right - the critique's silhouette regions of that edge, left/right mean per 50 mm stretch, v23 against v24, ranking photos
          and held-out photos.
--summary writes the numbers the PR quotes (per 50 mm bin: median, quartiles, photo count). Tiny compute."""
import sys, json, math, argparse
import numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
ap = argparse.ArgumentParser(); ap.add_argument("pick"); ap.add_argument("old"); ap.add_argument("new"); ap.add_argument("out"); ap.add_argument("--summary")
a = ap.parse_args()
BLUE, ORANGE, INK, MUTE, GRID, SURF = "#2a78d6", "#eb6834", "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
plt.rcParams.update({"font.size": 10, "axes.edgecolor": MUTE, "axes.labelcolor": MUTE, "xtick.color": MUTE, "ytick.color": MUTE, "text.color": INK,
                     "axes.spines.top": False, "axes.spines.right": False})
P = json.load(open(a.pick)); X = np.arange(10, 245, 2.0)
per = {}
for s in P:
    r = s["rows"]
    if len(r) < 20: continue
    ax_ = np.array([abs(q["x"]) for q in r]); t = np.array([q["t"] for q in r]); v = np.full(len(X), np.nan)
    for i, x in enumerate(X):
        k = np.abs(ax_ - x) <= 6
        if k.sum() >= 3: v[i] = np.median(t[k])
    per.setdefault(s["photo"], {})[s["side"]] = (v, s["pxmm"])
mean = {p: ((d["L"][0] + d["R"][0]) / 2, (d["L"][1] + d["R"][1]) / 2) for p, d in per.items() if "L" in d and "R" in d}
M = np.array([m for m, _ in mean.values()]); med = np.nanmedian(M, 0)
fig, (A, B) = plt.subplots(1, 2, figsize=(13.5, 5.2), facecolor=SURF, gridspec_kw={"width_ratios": [1.25, 1]})
for ax in (A, B): ax.set_facecolor(SURF); ax.grid(color=GRID, lw=0.6); ax.set_axisbelow(True)
for p, (m, pm) in mean.items():
    hi = pm > 5
    A.plot(X, m, color=BLUE if hi else MUTE, lw=1.8 if hi else 0.7, alpha=1 if hi else 0.45, zorder=3 if hi else 2, ls=":" if p == "1559" else "-",
           label=f"IMG_{p}, {pm:.1f} px/mm" if hi else None)
A.plot(X, med, color=INK, lw=2.2, label=f"median of {len(mean)} photos (2.0-6.4 px/mm)", zorder=4)
A.axhline(0, color=ORANGE, lw=1.6, label="model v23's bottom arris (the r = 1 tube's spine)")
A.axhline(0.94, color=BLUE, lw=1.6, ls=(0, (5, 3)), label="model v24: 0.94 lower (the spine moved out by r)")
A.plot([], [], color=MUTE, lw=0.7, label="one photo, left/right mean")
A.set_xlabel("|x| across the chair, mm (0 = centre)"); A.set_ylabel("wood outline beyond v23's line, mm (+ = model inside)")
A.set_xlim(0, 300); A.set_ylim(-1, 4.5); A.legend(loc="upper left", frameon=False, fontsize=9)
A.set_title("Direct trace on single photos, front-above views", color=INK, loc="left")
L = lambda p: {r["region"]: r for r in json.load(open(p))["regions"]}
O, N = L(a.old), L(a.new); st = [0, 50, 100, 150, 200, 250]
def sym(R, x, k):
    r = R.get(f"SEAT|sil|bottom/front|x {x}")
    if not r: return np.nan
    v = [r["sides"].get(s, {}).get(k) for s in "LR"]
    return (v[0]["median"] + v[1]["median"]) / 2 if all(v) and not any(math.isnan(q["median"]) for q in v) else np.nan
w = 14; xs = np.array(st) + 25
o = np.array([sym(O, x, "train") for x in st]); n = np.array([sym(N, x, "train") for x in st])
B.bar(xs - w / 2, o, w, color=ORANGE, label="v23, ranking photos (left/right mean)"); B.bar(xs + w / 2, n, w, color=BLUE, label="v24, ranking photos (left/right mean)")
first = True
for x, xc in zip(st, xs):        # held-out: per side, only where both runs measured the same held-out photos
    for s_, dx, mk in (("L", -5, "o"), ("R", 5, "s")):
        ra, rb = (R.get(f"SEAT|sil|bottom/front|x {x}", {}).get("sides", {}).get(s_, {}).get("held") for R in (O, N))
        if not (ra and rb) or ra["photos"] != rb["photos"]: continue
        B.annotate("", (xc + dx, rb["median"]), (xc + dx, ra["median"]), arrowprops=dict(arrowstyle="->", color=MUTE, lw=1))
        B.plot(xc + dx, ra["median"], mk, color=ORANGE, mfc=SURF, mew=1.6, ms=7); B.plot(xc + dx, rb["median"], mk, color=BLUE, mew=1.6, ms=7)
B.plot([], [], "o", color=MUTE, mfc=SURF, label="held-out, left half: v23 (open) to v24"); B.plot([], [], "s", color=MUTE, mfc=SURF, label="held-out, right half (same photos in both runs)")
B.axhline(0, color=MUTE, lw=0.8); B.set_xticks(xs); B.set_xticklabels([f"{x}-{x + 50}" for x in st])
B.set_xlabel("|x| stretch, mm"); B.set_ylabel("critique gap, left/right mean, mm (- = model inside)")
B.set_title("Critique, silhouette of the edge: v23 against v24", color=INK, loc="left"); B.legend(frameon=False, fontsize=9, loc="lower right"); B.set_ylim(-4.3, 1.6)
fig.tight_layout(); fig.savefig(a.out, dpi=130, facecolor=SURF)
if a.summary:
    out = {"photos": sorted(mean), "pxmm": {p: round(pm, 2) for p, (_, pm) in mean.items()}, "bins": {}}
    for b0 in range(0, 250, 50):
        k = (X >= max(b0, 10)) & (X < b0 + 50); pv = np.array([np.nanmedian(m[k]) for m, _ in mean.values()]); pv = pv[np.isfinite(pv)]
        hi = [round(float(np.nanmedian(m[k])), 2) for m, pm in mean.values() if pm > 5]
        out["bins"][f"{b0}-{b0 + 50}"] = {"median": round(float(np.median(pv)), 2), "q25": round(float(np.percentile(pv, 25)), 2), "q75": round(float(np.percentile(pv, 75)), 2),
                                          "min": round(float(pv.min()), 2), "max": round(float(pv.max()), 2), "n_photos": int(len(pv)), "six_px_per_mm_photos": hi}
    allv = np.array([np.nanmedian(m[(X >= 10) & (X < 200)]) for m, _ in mean.values()])
    out["abs_x_10_200"] = {"median": round(float(np.median(allv)), 2), "q25": round(float(np.percentile(allv, 25)), 2), "q75": round(float(np.percentile(allv, 75)), 2),
                           "per_photo": {p: round(float(v), 2) for p, v in zip(mean, allv)}}
    rl = {p: round(float(np.nanmedian((d["R"][0] - d["L"][0])[(X >= 150) & (X < 240)])), 2) for p, d in per.items() if "L" in d and "R" in d}
    rl = {p: v for p, v in rl.items() if math.isfinite(v)}; out["right_minus_left_abs_x_150_240"] = {"median": round(float(np.median(list(rl.values()))), 2), "per_photo": rl}
    json.dump(out, open(a.summary, "w"), indent=1); print(json.dumps(out["bins"]), json.dumps(out["abs_x_10_200"]), json.dumps(out["right_minus_left_abs_x_150_240"]))
