"""USAGE: python -I tools/domino_ortho.py MODEL.glb OUTDIR -- orthophotos of each leg's outer face around the seat joint
(where the through-Domino ends show), from every solved photo that looks at that face within 55 deg. 0.25 mm/px; grid every 10 mm.
Plane = the model leg's outer face fitted at z 330-430 (chair frame mm). Small compute: one photo decoded at a time."""
import sys, json; sys.path.insert(0, ".")
import numpy as np, trimesh, cv2
from rocker.cameras import Cameras
from rocker.ortho import Plane, ortho
glb, out = sys.argv[1], sys.argv[2]; VOFF = float(sys.argv[3]) if len(sys.argv) > 3 else 0.0; LEGS = sys.argv[4].split(",") if len(sys.argv) > 4 else ["FLEG_R", "FLEG_L", "BLEG_R", "BLEG_L"]
sc = trimesh.load(glb); cams = Cameras.load()
rep = {}
for leg in LEGS:
    V = np.asarray(sc.geometry[leg].vertices); sgn = 1 if leg.endswith("R") else -1
    M = sc.geometry[leg]; Sm, fi = trimesh.sample.sample_surface(M, 40000, seed=1)
    nrm = M.face_normals[fi]; k = (nrm[:, 0] * sgn > 0.9) & (Sm[:, 2] > 300) & (Sm[:, 2] < 450)
    P = Sm[k]; c = P.mean(0); _, _, vt = np.linalg.svd(P - c); n = vt[2] * np.sign(vt[2][0] * sgn)
    v = np.array([0, 0, 1.0]); v -= n * (v @ n); u = np.cross(v, n) * sgn       # u forward-ish (+y), v up
    if u[1] < 0: u = -u
    pl = Plane(c, u, v); rep[leg] = {"origin": c.round(1).tolist(), "normal": n.round(3).tolist(), "photos": []}
    for nm in cams.names():
        cam = cams[nm]; C = cam.center
        d = C - c; ang = np.degrees(np.arccos((d @ n) / np.linalg.norm(d)))
        uv = cam.project(c[None])[0]
        if ang > 55 or not cam.in_image(uv[None], 200).all(): continue
        img = ortho(cams, nm, pl, (-70, 70), (-60 + VOFF, 60 + VOFF), 0.25)
        img = np.ascontiguousarray(img)
        for g in range(-60, 61, 10):
            col = int((g + 70) / 0.25); row = int((60 + VOFF - g) / 0.25)
            if 0 <= col < img.shape[1]: img[:, col] = (img[:, col] * 0.6 + np.array([0, 200, 255]) * 0.4 * (g % 50 == 0)).astype(img.dtype) if g % 50 == 0 else img[:, col]
            if 0 <= row < img.shape[0] and g % 50 == 0: img[row, :] = (img[row, :] * 0.6 + np.array([0, 200, 255]) * 0.4).astype(img.dtype)
        cv2.imwrite(f"{out}/{leg}_{nm.replace('.JPG','')}.jpg", cv2.cvtColor(img, cv2.COLOR_RGB2BGR) if img.ndim == 3 else img)
        rep[leg]["photos"].append([nm, round(float(ang), 1)])
json.dump(rep, open(f"{out}/planes.json", "w"), indent=1); print(json.dumps(rep, indent=1))
