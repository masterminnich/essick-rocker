"""USAGE: uv run --no-project --with pycolmap --with numpy python -I tools/solve_export.py \
    --variant work/solve/var_S --model_out work/solve/model --json_out solve/cameras.json [--note "..."]

Publishes a solve variant: copies its COLMAP binary model to --model_out and writes a text export with cameras
(OPENCV, full-res raw sensor pixels, COLMAP pixel convention: top-left pixel centre = (0.5, 0.5)), per-image
world->camera pose (R, t, quaternion qvec w,x,y,z), camera centre, per-image RMS reprojection error and number of
observations (taken from the variant's stats.json), plus overall numbers.
"""
import argparse, json, pathlib, shutil
import numpy as np
import pycolmap


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--variant", required=True); ap.add_argument("--model_out", required=True)
    ap.add_argument("--json_out", required=True); ap.add_argument("--note", default="")
    a = ap.parse_args()
    src = pathlib.Path(a.variant); dst = pathlib.Path(a.model_out)
    st = json.load(open(src / "stats.json"))
    if dst.exists(): shutil.rmtree(dst)
    dst.mkdir(parents=True)
    for f in src.glob("*.bin"): shutil.copy(f, dst / f.name)
    shutil.copy(src / "stats.json", dst / "stats.json")
    m = pycolmap.Reconstruction(str(dst))
    cams = {str(c.camera_id): dict(model=c.model_name, width=c.width, height=c.height,
                                   params=[float(x) for x in c.params], param_names="fx,fy,cx,cy,k1,k2,p1,p2")
            for c in m.cameras.values()}
    imgs = {}
    for im in sorted(m.images.values(), key=lambda i: i.name):
        T = im.cam_from_world(); M = T.matrix()
        q = T.rotation.quat  # x,y,z,w
        s = st["per_image"].get(im.name, {})
        imgs[im.name] = dict(image_id=im.image_id, camera_id=im.camera_id, R=M[:, :3].round(12).tolist(),
                             t=M[:, 3].round(12).tolist(), qvec_wxyz=[float(q[3]), float(q[0]), float(q[1]), float(q[2])],
                             center=im.projection_center().round(9).tolist(), n_obs=s.get("n_obs"),
                             rms_px=s.get("rms_px"), mean_px=s.get("mean_px"))
    out = dict(source_variant=str(src), model=str(dst), variant=st.get("variant"), note=a.note,
               convention="x_cam = R @ X_world + t; pixels on RAW sensor grid 4032x3024 (EXIF orientation not applied); "
                          "COLMAP continuous pixel coords (top-left pixel centre = 0.5,0.5); OPENCV distortion",
               n_images=st["n_images"], n_points=st["n_points"], n_obs=st["n_obs"], rms_px=st["rms_px"],
               mean_px=st["mean_px"], median_px=st["median_px"], cameras=cams, images=imgs)
    pathlib.Path(a.json_out).parent.mkdir(parents=True, exist_ok=True)
    json.dump(out, open(a.json_out, "w"), indent=1)
    print("exported", len(imgs), "images,", len(cams), "cameras; rms", round(st["rms_px"], 3))


if __name__ == "__main__":
    main()
