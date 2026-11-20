"""Shared CLI plumbing for the rocker toolkit (not a CLI itself)."""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def add_camera_args(ap):
    ap.add_argument("--model", default=str(ROOT / "work/solve/model"), help="COLMAP model dir (half-res probe: work/sfm/sparse/0; final: work/solve/model)")
    ap.add_argument("--metric", default=str(ROOT / "solve/metric_frame.json"), help="metric frame json; missing = COLMAP units")
    ap.add_argument("--image-scale", type=float, default=None, help="raw px per model px (default: 4032/camera.width)")


def load_cams(a):
    from rocker.cameras import Cameras
    return Cameras.load(a.model, metric=a.metric, image_scale=a.image_scale)


def img_name(s):
    s = str(s)
    return f"IMG_{s}.JPG" if s.isdigit() else s
