"""USAGE: work/toolkit/rk.sh tools/seat_scoop/compare_lr.py      (after solve.py for both sides; then fit.py with the left solve, then fig_lr.py)
Left-side check of the seat scoop (PLAN 5b). Reads the two solved edges of each side (tools/seat_scoop/solve.py):
  R: tools/seat_scoop/inputs/solve.json   -> work/seat_scoop_L/R/solved_R.json   (identical to the PR #20 solve, plus the jackknife curves)
  L: tools/seat_scoop/inputs_L/solve.json -> work/seat_scoop_L/solved_L.json
and computes, with the SAME formulas as tools/seat_scoop/fit.py, the section quantities of each side, relative to that side's own
edge (so the 3-4 mm left/right lean of the chair in parts/lr_skew.json drops out):
  g      height of the hard line above that side's underside line (the lens)
  face   height of the vertical edge face: plan-sheet top arris z minus hard line z (parts/seat_edge.json)
  lean   hard line minus plan-sheet top arris, across (outboard +)
  angle  under-bevel angle below horizontal, hard line to bottom arris
  run    under-bevel width across (hard line to bottom arris)
plus the absolute heights (hard line z, bottom arris z) and |x|. Spread: jackknife over photos (each curve re-solved without each
photo, solve.py 'loo_xyz'); se = sqrt((n-1)/n * sum (q_i - q)^2), the two curves' parts added in quadrature.
Writes work/seat_scoop_L/compare.json, which fit.py (third argument = the left solve) copies into parts/seat_scoop.json as 'left_vs_right'."""
import sys, json, numpy as np
sys.path.insert(0, ".")
SOL = {"R": "work/seat_scoop_L/R/solved_R.json", "L": "work/seat_scoop_L/solved_L.json"}
E = json.load(open("parts/seat_edge.json")); TOL = 1.6
YS = np.arange(110.0, 441.0, 10.0)
def ip(A, y, i): A = np.array(A); A = A[np.argsort(A[:, 1])]; return np.interp(y, A[:, 1], A[:, i])

def quantities(C, B, side):
    """C, B: hard line and bottom arris xyz (every mm), x made positive outboard. Returns per-station arrays and scalars (fit.py formulas)."""
    P = np.array(E["left" if side == "L" else "right"]["top_arris_plan_xyz"]) * [-1 if side == "L" else 1, 1, 1]
    pb = np.polyfit(B[:, 1] - 250.0, B[:, 2], 1); line = lambda y: np.polyval(pb, np.asarray(y, float) - 250.0)
    g = C[:, 2] - line(C[:, 1])
    def tip(lo):
        m = (C[:, 1] <= C[0, 1] + 30) if lo else (C[:, 1] >= C[-1, 1] - 30); a, b = np.polyfit(C[m, 1], g[m], 1); return float(-b / a)
    yb = B[:, 1]; cx, cz = ip(C, yb, 0), ip(C, yb, 2); ang = np.degrees(np.arctan2(cz - B[:, 2], cx - B[:, 0])); core = (yb >= 150) & (yb <= 410)
    st = {}
    st["g"] = np.interp(YS, C[:, 1], g)
    st["hard_z"] = np.interp(YS, C[:, 1], C[:, 2]); st["hard_absx"] = np.interp(YS, C[:, 1], C[:, 0])
    st["bottom_z"] = np.interp(YS, B[:, 1], B[:, 2], left=np.nan); st["bottom_absx"] = np.interp(YS, B[:, 1], B[:, 0], left=np.nan)
    st["angle"] = np.interp(YS, yb, ang, left=np.nan); st["run"] = np.interp(YS, yb, cx - B[:, 0], left=np.nan)
    inp = (YS >= max(110.0, C[0, 1])) & (YS <= min(400.0, C[-1, 1]))
    st["face"] = np.where(inp, ip(P, YS, 2) - st["hard_z"], np.nan); st["lean"] = np.where(inp, st["hard_absx"] - ip(P, YS, 0), np.nan)
    sc = {"angle_median_y150_410": float(np.median(ang[core])), "g_max": float(g.max()), "y_of_g_max": float(C[g.argmax(), 1]),
          "back_tip_y": tip(True), "front_tip_y": tip(False), "underside_z_at_y250": float(pb[1]), "underside_tilt_deg": float(np.degrees(np.arctan(pb[0]))),
          "lean_mean_y110_400": float(np.nanmean(st["lean"])), "face_at_y250": float(np.interp(250, YS, st["face"]))}
    return st, sc

