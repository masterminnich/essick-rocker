"""USAGE: work/toolkit/rk.sh tools/slat_width/decomp.py CRITIQUE_RUNDIR OUT.json [--band 100] [--slats parts/slats.json]
Which kind of error fits ALL FOUR long edges of a slat at once? Reads the critique's per-point gaps (tools/critique/measure.py
npz, silhouettes only, status 0) of SLAT_L, SLAT_R and SLAT_C and fits, per slat (side) and z band, the model-minus-wood
displacement of the slat's section as five numbers:
  sa  shift outward (away from the chair's centre plane; SLAT_C: toward the chair's right, +x)
  sf  shift forward, square to the slat's back face (= the bend line in side view off)
  dw  model too WIDE by dw (each side edge proud by dw/2)
  dt  model too THICK by dt (front and back faces proud by dt/2)
  th  turn about the slat's own length, degrees; + = the OUTER edge forward of the inner one (mirrored for the left slat;
      SLAT_C: + = its right edge forward)
gap = m . delta(corner), m = the critique's outward 3D direction square to the line of sight at that point, corner = the
model's arris (inner/outer x front/back) at +-w/2, +-t/2 of the section. One row per photo x edge x band (median of the
photo's points, mean m); robust least squares (soft L1, scale 1 mm); se by a bootstrap over photos. Ranking photos fit;
the 15 held-out photos (tools/critique/holdout.json) are predicted from the ranking fit and their residuals reported.
Sign as the critique: + = the model sticks out beyond the wood."""
import sys, json, argparse
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares
ROOT = Path(__file__).resolve().parents[2]
ap = argparse.ArgumentParser(); ap.add_argument("run"); ap.add_argument("out")
ap.add_argument("--band", type=float, default=100.0); ap.add_argument("--slats", default=str(ROOT / "parts/slats.json"))
ap.add_argument("--zlo", type=float, default=400); ap.add_argument("--zhi", type=float, default=1000)
a = ap.parse_args()
PARTS = ["SEAT", "ARM_L", "ARM_R", "FLEG_L", "FLEG_R", "BLEG_L", "BLEG_R", "ROCKER_L", "ROCKER_R", "CREST", "SLAT_L", "SLAT_C", "SLAT_R"]
HO = set(json.load(open(ROOT / "tools/critique/holdout.json"))["held_out"])
SL = json.load(open(a.slats)); T = float(SL["thickness_mm"]); SY = SL["symmetric"]


def tables(sh):
    tb = np.array(sh["table"]); z = np.linspace(tb[0, 0], tb[-1, 0], 2000); y = np.interp(z, tb[:, 0], tb[:, 1])
    return z, y, np.r_[0, np.cumsum(np.hypot(np.diff(z), np.diff(y)))]


GEO = {}
for key, sh, lo, hi, sg in (("C", SL["sheet_centre"], SY["centre_half"], SY["centre_half"], -1.0), ("O", SL["sheet_outer"], SY["outer_in"], SY["outer_out"], 1.0)):
    z, y, s = tables(sh); dz = np.gradient(y, z)
    GEO[key] = (z, s, dz, lo, hi, sg)


def section(key, zq):
    z, s, dz, lo, hi, sg = GEO[key]; v = np.clip(np.interp(zq, z, s), *SL["v_range"])
    l, h = np.polyval(lo, v) * sg, np.polyval(hi, v); ds = np.interp(zq, z, dz); nr = np.hypot(1, ds)
    f = np.c_[np.zeros(len(zq)), 1 / nr, -ds / nr]           # forward, square to the back face
    return (l + h) / 2, h - l, f


rows = []   # slat, photo, held, edge, zb, gap, m(3), r(3) corner rel. centreline, a(3), f(3), sgn_a, sgn_f
for fn in sorted(Path(a.run).glob("IMG_*.npz")):
    name = fn.stem + ".JPG"; R = np.load(fn)
    part = np.array(PARTS)[R["part"]]
    ok = (R["st"] == 0) & (R["kind"] == 1) & np.isin(part, ["SLAT_L", "SLAT_R", "SLAT_C"])
    if not ok.any(): continue
    X, m, g, c1, c2, P = R["X"][ok].astype(float), R["m"][ok].astype(float), R["gap"][ok].astype(float), R["c1"][ok], R["c2"][ok], part[ok]
    for slat in ("SLAT_L", "SLAT_R", "SLAT_C"):
        for edge, (ca_, cf_) in {"inner/front": (3, 4), "outer/front": (2, 4), "inner/back": (3, 5), "outer/back": (2, 5)}.items():
            s = (P == slat) & (c1 == min(ca_, cf_)) & (c2 == max(ca_, cf_))
            if not s.any(): continue
            zb = np.floor(X[s, 2] / a.band) * a.band
            for b in np.unique(zb):
                q = np.nonzero(s)[0][zb == b]
                if b < a.zlo or b >= a.zhi: continue
                Xq = X[q]; zq = Xq[:, 2]
                key = "C" if slat == "SLAT_C" else "O"
                cen, w, f = section(key, zq)
                if slat == "SLAT_C":
                    sgnx = np.sign(Xq[:, 0]); cx = np.zeros(len(q)) * 0
                else:
                    sgnx = np.full(len(q), 1.0 if slat == "SLAT_R" else -1.0); cx = cen * sgnx
                aa = np.c_[sgnx, np.zeros(len(q)), np.zeros(len(q))]
                sa_ = 1.0 if ca_ == 2 else -1.0; sf_ = 1.0 if cf_ == 4 else -1.0
                if slat == "SLAT_C": sa_ = 1.0          # both side edges of the centre slat are its 'outer' faces
                r = (np.c_[cx, np.zeros(len(q)), np.zeros(len(q))] + aa * (sa_ * w / 2)[:, None] + f * (sf_ * T / 2)) - np.c_[cx, np.zeros((len(q), 2))]
                rows.append(dict(slat=slat, photo=name, held=name in HO, edge=edge + ((" R" if Xq[:, 0].mean() > 0 else " L") if slat == "SLAT_C" else ""), zb=int(b), gap=float(np.median(g[q])), n=len(q),
                                 m=m[q].mean(0), r=r.mean(0), a=aa.mean(0) if slat != "SLAT_C" else np.array([1.0, 0, 0]), f=f.mean(0),
                                 sa=sa_, sf=sf_, sgnx=float(np.sign(Xq[:, 0].mean())), w=float(w.mean())))


