"""USAGE: work/toolkit/rk.sh tools/seat_corner/aggregate.py [--dir work/seatcorner/sil] [--use tools/seat_corner/inputs/use.json] [--out work/seatcorner/summary.json]
Per photo and side: median silhouette offset (mm along the surface normal; < 0 = model proud of the wood) of the samples written by
sil.py, split into zones by where the contour generator lies on the model:
  roll    = within 12 mm behind the front plan outline (the rolled front edge; parts/seat_front_face.json, L/R mean)
  surface = 12 mm or more behind it, |x| <= 255 (the seat top: seat/surface.json, right-half tape dots mirrored)
  end     = |x| > 255 (the corner's rounded end and the side edge near it)
Only |x| >= --xmin (default 150) is the corner region; --xmin 100 widens it. Uses only the photos/sides/zones listed in the
--use file (checked by eye on the 10 px/mm crops), if given. Tiny compute."""
import sys, json, argparse, glob; from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]; sys.path.insert(0, str(ROOT))
import numpy as np
ap = argparse.ArgumentParser(); ap.add_argument("--dir", default="work/seatcorner/sil"); ap.add_argument("--use", default=None); ap.add_argument("--out", default="work/seatcorner/summary.json")
ap.add_argument("--xmin", type=float, default=150.0); ap.add_argument("--min-ppm", type=float, default=0.0); ap.add_argument("--quiet", action="store_true")
a = ap.parse_args()
FY = np.array(json.load(open(ROOT / "parts/seat_front.json"))["design"]["front_y_of_abs_x"]); fy = lambda x: np.interp(np.abs(x), FY[:, 0], FY[:, 1])
use = json.load(open(ROOT / a.use)) if a.use else None
def zone(X):
    ax = abs(X[0]); return "end" if ax > 255 else ("roll" if fy(ax) - X[1] < 12 else "surface")
rows = []
for f in sorted(glob.glob(str(ROOT / a.dir / "*.json"))):
    R = json.load(open(f)); p = Path(f).stem
    for side, sg in (("R", 1), ("L", -1)):
        for zn in ("surface", "roll", "end"):
            if use is not None and zn not in use.get(p, {}).get(side, []): continue
            q = [s for s in R["samples"] if not s["occluded"] and s.get("agree", True) and np.sign(s["X"][0]) == sg and abs(s["X"][0]) >= a.xmin and zone(s["X"]) == zn]
            if len(q) < 8: continue
            o = np.array([s["offset_mm"] for s in q]); ppm = float(np.median([s["px_per_mm"] for s in q]))
            if ppm < a.min_ppm: continue
            zq = np.array([s["z_equiv"] for s in q]); med = float(np.median(o)); mad = float(1.4826 * np.median(np.abs(o - med)))
            rows.append({"photo": p, "side": side, "zone": zn, "n": len(q), "px_per_mm": ppm, "median_mm": med, "mad_mm": mad, "z_equiv_median": float(np.median(zq)),
                         "abs_x": [float(min(abs(s["X"][0]) for s in q)), float(max(abs(s["X"][0]) for s in q))], "y": [float(min(s["X"][1] for s in q)), float(max(s["X"][1] for s in q))]})
if not a.quiet:
    for r in rows: print(f"{r['photo']} {r['side']} {r['zone']:7s} n {r['n']:4d} {r['px_per_mm']:4.1f} px/mm  |x| {r['abs_x'][0]:3.0f}-{r['abs_x'][1]:3.0f} y {r['y'][0]:3.0f}-{r['y'][1]:3.0f}  offset {r['median_mm']:+5.2f} (mad {r['mad_mm']:.2f})  z_eq {r['z_equiv_median']:+5.2f}")
summ = {}
print("\nzone    side  photos  median of photo medians   mean   sd    (mm, < 0 = model proud of the wood)")
for zn in ("surface", "roll", "end"):
    for side in ("R", "L"):
        v = np.array([r["median_mm"] for r in rows if r["zone"] == zn and r["side"] == side])
        if len(v) == 0: continue
        summ[f"{zn}_{side}"] = {"photos": int(len(v)), "median": float(np.median(v)), "mean": float(v.mean()), "sd": float(v.std(ddof=1)) if len(v) > 1 else None, "min": float(v.min()), "max": float(v.max())}
        print(f"{zn:7s} {side}     {len(v):3d}    {np.median(v):+6.2f}                {v.mean():+6.2f}  {v.std(ddof=1) if len(v) > 1 else 0:5.2f}   range {v.min():+.2f}..{v.max():+.2f}")
    # same photo, both sides: R - L (cancels most of a photo's own pose error)
    pr = {(r["photo"]): {} for r in rows if r["zone"] == zn}
    for r in rows:
        if r["zone"] == zn: pr[r["photo"]][r["side"]] = r["median_mm"]
    d = np.array([v["R"] - v["L"] for v in pr.values() if "R" in v and "L" in v]); m = np.array([(v["R"] + v["L"]) / 2 for v in pr.values() if "R" in v and "L" in v])
    if len(d):
        summ[f"{zn}_R_minus_L_same_photo"] = {"photos": int(len(d)), "median": float(np.median(d)), "mean": float(d.mean()), "sd": float(d.std(ddof=1)) if len(d) > 1 else None}
        summ[f"{zn}_mean_of_sides_same_photo"] = {"photos": int(len(m)), "median": float(np.median(m)), "mean": float(m.mean()), "sd": float(m.std(ddof=1)) if len(m) > 1 else None}
        print(f"{zn:7s} R-L same photo: {len(d)} photos, median {np.median(d):+.2f}, mean {d.mean():+.2f}, sd {d.std(ddof=1) if len(d) > 1 else 0:.2f};  (R+L)/2: median {np.median(m):+.2f}, mean {m.mean():+.2f}, sd {m.std(ddof=1) if len(m) > 1 else 0:.2f}")
json.dump({"rows": rows, "summary": summ, "xmin": a.xmin, "use": a.use}, open(ROOT / a.out, "w"), indent=1)
