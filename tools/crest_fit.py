"""USAGE: python -I tools/crest_fit.py [--dir work/parts/top/t] [--out parts/crest.json]
Collect the crest rail's four triangulated arrises (tools/curve_tri.py: crest_top_rear, crest_top_front, crest_bot_rear,
crest_bot_front) into parts/crest.json: left and right halves kept separate (mirror comparison), then a symmetric design version
(even polynomials in x), the simplest edge type within tolerance (single-radius arc or fair curve), sections, the joints with the
back legs (from parts/back_legs.json) and a provenance tag + tolerance on every number. Tiny compute."""
import sys, json, argparse
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import numpy as np
ap = argparse.ArgumentParser(); ap.add_argument("--dir", default="work/parts/top/t"); ap.add_argument("--out", default="parts/crest.json"); a = ap.parse_args()
D = ROOT / a.dir; IN = 25.4
def load(n):
    j = json.load(open(D / f"{n}.json")); X = np.array(j[n + "_xyz"]); return X[np.argsort(X[:, 0])], j[n + "_info"]
def frac(mm):
    v = mm / IN; s = "-" if v < 0 else ""; v = abs(v); w = int(v); f = round((v - w) * 32)
    if f == 32: w, f = w + 1, 0
    g = np.gcd(f, 32); return f"{s}{w}" + (f" {f // g}/{32 // g}" if f else "") + '"'
def dim(mm, prov, tol, note=""):
    return {"mm": round(float(mm), 1), "in": frac(mm), "provenance": prov, "tol_mm": tol, **({"note": note} if note else {})}

TR, iTR = load("crest_top_rear"); TF, iTF = load("crest_top_front"); BR, iBR = load("crest_bot_rear"); BF, iBF = load("crest_bot_front")
lean = json.load(open(D / "rear_bot_guess.json"))["lean_slope"]
X0 = 212.0                                                          # common x range of all four arrises (between the legs)

def even_fit(X, col, xmax, deg=4):
    m = np.abs(X[:, 0]) <= xmax; x = np.abs(X[m, 0]); A = np.stack([x ** k for k in range(0, deg + 1, 2)], 1)
    c = np.linalg.lstsq(A, X[m, col], rcond=None)[0]; r = X[m, col] - A @ c
    return c, r, X[m, 0]
def ev(c, x): x = np.abs(np.asarray(x, float)); return sum(ck * x ** (2 * k) for k, ck in enumerate(c))
def arc_fit(x, y):
    """circle through (x, y) symmetric about x = 0: centre (0, yc); returns radius, centre, max deviation"""
    A = np.c_[2 * y, np.ones(len(y))]; b = x ** 2 + y ** 2; (yc, k), *_ = np.linalg.lstsq(A, b, rcond=None); R = np.sqrt(k + yc ** 2)
    yy = yc + np.sign(np.mean(y) - yc) * np.sqrt(np.maximum(R ** 2 - x ** 2, 0)); return float(R), float(yc), float(np.abs(yy - y).max())

edges = {"top_rear": (TR, iTR), "top_front": (TF, iTF), "bottom_rear": (BR, iBR), "bottom_front": (BF, iBF)}
out = {"part": "CREST", "frame": "chair frame mm (+X right, +Y forward, +Z up; origin table top under seat front centre)",
       "method": "each arris triangulated as a 3D curve x -> (y, z) from per-photo traces on an overhead sheet (z const) and a rear sheet (y const), "
                 "only photos that cannot see the adjoining face (tools/edge_tri.py traces + tools/curve_tri.py joint solve)", "edges": {}}