def design(rr, slat):
    """columns: sa, sf, dw, dt, th(rad)"""
    A = []
    for r in rr:
        m = r["m"]; aa = r["a"]; f = r["f"]
        if slat == "SLAT_C": aw = np.array([r["sgnx"], 0, 0])     # width direction = outward of the half
        else: aw = aa
        rot = np.array([-r["r"][1], r["r"][0], 0.0])              # z x r: CCW from above
        sg = 1.0 if slat in ("SLAT_R", "SLAT_C") else -1.0       # mirror the turn for the left slat
        A.append([m @ aa, m @ f, 0.5 * r["sa"] * (m @ aw), 0.5 * r["sf"] * (m @ f), sg * (m @ rot)])
    return np.array(A)


def fit(rr, slat):
    A = design(rr, slat); y = np.array([r["gap"] for r in rr])
    res = least_squares(lambda p: A @ p - y, np.zeros(5), loss="soft_l1", f_scale=1.0)
    return res.x, A, y


out = {"note": __doc__.split("\n\n")[0], "band_mm": a.band, "fits": []}
rng = np.random.default_rng(0)
for slat in ("SLAT_L", "SLAT_R", "SLAT_C"):
    for b in sorted({r["zb"] for r in rows if r["slat"] == slat}):
        tr = [r for r in rows if r["slat"] == slat and r["zb"] == b and not r["held"]]
        he = [r for r in rows if r["slat"] == slat and r["zb"] == b and r["held"]]
        edges = sorted({r["edge"] for r in tr})
        if len(tr) < 8 or len(edges) < 3: continue
        p, A, y = fit(tr, slat)
        ph = sorted({r["photo"] for r in tr}); boots = []
        for _ in range(200):
            pick = rng.choice(ph, len(ph)); rr = [r for k in pick for r in tr if r["photo"] == k]
            if len({r["edge"] for r in rr}) < 3: continue
            boots.append(fit(rr, slat)[0])
        se = np.std(boots, 0) if boots else np.full(5, np.nan)
        rt = y - A @ p
        rh = (np.array([r["gap"] for r in he]) - design(he, slat) @ p) if he else np.array([])
        per_edge = {e: dict(n=sum(r["edge"] == e for r in tr), med_gap=float(np.median([r["gap"] for r in tr if r["edge"] == e])),
                            med_resid=float(np.median(rt[[r["edge"] == e for r in tr]]))) for e in edges}
        per_edge_h = {e: dict(n=sum(r["edge"] == e for r in he), med_gap=float(np.median([r["gap"] for r in he if r["edge"] == e])),
                              med_resid=float(np.median(rh[[r["edge"] == e for r in he]]))) for e in sorted({r["edge"] for r in he})}
        w = float(np.mean([r["w"] for r in tr]))
        o = dict(slat=slat, z=b, rows=len(tr), photos=len(ph), width_model_mm=w,
                 sa=p[0], sf=p[1], dw=p[2], dt=p[3], th_deg=float(np.degrees(p[4])), th_edge_mm=float(p[4] * w / 2),
                 se=dict(sa=se[0], sf=se[1], dw=se[2], dt=se[3], th_deg=float(np.degrees(se[4]))),
                 resid_rms_rank=float(np.sqrt(np.median(rt ** 2))), resid_med_abs_held=float(np.median(np.abs(rh))) if len(rh) else None,
                 gap_med_abs_held=float(np.median(np.abs([r["gap"] for r in he]))) if he else None, held_rows=len(he),
                 edges_rank=per_edge, edges_held=per_edge_h)
        out["fits"].append(o)
        print(f"{slat} z{b:4d} rows {len(tr):3d} ph {len(ph):2d} w {w:5.1f} | sa {p[0]:+5.2f}({se[0]:.2f}) sf {p[1]:+5.2f}({se[1]:.2f}) "
              f"dw {p[2]:+5.2f}({se[2]:.2f}) dt {p[3]:+5.2f}({se[3]:.2f}) th {np.degrees(p[4]):+5.2f}deg({np.degrees(se[4]):.2f}) = {p[4]*w/2:+5.2f}mm at edge"
              f" | rms {o['resid_rms_rank']:.2f} | held n{len(he)} |gap| {o['gap_med_abs_held'] if he else float('nan'):.2f} -> |res| {o['resid_med_abs_held'] if len(rh) else float('nan'):.2f}")
        print("      " + "  ".join(f"{e} n{d['n']} g{d['med_gap']:+.2f} r{d['med_resid']:+.2f}" for e, d in per_edge.items()))
json.dump(out, open(a.out, "w"), indent=1, default=float)
