"""USAGE: tools/py.sh -t 20 tools/rocker_thickness/ribbon.py MODEL.glb OUTDIR
Step 1 (ribbon -> trace -> fit). The rocker's TOP face resampled from every solved photo onto the model's own top face:
column = station u along the design top edge (the build's outline: rocker_profile.json mean_top between the ends of
rocker_ends.json, carried into the design frame by to_mean), row = d, the distance INWARD from the model's outer face, square to
the side plane (the model's top face is the side outline extruded square across: d 0 = outer arris, d 31 = inner arris).
Pixel (col, row): u = U0 + col*DU, d = D0 + row*DD. Rows run outer (top of the image) to inner.
Per column it also stores whether the photo sees that column clean: the joined model's painter's render (as tools/critique)
shows this rocker at d 2, 15 and 29 (depth within 10 mm) and at d -8 and d 39 nothing in front (background or this rocker),
the camera above the top face by >= MINEL degrees, the column inside the frame; plus the local elevation, which side of the
rocker the camera is on (outboard / inboard) and native pixels per mm along d.
Writes OUTDIR/<S>_<photo>.png and OUTDIR/ribbons.json. Compute: one photo decoded at a time; ~0.9 GB peak, ~2 s a photo."""
import sys, json
from pathlib import Path
sys.path.insert(0, "."); sys.path.insert(0, "tools/critique")
import numpy as np, cv2
from common import load_model, render_mesh
from rocker.cameras import Cameras
from rocker.ortho import load_raw
from rocker.sideframe import side_plane

glb, out = sys.argv[1], Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True)
MINEL = 8.0
U0, U1, DU, D0, D1, DD = -495.0, 640.0, 1.0, -12.0, 46.0, 0.1
# the build's top edge (tools/build_model.py, rocker block), design frame
rp = json.load(open("parts/rocker_profile.json")); U = np.array(rp["u"]); rtop = np.array(rp["mean_top"]); RVL = rp["right_vs_left"]
ends = json.load(open("parts/rocker_ends.json"))["design"]; tl, ns = ends["tail"], ends["nose"]
mid = (U > tl["blend_u"][0]) & (U < ns["blend_u"][0])
def rigid_inv(q, th_deg, su, sv):
    th = np.radians(th_deg); c, s_ = np.cos(th), np.sin(th); d = np.asarray(q, float) - [su, sv]; return np.c_[c * d[:, 0] + s_ * d[:, 1], -s_ * d[:, 0] + c * d[:, 1]]
top = rigid_inv(np.r_[np.array(tl["top"])[::-1], np.c_[U, rtop][mid], np.array(ns["top"])], RVL["rotation_deg"] / 2, RVL["shift_u_mm"] / 2, RVL["shift_v_mm"] / 2)
top = top[np.argsort(top[:, 0])]
us = np.arange(U0, U1 + 1e-9, DU); ds = np.arange(D0, D1 + 1e-9, DD)
vt = np.interp(us, top[:, 0], top[:, 1]); slope = np.gradient(vt, us)
inr = (us >= top[0, 0]) & (us <= top[-1, 0])

meshes = load_model(glb); RV, RF, RP, RN = render_mesh(meshes)
RFN = np.cross(RV[RF[:, 1]] - RV[RF[:, 0]], RV[RF[:, 2]] - RV[RF[:, 0]]); RFC = RV[RF].mean(1)
H2, W2 = 1512, 2016
def render(V):
    C = V.center; uv, z = V.project(RV, return_depth=True)
    fr = np.einsum("ij,ij->i", RFN, C - RFC) > 0
    ok = fr & np.isfinite(uv[RF]).all((1, 2)) & (z[RF] > 0).all(1)
    f = np.nonzero(ok)[0]; dep = z[RF[f]].mean(1); o = np.argsort(-dep); f = f[o]; dep = dep[o]
    q = np.clip(np.round(((uv + 0.5) / 2 - 0.5) * 4).astype(np.int32), -40000, 40000)
    ID = np.zeros((H2, W2), np.uint16); D = np.full((H2, W2), 1e9, np.float32)
    for i, d in zip(f, dep):
        p = q[RF[i]]; cv2.fillConvexPoly(ID, p, int(RP[i]), shift=2); cv2.fillConvexPoly(D, p, float(d), shift=2)
    return ID, D
