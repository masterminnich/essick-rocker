"""USAGE: work/toolkit/rk.sh tools/rocker_thickness/trace.py RIBDIR
Step 2. In every ribbon (tools/rocker_thickness/ribbon.py) and every clean column: the two arrises of the top face along d.
Colour (Lab) averaged over 5 mm of u, gradient along d (Gaussian derivative, sigma 0.4 mm), edge strength = |dLab/dd|.
Outer arris = the strongest step in d -7..9, inner arris = the strongest step in d 22..41 (bands wide enough for the photos' pose
error, +-5 mm, and for a rocker up to 41 mm thick); sub-sampled with a parabola. Kept where the step's contrast (Lab distance
between the means 1.0-2.0 mm either side) is >= 8 and the column agrees within 1.0 mm with the running median of its
neighbours (21 mm of u; a trace must be continuous along the rocker), so marks and tone bands on the face drop out.
Writes RIBDIR/trace.json: per side, per photo: d_out, d_in (mm from the model's outer face, NaN where not kept), contrasts."""
import sys, json
import numpy as np, cv2
from scipy.ndimage import uniform_filter1d, gaussian_filter1d, median_filter
rib = sys.argv[1]
R = json.load(open(f"{rib}/ribbons.json")); g = R["grid"]; DD = g["dd"]
ds = np.arange(g["d0"], g["d1"] + 1e-9, DD); ri = lambda d: int(round((d - g["d0"]) / DD))
BANDS = {"d_out": (-7.0, 9.0), "d_in": (22.0, 41.0)}
out = {"method": "strongest Lab step in band, contrast >= 8, continuous within 1 mm over 21 mm", "u0": g["u0"], "du": g["du"], "sides": {}}
def runmed(v, w=21):
    f = np.where(np.isfinite(v), v, np.nan); o = np.full(len(v), np.nan)
    for i in range(len(v)):
        s = f[max(0, i - w // 2): i + w // 2 + 1]; s = s[np.isfinite(s)]
        if len(s) >= 5: o[i] = np.median(s)
    return o
for S, sd in R["sides"].items():
    out["sides"][S] = {}
    for ph, info in sd["photos"].items():
        img = cv2.imread(f"{rib}/{S}_{ph}.png"); ok = np.array(info["ok"], bool)
        lab = cv2.cvtColor(img, cv2.COLOR_BGR2Lab).astype(np.float32)
        lab = uniform_filter1d(lab, 5, axis=1)
        okc = uniform_filter1d(ok.astype(float), 5) > 0.99
        gr = np.linalg.norm(gaussian_filter1d(lab, 0.4 / DD, axis=0, order=1), axis=2)     # (nd, nu)
        rec = {}
        for key, (a, b) in BANDS.items():
            i0, i1 = ri(a), ri(b); sub = gr[i0:i1]; k = sub.argmax(0); kk = np.clip(k, 1, len(sub) - 2); cc = np.arange(sub.shape[1])
            ym, y0, yp = sub[kk - 1, cc], sub[kk, cc], sub[kk + 1, cc]; den = ym - 2 * y0 + yp
            dl = np.clip(np.where(np.abs(den) > 1e-9, 0.5 * (ym - yp) / den, 0), -0.5, 0.5)
            d = g["d0"] + (i0 + kk + dl) * DD
            idx = i0 + kk; lo = np.clip(idx[None] - np.arange(10, 21)[:, None], 0, len(ds) - 1); hi = np.clip(idx[None] + np.arange(10, 21)[:, None], 0, len(ds) - 1)
            con = np.linalg.norm(lab[hi, cc].mean(0) - lab[lo, cc].mean(0), axis=1)
            d[~okc | (con < 8) | (k == 0) | (k == len(sub) - 1)] = np.nan
            rm = runmed(d); d[~(np.abs(d - rm) <= 1.0)] = np.nan
            rec[key] = np.round(d, 2).tolist(); rec["c" + key[1:]] = np.round(con, 1).tolist()
        out["sides"][S][ph] = rec
        do, di = np.array(rec["d_out"], float), np.array(rec["d_in"], float); both = np.isfinite(do) & np.isfinite(di)
        print(S, ph, "out %4d in %4d both %4d" % (np.isfinite(do).sum(), np.isfinite(di).sum(), both.sum()),
              "T median %.2f" % np.median(di[both] - do[both]) if both.any() else "", flush=True)
json.dump(out, open(f"{rib}/trace.json", "w"))
