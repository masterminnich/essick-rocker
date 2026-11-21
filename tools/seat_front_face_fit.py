"""USAGE: python -I tools/seat_front_face_fit.py [--out parts/seat_front_face.json]
Assemble the seat's FRONT FACE (the section of the front edge) from two sets of solves of tools/tube_tri.py, seeds
parts/seat_front_face_seeds.json:
  work/parts/seatF/face_top/top{R,L}.json        the rolled TOP edge, overhead photos (plan sheet) + level and low front photos
                                                 (vertical sheet) in one solve, radius 8 given
  work/parts/seatF/face_bottom/bottom{R,L}.json  the BOTTOM arris of the front face (a sharp line: radius 1), nine front photos
and their variants (work/parts/seatF/face_top_<tag>/, face_bottom_<tag>/). Output: raw right and left lines, their mirror
comparison, a symmetric design (mean of right and mirrored left): height of the top of the roll, plan outline, bottom arris in
plan and height, face height and lean; how far each moves when an assumption changes; checks against parts/seat_front.json (the
plan outline from the overhead photos alone) and the seat session's tape dots on the face (seat/front_face.csv), not used here.
Tiny compute (a few hundred points)."""
import json, argparse, csv
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parent.parent
ap = argparse.ArgumentParser(); ap.add_argument("--out", default=str(ROOT / "parts/seat_front_face.json")); a = ap.parse_args()
W = ROOT / "work/parts/seatF"; X0, X1, XC, R = 8.0, 262.0, 268.0, 8.0
xs = np.arange(X0, X1 + 1e-9, 2.0)
# bottom corner: read on the 5 mm grid of the rectified level photo IMG_1558 (sheet through y 525; the corner is 9 mm in front of it, parallax under 1 mm)
CORNER_BOTTOM_Z = 398.0


def line(path, ykey, zkey):
    t = json.load(open(path)); x = np.abs(np.array(t["x"])); k = np.argsort(x)
    y = np.array(t["plan_outline_xy"])[:, 1] if ykey == "plan" else np.array(t[ykey]); xo = np.abs(np.array(t["plan_outline_xy"])[:, 0]) if ykey == "plan" else x; ko = np.argsort(xo)
    return np.interp(xs, xo[ko], y[ko]), np.interp(xs, x[k], np.array(t[zkey])[k]), t


def load(dt, db):
    o = {}
    for s in "RL":
        if dt: o["ty" + s], o["tz" + s], o["tt" + s] = line(W / dt / f"top{s}.json", "plan", "top_of_roll_z")
        if db: o["by" + s], o["bz" + s], o["bt" + s] = line(W / db / f"bottom{s}.json", "spine_y", "spine_z")
    return o


A = load("face_top", "face_bottom"); m = lambda k: (A[k + "R"] + A[k + "L"]) / 2
ty, tz, by, bz = m("ty"), m("tz"), m("by"), m("bz")
st = lambda v: {"mean": round(float(np.mean(v)), 2), "sd": round(float(np.std(v)), 2), "min": round(float(np.min(v)), 1), "max": round(float(np.max(v)), 1)}
tab = lambda v, n=1: [[float(x), round(float(q), n)] for x, q in zip(xs, v)]
sub = lambda v: [[float(x), round(float(q), 1)] for x, q in zip(xs[::8], v[::8])]
at = lambda v: {str(int(x)): round(float(q), 1) for x, q in zip(xs[::16], v[::16])}
F0 = json.load(open(ROOT / "parts/seat_front.json"))["design"]; f0 = np.array(F0["front_y_of_abs_x"]); y0 = np.interp(xs, f0[:, 0], f0[:, 1])
height = tz - bz; lean = by - ty
# variants: movement of the design lines (mean of right and left) over |x| 8-262
var = {"top_roll": {}, "bottom_arris": {}}
for p in sorted(W.glob("face_top_*")):
    if (p / "topR.json").exists() and (p / "topL.json").exists():
        B = load(p.name, None); var["top_roll"][p.name[9:]] = {"top_z_moves_mm": st((B["tzR"] + B["tzL"]) / 2 - tz), "plan_outline_moves_mm": st((B["tyR"] + B["tyL"]) / 2 - ty),
                                                               "top_z_moves_abs_x_70_to_262_mm": st(((B["tzR"] + B["tzL"]) / 2 - tz)[xs >= 70]), "residual_rms_mm": {s: round(B["tt" + s]["residual_rms_mm"], 2) for s in "RL"}}
