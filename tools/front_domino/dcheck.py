"""Front-leg Domino visible end vs the leg's outer face, in a built model. Usage: tools/py.sh work/fdom/dcheck.py PREFIX [dominos.json]
PREFIX e.g. parts/model_v18 (reads PREFIX.glb and PREFIX_shapes.glb). Prints, per leg: the outer-face plane, the visible end's
area-weighted centroid (u forward along the face, v up), the outer flat face's two edges at that height, offset = end centre - face middle."""
import sys, json; sys.path.insert(0, ".")
import numpy as np, trimesh
pre = sys.argv[1]; dj = sys.argv[2] if len(sys.argv) > 2 else "parts/dominos.json"
sh = trimesh.load(f"{pre}_shapes.glb"); jn = trimesh.load(f"{pre}.glb"); out = {}
c0 = np.array(json.load(open(dj))["joints"]["front_leg"]["centre_xyz"], float)
for S, sgn in (("R", 1), ("L", -1)):
    M = sh.geometry[f"FLEG_{S}"]; Sm, fi = trimesh.sample.sample_surface(M, 40000, seed=1); nrm = M.face_normals[fi]
    k = (nrm[:, 0] * sgn > 0.9) & (Sm[:, 2] > 300) & (Sm[:, 2] < 450); P = Sm[k]; c = P.mean(0)
    _, _, vt = np.linalg.svd(P - c); n = vt[2] * np.sign(vt[2][0] * sgn)
    v = np.array([0, 0, 1.0]); v -= n * (v @ n); v /= np.linalg.norm(v); u = np.cross(v, n) * sgn
    if u[1] < 0: u = -u
    Dm = jn.geometry[f"DOMINO_F{S}"]; fn = Dm.face_normals; cap = fn @ n > 0.95; A = Dm.area_faces[cap]; T = Dm.triangles_center[cap]
    g = (A[:, None] * T).sum(0) / A.sum(); gu, gv, gn = (g - c) @ u, (g - c) @ v, (g - c) @ n
    E = Dm.vertices[np.unique(Dm.faces[cap])]; eu = (E - c) @ u
    sec = np.asarray(M.section(plane_origin=c + gv * v, plane_normal=v).vertices); d = (sec - c) @ n; us = (sec - c) @ u
    flat = us[np.abs(d - d.max()) < 0.5]; lo, hi = flat.min(), flat.max(); mid = (lo + hi) / 2
    dc = c0.copy(); dc[0] = abs(dc[0]) * sgn; cu = (dc - c) @ u
    out[S] = dict(end_u=round(gu, 2), end_v=round(gv, 2), end_off_face=round(gn, 2), end_area=round(A.sum(), 1), end_u_extent=[round(eu.min(), 2), round(eu.max(), 2)],
                  face_rear=round(lo, 2), face_front=round(hi, 2), face_width=round(hi - lo, 2), face_mid=round(mid, 2), offset=round(gu - mid, 2),
                  json_centre_u=round(cu, 2), json_centre_offset=round(cu - mid, 2), plane=dict(origin=c.round(3).tolist(), u=u.round(4).tolist(), v=v.round(4).tolist(), n=n.round(4).tolist()))
    print(S, {k: x for k, x in out[S].items() if k != "plane"})
json.dump(out, open(f"work/fdom/dcheck_{pre.split('/')[-1]}.json", "w"), indent=1)
