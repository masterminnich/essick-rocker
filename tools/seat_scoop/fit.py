"""USAGE: work/toolkit/rk.sh tools/seat_scoop/fit.py [SOLVED work/seat_scoop/solved_R.json] [OUT parts/seat_scoop.json]
Step 4 of 4 (strip -> snap -> solve -> fit). Turns the two triangulated edges of the seat's right side edge (the hard line and the bottom
arris, tools/seat_scoop/solve.py) into the section of the side edge between the legs and writes parts/seat_scoop.json:

  top arris -- edge face (vertical) -- HARD LINE -- under-bevel (constant angle) -- BOTTOM ARRIS -- underside (a plane)

The under-bevel is a scoop: deepest at mid-length, running out to nothing at the legs. It is described by ONE function of the station y,
the height of the hard line above the underside plane, plus one angle. build_model.py reads "design" only.
Numbers printed here are the ones quoted in LEDGER.md and the pull request."""
import sys, json, numpy as np
sys.path.insert(0, ".")
solved = sys.argv[1] if len(sys.argv) > 1 else "work/seat_scoop/solved_R.json"; outf = sys.argv[2] if len(sys.argv) > 2 else "parts/seat_scoop.json"
S = json.load(open(solved)); E = json.load(open("parts/seat_edge.json")); R = E["right"]
C = np.array(S["crescent"]["xyz"]); B = np.array(S["bottom"]["xyz"])
def ip(A, y, i): A = np.array(A); A = A[np.argsort(A[:, 1])]; return np.interp(y, A[:, 1], A[:, i])
st = lambda v: {"mean": round(float(np.mean(v)), 2), "sd": round(float(np.std(v)), 2), "min": round(float(np.min(v)), 2), "max": round(float(np.max(v)), 2)}
# underside along the right edge: the bottom arris is a straight line in z (the underside is a plane tilted back)
pb = np.polyfit(B[:, 1] - 250.0, B[:, 2], 1); line = lambda y: np.polyval(pb, np.asarray(y, float) - 250.0); rb = B[:, 2] - line(B[:, 1])
# height of the hard line above that plane, and the bevel between the two edges where both are solved
g = C[:, 2] - line(C[:, 1]); yb = B[:, 1]; cx, cz = ip(C, yb, 0), ip(C, yb, 2); run, drop = cx - B[:, 0], cz - B[:, 2]; ang = np.degrees(np.arctan2(drop, run))
core = (yb >= 150) & (yb <= 410); angle = float(np.median(ang[core]))
# the edge face above the hard line: is the hard line under the top arris? (top arris from the plan sheet of parts/seat_edge.json: its x is the strong direction there)
P = np.array(R["top_arris_plan_xyz"]); yy = np.arange(max(110.0, C[0, 1]), min(400.0, C[-1, 1]) + 1e-9, 5.0)
lean = ip(C, yy, 0) - ip(P, yy, 0); face_h = ip(P, yy, 2) - ip(C, yy, 2)
# tips: where the hard line reaches the underside, by carrying the end 30 mm of g on as a straight line
def tip(lo):
    m = (C[:, 1] <= C[0, 1] + 30) if lo else (C[:, 1] >= C[-1, 1] - 30); a, b = np.polyfit(C[m, 1], g[m], 1); return float(-b / a), float(a)
