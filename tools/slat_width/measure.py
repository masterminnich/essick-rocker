"""USAGE: tools/py.sh -t 20 tools/slat_width/measure.py parts/model_vN.glb OUT.npz [--photos all|1502,1527] [--slats parts/slats.json]
The slats' silhouette WIDTH across, both edges read in the SAME photo on the SAME line (so the photo's pose error cancels).

Per solved photo (one decoded at a time, ~0.6 GB peak), per slat (SLAT_L, SLAT_C, SLAT_R) and station (every 25 mm of the
section centre's height z, 350..1025):
 1. The model's section from parts/slats.json, as tools/build_model.py makes it: a w x t rectangle whose back face lies on the
    slat sheet, centre c, axis tau along the sheet, width along x, thickness along f (square to the back face, forward).
 2. The line ACROSS the slat square to both the line of sight and the slat axis: n = tau x ray (so n lies in the section
    plane and the silhouette's two edges both lie on it); n points outward (away from the centre plane; SLAT_C: to +x).
    The model rectangle's extent along n gives the two predicted outline points s_lo < s_hi (mm from c).
 3. The photo (CIE Lab) sampled along c + s n at 0.1 mm, averaged over +-1.5 mm along tau. Each edge searched only within
    +-BAND mm of its predicted point, with the critique's rule (tools/critique/measure.py step 3): edge strength = |d Lab/ds|
    where the colour moves AWAY from the slat's own colour (median over the middle half of the model width) going outward;
    rejected on contrast < 10, a second peak >= 0.7 of the best at least 1 mm away, or a peak within 0.5 mm of the band end.
 4. Kept only where the painter's render of the joined model (all parts as occluders) shows the slat itself 1-4 mm inside
    each edge and NOTHING 1-5.5 mm outside it (a silhouette against the background, not against another part), the photo has
    >= 1.5 px/mm there and the line of sight is more than 25 deg off the slat's axis.
Writes one row per photo x slat x station: the found edges s_lo, s_hi (mm along n from the model centre), the predicted
ones, the angle alpha of n in the section plane (deg; 0 = straight across the width, + = toward the slat's FRONT on its
outer side; mirrored for the left slat), px/mm, camera azimuth/elevation, status per edge (0 ok, 1 low contrast,
2 ambiguous, 3 band end, 10 not clean in the render, 11 oblique, 12 < 1.5 px/mm, 13 off the image).
Width seen = s_hi - s_lo. Sign of edge gaps as the critique: model point minus found point along the outward normal."""
import sys, json, time, argparse
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tools/critique"))
import numpy as np, cv2
from scipy.ndimage import gaussian_filter1d
from common import load_model, render_mesh  # noqa
sys.path.insert(0, str(Path(__file__).resolve().parent))
from geo import stations  # noqa
from rocker.cameras import Cameras

ap = argparse.ArgumentParser(); ap.add_argument("glb"); ap.add_argument("out")
ap.add_argument("--photos", default="all"); ap.add_argument("--slats", default=str(ROOT / "parts/slats.json"))
ap.add_argument("--band", type=float, default=5.0); ap.add_argument("--rule", default="hybrid", choices=["hybrid", "bg", "wood"]); ap.add_argument("--step", type=float, default=25.0)
a = ap.parse_args()
SL = json.load(open(a.slats)); TH = float(SL["thickness_mm"]); SY = SL["symmetric"]


GEO = {s: stations(SL, s, np.arange(350.0, 1025.1, a.step)) for s in ("SLAT_L", "SLAT_C", "SLAT_R")}
cams = Cameras.load(); meshes = load_model(a.glb)
RV, RF, RP, RN = render_mesh(meshes)
RFN = np.cross(RV[RF[:, 1]] - RV[RF[:, 0]], RV[RF[:, 2]] - RV[RF[:, 0]]); RFC = RV[RF].mean(1)
PID = {k: RN.index(k) + 1 for k in RN}
H2, W2 = 1512, 2016
HO = set(json.load(open(ROOT / "tools/critique/holdout.json"))["held_out"])


def render(V):
    C = V.center; uv, z = V.project(RV, return_depth=True)
    fr = np.einsum("ij,ij->i", RFN, C - RFC) > 0
    ok = fr & np.isfinite(uv[RF]).all((1, 2)) & (z[RF] > 0).all(1)
    f = np.nonzero(ok)[0]; dep = z[RF[f]].mean(1); o = np.argsort(-dep); f = f[o]
    q = np.clip(np.round(((uv + 0.5) / 2 - 0.5) * 4).astype(np.int32), -40000, 40000)
    ID = np.zeros((H2, W2), np.uint16)
    for i in f: cv2.fillConvexPoly(ID, q[RF[i]], int(RP[i]), shift=2)
    return ID


