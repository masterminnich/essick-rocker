"""USAGE: tools/py.sh work/fdom/domfit.py LEG SEEDS.json({photo: [s, v] seed by eye}) OUT.json [OUT.jpg]
Domino end on the straightened ortho by a matched filter: a stadium (long a, short b, long axis at angle t, front end up) dark inside
against a 2 mm ring outside; score = mean(ring) - mean(inside) of the L channel; L clipped to the 2-80 percentile of the wood around the seed; searched over a 24.5-26.5, b 10.5-12, t 8-22 deg and the
centre (0.2 mm grid within 2.5 mm of the seed), then the centre refined to 0.05 mm on a 0.1 mm image. Writes the centre (s, v) per photo."""
import sys, json, cv2, numpy as np
sys.path.insert(0, "work/fdom"); from shear import straight
leg, SEED, outj = sys.argv[1], json.load(open(sys.argv[2])), sys.argv[3]; phs = list(SEED); outi = sys.argv[4] if len(sys.argv) > 4 else None
def kern(a, b, t, res, ring=2.0):
    n = int(np.ceil((a / 2 + ring + 1) / res)); y, x = np.mgrid[-n:n + 1, -n:n + 1] * res; y = -y
    tt = np.radians(t); xl = x * np.cos(tt) + y * np.sin(tt); yl = -x * np.sin(tt) + y * np.cos(tt)
    h = a / 2 - b / 2; d = np.sqrt(np.maximum(np.abs(xl) - h, 0) ** 2 + yl ** 2) - b / 2   # signed distance to the stadium
    inside = (d <= -0.3).astype(np.float32); ringm = ((d >= 0.6) & (d <= 0.6 + ring)).astype(np.float32)
    return (ringm / ringm.sum() - inside / inside.sum()).astype(np.float32)
S, V = (-45, 25), (-10, 50); res = {}; tiles = []
for ph in phs:
    out = {}
    for R in (0.2, 0.1):
        im, ss, vs = straight(leg, ph, S, V, R); L = cv2.GaussianBlur(cv2.cvtColor(im, cv2.COLOR_BGR2Lab)[:, :, 0].astype(np.float32), (0, 0), 0.3 / R)
        box = L[np.ix_(np.abs(vs - SEED[ph][1]) <= 14, np.abs(ss - SEED[ph][0]) <= 20)]; L = np.clip(L, np.percentile(box, 2), np.percentile(box, 80))   # bright background cannot pull the filter
        if R == 0.2:
            best = (-1e9,)
            for a in (24.5, 25.5, 26.5):
                for b in (10.5, 11.25, 12.0):
                    for t in range(8, 23, 2):
                        r = cv2.filter2D(L, -1, kern(a, b, t, R), borderType=cv2.BORDER_REPLICATE)
                        m = np.zeros_like(r, bool); m[np.ix_(np.abs(vs - SEED[ph][1]) <= 2.5, np.abs(ss - SEED[ph][0]) <= 2.5)] = True; r[~m] = -1e9
                        i = np.unravel_index(np.argmax(r), r.shape)
                        if r[i] > best[0]: best = (float(r[i]), a, b, t, ss[i[1]], vs[i[0]])
            sc, a, b, t, s0, v0 = best
        else:
            r = cv2.filter2D(L, -1, kern(a, b, t, R), borderType=cv2.BORDER_REPLICATE); m = np.zeros_like(r, bool); m[np.ix_(np.abs(vs - v0) < 1.5, np.abs(ss - s0) < 1.5)] = True; r[~m] = -1e9
            i = np.unravel_index(np.argmax(r), r.shape)
            def sub(f0, f1, f2): den = f0 - 2 * f1 + f2; return 0.0 if den == 0 else 0.5 * (f0 - f2) / den
            ds = sub(r[i[0], i[1] - 1], r[i], r[i[0], i[1] + 1]) * R; dv = -sub(r[i[0] - 1, i[1]], r[i], r[i[0] + 1, i[1]]) * R
            s0, v0 = ss[i[1]] + ds, vs[i[0]] + dv
            # how sharp the optimum is: centre of the score where it is within 5 % of the top, along s
            row = r[i[0]]; okc = row > r[i] - 0.05 * abs(r[i]); w5 = float(ss[okc].max() - ss[okc].min())
    res[ph] = {"centre_s": round(float(s0), 2), "centre_v": round(float(v0), 2), "a": float(a), "b": float(b), "tilt": t, "score": round(sc, 2), "width_5pct_s": round(w5, 2)}
    print(ph, res[ph])
    if outi:
        im, ss, vs = straight(leg, ph, (-35, 25), (0, 40), 0.1); big = cv2.resize(im, None, fx=0.8, fy=0.8)
        lab = cv2.cvtColor(big, cv2.COLOR_BGR2Lab); lab[:, :, 0] = cv2.createCLAHE(2.0, (4, 4)).apply(lab[:, :, 0]); big = cv2.cvtColor(lab, cv2.COLOR_Lab2BGR)
        k = kern(a, b, t, 0.125); n = k.shape[0] // 2; cx, cy = (s0 + 35) * 8, (40 - v0) * 8
        cnt, _ = cv2.findContours((k < 0).astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        cv2.polylines(big, [(c.reshape(-1, 2) - n + [cx, cy]).astype(np.int32) for c in cnt], True, (0, 255, 255), 1, cv2.LINE_AA)
        cv2.drawMarker(big, (int(cx), int(cy)), (0, 255, 255), cv2.MARKER_CROSS, 10, 1); cv2.putText(big, ph, (4, 16), 0, 0.5, (255, 255, 255), 1); tiles.append(big)
json.dump(res, open(outj, "w"), indent=1)
if outi:
    per = 4; rows = [np.hstack(tiles[i:i+per] + [np.zeros_like(tiles[0])] * (per - len(tiles[i:i+per]))) for i in range(0, len(tiles), per)]
    cv2.imwrite(outi, np.vstack(rows), [cv2.IMWRITE_JPEG_QUALITY, 92])
