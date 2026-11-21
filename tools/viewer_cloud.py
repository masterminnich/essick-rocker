"""USAGE: tools/py.sh tools/viewer_cloud.py [--out viewer/cloud] [--max-err 2.0] [--min-views 3]
Export the measured 3D points for the browser viewer's "Cloud vs model" layer (viewer/, PR "cloud heatmap").
The viewer colours each point by its signed distance to whatever model version is showing (computed in the browser),
so this only needs re-running when the clouds themselves change, never for a new model.

Layers (all in the chair frame, mm; table points z < --min-z dropped, chair box only):
  dense   work/dense/chair_dense.npy   tools/densify.py tracks, >= 3 photos (x y z r g b views rms_px angle_deg)
  sparse  work/solve/model             the COLMAP solve's own points3D, mapped by solve/metric_frame.json
  dots    seat/dots.csv                the seat session's dot targets (sub-mm sigma per dot)
Writes <out>/<layer>.bin (little-endian: float32 xyz[3N], float32 rms_px[N], float32 sigma_mm[N] (NaN = unknown),
uint8 rgb[3N], uint8 views[N]) and <out>/index.json (counts, byte offsets, provenance).
Compute: < 60k points, numpy only, < 200 MB, a few seconds."""
import sys, json, csv, argparse
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
import numpy as np

BOX = np.array([[-430, -580, -5], [430, 820, 1310]], float)          # same chair box as tools/densify.py
ap = argparse.ArgumentParser()
ap.add_argument("--out", default=str(ROOT / "viewer/cloud")); ap.add_argument("--max-err", type=float, default=2.0)
ap.add_argument("--min-views", type=int, default=3); ap.add_argument("--min-z", type=float, default=4.0)
ap.add_argument("--dense", default=str(ROOT / "work/dense/chair_dense.npy")); ap.add_argument("--model", default=str(ROOT / "work/solve/model"))
ap.add_argument("--metric", default=str(ROOT / "solve/metric_frame.json")); ap.add_argument("--dots", default=str(ROOT / "seat/dots.csv"))
a = ap.parse_args()
out = Path(a.out); out.mkdir(parents=True, exist_ok=True)


def keep(xyz, err, views):
    return np.all((xyz > BOX[0]) & (xyz < BOX[1]), 1) & (xyz[:, 2] > a.min_z) & (err <= a.max_err) & (views >= a.min_views)


def write(name, xyz, err, sigma, rgb, views, desc):
    n = len(xyz); f = out / f"{name}.bin"
    parts = [xyz.astype("<f4").ravel(), err.astype("<f4"), sigma.astype("<f4"), np.clip(rgb, 0, 255).astype(np.uint8).ravel(),
             np.clip(views, 0, 255).astype(np.uint8)]
    with open(f, "wb") as fh:
        for p in parts: fh.write(p.tobytes())
    print(f"{name}: {n} points, {f.stat().st_size / 1024:.0f} KB, median rms {np.median(err):.2f} px, median views {np.median(views):.0f}")
    return {"file": f.name, "n": int(n), "fields": ["xyz f32x3", "rms_px f32", "sigma_mm f32", "rgb u8x3", "views u8"], "desc": desc,
            "median_rms_px": round(float(np.median(err)), 3), "median_views": float(np.median(views))}


index = {"frame": "chair frame mm (+X right, +Y forward, +Z up, table Z=0)", "filters": {"max_rms_px": a.max_err, "min_views": a.min_views,
         "min_z_mm": a.min_z, "box_mm": BOX.tolist()}, "layers": {}}

D = np.load(a.dense)                                                   # x y z r g b views rms angle
m = keep(D[:, :3], D[:, 7], D[:, 6])
index["layers"]["dense"] = write("dense", D[m, :3], D[m, 7], np.full(m.sum(), np.nan), D[m, 3:6], D[m, 6],
                                 "Feature tracks matched across the photos (tools/densify.py), each seen in 3 or more photos")

import pycolmap
rec = pycolmap.Reconstruction(a.model); rec.update_point_3d_errors(); M = json.loads(Path(a.metric).read_text())
s, R, t = M["scale"], np.array(M["R"]), np.array(M["t"])
P = [(p.xyz, p.error, p.track.length(), p.color) for p in rec.points3D.values()]
xyz = s * np.array([p[0] for p in P]) @ R.T + t
err = np.array([p[1] for p in P]); views = np.array([p[2] for p in P]); rgb = np.array([p[3] for p in P])
m = keep(xyz, err, views)
index["layers"]["sparse"] = write("sparse", xyz[m], err[m], np.full(m.sum(), np.nan), rgb[m], views[m],
                                  "The camera solve's own points (COLMAP), mapped into the chair frame")

rows = list(csv.DictReader(open(a.dots)))
xyz = np.array([[float(r[k]) for k in ("x_mm", "y_mm", "z_mm")] for r in rows])
err = np.array([float(r["rms_px"]) for r in rows]); sig = np.array([float(r["s_normal_mm"]) for r in rows])
views = np.array([int(r["n_photos"]) for r in rows])
index["layers"]["dots"] = write("dots", xyz, err, sig, np.tile([20, 20, 20], (len(rows), 1)), views,
                                "Seat dot targets (seat session, seat/dots.csv): sub-mm, the best-measured points on the chair")
(out / "index.json").write_text(json.dumps(index, indent=1))
