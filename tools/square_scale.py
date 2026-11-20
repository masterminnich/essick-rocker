"""USAGE: python -I tools/square_scale.py --prov work/frame/prov.json --photos 1500,1513,... [--out work/frame/scale.json]
Metric scale from the framing square's printed 1/8-inch tick comb, independent of any plane assumption.
For each photo: rectify a strip along the outer edge of the tongue and of the body onto the provisional square plane,
measure the local phase of the 1/8" tick comb (complex demodulation, 1-inch window), locate every whole-inch mark,
map it back to a raw pixel of that photo. Then triangulate each inch mark from all photos that see it, fit a 3D line
per leg, and regress distance along the line against inches.
Compute: one photo in memory at a time (~36 MB), strips of ~0.3 MP; a few seconds, < 1 GB.
"""
import sys, json, argparse
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import numpy as np, cv2
from rocker.cameras import Cameras
from rocker.ortho import Plane, ortho, load_raw
from rocker.triangulate import triangulate

ap = argparse.ArgumentParser()
ap.add_argument("--prov", required=True); ap.add_argument("--photos", required=True)
ap.add_argument("--model", default=str(ROOT / "work/solve/model")); ap.add_argument("--out", default=None)
ap.add_argument("--res", type=float, default=0.2, help="strip resolution, provisional mm/px")
ap.add_argument("--band", default="2.5,5.5", help="tick band, mm in from the outer edge")
ap.add_argument("--min-amp", type=float, default=0.25, help="min comb amplitude relative to the photo's median")
ap.add_argument("--debug", default=None)
a = ap.parse_args()
cams = Cameras.load(a.model, metric=None)
pv = json.load(open(a.prov)); s0 = pv["s0"]
heel, e1, e2 = map(np.array, (pv["heel"], pv["e1"], pv["e2"]))
res = a.res; b0, b1 = map(float, a.band.split(","))
LEGS = {  # along-axis, across-axis (pointing into the steel from the outer edge), length in inches
    "tongue": (e1, -e2, 16), "body": (-e2, e1, 24)}
P0 = 3.175 / res  # nominal 1/8" in strip px


def strip(name, raw, along, across, L):
    pl = Plane(heel, along, across)   # u along the leg, v into the steel
    im = ortho(cams, name, pl, (-12 / s0, (L * 25.4 + 12) / s0), (-2 / s0, 14 / s0), res / s0, raw=raw)
    return pl, im[::-1]               # flip so row index increases with v (into the steel); row r -> v = -2 + r*res


def analyse(im):
    hsv = cv2.cvtColor(im, cv2.COLOR_BGR2HSV).astype(float)
    yellow = (np.abs(hsv[..., 0] - 28) < 9) & (hsv[..., 1] > 90) & (hsv[..., 2] > 110)
    g = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY).astype(float)
    r0, r1 = int((b0 + 2) / res), int((b1 + 2) / res)
    rows = slice(r0, r1)
    ok = yellow[rows].mean(0) > 0.6
    # edge-to-edge yellow extent check a bit deeper too (rules out occluders crossing the band)
    ok &= yellow[int(7 / res):int(11 / res)].mean(0) > 0.5
    p = g[rows].mean(0)
    p = p - cv2.GaussianBlur(p[None], (0, 0), 2 * P0)[0]
    p = -p * ok
    n = len(p); u = np.arange(n)
    W = int(round(25.4 / res)) | 1
    win = np.hanning(W)
    z = np.convolve(p * np.exp(-2j * np.pi * u / P0), win, "same")
    w = np.convolve(ok.astype(float), win, "same") / win.sum()
    amp = np.abs(z) / np.maximum(w, 1e-6) / win.sum()
    return p, ok, z, w, amp


def inch_marks(name, raw, leg):
    along, across, L = LEGS[leg]
    pl, im = strip(name, raw, along, across, L)
    p, ok, z, w, amp = analyse(im)
    n = len(p); u = np.arange(n)
    good = (w > 0.85) & (amp > a.min_amp * np.median(amp[w > 0.85]) if (w > 0.85).any() else False)
    if good.sum() < 3 * P0 * 8:
        return pl, im, {}, None
    # global comb: phase slope from the longest good run, then extend
    ph = np.angle(z)
    idx = np.flatnonzero(good)
    runs = np.split(idx, np.flatnonzero(np.diff(idx) > 1) + 1)
    run = max(runs, key=len)
    phu = np.unwrap(ph[run]); A = np.c_[run, np.ones(len(run))]
    beta, phi0 = np.linalg.lstsq(A, phu, rcond=None)[0]
    for _ in range(3):   # extend across gaps using the current line to pick the 2*pi branch
        pred = beta * idx + phi0
        phi_all = ph[idx] + 2 * np.pi * np.round((pred - ph[idx]) / (2 * np.pi))
        beta, phi0 = np.linalg.lstsq(np.c_[idx, np.ones(len(idx))], phi_all, rcond=None)[0]
    p_px = 1 / (1 / P0 + beta / (2 * np.pi))
    a_px = (-phi0 * p_px / (2 * np.pi)) % p_px
    # which comb teeth are whole inches: longest ticks -> darkest in a deeper band
    g = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY).astype(float)
    deep = g[int((8.8 + 2) / res):int((10.8 + 2) / res)].mean(0)
    deep = deep - cv2.GaussianBlur(deep[None], (0, 0), 2 * P0)[0]
    j = np.arange(int((n - a_px) / p_px))
    tu = a_px + p_px * j
    val = np.interp(tu, u, -deep) * np.interp(tu, u, good.astype(float))
    score = [val[r::8].sum() for r in range(8)]
    r8 = int(np.argmax(score))
    # absolute inch index: the heel's outer edge is at strip px u_h = 12/res (provisional, +-2 mm)
    u_h = 12 / res
    inch_px = 8 * p_px
    first = a_px + p_px * r8
    k0 = int(np.round((first - u_h) / inch_px))
    marks = {}
    for m in range(0, 40):
        k = k0 + m; uk = first + m * inch_px
        if k < 1 or uk >= n - 1: continue
        ui = int(round(uk))
        if not good[ui]: continue
        # local refinement from the local phase
        loc = (-ph[ui] * P0 / (2 * np.pi))
        cand = loc + P0 * np.round((uk - loc) / P0)
        if abs(cand - uk) > 0.3 * P0: continue
        v_mm = (b0 + b1) / 2
        X = pl.to3d([[(-12 + cand * res) / s0, v_mm / s0]])
        marks[k] = (cams[name].project(X)[0], float(amp[ui]))
    info = {"period_px": p_px, "inch_mm_prov": inch_px * res, "inch_residue_score": [round(float(s), 1) for s in score], "k0": k0,
            "n_good": int(good.sum())}
    return pl, im, marks, info


