"""USAGE: python -I tools/side_mirror.py parts/side_frame_L.json parts/side_frame_R.json [--out parts/side_frame.json]
Mirror-compare the left and right side-frame lines in the chair frame: the left line is reflected through the centre plane
(x -> -x) and compared with the right one in the fore-aft direction (chair Y at the same height Z) and in X. Prints per line
the mean and rms difference, and member widths side by side. --out writes the symmetric (averaged) lines as
{name without L/R: {"z": [...], "y": [...], "x_abs": [...], "half_diff_y_mm": rms/2}} = the design-intent side frame. Tiny compute."""
import json, sys, argparse, numpy as np
ap = argparse.ArgumentParser(); ap.add_argument("left"); ap.add_argument("right"); ap.add_argument("--out", default=None); a = ap.parse_args()
L = json.load(open(a.left))["lines"]; R = json.load(open(a.right))["lines"]; out = {}
for n in sorted(L):
    m = n.replace("L_", "R_", 1)
    if m not in R: continue
    A = np.array(L[n]["xyz"]); B = np.array(R[m]["xyz"]); A = A[np.argsort(A[:, 2])]; B = B[np.argsort(B[:, 2])]
    z = np.arange(max(A[0, 2], B[0, 2]), min(A[-1, 2], B[-1, 2]) + 1e-6, 10.0)
    yl, yr = np.interp(z, A[:, 2], A[:, 1]), np.interp(z, B[:, 2], B[:, 1]); xl, xr = -np.interp(z, A[:, 2], A[:, 0]), np.interp(z, B[:, 2], B[:, 0])
    dy = yr - yl; dx = xr - xl; key = n.replace("L_", "_", 1)
    out[key] = {"z": z.round(1).tolist(), "y": ((yl + yr) / 2).round(2).tolist(), "x_abs": ((xl + xr) / 2).round(2).tolist(), "lr_diff_y_mean_mm": round(float(dy.mean()), 2),
                "lr_diff_y_rms_about_mean_mm": round(float(dy.std()), 2), "lr_diff_x_mean_mm": round(float(dx.mean()), 2), "soft": "soft" in L[n]["provenance"] or "soft" in R[m]["provenance"]}
    print(f"{key:16s} z {z[0]:.0f}..{z[-1]:.0f}  R minus mirrored L, fore-aft: mean {dy.mean():+.2f}, rms about mean {dy.std():.2f}, max |d| {np.abs(dy).max():.2f} mm | across (x): mean {dx.mean():+.2f} mm" + ("  [soft line]" if out[key]["soft"] else ""))
if a.out: json.dump({"frame": "chair frame mm; right side shown, left is its mirror; y = mean of R and mirrored L", "lines": out}, open(a.out, "w"), indent=1)
