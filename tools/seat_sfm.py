"""USAGE: tools/py.sh -m 4 -t 20 tools/seat_sfm.py [--out NAME] IMG_1595 IMG_1597 ...
Own small SfM of the blue-dot seat photos at HALF resolution (2016x1512, raw sensor orientation), with the final model's
intrinsics (scaled x0.5) held FIXED (same iPhone 14, 26 mm, no zoom). Exhaustive matching, incremental mapping.
Output: work/seat/sfm/sparse/<k>/ (COLMAP, arbitrary similarity frame; align with tools/seat_align.py).
Compute audit: 17 photos -> ~8k SIFT each, 136 pairs, 2 threads; peak ~1-2 GB, ~5-10 min. One photo decoded at a time."""
import sys, pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from PIL import Image
import pycolmap
OUT = "sfm"
if sys.argv[1] == "--out": OUT = sys.argv[2]; del sys.argv[1:3]
names = [n if n.endswith(".JPG") else (n if n.startswith("IMG_") else "IMG_" + n) + ".JPG" for n in sys.argv[1:]]
W = ROOT / "work/seat" / OUT; img = W / "images"; img.mkdir(parents=True, exist_ok=True)
for n in names:
    o = img / n
    if not o.exists():
        im = Image.open(ROOT / "drive" / n); im = im.resize((2016, 1512), Image.LANCZOS); im.save(o, quality=97, subsampling=0)
ref = pycolmap.Reconstruction(str(ROOT / "work/solve/model")); cam = next(iter(ref.cameras.values()))
assert cam.model.name == "OPENCV" and cam.width == 4032, (cam.model.name, cam.width)
p = cam.params.copy(); p[:4] *= 0.5     # COLMAP continuous coords: f, cx, cy scale exactly by 0.5
db = W / "db.db"
if db.exists(): db.unlink()
ro = pycolmap.ImageReaderOptions(); ro.camera_model = "OPENCV"; ro.camera_params = ",".join(f"{x:.10g}" for x in p)
eo = pycolmap.FeatureExtractionOptions(); eo.num_threads = 2; eo.use_gpu = False; eo.max_image_size = 2016
eo.sift.max_num_features = 12000      # ~0.9 GB per extraction thread measured (10 threads hit 8.8 GB): 2 threads ~2 GB
pycolmap.extract_features(db, img, camera_mode=pycolmap.CameraMode.SINGLE, reader_options=ro, extraction_options=eo,
                          device=pycolmap.Device.cpu)
mo = pycolmap.FeatureMatchingOptions(); mo.num_threads = 2; mo.use_gpu = False
pycolmap.match_exhaustive(db, matching_options=mo, device=pycolmap.Device.cpu)
opts = pycolmap.IncrementalPipelineOptions(); opts.num_threads = 2
opts.ba_refine_focal_length = False; opts.ba_refine_principal_point = False; opts.ba_refine_extra_params = False
out = W / "sparse"; out.mkdir(exist_ok=True)
maps = pycolmap.incremental_mapping(db, img, out, options=opts)
for i, m in maps.items():
    print("MODEL", i, "images", m.num_reg_images(), "points", m.num_points3D(), "mean_reproj_err", round(m.compute_mean_reprojection_error(), 3))
    print(" registered:", " ".join(sorted(im.name[4:8] for im in m.images.values())))
