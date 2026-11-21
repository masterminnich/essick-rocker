"""USAGE: tools/py.sh -t 15 tools/seat_corner/sil.py --photos 1558,1562 [--glb parts/model_v19_shapes.glb] [--out work/seatcorner/sil]
          [--band 6] [--roi "100 275 380 545"]
Seat-top silhouette near the FRONT CORNERS against the wood, per photo, as an offset along the surface normal (mm).

For each photo: the SEAT mesh's contour generator (edges between a face turned toward the camera and one turned away) is
sampled every 1 mm; only samples that lie on the OUTER contour of the projected seat, on the top surface (normal z > 0.35),
inside the region of interest (|x| x0..x1, y y0..y1, both halves) and not hidden by another part (painter's depth of the
other parts) are kept. At each one the photo is read along the image normal (raw sensor pixels, bilinear, colour gradient
after a 1.2 px Gaussian); the wood's edge is the OUTERMOST gradient peak of at least half the strongest one within
+-band mm of the model's contour (the model contour is the seed; a specular band on the roll lies INSIDE the contour).
offset_mm > 0: the wood reaches beyond the model (model low / inside); < 0: the model stands proud of the wood.
z_equiv = offset_mm / normal_z (the vertical shift of the surface that would explain it).

Writes <out>/<photo>.json (samples) and <out>/<photo>_<side>.jpg (crop at 10 px per mm of the nearest sample, model contour
yellow, wood edge found cyan, ambiguous (inner and outer readings disagree) magenta, hidden by another part red). One photo decoded at a time; peak about 1 GB; 3-8 s per photo."""
import sys, json, argparse; from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]; sys.path.insert(0, str(ROOT))
import numpy as np, cv2, trimesh
from rocker.cameras import Cameras
from rocker.ortho import load_raw
ap = argparse.ArgumentParser(); ap.add_argument("--photos", required=True); ap.add_argument("--glb", default="parts/model_v19_shapes.glb")
ap.add_argument("--out", default="work/seatcorner/sil"); ap.add_argument("--band", type=float, default=6.0); ap.add_argument("--roi", default="100 275 380 545")
ap.add_argument("--nofig", action="store_true")
a = ap.parse_args(); X0, X1, Y0, Y1 = map(float, a.roi.split())
out = ROOT / a.out; out.mkdir(parents=True, exist_ok=True)
cams = Cameras.load(); sc = trimesh.load(ROOT / a.glb)
seat = sc.geometry["SEAT"]; others = {k: g for k, g in sc.geometry.items() if k != "SEAT"}
V, F = np.asarray(seat.vertices), np.asarray(seat.faces); FN = np.asarray(seat.face_normals); FC = V[F].mean(1)
E = np.asarray(seat.face_adjacency_edges); FA = np.asarray(seat.face_adjacency)


def raster_depth(view, meshes, x0, y0, w, h):
    """painter's depth (mm from the camera, face-centroid depth) of the given meshes in the raw-pixel window."""
    D = np.full((h, w), np.inf, np.float32)
    for g in meshes:
        uv, z = view.project(np.asarray(g.vertices), return_depth=True); f = np.asarray(g.faces)
        if not np.isfinite(uv).all(): continue
        tri = uv[f] - [x0, y0]; dz = z[f].mean(1)
        inwin = (tri[:, :, 0].max(1) >= 0) & (tri[:, :, 0].min(1) < w) & (tri[:, :, 1].max(1) >= 0) & (tri[:, :, 1].min(1) < h)
        for i in np.where(inwin)[0][np.argsort(-dz[inwin])]:
            p = np.round(tri[i]).astype(np.int32)
            bx0, by0 = max(p[:, 0].min(), 0), max(p[:, 1].min(), 0); bx1, by1 = min(p[:, 0].max() + 1, w), min(p[:, 1].max() + 1, h)
            if bx1 <= bx0 or by1 <= by0: continue
            sub = np.zeros((by1 - by0, bx1 - bx0), np.uint8); cv2.fillConvexPoly(sub, p - [bx0, by0], 1)
            blk = D[by0:by1, bx0:bx1]; blk[(sub > 0) & (blk > dz[i])] = dz[i]
    return D


def bilinear(img, xy):
    return np.stack([cv2.remap(img[:, :, c], xy[..., 0].astype(np.float32), xy[..., 1].astype(np.float32), cv2.INTER_LINEAR) for c in range(img.shape[2])], -1)


