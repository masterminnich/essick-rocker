"""USAGE: python -I tools/seat_edge_fit.py [--out parts/seat_edge.json]
Assemble the seat's SIDE EDGE from the triangulated lines (tools/tri_lines.py output in work/parts/side{L,R}/):
  tsp/seat{L,R}_plan.json  top arris on the plan sheet (sheet in the rim plane; cameras above, inside and outside) -> half-width
  tse/seat{L,R}_top.json   the same arris on the side sheet (height check only: its depth = x is weak from the side)
  tse/seat{L,R}_bot.json   bottom arris on the side sheet (outline against the background from every camera above it)
Writes the raw left/right lines, their mirror comparison and a symmetric design version (mean of right and mirrored left,
low-order polynomials in y). Tiny compute (a few hundred points)."""
import json, argparse
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parent.parent
ap = argparse.ArgumentParser(); ap.add_argument("--out", default=str(ROOT / "parts/seat_edge.json")); a = ap.parse_args()
Y0, Y1, YC = 110.0, 400.0, 250.0          # design range: where both plan lines and both side lines exist; polynomials in (y - YC)


def load(side, sub, name):
    d = json.load(open(ROOT / f"work/parts/side{side}/{sub}/{name}.json")); P = np.array(d[name + "_xyz"]); P = P[np.argsort(P[:, 1])]; i = d[name + "_info"]
    return P, {"photos": i["photos"], "residual_rms_mm": round(i["residual_rms_mm"], 2), "arris_off_sheet_mm_start_mid_end": [round(i["depth_mm"][k], 1) for k in ("start", "mid", "end")]}


raw = {}; info = {}
for s in "LR":
    for key, sub, nm in (("top_plan", "tsp", f"seat{s}_plan"), ("top_side", "tse", f"seat{s}_top"), ("bottom", "tse", f"seat{s}_bot")):
        raw[s, key], info[s, key] = load(s, sub, nm)
ys = np.arange(Y0, Y1 + 1e-9, 10.0)
at = lambda s, key, c: np.interp(ys, raw[s, key][:, 1], raw[s, key][:, c])
T = {s: (np.abs(at(s, "top_plan", 0)), at(s, "top_plan", 2), at(s, "top_side", 2), np.abs(at(s, "top_side", 0))) for s in "LR"}      # |x|, z (plan), z (side), |x| (side)
B = {s: (np.abs(at(s, "bottom", 0)), at(s, "bottom", 2)) for s in "LR"}
top_hw = (T["L"][0] + T["R"][0]) / 2; top_z = (T["L"][1] + T["R"][1] + T["L"][2] + T["R"][2]) / 4; bot_hw = (B["L"][0] + B["R"][0]) / 2; bot_z = (B["L"][1] + B["R"][1]) / 2


def poly(v, deg):
    c = np.polyfit(ys - YC, v, deg); return {"poly_in_(y-250)": [float(x) for x in c], "fit_rms_mm": round(float(np.sqrt(np.mean((np.polyval(c, ys - YC) - v) ** 2))), 2)}, np.polyval(c, ys - YC)


P_th, f_th = poly(top_hw, 3); P_tz, f_tz = poly(top_z, 2); P_bh, f_bh = poly(bot_hw, 2); P_bz, f_bz = poly(bot_z, 1)
st = lambda v: {"mean": round(float(np.mean(v)), 2), "sd": round(float(np.std(v)), 2), "min": round(float(np.min(v)), 1), "max": round(float(np.max(v)), 1)}
lr = {"note": "right minus mirrored left at the same y (0 = mirror images), stations every 10 mm, y 110-400",
      "top_half_width_plan_mm": st(T["R"][0] - T["L"][0]), "top_z_plan_mm": st(T["R"][1] - T["L"][1]), "top_z_side_mm": st(T["R"][2] - T["L"][2]),
      "bottom_half_width_mm": st(B["R"][0] - B["L"][0]), "bottom_z_mm": st(B["R"][1] - B["L"][1]),
      "reading": "the right edge is further from the centre plane and lower, the same sense as the arms (parts/arms.json 'open'): a slight roll of the chair on the table "
                 "(or a real asymmetry); the design takes the mean, which cancels a roll to first order"}
chk = {"note": "the top arris solved twice, on the plan sheet and on the side sheet (different photos, different sheet): plan minus side",
       "left": {"half_width_mm": st(T["L"][0] - T["L"][3]), "z_mm": st(T["L"][1] - T["L"][2])}, "right": {"half_width_mm": st(T["R"][0] - T["R"][3]), "z_mm": st(T["R"][1] - T["R"][2])}}
