"""USAGE: tools/py.sh tools/seat_side_ends/model_outline.py SHAPES.glb OUT.json
The SEAT's plan outline on both sides: for each y (1 mm) the section of the mesh square to y; max x and min x (= top arris
half-width on the right / left, the faces are vertical or lean under), with the z of that point."""
import sys, json, numpy as np, trimesh
sc = trimesh.load(sys.argv[1]); T, gn = sc.graph['SEAT']; m = sc.geometry[gn].copy(); m.apply_transform(T)
out = []
for y in np.arange(0, 537, 1.0):
    s = m.section(plane_origin=[0, y, 0], plane_normal=[0, 1, 0])
    if s is None: continue
    v = s.vertices; xr, xl = v[:, 0].max(), v[:, 0].min(); zr = v[v[:, 0] > xr - 0.3, 2].max(); zl = v[v[:, 0] < xl + 0.3, 2].max()
    out.append({"y": float(y), "xR": float(xr), "zR": float(zr), "xL": float(xl), "zL": float(zl)})
json.dump(out, open(sys.argv[2], 'w')); print(len(out))
