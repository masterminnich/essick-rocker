"""USAGE: work/toolkit/rk.sh tools/seat_back/fit.py [SOLVED work/seat_back/solved.json] [OUT parts/seat_back.json]
Step 4 of 4 (sheet -> trace -> solve -> fit) for the seat's BACK EDGE. Turns the three triangulated edges (tools/seat_back/solve.py) into
the section of the back edge between the two back legs and writes parts/seat_back.json:

  TOP ARRIS -- back face (flat, leaning forward going down) -- HARD LINE -- under-bevel (flat) -- BOTTOM ARRIS -- underside (a plane)

In plan the back edge is a bow: furthest back on the centre line, coming forward to meet each back leg flush with the leg's rear face.
The under-bevel is a lens: deepest on the centre line, running out to nothing before the legs.
build_model.py reads "design" only: one table per edge against |x| (the symmetric, even solves).
Numbers printed here are the ones quoted in LEDGER.md and the pull request."""
import sys, json, numpy as np
solved = sys.argv[1] if len(sys.argv) > 1 else "work/seat_back/solved.json"; outf = sys.argv[2] if len(sys.argv) > 2 else "parts/seat_back.json"
S = json.load(open(solved)); EJ = json.load(open("tools/seat_back/inputs/edges.json")); SE = json.load(open("parts/seat_edge.json"))
T, H, B = (np.array(S[k]["even_xyz"]) for k in ("top", "hard", "bottom")); Tf, Hf, Bf = (np.array(S[k]["free_xyz"]) for k in ("top", "hard", "bottom"))
ev = lambda A, x, i: np.interp(np.abs(x), A[A[:, 0] >= 0, 0], A[A[:, 0] >= 0, i])
st = lambda v: {"mean": round(float(np.mean(v)), 2), "sd": round(float(np.std(v)), 2), "min": round(float(np.min(v)), 2), "max": round(float(np.max(v)), 2)}
XT, XH, XB = (float(A[-1, 0]) for A in (T, H, B)); XEND = 195.0                                # measured to |x| XT / XH / XB; the tables run on to XEND (inside the legs)
def carry(A, i, x, x_end, run=20.0):                                                           # straight continuation of the last `run` mm of an even curve
    m = (A[:, 0] >= x_end - run); a, b = np.polyfit(A[m, 0], A[m, i], 1); return np.where(np.abs(x) <= x_end, ev(A, x, i), a * np.abs(x) + b)
xs = np.arange(0.0, XEND + 1e-9, 5.0)
yT, zT, yB, zB = carry(T, 1, xs, XT), carry(T, 2, xs, XT), carry(B, 1, xs, XB), carry(B, 2, xs, XB)
# the lens: height of the hard line above the bottom arris; its tip = where the last 30 mm, carried on straight, reach zero
xh = np.arange(0.0, XH + 1e-9, 1.0); hh = ev(H, xh, 2) - ev(B, xh, 2); a, b = np.polyfit(xh[xh >= XH - 30], hh[xh >= XH - 30], 1); tip = float(-b / a)
t = np.clip((xs - XH) / (tip - XH), 0, 1)                                                      # beyond the measured range the hard line runs straight into the bottom arris at the tip
yH = np.where(xs <= XH, ev(H, xs, 1), ev(H, XH, 1) + t * (carry(B, 1, np.array([tip]), XB)[0] - ev(H, XH, 1)))
zH = np.where(xs <= XH, ev(H, xs, 2), ev(H, XH, 2) + t * (carry(B, 2, np.array([tip]), XB)[0] - ev(H, XH, 2)))
on = xs < tip; yH[~on] = yB[~on]; zH[~on] = zB[~on]
# section angles where all three edges are measured
xa = np.arange(0.0, 150.0 + 1e-9, 5.0); lean = np.degrees(np.arctan2(ev(H, xa, 1) - ev(T, xa, 1), ev(T, xa, 2) - ev(H, xa, 2))); bev = np.degrees(np.arctan2(ev(H, xa, 2) - ev(B, xa, 2), ev(B, xa, 1) - ev(H, xa, 1)))
face_h = np.hypot(ev(H, xa, 1) - ev(T, xa, 1), ev(T, xa, 2) - ev(H, xa, 2)); bev_w = np.hypot(ev(H, xa, 2) - ev(B, xa, 2), ev(B, xa, 1) - ev(H, xa, 1))
# underside: is the back's bottom arris on the plane through the two side bottom arrises (parts/seat_edge.json)?
pz = SE["design"]["bottom_z_of_y"]["poly_in_(y-250)"]; xb = np.arange(0.0, XB + 1e-9, 5.0); dpl = ev(B, xb, 2) - np.polyval(pz, ev(B, xb, 1) - 250.0)
# left against right (the free solves), every 5 mm
def lr(A, x_end):
    x = np.arange(5.0, x_end + 1e-9, 5.0); L = np.c_[np.interp(-x, A[:, 0], A[:, 1]), np.interp(-x, A[:, 0], A[:, 2])]; R = np.c_[np.interp(x, A[:, 0], A[:, 1]), np.interp(x, A[:, 0], A[:, 2])]
    return {"y_mm": st(L[:, 0] - R[:, 0]), "z_mm": st(L[:, 1] - R[:, 1])}