for p in a.photos.split(","):
    nm = f"IMG_{p}.JPG"
    if nm not in cams.views: print(p, "not registered"); continue
    v = cams[nm]; C = v.center
    front = ((FC - C) * FN).sum(1) < 0
    sil = front[FA[:, 0]] != front[FA[:, 1]]
    S = []; NS = []
    for (i0, i1), (fa, fb) in zip(E[sil], FA[sil]):
        A, B = V[i0], V[i1]; L = np.linalg.norm(B - A); k = max(int(L), 1); t = (np.arange(k) + 0.5) / k
        n = FN[fa] + FN[fb]; S.append(A + t[:, None] * (B - A)); NS.append(np.tile(n, (k, 1)))
    S = np.concatenate(S); NS = np.concatenate(NS)
    ray = S - C; ray /= np.linalg.norm(ray, axis=1, keepdims=True); NS = NS - (NS * ray).sum(1, keepdims=True) * ray; NS /= np.linalg.norm(NS, axis=1, keepdims=True)
    roi = (np.abs(S[:, 0]) >= X0) & (np.abs(S[:, 0]) <= X1) & (S[:, 1] >= Y0) & (S[:, 1] <= Y1) & (NS[:, 2] > 0.35)
    S, NS = S[roi], NS[roi]
    res = {"photo": nm, "glb": a.glb, "band_mm": a.band, "roi": [X0, X1, Y0, Y1], "camera_centre": C.tolist(), "samples": []}
    if len(S) == 0:
        json.dump(res, open(out / f"{p}.json", "w")); print(p, "no contour samples in the ROI"); continue
    uv, z = v.project(S, return_depth=True); uv2 = v.project(S + 1.0 * NS); dn = uv2 - uv; ppm = np.linalg.norm(dn, axis=1); dn /= ppm[:, None]
    okv = v.in_image(uv, margin=-40)
    # window covering the samples plus margin
    if not okv.any(): json.dump(res, open(out / f"{p}.json", "w")); print(p, "samples outside the image"); continue
    m = int(np.ceil(a.band * ppm.max() + 40)); x0, y0 = int(max(uv[okv, 0].min() - m, 0)), int(max(uv[okv, 1].min() - m, 0))
    x1, y1 = int(min(uv[okv, 0].max() + m, 4031)), int(min(uv[okv, 1].max() + m, 3023)); w, h = x1 - x0 + 1, y1 - y0 + 1
    # outer contour of the projected seat
    sm = np.zeros((h, w), np.uint8); suv = v.project(V) - [x0, y0]
    for tri in np.round(suv[F]).astype(np.int32): cv2.fillConvexPoly(sm, tri, 255)
    cs, _ = cv2.findContours(sm, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE); cm = np.zeros_like(sm); cv2.drawContours(cm, cs, -1, 255, 1)
    dt = cv2.distanceTransform(255 - cm, cv2.DIST_L2, 3)
    Do = raster_depth(v, others.values(), x0, y0, w, h)
    raw = load_raw(cams, nm)[y0:y1 + 1, x0:x1 + 1].astype(np.float32); bl = cv2.GaussianBlur(raw, (0, 0), 1.2)
    for j in np.where(okv)[0]:
        q = uv[j] - [x0, y0]; qi = np.round(q).astype(int)
        if not (0 <= qi[0] < w and 0 <= qi[1] < h) or dt[qi[1], qi[0]] > 1.5: continue
        bandpx = a.band * ppm[j]; occ = False
        for tt in np.linspace(-bandpx, bandpx, 9):
            r = np.round(q + tt * dn[j]).astype(int)
            if 0 <= r[0] < w and 0 <= r[1] < h and Do[r[1], r[0]] < z[j] - 5: occ = True; break
        ts = np.arange(-bandpx - 3, bandpx + 3, 0.25); xy = q[None] + ts[:, None] * dn[j][None]
        if xy.min() < 0 or xy[:, 0].max() > w - 1 or xy[:, 1].max() > h - 1: continue
        prof = bilinear(bl, xy[None])[0]; g = np.linalg.norm(np.gradient(prof, axis=0), axis=1) / 0.25
        inb = np.abs(ts) <= bandpx; gb = np.where(inb, g, 0); gmax = gb.max()
        # wood colour = the inner end of the band (band mm inside the model's contour); the edge is where the profile first leaves it going outward,
        # refined to the gradient peak within 1.5 mm (background clutter lies OUTSIDE the wood, so the first departure from the inside is the wood's edge)
        iw = inb & (ts <= -bandpx + 1.5 * ppm[j]); ref = np.median(prof[iw], 0); dist = np.linalg.norm(prof - ref, axis=1)
        dmax = np.where(inb, dist, 0).max(); thr = max(25.0, 0.5 * dmax)
        cross = np.where(inb & (ts > -bandpx + 1.5 * ppm[j]) & (dist > thr))[0]
        if len(cross) == 0 or gmax <= 0: continue
        c0 = cross[0]; win = np.where(inb & (np.abs(ts - ts[c0]) <= 1.5 * ppm[j]))[0]; i = int(win[np.argmax(gb[win])]); i = min(max(i, 1), len(ts) - 2)
        pk = [k for k in range(1, len(ts) - 1) if inb[k] and gb[k] >= gb[k - 1] and gb[k] >= gb[k + 1] and gb[k] >= 0.5 * gmax]
        def sub(i): d = (gb[i - 1] - gb[i + 1]) / (2 * (gb[i - 1] - 2 * gb[i] + gb[i + 1]) + 1e-9); return ts[i] + 0.25 * float(np.clip(d, -0.5, 0.5))
        tpk = sub(i); tout = sub(pk[-1]) if pk else np.nan
        # two readings of the same edge: INNER = first departure from the wood colour (fooled by background clutter? no; by a pale highlight band on
        # the wood: yes, it stops at the band's inner edge); OUTER = outermost strong gradient peak (fooled by clutter outside the wood). Where the two
        # agree within 0.5 mm the edge is unambiguous: clean wood against clean background. Only those samples are used.
        agree = bool(np.isfinite(tout) and abs(tout - tpk) <= 0.5 * ppm[j])
        lum_in, lum_out = float(prof[ts < tpk - 3].mean()), float(prof[ts > tpk + 3].mean()) if (ts > tpk + 3).any() else np.nan
        res["samples"].append({"X": S[j].round(2).tolist(), "N": NS[j].round(4).tolist(), "uv": uv[j].round(2).tolist(), "dn": dn[j].round(4).tolist(), "px_per_mm": float(ppm[j]),
                               "depth_mm": float(z[j]), "t_px": float(tpk), "offset_mm": float(tpk / ppm[j]), "z_equiv": float(tpk / ppm[j] / NS[j, 2]), "strength": float(gb[i]),
                               "second_peak": int(len(pk)), "occluded": occ, "t_outer_px": float(tout), "agree": agree, "lum_in": lum_in, "lum_out": lum_out})
    json.dump(res, open(out / f"{p}.json", "w"))
    ss = [s for s in res["samples"] if not s["occluded"] and s["agree"]]
    for side, sg in (("R", 1), ("L", -1)):
        q = [s for s in ss if np.sign(s["X"][0]) == sg]
        if q: print(f"{p} {side}: {len(q):4d} samples, |x| {min(abs(s['X'][0]) for s in q):.0f}-{max(abs(s['X'][0]) for s in q):.0f}, y {min(s['X'][1] for s in q):.0f}-{max(s['X'][1] for s in q):.0f}, "
                    f"{np.mean([s['px_per_mm'] for s in q]):.1f} px/mm, offset median {np.median([s['offset_mm'] for s in q]):+.2f} mm")
    if a.nofig: continue
    for side, sg in (("R", 1), ("L", -1)):
        q = [s for s in res["samples"] if np.sign(s["X"][0]) == sg]
        if len(q) < 5: continue
        U = np.array([s["uv"] for s in q]) - [x0, y0]; s10 = 10.0 / np.median([s["px_per_mm"] for s in q])
        bx0, by0 = int(max(U[:, 0].min() - 15 * q[0]["px_per_mm"], 0)), int(max(U[:, 1].min() - 15 * q[0]["px_per_mm"], 0))
        bx1, by1 = int(min(U[:, 0].max() + 15 * q[0]["px_per_mm"], w)), int(min(U[:, 1].max() + 15 * q[0]["px_per_mm"], h))
        crop = raw[by0:by1, bx0:bx1].astype(np.uint8); crop = cv2.resize(crop, None, fx=s10, fy=s10, interpolation=cv2.INTER_CUBIC)
        for s in q:
            u = (np.array(s["uv"]) - [x0 + bx0, y0 + by0]) * s10; e = u + np.array(s["dn"]) * s["t_px"] * s10
            cv2.circle(crop, tuple(np.round(u).astype(int)), 1, (0, 255, 255), -1)
            cv2.circle(crop, tuple(np.round(e).astype(int)), 2, (0, 0, 255) if s["occluded"] else ((255, 255, 0) if s["agree"] else (255, 0, 255)), -1)
        if max(crop.shape[:2]) > 4000: f = 4000 / max(crop.shape[:2]); crop = cv2.resize(crop, None, fx=f, fy=f, interpolation=cv2.INTER_AREA)
        cv2.imwrite(str(out / f"{p}_{side}.jpg"), crop, [cv2.IMWRITE_JPEG_QUALITY, 88])