for p in sorted(W.glob("face_bottom_*")):
    if (p / "bottomR.json").exists() and (p / "bottomL.json").exists():
        B = load(None, p.name); var["bottom_arris"][p.name[12:]] = {"bottom_z_moves_mm": st((B["bzR"] + B["bzL"]) / 2 - bz), "bottom_y_moves_mm": st((B["byR"] + B["byL"]) / 2 - by),
                                                                     "residual_rms_mm": {s: round(B["bt" + s]["residual_rms_mm"], 2) for s in "RL"}}
# tape dots on the front face (seat session, not used in any solve): a dot must lie between the bottom arris and the top of the roll, and on a vertical face it lies on the plan outline
dots = [(int(r["id"]), float(r["x_mm"]), float(r["y_mm"]), float(r["z_mm"]), float(r["top_surface_z_above_mm"])) for r in csv.DictReader(open(ROOT / "seat/front_face.csv"))]
ip = lambda v, x: float(np.interp(abs(x), xs, v))
face = [{"dot": i, "x": x, "y": y, "z": z, "above_bottom_arris_mm": round(z - ip(A["bzR"], x), 1), "below_top_of_roll_mm": round(ip(A["tzR"], x) - z, 1), "seat_session_says_below_top_mm": d,
         "top_outline_minus_dot_y_mm": round(ip(A["tyR"], x) - y, 1), "bottom_arris_minus_dot_y_mm": round(ip(A["byR"], x) - y, 1)} for i, x, y, z, d in dots if X0 <= x <= X1]
# tape dots on the seat TOP that sit on the roll (less than one radius behind the right-hand plan outline): the height the tube gives at the dot's place against the dot's own height
alld = [(int(r["id"]), float(r["x_mm"]), float(r["y_mm"]), float(r["z_mm"])) for r in csv.DictReader(open(ROOT / "seat/dots.csv"))]; fid = {d[0] for d in dots}; roll = []
for i, x, y, z in alld:
    if i in fid or not (X0 <= x <= X1): continue
    d = ip(A["tyR"], x) - y
    if 0 <= d <= R: roll.append({"dot": i, "x": x, "behind_outline_mm": round(d, 1), "dot_z": z, "tube_z_there": round(ip(A["tzR"], x) - R + float(np.sqrt(R * R - (R - d) ** 2)), 1)})
for q in roll: q["dot_minus_tube_mm"] = round(q["dot_z"] - q["tube_z_there"], 1)
roll.sort(key=lambda q: q["x"]); rd = np.array([q["dot_minus_tube_mm"] for q in roll]); rx = np.array([q["x"] for q in roll])
info = lambda t: {"photos_and_x_ranges": t["photo_range_x"], "residual_rms_mm": round(t["residual_rms_mm"], 2), "per_photo_rms_mm": {k: round(v, 2) for k, v in t["per_photo_rms_mm"].items()},
                  "per_photo_median_mm": {k: round(v, 2) for k, v in t["per_photo_median_mm"].items()}}
