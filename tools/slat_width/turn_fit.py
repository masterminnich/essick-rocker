"""USAGE: work/toolkit/rk.sh tools/slat_width/turn_fit.py FIT.json OUT.json [--model parts/model_v23.glb]
Writes the side slats' turn (parts/slat_turn.json) from the per-band fits of tools/slat_width/fit.py.

Design = the LEFT/RIGHT MEAN turn per band, smoothed along z by a straight line (least squares weighted by 1/se^2, se from
fit.py's bootstrap over photos, L and R combined as sqrt(seL^2 + seR^2) / 2), tabulated every 25 mm. Both sides' band values
are stored unchanged, with photo counts and se. The centre slat's fitted turn is stored as the CONTROL: it should be 0 for a
flat slat, so its mean is the method's own bias estimate (not subtracted; see 'centre_control')."""
import sys, json, argparse
import numpy as np
ap = argparse.ArgumentParser(); ap.add_argument("fit"); ap.add_argument("out"); ap.add_argument("--model", default="parts/model_v23.glb")
ap.add_argument("--apply", action="store_true", help="set apply_in_build (the build then turns the side slats)")
a = ap.parse_args()
F = json.load(open(a.fit))
side = {s: [o for o in F["fits"] if o["slat"] == s] for s in ("SLAT_L", "SLAT_R", "SLAT_C")}
zL = [o["z"] for o in side["SLAT_L"]]; zR = [o["z"] for o in side["SLAT_R"]]
assert zL == zR, "L and R bands differ"
z = np.array(zL); tL = np.array([o["th_deg"] for o in side["SLAT_L"]]); tR = np.array([o["th_deg"] for o in side["SLAT_R"]])
sL = np.array([o["se_th_deg"] for o in side["SLAT_L"]]); sR = np.array([o["se_th_deg"] for o in side["SLAT_R"]])
tm = (tL + tR) / 2; sm = np.sqrt(sL ** 2 + sR ** 2) / 2
cf, cov = np.polyfit(z, tm, 1, w=1 / sm, cov="unscaled")
zd = np.arange(375, 1026, 25.0); td = np.polyval(cf, zd)
res = tm - np.polyval(cf, z)
tC = np.array([o["th_deg"] for o in side["SLAT_C"]]); sC = np.array([o["se_th_deg"] for o in side["SLAT_C"]])
cmean = float(np.sum(tC / sC ** 2) / np.sum(1 / sC ** 2))
blk = lambda s: {"z_mm": [float(v) for v in z if True], "turn_deg": [round(o["th_deg"], 2) for o in side[s]],
                 "se_deg": [round(o["se_th_deg"], 2) for o in side[s]], "photos": [o["photos"] for o in side[s]],
                 "width_fit_mm": [round(o["w"], 1) for o in side[s]], "width_model_v23_mm": [round(o["w_model"], 1) for o in side[s]],
                 "thickness_fit_mm": [round(o["t"], 1) for o in side[s]]}
out = {
    "about": "Turn of the two side slats (SLAT_L, SLAT_R) about their own length, measured directly from single photos. "
             "Added in model v24 (critique v23 item: side slats' inner front edge near the crest, +2.9 mm). Hub file; read by tools/build_model.py "
             "(slat block). Without this file the build makes flat (unturned) slats as before.",
    "apply_in_build": bool(a.apply),
    "apply_note": "false = measurement only: tools/build_model.py makes flat slats. The trial build with it applied (work/trial/v24, PR of "
                  "2026-11-21) passed the assembly check and improved the direct, pose-free held-out widths, but the critique's held-out "
                  "edge medians did not confirm it as a whole (see LEDGER 2026-11-21); applying it is the hub's call.",
    "convention": "turn_deg + = the slat's OUTER edge (the one away from the centre slat) FORWARD, i.e. the slat's face turns toward the "
                  "middle of the chair. Rotation about the section's own centre line (width and thickness unchanged, the centre of the section "
                  "stays where parts/slats.json puts it). SLAT_L is the mirror of SLAT_R, so one design value serves both. The centre slat is not turned.",
    "design": {"z_mm": [float(v) for v in zd], "turn_deg": [round(float(v), 2) for v in td],
               "fit": f"turn_deg = {cf[1]:.2f} {cf[0] * 100:+.3f} x z_mm / 100 (straight line through the L/R band means, 1/se^2 weights)",
               "slope_deg_per_100mm": round(float(cf[0] * 100), 3), "slope_se_deg_per_100mm": round(float(np.sqrt(cov[0, 0]) * 100), 3)},
    "tolerance_deg": 1.5,
    "tolerance_note": "+-1.5 deg covers the left/right disagreement about the line (rms of (L-R)/2 = "
                      f"{np.sqrt(np.mean(((tL - tR) / 2) ** 2)):.1f} deg), the band means' scatter about the line (rms {np.sqrt(np.mean(res ** 2)):.1f} deg) and the centre "
                      f"slat control ({cmean:+.1f} deg). At the slat edge 1 deg = w/2 x 1 deg = 0.4 mm.",
    "left": blk("SLAT_L"), "right": blk("SLAT_R"),
    "band_mean_deg": [round(float(v), 2) for v in tm], "band_mean_se_deg": [round(float(v), 2) for v in sm],
    "centre_control": {"turn_deg": [round(float(v), 2) for v in tC], "se_deg": [round(float(v), 2) for v in sC], "weighted_mean_deg": round(cmean, 2),
                       "note": "the centre slat (sign: its right edge forward) fitted the same way; a flat slat should read 0. Its weighted mean is "
                               "kept as the size of a possible method bias and is NOT subtracted (it is within 2 se of 0 and its sign convention is "
                               "not the side slats' mirror-symmetric one)."},
    "method": "tools/slat_width/measure.py: per photo, slat and station (z 350-1025 every 25 mm) both silhouette edges of the slat read on ONE "
              "line across the slat, square to the line of sight, in the same photo (pose-free width W; 0.1 mm samples averaged over 3 mm "
              "along the slat; edge = colour moving toward the background, moved outward past a visible side face; checked by eye at "
              "10 px/mm on single photos, native 1.7-2.4 px/mm). tools/slat_width/fit.py: W(alpha) = w|cos(alpha-th)| + t|sin(alpha-th)| "
              "fitted per 100 mm band over the 78 ranking photos (robust, 3.5 MAD rejection, bootstrap se over photos); the 15 "
              "held-out photos are only predicted. Eased arrises: the fit with rho = 2 mm and with t held at 8 or 10 mm moves the turn by "
              "under 1.5 deg (the turn is set by how W changes between photos looking from the left and from the right, which easing "
              "does not change); widths and thickness are NOT changed by this file.",
    "source": {"widths": "measurements/slat_widths_v23.npz (tools/py.sh -t 20 tools/slat_width/measure.py " + a.model + " measurements/slat_widths_v23.npz)",
               "fit": a.fit, "model": a.model},
}
json.dump(out, open(a.out, "w"), indent=1)
print("design", dict(zip(out["design"]["z_mm"][::4], out["design"]["turn_deg"][::4])), out["design"]["fit"], "slope se", out["design"]["slope_se_deg_per_100mm"])
print("band means", out["band_mean_deg"], "centre control", cmean)
print(out["tolerance_note"])
