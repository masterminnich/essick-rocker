"""Front-leg Domino vs the leg's two arrises, per photo and per leg. Reads work/fdom/{m,dom}_{L,R}.json, work/fdom/raw/planes.json."""
import sys, json; sys.path.insert(0, ".")
import numpy as np
from rocker.cameras import Cameras
c = Cameras.load(); P = json.load(open("work/fdom/raw/planes.json")); out = {}
ANG = 50.0; SCORE = 6.0; AGREE = 1.5
for leg in ("L", "R"):
    d = P[f"FLEG_{leg}"]; o, u, n = (np.array(d[k]) for k in ("origin", "u", "n")); ang = {nm[4:8]: a for nm, a in d["photos"]}
    M = json.load(open(f"work/fdom/m_{leg}.json")); D = json.load(open(f"work/fdom/dom_{leg}.json")); rows = []
    for ph, r in M.items():
        C = np.asarray(c[f"IMG_{ph}.JPG"].center, float) - o; az = float(np.degrees(np.arctan2(C @ u, C @ n)))
        re_ = [x[2] for x in r["edges"]["rear"]]; fr = [x[2] for x in r["edges"]["front"]]; ds = D[ph]["centre_s"]
        a, b = float(np.mean(re_)), float(np.mean(fr)); why = []
        if ang[ph] > ANG: why.append(f"view {ang[ph]:.0f} deg")
        if D[ph]["score"] < SCORE: why.append(f"Domino faint (score {D[ph]['score']})")
        if len(re_) < 2 or np.ptp(re_) > AGREE: why.append(f"rear edge bands differ {np.ptp(re_):.1f}" if len(re_) > 1 else "rear edge one band")
        if len(fr) < 2 or np.ptp(fr) > AGREE: why.append(f"front edge bands differ {np.ptp(fr):.1f}" if len(fr) > 1 else "front edge one band")
        rows.append({"photo": ph, "az": round(az, 1), "view": ang[ph], "rear": round(a, 2), "front": round(b, 2), "dom": ds, "width": round(b - a, 2),
                     "dom_minus_rear": round(ds - a, 2), "front_minus_dom": round(b - ds, 2), "offset": round(ds - (a + b) / 2, 2), "used": not why, "why_not": why})
    use = [r for r in rows if r["used"]]; off = np.array([r["offset"] for r in use]); az = np.array([r["az"] for r in use]); wd = np.array([r["width"] for r in use])
    sq = [r for r in use if abs(r["az"]) <= 14]; A = np.c_[np.ones(len(az)), az]; coef = np.linalg.lstsq(A, off, rcond=None)[0]
    out[leg] = {"rows": rows, "n_used": len(use), "offset_mean": round(float(off.mean()), 2), "offset_sd": round(float(off.std(ddof=1)), 2), "offset_median": round(float(np.median(off)), 2),
                "offset_range": [float(off.min()), float(off.max())], "offset_at_az0_linear": round(float(coef[0]), 2), "slope_per_10deg": round(float(coef[1] * 10), 2),
                "square_on": {"photos": [r["photo"] for r in sq], "offset_mean": round(float(np.mean([r["offset"] for r in sq])), 2) if sq else None,
                              "width_mean": round(float(np.mean([r["width"] for r in sq])), 2) if sq else None},
                "width_mean": round(float(wd.mean()), 2), "width_sd": round(float(wd.std(ddof=1)), 2)}
    print(f"FLEG_{leg}: photos used {len(use)} of {len(rows)}")
    for r in sorted(rows, key=lambda r: r["az"]):
        print(f"  {r['photo']} az {r['az']:+6.1f} view {r['view']:4.1f}  rear {r['rear']:+7.2f} front {r['front']:+7.2f} width {r['width']:5.2f}  dom {r['dom']:+6.2f}  "
              f"dom-rear {r['dom_minus_rear']:5.2f} front-dom {r['front_minus_dom']:5.2f}  offset {r['offset']:+5.2f}  {'used' if r['used'] else 'NOT: ' + '; '.join(r['why_not'])}")
    print("  ", {k: v for k, v in out[leg].items() if k != "rows"})
allo = np.array([r["offset"] for l in "LR" for r in out[l]["rows"] if r["used"]])
out["both"] = {"n": int(len(allo)), "offset_mean": round(float(allo.mean()), 2), "offset_sd": round(float(allo.std(ddof=1)), 2), "sem": round(float(allo.std(ddof=1) / np.sqrt(len(allo))), 2)}
print("both legs:", out["both"], "(offset = Domino centre minus the middle between the two arrises, + = toward the FRONT of the leg)")
json.dump(out, open("work/fdom/analysis.json", "w"), indent=1)
