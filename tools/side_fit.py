"""USAGE: python -I tools/side_fit.py DIR --sheet PLANE.json --side L|R --out parts/side_frame_L.json
Collect the triangulated side-frame lines (DIR/<name>.json from tools/tri_lines.py / tools/edge_tri.py) into one parts file:
each line is faired with a robust polynomial u(v) (degree 3, or 2 for short lines), sampled every 10 mm, with its scatter about
the fair curve, its depth off the side plane, the photos used, the solve residual and a provenance tag. Also prints member
widths (front outline to rear lines) where a member has several lines. Tiny compute."""
import json, argparse, glob, os, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent; sys.path.insert(0, str(ROOT))
import numpy as np
from rocker.surface import load_surface
ap = argparse.ArgumentParser(); ap.add_argument("dir"); ap.add_argument("--sheet", required=True); ap.add_argument("--side", required=True); ap.add_argument("--out", required=True)
a = ap.parse_args(); S = load_surface(json.load(open(a.sheet))); out = {"side": a.side, "sheet": a.sheet, "units": "mm on the side plane: u forward, v up; depth + = towards the camera side (outboard)", "lines": {}}
for f in sorted(glob.glob(os.path.join(a.dir, "*.json"))):
    n = os.path.basename(f)[:-5]
    if n == "per_photo": continue
    j = json.load(open(f)); E = np.array(j[n]); d = np.array(j[n + "_depth_mm"]); info = j[n + "_info"]; o = np.argsort(E[:, 1]); E = E[o]; d = d[o]
    deg = 3 if np.ptp(E[:, 1]) > 180 else 2; keep = np.ones(len(E), bool)
    for _ in range(4):
        c = np.polyfit(E[keep, 1], E[keep, 0], deg); r = E[:, 0] - np.polyval(c, E[:, 1]); s = 1.4826 * np.median(np.abs(r[keep])) + 1e-6; keep = np.abs(r) < max(3 * s, 0.6)
    vs = np.arange(np.ceil(E[0, 1] / 10) * 10, E[-1, 1] + 1e-6, 10.0); us = np.polyval(c, vs); ds = np.interp(vs, E[:, 1], d)
    soft = info["residual_rms_mm"] > 1.0
    out["lines"][n] = {"uv": np.c_[us, vs].round(2).tolist(), "depth_mm": ds.round(1).tolist(), "xyz": S.to3d(np.c_[us, vs], ds).round(2).tolist(), "poly_u_of_v": c.tolist(),
                       "scatter_rms_mm": round(float(np.sqrt(np.mean(r[keep] ** 2))), 2), "photos": info["photos"], "solve_residual_rms_mm": round(info["residual_rms_mm"], 2),
                       "depth_solved": bool(info["triangulated"]), "provenance": "fitted (soft arris, +-2 mm)" if soft else "triangulated", "tol_mm": 2.0 if soft else 1.0}
    print(f"{n:18s} v {vs[0]:.0f}..{vs[-1]:.0f}  scatter {out['lines'][n]['scatter_rms_mm']:.2f} mm  solve residual {info['residual_rms_mm']:.2f}  depth {d[0]:+.1f}..{d[-1]:+.1f}  photos {','.join(info['photos'])}")
json.dump(out, open(a.out, "w"), indent=1)
Ls = out["lines"]
def at(n, v): P = np.array(Ls[n]["uv"]); return float(np.interp(v, P[:, 1], P[:, 0])) if P[0, 1] <= v <= P[-1, 1] else None
for front in [n for n in Ls if "_front_" in n]:
    m, seg = front.split("_front_"); rr = [n for n in (f"{m}_rear_{seg}", f"{m}_rearfar_{seg}") if n in Ls]; P = np.array(Ls[front]["uv"])
    for v in np.linspace(P[0, 1], P[-1, 1], 5).round():
        w = [(n.split("_")[1], at(front, v) - at(n, v)) for n in rr if at(n, v) is not None]
        print(f"  {m}_{seg} v {v:.0f}: front u {at(front, v):.1f}  " + "  ".join(f"width to {k} {x:.1f} mm ({x / 25.4:.2f} in)" for k, x in w))
