"""USAGE: python -I tools/arm_fit.py [--dir work/parts/top/ta] [--out parts/arms.json]
Assemble parts/arms.json from the per-edge triangulations of the two arms (tools/edge_tri.py on the overhead arm sheets
work/parts/top/aR, aL and the front-end sheets fR, fL):
  arm{R,L}_out.json            outer top arris, depth solved (clean cameras on the chair's far side, wide baseline)
  arm{R,L}_in_d{0,-6,6}.json   inner top arris at three fixed depths (its clean cameras all stand on one side, baseline too
                               short to solve depth): the depth is taken from the outer arris at the same station, i.e.
                               the arm top is assumed flat ACROSS its width; the d=+/-6 runs give the sensitivity
  arm{R,L}_front_dside.json    front-end top arris, depth fixed to the side arrises' depth at the front (the free solve
                               put it 7-13 mm deeper, which disagrees with the side arrises and the point cloud)
Writes each arm separately (chair frame, mm), a left/right comparison, and a symmetric design version (mean of the right
arm and the mirrored left arm, smooth polynomials in y). Every number carries provenance and a tolerance. Tiny compute."""
import sys, json, argparse
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
import numpy as np

ap = argparse.ArgumentParser(); ap.add_argument("--dir", default=str(ROOT / "work/parts/top/ta")); ap.add_argument("--out", default=str(ROOT / "parts/arms.json"))
a = ap.parse_args(); D = Path(a.dir)
C = np.load(ROOT / "work/dense/chair_dense.npy")[:, :3]
J = lambda f: json.load(open(D / f))
r1 = lambda v, n=1: [round(float(x), n) for x in v]


def by_y(X):
    X = np.asarray(X, float); return X[np.argsort(X[:, 1])]


def at_y(X, y, col):
    return np.interp(y, X[:, 1], X[:, col])


def arm(s):
    O = J(f"arm{s}_out.json"); Xo = np.array(O[f"arm{s}_out_xyz"]); do = np.array(O[f"arm{s}_out_depth_mm"]); vo = np.array(O[f"arm{s}_out"])[:, 1]
    I0, Im, Ip = (np.array(J(f"arm{s}_in_d{d}.json")[f"arm{s}_in_xyz"]) for d in ("0", "-6", "6"))
    vi = np.array(J(f"arm{s}_in_d0.json")[f"arm{s}_in"])[:, 1]; o = np.argsort(vo); d_in = np.interp(vi, vo[o], do[o])
    Xi = I0 + (Ip - Im) / 12.0 * d_in[:, None]                       # linear in depth (exact enough for |d| < 13 mm)
    sens = np.linalg.norm((Ip - Im)[:, :2], axis=1) / 12.0             # plan movement per mm of depth error
    Fd = J(f"arm{s}_front_dside.json"); Xf = np.array(Fd[f"arm{s}_front_xyz"]); Fx0 = Xf.copy(); Ff = np.array(J(f"arm{s}_front.json")[f"arm{s}_front_xyz"])
    Xo, Xi = by_y(Xo), by_y(Xi)
    # trim the side arrises where they meet the front arris (in plan) and close the outline there
    Xf = Xf[np.argsort(Xf[:, 0])]
    yf = lambda x: np.interp(x, Xf[:, 0], Xf[:, 1]); zf = lambda x: np.interp(x, Xf[:, 0], Xf[:, 2])

    def corner(X):
        g = X[:, 1] - yf(X[:, 0]); k = np.where(np.diff(np.sign(g)) != 0)[0]
        if len(k): i = k[-1]; t = g[i] / (g[i] - g[i + 1]); P = X[i] + t * (X[i + 1] - X[i]); return P, X[: i + 1]
        P = X[-1].copy(); P[1] = yf(P[0]); return P, X                       # extrapolate straight to the front line

    Po, Xo_t = corner(Xo); Pi, Xi_t = corner(Xi)
    xa, xb = sorted([Pi[0], Po[0]]); m = (Xf[:, 0] > xa) & (Xf[:, 0] < xb); front = np.r_[[Pi], Xf[m] if Pi[0] < Po[0] else Xf[m][::-1], [Po]]
    outline = np.r_[Xi_t, [Pi], front[1:-1], [Po], Xo_t[::-1]]
    ys = np.arange(80, 501, 20.0); st = []
    for y in ys:
        xi, xo = at_y(Xi_t, y, 0), at_y(Xo_t, y, 0); zi, zo = at_y(Xi_t, y, 2), at_y(Xo_t, y, 2); lo, hi = sorted((xi, xo))
        mm = (C[:, 0] > lo + 3) & (C[:, 0] < hi - 3) & (np.abs(C[:, 1] - y) < 8) & (C[:, 2] > 450) & (C[:, 2] < max(zi, zo) + 25)
        zc = float(np.percentile(C[mm, 2], 90)) if mm.sum() >= 5 else None
        st.append({"y": float(y), "x_inner": round(float(xi), 1), "x_outer": round(float(xo), 1), "width": round(float(abs(xo - xi)), 1),
                   "z_top_inner": round(float(zi), 1), "z_top_outer": round(float(zo), 1), "z_cloud_p90": None if zc is None else round(zc, 1), "cloud_n": int(mm.sum())})
    back_y = float(min(Xi_t[0, 1], Xo_t[0, 1]))
    return dict(Xo=Xo_t, Xi=Xi_t, Xf=front, Po=Po, Pi=Pi, outline=outline, st=st, back_y=back_y, sens=float(np.median(sens)), sens_max=float(sens.max()),
                d_out=[float(do.min()), float(do.max())], info_out=O[f"arm{s}_out_info"], front_free_vs_fixed=r1(np.mean(Ff - Fx0, 0)[1:]))


