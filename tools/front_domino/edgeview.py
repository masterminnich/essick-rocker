"""USAGE: rk.sh work/fdom/edgeview.py LEG PHOTOS OUT.jpg   two crops per photo of the straightened ortho, around the rear edge (s -36..-14)
and the front edge (s 2..24), v -28..58; 10 px/mm across, 5 px/mm up; ticks every mm, labels every 5 (s mm). With the mean dL/ds profile
of the bands below (v -28..6) and above (v 34..58) the Domino drawn under each crop (white = below, cyan = above)."""
import sys, json, cv2, numpy as np
sys.path.insert(0, "work/fdom"); from shear import straight
from scipy.ndimage import gaussian_filter
leg, phs, out = sys.argv[1], sys.argv[2].split(","), sys.argv[3]; T = []; RD = json.load(open(sys.argv[4])) if len(sys.argv) > 4 else {}
for ph in phs:
    im, ss, vs = straight(leg, ph, (-45, 25), (-28, 58), 0.1); L = gaussian_filter(cv2.cvtColor(im, cv2.COLOR_BGR2Lab)[:, :, 0].astype(float), 3); g = np.gradient(L, axis=1)
    cols = []
    for s0, s1 in ((-36, -14), (2, 24)):
        c0, c1 = int((s0 + 45) / 0.1), int((s1 + 45) / 0.1); cr = im[:, c0:c1]; cr = cv2.resize(cr, (cr.shape[1], cr.shape[0] // 2), interpolation=cv2.INTER_AREA)
        lab = cv2.cvtColor(cr, cv2.COLOR_BGR2Lab); lab[:, :, 0] = cv2.createCLAHE(2.0, (4, 4)).apply(lab[:, :, 0]); cr = cv2.cvtColor(lab, cv2.COLOR_Lab2BGR)
        pl = np.full((90, cr.shape[1], 3), 30, np.uint8); cv2.line(pl, (0, 45), (cr.shape[1], 45), (90, 90, 90), 1)
        for (b0, b1), col in (((-28, 6), (255, 255, 255)), ((34, 58), (255, 255, 0))):
            rows = (vs >= b0) & (vs <= b1); p = g[rows, c0:c1].mean(0); p = 45 - p / max(1e-6, np.abs(g[:, c0:c1]).mean(0).max() * 1.0) * 40
            cv2.polylines(pl, [np.c_[np.arange(len(p)), np.clip(p, 0, 89)].astype(np.int32)], False, col, 1)
        top = np.full((16, cr.shape[1], 3), 255, np.uint8)
        for k in range(int(np.ceil(s0)), int(s1) + 1):
            x = int(round((k - s0) * 10)); h = 8 if k % 5 == 0 else 4
            for a in (cr, pl): cv2.line(a, (x, 0), (x, h), (0, 255, 255) if k % 5 == 0 else (200, 200, 200), 1)
            if k % 5 == 0: cv2.putText(top, str(k), (x - 8, 12), 0, 0.38, (0, 0, 0), 1, cv2.LINE_AA)
        for e in ("rear", "front"):
            for b0, b1, s_, g_ in RD.get(ph, {}).get("edges", {}).get(e, []):
                if s0 <= s_ <= s1:
                    x = int(round((s_ - s0) * 10)); cv2.line(cr, (x, int((58 - b1) * 5)), (x, int((58 - b0) * 5)), (0, 255, 0), 1)
        for vv in range(-20, 59, 10): y = int(round((58 - vv) * 5)); cv2.line(cr, (0, y), (6, y), (0, 255, 255), 1)
        cols.append(np.vstack([top, cr, pl])); cols.append(np.full((cols[-1].shape[0], 6, 3), 255, np.uint8))
    t = np.hstack(cols); cv2.rectangle(t, (0, t.shape[0] - 108), (44, t.shape[0] - 90), (255, 255, 255), -1); cv2.putText(t, ph, (2, t.shape[0] - 94), 0, 0.45, (0, 0, 0), 1); T.append(t)
per = 3; rows = [np.hstack(T[i:i+per] + [np.zeros_like(T[0])] * (per - len(T[i:i+per]))) for i in range(0, len(T), per)]
cv2.imwrite(out, np.vstack(rows), [cv2.IMWRITE_JPEG_QUALITY, 92])