ph = lambda k: {p: {"rms_mm": v["rms_even_mm"], "x_ranges": v["x_ranges"], "left_out_moves_curve_mm": S[k]["leave_one_photo_out_mm"][p]} for p, v in S[k]["photos"].items()}
rms = lambda k: (min(v["rms_even_mm"] for v in S[k]["photos"].values()), max(v["rms_even_mm"] for v in S[k]["photos"].values()))
loo = lambda k, c: max(v[c] for v in S[k]["leave_one_photo_out_mm"].values())
tab = lambda y, z: {"y": np.round(y, 2).tolist(), "z": np.round(z, 2).tolist()}
out = {
 "frame": SE["frame"],
 "method": "One rear sheet (tools/face_ortho.py, plane y = 30 seen from behind, u = chair x, v = height) rendered from 12 photos taken from behind the chair, level to 56 degrees above. Each of the three "
           "edges seeded as a 3D curve, drawn through each photo's camera onto that photo's sheet and snapped to the tone edge inside +-2 mm (tools/seat_back/trace.py); then each edge triangulated as ONE "
           "smooth curve x -> (y, z) from all its photos at once (tools/seat_back/solve.py -> tools/curve_tri.py). Height comes from the level photos, depth from the photos taken from above. "
           "Inputs: tools/seat_back/inputs/ (seeds, trusted stretches per photo, the snapped traces).",
 "section": {
  "is": "TOP ARRIS (sharp) -> back face, flat, leaning FORWARD going down -> HARD LINE -> under-bevel, flat -> BOTTOM ARRIS -> underside (the same plane as along the sides). In plan the edge is a bow: "
        "furthest back on the centre line, coming forward to meet each back leg flush with the leg's rear face. The under-bevel is a lens across the chair: deepest on the centre line, nothing at the legs.",
  "replaces": "build_model.py's straight back edge at the 1st percentile of the cloud (y 10.8), vertical, full thickness, running on behind the legs",
  "plan_bow_mm": {"value": round(float(ev(T, XT, 1) - ev(T, 0, 1)), 1), "note": "top arris y at |x| %d minus y on the centre line" % XT, "provenance": "triangulated"},
  "back_face_lean_deg": {**st(lean), "x_range": [0, 150], "provenance": "triangulated", "note": "angle from vertical of the line top arris -> hard line (the two edges solved separately); the face looks backward and down"},
  "back_face_height_mm": {**st(face_h), "x_range": [0, 150]},
  "bevel_angle_deg": {**st(bev), "x_range": [0, 150], "provenance": "triangulated", "note": "angle below level of the line hard line -> bottom arris; the side edges' under-bevel measures %.1f (parts/seat_scoop.json)" % json.load(open("parts/seat_scoop.json"))["design"]["bevel_angle_deg"]["value"]},
  "bevel_width_mm": {**st(bev_w), "x_range": [0, 150]},
  "lens": {"height_on_centre_line_mm": round(float(hh[0]), 1), "height_of_abs_x": [[float(x), round(float(np.interp(x, xh, hh)), 1)] for x in (0, 30, 60, 90, 120, 150, 165)], "tip_abs_x": round(tip, 1),
           "provenance": "triangulated to |x| %d; the tip is the straight continuation of the last 30 mm (fitted)" % XH},
  "underside": {"bottom_arris_z_minus_side_arris_plane_mm": st(dpl), "x_range": [0, XB], "note": "the back's bottom arris against the plane through the two SIDE bottom arrises (parts/seat_edge.json 'bottom_z_of_y'): the underside is one plane, flat across; an independent check, the two were measured from different photos"}},
 "measured": {k: {"degree": S[k]["degree"], "x_range": S[k]["x_range"], "even_xyz": np.array(S[k]["even_xyz"])[::5].round(2).tolist(), "free_xyz": np.array(S[k]["free_xyz"])[::5].round(2).tolist(), "photos": ph(k),
                  "left_minus_mirrored_right": lr(F, xe), "what": EJ["edges"][k]["what"]} for k, F, xe in (("top", Tf, XT), ("hard", Hf, XH), ("bottom", Bf, XB))},
 "design": {
  "note": "symmetric design version (the even solves). For each |x|: the top arris (y, z), the hard line (y, z) and the bottom arris (y, z). Between the top arris and the hard line the back face is flat; "
          "between the hard line and the bottom arris the under-bevel is flat. Beyond 'lens_tip_abs_x' the hard line IS the bottom arris: one flat face, full thickness. The tables run on to |x| %d, "
          "inside the back legs, so the legs cut the seat's corners (the joint face is the leg's inner face)." % XEND,
  "abs_x": xs.tolist(), "top_arris": {**tab(yT, zT), "provenance": "triangulated to |x| %d; beyond that the straight continuation of the last 20 mm (fitted; inside the leg from about |x| 188)" % XT, "tol_mm": 1.6},
  "hard_line": {**tab(yH, zH), "provenance": "triangulated to |x| %d; from there straight into the bottom arris at the lens tip (fitted)" % XH, "tol_mm": 1.6},
  "bottom_arris": {**tab(yB, zB), "provenance": "triangulated to |x| %d; beyond that the straight continuation of the last 20 mm (fitted)" % XB, "tol_mm": 1.6,
                   "note": "build_model.py takes y from here and z from the underside plane at that y (the two agree within %.1f mm)" % float(np.abs(dpl).max())},
  "lens_tip_abs_x": round(tip, 1),
  "at_leg_inner_face": {"abs_x": 188.0, "top_arris_y": round(float(np.interp(188.0, xs, yT)), 1), "top_arris_z": round(float(np.interp(188.0, xs, zT)), 1), "bottom_arris_y": round(float(np.interp(188.0, xs, yB)), 1), "provenance": "fitted",
                        "note": "the model leg's rear face is at y 30.2 at this height (z 335) and y 34.9 at the underside (z 290): the seat's top arris meets the leg flush with the leg's rear face"}},
 "checks": {
  "tolerance": "free curve: 1.6 mm",
  "top_arris": "%d photos; rms on the sheet %.2f-%.2f mm; dropping any one photo moves the curve by at most %.2f mm in depth (y), %.2f mm in height (z)" % (len(S["top"]["photos"]), *rms("top"), loo("top", "y_whole"), loo("top", "z_whole")),
  "hard_line": "%d photos; rms %.2f-%.2f mm; leave-one-out at most %.2f mm in y, %.2f mm in z (%.2f away from the ends)" % (len(S["hard"]["photos"]), *rms("hard"), loo("hard", "y_whole"), loo("hard", "z_whole"), loo("hard", "z_inner")),
  "bottom_arris": "%d photos; rms %.2f-%.2f mm; leave-one-out at most %.2f mm in y (%.2f away from the ends), %.2f mm in z" % (len(S["bottom"]["photos"]), *rms("bottom"), loo("bottom", "y_whole"), loo("bottom", "y_inner"), loo("bottom", "z_whole")),
  "bevel_is_45": "with the two edges solved separately and symmetric, the bevel's run equals its drop within %.1f mm at every station from the centre line to |x| 150" % float(np.abs((ev(B, xa, 1) - ev(H, xa, 1)) - (ev(H, xa, 2) - ev(B, xa, 2))).max())},
 "open": ["bottom arris, depth (y): left and right differ by up to %.1f mm at the ends in the free solve (left further back). Its depth comes only from the photos 19-33 degrees above (1 mm on the sheet = 1.5-3 mm in depth) and the two "
          "ends are seen by different photos, so this is inside what those photos can tell; the symmetric solve gives a 45 degree bevel all the way along, the two free halves do not. Height (z) agrees left/right within %.1f mm" % (
              float(np.abs(np.interp(-xb, Bf[:, 0], Bf[:, 1]) - np.interp(xb, Bf[:, 0], Bf[:, 1])).max()), float(np.abs(np.interp(-xb, Bf[:, 0], Bf[:, 2]) - np.interp(xb, Bf[:, 0], Bf[:, 2])).max())),
          "hard line, height (z): the left half sits up to %.1f mm lower than the right in the free solve (the bevel was worked by hand); the design is the mean" % float(np.abs(np.interp(-xh, Hf[:, 0], Hf[:, 2]) - np.interp(xh, Hf[:, 0], Hf[:, 2])).max()),
          "hard line, depth (y): from IMG_1540 and IMG_1542 only (from more than 45 degrees above the bevel is hidden and the seat's lower outline is the hard line). In 1542 the outline sits 1.9 mm off the solved curve on the right half and 0.3-0.6 mm on the left; left of x -135 no photo gives depth",
          "the lens tips (|x| %d to %.0f) and the last stretch to the legs (top arris beyond |x| %d, bottom arris beyond %d) are straight continuations, not traced: the legs and their shadows hide them" % (XH, tip, XT, XB),
          "the top arris is drawn sharp; its small easing is not measured",
          "the real seam between seat and leg sits 2.5-3.4 mm inboard of the model leg's inner face at the rear (LEDGER 19:25): leg placement, not changed here"]}
json.dump(out, open(outf, "w"), indent=1); print("wrote", outf)
print("plan bow:", out["section"]["plan_bow_mm"]["value"], "| face lean:", out["section"]["back_face_lean_deg"], "| face height:", out["section"]["back_face_height_mm"])
print("bevel angle:", out["section"]["bevel_angle_deg"], "| bevel width:", out["section"]["bevel_width_mm"]); print("lens:", out["section"]["lens"]); print("underside:", out["section"]["underside"]["bottom_arris_z_minus_side_arris_plane_mm"])
print("at the leg:", out["design"]["at_leg_inner_face"]); print("L-R:", {k: v["left_minus_mirrored_right"] for k, v in out["measured"].items()})
print("table |x|: yT zT | yH zH | yB zB"); [print("  %3d: %6.1f %6.1f | %6.1f %6.1f | %6.1f %6.1f" % (x, yT[i], zT[i], yH[i], zH[i], yB[i], zB[i])) for i, x in enumerate(xs) if x % 15 == 0 or x >= 165]
print("checks:", json.dumps(out["checks"], indent=1)); print("open:", json.dumps(out["open"], indent=1))