photos = [f"IMG_{p}.JPG" for p in a.photos.split(",")]
allmarks = {"tongue": {}, "body": {}}; infos = {}
for name in photos:
    raw = load_raw(cams, name)
    for leg in LEGS:
        pl, im, marks, info = inch_marks(name, raw, leg)
        infos[f"{name}:{leg}"] = info
        if a.debug:
            cv2.imwrite(f"{a.debug}/strip_{leg}_{name[4:8]}.png", im)
        for k, (uv, amp) in marks.items():
            if np.all(np.isfinite(uv)) and 0 <= uv[0] < 4032 and 0 <= uv[1] < 3024:
                allmarks[leg].setdefault(k, []).append((name, tuple(uv)))
        print(name[4:8], leg, "inches found:", sorted(marks), "| inch mm (prov):", None if not info else round(info["inch_mm_prov"], 3))
    del raw

out = {"legs": {}, "photos": a.photos}
lines = {}
for leg, mk in allmarks.items():
    ks, Xs, rms, nv = [], [], [], []
    for k in sorted(mk):
        if len(mk[k]) < 3: continue
        t = triangulate(cams, mk[k], outlier_px=4.0)
        if t.n_inliers < 3: continue
        ks.append(k); Xs.append(t.X); rms.append(t.rms_px); nv.append(t.n_inliers)
    ks = np.array(ks); Xs = np.array(Xs)
    c = Xs.mean(0); _, _, vt = np.linalg.svd(Xs - c); d = vt[0]
    tt = (Xs - c) @ d
    if np.polyfit(ks, tt, 1)[0] < 0: d, tt = -d, -tt
    slope, icpt = np.polyfit(ks, tt, 1)
    resid = tt - (slope * ks + icpt)
    perp = np.linalg.norm((Xs - c) - np.outer(tt, d), axis=1)
    mm_per_unit = 25.4 / slope
    # leave-one-out style slope uncertainty
    cov = np.sqrt(np.sum(resid ** 2) / (len(ks) - 2) / np.sum((ks - ks.mean()) ** 2))
    lines[leg] = (c, d, icpt, slope)
    out["legs"][leg] = {"inches": ks.tolist(), "n_views": nv, "tri_rms_px": [round(float(x), 2) for x in rms],
                        "mm_per_unit": mm_per_unit, "slope_rel_stderr_pct": 100 * cov / slope,
                        "along_resid_mm": [round(float(x * mm_per_unit), 3) for x in resid],
                        "perp_mm": [round(float(x * mm_per_unit), 3) for x in perp],
                        "points": Xs.tolist(), "dir": d.tolist()}
    print(f"\n{leg}: {len(ks)} inch marks (k {ks.min()}..{ks.max()}), views/mark {min(nv)}..{max(nv)}, tri rms px median {np.median(rms):.2f}")
    print(f"  mm per model unit = {mm_per_unit:.4f}  (slope stderr {100 * cov / slope:.3f} %)")
    print(f"  along-line residual: rms {np.std(resid) * mm_per_unit:.3f} mm, max {np.abs(resid).max() * mm_per_unit:.3f} mm; off-line rms {np.sqrt(np.mean(perp ** 2)) * mm_per_unit:.3f} mm")
if len(lines) == 2:
    dt, db = lines["tongue"][1], lines["body"][1]
    ang = np.degrees(np.arccos(abs(dt @ db)))
    s_t, s_b = out["legs"]["tongue"]["mm_per_unit"], out["legs"]["body"]["mm_per_unit"]
    print(f"\nangle between legs: {ang:.3f} deg; scale tongue vs body differ by {100 * (s_t - s_b) / s_b:+.3f} %")
    out["angle_deg"] = ang; out["scale_diff_pct"] = 100 * (s_t - s_b) / s_b
    allX = np.vstack([out["legs"]["tongue"]["points"], out["legs"]["body"]["points"]])
    c = allX.mean(0); _, sv, vt = np.linalg.svd(allX - c)
    out["plane_n"] = vt[2].tolist(); out["plane_c"] = c.tolist()
    out["coplanarity_rms_mm"] = float(np.std((allX - c) @ vt[2]) * (s_t + s_b) / 2)
    print(f"coplanarity of all inch marks: rms {out['coplanarity_rms_mm']:.3f} mm")
if a.out:
    json.dump(out, open(a.out, "w"), indent=1); json.dump(infos, open(a.out.replace(".json", "_info.json"), "w"), indent=1)
