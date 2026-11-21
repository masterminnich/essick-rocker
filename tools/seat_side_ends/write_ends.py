"""USAGE: python3 -I tools/seat_side_ends/write_ends.py [STATIONS.json (tools/seat_side_ends/data/stations_v22.json)] [--dry]
Writes (or replaces) the block `ends` in parts/seat_edge.json: the side edge's top arris (plan outline) traced at the two ends of the
design range, toward the back leg (y < 110) and toward the front leg (y > 400), where the model extrapolates. Check only: the model is
unchanged, so `design` and every other key of the file stay as they are. Idempotent. tools/seat_edge_fit.py keeps this block when it
rewrites the file."""
import sys, json, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[2]
args = [a for a in sys.argv[1:] if not a.startswith("--")]; dry = "--dry" in sys.argv
S = json.load(open(args[0] if args else ROOT / "tools/seat_side_ends/data/stations_v22.json"))
f = ROOT / "parts/seat_edge.json"; E = json.load(open(f))
ys = S["stations_y"]; r2 = lambda v: None if v is None else round(v, 2)
st = [{"y": y, "right_half_width": S["R"]["half_width"][i], "right_se": S["R"]["jackknife_se"][i], "left_half_width": S["L"]["half_width"][i], "left_se": S["L"]["jackknife_se"][i],
       "mean_half_width": S["mean"]["half_width"][i], "model_v22_half_width": S["model"]["half_width"][i], "mean_minus_model": S["model"]["mean_minus_model"][i],
       "shape_vs_model_right": S["shape_vs_model"]["R"][i], "shape_vs_model_left": S["shape_vs_model"]["L"][i], "arris_z_mean_minus_model_top": S["model"]["z_mean_minus_model"][i]}
      for i, y in enumerate(ys) if S["mean"]["half_width"][i] is not None]
E["ends"] = {
    "what": "top arris (plan outline) of the side edge at the two ends of design.y_range: toward the back leg (y 81-110) and toward the front leg (y 400-435); "
            "the build (tools/build_model.py) extrapolates the outline there: behind y 110 the point cloud's outline (shift 0.0) faded in over 60 mm, in front of y 400 a straight line to the front corner (268.0 at y 534.2)",
    "provenance": "traced, agrees within 0.5 mm",
    "result": "the model v22 outline sits on the wood: left/right mean minus model -0.26..+0.49 mm (worst +0.49 at y 85, at the back leg's face); each side's shape against the model "
              "(own offset at y 110 / 400 removed) within 0.6 mm; tolerance 1.6 mm (free curve); no change to the model",
    "method": "the plan solve of PR #8 (tools/edge_tri.py on work/parts/side{L,R}/sp, the settings of parts/seat_plan_seeds_{L,R}.json) with the seed carried on to each leg (tools/seat_side_ends/tri.sh); "
              "inside y 110-400 it reproduces the stored solve (right mean -0.02 / max 0.24 mm, left -0.03 / 0.62); spread = leave-one-photo-out (tools/seat_side_ends/jackknife.sh); "
              "each photo's own trace checked by eye at 10-12 px/mm (tools/seat_side_ends/check.py); numbers tools/seat_side_ends/analyse.py, data tools/seat_side_ends/data/stations_v22.json",
    "right": {"photos": S["R"]["photos"], "residual_rms_mm": S["R"]["residual_rms_mm"], "y_range": S["R"]["y_range"]},
    "left": {"photos": S["L"]["photos"], "residual_rms_mm": S["L"]["residual_rms_mm"], "y_range": S["L"]["y_range"]},
    "right_minus_left_mm": {"back_y85_110": [min(S["mean"]["right_minus_left"][:6]), max(S["mean"]["right_minus_left"][:6])],
                            "front_y400_430": [min(v for v in S["mean"]["right_minus_left"][6:] if v is not None), max(v for v in S["mean"]["right_minus_left"][6:] if v is not None)],
                            "note": "the chair's known left/right lean (parts/lr_skew.json); the model is the mean"},
    "stations": st,
    "height": "the traced arris sits 1.1-1.8 mm below the model's top at the outline at the back and 0.9-2.1 at the front (1.1 / 0.9 of that already at y 110 / 400, the plan solve's known offset on the round-over, plan_vs_side_check); "
              "inside the 2.5 mm tolerance of design.top_z_of_y; no change",
    "hidden": "y 45-78 (inside the back leg) and about y 446-500 (inside the front leg's lap) cannot be seen in any photo: assumed as built",
    "back_end_section": "by eye only (IMG_1489 right, IMG_1523 left, 1.3-2.6 px/mm): the hard line of parts/seat_scoop.json runs out into the bottom arris at the back leg as the model has it; the lens tips stay fitted",
    "open": ["front corner in front of the front leg (y 500-530), LEFT only (9 photos, residual 0.35 mm): half-width 265.1 at y 500 and 264.9 at y 528 against the model's 268.1 / 268.0, and the arris at z 423.4 / 428.4 "
             "against 420.0 / 418.8: the model rounds the corner's top down over its last 16 mm, the wood does not seem to; the right side did not solve (its traces jump at the leg); the corner is the front edge's "
             "(tools/seat_front_fit.py), so this is left for that item; figure figures/seat_side_ends/L_corner_lead.jpg"]}
if dry: print(json.dumps(E["ends"], indent=1)[:3000])
else: json.dump(E, open(f, "w"), indent=1); print("wrote", f, "ends:", len(st), "stations")