def look(img, uv):
    h = np.round((uv + 0.5) / 2 - 0.5).astype(int)
    x = np.clip(h[..., 0], 0, W2 - 1); y = np.clip(h[..., 1], 0, H2 - 1)
    inside = (h[..., 0] >= 0) & (h[..., 0] < W2) & (h[..., 1] >= 0) & (h[..., 1] < H2)
    return np.where(inside, img[y, x], 0)


BG = (6.0, 8.5)   # mm outside the predicted edge: the background colour (rule bg)
DT = 0.1; SIG = 0.35 / DT; TS = np.array([-1.5, -0.75, 0, 0.75, 1.5])
names = cams.names() if a.photos == "all" else [f"IMG_{n}.JPG" if n.isdigit() else n for n in a.photos.split(",")]
cols = {k: [] for k in ("photo", "held", "slat", "z", "alpha", "w_model", "s_lo_m", "s_hi_m", "s_lo", "s_hi", "st_lo", "st_hi",
                        "con_lo", "con_hi", "mv_lo", "mv_hi", "pxmm", "az", "el", "nx", "ny", "nz")}
t0 = time.time()
for name in names:
    t1 = time.time(); V = cams[name]; C = V.center
    ID = render(V)
    img = cv2.imread(str(ROOT / "drive" / name), cv2.IMREAD_COLOR | cv2.IMREAD_IGNORE_ORIENTATION)
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2Lab).astype(np.float32); del img
    nrow = 0
    for slat, G in GEO.items():
        pid = PID[slat]
        for i in range(len(G["z"])):
            c, tau, e1, f, w = G["c"][i], G["tau"][i], G["e1"][i], G["f"][i], G["w"][i]
            ray = c - C; ray /= np.linalg.norm(ray)
            n = np.cross(tau, ray); nn_ = np.linalg.norm(n)
            if nn_ < 1e-6: continue
            n /= nn_
            if n @ e1 < 0: n = -n
            corners = [sa * w / 2 * e1 + sf * TH / 2 * f for sa in (-1, 1) for sf in (-1, 1)]
            pr = np.array([k @ n for k in corners]); s_lo_m, s_hi_m = pr.min(), pr.max()
            sas = [sa for sa in (-1, 1) for sf in (-1, 1)]; ws = []; moved = [0, 0]
            for kk in (int(pr.argmin()), int(pr.argmax())):       # side face width seen at each edge (0 if that side face is hidden)
                vis = (C - (c + corners[kk])) @ (sas[kk] * e1) > 0
                ws.append(abs(TH * (f @ n)) if vis else 0.0)
            alpha = float(np.degrees(np.arctan2(n @ f, n @ e1)))
            st = [0, 0]
            u0 = V.project(c[None])[0]
            pxmm = float(np.linalg.norm(V.project((c + n)[None])[0] - u0))
            if not (np.isfinite(u0).all() and V.in_image(u0[None], margin=-40)[0]): st = [13, 13]
            elif pxmm < 1.5: st = [12, 12]
            elif abs(tau @ ray) > np.cos(np.radians(25)): st = [11, 11]
            s = np.arange(s_lo_m - max(a.band, BG[1]) - 1.0, s_hi_m + max(a.band, BG[1]) + 1.0 + DT / 2, DT)
            res = [np.nan, np.nan]; con = [np.nan, np.nan]
            if st == [0, 0]:
                # render checks
                for j, (sm, sgn) in enumerate(((s_lo_m, -1), (s_hi_m, 1))):
                    pin = c + (sm - sgn * np.array([1.0, 2.0, 3.0, 4.0]))[:, None] * n
                    pout = c + (sm + sgn * np.arange(1.0, BG[1] + 0.01, 0.75))[:, None] * n
                    ii, oo = look(ID, V.project(pin)), look(ID, V.project(pout))
                    if not ((ii == pid).all() and (oo == 0).all()): st[j] = 10
                X = c[None, None, :] + s[None, :, None] * n[None, None, :] + TS[:, None, None] * tau[None, None, :]
                uv = V.project(X.reshape(-1, 3)).reshape(len(TS), len(s), 2).astype(np.float32)
                P = cv2.remap(lab, uv[..., 0], uv[..., 1], cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE).mean(0)
                mid = np.abs(s - (s_lo_m + s_hi_m) / 2) < 0.25 * (s_hi_m - s_lo_m)
                wcol = np.median(P[mid], 0)
                for j, (sm, sgn) in enumerate(((s_lo_m, -1), (s_hi_m, 1))):
                    if st[j]: continue
                    Q = P if sgn > 0 else P[::-1]; ss = s if sgn > 0 else -s[::-1]
                    g = np.linalg.norm(gaussian_filter1d(Q, SIG, axis=0, order=1), axis=1)
                    win = (ss >= sgn * sm - a.band) & (ss <= sgn * sm + a.band)
                    idx = np.nonzero(win)[0]
                    dA = gaussian_filter1d(np.linalg.norm(Q - wcol, axis=1), SIG, order=1)      # colour moving away from the wood
                    scA = g * np.clip(dA / np.maximum(g, 1e-6), 0, 1)
                    bgc = np.median(Q[(ss >= sgn * sm + BG[0]) & (ss <= sgn * sm + BG[1])], 0)
                    dB = -gaussian_filter1d(np.linalg.norm(Q - bgc, axis=1), SIG, order=1)      # colour moving TOWARD the background
                    scB = g * np.clip(dB / np.maximum(g, 1e-6), 0, 1)
                    sc = scB if a.rule == "bg" else scA
                    scw = sc[idx]; ib = int(scw.argmax()); best = scw[ib]
                    lm = np.zeros(len(scw), bool); lm[1:-1] = (scw[1:-1] >= scw[:-2]) & (scw[1:-1] > scw[2:])
                    far = np.abs(np.arange(len(scw)) - ib) >= int(round(1.0 / DT))
                    second = scw[lm & far].max() if (lm & far).any() else 0.0
                    if a.rule == "bg":                 # the silhouette = the OUTERMOST strong step to the background
                        cand = np.nonzero(lm & (scw >= 0.5 * best))[0]
                        if len(cand): ib = int(cand.max())
                        second = 0.0
                    elif a.rule == "hybrid" and ws[j] >= 1.5:
                        # a side face shows at this edge (ws mm wide): if the wood-rule edge is followed, within ws + 2 mm,
                        # by a step TO the background, the wood-rule edge was the crease (front face / side face): take the step
                        sb = scB[idx]; lb = np.zeros(len(sb), bool); lb[1:-1] = (sb[1:-1] >= sb[:-2]) & (sb[1:-1] > sb[2:])
                        span = (np.arange(len(sb)) > ib + int(0.8 / DT)) & (np.arange(len(sb)) <= ib + int((ws[j] + 2.0) / DT))
                        cand = np.nonzero(lb & span & (sb >= 0.4 * sb.max()))[0]
                        if len(cand):
                            ib = int(cand.max()); sc = scB; best = sb[ib]; second = 0.0; moved[j] = 1
                    k = idx[ib]; k0 = min(max(k, 1), len(sc) - 2)
                    ym, y0, yp = sc[k0 - 1], sc[k0], sc[k0 + 1]; den = ym - 2 * y0 + yp
                    dl = np.clip(0.5 * (ym - yp) / den, -0.5, 0.5) if abs(den) > 1e-9 else 0.0
                    pos = ss[k0] + dl * DT
                    inn = np.clip(k0 - np.arange(6, 16), 0, len(Q) - 1); out = np.clip(k0 + np.arange(6, 16), 0, len(Q) - 1)
                    cst = float(np.linalg.norm(Q[out].mean(0) - Q[inn].mean(0)))
                    con[j] = cst
                    if cst < 10: st[j] = 1
                    elif second >= 0.7 * best: st[j] = 2
                    elif ib <= 5 or ib >= len(scw) - 6 or best <= 0: st[j] = 3
                    res[j] = sgn * pos
            vv = c - C; az = float(np.degrees(np.arctan2(-vv[0], -vv[1]))); el = float(np.degrees(np.arcsin(-vv[2] / np.linalg.norm(vv))))
            for k_, v_ in (("photo", name), ("held", name in HO), ("slat", slat), ("z", float(G["z"][i])), ("alpha", alpha), ("w_model", float(w)),
                           ("s_lo_m", float(s_lo_m)), ("s_hi_m", float(s_hi_m)), ("s_lo", res[0]), ("s_hi", res[1]), ("st_lo", st[0]), ("st_hi", st[1]),
                           ("con_lo", con[0]), ("con_hi", con[1]), ("mv_lo", moved[0]), ("mv_hi", moved[1]), ("pxmm", pxmm), ("az", az), ("el", el), ("nx", n[0]), ("ny", n[1]), ("nz", n[2])):
                cols[k_].append(v_)
            nrow += (st == [0, 0])
    del lab
    print(f"{name}: {nrow} stations with both edges, {time.time() - t1:.1f} s", flush=True)
np.savez_compressed(a.out, **{k: np.array(v) for k, v in cols.items()})
print(f"done {len(names)} photos in {time.time() - t0:.0f} s")
