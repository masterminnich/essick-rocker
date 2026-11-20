"""USAGE:
  python -I tools/refine.py blob   IMAGE X Y [--radius 25]
  python -I tools/refine.py corner IMAGE X Y [--win 7]
  python -I tools/refine.py edges  IMAGE AX1 AY1 AX2 AY2 BX1 BY1 BX2 BY2 [--half 12]
  python -I tools/refine.py edgept IMAGE X Y DX DY [--half 15]
  add --save LANDMARK to write the refined point into skeleton/marks.csv (source=refined:<method>), and --crop to
  write a check crop with seed (red) and refined point (green).
All coordinates raw px. 'edges' intersects two straight edges, each given by two rough points along it.
  python -I tools/refine.py blob|corner --landmark L [--images 1502,1513] [--dry]
      refine every existing mark of landmark L in place (seed = current mark); only 'ok' results are written.
Example: python -I tools/refine.py blob 1470 1203 2210 --radius 20 --save L01 --crop
"""
import argparse, json
import sys, pathlib; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))  # noqa: E702
from tools._common import ROOT, img_name
import numpy as np


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("method", choices=["blob", "corner", "edges", "edgept"]); ap.add_argument("image", nargs="?")
    ap.add_argument("coords", type=float, nargs="*")
    ap.add_argument("--landmark", default=None); ap.add_argument("--images", default=None); ap.add_argument("--dry", action="store_true")
    ap.add_argument("--radius", type=float, default=25); ap.add_argument("--win", type=int, default=7)
    ap.add_argument("--half", type=float, default=None)
    ap.add_argument("--save", default=None); ap.add_argument("--note", default="")
    ap.add_argument("--crop", action="store_true"); ap.add_argument("--zoom", type=float, default=8)
    a = ap.parse_args()
    from rocker import refine as rf, marks as mk
    if a.landmark:
        imgs = {img_name(s) for s in a.images.split(",")} if a.images else None
        for m in mk.read():
            if m["landmark_id"] != a.landmark or (imgs and m["image"] not in imgs):
                continue
            seed = np.array([m["x_raw"], m["y_raw"]])
            xy, info = rf.blob(m["image"], seed, a.radius) if a.method == "blob" else rf.corner(m["image"], seed, a.win)
            print(m["image"], None if xy is None else [round(float(v), 2) for v in xy], json.dumps(info, default=str))
            if xy is not None and info.get("ok") and not a.dry:
                mk.upsert(a.landmark, m["image"], xy[0], xy[1], f"refined:{a.method}", m["note"])
        return
    name = img_name(a.image); c = a.coords
    if a.method == "blob":
        seed = np.array(c[:2]); xy, info = rf.blob(name, seed, a.radius)
    elif a.method == "corner":
        seed = np.array(c[:2]); xy, info = rf.corner(name, seed, a.win)
    elif a.method == "edges":
        e1 = (c[0:2], c[2:4]); e2 = (c[4:6], c[6:8]); seed = np.array(c[0:2])
        xy, info = rf.edges(name, e1, e2, half=a.half or 12)
    else:
        seed = np.array(c[:2]); xy, info = rf.edge_point(name, seed, c[2:4], half=a.half or 15)
    print(json.dumps({"xy_raw": None if xy is None else [round(float(v), 2) for v in xy], **info}, default=str))
    if xy is not None and a.save:
        mk.upsert(a.save, name, xy[0], xy[1], f"refined:{a.method}", a.note)
    if xy is not None and a.crop:
        import cv2
        from rocker.images import render_crop
        img, _ = render_crop(name, xy, half=40 * 8 / a.zoom, zoom=a.zoom, crosshair=False,
                             marks=[(seed, "seed", (0, 0, 255)), (xy, a.method, (0, 255, 0))])
        out = ROOT / f"work/toolkit/crops/refine_{name[:-4]}_{a.method}_{int(xy[0])}_{int(xy[1])}.png"
        cv2.imwrite(str(out), img); print(out)


if __name__ == "__main__":
    main()
