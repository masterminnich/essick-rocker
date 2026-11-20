"""Solved cameras in the chair frame.

    cams = Cameras.load()                                  # half-res probe model, metric frame if present
    cams = Cameras.load("work/solve/model", metric="solve/metric_frame.json")   # final model
    uv  = cams.project("IMG_1470.JPG", X)                  # X: (N,3) chair frame -> (N,2) raw pixels
    uvd = cams.project_disp("IMG_1470.JPG", X)             # -> displayed (EXIF-oriented) pixels
    o, d = cams.ray("IMG_1470.JPG", uv)                    # back-projected rays in the chair frame

Pixel conventions: see rocker/__init__.py. Model resolution is detected from camera.width vs the raw
width (4032), so a half-res model (2016 wide) gets image_scale=2 automatically; pass image_scale to force.
COLMAP continuous coords (pixel corner = 0) at model resolution relate to raw index coords by
    x_raw = image_scale * x_colmap - 0.5
Metric frame: X_chair = s * R @ X_colmap + t (identity when the file is missing -> COLMAP units).
"""
import json
from pathlib import Path
import numpy as np

from . import ROOT
from .orientation import RAW_W, RAW_H, raw_to_disp, disp_to_raw, exif_orientation, disp_size

DEFAULT_MODEL = ROOT / "work/solve/model"
DEFAULT_METRIC = ROOT / "solve/metric_frame.json"
DEFAULT_DRIVE = ROOT / "drive"


# ---------------------------------------------------------------- lens models (normalized <-> distorted)
def _distort(model, p, xn):
    """xn: (N,2) normalized undistorted -> (N,2) normalized distorted, for COLMAP model names."""
    x, y = xn[:, 0], xn[:, 1]
    r2 = x * x + y * y
    if model in ("PINHOLE", "SIMPLE_PINHOLE"):
        return xn.copy()
    if model == "SIMPLE_RADIAL":
        k = p[3]; f = 1 + k * r2
        return xn * f[:, None]
    if model == "RADIAL":
        k1, k2 = p[3], p[4]; f = 1 + k1 * r2 + k2 * r2 * r2
        return xn * f[:, None]
    if model in ("OPENCV", "FULL_OPENCV"):
        k1, k2, p1, p2 = p[4:8]
        if model == "FULL_OPENCV":
            k3, k4, k5, k6 = p[8:12]
            f = (1 + k1 * r2 + k2 * r2**2 + k3 * r2**3) / (1 + k4 * r2 + k5 * r2**2 + k6 * r2**3)
        else:
            f = 1 + k1 * r2 + k2 * r2 * r2
        xd = x * f + 2 * p1 * x * y + p2 * (r2 + 2 * x * x)
        yd = y * f + p1 * (r2 + 2 * y * y) + 2 * p2 * x * y
        return np.stack([xd, yd], 1)
    raise NotImplementedError(model)


def _intrinsics(model, p):
    if model in ("SIMPLE_PINHOLE", "SIMPLE_RADIAL", "RADIAL"):
        return p[0], p[0], p[1], p[2]
    return p[0], p[1], p[2], p[3]


def _undistort(model, p, xd, iters=30):
    """Invert _distort by Gauss-Newton with a numeric Jacobian (well-behaved for phone lenses)."""
    xu = xd.copy()
    eps = 1e-7
    for _ in range(iters):
        r = _distort(model, p, xu) - xd
        if np.max(np.abs(r)) < 1e-12:
            break
        jx = (_distort(model, p, xu + [eps, 0]) - _distort(model, p, xu)) / eps
        jy = (_distort(model, p, xu + [0, eps]) - _distort(model, p, xu)) / eps
        a, b, c, d = jx[:, 0], jy[:, 0], jx[:, 1], jy[:, 1]
        det = a * d - b * c
        xu = xu - np.stack([(d * r[:, 0] - b * r[:, 1]) / det, (-c * r[:, 0] + a * r[:, 1]) / det], 1)
    return xu


# ---------------------------------------------------------------- metric frame
class MetricFrame:
    def __init__(self, s=1.0, R=None, t=None, units="colmap", source=None):
        self.s, self.R = float(s), np.eye(3) if R is None else np.asarray(R, float)
        self.t = np.zeros(3) if t is None else np.asarray(t, float)
        self.units, self.source = units, source

    @classmethod
    def load(cls, path):
        if path is None or not Path(path).exists():
            return cls(source=None)
        j = json.loads(Path(path).read_text())
        return cls(j["scale"], j["R"], j["t"], j.get("units", "mm"), str(path))

    def to_chair(self, Xc):
        return self.s * (np.asarray(Xc, float) @ self.R.T) + self.t

    def to_colmap(self, X):
        return ((np.asarray(X, float) - self.t) @ self.R) / self.s