R, Lf = arm("R"), arm("L")
mir = lambda X: np.asarray(X) * [-1, 1, 1]

# ---- left / right comparison at the stations
cmp_ = []
for sr, sl in zip(R["st"], Lf["st"]):
    cmp_.append({"y": sr["y"], "d_inner_mm": round(sr["x_inner"] + sl["x_inner"], 1), "d_outer_mm": round(sr["x_outer"] + sl["x_outer"], 1),
                 "d_width_mm": round(sr["width"] - sl["width"], 1), "d_z_mm": round((sr["z_top_inner"] + sr["z_top_outer"] - sl["z_top_inner"] - sl["z_top_outer"]) / 2, 1)})
rms = lambda k: round(float(np.sqrt(np.mean([c[k] ** 2 for c in cmp_]))), 2)

# ---- symmetric design (right-hand arm; the left is its mirror image)
yd = np.arange(max(R["back_y"], Lf["back_y"]), min(R["Pi"][1], -0 + Lf["Pi"][1], R["Po"][1], Lf["Po"][1]) + 1e-9, 2.0)
def avg(col, edge):
    # left inner arris behind y ~ 180 traced on shading a few mm inside the edge (by eye, 1547-1549): use the right arm there
    wl = np.clip((yd - 140) / 40, 0, 1) if (edge == "Xi" and col == 0) else np.full(len(yd), 1.0)
    return (at_y(R[edge], yd, col) * (2 - wl) + at_y(mir(Lf[edge]), yd, col) * wl) / 2
xin, xout = avg(0, "Xi"), avg(0, "Xo"); zin, zout = avg(2, "Xi"), avg(2, "Xo")
fit = lambda y, v, deg: np.polyfit(y - 300, v, deg)
c_in, c_out = fit(yd, xin, 3), fit(yd, xout, 3); c_z = fit(yd, (zin + zout) / 2, 2); c_zx = fit(yd, zout - zin, 1)
res_in = float(np.sqrt(np.mean((np.polyval(c_in, yd - 300) - xin) ** 2))); res_out = float(np.sqrt(np.mean((np.polyval(c_out, yd - 300) - xout) ** 2)))
res_z = float(np.sqrt(np.mean((np.polyval(c_z, yd - 300) - (zin + zout) / 2) ** 2)))
FR = R["Xf"]; FL = mir(Lf["Xf"]); F = np.r_[FR, FL]; cf = np.polyfit(F[:, 0], F[:, 1], 1); cfz = np.polyfit(F[:, 0], F[:, 2], 1)
front_res = float(np.sqrt(np.mean((np.polyval(cf, F[:, 0]) - F[:, 1]) ** 2)))
# design corners: front line meets the inner / outer curves
def meet(c):
    y = 500.0
    for _ in range(30): x = np.polyval(c, y - 300); y = np.polyval(cf, x)
    return [x, y]
ci, co = meet(c_in), meet(c_out)
yb = float(yd[0])
yin = np.linspace(yb, ci[1], 40); yout = np.linspace(yb, co[1], 40); xf = np.linspace(ci[0], co[0], 12)
design_outline = np.r_[np.c_[np.polyval(c_in, yin - 300), yin], np.c_[xf, np.polyval(cf, xf)], np.c_[np.polyval(c_out, yout[::-1] - 300), yout[::-1]]]
zt = lambda y: np.polyval(c_z, y - 300)

TJ, TC = 0.8, 1.6
def side_json(A, s):
    io = A["info_out"]
    return {
        "outer_top_arris_xyz": [r1(p) for p in A["Xo"][::5]],
        "inner_top_arris_xyz": [r1(p) for p in A["Xi"][::5]],
        "front_top_arris_xyz": [r1(p) for p in A["Xf"]],
        "corners": {"front_inner": r1(A["Pi"]), "front_outer": r1(A["Po"])},
        "plan_outline_xy": [r1(p[:2]) for p in A["outline"][::3]],
        "stations": A["st"],
        "provenance": {
            "outer": f"triangulated (edge_tri, clean photos {','.join(io['photos'])}, depth solved, residual {io['residual_rms_mm']:.2f} mm rms)",
            "inner": "triangulated (edge_tri, clean photos on one side only; depth taken from the outer arris at the same station = top assumed flat across the width)",
            "front": "triangulated (edge_tri on a front-end sheet, all 7-8 photos clean; depth fixed to the side arrises' front depth)",
            "z": "triangulated (edge depths); checked against the dense cloud per station (z_cloud_p90)",
            "back_end": "OPEN: the arm runs on into the back leg below the photos' view; the traces stop at y = %.0f" % A["back_y"]},
        "tolerance_mm": {
            "outer_plan": round(max(TC, 2 * io["residual_rms_mm"]), 1),
            "inner_plan": round(max(TC, A["sens"] * 3 + 0.5), 1),
            "front_along_arm_y": 2.5,
            "z_top": 2.0},
        "front_free_depth_solve_minus_adopted_mm": {"dy": A["front_free_vs_fixed"][0], "dz": A["front_free_vs_fixed"][1]},
        "outer_arris_depth_off_sheet_mm": r1(A["d_out"]),
        "inner_plan_shift_per_mm_depth": round(A["sens"], 2)}