tilt = float(np.degrees(np.arctan(P_bz["poly_in_(y-250)"][0])))
sub = lambda P: [[round(float(x), 1) for x in p] for p in P[::5]]
out = {
    "frame": "chair frame, mm: +X chair's right, +Y forward, +Z up, table top Z=0",
    "method": "Seat side edge between the back and front legs. Top arris: photos rectified onto a sheet in the seat's rim plane (tools/face_ortho.py, u = x); the arris is the "
              "seat's horizon against the floor from the overhead cameras on the far side and the face/top tone boundary from the cameras on the near side; triangulated "
              "(tools/edge_tri.py, seeds parts/seat_plan_seeds_{L,R}.json). Bottom arris and a second solve of the top arris: side sheets with u = height "
              "(seeds parts/seat_edge_seeds_{L,R}.json). Assembled by tools/seat_edge_fit.py.",
    "left": {"top_arris_plan_xyz": sub(raw["L", "top_plan"]), "top_arris_side_xyz": sub(raw["L", "top_side"]), "bottom_arris_xyz": sub(raw["L", "bottom"]),
             "solve": {"top_plan": info["L", "top_plan"], "top_side": info["L", "top_side"], "bottom": info["L", "bottom"]}},
    "right": {"top_arris_plan_xyz": sub(raw["R", "top_plan"]), "top_arris_side_xyz": sub(raw["R", "top_side"]), "bottom_arris_xyz": sub(raw["R", "bottom"]),
              "solve": {"top_plan": info["R", "top_plan"], "top_side": info["R", "top_side"], "bottom": info["R", "bottom"]}},
    "left_vs_right": lr, "plan_vs_side_check": chk,
    "design": {"note": "symmetric design version: mean of the right edge and the mirrored left edge; valid y 110-400 (between the legs); x -> -x for the left",
               "y_range": [Y0, Y1],
               "top_half_width_of_y": {**P_th, "provenance": "triangulated", "tol_mm": 1.5, "note": "plan outline of the seat blank at the sides (the top arris is the widest line: the edge face leans under)"},
               "top_z_of_y": {**P_tz, "provenance": "triangulated", "tol_mm": 2.5, "note": "mean of four solves (plan and side, left and right); the arris is rounded over, so its height is soft"},
               "bottom_half_width_of_y": {**P_bh, "provenance": "triangulated", "tol_mm": 3.0, "note": "from side photos only: depth (x) is the weak direction"},
               "bottom_z_of_y": {**P_bz, "provenance": "triangulated", "tol_mm": 2.5, "tilt_deg": round(tilt, 2)},
               "stations": [{"y": float(y), "top_half_width": round(float(f_th[i]), 1), "top_z": round(float(f_tz[i]), 1), "bottom_half_width": round(float(f_bh[i]), 1), "bottom_z": round(float(f_bz[i]), 1),
                             "edge_height_vertical": round(float(f_tz[i] - f_bz[i]), 1), "lean_under": round(float(f_th[i] - f_bh[i]), 1)} for i, y in enumerate(ys) if y % 30 == 20 or y in (Y0, Y1)]},
    "edge_thickness": {"vertical_top_to_bottom_arris_mm": st(f_tz - f_bz), "square_to_the_seat_plane_mm": st((f_tz - f_bz) * np.cos(np.radians(tilt))), "provenance": "triangulated", "tol_mm": 3.0,
                       "raw_left_mm": st(T["L"][2] - B["L"][1]), "raw_right_mm": st(T["R"][2] - B["R"][1]),
                       "note": "top arris minus bottom arris at the same y (the bottom arris is 'lean_under' further in); raw = side-sheet lines of one side only"},
    "open": ["the edge face between the two arrises is taken as straight; in the low photos its lower 12-17 mm reads darker (4 mm in the high photo 1510), which moves with the camera, so it is a "
             "reflection on a face that curves under, not a third arris; the section is not measured",
             "the underside between the two bottom arrises is not measured (flat across assumed); IMG_1570, 1572, 1573, 1576 look up at it from close range and could give it",
             "front edge, back edge and the corners outside y 110-400 are still the point cloud's outline",
             "top arris: the right edge solves 3-5 mm lower than the seat session's surface at |x| 251 while the left agrees within about 1 mm; the arris is a round-over, so the traced line sits "
             "at a slightly different place on it per side"]}
json.dump(out, open(a.out, "w"), indent=1)
print("design stations (y, top half-width, top z, bottom half-width, bottom z, edge height, lean under):")
for s_ in out["design"]["stations"]: print("  ", *[f"{v:7.1f}" for v in s_.values()])
print("fits rms: top hw", P_th["fit_rms_mm"], "top z", P_tz["fit_rms_mm"], "bottom hw", P_bh["fit_rms_mm"], "bottom z", P_bz["fit_rms_mm"], "| bottom tilt", round(tilt, 2), "deg")
print("R - mirrored L:", json.dumps({k: v for k, v in lr.items() if isinstance(v, dict)}))
print("plan vs side:", json.dumps({k: v for k, v in chk.items() if isinstance(v, dict)}))
print("edge thickness:", json.dumps({k: v for k, v in out["edge_thickness"].items() if isinstance(v, dict)}))
