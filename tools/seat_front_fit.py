"""USAGE: python -I tools/seat_front_fit.py [--out parts/seat_front.json]
Assemble the seat's FRONT EDGE in plan from the rolled-edge solves (tools/tube_tri.py, seeds parts/seat_front_seeds.json,
output work/parts/seatF/tube/front{R,L}.json; variants in work/parts/seatF/tube_<tag>/): raw right and left outlines, their
mirror comparison, a symmetric design outline (mean of right and mirrored left, pommel tip and front corners added), how far the
outline moves when the assumptions change, and a check against the seat session's tape dots (seat/dots.csv, seat/front_face.csv),
which were not used in the solve. Tiny compute (a few hundred points)."""
import json, argparse, csv
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parent.parent
ap = argparse.ArgumentParser(); ap.add_argument("--out", default=str(ROOT / "parts/seat_front.json")); a = ap.parse_args()
W = ROOT / "work/parts/seatF"; X0, X1, XC = 8.0, 262.0, 268.0          # solved range of |x|; front corner half-width (the side arris line carried forward, parts/seat_edge.json 268.6 at y 400)
xs = np.arange(X0, X1 + 1e-9, 2.0)


def load(d):
    o = {}
    for s in "RL":
        t = json.load(open(W / d / f"front{s}.json")); P = np.array(t["plan_outline_xy"]); P[:, 0] = np.abs(P[:, 0]); P = P[np.argsort(P[:, 0])]; o[s] = (np.interp(xs, P[:, 0], P[:, 1]), t)
    return o


A = load("tube"); yR, yL = A["R"][0], A["L"][0]; ym = (yR + yL) / 2
st = lambda v: {"mean": round(float(np.mean(v)), 2), "sd": round(float(np.std(v)), 2), "min": round(float(np.min(v)), 1), "max": round(float(np.max(v)), 1)}
dots = {int(r["id"]): (float(r["x_mm"]), float(r["y_mm"]), float(r["z_mm"])) for r in csv.DictReader(open(ROOT / "seat/dots.csv"))}
face_ids = [int(r["id"]) for r in csv.DictReader(open(ROOT / "seat/front_face.csv"))]; face_drop = {int(r["id"]): float(r["top_surface_z_above_mm"]) for r in csv.DictReader(open(ROOT / "seat/front_face.csv"))}
# design outline y(|x|): 0 .. X0 straight to the pommel tip (the seat session's dot 108 sits on the tip's front face), X0 .. X1 the mean, X1 .. XC carried on straight to the corner
tip_y = dots[108][1]; sl = np.polyfit(xs[-7:], ym[-7:], 1)[0]; xd = np.r_[0.0, xs, XC]; yd = np.r_[tip_y, ym, ym[-1] + sl * (XC - X1)]; xt = np.arange(0, XC + 1e-9, 2.0); yt = np.interp(xt, xd, yd)
des = lambda x: np.interp(np.abs(x), xd, yd)
var = {}
for d in sorted(p.name for p in W.glob("tube_*") if (p / "frontR.json").exists() and (p / "frontL.json").exists()):
    B = load(d); dm = (B["R"][0] + B["L"][0]) / 2 - ym; var[d[5:]] = {"design_outline_moves_mm": st(dm), "right_moves_mm": st(B["R"][0] - yR), "left_moves_mm": st(B["L"][0] - yL),
                                                                      "residual_rms_mm": {s: round(B[s][1]["residual_rms_mm"], 2) for s in "RL"}}
face = [{"dot": i, "x": dots[i][0], "y": dots[i][1], "below_top_mm": face_drop[i], "design_outline_minus_dot_mm": round(float(des(dots[i][0]) - dots[i][1]), 2),
         "right_outline_minus_dot_mm": round(float(np.interp(dots[i][0], xs, yR) - dots[i][1]), 2) if X0 <= dots[i][0] <= X1 else None} for i in face_ids]
used = [f for f in face if f["dot"] not in (107, 108)]; fd = np.array([f["design_outline_minus_dot_mm"] for f in used]); fr = np.array([f["right_outline_minus_dot_mm"] for f in used])
top = sorted([(round(float(des(x) - y), 1), i, x, y) for i, (x, y, z) in dots.items() if i not in face_ids and des(x) - y < 14 and y > 480])
sub = lambda y: [[float(x), round(float(v), 1)] for x, v in zip(xs[::5], y[::5])]
info = lambda t: {"photos_and_x_ranges": t["photo_range_x"], "residual_rms_mm": round(t["residual_rms_mm"], 2), "per_photo_rms_mm": {k: round(v, 2) for k, v in t["per_photo_rms_mm"].items()},
                  "per_photo_median_mm": {k: round(v, 2) for k, v in t["per_photo_median_mm"].items()}, "view_angle_round_roll_deg_start_mid_end": t["view_angle_round_roll_deg_start_mid_end"],
                  "top_of_roll_minus_seat_surface_mm": st(np.array(t["top_of_roll_minus_seat_surface_mm"]))}
