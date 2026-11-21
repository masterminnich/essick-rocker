"""USAGE: tools/py.sh tools/seat_corner/fig_chart.py   (after aggregate.py --min-ppm 2.2 --xmin 170)
Chart: seat-top silhouette offset near each front corner, per photo, right and left; and the slope of the model's top across x
there (how much a sideways shift of the seat would change the heights). Writes figures/seat_corner/offset_per_photo.png and
work/seatcorner/slope.json."""
import sys, json; from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]; sys.path.insert(0, str(ROOT))
import numpy as np, matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from tools.seat_corner.common import seat_top_z_fn
BLUE, ORANGE, SURF, INK, INK2, GRID = "#2a78d6", "#eb6834", "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
A = json.load(open(ROOT / "work/seatcorner/summary.json")); rows = [r for r in A["rows"] if r["zone"] in ("surface", "roll")]
# one number per photo and side: the sample-weighted mean of its zone medians
per = {}
for r in rows: per.setdefault(r["photo"], {}).setdefault(r["side"], []).append((r["n"], r["median_mm"]))
val = {p: {s: float(np.average([m for _, m in v], weights=[n for n, _ in v])) for s, v in d.items()} for p, d in per.items()}
ph = sorted(val); xi = {p: i for i, p in enumerate(ph)}
R = np.array([val[p]["R"] for p in ph if "R" in val[p]]); L = np.array([val[p]["L"] for p in ph if "L" in val[p]])
both = [p for p in ph if "R" in val[p] and "L" in val[p]]; D = np.array([val[p]["R"] - val[p]["L"] for p in both]); M = np.array([(val[p]["R"] + val[p]["L"]) / 2 for p in both])
fig, ax = plt.subplots(figsize=(10, 4.8), dpi=150); fig.patch.set_facecolor(SURF); ax.set_facecolor(SURF)
for p in both: ax.plot([xi[p], xi[p]], [val[p]["R"], val[p]["L"]], color=GRID, lw=2, zorder=1)
ax.scatter([xi[p] for p in ph if "R" in val[p]], R, s=36, color=ORANGE, zorder=3, label=f"chair's right corner: {len(R)} photos, median {np.median(R):+.2f}, sd {R.std(ddof=1):.2f} mm")
ax.scatter([xi[p] for p in ph if "L" in val[p]], L, s=36, color=BLUE, zorder=3, label=f"chair's left corner: {len(L)} photos, median {np.median(L):+.2f}, sd {L.std(ddof=1):.2f} mm")
ax.axhline(np.median(R), color=ORANGE, lw=1, ls=":"); ax.axhline(np.median(L), color=BLUE, lw=1, ls=":")
ax.axhline(0, color=INK2, lw=1); ax.text(len(ph) - 0.6, 0.1, "model on the wood", color=INK2, fontsize=8, ha="right")
ax.set_xticks(range(len(ph))); ax.set_xticklabels(ph, rotation=60, fontsize=7.5, color=INK2); ax.set_xlim(-0.8, len(ph) - 0.2)
ax.grid(True, axis="y", color=GRID, lw=0.6); ax.set_axisbelow(True)
for s in ax.spines.values(): s.set_color(GRID)
ax.tick_params(colors=INK2, labelsize=8)
ax.set_ylabel("wood edge minus model contour, mm along the surface normal\n(- = model stands above / outside the wood)", color=INK2, fontsize=9)
ax.set_title(f"Seat top near the front corners (|x| 170-255, 0-40 mm behind the front edge), model v19\nsame photo, right - left: median {np.median(D):+.2f} mm ({len(D)} photos)",
             color=INK, fontsize=10, loc="left")
ax.legend(loc="lower left", fontsize=8, frameon=False, labelcolor=INK2)
fig.tight_layout(); (ROOT / "figures/seat_corner").mkdir(parents=True, exist_ok=True); fig.savefig(ROOT / "figures/seat_corner/offset_per_photo.png", facecolor=SURF)
# slope of the model top across x in the corner region
tz = seat_top_z_fn(ROOT / "parts/model_v19_shapes.glb"); xs = np.arange(180, 241, 10.0); out = {}
for y in (490.0, 500.0, 505.0):
    zp = tz(np.c_[xs + 1, np.full(len(xs), y)]); zm = tz(np.c_[xs - 1, np.full(len(xs), y)]); out[f"y{int(y)}"] = {f"x{int(x)}": float((a - b) / 2) for x, a, b in zip(xs, zp, zm)}
sl = np.array([v for d in out.values() for v in d.values()]); sl = sl[np.isfinite(sl)]
res = {"dz_dabsx_model_top": out, "median_slope": float(np.median(sl)), "photos_right": len(R), "photos_left": len(L), "right_median": float(np.median(R)), "right_sd": float(R.std(ddof=1)),
       "left_median": float(np.median(L)), "left_sd": float(L.std(ddof=1)), "same_photo_right_minus_left": {"photos": both, "median": float(np.median(D)), "mean": float(D.mean()), "sd": float(D.std(ddof=1))},
       "same_photo_mean_of_sides": {"median": float(np.median(M)), "mean": float(M.mean()), "sd": float(M.std(ddof=1))}, "per_photo": val}
json.dump(res, open(ROOT / "work/seatcorner/slope.json", "w"), indent=1)
print(json.dumps({k: v for k, v in res.items() if k not in ("per_photo", "dz_dabsx_model_top")}, indent=1))