# ---------------------------------------------------------------- cameras
class View:
    """One posed image. All public methods take/return raw pixels and chair-frame points."""

    def __init__(self, name, model, params, Rcw, tcw, scale, metric, orient):
        self.name, self.model, self.params = name, model, np.asarray(params, float)
        self.Rcw, self.tcw, self.scale, self.metric, self.orient = Rcw, tcw, scale, metric, orient
        self.fx, self.fy, self.cx, self.cy = _intrinsics(model, self.params)

    # camera centre / axes in chair frame
    @property
    def center(self):
        return self.metric.to_chair(-self.Rcw.T @ self.tcw)

    @property
    def R_chair(self):
        """Rotation chair -> camera."""
        return self.Rcw @ self.metric.R.T

    def to_cam(self, X):
        Xc = self.metric.to_colmap(np.atleast_2d(X))
        return Xc @ self.Rcw.T + self.tcw

    def project(self, X, return_depth=False):
        """(N,3) chair -> (N,2) raw pixels (index convention). Points behind the camera get NaN."""
        P = self.to_cam(X)
        z = P[:, 2]
        with np.errstate(divide="ignore", invalid="ignore"):
            xn = P[:, :2] / z[:, None]
        xd = _distort(self.model, self.params, xn)
        uv = np.stack([self.fx * xd[:, 0] + self.cx, self.fy * xd[:, 1] + self.cy], 1)
        uv = self.scale * uv - 0.5
        uv[z <= 0] = np.nan
        return (uv, z * self.metric.s) if return_depth else uv

    def project_disp(self, X):
        return raw_to_disp(self.project(X), self.orient)

    def normalized(self, uv_raw):
        """raw pixels -> undistorted normalized image coords (N,2)."""
        uv = (np.atleast_2d(np.asarray(uv_raw, float)) + 0.5) / self.scale
        xd = np.stack([(uv[:, 0] - self.cx) / self.fx, (uv[:, 1] - self.cy) / self.fy], 1)
        return _undistort(self.model, self.params, xd)

    def undistort_pixels(self, uv_raw):
        """raw distorted pixels -> raw pixels of an ideal pinhole camera with the same K (full-res)."""
        xn = self.normalized(uv_raw)
        return np.stack([self.fx * xn[:, 0] + self.cx, self.fy * xn[:, 1] + self.cy], 1) * self.scale - 0.5

    def ray(self, uv_raw):
        """raw pixels -> (origin (3,), unit directions (N,3)) in the chair frame."""
        xn = self.normalized(uv_raw)
        dc = np.c_[xn, np.ones(len(xn))]
        dw = dc @ self.Rcw            # Rcw^T @ d  (colmap frame)
        dch = dw @ self.metric.R.T
        dch /= np.linalg.norm(dch, axis=1, keepdims=True)
        return self.center, dch

    def in_image(self, uv, margin=0):
        uv = np.atleast_2d(uv)
        return (np.isfinite(uv).all(1) & (uv[:, 0] >= -margin) & (uv[:, 1] >= -margin)
                & (uv[:, 0] <= RAW_W - 1 + margin) & (uv[:, 1] <= RAW_H - 1 + margin))

    @property
    def focal_raw(self):
        return 0.5 * (self.fx + self.fy) * self.scale


class Cameras:
    def __init__(self, rec, metric, image_scale=None, drive=DEFAULT_DRIVE, model_dir=None):
        import pycolmap  # noqa
        self.rec, self.metric, self.drive, self.model_dir = rec, metric, Path(drive), model_dir
        self.views = {}
        for im in rec.images.values():
            if not im.has_pose:
                continue
            cam = rec.cameras[im.camera_id]
            sc = image_scale if image_scale else RAW_W / cam.width
            M = im.cam_from_world().matrix()
            p = self.drive / im.name
            orient = exif_orientation(str(p)) if p.exists() else 1
            self.views[im.name] = View(im.name, cam.model.name, cam.params, M[:, :3], M[:, 3], sc, metric, orient)

    @classmethod
    def load(cls, model=DEFAULT_MODEL, metric=DEFAULT_METRIC, image_scale=None, drive=DEFAULT_DRIVE):
        import pycolmap
        rec = pycolmap.Reconstruction(str(model))
        return cls(rec, MetricFrame.load(metric), image_scale, drive, str(model))

    @property
    def units(self):
        return self.metric.units

    def __getitem__(self, name):
        return self.views[self._key(name)]

    def _key(self, name):
        if name in self.views:
            return name
        for cand in (f"IMG_{name}.JPG", f"{name}.JPG", f"{name}"):
            if cand in self.views:
                return cand
        raise KeyError(name)

    def names(self):
        return sorted(self.views)

    def project(self, name, X, **kw):
        return self[name].project(np.atleast_2d(X), **kw)

    def project_disp(self, name, X):
        return self[name].project_disp(np.atleast_2d(X))

    def ray(self, name, uv_raw):
        return self[name].ray(uv_raw)

    def raw_to_disp(self, name, uv):
        return raw_to_disp(uv, self[name].orient)

    def disp_to_raw(self, name, uv):
        return disp_to_raw(uv, self[name].orient)

    def disp_size(self, name):
        return disp_size(self[name].orient)
