"""USAGE: work/toolkit/rk.sh tools/edge_radii/tick.py IMG X0 Y0 X1 Y1 [WIDTH]
Scale of a tape close-up (NOTE: Stanley tapes have 1/32 in marks over the first inches; check the period against the inch numerals): the tape's 1/16 in graduation period along a line drawn through the tick marks (display
orientation, EXIF applied), averaged over WIDTH px across (default 6). Period from the autocorrelation peak in 6-60 px,
refined by a parabola. Refined on the autocorrelation peaks at 2, 4, 8, 16 periods where the line is long enough. Prints px per 1/16 in and px per mm, for the whole line and for its two halves (perspective)."""
import sys
import numpy as np, cv2

img = sys.argv[1]; x0, y0, x1, y1 = map(float, sys.argv[2:6]); W = float(sys.argv[6]) if len(sys.argv) > 6 else 6.0
g = cv2.cvtColor(cv2.imread(f"drive/IMG_{img}.JPG"), cv2.COLOR_BGR2GRAY).astype(np.float32)
p0, p1 = np.array([x0, y0]), np.array([x1, y1]); L = np.linalg.norm(p1 - p0); e = (p1 - p0) / L; n = np.array([-e[1], e[0]])


def period(sa, sb):
    s = np.arange(sa, sb, 0.25); w = np.arange(-W / 2, W / 2 + 1e-6, 1.0)
    mx = (p0[0] + s[:, None] * e[0] + w[None, :] * n[0]).astype(np.float32)
    my = (p0[1] + s[:, None] * e[1] + w[None, :] * n[1]).astype(np.float32)
    v = cv2.remap(g, mx, my, cv2.INTER_LINEAR).mean(1); v = v - np.convolve(v, np.ones(161) / 161, "same")
    v = v[80:-80]
    ac = np.correlate(v, v, "full")[len(v) - 1:]; ac /= ac[0]
    lag = np.arange(len(ac)) * 0.25
    ok = (lag > 6) & (lag < 60)
    i = np.nonzero(ok)[0][np.argmax(ac[ok])]
    y_, z_, w_ = ac[i - 1], ac[i], ac[i + 1]; d = 0.5 * (y_ - w_) / (y_ - 2 * z_ + w_)
    per = (i + d) * 0.25
    for mult in (2, 4, 8, 16):          # refine on the longer marks: the peak near mult x the period
        okm = (lag > per * mult * 0.93) & (lag < per * mult * 1.07)
        if okm.sum() < 3 or lag[okm].max() > lag[-1] - 1: break
        jm = np.nonzero(okm)[0][np.argmax(ac[okm])]
        y_, z_, w_ = ac[jm - 1], ac[jm], ac[jm + 1]; dm = 0.5 * (y_ - w_) / (y_ - 2 * z_ + w_)
        per = (jm + dm) * 0.25 / mult
    return per, ac[i]


for nm, (sa, sb) in (("whole", (0, L)), ("first half", (0, L / 2)), ("second half", (L / 2, L))):
    per, q = period(sa, sb)
    print(f"{nm}: {per:.3f} px per 1/16 in -> {per / 1.5875:.3f} px/mm (autocorr {q:.2f})")
