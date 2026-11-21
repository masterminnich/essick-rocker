"""USAGE: work/toolkit/rk.sh tools/seat_scoop/fit.py [SOLVED work/seat_scoop/solved_R.json] [OUT parts/seat_scoop.json] [SOLVED_LEFT]
Model v20 on (left-side check): work/toolkit/rk.sh tools/seat_scoop/fit.py work/seat_scoop_L/R/solved_R.json parts/seat_scoop.json work/seat_scoop_L/solved_L.json
  With SOLVED_LEFT the left side is reduced with the same formulas, stored in "left" and "left_vs_right", and "design" becomes the
  LEFT/RIGHT MEAN (height table and bevel angle; as parts/rocker_ends.json). Without it the file is the right-only PR #20 version.
Step 4 of 4 (strip -> snap -> solve -> fit). Turns the two triangulated edges of the seat's right side edge (the hard line and the bottom
arris, tools/seat_scoop/solve.py) into the section of the side edge between the legs and writes parts/seat_scoop.json:

  top arris -- edge face (vertical) -- HARD LINE -- under-bevel (constant angle) -- BOTTOM ARRIS -- underside (a plane)

The under-bevel is a scoop: deepest at mid-length, running out to nothing at the legs. It is described by ONE function of the station y,
the height of the hard line above the underside plane, plus one angle. build_model.py reads "design" only.
Numbers printed here are the ones quoted in LEDGER.md and the pull request."""
import sys, os, json, numpy as np
sys.path.insert(0, ".")
solved = sys.argv[1] if len(sys.argv) > 1 else "work/seat_scoop/solved_R.json"; outf = sys.argv[2] if len(sys.argv) > 2 else "parts/seat_scoop.json"; solved_l = sys.argv[3] if len(sys.argv) > 3 else None
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

def reduce_side(C, B, Pplan):
    """the fit.py formulas above for one side; C, B, Pplan with x made positive outboard. Returns the design curve and the section numbers."""
    pb = np.polyfit(B[:, 1] - 250.0, B[:, 2], 1); line = lambda y: np.polyval(pb, np.asarray(y, float) - 250.0); rb = B[:, 2] - line(B[:, 1])
    g = C[:, 2] - line(C[:, 1]); yb = B[:, 1]; cx, cz = ip(C, yb, 0), ip(C, yb, 2); run, drop = cx - B[:, 0], cz - B[:, 2]; ang = np.degrees(np.arctan2(drop, run))
    core = (yb >= 150) & (yb <= 410); angle = float(np.median(ang[core]))
    yy = np.arange(max(110.0, C[0, 1]), min(400.0, C[-1, 1]) + 1e-9, 5.0); lean = ip(C, yy, 0) - ip(Pplan, yy, 0); face_h = ip(Pplan, yy, 2) - ip(C, yy, 2)
    def tip(lo):
        m = (C[:, 1] <= C[0, 1] + 30) if lo else (C[:, 1] >= C[-1, 1] - 30); a, b = np.polyfit(C[m, 1], g[m], 1); return float(-b / a), float(a)
    (tb, sb), (tf, sf) = tip(True), tip(False)
    yd = np.unique(np.r_[np.ceil(tb / 5) * 5, np.arange(np.ceil(tb / 5) * 5, np.floor(tf / 5) * 5 + 1e-9, 5.0)]); gd = np.where(yd < C[0, 1], sb * (yd - tb), np.where(yd > C[-1, 1], sf * (yd - tf), np.interp(yd, C[:, 1], g)))
    gd = np.maximum(gd, 0.0)
    return {"g": g, "ang": ang, "core": core, "angle": angle, "lean": lean, "face_h": face_h, "yy": yy, "tb": tb, "tf": tf, "ytab": np.r_[tb, yd, tf], "gtab": np.r_[0.0, gd, 0.0],
            "pb": pb, "rb": rb, "run": run, "drop": drop}