out = {
    "frame": "chair frame, mm: +X chair's right, +Y forward, +Z up, table top Z=0",
    "method": "Front edge of the seat seen from above. The edge is rolled over (no arris), so every camera outlines a different line on it; tools/tube_tri.py models it as a tube "
              "(circle of radius r swept along a spine) and finds the spine whose outline, computed per camera, matches the outline traced in each of 8 overhead photos "
              "(1545, 1544 from behind; 1549, 1548, 1547 from the left; 1539, 1538, 1537 from the right) rectified onto a sheet through the front rim (tools/face_ortho.py). "
              "Plan outline = spine moved out by r. Seeds parts/seat_front_seeds.json; assembled by tools/seat_front_fit.py.",
    "right": {"outline_xy": sub(yR), "solve": info(A["R"][1])}, "left": {"outline_abs_x_y": sub(yL), "solve": info(A["L"][1])},
    "left_vs_right": {"note": "right minus mirrored left, front outline y at the same |x| (0 = mirror images), stations every 2 mm, |x| 8-262", "y_mm": st(yR - yL),
                      "at_abs_x": {str(int(x)): round(float(v), 1) for x, v in zip(xs[::16], (yR - yL)[::16])}},
    "design": {"note": "symmetric design outline of the seat's front edge in plan: y of the furthest-forward line of the rolled top edge as a function of |x|; x -> -x for the left. "
                       "Scalloped: pommel point at the centre, thigh hollows either side, front corners (horns) forward again",
               "front_y_of_abs_x": [[float(x), round(float(y), 1)] for x, y in zip(xt, yt)],
               "pommel_tip": {"x": 0.0, "y": round(tip_y, 1), "provenance": "measured (seat session dot 108, on the front face of the tip, 30 mm below the top; the real tip sits at x = +1.8)", "tol_mm": 1.5},
               "hollow": {"abs_x": float(xt[np.argmin(yt)]), "y": round(float(yt.min()), 1), "scallop_depth_from_tip_mm": round(float(tip_y - yt.min()), 1), "scallop_depth_from_corner_mm": round(float(yt[-1] - yt.min()), 1)},
               "corner": {"abs_x": XC, "y": round(float(yt[-1]), 1), "provenance": "fitted (outline carried 6 mm straight on to the side line x = 268; the corner reads at |u| 267-268 on the rectified photos 1545, 1544)", "tol_mm": 2.0},
               "provenance": "triangulated", "tol_mm": 2.0, "roll_radius_mm": {"value": 8.0, "provenance": "assumed", "note": "the photos cannot tell 4 from 16 mm (same residual); the outline moves by under 1 mm over that range"},
               "face_below": "vertical within about 1 mm at the five tape dots on the front face (11-23 mm below the top); the model's front wall is vertical. "
                             "Heights of the top of the roll and the bottom arris of the face: parts/seat_front_face.json"},
    "checks": {"front_face_dots": {"note": "the seat session's dots on the front face (seat/front_face.csv), not used in the solve: on a vertical face they lie on the plan outline. 107 (on the horn, 35 mm below "
                                           "the top) and 108 (the pommel tip, used for the tip) are listed but not counted",
                                   "dots": face, "design_minus_dot_mm": st(fd), "design_minus_dot_rms_mm": round(float(np.sqrt(np.mean(fd ** 2))), 2), "right_outline_minus_dot_rms_mm": round(float(np.sqrt(np.mean(fr ** 2))), 2)},
               "top_dots_nearest_the_edge": {"note": "tape dots on the seat top within 14 mm of the design outline: all must be inside it (margin > 0)", "smallest_margins_mm": [{"dot": i, "x": x, "y": y, "margin": m} for m, i, x, y in top[:6]]},
               "variants": {"note": "the same solve with one assumption changed; movement of the plan outline over |x| 8-262 (design = mean of right and left)", **var}},
    "open": ["depth is the weak direction of this solve (the overhead cameras look at the edge from 0-35 degrees round the roll): tying the roll's height to the measured seat surface instead of solving it "
             "moves the outline by up to 3 mm in places, and dropping the two steepest photos by up to 3 mm; hence tol 2 mm, not 1/16 inch",
             "right half beyond x 126 rests on two camera groups only (1545/1544 and 1549/1548/1547); the right arm hides it from 1539/1538/1537",
             "the roll radius (8 mm) is assumed. The front face's bottom arris and the height of the top of the roll are measured since in parts/seat_front_face.json (front edge 38 mm high "
             "at the pommel flank, 21 mm in the hollows). The dark band IMG_1539 shows outside the top edge on the right flank of the pommel (about 5 mm wide) is NOT explained by it: the bottom arris "
             "stands only 0-2.5 mm forward of the top edge there and that camera looks along the face (2 degrees from behind edge-on); still open",
             "pommel tip region |x| < 8 and the corners |x| > 262 are straight joins, not traced"]}
json.dump(out, open(a.out, "w"), indent=1)
k = np.arange(0, len(xs), 16)
print("|x|:            " + " ".join(f"{xs[i]:6.0f}" for i in k)); print("right y:        " + " ".join(f"{yR[i]:6.1f}" for i in k)); print("left y:         " + " ".join(f"{yL[i]:6.1f}" for i in k)); print("design y:       " + " ".join(f"{ym[i]:6.1f}" for i in k))
print("tip y", round(tip_y, 1), "| hollow", out["design"]["hollow"], "| corner", out["design"]["corner"]["abs_x"], out["design"]["corner"]["y"]); print("R - mirrored L:", out["left_vs_right"]["y_mm"])
print("face dots (design - dot):", [(f["dot"], f["design_outline_minus_dot_mm"], f["right_outline_minus_dot_mm"]) for f in face], "rms", out["checks"]["front_face_dots"]["design_minus_dot_rms_mm"], "/ right only", out["checks"]["front_face_dots"]["right_outline_minus_dot_rms_mm"])
print("top dots, smallest margins:", [(m, i) for m, i, x, y in top[:6]])
for kk, v in var.items(): print(f"variant {kk:30s} design moves {v['design_outline_moves_mm']}  R {v['right_moves_mm']['min']}..{v['right_moves_mm']['max']}  L {v['left_moves_mm']['min']}..{v['left_moves_mm']['max']}  rms {v['residual_rms_mm']}")
