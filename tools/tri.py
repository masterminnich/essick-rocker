"""USAGE: python -I tools/tri.py [--marks skeleton/marks.csv] [--out skeleton/points.csv] [--only L01,L02] [--sigma-px 1.0]
          [--outlier-px 6] [--residuals]   + camera args (--model, --metric, --image-scale)
Triangulate every landmark with >=2 marks. Writes one row per landmark: X,Y,Z (chair frame; COLMAP units if no
metric frame), n_marks, n_inliers, rms_px, max_px (raw full-res px), sigma (sqrt trace cov, 1-sigma), the three
error-ellipsoid semi-axes, max ray angle, outlier images. --residuals prints per-mark residuals.
Example: python -I tools/tri.py --out skeleton/points_pilot.csv --residuals
"""
import argparse, csv
import sys, pathlib; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))  # noqa: E702
from tools._common import ROOT, add_camera_args, load_cams


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    add_camera_args(ap)
    ap.add_argument("--marks", default=str(ROOT / "skeleton/marks.csv"))
    ap.add_argument("--out", default=str(ROOT / "skeleton/points.csv"))
    ap.add_argument("--only", default=None)
    ap.add_argument("--sigma-px", type=float, default=1.0, help="prior marking sigma (raw px)")
    ap.add_argument("--outlier-px", type=float, default=6.0)
    ap.add_argument("--residuals", action="store_true")
    ap.add_argument("--mm-per-unit", type=float, default=None,
                    help="PROVISIONAL scale for model units -> mm when no metric frame exists; adds *_mm_prov columns")
    a = ap.parse_args()
    from rocker import marks as mk
    from rocker.triangulate import triangulate
    cams = load_cams(a)
    groups = mk.by_landmark(mk.read(a.marks))
    only = set(a.only.split(",")) if a.only else None
    rows = []
    print(f"units: {cams.units}  model: {a.model}")
    print(f"{'id':10s} {'n':>2s} {'in':>2s} {'rms':>5s} {'max':>5s} {'sigma':>8s} {'axes':>26s} {'ang':>5s}  X Y Z")
    for lid, ms in sorted(groups.items()):
        if only and lid not in only:
            continue
        obs = [(m["image"], (m["x_raw"], m["y_raw"])) for m in ms if m["image"] in cams.views]
        if len(obs) < 2:
            print(f"{lid:10s} only {len(obs)} usable mark(s)"); continue
        r = triangulate(cams, obs, sigma_px=a.sigma_px, outlier_px=a.outlier_px)
        ax = r.sigma_axes
        outl = [n for n, o in zip(r.names, r.outlier) if o]
        print(f"{lid:10s} {len(obs):2d} {r.n_inliers:2d} {r.rms_px:5.2f} {r.max_px:5.2f} {r.sigma_mm:8.4g} "
              f"{ax[0]:8.3g} {ax[1]:8.3g} {ax[2]:8.3g} {r.ray_angle_deg:5.1f}  {r.X[0]:.4g} {r.X[1]:.4g} {r.X[2]:.4g}"
              + (f"  OUTLIERS {outl}" if outl else ""))
        if a.residuals:
            for n, uv, res, o in zip(r.names, r.marks, r.residuals_px, r.outlier):
                print(f"    {n} ({uv[0]:.1f},{uv[1]:.1f}) resid {res:.2f}px{' OUTLIER' if o else ''}")
        rows.append(dict(landmark_id=lid, X=r.X[0], Y=r.X[1], Z=r.X[2], units=cams.units, n_marks=len(obs), n_inliers=r.n_inliers,
                         rms_px=r.rms_px, max_px=r.max_px, sigma=r.sigma_mm, ax1=ax[0], ax2=ax[1], ax3=ax[2],
                         ray_angle_deg=r.ray_angle_deg, sigma_px_used=r.sigma_used_px, outliers=";".join(outl)))
        if a.mm_per_unit:
            k = a.mm_per_unit
            rows[-1].update(sigma_mm_prov=r.sigma_mm * k, ax1_mm_prov=ax[0] * k, ax2_mm_prov=ax[1] * k, ax3_mm_prov=ax[2] * k,
                            mm_per_unit_prov=k)
    if rows:
        with open(a.out, "w", newline="") as f:
            w = csv.DictWriter(f, list(rows[0])); w.writeheader()
            for r in rows:
                w.writerow({k: (f"{v:.6g}" if isinstance(v, float) else v) for k, v in r.items()})
        print("wrote", a.out)


if __name__ == "__main__":
    main()
