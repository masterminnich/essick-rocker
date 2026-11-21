"""USAGE: python -I tools/arm_top_ortho.py MODEL.glb OUTDIR [ARMS] -- orthophotos of each arm's top over its front leg (where the
round end grain of the arm / front-leg joint shows, IMG_1528), from every solved photo that sees that face within 60 deg.
Plane = the model arm's top face fitted within 45 mm of the leg's axis (chair frame mm). 0.2 mm/px, u (columns) -50..90 mm
~forward, v (rows, up) -60..60 mm = -x; grid every 10 mm, brighter at 0 and +-50. Axes in planes.json. Small compute: one photo at a time."""
import sys, json; sys.path.insert(0, ".")
import numpy as np, trimesh, cv2
from rocker.cameras import Cameras
from rocker.ortho import Plane, ortho
glb, out = sys.argv[1], sys.argv[2]; ARMS = sys.argv[3].split(",") if len(sys.argv) > 3 else ["ARM_R", "ARM_L"]
sc = trimesh.load(glb); cams = Cameras.load(); rep = {}; H = 45.0; RES = 0.2; UR = (-50.0, 90.0); VR = (-60.0, 60.0)
for arm in ARMS:
    S = arm[-1]; sgn = 1 if S == "R" else -1; A = sc.geometry[arm]; L = sc.geometry[f"FLEG_{S}"]
    LV = np.asarray(L.vertices); top = LV[LV[:, 2] > LV[:, 2].max() - 40]; lc = top.mean(0)          # leg top, centre
    Sm, fi = trimesh.sample.sample_surface(A, 60000, seed=1); nz = A.face_normals[fi][:, 2]
    k = (nz > 0.8) & (np.hypot(Sm[:, 0] - lc[0], Sm[:, 1] - lc[1]) < H)
    P = Sm[k]; c = P.mean(0); _, _, vt = np.linalg.svd(P - c); n = vt[2] * np.sign(vt[2][2])
    u = np.array([0, 1.0, 0]); u -= n * (u @ n); u /= np.linalg.norm(u); v = np.cross(n, u)            # u forward, v = n x u (-x side)
    pl = Plane(c, u, v); rep[arm] = {"origin": c.round(1).tolist(), "normal": n.round(3).tolist(), "u": u.round(3).tolist(), "v": v.round(3).tolist(),
                                     "leg_top_centre": lc.round(1).tolist(), "leg_top_in_plane_uv": [round(float((lc - c) @ u), 1), round(float((lc - c) @ v), 1)], "photos": []}
    for nm in cams.names():
        cam = cams[nm]; d = cam.center - c; ang = np.degrees(np.arccos((d @ n) / np.linalg.norm(d)))
        if ang > 60 or not cam.in_image(cam.project(c[None]), 200).all(): continue
        img = np.ascontiguousarray(ortho(cams, nm, pl, UR, VR, RES))
        for g in range(-100, 101, 10):                                         # grid in plane mm (ortho() returns BGR)
            w = 0.45 if g % 50 == 0 else 0.2; col = int((g - UR[0]) / RES); row = int((VR[1] - g) / RES)
            if 0 <= col < img.shape[1]: img[:, col] = (img[:, col] * (1 - w) + np.array([255, 200, 0]) * w).astype(img.dtype)
            if 0 <= row < img.shape[0]: img[row, :] = (img[row, :] * (1 - w) + np.array([255, 200, 0]) * w).astype(img.dtype)
        cv2.imwrite(f"{out}/{arm}_{nm.replace('.JPG', '')}.jpg", img)
        rep[arm]["photos"].append([nm, round(float(ang), 1)])
json.dump(rep, open(f"{out}/planes.json", "w"), indent=1); print(json.dumps(rep, indent=1))
