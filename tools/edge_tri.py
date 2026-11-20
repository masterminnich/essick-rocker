"""USAGE: python -I tools/edge_tri.py PREFIX --seed "u,v u,v ..." | --seed-poly "c4 c3 .. c0" V0 V1   --inside U,V
            [--photos 1502,1501 | auto] [--mode clean|far|all] [--margin 0] [--band 6] [--ddeg 2] [--depth-fixed D] [--depth-guess D]
            [--dump PERPHOTO.json] [--name NAME] --out FILE.json
Trace ONE edge (arris) of a part in several rectified photos and TRIANGULATE it: the result is the edge on the sheet with
parallax removed, plus how far the arris really sits off the sheet (so the sheet no longer has to be exactly on the face).
Why: a point d mm off the sheet lands at  u_obs = u + d * (u - xc) / (H - d)  in a photo whose camera is H above the sheet
and at lateral position xc, so photos disagree in proportion to d. Two or more photos give both u and d.
Only "clean" photos are used: the camera must stand on the INSIDE of the edge (--inside = any point inside the part, on
the sheet), so that it cannot see the part's side face there and the outline it sees is this arris, not the far one.
--margin lets a camera stand that many mm outside (use only for thin parts). --mode far does the opposite: only cameras
standing OUTSIDE the edge line, which all see the far arris as the outline; its depth is then minus the part's thickness. d(v) is a polynomial of degree --ddeg along
the edge; u is free per station. Each photo is refined separately around the seed (band, then band/2 around its own
smoothed result). --depth-fixed D skips the depth solve (for an edge whose clean photos all stand on one side with a short baseline: put the
sheet on the neighbouring, well-triangulated arris first, then fix d = 0). With a single clean photo d is taken as 0 and the edge is NOT parallax-corrected (it says so).
PREFIX_<photo>.png + PREFIX_plane.json come from tools/face_ortho.py or tools/sheet_ortho.py.
Output JSON: {name: [[u, v]..], name_depth_mm: [...], name_xyz: [[x, y, z]..] (chair frame), name_info: {...}}. Tiny compute."""
import sys, json, argparse
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import numpy as np, cv2
from rocker.cameras import Cameras
from rocker.surface import load_surface
ap = argparse.ArgumentParser(); ap.add_argument("prefix"); ap.add_argument("--seed", default=None); ap.add_argument("--seed-poly", nargs="+", default=None, help='"coefs of u(v)" V0 V1')
ap.add_argument("--inside", required=True); ap.add_argument("--photos", default="auto"); ap.add_argument("--margin", type=float, default=0.0)
ap.add_argument("--band", type=float, default=6.0); ap.add_argument("--ddeg", type=int, default=2); ap.add_argument("--name", default="edge"); ap.add_argument("--out", required=True)
ap.add_argument("--mode", default="clean", choices=["clean", "far", "all"], help="clean: cameras inside the edge line (outline = near arris). far: cameras outside it by > margin (outline = the FAR arris; "
                "the depth then comes out as minus the part's thickness). all: every photo (only for a line drawn on the surface, e.g. a ridge)")
ap.add_argument("--depth-fixed", type=float, default=None, help="do not solve d; take the arris this far off the sheet (e.g. 0 when the sheet was already put on the neighbouring arris) and weight photos by how little a depth error moves them")
ap.add_argument("--depth-guess", type=float, default=0.0, help="expected depth of the arris off the sheet: each photo's search is centred where an arris at that depth would land (g * D), so the band can stay small for a far arris")
ap.add_argument("--pool", default=None, help="candidate photos (e.g. only the near-frontal ones); unlike --photos the --mode filter still picks among them")
ap.add_argument("--seed-photo", default=None, help="the photo the seed was read on (e.g. 1507): with --depth-guess the search in every other photo is shifted by the parallax difference to that photo")
ap.add_argument("--dump", default=None, help="also write every photo's own traced curve {photo: [[u, v]..]} to this JSON, to overlay on that single photo and check by eye")
ap.add_argument("--lam", type=float, default=1.5); ap.add_argument("--max-photos", type=int, default=4); ap.add_argument("--clip", type=float, default=1.5)
a = ap.parse_args()
pj = json.load(open(a.prefix + "_plane.json")); res = pj["res"]; (u0, u1), (v0, v1) = pj["urange"], pj["vrange"]; S = load_surface(pj); cams = Cameras.load()
if a.seed_poly:
    c = [float(x) for x in a.seed_poly[0].split()]; vs = np.arange(float(a.seed_poly[1]), float(a.seed_poly[2]) + 1e-9, 1.0); P = np.c_[np.polyval(c, vs), vs]
