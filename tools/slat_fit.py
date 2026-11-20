"""USAGE: python -I tools/slat_fit.py --dir work/parts/back --out parts/slats.json
Fair edges for the three slats from the traces in the unrolled back view (u = across the chair, v = length along the
slat's curve, mm). Each edge: robust quadratic u(v) (mis-traced stations rejected at 1.5 mm). Reports widths, the
left/right mirror agreement and the centre slat's symmetry about the chair centre line. Tiny compute."""
import json, argparse, numpy as np
ap = argparse.ArgumentParser(); ap.add_argument("--dir", required=True); ap.add_argument("--out", required=True); a = ap.parse_args()
def fit(e, lo=60, hi=680):
    e = np.array(e); e = e[(e[:, 1] > lo) & (e[:, 1] < hi)]; keep = np.ones(len(e), bool)
    for _ in range(8): c = np.polyfit(e[keep, 1], e[keep, 0], 2); keep = np.abs(e[:, 0] - np.polyval(c, e[:, 1])) < 1.5
    return c, float(np.std(e[keep, 0] - np.polyval(c, e[keep, 1]))), float(keep.mean())
E = {}
for n in ("slatC", "slatR", "slatL"):
    d = json.load(open(f"{a.dir}/{n}.json"))
    for s in "ab":
        c, sd, k = fit(d[f"{n}_{s}"]); E[f"{n}_{s}"] = {"coef": c.tolist(), "scatter_mm": sd, "inlier_share": k}
        print(f"{n}_{s}: scatter {sd:.2f} mm, clean stations {k:.0%}")
V = np.array([60, 200, 350, 500, 680.0]); ev = lambda k: np.polyval(E[k]["coef"], V)
def lohi(n): x, y = ev(n + "_a"), ev(n + "_b"); return np.minimum(x, y), np.maximum(x, y)
cl, ch = lohi("slatC"); rl, rh = lohi("slatR"); ll, lh = lohi("slatL")
print("v (mm up the slat):        ", V.astype(int).tolist())
print("centre slat width mm:      ", (ch - cl).round(1).tolist(), "| inches", ((ch - cl) / 25.4).round(2).tolist())
print("centre slat mid-line u mm: ", ((ch + cl) / 2).round(1).tolist())
print("right slat width mm:       ", (rh - rl).round(1).tolist()); print("left slat width mm:        ", (lh - ll).round(1).tolist())
print("right slat inner/outer u:  ", rl.round(1).tolist(), rh.round(1).tolist()); print("left slat (mirrored) in/out:", (-lh).round(1).tolist(), (-ll).round(1).tolist())
print("gap centre-right mm:       ", (rl - ch).round(1).tolist(), "| gap centre-left mm:", (cl - lh).round(1).tolist())
json.dump({"edges": E, "v_samples": V.tolist(), "centre_width": (ch - cl).tolist(), "right_width": (rh - rl).tolist(), "left_width": (lh - ll).tolist(),
           "sheet": json.load(open(f"{a.dir}/s_plane.json"))}, open(a.out, "w"), indent=1)