sym = {}
for nm, (X, info) in edges.items():
    xmax = 249.0 if nm == "top_rear" else X0
    cy, ry, xs = even_fit(X, 1, xmax); cz, rz, _ = even_fit(X, 2, xmax)
    xl = np.arange(20, min(xmax, -X[0, 0], X[-1, 0]) + 1e-9, 2.0)
    yl, yr = np.interp(-xl, X[:, 0], X[:, 1]), np.interp(xl, X[:, 0], X[:, 1]); zl, zr = np.interp(-xl, X[:, 0], X[:, 2]), np.interp(xl, X[:, 0], X[:, 2])
    src = {"top_rear": "triangulated (overhead 1545,1547,1548,1549 + rear 1502,1501,1503; y and z both solved)",
           "top_front": "triangulated in plan (1545 tone line, 1544 and 1542 outlines agree to ~1 mm); z = top_rear z + 4.4 mm (top face assumed square to the rail's lean)",
           "bottom_rear": "z triangulated (rear 1502,1501,1503 tone line); y assumed = back face carried down from top_rear along the back legs' lean (crest back face flush with the leg backs, IMG_1540)",
           "bottom_front": "triangulated in plan (1545 front outline; cross-checked from 1547,1548,1549 on a z=1005 sheet: agree within 0.7 mm); z = bottom_rear z + 4.4 mm (assumed)"}[nm]
    tol = {"top_rear": 1.0, "top_front": 1.6, "bottom_rear": 1.6, "bottom_front": 1.6}[nm]
    sig = {k: v for k, v in info.items() if k.startswith("sigma")}
    out["edges"][nm] = {"provenance": src, "tol_mm": tol, "photo_residuals_mm": {p["photo"]: round(p["inlier_rms_mm"] or -1, 2) for p in info["photos"]}, "solve_sigma_mm": sig,
                        "left_xyz": X[X[:, 0] < 0][::5].round(2).tolist(), "right_xyz": X[X[:, 0] >= 0][::5].round(2).tolist(),
                        "left_vs_right_mirror_mm": {"y_rms": float(np.sqrt(np.mean((yl - yr) ** 2))), "y_max": float(np.abs(yl - yr).max()), "z_rms": float(np.sqrt(np.mean((zl - zr) ** 2))), "z_max": float(np.abs(zl - zr).max())},
                        "design": {"y_even_poly": cy.tolist(), "z_even_poly": cz.tolist(), "valid_abs_x_mm": xmax, "form": "y = sum c_k |x|^(2k), k = 0..2",
                                   "fit_resid_rms_mm": {"y": float(np.sqrt(np.mean(ry ** 2))), "z": float(np.sqrt(np.mean(rz ** 2)))}}}
    sym[nm] = (cy, cz)

# simplest edge type: arcs for the plan bow and the top arch
xs = np.linspace(-X0, X0, 213)
Rp, ycp, devp = arc_fit(xs, ev(sym["top_rear"][0], xs)); Rpf, _, devpf = arc_fit(xs, ev(sym["top_front"][0], xs))
xa = np.linspace(-249, 249, 250); Ra, zca, deva = arc_fit(xa, ev(sym["top_rear"][1], xa)); xb_ = np.linspace(-X0, X0, 213); Rb, zcb, devb = arc_fit(xb_, ev(sym["bottom_rear"][1], xb_))
out["edge_types"] = {
    "plan_back_face_top": {"type": "arc" if devp <= 1.6 else "fair curve", "radius_mm": round(Rp, 0), "radius_in": frac(Rp), "max_dev_of_arc_mm": round(devp, 2)},
    "plan_front_face_top": {"type": "arc" if devpf <= 1.6 else "fair curve", "radius_mm": round(Rpf, 0), "max_dev_of_arc_mm": round(devpf, 2)},
    "top_arch_elevation": {"type": "arc" if deva <= 1.6 else "fair curve", "radius_mm": round(Ra, 0), "radius_in": frac(Ra), "max_dev_of_arc_mm": round(deva, 2), "span_abs_x_mm": 249},
    "bottom_arch_elevation": {"type": "arc" if devb <= 1.6 else "fair curve", "radius_mm": round(Rb, 0), "max_dev_of_arc_mm": round(devb, 2)}}