def side_result(side):
    S = json.load(open(SOL[side])); f = np.array([-1.0 if side == "L" else 1.0, 1, 1])
    C, B = np.array(S["crescent"]["xyz"]) * f, np.array(S["bottom"]["xyz"]) * f
    st, sc = quantities(C, B, side)
    var_st = {k: np.zeros_like(v) for k, v in st.items()}; var_sc = {k: 0.0 for k in sc}
    for curve in ("crescent", "bottom"):
        L = S[curve]["loo_xyz"]; n = len(L); qs = []
        for ph, xyz in L.items():
            X = np.array(xyz) * f; qs.append(quantities(X, B, side) if curve == "crescent" else quantities(C, X, side))
        for k in st:
            a = np.array([q[0][k] for q in qs]); var_st[k] += (n - 1) / n * np.sum((a - a.mean(0)) ** 2, 0)
        for k in sc:
            a = np.array([q[1][k] for q in qs]); var_sc[k] += (n - 1) / n * float(np.sum((a - a.mean()) ** 2))
    photos = {c: sorted(S[c]["photos"]) for c in ("crescent", "bottom")}
    rms = {c: [min(v["rms_mm"] for v in S[c]["photos"].values()), max(v["rms_mm"] for v in S[c]["photos"].values())] for c in ("crescent", "bottom")}
    loo = {c: [max(v[0] for v in S[c]["leave_one_out_mm"].values()), max(v[1] for v in S[c]["leave_one_out_mm"].values())] for c in ("crescent", "bottom")}
    return {"st": st, "se": {k: np.sqrt(v) for k, v in var_st.items()}, "sc": sc, "sc_se": {k: float(np.sqrt(v)) for k, v in var_sc.items()},
            "photos": photos, "rms": rms, "loo": loo, "C": C, "B": B}

R, L = side_result("R"), side_result("L")
r2 = lambda a: [None if not np.isfinite(v) else round(float(v), 2) for v in np.atleast_1d(a)]
names = {"g": "hard line above own underside", "face": "edge face height (top arris to hard line)", "lean": "hard line minus top arris, across (out +)",
         "angle": "under-bevel angle, deg", "run": "under-bevel width across", "hard_z": "hard line z (absolute)", "bottom_z": "bottom arris z (absolute)",
         "hard_absx": "hard line |x| (absolute)", "bottom_absx": "bottom arris |x| (absolute)"}
table = {}
print("station y:", " ".join(f"{y:6.0f}" for y in YS))
for k in names:
    d = L["st"][k] - R["st"][k]; se = np.sqrt(L["se"][k] ** 2 + R["se"][k] ** 2)
    table[k] = {"what": names[k], "left": r2(L["st"][k]), "right": r2(R["st"][k]), "left_minus_right": r2(d), "se_left": r2(L["se"][k]), "se_right": r2(R["se"][k]), "se_diff": r2(se)}
    print(f"-- {names[k]}"); print("   L    ", " ".join(f"{v:6.1f}" for v in L["st"][k])); print("   R    ", " ".join(f"{v:6.1f}" for v in R["st"][k]))
    print("   L-R  ", " ".join(f"{v:+6.1f}" for v in d)); print("   se   ", " ".join(f"{v:6.2f}" for v in se))
scal = {k: {"left": round(L["sc"][k], 2), "right": round(R["sc"][k], 2), "left_minus_right": round(L["sc"][k] - R["sc"][k], 2),
            "se_left": round(L["sc_se"][k], 2), "se_right": round(R["sc_se"][k], 2)} for k in L["sc"]}
print("-- scalars"); [print(f"   {k:24s} L {v['left']:8.2f} (se {v['se_left']:.2f})   R {v['right']:8.2f} (se {v['se_right']:.2f})   L-R {v['left_minus_right']:+.2f}") for k, v in scal.items()]
# verdict over the measured range of both sides, per quantity: worst |L-R| and where it is outside the 1.6 mm free-curve tolerance
shape = ("g", "face", "lean", "run")
verdict = {}
for k in list(shape) + ["angle", "hard_z", "bottom_z", "hard_absx", "bottom_absx"]:
    d = np.array(table[k]["left_minus_right"], dtype=float); se = np.array(table[k]["se_diff"], dtype=float); ok = np.isfinite(d)
    lim = 1.5 if k == "angle" else TOL
    out = [float(y) for y, v in zip(YS[ok], d[ok]) if abs(v) > lim]
    verdict[k] = {"max_abs_left_minus_right": round(float(np.max(np.abs(d[ok]))), 2), "at_y": float(YS[ok][np.argmax(np.abs(d[ok]))]), "rms": round(float(np.sqrt(np.mean(d[ok] ** 2))), 2),
                  "limit": lim, "stations_outside_limit": out, "beyond_2se": [float(y) for y, v, s in zip(YS[ok], d[ok], se[ok]) if abs(v) > 2 * s]}
print("-- verdict"); [print(f"   {k:12s} max |L-R| {v['max_abs_left_minus_right']:5.2f} at y {v['at_y']:.0f}  rms {v['rms']:.2f}  outside {v['limit']}: {v['stations_outside_limit']}") for k, v in verdict.items()]
res = {"stations_y": YS.tolist(), "table": table, "scalars": scal, "verdict": verdict,
       "photos": {"left": L["photos"], "right": R["photos"]}, "rms_mm_per_photo_range": {"left": L["rms"], "right": R["rms"]}, "leave_one_photo_out_max_mm_inner_whole": {"left": L["loo"], "right": R["loo"]},
       "curves_every_mm": {"left_hard_line_absx_y_z": np.round(L["C"], 2).tolist(), "left_bottom_arris_absx_y_z": np.round(L["B"], 2).tolist(), "right_hard_line_absx_y_z": np.round(R["C"], 2).tolist(), "right_bottom_arris_absx_y_z": np.round(R["B"], 2).tolist()}}
json.dump(res, open("work/seat_scoop_L/compare.json", "w"), indent=1); print("wrote work/seat_scoop_L/compare.json")
