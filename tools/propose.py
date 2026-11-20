"""USAGE: python -I tools/propose.py LANDMARK [--images 1490,1503 | --best N] [--half 60] [--zoom 6] [--out-dir DIR]
          [--marks skeleton/marks.csv] + camera args
Predict where a landmark should appear in photos it has not been marked in yet, and write a marking crop for each:
  - >=2 marks: triangulated point (magenta ring) + 3-sigma uncertainty ellipse, and epipolar lines (cyan) from each marked view
  - 1 mark: only the epipolar line(s) (the ray of that mark projected, sampled over a depth range)
Crops are centred on the prediction (or the epipolar line's middle) and carry the usual raw-coordinate grid.
--best N picks the N unmarked views whose viewing directions differ most from the already-marked ones.
No occlusion test: a predicted point may be hidden behind another part in some views.
--refine blob|corner [--radius R] runs that refiner seeded at the prediction and prints the result; with --save it
writes results that are 'ok' AND within --gate px of the prediction into marks.csv (source refined:<m>:auto).
Always look at the crops of auto-saved marks (tools/review.py) before trusting them.
Example: python -I tools/propose.py L01 --best 4
"""
import argparse
import sys, pathlib; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))  # noqa: E702
from tools._common import ROOT, add_camera_args, load_cams, img_name
import numpy as np


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    add_camera_args(ap)
    ap.add_argument("landmark")
    ap.add_argument("--images", default=None)
    ap.add_argument("--best", type=int, default=6)
    ap.add_argument("--half", type=float, default=60); ap.add_argument("--zoom", type=float, default=6)
    ap.add_argument("--depth", default="0.3,30", help="epipolar depth range as min,max multiples of the median camera-to-scene distance")
    ap.add_argument("--marks", default=str(ROOT / "skeleton/marks.csv"))
    ap.add_argument("--out-dir", default=str(ROOT / "work/toolkit/crops"))
    ap.add_argument("--exclude", default="", help="comma list of images never to propose (e.g. held-out photos)")
    ap.add_argument("--sheet", action="store_true", help="also tile all crops into one image (2 columns) for a single look")
    ap.add_argument("--tile", type=int, default=0, help="tile size in --sheet (0 = native crop size, keeps grid scale honest)")
    ap.add_argument("--refine", choices=["blob", "corner"], default=None)
    ap.add_argument("--radius", type=float, default=25); ap.add_argument("--save", action="store_true")
    ap.add_argument("--gate", type=float, default=12.0)
    a = ap.parse_args()
    import cv2
    from rocker import marks as mk
    from rocker.triangulate import triangulate
    from rocker.images import render_crop
    cams = load_cams(a)
    ms = [m for m in mk.read(a.marks) if m["landmark_id"] == a.landmark and m["image"] in cams.views]
    if not ms:
        sys.exit(f"no marks for {a.landmark}")
    marked = {m["image"] for m in ms}
    excl = {img_name(s) for s in a.exclude.split(",") if s}
    X = None; cov = None
    if len(ms) >= 2:
        r = triangulate(cams, [(m["image"], (m["x_raw"], m["y_raw"])) for m in ms])
        X, cov = r.X, r.cov
        print(f"triangulated {a.landmark}: rms {r.rms_px:.2f}px, sigma {r.sigma_mm:.3g} {cams.units}")
    rays = [cams.ray(m["image"], np.array([[m["x_raw"], m["y_raw"]]])) for m in ms]
    rays = [(o, d[0]) for o, d in rays]
    X1 = None
    if X is None:   # one mark: depth prior from COLMAP sparse points that project within 25 px of the mark
        P3 = cams.metric.to_chair(np.array([p.xyz for p in cams.rec.points3D.values()]))
        m0 = ms[0]; v0 = cams[m0["image"]]
        uv, dep = v0.project(P3, return_depth=True)
        near = np.hypot(uv[:, 0] - m0["x_raw"], uv[:, 1] - m0["y_raw"]) < 25
        if near.sum() >= 3:
            o, d = rays[0]
            X1 = o + d * np.median((P3[near] - o) @ d)
            print(f"one mark: depth prior from {int(near.sum())} sparse points (may be the background, check the line)")
    # depth range along each ray: from the camera-to-scene distance (median distance of camera centres to X or 3D pts)
    cen = np.array([cams[n].center for n in cams.names()])
    scene_c = X if X is not None else np.median(cen, 0)
    dist = np.median(np.linalg.norm(cen - scene_c, axis=1))
    lo, hi = (float(s) for s in a.depth.split(","))
    ts = np.geomspace(lo * dist, hi * dist, 400) if lo > 0 else np.linspace(0, hi * dist, 400)
    cand = [n for n in (cams.names() if not a.images else [img_name(s) for s in a.images.split(",")]) if n not in marked and n not in excl]
    dirs_marked = [cams[n].center - (X if X is not None else scene_c) for n in marked]
    dirs_marked = [d / np.linalg.norm(d) for d in dirs_marked]
    scored = []
    for n in cand:
        v = cams[n]
        if X is not None:
            uv = v.project(X[None])[0]
            if not v.in_image(uv[None], margin=-20)[0]:
                continue
        d = v.center - scene_c; d /= np.linalg.norm(d)
        sep = min(np.degrees(np.arccos(np.clip(d @ dm, -1, 1))) for dm in dirs_marked)
        scored.append((sep, n))
    scored.sort(reverse=True)
    pick = [n for _, n in scored] if a.images else []
    if not a.images:   # greedy max-min angular spread
        chosen_dirs = list(dirs_marked)
        pool = [n for _, n in scored]
        while pool and len(pick) < a.best:
            def sep(n):
                d = cams[n].center - scene_c; d /= np.linalg.norm(d)
                return min(np.degrees(np.arccos(np.clip(d @ dm, -1, 1))) for dm in chosen_dirs)
            n = max(pool, key=sep); pool.remove(n); pick.append(n)
            d = cams[n].center - scene_c; chosen_dirs.append(d / np.linalg.norm(d))
    tiles = []
    for n in pick:
        v = cams[n]
        pls = [(v.project(o + ts[:, None] * d), (255, 255, 0)) for o, d in rays]
        if X is not None:
            uv = v.project(X[None])[0]
            h = 1e-4 * dist
            J = np.stack([(v.project((X + e)[None])[0] - v.project((X - e)[None])[0]) / (2 * h) for e in np.eye(3) * h], 1)
            C2 = J @ cov @ J.T
            sig = float(np.sqrt(np.trace(C2)))
            img, _ = render_crop(n, uv, half=max(a.half, 4 * sig), zoom=a.zoom, polylines=pls,
                                 ellipses=[(uv, 9 * C2, (255, 0, 255))], marks=[(uv, "pred", (255, 0, 255))], crosshair=False)
            msg = f"pred raw=({uv[0]:.1f},{uv[1]:.1f}) 1-sigma {sig:.1f}px"
            if a.refine:
                from rocker import refine as rf
                xy, info = rf.blob(n, uv, a.radius) if a.refine == "blob" else rf.corner(n, uv)
                if xy is not None:
                    dpred = float(np.hypot(*(xy - uv)))
                    ok = bool(info.get("ok")) and dpred < a.gate
                    msg += f" | {a.refine} ({xy[0]:.1f},{xy[1]:.1f}) d={dpred:.1f} ok={ok} fit={info.get('fit_px', info.get('cornerness', 0)):.2f}"
                    if ok and a.save:
                        mk.upsert(a.landmark, n, xy[0], xy[1], f"refined:{a.refine}:auto", ""); msg += " SAVED"
                    img = render_crop(n, uv, half=max(a.half, 4 * sig), zoom=a.zoom, polylines=pls, crosshair=False,
                                      ellipses=[(uv, 9 * C2, (255, 0, 255))],
                                      marks=[(uv, "pred", (255, 0, 255)), (xy, a.refine, (0, 255, 0))])[0]
                else:
                    msg += f" | {a.refine} failed {info}"
        else:
            q = pls[0][0]; ok = v.in_image(q)
            if not ok.any():
                continue
            uv = q[ok][len(q[ok]) // 2]
            if X1 is not None:
                u1 = v.project(X1[None])[0]
                if v.in_image(u1[None])[0]:
                    uv = u1
            img, _ = render_crop(n, uv, half=a.half * 4, zoom=a.zoom / 4, polylines=pls, crosshair=False)
            msg = f"epipolar only, crop centre raw=({uv[0]:.1f},{uv[1]:.1f})"
        out = pathlib.Path(a.out_dir) / f"prop_{a.landmark}_{n[:-4]}.png"
        cv2.imwrite(str(out), img)
        tiles.append(cv2.resize(img, (a.tile, a.tile), interpolation=cv2.INTER_AREA) if a.tile else img)
        print(n, msg, out)
    if a.sheet and tiles:
        while len(tiles) % 2:
            tiles.append(np.zeros_like(tiles[0]))
        rows = [np.hstack(tiles[i:i + 2]) for i in range(0, len(tiles), 2)]
        out = pathlib.Path(a.out_dir) / f"sheet_{a.landmark}.png"
        cv2.imwrite(str(out), np.vstack(rows)); print("sheet", out)


if __name__ == "__main__":
    main()