def section(x):
    p = {k: np.array([x, ev(sym[k][0], x), ev(sym[k][1], x)]) for k in sym}
    back = p["top_rear"] - p["bottom_rear"]; nb = back / np.linalg.norm(back); perp = np.array([0, nb[2], -nb[1]])   # forward-ish normal to the back face in the section
    t_top = abs((p["top_front"] - p["top_rear"]) @ perp); t_bot = abs((p["bottom_front"] - p["bottom_rear"]) @ perp)
    front = p["top_front"] - p["bottom_front"]
    return p, {"height_back_face": float(np.linalg.norm(back)), "height_front_face": float(np.linalg.norm(front)), "plan_width_top": float(p["top_front"][1] - p["top_rear"][1]),
               "plan_width_bottom": float(p["bottom_front"][1] - p["bottom_rear"][1]), "thickness_top_perp": float(t_top), "thickness_bottom_perp": float(t_bot),
               "front_face_lean_deg": float(np.degrees(np.arctan2(-front[1], front[2]))), "back_face_lean_deg": float(np.degrees(np.arctan(lean)))}
S0 = section(0.0)[1]; S2 = section(X0)[1]; Stape = section(-75.0)[1]
out["section"] = {
    "height_back_face_centre": dim(S0["height_back_face"], "triangulated", 1.6, "top_rear to bottom_rear along the back face"),
    "height_back_face_at_joint": dim(S2["height_back_face"], "triangulated", 1.6),
    "height_tape_check": {"tape_IMG_1555_mm": 77.5, "tape_tol_mm": 1.6, "model_at_x-75_mm": round(Stape["height_back_face"], 1), "diff_mm": round(Stape["height_back_face"] - 77.5, 1),
                          "note": "tape hooked over the ROUNDED top edge (hook seat uncertain, per the tape notes): a tape over a rounded arris reads long"},
    "plan_width_top_centre": dim(S0["plan_width_top"], "triangulated", 1.6), "plan_width_top_at_joint": dim(S2["plan_width_top"], "triangulated", 1.6),
    "plan_width_bottom_centre": dim(S0["plan_width_bottom"], "fitted", 1.6, "bottom_rear y assumed from the lean"), "plan_width_bottom_at_joint": dim(S2["plan_width_bottom"], "fitted", 1.6),
    "thickness_top": dim(S0["thickness_top_perp"], "triangulated", 1.6, "perpendicular to the back face"), "thickness_bottom": dim(S0["thickness_bottom_perp"], "fitted", 2.0, "perpendicular to the back face; the rail tapers, thicker at the bottom"),
    "back_face_lean_deg": {"deg": round(S0["back_face_lean_deg"], 1), "provenance": "assumed = back legs' rear arris over z 980-1080 (parts/back_profile.json blegs_back3)", "tol_deg": 1.5},
    "front_face_lean_deg": {"deg": round(S0["front_face_lean_deg"], 1), "note": "positive = top leans back, like the back face", "provenance": "triangulated (top_front and bottom_front plan positions, z from the rear view)", "tol_deg": 2.0},
    "per_station": {f"x{int(x)}": {k: round(v, 1) for k, v in section(float(x))[1].items()} for x in (-200, -100, 0, 100, 200)}}
zt0 = ev(sym["top_rear"][1], 0.0)
out["key_points"] = {"top_centre_z": dim(zt0, "triangulated", 1.0, "rear top arris at x = 0"), "top_at_leg_outer_z": dim(ev(sym["top_rear"][1], 249.0), "triangulated", 1.6, "arch carried over the leg tops"),
                     "arch_rise_over_leg_tops": dim(zt0 - ev(sym["top_rear"][1], 249.0), "triangulated", 1.6), "bottom_centre_z": dim(ev(sym["bottom_rear"][1], 0.0), "triangulated", 1.0),
                     "bow_back_face_top": dim(ev(sym["top_rear"][0], 212.0) - ev(sym["top_rear"][0], 0.0), "triangulated", 1.0, "plan: centre sits this far behind the line between the joints"),
                     "back_face_top_y_centre": dim(ev(sym["top_rear"][0], 0.0), "triangulated", 1.0)}