xd = np.r_[xs, XC]; bzd = np.r_[bz, CORNER_BOTTOM_Z]
out = {
    "frame": "chair frame, mm: +X chair's right, +Y forward, +Z up, table top Z=0",
    "method": "Section of the seat's front edge. TOP: the rolled edge as a tube (tools/tube_tri.py), now fixed by 8 overhead photos on the plan sheet AND 6 level/low front photos "
              "(1558, 1562 square on; 1531, 1530, 1523, 1524 from the chair's left) on a vertical sheet through y 525, in one solve: the front photos see the top of the roll "
              "as a horizon, which pins its HEIGHT (the weak direction of the overhead-only solve of parts/seat_front.json). BOTTOM: the arris between the front face and the "
              "underside, a sharp line (tube of radius 1), traced in 9 front photos between 7 below and 34 degrees above level (1558, 1559, 1496, 1562 square on; 1533, 1534, "
              "1525 from the left; 1485, 1484 from the right). The underside is glossy and pitched 10 degrees, so the level photo sees it as a mirror band under the dark face: "
              "the arris is the crease between the two there and a silhouette in the higher photos. Seeds parts/seat_front_face_seeds.json; assembled by tools/seat_front_face_fit.py.",
    "right": {"top_of_roll_z": sub(A["tzR"]), "top_plan_outline_y": sub(A["tyR"]), "bottom_arris_y": sub(A["byR"]), "bottom_arris_z": sub(A["bzR"]), "top_solve": info(A["ttR"]), "bottom_solve": info(A["btR"])},
    "left": {"note": "against |x| (mirrored)", "top_of_roll_z": sub(A["tzL"]), "top_plan_outline_y": sub(A["tyL"]), "bottom_arris_y": sub(A["byL"]), "bottom_arris_z": sub(A["bzL"]), "top_solve": info(A["ttL"]), "bottom_solve": info(A["btL"])},
    "left_vs_right": {"note": "right minus mirrored left at the same |x| (0 = mirror images), stations every 2 mm, |x| 8-262. The right half sits lower toward the outside: the same sense and "
                              "size as the left/right skew of the seat edges and arms (parts/lr_skew.json); the design is the mean",
                      "top_of_roll_z_mm": {**st(A["tzR"] - A["tzL"]), "at_abs_x": at(A["tzR"] - A["tzL"])}, "top_plan_outline_y_mm": {**st(A["tyR"] - A["tyL"]), "at_abs_x": at(A["tyR"] - A["tyL"])},
                      "bottom_arris_z_mm": {**st(A["bzR"] - A["bzL"]), "at_abs_x": at(A["bzR"] - A["bzL"])}, "bottom_arris_y_mm": {**st(A["byR"] - A["byL"]), "at_abs_x": at(A["byR"] - A["byL"])}},
    "design": {"note": "symmetric design section of the front edge against |x| (x -> -x for the left), every 2 mm for |x| 8-262. The plan outline of the top edge stays parts/seat_front.json "
                       "(design.front_y_of_abs_x); this file adds the heights and the bottom arris",
               "top_of_roll_z_of_abs_x": tab(tz), "top_of_roll": {"provenance": "triangulated", "tol_mm": 1.5, "tol_note": "+-1.5 for |x| 70-250; +-3 on the pommel flanks |x| 8-70 (steep, the trace slides along the edge) and at the corner ends |x| > 250"},
               "roll_radius_mm": {"value": R, "provenance": "assumed", "note": "solved freely it wanders between 2 and 20 mm along the edge, differently left and right, and the fit is no better (rms 0.76/0.81 against 0.80/0.82); "
                                                                                 "the top height moves by about 1 mm and the plan outline by -1.3 / +1.2 mm for radius 4 / 12"},
               "bottom_arris_y_of_abs_x": tab(by), "bottom_arris_z_of_abs_x": tab(bz), "bottom_arris": {"provenance": "triangulated", "tol_z_mm": 1.5, "tol_y_mm": 2.0},
               "bottom_corner": {"abs_x": XC, "z": CORNER_BOTTOM_Z, "provenance": "fitted", "tol_mm": 3.0,
                                 "note": "beyond |x| 240 the bottom arris rounds up into the end of the front corner (D-shaped end face); the last point is read on the 5 mm grid of rectified IMG_1558 (397-400)"},
               "bottom_arris_z_of_abs_x_with_corner": [[float(x), round(float(z), 1)] for x, z in zip(xd, bzd)],
               "face_height_top_of_roll_to_bottom_arris_mm": {"of_abs_x": tab(height), "pommel_flank_x8": round(float(height[0]), 1), "min": round(float(height.min()), 1), "min_at_abs_x": float(xs[np.argmin(height)]),
                                                               "corner_x262": round(float(height[-1]), 1), "provenance": "triangulated", "tol_mm": 2.0},
               "face_lean_mm": {"note": "bottom arris y minus plan outline y of the top edge at the same |x| (+ = the bottom stands further forward). Within the tolerance of the two lines for |x| < 240: "
                                        "the face is modelled vertical. Beyond 240 the bottom reads 2-4 mm forward, but the corner is a rounded 3D shape there and both lines are weak",
                                "of_abs_x": sub(lean), **st(lean), "abs_x_under_240": st(lean[xs < 240])},
               "underside_at_front_vs_side_plane_mm": None},
    "checks": {"plan_outline_vs_seat_front_json": {"note": "plan outline of the top edge from this combined solve minus the design outline of parts/seat_front.json (overhead photos only), |x| 8-262: "
                                                           "inside that file's +-2 mm, so it is left as it is", **st(ty - y0), "at_abs_x": at(ty - y0)},
               "front_face_dots": {"note": "the seat session's tape dots on the front face of the RIGHT half, not used in the solve, against the right-hand lines: each dot must sit between the bottom arris and the top, "
                                           "and on a vertical face on the plan outline", "dots": face},
               "top_dots_on_the_roll": {"note": "the seat session's tape dots on the seat top that sit on the roll of the RIGHT half (within one radius behind its plan outline), not used in the solve: "
                                                "dot height minus the tube's height at the same place. Up to x 218 the dots sit about 1 mm BELOW the tube (a softer roll than radius 8 would do that: radius 12 lowers the tube "
                                                "by 2 mm at those places); from x 228 to the corner they sit 2-4 mm ABOVE the right-hand tube (near the left/right mean instead). The level photo IMG_1558 sides with the tube there: the model surface built from the dots "
                                                "shows 2-3 mm above the wood's horizon at x 180-230 (model v10 and v11 alike). Not resolved",
                                        "dots": roll, "dot_minus_tube_mm": st(rd), "x_under_218": st(rd[rx < 218]), "x_over_218": st(rd[rx >= 218])},
               "variants": {"note": "the same solve with one thing changed; movement of the design lines (mean of right and left) over |x| 8-262", **var}},
    "open": ["roll radius of the top edge (8 mm) is assumed: no photo set tells 4 from 12",
             "pommel tip |x| < 8 and the corner ends |x| > 262 are not traced (the model holds the offsets found at 8 and 262)",
             "tape dots near the right front corner (x 228-245) sit 2-4 mm above the right-hand top of the roll solved here, and the model's seat surface (seat/surface.json, from those dots) shows "
             "2-3 mm above the wood in the level photo IMG_1558 at x 180-230; the design top of the roll (left/right mean) happens to agree with the dots. Either the dots' heights or the right-hand "
             "rim are off by that much there; a tape reading of the table-to-rim height at one front corner (PLAN.md M9 is the same kind of reading, behind the leg) would settle it",
             "whether the face leans under by 1-2 mm in the hollows is below what the two lines can tell (+-2 each); modelled vertical",
             "the bottom arris stands 2-3 mm above the plane through the two side bottom arrises carried forward (parts/seat_edge.json): the underside is not one flat plane up to the front, or the "
             "side plane is off by that much at its front end (its own tolerance is +-2.5). The underside itself is still unmeasured (IMG_1570, 1572, 1573, 1576 not used yet)"]}
