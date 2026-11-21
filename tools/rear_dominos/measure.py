"""USAGE: tools/py.sh tools/rear_dominos/measure.py PLANES.json KEY "uc vc" OUT.jpg PHOTOS(1501,1502,..) [HALF_U 22] [HALF_V 12]
Step 2 of 3 (tools/rear_ortho.py -> measure -> tri). Fine orthophoto (0.1 mm/px, no grid over the picture, mm ticks on the border) of ONE
Domino end on a rear_ortho plane (PLANES.json = OUTDIR/planes.json of tools/rear_ortho.py, KEY e.g. BLEG_L_seat, "uc vc" = the end's
centre in plane mm), one tile per photo, and the edges of the dark oval by the steepest tone change: along u through the centre row
band (+-2 mm) and along v through the centre column band (+-4 mm), marked yellow on the border. Check every reading by eye on the tile:
on a dark background the steepest change sits inside the end's rim.
Compute: one photo decoded at a time; < 1 GB, seconds."""
import sys, json; sys.path.insert(0, ".")
import numpy as np, cv2
from scipy.ndimage import gaussian_filter1d
from rocker.cameras import Cameras
from rocker.ortho import Plane, ortho
P = json.load(open(sys.argv[1]))[sys.argv[2]]; uc, vc = [float(v) for v in sys.argv[3].split()]; out = sys.argv[4]; photos = [f"IMG_{p}.JPG" for p in sys.argv[5].split(",")]
HU = float(sys.argv[6]) if len(sys.argv) > 6 else 22.0; HV = float(sys.argv[7]) if len(sys.argv) > 7 else 12.0; R = 0.1
pl = Plane(P["origin"], P["u"], P["v"]); cams = Cameras.load(); tiles = []
for nm in photos:
    img = np.ascontiguousarray(ortho(cams, nm, pl, (uc - HU, uc + HU), (vc - HV, vc + HV), R)); L = cv2.cvtColor(img, cv2.COLOR_BGR2Lab)[:, :, 0].astype(float)
    us = uc - HU + R * np.arange(img.shape[1]); vs = vc + HV - R * np.arange(img.shape[0])
    def edges(prof, ax):
        g = np.gradient(gaussian_filter1d(prof, 4)); c = len(prof) // 2
        a = int(np.argmin(g[:c])); b = c + int(np.argmax(g[c:])); return ax[a], ax[b], g[a], g[b]      # falls into the dark oval, rises out of it
    rows = np.abs(vs - vc) < 2.0; cols = np.abs(us - uc) < 4.0
    ua, ub, ga, gb = edges(L[rows].mean(0), us); va, vb, gc, gd = edges(L[:, cols].mean(1)[::-1], vs[::-1])
    print(f"{nm[4:8]}: u {ua:+6.1f} .. {ub:+6.1f} (len {ub - ua:4.1f}, step {ga:+.2f}/{gb:+.2f})   v {va:+6.1f} .. {vb:+6.1f} (height {vb - va:4.1f}, step {gc:+.2f}/{gd:+.2f})")
    z = 3; big = cv2.resize(img, None, fx=z * 1.0, fy=z * 1.0, interpolation=cv2.INTER_CUBIC); big = cv2.copyMakeBorder(big, 24, 0, 30, 0, cv2.BORDER_CONSTANT, value=(255, 255, 255))
    for g in range(int(np.ceil(uc - HU)), int(uc + HU) + 1):
        x = 30 + int(round((g - (uc - HU)) / R * z)); cv2.line(big, (x, 24 - (12 if g % 5 == 0 else 5)), (x, 24), (0, 0, 0), 1)
        if g % 5 == 0: cv2.putText(big, str(g), (x - 8, 10), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 0, 0), 1, cv2.LINE_AA)
    for g in range(int(np.ceil(vc - HV)), int(vc + HV) + 1):
        y = 24 + int(round((vc + HV - g) / R * z)); cv2.line(big, (30 - (12 if g % 5 == 0 else 5), y), (30, y), (0, 0, 0), 1)
        if g % 5 == 0: cv2.putText(big, str(g), (0, y + 4), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 0, 0), 1, cv2.LINE_AA)
    for u_ in (ua, ub): x = 30 + int(round((u_ - (uc - HU)) / R * z)); cv2.line(big, (x, 24), (x, 60), (0, 255, 255), 1); cv2.line(big, (x, big.shape[0] - 36), (x, big.shape[0]), (0, 255, 255), 1)
    for v_ in (va, vb): y = 24 + int(round((vc + HV - v_) / R * z)); cv2.line(big, (30, y), (66, y), (0, 255, 255), 1); cv2.line(big, (big.shape[1] - 36, y), (big.shape[1], y), (0, 255, 255), 1)
    cv2.putText(big, nm[4:8], (36, big.shape[0] - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2, cv2.LINE_AA); tiles.append(big)
per = 2; rows_ = [np.hstack(tiles[i:i + per] + [np.full_like(tiles[0], 255)] * (per - len(tiles[i:i + per]))) for i in range(0, len(tiles), per)]
cv2.imwrite(out, np.vstack(rows_), [cv2.IMWRITE_JPEG_QUALITY, 92]); print(out, np.vstack(rows_).shape)
