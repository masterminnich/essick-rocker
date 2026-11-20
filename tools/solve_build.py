"""USAGE: uv run --no-project --with pycolmap --with numpy python -I tools/solve_build.py \
    --init work/sfm/sparse/0 --db work/solve/db_full.db --images work/sfm_full/images --out work/solve/single [--rounds 2]

Full-resolution re-triangulation + bundle adjustment from an initial pose set.
The half-res probe registered 93/94 images in one model, the full-res probe split into 83 + 10. This tool takes the
initial poses (any model whose image NAMES match the database; intrinsics are promoted to the database image size),
attaches the full-res keypoints from the database, triangulates all verified matches with fixed poses
(COLMAP point_triangulator), then alternates global bundle adjustment (poses, points, one shared OPENCV camera incl.
distortion) and re-triangulation --rounds times. Writes a COLMAP binary model to --out and prints its summary.
"""
import argparse, pathlib, shutil
import numpy as np
import pycolmap


def build(init_path, db_path):
    init = pycolmap.Reconstruction(str(init_path))
    db = pycolmap.Database.open(str(db_path)) if hasattr(pycolmap.Database, "open") else pycolmap.Database(str(db_path))
    dbcams = {c.camera_id: c for c in db.read_all_cameras()}
    assert len(dbcams) == 1, "expects a single-camera database"
    dbcam = next(iter(dbcams.values()))
    c0 = next(iter(init.cameras.values()))
    s = dbcam.width / c0.width
    p = np.array(c0.params, float); p[:4] *= s
    cam = pycolmap.Camera(model="OPENCV", width=dbcam.width, height=dbcam.height, params=p, camera_id=dbcam.camera_id)
    rec = pycolmap.Reconstruction()
    rec.add_camera_with_trivial_rig(cam)
    for im in init.images.values():
        if not im.has_pose: continue
        dbim = db.read_image_with_name(im.name)
        kp = db.read_keypoints(dbim.image_id)[:, :2].astype(np.float64)
        new = pycolmap.Image(name=im.name, keypoints=kp, camera_id=cam.camera_id, image_id=dbim.image_id)
        rec.add_image_with_trivial_frame(new, im.cam_from_world())
    db.close()
    return rec


def ba(rec, refine_intrinsics=True):
    o = pycolmap.BundleAdjustmentOptions()
    o.refine_focal_length = o.refine_principal_point = o.refine_extra_params = refine_intrinsics
    o.refine_principal_point = False  # principal point is poorly constrained; keep at sensor centre
    pycolmap.bundle_adjustment(rec, o)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--init", required=True); ap.add_argument("--db", required=True); ap.add_argument("--images", required=True)
    ap.add_argument("--out", required=True); ap.add_argument("--rounds", type=int, default=2)
    a = ap.parse_args()
    out = pathlib.Path(a.out); out.mkdir(parents=True, exist_ok=True)
    rec = build(a.init, a.db)
    opts = pycolmap.IncrementalPipelineOptions()
    for r in range(a.rounds):
        tmp = out / f"_tri{r}"; tmp.mkdir(exist_ok=True)
        rec = pycolmap.triangulate_points(rec, a.db, a.images, tmp, clear_points=True, options=opts, refine_intrinsics=True)
        print(f"round {r} triangulated:", rec.num_points3D(), "pts, err", round(rec.compute_mean_reprojection_error(), 3))
        ba(rec)
        print(f"round {r} after BA:", rec.num_points3D(), "pts, err", round(rec.compute_mean_reprojection_error(), 3),
              [round(x, 4) for x in next(iter(rec.cameras.values())).params])
        shutil.rmtree(tmp, ignore_errors=True)
    rec.write(str(out))
    print(rec.summary())


if __name__ == "__main__":
    main()
