"""USAGE: python -I tools/audit_bleg.py parts/model_v9.glb figures/model_audit/back_leg_profile.png
Side-view audit of the back leg: the model's front and rear outline (fore-aft y vs height z) against the triangulated lines in
parts/side_frame.json, and the leg's lean angle and bend (deg per 100 mm) along its height. Shows where the model is measured
and where it is bridged. Tiny compute."""
import sys
import json
from pathlib import Path
import numpy as np, trimesh, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
sc = trimesh.load(sys.argv[1]); M = sc.geometry["BLEG_R"]; V = np.asarray(M.vertices)
z = np.arange(np.ceil(V[:, 2].min()) + 2, V[:, 2].max() - 25, 4.0); cen = []; front = []; rear = []
for z0 in z:                                                    # horizontal slices of the mesh
    seg = trimesh.intersections.mesh_plane(M, [0, 0, 1], [0, 0, z0]).reshape(-1, 3)
    front.append(seg[:, 1].max()); rear.append(seg[:, 1].min()); cen.append([seg[:, 0].mean(), 0, z0])
front, rear, cen = np.array(front), np.array(rear), np.array(cen); cen[:, 1] = (front + rear) / 2; n = len(z)
L = json.load(open("parts/side_frame.json"))["lines"]
from scipy.ndimage import uniform_filter1d
lean = np.degrees(np.arctan2(np.gradient(uniform_filter1d(cen[:, 1], 3)), np.gradient(z)))       # + = top leaning forward
s = np.r_[0, np.cumsum(np.linalg.norm(np.diff(cen[:, 1:], axis=0), axis=1))]
bend = np.gradient(lean, s) * 100                                                   # deg per 100 mm of leg
body = (z > 70) & (z < 1025)                                                        # leave out the foot cut and the crest-joint top (slice artefacts)
fig, ax = plt.subplots(1, 3, figsize=(17, 11), gridspec_kw={"width_ratios": [1.3, 1, 1]}, sharey=True)
a = ax[0]
a.fill_betweenx(z, rear, front, color="#e9b9a6", alpha=0.6, label=f"model back leg (side view, {Path(sys.argv[1]).stem})")
a.plot(front, z, color="#b5452a", lw=1.2); a.plot(rear, z, color="#b5452a", lw=1.2)
for k, c, lab in (("bleg_front_lo", "#1f6fb2", "triangulated front outline"), ("bleg_front_hi", "#1f6fb2", None),
                  ("bleg_rearfar_lo", "#2a9d5b", "triangulated rear arris"), ("bleg_rear_hi", "#2a9d5b", None), ("bleg_rear_lo", "#7fbf9a", "rear (soft line)")):
    a.plot(L[k]["y"], L[k]["z"], color=c, lw=3, label=lab, alpha=0.9)
# one smooth board: a single quintic through the measured front lines (lo + hi), and one through the rear arrises
fit = {}
for nm, ks, c in (("front", ("bleg_front_lo", "bleg_front_hi"), "#1f6fb2"), ("rear", ("bleg_rearfar_lo", "bleg_rear_hi"), "#2a9d5b")):
    zz = np.r_[L[ks[0]]["z"], L[ks[1]]["z"]]; yy = np.r_[L[ks[0]]["y"], L[ks[1]]["y"]]
    for deg in (3, 4, 5):
        cf = np.polyfit(zz, yy, deg); r = yy - np.polyval(cf, zz)
        fit[f"{nm}_deg{deg}"] = {"rms_mm": round(float(np.sqrt(np.mean(r ** 2))), 2), "max_mm": round(float(np.abs(r).max()), 2)}
    cf = np.polyfit(zz, yy, 5); zq = np.linspace(zz.min(), zz.max(), 300)
    a.plot(np.polyval(cf, zq), zq, "--", color=c, lw=1.4, label=f"one smooth curve through both measured {nm} lines")
    fit[nm + "_model_minus_smooth_in_band"] = round(float(np.max(np.abs(np.interp(zq[(zq > 270) & (zq < 608)], z, front if nm == "front" else rear) - np.polyval(cf, zq[(zq > 270) & (zq < 608)])))), 1)
for z0, z1, t in ((270, 608, "not measured: seat joint + arm joint"),):
    for aa in ax: aa.axhspan(z0, z1, color="#f2d36b", alpha=0.25, lw=0)
    a.text(-170, (z0 + z1) / 2, t, fontsize=9, va="center")
a.set_xlabel("fore-aft y (mm, + forward)"); a.set_ylabel("height z (mm)"); a.set_aspect("equal"); a.grid(alpha=0.3); a.legend(loc="upper right", fontsize=8)
a.set_title("Back leg in side view: model vs measured lines")
ax[1].plot(lean, z, color="#b5452a"); ax[1].set_xlabel("lean of leg centreline (deg, + = top forward)"); ax[1].grid(alpha=0.3); ax[1].set_title("Lean angle")
ax[2].plot(np.where(body, bend, np.nan), z, color="#b5452a"); ax[2].axvline(0, color="k", lw=0.6); ax[2].set_xlabel("bend (deg per 100 mm of leg)"); ax[2].grid(alpha=0.3); ax[2].set_title("Bend: a smooth board stays small and one-signed")
fig.tight_layout(); fig.savefig(sys.argv[2], dpi=110)
# the kinks: largest change of lean over 40 mm of height, and sign changes of bend
rep = {"stations": int(n), "lean_deg_at": {f"z{int(q)}": round(float(np.interp(q, z, lean)), 1) for q in (100, 250, 350, 400, 450, 500, 550, 600, 700, 850, 1000)},
       "bend_extremes_deg_per_100mm": [round(float(bend[body].min()), 1), round(float(bend[body].max()), 1)],
       "bend_sign_changes": int(np.sum(np.diff(np.sign(np.round(bend[body], 0))) != 0)),
       "width_fore_aft_at": {f"z{int(q)}": round(float(np.interp(q, z, front - rear)), 1) for q in (100, 250, 350, 400, 450, 500, 550, 600, 700, 850, 1000)}}
ib = np.flatnonzero(body); big = ib[np.argsort(-np.abs(bend[ib]))[:6]]; rep["worst_bends"] = [[round(float(z[i])), round(float(bend[i]), 1)] for i in sorted(big)]
rep["smooth_fit"] = fit; print(json.dumps(rep, indent=1))
