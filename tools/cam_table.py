"""USAGE: python -I tools/cam_table.py [--target X Y Z] [--photos 1544,1545 | all]
Print each solved camera's centre (chair frame, mm), its height, its distance and elevation angle as seen from TARGET
(degrees above horizontal; 90 = straight overhead) and whether TARGET projects inside the frame. Tiny compute (camera model only)."""
import sys, argparse
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import numpy as np
from rocker.cameras import Cameras
ap = argparse.ArgumentParser(); ap.add_argument("--target", nargs=3, type=float, default=[0, -170, 1050]); ap.add_argument("--photos", default="all")
a = ap.parse_args(); cams = Cameras.load(); T = np.array(a.target)
names = sorted(cams.views) if a.photos == "all" else [f"IMG_{p}.JPG" for p in a.photos.split(",")]
rows = []
for nm in names:
    if nm not in cams.views: print(nm, "not in model"); continue
    v = cams.views[nm]; C = v.center; d = C - T; el = np.degrees(np.arcsin(d[2] / np.linalg.norm(d)))
    inside = bool(v.in_image(v.project(T[None]), margin=0)[0])
    rows.append((el, nm, C, np.linalg.norm(d), inside))
for el, nm, C, dist, ins in sorted(rows, reverse=True):
    print(f"{nm[4:8]}  C=({C[0]:7.0f},{C[1]:7.0f},{C[2]:7.0f})  dist {dist:6.0f}  elev {el:5.1f}  {'in' if ins else 'OUT'}")
