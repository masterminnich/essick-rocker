"""USAGE: rk.sh work/fdom/measure.py LEG SEEDS.json OUT_PREFIX [max|sil]
Per photo, on the straightened ortho (s = across the leg at the Domino's height, v = up the face; res 0.1 mm):
  leg edges: mean over the rows of v-bands of dL/ds; the edge = the extreme of that mean within +-W mm of the seed (sign free; mode 'sil': the OUTERMOST extreme reaching 40 % of the strongest),
             per band separately (below the Domino, above it) -> two readings per edge; a straight vertical edge gives the same s
  Domino end: centre from work/fdom/domfit.py (matched filter), given in SEEDS as "dom".
SEEDS.json: {photo: {"rear": s, "front": s, "dom": [s, v], "bands": [[v0,v1],...] (optional), "w": mm (optional)}}"""
import sys, json, cv2, numpy as np
sys.path.insert(0, "work/fdom"); from shear import straight
from scipy.ndimage import gaussian_filter1d, gaussian_filter
leg, seeds, pre = sys.argv[1], json.load(open(sys.argv[2])), sys.argv[3]; MODE = sys.argv[4] if len(sys.argv) > 4 else "max"
S, V, R = (-50, 35), (-30, 60), 0.1; out = {}; tiles = []
for ph, sd in seeds.items():
    if ph.startswith("_"): continue
    im, ss, vs = straight(leg, ph, S, V, R); L = cv2.cvtColor(im, cv2.COLOR_BGR2Lab)[:, :, 0].astype(float)
    Ls = gaussian_filter(L, 3); gs = np.gradient(Ls, axis=1); W = sd.get("w", 3.0); res = {"edges": {}}
    for e in ("rear", "front"):
        rd = []
        for b0, b1 in sd.get("bands", [[-28, 6], [34, 58]]):
            rows = (vs >= b0) & (vs <= b1) & (L[:, int((sd[e] - S[0]) / R)] > 5)
            if rows.sum() < 50: continue
            prof = gs[rows].mean(0); win = np.abs(ss - sd[e]) <= W; a_ = np.abs(prof) * win
            if MODE == "sil":   # outermost local extreme of |dL/ds| that reaches 40 % of the strongest in the window: the leg's silhouette
                pk = [j for j in range(1, len(a_) - 1) if win[j] and a_[j] >= a_[j - 1] and a_[j] >= a_[j + 1] and a_[j] >= 0.4 * a_.max()]
                i = min(pk) if e == "rear" else max(pk)
            else: i = int(np.argmax(a_))
            rd.append([b0, b1, round(float(ss[i]), 2), round(float(prof[i]), 2)])
        res["edges"][e] = rd
    ex, ey = sd["dom"]; res["dom"] = {"centre": [ex, ey]}
    out[ph] = res
    # overlay
    SC = 6; big = cv2.resize(im, None, fx=SC * R, fy=SC * R, interpolation=cv2.INTER_AREA)
    lab = cv2.cvtColor(big, cv2.COLOR_BGR2Lab); lab[:, :, 0] = cv2.createCLAHE(2.0, (4, 4)).apply(lab[:, :, 0]); big = cv2.cvtColor(lab, cv2.COLOR_Lab2BGR)
    P = lambda s, v: (int(round((s - S[0]) * SC)), int(round((V[1] - v) * SC)))
    for e, col in (("rear", (255, 255, 0)), ("front", (0, 255, 255))):
        for b0, b1, s_, g in res["edges"][e]: cv2.line(big, P(s_, b0), P(s_, b1), col, 1)
    cv2.drawMarker(big, P(ex, ey), (0, 255, 0), cv2.MARKER_CROSS, 12, 1)
    for g in range(-50, 31, 10): cv2.line(big, P(g, V[1]), P(g, V[1] - 2), (255, 255, 255), 1); cv2.putText(big, str(g), (P(g, 0)[0] + 2, 12), 0, 0.35, (255, 255, 255), 1)
    cv2.rectangle(big, (0, big.shape[0] - 18), (50, big.shape[0]), (255, 255, 255), -1); cv2.putText(big, ph, (3, big.shape[0] - 4), 0, 0.5, (0, 0, 0), 1); tiles.append(big)
per = 5; rows = [np.hstack(tiles[i:i+per] + [np.zeros_like(tiles[0])] * (per - len(tiles[i:i+per]))) for i in range(0, len(tiles), per)]
cv2.imwrite(pre + ".jpg", np.vstack(rows), [cv2.IMWRITE_JPEG_QUALITY, 90]); json.dump(out, open(pre + ".json", "w"), indent=1)
for ph, r in out.items():
    re_ = [x[2] for x in r["edges"]["rear"]]; fr = [x[2] for x in r["edges"]["front"]]; c = r["dom"]["centre"]
    if re_ and fr:
        a, b = np.mean(re_), np.mean(fr); print(f"{ph}: rear {re_} front {fr} width {b - a:.2f} mid {(a + b) / 2:+.2f}  dom {c}  dom - rear {c[0] - a:.2f}  front - dom {b - c[0]:.2f}  dom - mid {c[0] - (a + b) / 2:+.2f}")
