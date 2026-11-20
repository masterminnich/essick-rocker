"""USAGE: python -I tools/slat_fit.py --edges work/parts/back/slat_edges.json --sheet work/parts/back/s_plane.json --out parts/slats.json
Fair edges for the three slats from the by-eye-seeded, refined traces in the unrolled back view (u = across the chair,
v = length up the slat's curve, mm). Each edge: robust 4th-order curve u(v), checked against the raw trace. Reports widths, left/right mirror agreement and
the design-intent (averaged, symmetric) edges. Tiny compute."""
import json, argparse, numpy as np
ap = argparse.ArgumentParser(); ap.add_argument("--edges", required=True); ap.add_argument("--sheet", required=True); ap.add_argument("--out", required=True); a = ap.parse_args()
E = json.load(open(a.edges)); F = {}
for k, e in E.items():
    e = np.array(e); keep = np.ones(len(e), bool)
    for _ in range(8): c = np.polyfit(e[keep, 1], e[keep, 0], 4); keep = np.abs(e[:, 0] - np.polyval(c, e[:, 1])) < 2.0
    # guard: the fair curve must agree with the raw trace's local median everywhere (a bad fit shows up here)
    chk = max(abs(np.median(e[np.abs(e[:, 1] - v0) < 25, 0]) - np.polyval(c, v0)) for v0 in np.arange(75, 670, 50))
    F[k] = {"coef": c.tolist(), "scatter_mm": float(np.std(e[keep, 0] - np.polyval(c, e[keep, 1]))), "clean": float(keep.mean()), "v": [float(e[:, 1].min()), float(e[:, 1].max())], "max_dev_from_raw_mm": float(chk)}
    print(f"{k:12s} scatter {F[k]['scatter_mm']:.2f} mm, clean stations {keep.mean():.0%}, worst gap between fair curve and raw trace {chk:.2f} mm")
V = np.array([60, 200, 350, 500, 660.0]); ev = lambda k: np.polyval(F[k]["coef"], V)
cw = ev("slatC_right") - ev("slatC_left"); rw = ev("slatR_out") - ev("slatR_in"); lw = ev("slatL_in") - ev("slatL_out")
print("v up the slat (mm):       ", V.astype(int).tolist())
print("centre slat width (mm):   ", cw.round(1).tolist(), "| in", (cw / 25.4).round(2).tolist())
print("centre half L / R (mm):   ", (-ev("slatC_left")).round(1).tolist(), ev("slatC_right").round(1).tolist())
print("right slat width (mm):    ", rw.round(1).tolist()); print("left slat width (mm):     ", lw.round(1).tolist())
print("inner edge R / L mirrored:", ev("slatR_in").round(1).tolist(), (-ev("slatL_in")).round(1).tolist())
print("outer edge R / L mirrored:", ev("slatR_out").round(1).tolist(), (-ev("slatL_out")).round(1).tolist())
d = np.r_[ev("slatR_in") + ev("slatL_in"), ev("slatR_out") + ev("slatL_out"), ev("slatC_right") + ev("slatC_left")]
print(f"left/right mirror disagreement: rms {np.sqrt(np.mean(d ** 2)):.2f} mm, max {np.abs(d).max():.2f} mm")
sym = {"centre_half": ((np.array(F["slatC_right"]["coef"]) - np.array(F["slatC_left"]["coef"])) / 2).tolist(),
       "outer_in": ((np.array(F["slatR_in"]["coef"]) - np.array(F["slatL_in"]["coef"])) / 2).tolist(),
       "outer_out": ((np.array(F["slatR_out"]["coef"]) - np.array(F["slatL_out"]["coef"])) / 2).tolist()}
json.dump({"fits": F, "symmetric": sym, "v_range": [50, 685], "sheet": json.load(open(a.sheet)),
           "widths_mm": {"v": V.tolist(), "centre": cw.tolist(), "right": rw.tolist(), "left": lw.tolist()}}, open(a.out, "w"), indent=1)
