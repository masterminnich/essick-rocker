"""Sub-pixel refiners: rough seed (raw px) -> refined mark (raw px) + a quality report.
All work on the raw (unrotated) image, so they are orientation independent.

  blob(name, seed, radius)            contrasting round feature (dowel/tenon plug, screw head): Otsu threshold in a
                                      window, component at/nearest the seed, ellipse fit -> centre
  corner(name, seed, win)             cv2.cornerSubPix on a true corner (crisp intersection of two edges)
  edges(name, (a1, a2), (b1, b2))     two straight edges, each seeded by 2 rough points along it: gradient maxima
                                      on perpendicular profiles -> trimmed line fit -> intersection
  edge_point(name, seed, direction)   strongest gradient along a profile through seed in the given direction
"""
import numpy as np
import cv2
from .images import load_raw


def _gray(name):
    """name of a photo, or a numpy image (for synthetic tests)."""
    if isinstance(name, np.ndarray):
        return (cv2.cvtColor(name, cv2.COLOR_BGR2GRAY) if name.ndim == 3 else name).astype(np.float32)
    return cv2.cvtColor(load_raw(name), cv2.COLOR_BGR2GRAY).astype(np.float32)


def blob(name, seed, radius=25, window=1.5):
    """radius ~ half the blob's longest extent; the analysis window is +-window*radius around the seed, so it
    should contain the blob plus a margin of its surround but no other big dark/bright regions."""
    g = _gray(name)
    x0, y0 = int(round(seed[0])), int(round(seed[1]))
    r = int(round(radius * window))
    xa, ya = max(0, x0 - r), max(0, y0 - r)
    win = g[ya:y0 + r + 1, xa:x0 + r + 1]
    win = cv2.GaussianBlur(win, (0, 0), 1.0)
    yy, xx = np.mgrid[:win.shape[0], :win.shape[1]]
    d = np.hypot(xx - (x0 - xa), yy - (y0 - ya))
    inner = np.median(win[d < max(2, radius * 0.25)])
    ring = np.median(win[(d > radius) & (d < radius * window)])
    dark = inner < ring
    thr = 0.5 * (inner + ring)       # midpoint between blob and its own surround (robust to other regions)
    bw = ((win < thr) if dark else (win > thr)).astype(np.uint8) * 255
    bw = cv2.morphologyEx(bw, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    n, lab, stats, cents = cv2.connectedComponentsWithStats(bw)
    sx, sy = x0 - xa, y0 - ya
    best, bd = None, 1e9
    for i in range(1, n):
        dd = np.hypot(cents[i][0] - sx, cents[i][1] - sy)
        if lab[sy, sx] == i:
            dd = -1
        if dd < bd and stats[i, cv2.CC_STAT_AREA] > 8:
            best, bd = i, dd
    if best is None:
        return None, dict(ok=False, why="no component")
    cs, _ = cv2.findContours((lab == best).astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    c = max(cs, key=len)
    if len(c) < 6:
        return None, dict(ok=False, why="contour too small")
    (ex, ey), (MA, ma), ang = cv2.fitEllipse(c)
    touches = (stats[best, cv2.CC_STAT_LEFT] == 0 or stats[best, cv2.CC_STAT_TOP] == 0 or
               stats[best, cv2.CC_STAT_LEFT] + stats[best, cv2.CC_STAT_WIDTH] >= win.shape[1] or
               stats[best, cv2.CC_STAT_TOP] + stats[best, cv2.CC_STAT_HEIGHT] >= win.shape[0])
    # ellipse fit residual: mean |algebraic distance| of contour points to the ellipse, px
    pts = c[:, 0, :].astype(float) - [ex, ey]
    t = np.radians(ang); R = np.array([[np.cos(t), np.sin(t)], [-np.sin(t), np.cos(t)]])
    q = pts @ R.T
    rr = np.hypot(q[:, 0] / (MA / 2), q[:, 1] / (ma / 2))
    fit = float(np.mean(np.abs(rr - 1)) * (MA + ma) / 4)
    xy = np.array([ex + xa, ey + ya])
    # cv2 contour coords are pixel indices on the boundary pixels; centre is unbiased for a symmetric blob
    info = dict(ok=not touches and fit < 3.5, axes=(MA, ma), angle=ang, fit_px=fit, dark=bool(dark),
                touches_window=bool(touches), moved=float(np.hypot(*(xy - seed))))
    return xy, info


def _corner1(g, seed, win):
    p = np.array([[seed]], np.float32)
    crit = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 100, 0.001)
    return cv2.cornerSubPix(g, p.copy(), (win, win), (-1, -1), crit)[0, 0].astype(float)


def corner(name, seed, win=7, starts=3.0):
    """cv2.cornerSubPix from 5 starts (seed and seed +-starts px in x and y). On real, textured wood/paint it often
    stalls at its start point, so the result is the median of the 5 and 'ok' requires >=3 of them within 1 px of it."""
    g = _gray(name)
    seed = np.asarray(seed, float)
    S = [seed + d for d in ([0, 0], [starts, 0], [-starts, 0], [0, starts], [0, -starts])]
    R = np.array([_corner1(g, s, win) for s in S])
    r = np.median(R, axis=0)
    dist = np.hypot(*(R - r).T)
    spread = float(np.max(dist))
    agree = int(np.sum(dist < 1.0))
    x0, y0 = int(round(r[0])), int(round(r[1]))
    gx = cv2.Sobel(g, cv2.CV_32F, 1, 0)[y0 - win:y0 + win + 1, x0 - win:x0 + win + 1]
    gy = cv2.Sobel(g, cv2.CV_32F, 0, 1)[y0 - win:y0 + win + 1, x0 - win:x0 + win + 1]
    T = np.array([[np.sum(gx * gx), np.sum(gx * gy)], [np.sum(gx * gy), np.sum(gy * gy)]])
    ev = np.linalg.eigvalsh(T)
    moved = float(np.hypot(*(r - seed)))
    cn = float(ev[0] / max(ev[1], 1e-9))
    return r, dict(ok=bool(moved < win and cn > 0.05 and agree >= 3), moved=moved, spread=spread, agree=agree, cornerness=cn)


def _profile_peak(g, gx, gy, p, n, half=12):
    """Sub-pixel position of max |gradient . n| along p + t n, t in [-half, half]."""
    ts = np.arange(-half, half + 0.5, 0.5)
    pts = p + ts[:, None] * n
    mx = cv2.remap(gx, pts[:, 0:1].astype(np.float32), pts[:, 1:2].astype(np.float32), cv2.INTER_LINEAR)[:, 0]
    my = cv2.remap(gy, pts[:, 0:1].astype(np.float32), pts[:, 1:2].astype(np.float32), cv2.INTER_LINEAR)[:, 0]
    s = np.abs(mx * n[0] + my * n[1])
    k = int(np.argmax(s))
    if 0 < k < len(s) - 1:
        den = s[k - 1] - 2 * s[k] + s[k + 1]
        off = 0.5 * (s[k - 1] - s[k + 1]) / den if den != 0 else 0
    else:
        off = 0
    return p + (ts[k] + 0.5 * off) * n, float(s[k])


def _grads(name, blur=1.2):
    g = cv2.GaussianBlur(_gray(name), (0, 0), blur)
    return g, cv2.Sobel(g, cv2.CV_32F, 1, 0, ksize=3), cv2.Sobel(g, cv2.CV_32F, 0, 1, ksize=3)


def fit_edge(name, a, b, half=12, n_prof=25, extend=0.0):
    g, gx, gy = _grads(name)
    a, b = np.asarray(a, float), np.asarray(b, float)
    d = (b - a) / np.linalg.norm(b - a); n = np.array([-d[1], d[0]])
    pts, st = [], []
    for s in np.linspace(-extend, 1 + extend, n_prof):
        q, strength = _profile_peak(g, gx, gy, a + s * (b - a), n, half)
        pts.append(q); st.append(strength)
    pts, st = np.array(pts), np.array(st)
    keep = st > 0.3 * np.median(st)
    for _ in range(3):
        c = pts[keep].mean(0)
        _, _, Vt = np.linalg.svd(pts[keep] - c)
        dirn = Vt[0]; nn = np.array([-dirn[1], dirn[0]])
        res = (pts - c) @ nn
        sig = 1.4826 * np.median(np.abs(res[keep])) + 0.1
        keep = keep & (np.abs(res) < 3 * sig)
    return c, dirn, dict(n_used=int(keep.sum()), rms_px=float(np.sqrt(np.mean(res[keep] ** 2))))


def edges(name, edge1, edge2, half=12):
    c1, d1, i1 = fit_edge(name, *edge1, half=half)
    c2, d2, i2 = fit_edge(name, *edge2, half=half)
    A = np.c_[d1, -d2]
    if abs(np.linalg.det(A)) < 1e-3:
        return None, dict(ok=False, why="edges parallel")
    t = np.linalg.solve(A, c2 - c1)
    xy = c1 + t[0] * d1
    ang = np.degrees(np.arccos(abs(d1 @ d2)))
    return xy, dict(ok=i1["rms_px"] < 1.5 and i2["rms_px"] < 1.5 and ang > 15, edge1=i1, edge2=i2, angle_deg=float(ang))


def edge_point(name, seed, direction, half=15):
    g, gx, gy = _grads(name)
    n = np.asarray(direction, float); n /= np.linalg.norm(n)
    q, s = _profile_peak(g, gx, gy, np.asarray(seed, float), n, half)
    return q, dict(ok=True, strength=s, moved=float(np.hypot(*(q - seed))))