# joints with the back legs: inner/outer leg edges at the crest's height, from the back-view leg traces
BL = json.load(open(ROOT / "parts/back_legs.json")); tb = np.array(BL["sheet"]["table"]); st = np.r_[0, np.cumsum(np.hypot(np.diff(tb[:, 0]), np.diff(tb[:, 1])))]
def leg_x(key, z):
    v = float(np.interp(z, tb[:, 0], st)) + max(0.0, z - tb[-1, 0]); return float(np.polyval(BL["fits"][key]["coef"], v))
zmid = float(ev(sym["bottom_rear"][1], X0) + ev(sym["top_rear"][1], X0)) / 2
jt = {}
for side, sgn in (("left", -1), ("right", 1)):
    k = "L" if side == "left" else "R"
    xi, xo = leg_x(f"bleg{k}_in", zmid), leg_x(f"bleg{k}_out", zmid)
    jt[side] = {"leg_inner_face_x": dim(xi, "triangulated" if BL["fits"][f"bleg{k}_in"]["triangulated"] else "fitted", 0.8, "back-view leg edge (parts/back_legs.json) extrapolated to the crest's mid height"),
                "leg_outer_face_x": dim(xo, "triangulated" if BL["fits"][f"bleg{k}_out"]["triangulated"] else "fitted", 0.8),
                "crest_shoulder_length_from_centre": dim(abs(xi), "fitted", 0.8, "visible crest length = between the legs' inner faces")}
dsx = (abs(jt["left"]["leg_inner_face_x"]["mm"]) + abs(jt["right"]["leg_inner_face_x"]["mm"])) / 2
out["joints"] = {**jt, "design_shoulder_half_length": dim(dsx, "fitted", 0.8, "L/R mean"), "shoulder_to_shoulder": dim(2 * dsx, "fitted", 0.8),
                 "z_mid_mm": round(zmid, 1),
                 "leg_tops": dim(ev(sym["top_rear"][1], 236.0), "triangulated", 1.6, "z at the leg centre: the legs end flush with the crest top and the arch runs on over them (IMG_1502, 1513, 1540); in model v3 they stood up past the crest"),
                 "faces": {"back": "flush with the back legs' back faces (IMG_1540; assumed exactly flush)", "front": "flush with the leg front at the top (overhead 1544/1545: leg top end grain 24-26 mm deep, same as the crest top face)", "provenance": "fitted (by eye on the overhead and rear orthophotos)", "tol_mm": 1.6},
                 "joinery": "NOT visible (no seam shows on the top or back faces beyond the end grain): treat as a mortise and tenon or bridle between the legs; tenon length assumed by the maker",
                 "seam_seen_overhead_x_mm": {"left": -216, "right": 222, "provenance": "fitted (by eye on overhead 1544/1545 zooms, plane z 1078: +-3 mm of parallax at the ends)"}}
out["summary_design"] = {"rail": "arched, bowed, tapered rail between the back legs; back face leans with the legs; top and bottom arched in elevation, back bowed in plan",
                         "top_arch_radius_mm": round(Ra, 0), "plan_bow_radius_mm": round(Rp, 0), "height_mm": round(S0["height_back_face"], 1), "thickness_top_mm": round(S0["thickness_top_perp"], 1), "thickness_bottom_mm": round(S0["thickness_bottom_perp"], 1)}
json.dump(out, open(ROOT / a.out, "w"), indent=1)
print(json.dumps({k: out[k] for k in ("edge_types", "key_points", "summary_design")}, indent=1))
print(json.dumps({k: v for k, v in out["section"].items() if k != "per_station"}, indent=0)[:2500]); print(json.dumps(out["section"]["per_station"]))
print({k: v["left_vs_right_mirror_mm"] for k, v in out["edges"].items()}); print({s: {k: v["mm"] for k, v in out["joints"][s].items()} for s in ("left", "right")}, out["joints"]["leg_tops"]["mm"])
