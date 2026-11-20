"""USAGE: python -I tools/crop.py IMAGE X Y [--space raw|disp|mid] [--half 60] [--zoom 8] [--grid N] [--out PATH]
            [--show-marks] [--interp cubic|nearest]
Cut an upright (display-oriented) zoomed crop of a photo around a point, with a grid whose lines sit at constant RAW
sensor coordinates and are labelled 'x1234' / 'y2345', and a red crosshair at the centre. Read a feature's position
straight off the grid: those numbers ARE the raw coordinates to put in marks.csv (no orientation maths needed).
IMAGE: 1470 or IMG_1470.JPG. X Y: centre; --space mid = pixel coords in the 1600px work/mid viewing copies.
--show-marks draws existing marks of all landmarks from skeleton/marks.csv on the crop.
Example: python -I tools/crop.py 1470 812 655 --space mid --half 80 --zoom 6
"""
import argparse
import sys, pathlib; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))  # noqa: E702
from tools._common import ROOT, img_name
import cv2


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("image"); ap.add_argument("x", type=float); ap.add_argument("y", type=float)
    ap.add_argument("--space", default="raw", choices=["raw", "disp", "mid"])
    ap.add_argument("--half", type=float, default=60, help="half-width of crop in raw px")
    ap.add_argument("--zoom", type=float, default=8)
    ap.add_argument("--grid", type=int, default=None)
    ap.add_argument("--interp", default="cubic", choices=["cubic", "nearest", "linear"])
    ap.add_argument("--show-marks", action="store_true")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    from rocker.images import to_raw, render_crop
    from rocker import marks as mk
    name = img_name(a.image)
    c = to_raw(name, (a.x, a.y), a.space)
    ms = []
    if a.show_marks:
        ms = [((r["x_raw"], r["y_raw"]), r["landmark_id"], (0, 255, 0)) for r in mk.read() if r["image"] == name]
    img, info = render_crop(name, c, half=a.half, zoom=a.zoom, grid=a.grid, interp=a.interp, marks=ms)
    out = a.out or str(ROOT / f"work/toolkit/crops/{name[:-4]}_{int(c[0])}_{int(c[1])}_z{a.zoom:g}.png")
    cv2.imwrite(out, img)
    print(f"{out}  centre raw=({c[0]:.1f},{c[1]:.1f}) grid={info['grid']}px orient={info['orient']}")


if __name__ == "__main__":
    main()
