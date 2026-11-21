"""USAGE: work/toolkit/rk.sh tools/arm_underside/fit.py SOLDIR OUT.json      (OUT normally parts/arm_underside.json)
Step 4 of 4 (strip -> snap -> solve -> fit). SOLDIR holds the six solve.py results, made by
    for j in above_R above_L obot_R inner_R obot_L inner_L; do
        work/toolkit/rk.sh tools/arm_underside/solve.py ${j#*_} tools/arm_underside/inputs/solve_$j.json SOLDIR/$j.json; done
above_*: the OUTER bottom arris from the photos above and level with the arm (its drop h AND its inboard offset a both fitted);
obot_*:  the same arris in the photos from below (a held at 0; a check, and the reference for the inner drop on the same photos);
inner_*: the INNER bottom arris (the lower silhouette from below), its inboard offset held at the arm's width (inner face vertical).
Every drop h is the VERTICAL distance below that arm's own outer top arris (parts/arms.json), as each photo sees it.
Design (what tools/build_model.py --arm-underside reads): outer drop = left/right mean of the above_* solves; inner drop = outer drop + the mean of the
two sides' cross drops (inner minus outer, each from its own photos from below). Ends: the photos stop at y 60 (the back leg) and
y 490 (the front end's rounding); the drops are continued straight (slope of the end 20 mm) to y 40 and y 510 and marked extrapolated."""
import sys, json, numpy as np
sd, outf = sys.argv[1:3]
S = {k: json.load(open(f"{sd}/{k}.json")) for k in ("above_R", "above_L", "obot_R", "inner_R", "obot_L", "inner_L")}
AJ = json.load(open("parts/arms.json")); pz = np.array(AJ["design"]["top_z_of_y"]["poly_in_(y-300)"])
ys = np.arange(40, 511, 5.0)
def on(k, key="h", y=ys, ext=True):
    """a solve curve at stations y; outside its range continued straight (ext) or NaN"""
    s = S[k]; sy = np.array(s["y"]); v = np.array(s[key] if key in s else s["jackknife_se"][key.split("_")[0]], float); out = np.interp(y, sy, v)
    for lo in (True, False):
        m = (y < sy[0]) if lo else (y > sy[-1]); sel = (sy <= sy[0] + 20) if lo else (sy >= sy[-1] - 20)
        if m.any(): out[m] = np.polyval(np.polyfit(sy[sel], v[sel], 1), y[m]) if ext else np.nan
    return out
seen = lambda k: (ys >= S[k]["y"][0]) & (ys <= S[k]["y"][-1])
hR, hL = on("above_R"), on("above_L"); seR, seL = on("above_R", "h_se", ext=False), on("above_L", "h_se", ext=False)
aR, aL = on("above_R", "a", ext=False), on("above_L", "a", ext=False)
hd = (hR + hL) / 2; vis_o = seen("above_R") & seen("above_L")
# cross drop: inner minus outer bottom arris, on the same photos from below (pose errors cancel); held at its end values beyond the seen range
def cross(si, so):
    yi = np.array(S[si]["y"]); d = np.array(S[si]["h"]) - np.interp(yi, S[so]["y"], S[so]["h"]); return np.interp(ys, yi, d), seen(si)
