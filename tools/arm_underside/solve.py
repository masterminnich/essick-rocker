"""USAGE: work/toolkit/rk.sh tools/arm_underside/solve.py SIDE(L|R) CFG.json OUT.json
Step 3 of 4 (strip -> snap -> solve -> fit). Triangulates one line of one arm (e.g. the outer bottom arris) from the per-photo traces
of tools/arm_underside/snap.py, relative to that arm's own outer top arris (parts/arms.json, the strip's reference).
CFG.json: {"traces": ["work/armu/tr_above_R.json", ...], "curve": "bot", "photos": {"1472": [[ya, yb], ...], ...},
           "register": true, "y": [ya, yb], "deg": 6}
Geometry. A trace point (y, d) is the point Q = top(y) - d * z on the vertical surface through the top arris. The real line lies on the
camera ray through Q, a mm further INBOARD (horizontally, square to the arris in plan) and h mm below the top arris:
    d = h(y') + a(y') r_z / r_in + ztop(y) - ztop(y'),   y' = y + a r_y / r_in      (r = ray direction, r_in its inboard horizontal part)
so photos from above (k < 0) and from below (k > 0) separate the drop h from the inboard offset a. A line far inboard (the bottom INNER
arris seen from below, a = the arm's width) is met by an oblique ray at another station, y' = y + a r_y / r_in: the fit is iterated with
h, a evaluated at y' and the top arris's own rise between y and y' added to d (for the outer bottom arris y' - y is under 3 mm). h(y), a(y): Legendre polynomials
of degree "deg" over "y", fitted by robust least squares (Huber, 0.6 mm) to all trusted trace points, one every 2 mm.
"register": each photo's own top-arris trace (key "top@photo", a straight line fitted to it in y) is subtracted from its d first: that
removes most of the photo's pose error, so h is measured from the top arris AS THIS PHOTO SEES IT (both lines on one photo). The mean of
those top offsets is reported (how far the side photos' top edge sits from the overhead-triangulated arris).
"fix_a": a number -> a(y) is held at that value (only h fitted; for a set of photos too narrow in elevation to separate a from h);
"width" -> a(y) is the arm's own width in plan at y (outer minus inner top arris, parts/arms.json): the line is the bottom INNER arris
straight below the inner top arris (inner face vertical), only its drop h is fitted.
"curve_by_photo": {photo: key prefix} reads another trace for that photo (e.g. "obot", the outer bottom arris seen from below).
Writes {"y": [...], "h": [...], "a": [...], "photos": {photo: {"n", "rms_mm", "top_offset_mm"}}, "loo": {photo: {"h": [...], "a": [...]}},
"jackknife_se": {"h": [...], "a": [...]}, "kz_range": [...]} (stations every 1 mm), and prints the numbers quoted in the PR."""
import sys, json, numpy as np
sys.path.insert(0, ".")
from numpy.polynomial import legendre as L
from rocker.cameras import Cameras
side, cfgf, outf = sys.argv[1:4]; cfg = json.load(open(cfgf)); sg = 1.0 if side == "R" else -1.0
c = Cameras.load(); A = json.load(open("parts/arms.json"))[{"L": "left", "R": "right"}[side]]
O = np.array(A["outer_top_arris_xyz"]); O = O[np.argsort(O[:, 1])]
I_ = np.array(A["inner_top_arris_xyz"]); I_ = I_[np.argsort(I_[:, 1])]
def width(y):
    """plan width outer - inner top arris at y, measured square to the outer arris (straight lines beyond the traced ends)"""
    y = np.atleast_1d(np.asarray(y, float)); wo = np.abs(np.interp(y, O[:, 1], O[:, 0], left=np.nan, right=np.nan)) - np.abs(np.interp(y, I_[:, 1], I_[:, 0], left=np.nan, right=np.nan))
    for lo in (True, False):
        m = ~np.isfinite(wo) & ((y < 200) if lo else (y > 200)); yy = np.arange(I_[0, 1] + 1, I_[0, 1] + 41) if lo else np.arange(I_[-1, 1] - 40, I_[-1, 1])
        if m.any(): wo[m] = np.polyval(np.polyfit(yy, np.abs(np.interp(yy, O[:, 1], O[:, 0])) - np.abs(np.interp(yy, I_[:, 1], I_[:, 0])), 1), y[m])
    return wo
def top(y):
    y = np.atleast_1d(np.asarray(y, float)); P = np.stack([np.interp(y, O[:, 1], O[:, i]) for i in range(3)], 1); P[:, 1] = y
    for lo in (True, False):
        m = (y < O[0, 1]) if lo else (y > O[-1, 1]); sel = (O[:, 1] < O[0, 1] + 40) if lo else (O[:, 1] > O[-1, 1] - 40)
        if m.any():
            for i in (0, 2): P[m, i] = np.polyval(np.polyfit(O[sel, 1], O[sel, i], 1), y[m])
    return P
