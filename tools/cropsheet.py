"""USAGE: python -I tools/cropsheet.py ITEM [ITEM ...] [--space raw|mid|disp] [--half 50] [--zoom 5] [--cols 2] [--out PATH]
          [--show-marks]
--landmark L: one tile per mark of L, centred on it (review/nudge loop with tools/mark.py nudge).
ITEM = IMAGE:X,Y[:TAG]  e.g. 1528:993,265:crestL . Same crops as tools/crop.py (upright, raw-coordinate grid labelled
x.../y..., red crosshair at the centre), tiled into one sheet so several points can be read in one look.
Each tile's footer shows image, tag and its centre in raw px.
Example: python -I tools/cropsheet.py 1528:993,265:crestL 1521:1065,190:crestL --space mid --half 40 --zoom 6
"""
import argparse
import sys, pathlib; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))  # noqa: E702
from tools._common import ROOT, img_name
import numpy as np


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("items", nargs="*")
    ap.add_argument("--landmark", default=None, help="comma list; one tile per existing mark of these landmarks, crosshair ON the mark")
    ap.add_argument("--space", default="raw", choices=["raw", "disp", "mid"])
    ap.add_argument("--half", type=float, default=50); ap.add_argument("--zoom", type=float, default=5)
    ap.add_argument("--cols", type=int, default=2); ap.add_argument("--grid", type=int, default=None)
    ap.add_argument("--show-marks", action="store_true")
    ap.add_argument("--out", default=str(ROOT / "work/toolkit/crops/sheet.png"))
    a = ap.parse_args()
    import cv2
    from rocker.images import to_raw, render_crop
    from rocker import marks as mk
    allm = mk.read() if a.show_marks else []
    tiles = []
    items = list(a.items)
    if a.landmark:
        a.space = "raw"
        want = a.landmark.split(",")
        rows = sorted((r for r in mk.read() if r["landmark_id"] in want), key=lambda r: (want.index(r["landmark_id"]), r["image"]))
        items += [f"{r['image']}:{r['x_raw']},{r['y_raw']}:{r['landmark_id']}" for r in rows]
    for it in items:
        parts = it.split(":")
        name = img_name(parts[0]); x, y = (float(v) for v in parts[1].split(","))
        tag = parts[2] if len(parts) > 2 else ""
        c = to_raw(name, (x, y), a.space)
        ms = [((r["x_raw"], r["y_raw"]), r["landmark_id"], (0, 255, 0)) for r in allm if r["image"] == name]
        img, _ = render_crop(name, c, half=a.half, zoom=a.zoom, grid=a.grid, marks=ms,
                             title=f"{name[4:8]} {tag} c=({c[0]:.0f},{c[1]:.0f})")
        tiles.append(img); print(f"{name} {tag} centre raw=({c[0]:.1f},{c[1]:.1f})")
    while len(tiles) % a.cols:
        tiles.append(np.zeros_like(tiles[0]))
    sheet = np.vstack([np.hstack(tiles[i:i + a.cols]) for i in range(0, len(tiles), a.cols)])
    cv2.imwrite(a.out, sheet); print(a.out)


if __name__ == "__main__":
    main()
