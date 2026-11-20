"""Robust multi-view triangulation of one point from raw-pixel marks.

    res = triangulate(cams, [("IMG_1470.JPG", (x, y)), ("IMG_1490.JPG", (x, y)), ...], sigma_px=1.0)
    res.X, res.residuals_px, res.rms_px, res.sigma_mm, res.outlier

Steps: (1) linear init = least-squares closest point to all back-projected rays (distortion-aware);
(2) nonlinear refinement of reprojection error in raw (full-res) pixels (plain least squares by default;
   loss="soft_l1" available, but it biases the point slightly, so rejection is done explicitly instead);
(3) outlier rejection: while a view's residual > max(outlier_px, 4*robust sigma) and >= min_views would
remain, drop the worst and re-solve; (4) covariance = s^2 (J^T J)^-1 from the ray geometry, with
s = max(sigma_px prior, a-posteriori RMS) -> 1-sigma error ellipsoid in chair units (mm when the metric
frame exists). Camera-pose / scale uncertainty is NOT included.
"""
from dataclasses import dataclass, field
import numpy as np
from scipy.optimize import least_squares


@dataclass
class TriResult:
    X: np.ndarray
    names: list
    marks: np.ndarray
    residuals_px: np.ndarray            # per-view residual norm, raw px (all views incl. outliers)
    outlier: np.ndarray                 # bool per view
    cov: np.ndarray = None              # 3x3 chair units^2
    sigma_used_px: float = np.nan
    ray_angle_deg: float = np.nan       # max angle between inlier rays
    ok: bool = True
    msg: str = ""

    @property
    def n_inliers(self):
        return int((~self.outlier).sum())

    @property
    def rms_px(self):
        r = self.residuals_px[~self.outlier]
        return float(np.sqrt(np.mean(r ** 2))) if len(r) else np.nan

    @property
    def max_px(self):
        r = self.residuals_px[~self.outlier]
        return float(r.max()) if len(r) else np.nan

    @property
    def sigma_axes(self):
        """1-sigma semi-axes of the error ellipsoid (sorted, chair units)."""
        return np.sqrt(np.clip(np.sort(np.linalg.eigvalsh(self.cov))[::-1], 0, None)) if self.cov is not None else np.full(3, np.nan)

    @property
    def sigma_mm(self):
        """Scalar 3D 1-sigma uncertainty = sqrt(trace(cov)) (chair units)."""
        return float(np.sqrt(np.trace(self.cov))) if self.cov is not None else np.nan


def rays_closest_point(origins, dirs):
    A = np.zeros((3, 3)); b = np.zeros(3)
    for o, d in zip(origins, dirs):
        P = np.eye(3) - np.outer(d, d)
        A += P; b += P @ o
    return np.linalg.lstsq(A, b, rcond=None)[0]


def _solve(views, uvs, X0, loss, f_scale):
    def fun(X):
        return np.concatenate([v.project(X[None])[0] - uv for v, uv in zip(views, uvs)])
    r = least_squares(lambda X: np.nan_to_num(fun(X), nan=1e6), X0, loss=loss, f_scale=f_scale,
                      method="trf", x_scale="jac")
    return r.x, fun


def _jac(views, X, h):
    J = []
    for v in views:
        Jv = np.zeros((2, 3))
        for k in range(3):
            d = np.zeros(3); d[k] = h
            Jv[:, k] = (v.project((X + d)[None])[0] - v.project((X - d)[None])[0]) / (2 * h)
        J.append(Jv)
    return np.vstack(J)


def triangulate(cams, obs, sigma_px=1.0, outlier_px=6.0, min_views=2, loss="linear", f_scale=2.0):
    """obs: list of (image_name, (x_raw, y_raw)). Returns TriResult."""
    names = [n for n, _ in obs]
    views = [cams[n] for n in names]
    uvs = np.array([uv for _, uv in obs], float)
    n = len(views)
    outl = np.zeros(n, bool)
    if n < 2:
        return TriResult(np.full(3, np.nan), names, uvs, np.full(n, np.nan), outl, ok=False, msg="need >=2 views")
    while True:
        idx = np.where(~outl)[0]
        o_d = [views[i].ray(uvs[i][None]) for i in idx]
        X0 = rays_closest_point([o for o, _ in o_d], [d[0] for _, d in o_d])
        X, _ = _solve([views[i] for i in idx], uvs[idx], X0, loss, f_scale)
        res = np.array([np.linalg.norm(v.project(X[None])[0] - uv) for v, uv in zip(views, uvs)])
        r_in = res[~outl]
        robust = 1.4826 * np.median(r_in) if len(r_in) > 2 else 0.0
        thr = max(outlier_px, 4 * robust)
        worst = idx[np.argmax(res[idx])]
        if res[worst] > thr and len(idx) - 1 >= min_views and len(idx) > 2:
            outl[worst] = True
            continue
        break
    idx = np.where(~outl)[0]
    vin = [views[i] for i in idx]
    depth = np.median([v.project(X[None], return_depth=True)[1][0] for v in vin])
    J = _jac(vin, X, h=max(1e-6, 1e-5 * abs(depth) if np.isfinite(depth) else 1e-3))
    dof = 2 * len(idx) - 3
    post = np.sqrt(np.sum(res[idx] ** 2) / dof) if dof > 0 else 0.0
    s = max(sigma_px, post)
    try:
        cov = s ** 2 * np.linalg.inv(J.T @ J)
    except np.linalg.LinAlgError:
        cov = None
    dirs = np.array([v.ray(uvs[i][None])[1][0] for v, i in zip(vin, idx)])
    ang = np.degrees(np.arccos(np.clip(dirs @ dirs.T, -1, 1))).max() if len(dirs) > 1 else 0.0
    ok = len(idx) >= 2 and np.isfinite(X).all()
    return TriResult(X, names, uvs, res, outl, cov, s, ang, ok)
