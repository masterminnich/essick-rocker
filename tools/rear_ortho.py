"""USAGE: tools/py.sh tools/rear_ortho.py MODEL_shapes.glb OUTDIR [MAXANG 50] [RES 0.2] [PHOTOS a,b,c]
Orthophotos of each back leg's REAR face (the face that looks backward, -y) in two windows: at the seat joint and at the arm joint,
where the Domino ends show from behind (IMG_1620). One strip per leg and window: every solved photo that looks at that face within
MAXANG degrees, each resampled onto the plane fitted to the model leg's rear face in that window, RES mm per pixel, grid every 10 mm
(labelled in plane mm: u = to the chair's right, v = up the face, origin = the window's centre on the face).
Writes OUTDIR/<leg>_<window>.jpg and OUTDIR/planes.json (origin, u, v, normal of each plane in the chair frame, photos used and their
angle off the face normal). Read positions by eye on the grid; turn plane mm into chair mm with planes.json.
Compute: one photo decoded at a time (36 MB), small meshes; < 1 GB, under a minute."""
import sys, json; sys.path.insert(0, ".")
import numpy as np, trimesh, cv2
from rocker.cameras import Cameras
from rocker.ortho import Plane, ortho, load_raw
glb, out = sys.argv[1], sys.argv[2]; MAXANG = float(sys.argv[3]) if len(sys.argv) > 3 else 50.0; RES = float(sys.argv[4]) if len(sys.argv) > 4 else 0.2
ONLY = [f"IMG_{p}.JPG" for p in sys.argv[5].split(",")] if len(sys.argv) > 5 else None
WIN = {"seat": (315.0, (-45, 75), (-60, 60)), "arm": (490.0, (-50, 50), (-60, 60))}      # window: centre height z, u range, v range (u given for the LEFT leg: + = inboard)
sc = trimesh.load(glb); cams = Cameras.load(); rep = {}
for leg in ("BLEG_L", "BLEG_R"):
    M = sc.geometry[leg]; S, fi = trimesh.sample.sample_surface(M, 80000, seed=1); nr = M.face_normals[fi]; sgn = 1 if leg.endswith("R") else -1
    for w, (zc, ur, vr) in WIN.items():
        k = (nr[:, 1] < -0.8) & (np.abs(S[:, 2] - zc) < 45); P = S[k]; c = P.mean(0); _, _, vt = np.linalg.svd(P - c); n = vt[2] * np.sign(-vt[2][1])
        u = np.array([1.0, 0, 0]); u -= n * (u @ n); u /= np.linalg.norm(u); v = np.cross(n, u); v *= np.sign(v[2])     # u to the chair's right, v up; u x v = -n ... viewer stands on the n side
        ur_ = ur if sgn < 0 else (-ur[1], -ur[0]); pl = Plane(c, u, v); tiles = []; used = []
        for nm in (ONLY or cams.names()):
            C = np.asarray(cams[nm].center, float); d = C - c; ang = float(np.degrees(np.arccos((d @ n) / np.linalg.norm(d))))
            if ang > MAXANG or not cams[nm].in_image(cams[nm].project(c[None]), 150).all(): continue
            img = np.ascontiguousarray(ortho(cams, nm, pl, ur_, vr, RES))
            for g in range(-100, 101, 10):
                col = int(round((g - ur_[0]) / RES)); row = int(round((vr[1] - g) / RES)); colr = (0, 255, 255) if g == 0 else (255, 255, 0)
                if 0 <= col < img.shape[1]: cv2.line(img, (col, 0), (col, img.shape[0]), colr, 1); cv2.putText(img, str(g), (col + 2, 11), cv2.FONT_HERSHEY_SIMPLEX, 0.35, colr, 1)
                if 0 <= row < img.shape[0]: cv2.line(img, (0, row), (img.shape[1], row), colr, 1); cv2.putText(img, str(g), (2, row - 2), cv2.FONT_HERSHEY_SIMPLEX, 0.35, colr, 1)
            lab = f"{nm[4:8]}  {ang:.0f} deg  {np.linalg.norm(d):.0f} mm"; cv2.rectangle(img, (0, img.shape[0] - 18), (8 * len(lab) + 8, img.shape[0]), (255, 255, 255), -1)
            cv2.putText(img, lab, (4, img.shape[0] - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (0, 0, 0), 1, cv2.LINE_AA); tiles.append(img); used.append([nm, round(ang, 1), round(float(np.linalg.norm(d)))])
        if tiles:
            per = 4; rows = [np.hstack(tiles[i:i + per] + [np.zeros_like(tiles[0])] * (per - len(tiles[i:i + per]))) for i in range(0, len(tiles), per)]
            cv2.imwrite(f"{out}/{leg}_{w}.jpg", np.vstack(rows), [cv2.IMWRITE_JPEG_QUALITY, 92])
        rep[f"{leg}_{w}"] = {"origin": c.round(2).tolist(), "u": u.round(4).tolist(), "v": v.round(4).tolist(), "normal": n.round(4).tolist(), "u_range": list(ur_), "v_range": list(vr), "res_mm": RES,
                             "plane_fit_rms_mm": round(float(np.sqrt(np.mean(((P - c) @ n) ** 2))), 2), "photos": used}
        print(leg, w, json.dumps(rep[f"{leg}_{w}"]))
json.dump(rep, open(f"{out}/planes.json", "w"), indent=1)
