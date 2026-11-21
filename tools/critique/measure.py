"""USAGE: tools/py.sh -t 30 tools/critique/measure.py parts/model_vN.glb OUTDIR [--photos 1471,1502 | --photos all] [--shift PART DX DY DZ]
Phase 6 critique, step 1: for every solved photo, the model's visible outline against the wood's edge in the photo.

Per photo (one decoded at a time, ~0.5 GB peak):
 1. Painter's render of the whole joined model (part id + depth, half resolution, back faces culled, triangles subdivided
    to 15 mm) through the solved camera with its lens distortion.
 2. Outline points of the 13 wooden parts (tools/critique/common.py): silhouette edges and visible sharp creases, every 3 mm.
    Kept only where the render shows the line clean: for a silhouette, its own part on the inside and NOTHING (background)
    on the outside for 1.0-5.5 mm along the image normal; for a crease, its own part on both sides and not hidden. Dropped
    where the edge runs within 25 deg of the line of sight (oblique), the photo has < 1.5 px per mm there, or the search
    band comes within 4 mm of the table top (the rockers' contact shadow).
 3. The wood's edge: the photo (CIE Lab, float) sampled along the image normal, -5..+5 mm in 0.1 mm steps, averaged over
    +-1.5 mm along the outline; edge strength = |d Lab / dt| (Gaussian derivative, sigma 0.35 mm); on a silhouette only
    where the colour moves AWAY from this part's own wood colour going outward (the part's median colour 2-5 mm inside in
    this photo), so a shadow or table edge further out does not win unless it is stronger. Rejected: contrast < 10 (Lab,
    8-bit) across the edge, a second peak >= 0.7 of the best at least 1 mm away (ambiguous: reflections, grain, shadow
    lines), or the best peak within 0.5 mm of the band's end (the edge may lie outside the band).
 4. Signed gap in mm = model outline minus wood edge along the outward normal: POSITIVE = the model sticks out beyond the
    wood (model too big there), NEGATIVE = the model lies inside the wood. Measured square to the line of sight
    (mm per px from projecting a 1 mm step of the edge square to the ray and to the edge).
Writes OUTDIR/IMG_nnnn.npz (every candidate point with its status `st`: 0 measured, 1 low contrast, 2 ambiguous, 3 edge at
the band's end, 10 hidden or not clean in the render, 11 oblique, 12 < 1.5 px/mm, 13 off the image, 14 band near the table)
and OUTDIR/run.json."""
import sys, json, time, argparse
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, PARTS, CREASE_DEG, load_model, static_outline, render_mesh, along_axis  # noqa
import numpy as np, cv2
from scipy.ndimage import gaussian_filter1d
from rocker.cameras import Cameras

ap = argparse.ArgumentParser()
ap.add_argument("glb"); ap.add_argument("out"); ap.add_argument("--photos", default="all")
ap.add_argument("--shift", nargs=4, default=None)
a = ap.parse_args()
shift = (a.shift[0], *map(float, a.shift[1:])) if a.shift else None
OUT = Path(a.out); OUT.mkdir(parents=True, exist_ok=True)
t0 = time.time()
cams = Cameras.load()
meshes = load_model(a.glb, shift)
S = static_outline(meshes)
RV, RF, RP, RN = render_mesh(meshes)
RFN = np.cross(RV[RF[:, 1]] - RV[RF[:, 0]], RV[RF[:, 2]] - RV[RF[:, 0]]); RFC = RV[RF].mean(1)
PID = {k: RN.index(k) + 1 for k in PARTS}
print(f"model {a.glb}: {len(RF)} render triangles, outline candidates " + ", ".join(f"{p} {len(S[p]['X'])}" for p in PARTS), flush=True)