else:
    Sd = np.array([[float(x) for x in p.split(",")] for p in a.seed.split()]); seg = np.r_[0, np.cumsum(np.linalg.norm(np.diff(Sd, axis=0), axis=1))]
    sta = np.arange(0, seg[-1] + 1e-9, 1.0); P = np.c_[np.interp(sta, seg, Sd[:, 0]), np.interp(sta, seg, Sd[:, 1])]
T = np.gradient(P, axis=0); T /= np.linalg.norm(T, axis=1, keepdims=True); N = np.c_[-T[:, 1], T[:, 0]]; n_st = len(P)
ins = np.array([float(x) for x in a.inside.split(",")]); out_sign = -np.sign(np.median((ins - P) @ N.T.mean(1)))      # +1: outward is +N
eu, ev, nn = S.frame(P); X = S.to3d(P); e_out = out_sign * (N[:, :1] * eu + N[:, 1:2] * ev)


def geom(nm):
    C = cams.views[nm].center; D = C - X; H = np.sum(D * nn, 1); lat = np.sum(D * e_out, 1)        # height above the sheet; camera position along outward
    return H, lat


def smooth(x, k=41):
    pad = np.r_[x[:k // 2][::-1], x, x[-(k // 2):][::-1]]; return np.array([np.median(pad[i:i + k]) for i in range(len(x))])


def snap(lab, centre, band):
    dt = res / 2; offs = np.arange(-band, band + 1e-9, dt); UV = P[:, None, :] + (centre[:, None] + offs[None, :])[..., None] * N[:, None, :]
    prof = cv2.remap(lab, ((UV[..., 0] - u0) / res).astype(np.float32), ((v1 - UV[..., 1]) / res).astype(np.float32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    G = cv2.GaussianBlur(np.linalg.norm(np.gradient(prof, axis=1), axis=2), (1, 7), 0); Gn = G / (np.percentile(G, 95) + 1e-6)
    n, m = Gn.shape; cost = np.full((n, m), -np.inf); back = np.zeros((n, m), int); cost[0] = Gn[0]; idx = np.arange(m)
    for i in range(1, n):
        best = np.full(m, -np.inf); arg = np.zeros(m, int)
        for dd in (-1, 0, 1):
            j = idx + dd; ok = (j >= 0) & (j < m); val = np.full(m, -np.inf); val[ok] = cost[i - 1, j[ok]] - a.lam * abs(dd) * dt
            upd = val > best; best[upd] = val[upd]; arg[upd] = j[upd]
        cost[i] = best + Gn[i]; back[i] = arg
    path = np.zeros(n, int); path[-1] = int(np.argmax(cost[-1]))
    for i in range(n - 1, 0, -1): path[i - 1] = back[i, path[i]]
    return centre + offs[path]


names = [f"IMG_{x}.JPG" for x in a.photos.split(",")] if a.photos != "auto" else ([f"IMG_{x}.JPG" for x in a.pool.split(",")] if a.pool else pj["photos"])
rows = []
for nm in names:
    H, lat = geom(nm); rows.append((nm, float(np.median(lat)), H, lat))
clean = rows if (a.photos != "auto" or a.mode == "all") else [r for r in rows if (r[1] <= a.margin if a.mode == "clean" else r[1] > a.margin)]
clean = sorted(clean, key=lambda r: abs(r[1]) / np.median(r[2]))[:a.max_photos]
if not clean: sys.exit(f"{a.name}: no clean photo (camera positions along outward: " + ", ".join(f"{r[0][4:8]} {r[1]:+.0f}" for r in rows) + ")")
g_ref = 0.0
if a.seed_photo:
    Hr, lr = geom(f"IMG_{a.seed_photo}.JPG"); g_ref = -lr / (Hr - a.depth_guess)
M = []; G = []; HH = np.array([r[2] for r in clean]); LL = np.array([r[3] for r in clean])
for nm, latm, H, lat in clean:
    lab = cv2.GaussianBlur(cv2.cvtColor(cv2.imread(f"{a.prefix}_{nm[4:8]}.png"), cv2.COLOR_BGR2LAB).astype(np.float32), (0, 0), 0.8)
    c0 = out_sign * (-lat / (H - a.depth_guess) - g_ref) * a.depth_guess
    m1 = snap(lab, c0, a.band); m2 = snap(lab, smooth(m1), max(a.band / 2, 2.0))
    M.append(m2 * out_sign); G.append(-lat / H)          # outward offset from the seed; observed = x + g * d  (d>0: arris off the sheet towards the cameras)
M = np.array(M); G = np.array(G); s_ = np.linspace(-1, 1, n_st); B = np.stack([s_ ** k for k in range(a.ddeg + 1)], 1)
if a.depth_fixed is not None:
    d = np.full(n_st, a.depth_fixed); w = 1.0 / (G ** 2 + 0.05 ** 2); x = np.sum((M - G * d) * w, 0) / w.sum(0); resid = (M - G * d - x).ravel(); solved = False
elif len(clean) >= 2 and np.ptp(G.mean(1)) > 0.08:
    Mc = M - M.mean(0); Gc = G - G.mean(0); keep = np.ones(M.shape, bool)
    for it in range(8):
        A_ = (Gc[..., None] * B[None]) [keep]; cf = np.linalg.lstsq(A_, Mc[keep], rcond=None)[0]; d = B @ cf
        r = Mc - Gc * d; keep = np.abs(r - np.median(r, 0)) < a.clip
        if it >= 3: G = -LL / (HH - d); Gc = G - G.mean(0)          # exact parallax factor once d is roughly known (matters for d of tens of mm)
    w = keep.astype(float) + 1e-6; x = np.sum((M - G * d) * w, 0) / w.sum(0); resid = (M - G * d - x)[keep]; solved = True
else:
    d = np.zeros(n_st); x = M.mean(0); resid = (M - x).ravel(); solved = False
E = P + (out_sign * x)[:, None] * N; XYZ = S.to3d(E, d)
if a.dump:
    dj = json.load(open(a.dump)) if Path(a.dump).exists() else {}
    for i, r in enumerate(clean): dj[f"{a.name}@{r[0][4:8]}"] = (P + (out_sign * M[i])[:, None] * N).tolist()
    json.dump(dj, open(a.dump, "w"))
info = {"photos": [r[0][4:8] for r in clean], "camera_along_outward_mm": [round(r[1]) for r in clean], "triangulated": solved, "residual_rms_mm": float(np.sqrt(np.mean(resid ** 2))),
        "depth_mm": {"start": float(d[0]), "mid": float(d[n_st // 2]), "end": float(d[-1])}, "moved_outward_from_seed_mm": {"median": float(np.median(x)), "p5": float(np.percentile(x, 5)), "p95": float(np.percentile(x, 95))},
        "per_photo_outward_minus_edge_mm": {r[0][4:8]: float(np.median(M[i] - x)) for i, r in enumerate(clean)}, "not_used": {r[0][4:8]: round(r[1]) for r in rows if r[0] not in [c[0] for c in clean]}}
json.dump({a.name: E.tolist(), a.name + "_depth_mm": d.tolist(), a.name + "_xyz": XYZ.tolist(), a.name + "_info": info}, open(a.out, "w"))
print(f"{a.name:10s} photos {','.join(info['photos'])} (camera along outward {info['camera_along_outward_mm']}) | " + (f"arris off the sheet {d[0]:+.1f} / {d[n_st // 2]:+.1f} / {d[-1]:+.1f} mm (start/mid/end)" if solved else (f"depth fixed at {a.depth_fixed:+.1f} mm" if a.depth_fixed is not None else "ONE VIEW ONLY: no parallax correction"))
      + f" | residual {info['residual_rms_mm']:.2f} mm rms | moved outward from seed {np.median(x):+.1f} ({np.percentile(x, 5):+.1f}..{np.percentile(x, 95):+.1f}) | raw per photo vs edge: "
      + ", ".join(f"{k} {v:+.1f}" for k, v in info["per_photo_outward_minus_edge_mm"].items()))
