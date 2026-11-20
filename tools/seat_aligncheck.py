"""USAGE: tools/py.sh -m 1 -t 2 tools/seat_aligncheck.py
Common rotation of the OLD cameras after the joint-SfM -> chair-frame similarity (work/seat/joint_align.json):
rotation vector (deg, about chair x, y, z) per camera, mean and sd. A pitch of the dot frame would show as a mean about x. Tiny."""
import sys, json; sys.path.insert(0,".")
import numpy as np, pycolmap, cv2
from rocker.cameras import Cameras
ja=json.load(open("work/seat/joint_align.json")); Rj=np.array(ja["R"])
rec=pycolmap.Reconstruction(ja["model"]); cams=Cameras.load()
rv=[]
for im in rec.images.values():
    if im.name not in ja["old"]: continue
    Rcj=im.cam_from_world().matrix()[:,:3]; Rch=Rcj@Rj.T
    dR=cams[im.name].R_chair.T@Rch          # chair-frame rotation error (world side)
    rv.append(cv2.Rodrigues(dR)[0][:,0])
rv=np.degrees(np.array(rv)); print(np.round(rv,3)); print("mean (about x,y,z) deg", rv.mean(0).round(3), " sd", rv.std(0).round(3))
