"""Cameras of the solved model PLUS the photos registered by tools/seat_register.py (work/seat/poses.json).

    from rocker.seatcams import load
    cams = load()                 # cams["IMG_1605.JPG"].project(X) etc., same API as rocker.cameras.Cameras
Registered views share the model's intrinsics (same phone, same lens, no zoom).
"""
import json
import numpy as np
from . import ROOT
from .cameras import Cameras, View
from .orientation import exif_orientation

POSES = ROOT / "work/seat/poses.json"


def load(min_inliers=60):
    cams = Cameras.load()
    ref = cams[cams.names()[0]]
    if POSES.exists():
        for name, r in json.loads(POSES.read_text()).items():
            if r.get("status") != "ok" or r["n_inliers"] < min_inliers or name in cams.views: continue
            p = cams.drive / name
            cams.views[name] = View(name, ref.model, ref.params, np.array(r["Rcw"]), np.array(r["tcw"]), ref.scale,
                                    cams.metric, exif_orientation(str(p)))
    return cams
