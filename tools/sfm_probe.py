"""USAGE: uv run --no-project --with pycolmap --with pillow python -I tools/sfm_probe.py <src_dir> <work_dir> [max_px]
Feasibility probe: half-res copies (raw sensor orientation, one shared camera), SIFT, exhaustive match, incremental SfM.
Prints how many images registered and reprojection error."""
import sys, os, pathlib
from PIL import Image
import pycolmap
src, work = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
max_px = int(sys.argv[3]) if len(sys.argv) > 3 else 2016
img = work / "images"; img.mkdir(parents=True, exist_ok=True)
for n in sorted(os.listdir(src)):
    o = img / n
    if not o.exists():
        im = Image.open(src / n); im.thumbnail((max_px, max_px)); im.save(o, quality=97, subsampling=0)  # no EXIF, no rotation
db = work / "db.db"
if db.exists(): db.unlink()
f = 26/36 * max_px
ropts = pycolmap.ImageReaderOptions(); ropts.camera_model = "OPENCV"; ropts.camera_params = f"{f},{f},{max_px/2},{max_px*0.375},0,0,0,0"
pycolmap.extract_features(db, img, camera_mode=pycolmap.CameraMode.SINGLE, reader_options=ropts)
pycolmap.match_exhaustive(db)
out = work / "sparse"; out.mkdir(exist_ok=True)
maps = pycolmap.incremental_mapping(db, img, out)
for i, m in maps.items():
    print("MODEL", i, "images", m.num_reg_images(), "points", m.num_points3D(), "mean_reproj_err", round(m.compute_mean_reprojection_error(), 3))
    print(" camera", [c.params.round(2).tolist() for c in m.cameras.values()])
    reg = sorted(im.name for im in m.images.values())
    print(" registered:", " ".join(x[4:8] for x in reg))
allreg = set(im.name for m in maps.values() for im in m.images.values())
print("UNREGISTERED:", " ".join(sorted(x[4:8] for x in set(os.listdir(img)) - allreg)))