(tb, sb), (tf, sf) = tip(True), tip(False)
# design table every 5 mm from tip to tip: measured inside the solved range, the straight continuation outside it
yd = np.unique(np.r_[np.ceil(tb / 5) * 5, np.arange(np.ceil(tb / 5) * 5, np.floor(tf / 5) * 5 + 1e-9, 5.0)]); gd = np.where(yd < C[0, 1], sb * (yd - tb), np.where(yd > C[-1, 1], sf * (yd - tf), np.interp(yd, C[:, 1], g)))
gd = np.maximum(gd, 0.0); ytab = np.r_[tb, yd, tf]; gtab = np.r_[0.0, gd, 0.0]
out = {
 "frame": E["frame"],
 "method": "The seat's right side edge unrolled in each photo (tools/seat_scoop/strip.py: column = station y, row = position across the edge), two edges seeded by eye and snapped to the tone edge "
           "(snap.py), each triangulated as one smooth 3D curve x(y), z(y) from all photos at once (solve.py: Legendre degree 6, residual = distance in the photo in mm at the edge, soft-L1 0.5 mm). "
           "The hard line is seen from 30 degrees below to 72 degrees above: from below as the top of the dark under-bevel, from 31-38 degrees above as the top of a grey sliver, from 43-72 degrees above "
           "as the seat's outer silhouette. Inputs: tools/seat_scoop/inputs/ (seeds, snapped traces, trusted ranges).",
 "section": {
  "is": "top arris (eased) -> edge face, vertical -> HARD LINE -> under-bevel, flat, constant angle -> BOTTOM ARRIS -> underside (a plane). The under-bevel is a scoop between the legs: deepest at "
        "mid-length and running out to nothing at each leg, where the edge face is the full thickness of the seat.",
  "replaces": "parts/seat_edge.json 'design.bottom_half_width_of_y' and its note that the whole edge face leans under in one straight line from top arris to bottom arris (that line was a chord "
              "across the corner at the hard line: up to %.1f mm inside the wood at mid-length)" % float(np.max(np.array(S["crescent"]["off_old_wall_mm"]))),
  "bevel_angle_deg": {**st(ang[core]), "median": round(angle, 2), "y_range": [150, 410], "provenance": "triangulated", "note": "angle below horizontal of the line from the hard line to the bottom arris, the two edges solved separately; 45 was probably the maker's setting"},
  "edge_face": {"hard_line_x_minus_top_arris_x_mm": st(lean), "height_top_arris_to_hard_line_mm": st(face_h), "y_range": [float(yy[0]), float(yy[-1])], "provenance": "triangulated",
                "note": "top arris = right plan-sheet solve of parts/seat_edge.json. The hard line sits under the top arris: the face is vertical (sawn square). Its height is soft: the top arris is eased (radius not measured)"},
  "underside_along_edge": {"z_at_y250": round(float(pb[1]), 2), "slope": round(float(pb[0]), 5), "tilt_deg": round(float(np.degrees(np.arctan(pb[0]))), 2), "straightness_rms_mm": round(float(np.sqrt(np.mean(rb ** 2))), 2), "max_mm": round(float(np.abs(rb).max()), 2),
                           "note": "bottom arris z against a straight line: the underside is a plane along the edge (right side, y %d-%d). In IMG_1492 the underside mirrors the room without distortion: flat across too (not measured)" % (B[0, 1], B[-1, 1])}},
 "right": {
  "hard_line_xyz": C[::5].round(2).tolist(), "bottom_arris_xyz": B[::5].round(2).tolist(),
  "height_of_hard_line_above_underside_mm": np.c_[C[::5, 1], g[::5]].round(2).tolist(),
  "bevel_run_drop_angle": np.c_[yb, run, drop, ang][::10].round(2).tolist(),
  "solve": {k: {"photos": S[k]["photos"], "leave_one_photo_out_moves_curve_mm": {n: {"inner": v[0], "whole": v[1]} for n, v in S[k]["leave_one_out_mm"].items()}, "degree": S[k]["degree"], "y_range": [float(S[k]["xyz"][0][1]), float(S[k]["xyz"][-1][1])]}
            for k in ("crescent", "bottom")},
  "note": "crescent = the hard line. 'inner' = more than 40 mm from the ends of the solved range"},
 "design": {
  "note": "symmetric design version. Along each side between the legs: the edge face drops vertically from the plan outline to the hard line; the hard line is 'height' above the underside; "
          "the under-bevel runs from the hard line inward and down at 'bevel_angle_deg' to the underside. Outside 'y_range' the height is 0: vertical edge face, full thickness.",
  "y_range": [round(tb, 1), round(tf, 1)],
  "hard_line_height_above_underside_of_y": {"y": ytab.round(2).tolist(), "height_mm": gtab.round(2).tolist(), "provenance": "triangulated", "tol_mm": 1.5,
      "provenance_ends": "fitted: outside y %d-%d the measured curve is carried on as a straight line to zero (back tip y %.0f, front tip y %.0f); where the tips sit against the leg joints has not been checked" % (C[0, 1], C[-1, 1], tb, tf)},
  "bevel_angle_deg": {"value": round(angle, 1), "provenance": "triangulated", "tol_deg": 1.5},
  "edge_face": {"lean_mm": 0.0, "provenance": "fitted", "note": "vertical; measured %.1f mm (sd %.1f) outboard at the hard line, inside the 1.5 mm tolerance of the outline" % (float(np.mean(lean)), float(np.std(lean)))},
  "left": {"provenance": "assumed", "note": "mirror of the right; the left side has not been traced from below yet"}},
 "checks": {
  "tolerance": "free curve: 1.6 mm",
  "hard_line": "14 photos; rms in the photo %.2f-%.2f mm; leave-one-photo-out moves the curve by at most %.2f mm away from the ends (%.2f mm at the ends)" % (
      min(v["rms_mm"] for v in S["crescent"]["photos"].values()), max(v["rms_mm"] for v in S["crescent"]["photos"].values()), max(v[0] for v in S["crescent"]["leave_one_out_mm"].values()), max(v[1] for v in S["crescent"]["leave_one_out_mm"].values())),
  "bottom_arris": "8 photos; rms in the photo %.2f-%.2f mm; leave-one-photo-out at most %.2f mm away from the ends (%.2f mm at the ends)" % (
      min(v["rms_mm"] for v in S["bottom"]["photos"].values()), max(v["rms_mm"] for v in S["bottom"]["photos"].values()), max(v[0] for v in S["bottom"]["leave_one_out_mm"].values()), max(v[1] for v in S["bottom"]["leave_one_out_mm"].values())),
  "bottom_arris_vs_seat_edge_json_right": {"x_mm": st(B[:, 0] - ip(R["bottom_arris_xyz"], yb, 0)), "z_mm": st(B[:, 2] - ip(R["bottom_arris_xyz"], yb, 2)), "x_mm_y150_300": st((B[:, 0] - ip(R["bottom_arris_xyz"], yb, 0))[(yb >= 150) & (yb <= 300)]),
      "note": "this file minus the old side-sheet bottom arris: they agree at mid-length; toward the front the old line (side photos only, depth weak) stays up to %.0f mm too far in, because the real arris swings out to close the scoop at the front leg" % float(np.max(B[:, 0] - ip(R["bottom_arris_xyz"], yb, 0)))}},
 "open": ["left side: assumed mirror (no trace from below yet)", "IMG_1490 (the lowest photo, 30 degrees below) sits 2.8 mm off the hard line and 1.5 mm off the bottom arris, same sign: its pose, not the edge (the other 13 photos fit within 1.7 mm)",
          "the top arris is eased; its radius is not measured", "on right-side photos the symmetric model sits about 2.5-3.4 mm inboard of these right-side curves (and up to 1.9 mm high at the back): the design is the left/right mean and this chair's right side measures wider (parts/seat_edge.json, parts/lr_skew.json); the section itself (height of the hard line above the underside, bevel angle) is carried over unchanged", "the tips of the scoop (behind y %d, in front of y %d) are a straight continuation (not traced; they run toward the leg joints)" % (C[0, 1], C[-1, 1]),
          "the underside is flat ACROSS by the undistorted reflection in IMG_1492 only; the close-ups IMG_1570-1576 are registered too badly to measure it"]}
json.dump(out, open(outf, "w"), indent=1)
print("wrote", outf)
print("bevel angle (y 150-410):", out["section"]["bevel_angle_deg"]); print("edge face:", out["section"]["edge_face"]); print("underside along the edge:", out["section"]["underside_along_edge"])
print("tips: back y %.1f (slope %.3f), front y %.1f (slope %.3f)" % (tb, sb, tf, sf)); print("height table:", [(float(a), float(b)) for a, b in zip(ytab.round(0), gtab.round(1))][::4])
print("max height %.1f mm at y %.0f; bevel run there %.1f mm" % (g.max(), C[g.argmax(), 1], g.max() / np.tan(np.radians(angle))))
print("checks:", json.dumps(out["checks"], indent=1))