def look(img, uv):
    h = np.round((uv + 0.5) / 2 - 0.5).astype(int); x = np.clip(h[..., 0], 0, W2 - 1); y = np.clip(h[..., 1], 0, H2 - 1)
    inside = np.isfinite(uv).all(-1) & (h[..., 0] >= 0) & (h[..., 0] < W2) & (h[..., 1] >= 0) & (h[..., 1] < H2)
    return np.where(inside, img[y, x], 0)

cams = Cameras.load(); rep = {"grid": dict(u0=U0, u1=U1, du=DU, d0=D0, d1=D1, dd=DD, minel=MINEL, top_v=vt.round(3).tolist()), "sides": {}}
SID = {"L": (-1, RN.index("ROCKER_L") + 1), "R": (1, RN.index("ROCKER_R") + 1)}
frames = {}
for S, (sg, pid) in SID.items():
    o, u3, v3, n3 = side_plane(sg)
    base = o + us[:, None] * u3 + vt[:, None] * v3                       # outer arris, (nu, 3)
    nt = -slope[:, None] * u3 + v3; nt /= np.linalg.norm(nt, axis=1, keepdims=True)   # top-face normal
    frames[S] = (base, -n3, nt, pid); rep["sides"][S] = {"inward": (-n3).round(6).tolist(), "photos": {}}
for nm in cams.names():
    V = cams[nm]; C = np.asarray(V.center, float); ID = None
    for S, (base, w, nt, pid) in frames.items():
        P15 = base + 15 * w; dv = C - P15; el = np.degrees(np.arcsin(np.clip(np.einsum("ij,ij->i", dv, nt) / np.linalg.norm(dv, axis=1), -1, 1)))
        side = np.sign(dv @ (-w))                                          # +1 camera outboard, -1 inboard
        cand = inr & (el > MINEL) & V.in_image(V.project(base), -40) & V.in_image(V.project(base + 31 * w), -40)
        if cand.sum() < 20: continue
        if ID is None: ID, D = render(V)
        ok = cand.copy()
        for dd_ in (2.0, 15.0, 29.0):
            X = base + dd_ * w; uv, z = V.project(X, return_depth=True)
            ok &= (look(ID, uv) == pid) & (look(D, uv) >= z - 10.0)
        for dd_ in (-8.0, 39.0):
            X = base + dd_ * w - 3.0 * nt; uv, z = V.project(X, return_depth=True); idv = look(ID, uv)
            ok &= (idv == 0) | (idv == pid)
        if ok.sum() < 20: continue
        X = (base[None] + ds[:, None, None] * w[None, None]).reshape(-1, 3); uv = V.project(X).astype(np.float32)
        raw = load_raw(cams, nm)
        img = cv2.remap(raw, np.nan_to_num(uv[:, 0], nan=-10).reshape(len(ds), len(us)), np.nan_to_num(uv[:, 1], nan=-10).reshape(len(ds), len(us)), cv2.INTER_LINEAR, borderValue=(0, 0, 0))
        del raw
        img[:, ~ok] = 0; cv2.imwrite(str(out / f"{S}_{nm[4:8]}.png"), img)
        p0 = V.project(base + 15 * w); p1 = V.project(base + 16 * w); pxmm = np.hypot(*(p1 - p0).T)
        rep["sides"][S]["photos"][nm[4:8]] = dict(ok=ok.astype(int).tolist(), el=np.round(el, 1).tolist(), cam_side=int(np.median(side[ok])), px_per_mm_d=np.round(pxmm, 2).tolist())
        print(S, nm[4:8], "clean %d mm  u %.0f..%.0f  el %.0f-%.0f  %s  px/mm(d) %.1f-%.1f" % (ok.sum(), us[ok].min(), us[ok].max(), el[ok].min(), el[ok].max(), "outboard" if np.median(side[ok]) > 0 else "inboard", pxmm[ok].min(), pxmm[ok].max()), flush=True)
json.dump(rep, open(out / "ribbons.json", "w"))
