"""Plane fitting helpers (chair frame, mm)."""
import numpy as np


def fit_plane(Q):
    c = Q.mean(0); _, sv, vt = np.linalg.svd(Q - c)
    return c, vt[2]


def ransac_plane(P, thr=1.0, iters=3000, seed=0, normal_hint=None, max_angle_deg=None):
    """Returns (c, n, inlier_mask). normal_hint/max_angle_deg restrict the plane orientation."""
    rng = np.random.default_rng(seed); best = None
    for _ in range(iters):
        a, b, c = P[rng.choice(len(P), 3, replace=False)]
        n = np.cross(b - a, c - a); ln = np.linalg.norm(n)
        if ln < 1e-9: continue
        n /= ln
        if normal_hint is not None and np.degrees(np.arccos(min(1, abs(n @ normal_hint)))) > max_angle_deg: continue
        inl = np.abs((P - a) @ n) < thr
        if best is None or inl.sum() > best.sum(): best = inl
    c, n = fit_plane(P[best])
    inl = np.abs((P - c) @ n) < thr
    c, n = fit_plane(P[inl])
    if normal_hint is not None and n @ normal_hint < 0: n = -n
    return c, n, inl
