"""USAGE: work/toolkit/rk.sh tools/seat_side_ends/analyse.py MODEL_OUTLINE.json OUT.json
The seat's plan outline (top arris half-width) at the two ends of the side edge, where parts/seat_edge.json's design (y 110-400) stops:
toward the back leg (y < 110) and toward the front leg (y > 400). Reads the extended solves work/seatside/{R,L}_ext.json and the
leave-one-photo-out solves work/seatside/jk/{R,L}_<photo>.json (tools/seat_side_ends/jackknife.sh), the stored solves of PR #8
(work/parts/side{R,L}/tsp/seat{R,L}_plan.json) and a model's outline (tools/seat_side_ends/model_outline.py). Writes the station table
and the summary numbers. Tiny compute."""
import sys, json, glob, numpy as np
mo_f, out = sys.argv[1:3]
E = json.load(open("parts/seat_edge.json")); D = E["design"]; pw = lambda y: np.polyval(D["top_half_width_of_y"]["poly_in_(y-250)"], np.asarray(y) - 250.0)
mo = json.load(open(mo_f)); my = np.array([r["y"] for r in mo]); mR = np.array([r["xR"] for r in mo]); mL = -np.array([r["xL"] for r in mo])
model = lambda y: np.interp(y, my, (mR + mL) / 2)
mz = lambda y: np.interp(y, my, (np.array([r["zR"] for r in mo]) + np.array([r["zL"] for r in mo])) / 2)   # model top at the outline


def line(f, s):
    P = np.array(json.load(open(f))[f"seat{s}_plan_xyz"]); P = P[np.argsort(P[:, 1])]; return P


def hw(P, y): return np.interp(y, P[:, 1], np.abs(P[:, 0]), left=np.nan, right=np.nan)


def zz(P, y): return np.interp(y, P[:, 1], P[:, 2], left=np.nan, right=np.nan)


ys = np.r_[np.arange(85, 111, 5.0), np.arange(400, 441, 5.0)]
res = {"stations_y": ys.tolist()}; ext = {}
for s in "RL":
    P = line(f"work/seatside/{s}_ext.json", s); ext[s] = P
    jk = [line(f, s) for f in sorted(glob.glob(f"work/seatside/jk/{s}_*.json")) if not f.endswith("_dump.json")]
    J = np.array([hw(Q, ys) for Q in jk]); n = len(jk); se = np.sqrt((n - 1) / n * np.nansum((J - np.nanmean(J, 0)) ** 2, 0))
    old = line(f"work/parts/side{s}/tsp/seat{s}_plan.json", s); yo = np.arange(110, 401, 5.0)
    info = json.load(open(f"work/seatside/{s}_ext.json"))[f"seat{s}_plan_info"]
    res[s] = {"photos": info["photos"], "residual_rms_mm": round(info["residual_rms_mm"], 2), "y_range": [round(float(P[0, 1]), 1), round(float(P[-1, 1]), 1)],
              "half_width": np.round(hw(P, ys), 2).tolist(), "z": np.round(zz(P, ys), 2).tolist(), "jackknife_se_z": np.round(np.sqrt((n - 1) / n * np.nansum((np.array([zz(Q, ys) for Q in jk]) - np.nanmean(np.array([zz(Q, ys) for Q in jk]), 0)) ** 2, 0)), 2).tolist(), "jackknife_se": np.round(se, 2).tolist(), "jackknife_range": np.round(np.nanmax(J, 0) - np.nanmin(J, 0), 2).tolist(),
              "ext_minus_stored_in_y110_400_mm": {"mean": round(float(np.mean(hw(P, yo) - hw(old, yo))), 2), "maxabs": round(float(np.max(np.abs(hw(P, yo) - hw(old, yo)))), 2)},
              # shape relative to the side's own edge: the half-width minus its own value at the end of the design range (y 110 / 400)
              "minus_own_at_range_end": np.round(np.where(ys < 250, hw(P, ys) - hw(P, 110.0), hw(P, ys) - hw(P, 400.0)), 2).tolist()}
mean = (np.array(res["R"]["half_width"]) + np.array(res["L"]["half_width"])) / 2; mod = model(ys)
se_mean = 0.5 * np.hypot(np.array(res["R"]["jackknife_se"]), np.array(res["L"]["jackknife_se"]))
res["mean"] = {"half_width": np.round(mean, 2).tolist(), "se": np.round(se_mean, 2).tolist(), "right_minus_left": np.round(np.array(res["R"]["half_width"]) - np.array(res["L"]["half_width"]), 2).tolist()}
zmean = (np.array(res["R"]["z"]) + np.array(res["L"]["z"])) / 2
res["model"] = {"source": mo_f, "half_width": np.round(mod, 2).tolist(), "mean_minus_model": np.round(mean - mod, 2).tolist(), "top_z": np.round(mz(ys), 2).tolist(), "z_mean_minus_model": np.round(zmean - mz(ys), 2).tolist(), "z_right_minus_left": np.round(np.array(res["R"]["z"]) - np.array(res["L"]["z"]), 2).tolist(),
                "z_design_poly": np.round(np.polyval(D["top_z_of_y"]["poly_in_(y-250)"], np.clip(ys, 110, 400) - 250), 2).tolist()}
# shape against the model, each side relative to its own value at the range end (removes the L/R lean of PR #25 / #26)
mod_rel = np.where(ys < 250, mod - model(110.0), mod - model(400.0))
res["shape_vs_model"] = {s: np.round(np.array(res[s]["minus_own_at_range_end"]) - mod_rel, 2).tolist() for s in "RL"}
json.dump(res, open(out, "w"), indent=1)
print("   y |  R      se  |  L      se  | R-L  | mean  model  mean-model | shape R  L (vs model, rel. to own y110/400)")
for i, y in enumerate(ys):
    print(f"{y:5.0f} | {res['R']['half_width'][i]:6.1f} {res['R']['jackknife_se'][i]:4.2f} | {res['L']['half_width'][i]:6.1f} {res['L']['jackknife_se'][i]:4.2f} | {res['mean']['right_minus_left'][i]:+4.1f} | "
          f"{mean[i]:6.1f} {mod[i]:6.1f} {mean[i] - mod[i]:+5.2f}  | {res['shape_vs_model']['R'][i]:+5.2f} {res['shape_vs_model']['L'][i]:+5.2f}")
print("z: arris R, L, mean, model top at outline, mean-model, design poly (clipped)")
for i, y in enumerate(ys): print(f"{y:5.0f} | {res['R']['z'][i]:6.1f} {res['L']['z'][i]:6.1f} {zmean[i]:6.1f} {mz(y):6.1f} {zmean[i]-mz(y):+5.2f} {res['model']['z_design_poly'][i]:6.1f}")
for s in "RL": print(s, res[s]["y_range"], res[s]["residual_rms_mm"], "ext - stored in y110-400:", res[s]["ext_minus_stored_in_y110_400_mm"], "n photos", len(res[s]["photos"]))