out = {
    "frame": "chair frame, mm: origin on the table top under the seat-front centre, +X chair's right, +Y forward, +Z up",
    "method": "Overhead photos rectified onto a sheet laid on each arm's top face (tools/face_ortho.py --optimize). Each top arris traced only in photos that cannot see that arris's side face, and triangulated on its own (tools/edge_tri.py). Front ends on a second sheet with swapped axes. Assembled by tools/arm_fit.py.",
    "right": side_json(R, "R"), "left": side_json(Lf, "L"),
    "left_vs_right": {"note": "d_inner/d_outer = x_right + x_left (0 = mirror images); d_z = right minus left top height",
                      "stations": cmp_, "rms_mm": {"inner": rms("d_inner_mm"), "outer": rms("d_outer_mm"), "width": rms("d_width_mm"), "z": rms("d_z_mm")}},
    "design": {
        "note": "symmetric design version: mean of the right arm and the mirrored left arm; right arm given, the left is x -> -x",
        "y_back": round(yb, 1), "inner_x_of_y": {"poly_in_(y-300)": r1(c_in, 8), "fit_rms_mm": round(res_in, 2)},
        "outer_x_of_y": {"poly_in_(y-300)": r1(c_out, 8), "fit_rms_mm": round(res_out, 2)},
        "front_y_of_x": {"poly": r1(cf, 6), "fit_rms_mm": round(front_res, 2), "note": "front end is a straight line in plan (measured ends lie within fit_rms of it)"},
        "top_z_of_y": {"poly_in_(y-300)": r1(c_z, 8), "fit_rms_mm": round(res_z, 2), "cross_slope_outer_minus_inner_poly": r1(c_zx, 6)},
        "front_z_of_x": r1(cfz, 6),
        "corners": {"front_inner": r1(ci), "front_outer": r1(co)},
        "plan_outline_xy": [r1(p) for p in design_outline],
        "key": {"width_at_y": {str(int(y)): round(float(np.polyval(c_out, y - 300) - np.polyval(c_in, y - 300)), 1) for y in (100, 200, 300, 400, 480)},
                "top_z_at_y": {str(int(y)): round(float(zt(y)), 1) for y in (100, 200, 300, 400, 480)},
                "slope_deg_at_y": {str(int(y)): round(float(np.degrees(np.arctan(np.polyval(np.polyder(c_z), y - 300)))), 1) for y in (100, 300, 480)}},
        "provenance": "fitted (to the triangulated edges of both arms)",
        "tolerance_mm": "plan: max(1.6, half the left/right difference at that station), see left_vs_right; top z 2.0"},
    "thickness": {"value_mm": 25.0, "provenance": "assumed (not measured; no photo here sees the arm's underside edge cleanly)", "tolerance_mm": 3.0},
    "open": ["left inner arris behind y ~ 180: the traces in 1547-1549 follow a shading line that sits ~4-5 mm inside the edge, which shows as most of the 11 mm left/right difference there; the design uses the right arm for y < 140",
             "both arms sit ~3.6 mm to +x and the left is ~5 mm higher at the front (y > 340): a real asymmetry or a slight roll of the chair frame; the design averages it out",
             "the back end where each arm meets the back leg is not seen from above (traces stop at y ~ 66)",
             "arm thickness assumed 25 mm",
             "the inner arrises assume the top is flat across the width (their depth comes from the outer arris)",
             "front-end position along the arm: +/-2.5 mm (depth-limited), beyond the 1/32\" joint target"],
}
json.dump(out, open(a.out, "w"), indent=1)
k = out["design"]["key"]; lr = out["left_vs_right"]["rms_mm"]
print("R front corners", r1(R["Pi"]), r1(R["Po"]), " L", r1(Lf["Pi"]), r1(Lf["Po"]))
print("design width", k["width_at_y"], " top z", k["top_z_at_y"], " slope", k["slope_deg_at_y"])
print("design fit rms in/out/z/front", round(res_in, 2), round(res_out, 2), round(res_z, 2), round(front_res, 2), " L/R rms", lr)
print("front free-minus-adopted R", R["front_free_vs_fixed"], " L", Lf["front_free_vs_fixed"], " inner sens R/L", round(R["sens"], 2), round(Lf["sens"], 2))