names = cams.names() if a.photos == "all" else [f"IMG_{n}.JPG" if n.isdigit() else n for n in a.photos.split(",")]
B, DT = 5.0, 0.1
TT = np.arange(-B, B + DT / 2, DT).astype(np.float32)          # mm along the normal, + = outward
SS = np.array([-1.5, -0.75, 0.0, 0.75, 1.5], np.float32)          # mm along the outline
OFF = np.array([1.0, 1.75, 2.5, 3.25, 4.0, 4.75, 5.5])             # mm, render checks
AX = {"y": 0, "z": 1, "ax": 2}
H2, W2 = 1512, 2016


def render(V):
    C = V.center
    uv, z = V.project(RV, return_depth=True)
    fr = np.einsum("ij,ij->i", RFN, C - RFC) > 0
    ok = fr & np.isfinite(uv[RF]).all((1, 2)) & (z[RF] > 0).all(1)
    f = np.nonzero(ok)[0]
    dep = z[RF[f]].mean(1); f = f[np.argsort(-dep)]; dep = np.sort(dep)[::-1]
    q = np.round(((uv + 0.5) / 2 - 0.5) * 4).astype(np.int32)   # half res, 2 fractional bits
    q = np.clip(q, -40000, 40000)
    ID = np.zeros((H2, W2), np.uint16); D = np.full((H2, W2), 1e9, np.float32)
    for i, d in zip(f, dep):
        p = q[RF[i]]
        cv2.fillConvexPoly(ID, p, int(RP[i]), shift=2); cv2.fillConvexPoly(D, p, float(d), shift=2)
    return ID, D


def look(img, uv):
    """nearest-pixel lookup of a half-res buffer at raw pixel positions (..., 2)."""
    h = np.round((uv + 0.5) / 2 - 0.5).astype(int)
    x = np.clip(h[..., 0], 0, W2 - 1); y = np.clip(h[..., 1], 0, H2 - 1)
    inside = (h[..., 0] >= 0) & (h[..., 0] < W2) & (h[..., 1] >= 0) & (h[..., 1] < H2)
    return np.where(inside, img[y, x], 0)


