"""USAGE: python -I tools/audit_misc.py   (reads parts/model_v9.glb) -- rocker plane, leg feet vs rocker, slat ends vs seat, mesh validity. Tiny compute."""
import sys, json; sys.path.insert(0, ".")
import numpy as np, trimesh
from rocker.sideframe import side_plane
sc = trimesh.load("parts/model_v9.glb"); G = sc.geometry
o, u, v, n = side_plane(+1); print("side plane R: origin", np.round(o, 1), "u", np.round(u, 3), "v", np.round(v, 3), "normal", np.round(n, 3))
print("normal tilt from horizontal-x: lean deg (z comp)", round(float(np.degrees(np.arcsin(n[2]))), 2), " toe deg (y comp)", round(float(np.degrees(np.arcsin(n[1]))), 2))
R = G["ROCKER_R"]; V = R.vertices
for y0 in (-450, -300, -100, 50, 200, 450, 600):
    s = V[np.abs(V[:, 1] - y0) < 8]
    if len(s): print(f"rocker y{y0}: x {s[:,0].min():.1f}..{s[:,0].max():.1f}  z {s[:,2].min():.1f}..{s[:,2].max():.1f}")
# leg feet vs rocker top
for leg in ("FLEG_R", "BLEG_R"):
    L = G[leg].vertices; f = L[L[:, 2] < L[:, 2].min() + 6]
    s = V[(V[:, 1] > f[:, 1].min() - 5) & (V[:, 1] < f[:, 1].max() + 5)]
    print(leg, "foot x", np.round([f[:,0].min(), f[:,0].max()], 1), "y", np.round([f[:,1].min(), f[:,1].max()], 1), "z", np.round([f[:,2].min(), f[:,2].max()], 1),
          "| rocker there x", np.round([s[:,0].min(), s[:,0].max()], 1), "top z", np.round(s[:,2].max(), 1))
# slats bottom vs seat top
S = G["SEAT"].vertices
for sl in ("SLAT_C", "SLAT_R"):
    L = G[sl].vertices; b = L[L[:, 2] < L[:, 2].min() + 4]; cx, cy = b[:, 0].mean(), b[:, 1].mean()
    near = S[(np.abs(S[:, 0] - cx) < 25) & (np.abs(S[:, 1] - cy) < 25)]
    print(sl, "bottom z", round(float(b[:,2].min()), 1), "at x,y", round(float(cx)), round(float(cy)), "seat top there", round(float(near[:,2].max()), 1) if len(near) else None, "seat bottom there", round(float(near[:,2].min()),1) if len(near) else None)
    t = L[L[:, 2] > L[:, 2].max() - 4]; print(sl, "top z", round(float(t[:,2].max()),1))
# back-leg mesh self-intersection: are horizontal cuts simple loops?
from shapely.geometry import LineString
from shapely.ops import polygonize, unary_union
for z in range(260, 640, 20):
    seg = trimesh.intersections.mesh_plane(G["BLEG_R"], [0, 0, 1], [0, 0, z])[:, :, :2]
    polys = list(polygonize(unary_union([LineString(s) for s in seg])))
    print("BLEG cut z", z, "segments", len(seg), "loops", len(polys), "area", round(sum(p.area for p in polys)))
print("seat watertight", G["SEAT"].is_watertight, "open edges", len(trimesh.grouping.group_rows(G["SEAT"].edges_sorted, require_count=1)))
for k, g in G.items(): print(k, "watertight", g.is_watertight, "winding ok", g.is_winding_consistent, "faces", len(g.faces))