dR, vR = cross("inner_R", "obot_R"); dL, vL = cross("inner_L", "obot_L"); dd = (dR + dL) / 2; vis_i = vR & vL
slope = np.arctan(np.polyval(np.polyder(pz), ys - 300)); c_ = np.cos(slope)
bl = 0.5 * (np.abs(on("obot_R") - hR) + np.abs(on("obot_L") - hL))       # photos from below read the same arris up to 1.9 mm higher (an eased arris)
tol_o = np.maximum(0.8, 0.5 * np.abs(hR - hL) + 2 * np.nan_to_num(np.fmax(seR, seL), nan=1.0) + 0.5 * bl); tol_o[~vis_o] = np.maximum(tol_o[~vis_o], 2.5)
tol_i = np.maximum(1.5, 0.5 * np.abs(dR - dL) + 1.0); tol_i[~vis_i] = np.maximum(tol_i[~vis_i], 3.0)
r1 = lambda v: [None if not np.isfinite(x) else round(float(x), 2) for x in v]
chk = lambda k, h: {"y": [60, 100, 200, 300, 400, 440], "obot_minus_above_mm": [round(float(np.interp(y, S[k]["y"], S[k]["h"]) - np.interp(y, ys, h)), 2) for y in (60, 100, 200, 300, 400, 440)]}
old_v = 25.0 / c_
J = {
 "frame": "chair frame, mm: +X chair's right, +Y forward, +Z up, table top Z=0. Stations y along each arm (same y as parts/arms.json).",
 "what": "The arms' thickness and underside (parts/arms.json gives only their top). h_outer(y) = how far the OUTER bottom arris sits straight below "
         "the arm's outer top arris; h_inner(y) = how far the INNER bottom arris sits below that same outer top arris. The underside is the "
         "straight line across between the two (no crease is seen across it). Thickness 'vertical' is h; 'square' is square to the top line in "
         "side view (h x cos of the top's slope; the arm rises 14-23 degrees toward the front).",
 "method": "tools/arm_underside/ (strip -> snap -> solve -> fit). Each arm's outer side face is unrolled in every photo that sees it onto the "
           "vertical surface through that arm's own outer top arris (strip.py); the top arris and the bottom arris(es) are seeded by eye and "
           "snapped to the tone edge (snap.py); every photo's bottom line is registered on its OWN top-arris trace, so each drop is measured "
           "within one photo; all photos are then solved together for the drop h(y) and the inboard offset a(y) of the line (solve.py; "
           "Legendre polynomials, Huber 0.6 mm; photos from above and below separate the two). Jackknife over photos gives se. "
           "Inputs (seeds, snapped traces, trusted ranges): tools/arm_underside/inputs/.",
 "design": {
  "y": ys.tolist(),
  "h_outer_mm": r1(hd), "h_inner_mm": r1(hd + dd),
  "thickness_outer_vertical_mm": r1(hd), "thickness_outer_square_to_top_mm": r1(hd * c_),
  "old_model_vertical_mm": r1(old_v),
  "tolerance_outer_mm": r1(tol_o), "tolerance_inner_mm": r1(tol_i),
  "provenance_outer": ["triangulated (left/right mean)" if v else "extrapolated (straight on from the end 20 mm; not seen: back leg joint / front-end rounding)" for v in vis_o],
  "provenance_inner": ["triangulated (left/right mean cross drop; inner face assumed vertical)" if v else "extrapolated (cross drop held at its end value; not seen)" for v in vis_i],
  "outer_bottom_arris_from_below": "the photos from below put the same arris 0.6-1.4 mm LOWER at the back and 0.9-1.9 mm HIGHER from y 300 on than the photos from above and level (an eased arris seen from either side of its rounding); design keeps the from-above/level value, the tolerance carries half the difference",
  "outer_face": "vertical: the outer bottom arris sits straight below the outer top arris (a fitted -1.7..+3.1 mm on both arms, within its se); assumed exactly 0",
  "inner_face": "assumed vertical (the inner bottom arris straight below the inner top arris; the inner face itself is not seen from outside)",
  "build": "tools/build_model.py --arm-underside (OFF by default until joinery 5c is fixed, see PLAN.md): arm underside z = (outer top arris z) - (h_inner + t (h_outer - h_inner)), t = 0 inner .. 1 outer across the arm; replaces parts/arms.json 'thickness' (assumed 25 mm square to the top) in the build. parts/arms.json is unchanged."},
 "right": {"photos_above": list(S["above_R"]["photos"]), "photos_below": list(S["obot_R"]["photos"]), "photos_inner": list(S["inner_R"]["photos"]),
           "y_seen": [S["above_R"]["y"][0], S["above_R"]["y"][-1]], "h_outer_mm": r1(hR), "h_outer_se_mm": r1(seR), "a_outer_mm": r1(aR),
           "cross_drop_inner_minus_outer_mm": r1(np.where(vR, dR, np.nan)), "inner_y_seen": [S["inner_R"]["y"][0], S["inner_R"]["y"][-1]],
           "per_photo": S["above_R"]["photos"], "below_check": chk("obot_R", hR), "rms_inner_per_photo": S["inner_R"]["photos"]},
 "left": {"photos_above": list(S["above_L"]["photos"]), "photos_below": list(S["obot_L"]["photos"]), "photos_inner": list(S["inner_L"]["photos"]),
          "y_seen": [S["above_L"]["y"][0], S["above_L"]["y"][-1]], "h_outer_mm": r1(hL), "h_outer_se_mm": r1(seL), "a_outer_mm": r1(aL),
          "cross_drop_inner_minus_outer_mm": r1(np.where(vL, dL, np.nan)), "inner_y_seen": [S["inner_L"]["y"][0], S["inner_L"]["y"][-1]],
          "per_photo": S["above_L"]["photos"], "below_check": chk("obot_L", hL), "rms_inner_per_photo": S["inner_L"]["photos"]},
 "left_vs_right": {"h_outer_L_minus_R_mm": r1(np.where(vis_o, hL - hR, np.nan)), "cross_drop_L_minus_R_mm": r1(np.where(vis_i, dL - dR, np.nan))},
 "open": ["The back 20 mm (y 40-60, inside the back-leg joint) and the front end beyond y 490 are not seen: continued straight. A tape reading of the arm's "
          "thickness at its front end and just in front of the back leg (outer face, vertical) settles both (M6).",
          "The left inner bottom arris rests on ONE photo (IMG_1519, 10-13 degrees below); the left underside reads 3-9 mm lower on the inside than "
          "the right one does. Part of that may be the left arm's inner top arris (parts/arms.json left) running 12-14 mm narrower than the design near the back "
          "(width 27.5 mm at y 100 against 41): with the design width the left cross drop there reads about 2 mm less. A tape/caliper reading of both "
          "arms' thickness on the INSIDE face at y ~150 and y ~400 settles it."]}
json.dump(J, open(outf, "w"), indent=1)
for y in (40, 60, 100, 150, 200, 250, 300, 350, 400, 440, 480, 500, 510):
    i = int((y - 40) / 5)
    print(f"y {y:3d}: outer R {hR[i]:5.1f} L {hL[i]:5.1f} design {hd[i]:5.1f} (sq {hd[i] * c_[i]:5.1f}, tol {tol_o[i]:.1f})  cross R {dR[i]:+5.1f} L {dL[i]:+5.1f}  inner design {hd[i] + dd[i]:5.1f}  old {old_v[i]:5.1f}  {'seen' if vis_o[i] else 'extrap'}")
