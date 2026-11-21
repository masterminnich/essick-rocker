"""USAGE: tools/py.sh tools/rocker_ends/ortho.py OUTDIR [MAXANG 62] [RES 0.25]
Step 1 of 3 (ortho -> trace -> fit). Orthophotos of the two ENDS of each rocker's outer side face (the tail behind the back leg and the
nose in front of the front leg), one image per photo, on the rocker's own face plane (work/parts/rocker{L,R}/o_plane.json, the plane the
rocker profile was traced on: u = along the rocker, forward positive; v = up; mm).
Every solved photo that looks at the face within MAXANG degrees and has the whole window in frame is used.
Writes OUTDIR/<side>_<end>_<photo>.png (no grid; pixel (col,row) = (u0 + col*RES, v1 - row*RES)), OUTDIR/<side>_<end>.jpg (all photos with a
10 mm grid) and OUTDIR/windows.json (window, plane, and for each photo: angle off the face normal, distance, and the camera's position in
plane coordinates u, v, height above the face: needed to know which edges that photo sees as a silhouette).
Compute: one photo decoded at a time (36 MB); < 1 GB, about a minute."""
import sys, json; sys.path.insert(0, ".")
import numpy as np, cv2
from rocker.cameras import Cameras
from rocker.ortho import Plane, ortho
out = sys.argv[1]; MAXANG = float(sys.argv[2]) if len(sys.argv) > 2 else 62.0; RES = float(sys.argv[3]) if len(sys.argv) > 3 else 0.25
WIN = {"tail": ((-545, -300), (100, 215)), "nose": ((545, 675), (55, 165))}       # the tail window runs well into the taper: the old profile is only good inward of about u -380
cams = Cameras.load(); rep = {}
for S in "LR":
    pj = json.load(open(f"work/parts/rocker{S}/o_plane.json")); pl = Plane(pj["origin"], pj["u"], pj["v"]); n = np.array(pj["n"])       # n = outward
    for end, (ur, vr) in WIN.items():
        c = pl.to3d([[np.mean(ur), np.mean(vr)]])[0]; corners = pl.to3d([[ur[0], vr[0]], [ur[0], vr[1]], [ur[1], vr[0]], [ur[1], vr[1]]]); tiles = []; used = {}
        for nm in cams.names():
            C = np.asarray(cams[nm].center, float); d = C - c; ang = float(np.degrees(np.arccos((d @ n) / np.linalg.norm(d))))
            if ang > MAXANG or not cams[nm].in_image(cams[nm].project(corners), 60).all(): continue
            img = np.ascontiguousarray(ortho(cams, nm, pl, ur, vr, RES)); cv2.imwrite(f"{out}/{S}_{end}_{nm[4:8]}.png", img); cuv = pl.to2d(C)[0]
            used[nm[4:8]] = {"angle_deg": round(ang, 1), "dist_mm": round(float(np.linalg.norm(d))), "cam_u": round(float(cuv[0])), "cam_v": round(float(cuv[1])), "cam_height": round(float((C - np.array(pj["origin"])) @ n))}
            t = cv2.resize(img, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC); k = 2 / RES
            for g in np.arange(np.ceil(ur[0] / 10) * 10, ur[1], 10):
                x = int((g - ur[0]) * k); cv2.line(t, (x, 0), (x, t.shape[0]), (255, 255, 0), 1); cv2.putText(t, str(int(g)), (x + 2, 11), cv2.FONT_HERSHEY_SIMPLEX, 0.36, (255, 255, 0), 1)
            for g in np.arange(np.ceil(vr[0] / 10) * 10, vr[1], 10):
                y = int((vr[1] - g) * k); cv2.line(t, (0, y), (t.shape[1], y), (255, 255, 0), 1); cv2.putText(t, str(int(g)), (2, y - 2), cv2.FONT_HERSHEY_SIMPLEX, 0.36, (255, 255, 0), 1)
            lab = f"{nm[4:8]}  {ang:.0f} deg  cam u {cuv[0]:.0f} v {cuv[1]:.0f}"; cv2.rectangle(t, (0, t.shape[0] - 20), (9 * len(lab) + 8, t.shape[0]), (255, 255, 255), -1)
            cv2.putText(t, lab, (4, t.shape[0] - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.46, (0, 0, 0), 1, cv2.LINE_AA); tiles.append(t)
        per = 2; rows = [np.hstack(tiles[i:i + per] + [np.zeros_like(tiles[0])] * (per - len(tiles[i:i + per]))) for i in range(0, len(tiles), per)]
        for i in range(0, len(rows), 3): cv2.imwrite(f"{out}/{S}_{end}_{i // 3}.jpg", np.vstack(rows[i:i + 3]), [cv2.IMWRITE_JPEG_QUALITY, 90])
        rep[f"{S}_{end}"] = {"u_range": ur, "v_range": vr, "res_mm": RES, "origin": pj["origin"], "u": pj["u"], "v": pj["v"], "n": pj["n"], "photos": used}
        print(S, end, len(used), json.dumps(used))
json.dump(rep, open(f"{out}/windows.json", "w"), indent=1)