TR = {}
for f in cfg["traces"]: TR.update(json.load(open(f)))
ya, yb = cfg["y"]; deg = cfg.get("deg", 6); ym, hw = (ya + yb) / 2, (yb - ya) / 2; curve = cfg.get("curve", "bot"); fix_a = cfg.get("fix_a")
basis = lambda y: np.stack([L.legval((np.asarray(y) - ym) / hw, np.eye(deg + 1)[j]) for j in range(deg + 1)], 1)
rows = []      # photo, y, d, k
tops = {}
for ph, ranges in cfg["photos"].items():
    T = np.array(TR[f"{cfg.get('curve_by_photo', {}).get(ph, curve)}@{ph}"]["yd"]); keep = np.zeros(len(T), bool)
    for a_, b_ in ranges: keep |= (T[:, 0] >= a_) & (T[:, 0] <= b_)
    T = T[keep & (T[:, 0] >= ya) & (T[:, 0] <= yb)]; T = T[(T[:, 0] % 2) == 0]
    off = np.zeros(len(T)); toff = None
    if cfg.get("register", True):
        tt = np.array(TR[f"top@{ph}"]["yd"]); tr = cfg.get("top_ranges", {}).get(ph, [[60, 480]]); km = np.zeros(len(tt), bool)
        for a_, b_ in tr: km |= (tt[:, 0] >= a_) & (tt[:, 0] <= b_)
        p = np.polyfit(tt[km, 0], tt[km, 1], 1); off = np.polyval(p, T[:, 0]); toff = float(np.median(tt[km, 1]))
    tops[ph] = toff
    P0 = top(T[:, 0]); Q = P0 - T[:, 1:2] * np.array([0, 0, 1.0])
    C = np.asarray(c[f"IMG_{ph}.JPG"].center, float); r = Q - C; r /= np.linalg.norm(r, axis=1, keepdims=True)
    tg = np.gradient(P0, axis=0); tg[:, 2] = 0; tg /= np.linalg.norm(tg, axis=1, keepdims=True); nin = np.cross([0, 0, 1.0], tg) * sg      # inboard horizontal normal
    nin *= np.sign(-nin[:, :1] * sg)
    r_in = (r * nin).sum(1)
    for yy, dd, kz, ky in zip(T[:, 0], T[:, 1] - off, r[:, 2] / r_in, r[:, 1] / r_in): rows.append((ph, yy, dd, kz, ky))
ph_ = np.array([r_[0] for r_ in rows]); Y = np.array([r_[1] for r_ in rows]); D = np.array([r_[2] for r_ in rows]); KZ = np.array([r_[3] for r_ in rows]); KY = np.array([r_[4] for r_ in rows])
ztop = lambda y: top(y)[:, 2]
def fit(m):
    fixed = None if fix_a is None else (lambda y: width(y)) if fix_a == "width" else (lambda y: np.full(len(np.atleast_1d(y)), float(fix_a)))
    a0 = fixed(Y[m]) if fixed else np.full(m.sum(), cfg.get("a_start", 0.0)); sol = None
    for it in range(6):
        Yp = Y[m] + a0 * KY[m]
        if fixed:
            for _ in range(5): a0 = fixed(Yp); Yp = Y[m] + a0 * KY[m]
        B = basis(Yp); M = np.c_[B, B * KZ[m, None]] if fix_a is None else B
        rhs = D[m] + ztop(Yp) - ztop(Y[m]) - (0 if fix_a is None else a0 * KZ[m]); w = np.ones(m.sum())
        for _ in range(15):
            lam = 1e-3; sol = np.linalg.lstsq(np.r_[M * w[:, None], lam * np.eye(M.shape[1])], np.r_[rhs * w, np.zeros(M.shape[1])], rcond=None)[0]
            res = rhs - M @ sol; w = np.sqrt(np.where(np.abs(res) < 0.6, 1.0, 0.6 / np.abs(res)))
        if fixed: break
        a0 = np.clip(B @ sol[deg + 1:], -100, 150)
    return sol, res
def curves(sol, ys):
    B = basis(ys); h = B @ sol[:deg + 1]; a = B @ sol[deg + 1:] if fix_a is None else width(ys) if fix_a == "width" else np.full(len(ys), float(fix_a)); return h, a
ys = np.arange(ya, yb + 1, 1.0); allm = np.ones(len(Y), bool); sol, res = fit(allm); h, a = curves(sol, ys)
phs = list(cfg["photos"]); out = {"y": ys.tolist(), "h": h.round(3).tolist(), "a": a.round(3).tolist(), "photos": {}, "loo": {}, "kz_range": [float(KZ.min()), float(KZ.max())]}
for p in phs:
    m = ph_ == p; out["photos"][p] = {"n": int(m.sum()), "rms_mm": round(float(np.sqrt(np.mean(res[m] ** 2))), 2), "median_resid_mm": round(float(np.median(res[m])), 2),
                                      "kz_median": round(float(np.median(KZ[m])), 3), "ky_median": round(float(np.median(KY[m])), 3), "top_offset_mm": None if tops[p] is None else round(tops[p], 2)}
    s2, _ = fit(~m); h2, a2 = curves(s2, ys); out["loo"][p] = {"h": h2.round(3).tolist(), "a": a2.round(3).tolist()}
n = len(phs); Hl = np.array([out["loo"][p]["h"] for p in phs]); Al = np.array([out["loo"][p]["a"] for p in phs])
se = lambda X: np.sqrt((n - 1) / n * ((X - X.mean(0)) ** 2).sum(0))
out["jackknife_se"] = {"h": se(Hl).round(3).tolist(), "a": se(Al).round(3).tolist()}
json.dump(out, open(outf, "w"))
print(f"{side} {curve}: {n} photos, {len(Y)} points, r_z/r_in {KZ.min():+.2f}..{KZ.max():+.2f}, robust rms {np.sqrt(np.mean(res ** 2)):.2f} mm")
for p in phs: print("  ", p, out["photos"][p])
for yy in range(int(np.ceil(ya / 20) * 20), int(yb) + 1, 20):
    i = int(yy - ya); print(f"  y {yy}: h {h[i]:6.2f} (se {out['jackknife_se']['h'][i]:.2f})  a {a[i]:+6.2f} (se {out['jackknife_se']['a'][i]:.2f})")