E = json.load(open(ROOT / "parts/seat_edge.json"))["design"]; pl = np.polyval(E["bottom_z_of_y"]["poly_in_(y-250)"], by - 250.0)
out["design"]["underside_at_front_vs_side_plane_mm"] = {"note": "measured bottom arris z minus the side-arris underside plane at the same y", **st(bz - pl), "abs_x_under_240": st((bz - pl)[xs < 240]), "at_abs_x": at(bz - pl)}
json.dump(out, open(a.out, "w"), indent=1)
k = np.arange(0, len(xs), 16); row = lambda n, v: print(f"{n:22s}" + " ".join(f"{v[i]:6.1f}" for i in k))
row("|x|", xs); row("top z R", A["tzR"]); row("top z L", A["tzL"]); row("top z design", tz); row("plan y R", A["tyR"]); row("plan y L", A["tyL"]); row("plan y design", ty); row("seat_front.json y", y0)
row("bottom y R", A["byR"]); row("bottom y L", A["byL"]); row("bottom y design", by); row("bottom z R", A["bzR"]); row("bottom z L", A["bzL"]); row("bottom z design", bz); row("face height", height); row("lean (bot - top y)", lean); row("bottom - side plane", bz - pl)
print("plan outline - seat_front.json:", st(ty - y0)); print("lean |x|<240:", st(lean[xs < 240]))
for f in face: print("dot", f)
for q in roll: print("roll dot", q)
print("roll dots, dot - tube:", st(rd), "x<218", st(rd[rx < 218]), "x>=218", st(rd[rx >= 218]))
for g in var:
    for kk, v in var[g].items(): print(f"{g:13s} {kk:32s}", {q: (w["min"], w["max"]) if isinstance(w, dict) and "min" in w else w for q, w in v.items()})