if solved_l:
    SL = json.load(open(solved_l)); fl = np.array([-1.0, 1, 1]); Le = E["left"]
    CL, BL = np.array(SL["crescent"]["xyz"]), np.array(SL["bottom"]["xyz"])      # chair frame (x negative)
    qR = reduce_side(C, B, P); qL = reduce_side(CL * fl, BL * fl, np.array(Le["top_arris_plan_xyz"]) * fl)
    assert np.allclose(qR["gtab"], gtab) and abs(qR["angle"] - angle) < 1e-9          # same formulas as the right-only path above
    ybL = BL[:, 1]
    out["left"] = {
     "hard_line_xyz": CL[::5].round(2).tolist(), "bottom_arris_xyz": BL[::5].round(2).tolist(),
     "height_of_hard_line_above_underside_mm": np.c_[CL[::5, 1], qL["g"][::5]].round(2).tolist(),
     "bevel_run_drop_angle": np.c_[ybL, qL["run"], qL["drop"], qL["ang"]][::10].round(2).tolist(),
     "section": {"bevel_angle_deg": {**st(qL["ang"][qL["core"]]), "median": round(qL["angle"], 2), "y_range": [150, 410]},
                 "edge_face": {"hard_line_x_minus_top_arris_x_mm": st(qL["lean"]), "height_top_arris_to_hard_line_mm": st(qL["face_h"]), "y_range": [float(qL["yy"][0]), float(qL["yy"][-1])],
                               "note": "x made positive outboard (out +); top arris = left plan-sheet solve of parts/seat_edge.json"},
                 "underside_along_edge": {"z_at_y250": round(float(qL["pb"][1]), 2), "slope": round(float(qL["pb"][0]), 5), "tilt_deg": round(float(np.degrees(np.arctan(qL["pb"][0]))), 2),
                                          "straightness_rms_mm": round(float(np.sqrt(np.mean(qL["rb"] ** 2))), 2), "max_mm": round(float(np.abs(qL["rb"]).max()), 2)},
                 "tips_y": [round(qL["tb"], 1), round(qL["tf"], 1)], "max_height_mm": round(float(qL["g"].max()), 2), "y_of_max": float(CL[qL["g"].argmax(), 1])},
     "solve": {k: {"photos": SL[k]["photos"], "leave_one_photo_out_moves_curve_mm": {n: {"inner": v[0], "whole": v[1]} for n, v in SL[k]["leave_one_out_mm"].items()}, "degree": SL[k]["degree"],
                   "y_range": [float(SL[k]["xyz"][0][1]), float(SL[k]["xyz"][-1][1])]} for k in ("crescent", "bottom")},
     "note": "LEFT side, chair frame (x negative), measured in PR #26 with the same four steps as the right (inputs: tools/seat_scoop/inputs_L/). crescent = the hard line. "
             "Left vs right per station, with jackknife spreads: 'left_vs_right' (tools/seat_scoop/compare_lr.py)"}
    # the design: mean of the two sides' height tables (each zero outside its own tips) and of the two bevel angles
    lo, hi = min(qL["tb"], qR["tb"]), max(qL["tf"], qR["tf"]); yg = np.unique(np.r_[lo, np.arange(np.ceil(lo / 5) * 5, np.floor(hi / 5) * 5 + 1e-9, 5.0), hi])
    gL = np.interp(yg, qL["ytab"], qL["gtab"], left=0.0, right=0.0); gR = np.interp(yg, qR["ytab"], qR["gtab"], left=0.0, right=0.0); gM = (gL + gR) / 2
    angM = (qL["angle"] + qR["angle"]) / 2; D = out["design"]
    D["note"] = D["note"].replace("symmetric design version.", "symmetric design version: the LEFT/RIGHT MEAN of the two measured sides (model v20 on; v16-v19 used the right side mirrored).")
    D["y_range"] = [round(lo, 1), round(hi, 1)]
    H = D["hard_line_height_above_underside_of_y"]; H["y"] = yg.round(2).tolist(); H["height_mm"] = gM.round(2).tolist()
    H["provenance_ends"] = ("fitted: on each side, outside its measured range the curve is carried on as a straight line to zero (right: back tip y %.0f, front tip y %.0f; left: back %.0f, front %.0f); "
                            "the mean of the two is tabled; where the tips sit against the leg joints has not been checked" % (qR["tb"], qR["tf"], qL["tb"], qL["tf"]))
    H["left_minus_right_mm"] = {"y": yg[::2].round(1).tolist(), "value": (gL - gR)[::2].round(2).tolist(), "note": "each side's own table (zero outside its tips); the design is the mean, so each side's wood is about half of this away from the model"}
    D["bevel_angle_deg"] = {"value": round(angM, 1), "provenance": "triangulated", "tol_deg": 1.5, "left": round(qL["angle"], 2), "right": round(qR["angle"], 2), "note": "mean of the two sides' medians over y 150-410"}
    D["edge_face"]["note"] = ("vertical; measured outboard at the hard line: right %.1f mm (sd %.1f), left %.1f mm (sd %.1f), mean %.1f, inside the 1.5 mm tolerance of the outline; "
                              "the left top arris is the plan-sheet solve, itself +-1.5 mm") % (float(np.mean(qR["lean"])), float(np.std(qR["lean"])), float(np.mean(qL["lean"])), float(np.std(qL["lean"])), float((np.mean(qR["lean"]) + np.mean(qL["lean"])) / 2))
    D["left"] = {"provenance": "triangulated", "note": "measured (PR #26: 12 photos for the hard line, 7 for the bottom arris); the design above is the mean of left and right, so the model is symmetric"}
    if os.path.exists("work/seat_scoop_L/compare.json"):
        CMP = json.load(open("work/seat_scoop_L/compare.json")); out["left_vs_right"] = {k: CMP[k] for k in ("stations_y", "table", "scalars", "verdict", "photos", "rms_mm_per_photo_range", "leave_one_photo_out_max_mm_inner_whole")}
        out["left_vs_right"]["note"] = ("tools/seat_scoop/compare_lr.py: each quantity on each side relative to that side's own edge (x positive outboard), left minus right, with jackknife standard errors "
                                        "(each curve re-solved without each photo). verdict: limit 1.6 mm (free curve), 1.5 deg for the angle")
    out["method"] += " LEFT side (PR #26): the same four steps on 12 photos from the left (tools/seat_scoop/inputs_L/); the design is the mean of the two sides."
    out["checks"]["left_hard_line"] = "12 photos; rms in the photo %.2f-%.2f mm; leave-one-photo-out moves the curve by at most %.2f mm away from the ends (%.2f mm at the ends)" % (
        min(v["rms_mm"] for v in SL["crescent"]["photos"].values()), max(v["rms_mm"] for v in SL["crescent"]["photos"].values()), max(v[0] for v in SL["crescent"]["leave_one_out_mm"].values()), max(v[1] for v in SL["crescent"]["leave_one_out_mm"].values()))
    out["checks"]["left_bottom_arris"] = "7 photos; rms in the photo %.2f-%.2f mm; leave-one-photo-out at most %.2f mm away from the ends (%.2f mm at the ends)" % (
        min(v["rms_mm"] for v in SL["bottom"]["photos"].values()), max(v["rms_mm"] for v in SL["bottom"]["photos"].values()), max(v[0] for v in SL["bottom"]["leave_one_out_mm"].values()), max(v[1] for v in SL["bottom"]["leave_one_out_mm"].values()))
    out["checks"]["bottom_arris_vs_seat_edge_json_left"] = {"x_mm": st(BL[:, 0] * -1 - ip(Le["bottom_arris_xyz"], ybL, 0) * -1), "z_mm": st(BL[:, 2] - ip(Le["bottom_arris_xyz"], ybL, 2)),
        "note": "this file minus the old left side-sheet bottom arris, x positive outboard"}
    out["open"] = [o for o in out["open"] if not o.startswith("left side: assumed mirror")]
    out["open"].insert(0, "left vs right (PR #26): the left scoop is shallower: the hard line is %.1f mm above the underside at most on the left (y %d) against %.1f on the right (y %d); left minus right up to %.1f mm at y 150-300, "
                          "1.1-1.6 mm at y 300-390; the left edge face is 1.8-3.3 mm taller at y 160-400. The absolute heights of the two hard lines agree within 1.5 mm at y 140-390; the left bottom arris sits 2.2-2.7 mm higher at y 150-420 "
                          "(the same lean as parts/lr_skew.json and PR #25). Design = mean, so on either side's photos the model's hard line sits about 1-2 mm off the wood" % (
                          qL["g"].max(), CL[qL["g"].argmax(), 1], qR["g"].max(), C[qR["g"].argmax(), 1], float(-np.min(np.interp(np.arange(150, 301, 5.0), CL[:, 1], qL["g"]) - np.interp(np.arange(150, 301, 5.0), C[:, 1], qR["g"])))))
    print("LEFT: angle %.2f, max height %.2f at y %.0f, tips %.1f / %.1f;  RIGHT: angle %.2f, max %.2f at y %.0f, tips %.1f / %.1f;  DESIGN (mean): angle %.1f, max %.2f at y %.0f, y_range %s" % (
        qL["angle"], qL["g"].max(), CL[qL["g"].argmax(), 1], qL["tb"], qL["tf"], qR["angle"], qR["g"].max(), C[qR["g"].argmax(), 1], qR["tb"], qR["tf"], angM, gM.max(), yg[gM.argmax()], D["y_range"]))
json.dump(out, open(outf, "w"), indent=1)
print("wrote", outf)
print("bevel angle (y 150-410):", out["section"]["bevel_angle_deg"]); print("edge face:", out["section"]["edge_face"]); print("underside along the edge:", out["section"]["underside_along_edge"])
print("tips: back y %.1f (slope %.3f), front y %.1f (slope %.3f)" % (tb, sb, tf, sf)); print("height table:", [(float(a), float(b)) for a, b in zip(ytab.round(0), gtab.round(1))][::4])
print("max height %.1f mm at y %.0f; bevel run there %.1f mm" % (g.max(), C[g.argmax(), 1], g.max() / np.tan(np.radians(angle))))
print("checks:", json.dumps(out["checks"], indent=1))
