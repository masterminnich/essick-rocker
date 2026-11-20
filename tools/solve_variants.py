"""USAGE: uv run --no-project --with pycolmap --with numpy python -I tools/solve_variants.py \
    --model work/solve/single --variant {S,G2,F} --out work/solve/var_F [--close 1493,1494,...] [--min_obs 300]
    [--max_err 4.0] [--rounds 3]

Intrinsics variants for the final bundle adjustment, all starting from the same full-res model and tracks:
  S   one shared OPENCV camera (focal, k1, k2, p1, p2 refined; principal point fixed at sensor centre).
  G2  two cameras: 'close' (the --close list: tape/joint close-ups focused near) and 'orbit' (everything else).
      orbit: focal + distortion refined; close: focal refined, distortion tied to the orbit values (copied each round).
  F   per-image focal: every image with >= --min_obs observations gets its own camera whose focal is refined;
      weaker images share one camera (focal refined). Distortion fixed at the S solution, principal point fixed.
Each round: robust BA (soft-L1, 1 px scale) -> delete observations with error > --max_err px -> BA again.
Writes a COLMAP binary model to --out and <out>/stats.json (overall/per-image RMS, observations, focal per image).
"""
import argparse, json, pathlib
import numpy as np
import pycolmap

CLOSE_DEFAULT = "1493,1494,1495,1497,1498,1551,1552,1553,1555,1556,1570,1572,1573,1574,1575,1576,1581,1582,1583"


def rebuild(src, assign):
    """Copy reconstruction `src` with a new image->camera-group assignment. assign: name -> group key.
    Each group gets a camera initialised from the source camera of its first image."""
    rec = pycolmap.Reconstruction()
    gid = {}
    for im in sorted(src.images.values(), key=lambda i: i.name):
        g = assign[im.name]
        if g not in gid:
            c = im.camera
            cid = len(gid) + 1
            rec.add_camera_with_trivial_rig(pycolmap.Camera(model=c.model_name, width=c.width, height=c.height,
                                                            params=np.array(c.params), camera_id=cid))
            gid[g] = cid
    for im in src.images.values():
        kp = np.array([p.xy for p in im.points2D], float).reshape(-1, 2)
        new = pycolmap.Image(name=im.name, keypoints=kp, camera_id=gid[assign[im.name]], image_id=im.image_id)
        rec.add_image_with_trivial_frame(new, im.cam_from_world())
    for pid, p in src.points3D.items():
        tr = pycolmap.Track([pycolmap.TrackElement(e.image_id, e.point2D_idx) for e in p.track.elements])
        rec.add_point3D(p.xyz, tr, p.color)
    return rec, gid


def run_ba(rec, refine_focal=True, refine_extra=True, constant_cams=()):
    o = pycolmap.BundleAdjustmentOptions()
    o.refine_focal_length = refine_focal; o.refine_extra_params = refine_extra; o.refine_principal_point = False
    o.ceres.loss_function_type = pycolmap.LossFunctionType.SOFT_L1
    o.ceres.loss_function_scale = 1.0
    o.print_summary = False
    cfg = pycolmap.BundleAdjustmentConfig()
    for iid in rec.reg_image_ids(): cfg.add_image(iid)
    for c in constant_cams: cfg.set_constant_cam_intrinsics(c)
    cfg.fix_gauge(pycolmap.BundleAdjustmentGauge.TWO_CAMS_FROM_WORLD)
    ad = pycolmap.create_default_bundle_adjuster(o, cfg, rec)
    s = ad.solve()
    return s


def obs_errors(rec):
    out = []
    for iid in rec.reg_image_ids():
        im = rec.image(iid); cam = im.camera; T = im.cam_from_world()
        for idx, p in enumerate(im.points2D):
            if not p.has_point3D(): continue
            X = rec.point3D(p.point3D_id).xyz
            xc = T * X
            uv = cam.img_from_cam(xc)
            e = np.inf if uv is None else float(np.linalg.norm(np.asarray(uv).ravel() - np.asarray(p.xy)))
            out.append((iid, idx, e))
    return out