run = {"glb": a.glb, "shift": a.shift, "photos": {}, "band_mm": B, "crease_deg": CREASE_DEG}
for name in names:
    t1 = time.time()
    V = cams[name]; C = V.center
    ID, D = render(V)
    img = cv2.imread(str(ROOT / "drive" / name), cv2.IMREAD_COLOR | cv2.IMREAD_IGNORE_ORIENTATION)
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2Lab).astype(np.float32); del img
    rows = []
    for pi, p in enumerate(PARTS):
        s = S[p]; adj = s["adj"]
        front = np.einsum("ij,ij->i", s["fn"], C - s["fcen"]) > 0
        fa, fb = front[adj[:, 0]], front[adj[:, 1]]
        kind_e = np.where(fa != fb, 1, np.where((s["ang"] > CREASE_DEG) & fa & fb, 2, 0)).astype(np.int8)
        sel = np.nonzero(kind_e[s["ei"]] > 0)[0]
        if not len(sel): continue
        ei = s["ei"][sel]; X = s["X"][sel]; T = s["T"][ei]; kind = kind_e[ei]
        f1, f2 = adj[ei, 0], adj[ei, 1]
        n1, n2 = s["fn"][f1], s["fn"][f2]
        sharp = s["ang"][ei] >= CREASE_DEG
        na = n1 + n2; na /= np.maximum(np.linalg.norm(na, axis=1, keepdims=True), 1e-9)
        v = X - C; v /= np.linalg.norm(v, axis=1, keepdims=True)
        ms = np.cross(v, T); ms /= np.maximum(np.linalg.norm(ms, axis=1, keepdims=True), 1e-9)
        sgn = np.sign(np.einsum("ij,ij->i", ms, na)); ms *= np.where(sgn == 0, 1, sgn)[:, None]
        mo = na - np.einsum("ij,ij->i", na, v)[:, None] * v; mo /= np.maximum(np.linalg.norm(mo, axis=1, keepdims=True), 1e-9)
        m = np.where(sharp[:, None], ms, mo)
        u0 = V.project(X); d = V.project(X + m) - u0; tg = V.project(X + T) - u0
        nt = np.c_[-tg[:, 1], tg[:, 0]]; nt /= np.maximum(np.linalg.norm(nt, axis=1, keepdims=True), 1e-9)
        nt *= np.where(np.einsum("ij,ij->i", nt, d) < 0, -1, 1)[:, None]
        dn = np.maximum(np.linalg.norm(d, axis=1, keepdims=True), 1e-9)
        nimg = np.where(sharp[:, None], nt, d / dn)
        pxmm = np.abs(np.einsum("ij,ij->i", d, nimg))
        cosTV = np.abs(np.einsum("ij,ij->i", T, v))
        k_ease = np.where(sharp, np.einsum("ij,ij->i", m, n1 + n2) / np.maximum(1 + np.einsum("ij,ij->i", n1, n2), 1e-6) - 1, 0.0)
        c1, c2 = s["fc"][f1], s["fc"][f2]
        lo, hi = np.minimum(c1, c2), np.maximum(c1, c2)
        if p in ("SEAT", "CREST", "SLAT_C"):
            side = np.where(np.abs(X[:, 0]) < 15, 0, np.sign(X[:, 0])).astype(np.int8)
        else:
            side = np.full(len(X), np.sign(meshes[p].vertices[:, 0].mean()), np.int8)
        axn = along_axis(p, T)
        alv = np.where(axn == "y", X[:, 1], np.where(axn == "z", X[:, 2], np.abs(X[:, 0])))
        st = np.zeros(len(X), np.int8)
        st[~np.isfinite(u0).all(1) | ~V.in_image(u0, margin=-40)] = 13
        st[(st == 0) & (pxmm < 1.5)] = 12
        st[(st == 0) & sharp & (cosTV > np.cos(np.radians(25)))] = 11
        st[(st == 0) & (np.abs(np.einsum("ij,ij->i", na, m)) < 0.1) & (kind == 2)] = 11
        st[(st == 0) & (np.minimum(X[:, 2], X[:, 2] + 6.0 * m[:, 2]) < 4.0)] = 14   # band reaches the table: contact shadow
        # render checks
        q = np.nonzero(st == 0)[0]
        if len(q):
            pid = PID[p]
            pin = u0[q, None, :] - (OFF[None, :, None] * pxmm[q, None, None]) * nimg[q, None, :]
            pout = u0[q, None, :] + (OFF[None, :, None] * pxmm[q, None, None]) * nimg[q, None, :]
            ii, oo = look(ID, pin), look(ID, pout)
            own_in = (ii == pid).all(1)
            clean = np.where(kind[q] == 1, own_in & (oo == 0).all(1), own_in & (oo == pid).all(1))
            _, z = V.project(X[q], return_depth=True)
            vis = look(D, u0[q]) >= z - 15.0
            clean &= np.where(kind[q] == 2, vis, True)
            st[q[~clean]] = 10
        rows.append(dict(part=np.full(len(X), pi, np.int8), si=sel, kind=kind, c1=lo.astype(np.int8), c2=hi.astype(np.int8),
                         side=side, ax=np.array([AX[x] for x in axn], np.int8), along=alv.astype(np.float32),
                         X=X.astype(np.float32), uv=u0.astype(np.float32), nimg=nimg.astype(np.float32), m=m.astype(np.float32),
                         pxmm=pxmm.astype(np.float32), cosTV=cosTV.astype(np.float32), k=k_ease.astype(np.float32),
                         joint=s["joint"][sel], sharp=sharp, st=st))
    R = {k: np.concatenate([r[k] for r in rows]) for k in rows[0]}
    n = len(R["st"]); gap = np.full(n, np.nan, np.float32); con = np.full(n, np.nan, np.float32); amb = np.full(n, np.nan, np.float32)
    q = np.nonzero(R["st"] == 0)[0]
    if len(q):
        uv, nn, px = R["uv"][q].astype(np.float32), R["nimg"][q], R["pxmm"][q]
        tg = np.c_[nn[:, 1], -nn[:, 0]]
        P = np.zeros((len(q), len(TT), 3), np.float32)
        for s_ in SS:                                   # one tangential offset at a time (memory)
            base = uv + (s_ * px)[:, None] * tg
            mx = (base[:, 0:1] + TT[None, :] * (px[:, None] * nn[:, 0:1])).astype(np.float32)
            my = (base[:, 1:2] + TT[None, :] * (px[:, None] * nn[:, 1:2])).astype(np.float32)
            P += cv2.remap(lab, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
        P /= len(SS)
        sig = 0.35 / DT
        g = np.linalg.norm(gaussian_filter1d(P, sig, axis=1, order=1), axis=2)
        score = g.copy()
        for pi in np.unique(R["part"][q]):
            j = np.nonzero((R["part"][q] == pi) & (R["kind"][q] == 1))[0]
            if not len(j): continue
            w = np.median(P[j][:, :30].reshape(-1, 3), 0)
            dd = gaussian_filter1d(np.linalg.norm(P[j] - w, axis=2), sig, axis=1, order=1)
            score[j] = g[j] * np.clip(dd / np.maximum(g[j], 1e-6), 0, 1)
        lo_i, hi_i = 5, len(TT) - 6                     # peak must be > 0.5 mm from the band's ends
        sc = score.copy(); sc[:, :lo_i] = 0; sc[:, hi_i + 1:] = 0
        ib = sc.argmax(1)
        best = sc[np.arange(len(q)), ib]
        lm = np.zeros_like(sc, bool); lm[:, 1:-1] = (sc[:, 1:-1] >= sc[:, :-2]) & (sc[:, 1:-1] > sc[:, 2:])
        far = np.abs(np.arange(len(TT))[None, :] - ib[:, None]) >= int(round(1.0 / DT))
        second = np.where(lm & far, sc, 0).max(1)
        # sub-sample
        i0 = np.clip(ib, 1, len(TT) - 2); ar = np.arange(len(q))
        ym, y0, yp = sc[ar, i0 - 1], sc[ar, i0], sc[ar, i0 + 1]
        den = ym - 2 * y0 + yp
        dlt = np.where(np.abs(den) > 1e-9, 0.5 * (ym - yp) / den, 0); dlt = np.clip(dlt, -0.5, 0.5)
        tf = TT[i0] + dlt * DT
        inn = np.clip(i0[:, None] - np.arange(6, 16)[None, :], 0, len(TT) - 1); out = np.clip(i0[:, None] + np.arange(6, 16)[None, :], 0, len(TT) - 1)
        cst = np.linalg.norm(P[ar[:, None], out].mean(1) - P[ar[:, None], inn].mean(1), axis=1)
        stq = np.zeros(len(q), np.int8)
        stq[cst < 10] = 1
        stq[(stq == 0) & (second >= 0.7 * best)] = 2
        stq[(stq == 0) & ((ib <= lo_i) | (ib >= hi_i) | (best <= 0))] = 3
        R["st"][q] = stq; gap[q] = -tf; con[q] = cst; amb[q] = second / np.maximum(best, 1e-9)
    R["gap"], R["contrast"], R["amb"] = gap, con, amb
    np.savez_compressed(OUT / f"{name[:-4]}.npz", **R)
    ok = R["st"] == 0
    run["photos"][name] = dict(candidates=int(n), clean=int((R["st"] < 10).sum()), measured=int(ok.sum()),
                               seconds=round(time.time() - t1, 1))
    print(f"{name}: {n} candidates, {(R['st'] < 10).sum()} clean, {ok.sum()} measured, median gap {np.nanmedian(gap[ok]) if ok.any() else float('nan'):+.2f}, {time.time() - t1:.1f} s", flush=True)
    del lab
run["seconds"] = round(time.time() - t0, 1)
(OUT / "run.json").write_text(json.dumps(run, indent=1))
print(f"done {len(names)} photos in {time.time() - t0:.0f} s")
