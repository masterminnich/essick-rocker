"""USAGE: python -I tools/review.py LANDMARK [--half 60] [--zoom 3] [--cols 4] [--out PATH] + camera args
One tile per mark of LANDMARK: the mark (green ring, crosshair centred on it) and the reprojection of the current
triangulated point (magenta ring) with each tile's residual in the footer. This is the check-and-nudge view:
fix a mark with tools/mark.py nudge, re-run.
Example: python -I tools/review.py CRS_L --half 50 --zoom 4
"""
import argparse
import sys, pathlib; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))  # noqa: E702
from tools._common import ROOT, add_camera_args, load_cams
import numpy as np


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    add_camera_args(ap)
    ap.add_argument("landmark"); ap.add_argument("--half", type=float, default=60); ap.add_argument("--zoom", type=float, default=3)
    ap.add_argument("--cols", type=int, default=4); ap.add_argument("--out", default=None)
    ap.add_argument("--marks", default=str(ROOT / "skeleton/marks.csv"))
    a = ap.parse_args()
    import cv2
    from rocker import marks as mk
    from rocker.images import render_crop
    from rocker.triangulate import triangulate
    cams = load_cams(a)
    ms = [m for m in mk.read(a.marks) if m["landmark_id"] == a.landmark and m["image"] in cams.views]
    r = triangulate(cams, [(m["image"], (m["x_raw"], m["y_raw"])) for m in ms]) if len(ms) >= 2 else None
    tiles = []
    for i, m in enumerate(ms):
        xy = np.array([m["x_raw"], m["y_raw"]])
        marks = [(xy, "", (0, 255, 0))]
        foot = f"{m['image'][4:8]} {a.landmark}"
        if r is not None:
            uv = cams.project(m["image"], r.X[None])[0]
            marks.append((uv, "", (255, 0, 255)))
            foot += f" res {r.residuals_px[i]:.1f}px" + (" OUT" if r.outlier[i] else "")
        img, _ = render_crop(m["image"], xy, half=a.half, zoom=a.zoom, marks=marks, title=foot)
        tiles.append(img)
    while len(tiles) % a.cols:
        tiles.append(np.zeros_like(tiles[0]))
    sheet = np.vstack([np.hstack(tiles[i:i + a.cols]) for i in range(0, len(tiles), a.cols)])
    out = a.out or str(ROOT / f"work/toolkit/crops/review_{a.landmark}.png")
    cv2.imwrite(out, sheet)
    if r is not None:
        print(f"{a.landmark}: n={len(ms)} rms {r.rms_px:.2f}px max {r.max_px:.2f}px")
    print(out)


if __name__ == "__main__":
    main()