def filter_obs(rec, max_err):
    n = 0
    for iid, idx, e in obs_errors(rec):
        if e > max_err:
            im = rec.image(iid)
            if im.points2D[idx].has_point3D():
                rec.delete_observation(iid, idx); n += 1
    return n


def stats(rec):
    per = {}
    for iid, idx, e in obs_errors(rec):
        per.setdefault(iid, []).append(e)
    allE = np.concatenate([np.array(v) for v in per.values()])
    rows = {}
    for iid, v in per.items():
        im = rec.image(iid); v = np.array(v)
        rows[im.name] = dict(n_obs=len(v), rms_px=float(np.sqrt(np.mean(v ** 2))), mean_px=float(v.mean()),
                             camera_id=im.camera_id, focal=float(im.camera.params[0]))
    for im in rec.images.values():
        if im.name not in rows: rows[im.name] = dict(n_obs=0, rms_px=None, camera_id=im.camera_id, focal=float(im.camera.params[0]))
    return dict(n_images=rec.num_reg_images(), n_points=rec.num_points3D(), n_obs=int(len(allE)),
                rms_px=float(np.sqrt(np.mean(allE ** 2))), mean_px=float(allE.mean()), median_px=float(np.median(allE)),
                cameras={c.camera_id: [float(x) for x in c.params] for c in rec.cameras.values()}, per_image=rows)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", required=True); ap.add_argument("--variant", required=True, choices=["S", "G2", "F"])
    ap.add_argument("--out", required=True); ap.add_argument("--close", default=CLOSE_DEFAULT)
    ap.add_argument("--min_obs", type=int, default=300); ap.add_argument("--max_err", type=float, default=4.0)
    ap.add_argument("--rounds", type=int, default=3)
    a = ap.parse_args()
    src = pycolmap.Reconstruction(a.model)
    close = {f"IMG_{c}.JPG" for c in a.close.split(",")}
    if a.variant == "S":
        assign = {im.name: "all" for im in src.images.values()}
    elif a.variant == "G2":
        assign = {im.name: ("close" if im.name in close else "orbit") for im in src.images.values()}
    else:
        nobs = {im.name: im.num_points3D for im in src.images.values()}
        assign = {n: (n if k >= a.min_obs else "weak") for n, k in nobs.items()}
    rec, gid = rebuild(src, assign)
    print("cameras:", len(gid))
    for r in range(a.rounds):
        if a.variant == "S":
            run_ba(rec)
        elif a.variant == "G2":
            run_ba(rec, refine_focal=True, refine_extra=True, constant_cams=[gid["close"]])
            oc = rec.camera(gid["orbit"]); cc = rec.camera(gid["close"])
            p = np.array(cc.params); p[4:] = np.array(oc.params)[4:]; cc.params = p
            run_ba(rec, refine_focal=True, refine_extra=False, constant_cams=[gid["orbit"]])
        else:
            run_ba(rec, refine_focal=True, refine_extra=False)
        nf = filter_obs(rec, a.max_err)
        st = stats(rec)
        print(f"round {r}: filtered {nf}; rms {st['rms_px']:.3f} mean {st['mean_px']:.3f} median {st['median_px']:.3f}"
              f" pts {st['n_points']} obs {st['n_obs']}")
    run_ba(rec) if a.variant == "S" else None
    st = stats(rec)
    out = pathlib.Path(a.out); out.mkdir(parents=True, exist_ok=True)
    rec.write(str(out))
    st["variant"] = a.variant; st["assign"] = assign
    json.dump(st, open(out / "stats.json", "w"), indent=1)
    print(f"final: rms {st['rms_px']:.3f} mean {st['mean_px']:.3f} median {st['median_px']:.3f} pts {st['n_points']} obs {st['n_obs']}")
    print("cameras:", {k: [round(x, 4) for x in v] for k, v in list(st["cameras"].items())[:4]})


if __name__ == "__main__":
    main()
