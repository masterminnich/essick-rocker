"""USAGE: python -I tools/overlay.py --images 1470,1490 | --all  [--points CSV] [--polylines JSON] [--obj MESH.obj]
          [--max-side 1600] [--crop-around LANDMARK --half 150 --zoom 3] [--out-dir DIR] + camera args
Draw chair-frame geometry onto photos through the solved cameras, distortion applied, display-oriented output.
  --points CSV     columns landmark_id,X,Y,Z (e.g. skeleton/points_pilot.csv)
  --polylines JSON [{"name":..., "points":[[x,y,z],...], "closed":false}, ...]
  --obj            mesh; every face/line edge is drawn
No occlusion handling (hidden geometry is drawn too).
Example: python -I tools/overlay.py --points skeleton/points_pilot.csv --images 1496,1510 --out-dir work/toolkit/pilot
"""
import argparse, csv, json
import sys, pathlib; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))  # noqa: E702
from tools._common import ROOT, add_camera_args, load_cams, img_name
import numpy as np


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    add_camera_args(ap)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--images"); g.add_argument("--all", action="store_true")
    ap.add_argument("--points"); ap.add_argument("--polylines"); ap.add_argument("--obj")
    ap.add_argument("--max-side", type=int, default=1600)
    ap.add_argument("--crop-around", default=None); ap.add_argument("--half", type=float, default=150)
    ap.add_argument("--zoom", type=float, default=3)
    ap.add_argument("--out-dir", default=str(ROOT / "work/toolkit/overlay"))
    ap.add_argument("--point-sheet", action="store_true",
                    help="also write <image>_points.jpg: one zoomed crop (--half/--zoom) per point that projects inside the photo")
    a = ap.parse_args()
    import cv2
    from rocker.overlay import Scene, render
    cams = load_cams(a)
    sc = Scene.from_obj(a.obj) if a.obj else Scene()
    pts = {}
    if a.points:
        for r in csv.DictReader(open(a.points)):
            pts[r["landmark_id"]] = np.array([float(r["X"]), float(r["Y"]), float(r["Z"])])
        sc.add_points(list(pts.values()), list(pts.keys()))
    if a.polylines:
        for pl in json.load(open(a.polylines)):
            sc.add_polyline(np.array(pl["points"]), closed=pl.get("closed", False))
    names = cams.names() if a.all else [img_name(s) for s in a.images.split(",")]
    out_dir = pathlib.Path(a.out_dir); out_dir.mkdir(parents=True, exist_ok=True)
    for n in names:
        if n not in cams.views:
            print(n, "not in model"); continue
        crop = None
        if a.crop_around:
            crop = (cams[n].project(pts[a.crop_around][None])[0], a.half, a.zoom)
        img = render(cams, n, sc, max_side=a.max_side, crop=crop)
        out = out_dir / (f"{n[:-4]}" + (f"_{a.crop_around}" if a.crop_around else "") + ".jpg")
        cv2.imwrite(str(out), img, [cv2.IMWRITE_JPEG_QUALITY, 90]); print(out)
        if a.point_sheet and pts:
            from rocker.images import render_crop
            tiles = []
            for lid, X in pts.items():
                uv = cams[n].project(X[None])[0]
                if not cams[n].in_image(uv[None])[0]:
                    continue
                t, _ = render_crop(n, uv, half=a.half, zoom=a.zoom, crosshair=True, marks=[], title=f"{n[4:8]} {lid}")
                tiles.append(t)
            if tiles:
                while len(tiles) % 4:
                    tiles.append(np.zeros_like(tiles[0]))
                sheet = np.vstack([np.hstack(tiles[i:i + 4]) for i in range(0, len(tiles), 4)])
                out2 = out_dir / f"{n[:-4]}_points.jpg"
                cv2.imwrite(str(out2), sheet, [cv2.IMWRITE_JPEG_QUALITY, 90]); print(out2)


if __name__ == "__main__":
    main()
