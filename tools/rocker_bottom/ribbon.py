"""USAGE: tools/py.sh tools/rocker_bottom/ribbon.py OUTDIR [MAXANG 62]
Step 1 of 3 (ribbon -> trace -> fit). The middle of each rocker's outer side face (u -345..590, between the two ends traced in PR #23)
resampled from every solved photo onto that rocker's own face plane (work/parts/rocker{L,R}/o_plane.json, the plane the profile and the
ends were traced on) as a RIBBON that follows the rocker: column = station u along the side's own top edge in parts/rocker_profile.json
(the left's `left.top`, the right's `right_aligned_to_left.top` carried back into the right's own frame), row = t, distance SQUARE TO THAT
TOP EDGE (t > 0 above it, t < 0 down the face). So the face height at a station is t(top arris) - t(bottom arris) read off one column of
one photo, whatever that photo's pose error (a slide of the whole photo moves both edges together).
Pixel (col, row) = station u0 + col*DU, t = T1 - row*DT; point = top(u) + t * n(u), n the unit normal of the top edge (up and out).
Writes OUTDIR/<S>_<photo>.png and OUTDIR/ribbons.json (grid, reference edges, and per photo: which columns are seen (in frame, camera on
the face's outer side, within MAXANG of square), angle and native pixels per mm every 5 mm, camera position in plane coordinates u, v,
height above the face: needed to know which photos see the bottom arris as a silhouette and which look onto the underside).
Compute: one photo decoded at a time (36 MB) plus a 1 M-point sample grid; < 0.6 GB, a few seconds per photo."""
import sys, json; sys.path.insert(0, ".")
import numpy as np, cv2
from rocker.cameras import Cameras
from rocker.ortho import Plane, load_raw
out = sys.argv[1]; MAXANG = float(sys.argv[2]) if len(sys.argv) > 2 else 62.0
U0, U1, DU, T1, T0, DT = -345.0, 590.0, 0.25, 12.0, -42.0, 0.2
RP = json.load(open("parts/rocker_profile.json")); RVL = RP["right_vs_left"]; UP = np.array(RP["u"])
def rigid_inv(q):
    th = np.radians(RVL["rotation_deg"]); c, s = np.cos(th), np.sin(th); d = np.asarray(q, float) - [RVL["shift_u_mm"], RVL["shift_v_mm"]]; return np.c_[c * d[:, 0] + s * d[:, 1], -s * d[:, 0] + c * d[:, 1]]
def own(S, key):
    """that side's edge `key` (top / bot) in its own plane frame, on the profile's 5 mm grid"""
    if S == "L": return np.c_[UP, RP["left"][key]]
    q = rigid_inv(np.c_[UP, RP["right_aligned_to_left"][key]]); return np.c_[UP, np.interp(UP, q[:, 0], q[:, 1])]
us = np.arange(U0, U1 + 1e-9, DU); ts = np.arange(T1, T0 - 1e-9, -DT); cams = Cameras.load(); rep = {"grid": {"u0": U0, "u1": U1, "du": DU, "t1": T1, "t0": T0, "dt": DT}, "sides": {}}
for S in "LR":
    pj = json.load(open(f"work/parts/rocker{S}/o_plane.json")); pl = Plane(pj["origin"], pj["u"], pj["v"]); n3 = np.array(pj["n"])        # n3 = outward
    top = own(S, "top"); bot = own(S, "bot"); vt = np.interp(us, top[:, 0], top[:, 1]); a = np.gradient(vt, us); nn = np.c_[-a, np.ones_like(a)] / np.hypot(1, a)[:, None]
    tb = -np.interp(us, bot[:, 0], (top[:, 1] - bot[:, 1])) * nn[:, 1]                      # the old bottom edge, square to the top edge (t), as the seed
    UV = np.c_[us, vt][None] + ts[:, None, None] * nn[None]; X = pl.to3d(UV.reshape(-1, 2))
    st = np.arange(0, len(us), 20); P5 = pl.to3d(np.c_[us[st], vt[st] - 13.0 * nn[st, 1]])     # mid-face points every 5 mm
    side = {"plane": pj, "top_v": vt[::20].round(3).tolist(), "seed_bottom_t": tb[::20].round(3).tolist(), "photos": {}}
    for nm in cams.names():
        V = cams[nm]; C = np.asarray(V.center, float); d = C - P5; ang = np.degrees(np.arccos(np.clip((d @ n3) / np.linalg.norm(d, axis=1), -1, 1)))
        e0 = V.project(pl.to3d(np.c_[us[st], vt[st] + T1 * nn[st, 1]])); e1 = V.project(pl.to3d(np.c_[us[st], vt[st] + T0 * nn[st, 1]]))
        ok5 = (ang < MAXANG) & V.in_image(e0, -20) & V.in_image(e1, -20)
        if ok5.sum() < 16: continue                                                            # fewer than 80 mm of the rocker seen
        p1 = V.project(P5 + pl.v * 1.0); p0 = V.project(P5); pxmm = np.hypot(*(p1 - p0).T)
        uv = V.project(X).astype(np.float32); img = cv2.remap(load_raw(cams, nm), uv[:, 0].reshape(len(ts), len(us)), uv[:, 1].reshape(len(ts), len(us)), cv2.INTER_LINEAR, borderValue=(0, 0, 0))
        okc = np.repeat(ok5, 20)[:len(us)]; img[:, ~okc] = 0; cv2.imwrite(f"{out}/{S}_{nm[4:8]}.png", img); cuv = pl.to2d(C)[0]
        side["photos"][nm[4:8]] = {"seen_5mm": ok5.astype(int).tolist(), "angle_deg_5mm": ang.round(1).tolist(), "px_per_mm_5mm": pxmm.round(2).tolist(),
                                   "cam_u": round(float(cuv[0]), 1), "cam_v": round(float(cuv[1]), 1), "cam_height": round(float((C - np.array(pj["origin"])) @ n3), 1)}
        sn = us[st][ok5]; print(S, nm[4:8], "seen u %.0f..%.0f (%d mm)" % (sn.min(), sn.max(), 5 * ok5.sum()), "angle %.0f-%.0f" % (ang[ok5].min(), ang[ok5].max()), "px/mm %.1f-%.1f" % (pxmm[ok5].min(), pxmm[ok5].max()),
                                    "cam u %.0f v %.0f h %.0f" % (cuv[0], cuv[1], side["photos"][nm[4:8]]["cam_height"]), flush=True)
    rep["sides"][S] = side
json.dump(rep, open(f"{out}/ribbons.json", "w"))
