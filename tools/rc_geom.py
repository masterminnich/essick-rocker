"""Shared geometry helpers for the rocking-chair camera solve (imported by other tools; not a CLI).

Conventions
- Pixel coordinates follow COLMAP: continuous coordinates on the RAW sensor grid (4032x3024, EXIF orientation NOT
  applied); the centre of the top-left pixel is (0.5, 0.5). numpy index (row i, col j) has centre (j+0.5, i+0.5).
- Camera model OPENCV: fx, fy, cx, cy, k1, k2, p1, p2.
- A model solved on a downscaled copy is promoted to full resolution by multiplying fx, fy, cx, cy by
  full_width / model_width (exact for COLMAP's continuous pixel convention).
"""
import json, pathlib
import numpy as np

FULL_W, FULL_H = 4032, 3024


class Cam:
    """One registered image: OPENCV intrinsics at full resolution + world->camera pose (COLMAP world units)."""

    def __init__(self, name, params, R, t, width=FULL_W, height=FULL_H, image_id=None, camera_id=None):
        self.name, self.image_id, self.camera_id = name, image_id, camera_id
        self.p = np.asarray(params, float)
        self.R, self.t = np.asarray(R, float), np.asarray(t, float)
        self.w, self.h = width, height

    @property
    def center(self):
        return -self.R.T @ self.t

    def to_cam(self, X):
        return (np.atleast_2d(X) @ self.R.T) + self.t

    def distort(self, xn):
        fx, fy, cx, cy, k1, k2, p1, p2 = self.p
        x, y = xn[:, 0], xn[:, 1]
        r2 = x * x + y * y
        rad = 1 + k1 * r2 + k2 * r2 * r2
        dx = 2 * p1 * x * y + p2 * (r2 + 2 * x * x)
        dy = p1 * (r2 + 2 * y * y) + 2 * p2 * x * y
        return np.c_[fx * (x * rad + dx) + cx, fy * (y * rad + dy) + cy]

    def project(self, X):
        """World points (N,3) -> pixels (N,2) and depth (N,)."""
        Xc = self.to_cam(X)
        z = Xc[:, 2]
        return self.distort(Xc[:, :2] / z[:, None]), z

    def undistort(self, uv, iters=30):
        """Pixels (N,2) -> normalized pinhole coordinates (N,2) by fixed-point inversion."""
        fx, fy, cx, cy = self.p[:4]
        uv = np.atleast_2d(np.asarray(uv, float))
        xd = np.c_[(uv[:, 0] - cx) / fx, (uv[:, 1] - cy) / fy]
        x = xd.copy()
        for _ in range(iters):
            d = self.distort(x)
            dn = np.c_[(d[:, 0] - cx) / fx, (d[:, 1] - cy) / fy]
            x = x + (xd - dn)
        return x

    def ray(self, uv):
        """Pixels -> (centre, unit world directions)."""
        xn = self.undistort(uv)
        d = np.c_[xn, np.ones(len(xn))] @ self.R  # R^T applied to camera rays
        return self.center, d / np.linalg.norm(d, axis=1, keepdims=True)


def load_model(path):
    """Load a COLMAP model (pycolmap) and return (reconstruction, {name: Cam}) promoted to full resolution."""
    import pycolmap
    m = pycolmap.Reconstruction(str(path))
    cams = {}
    for im in m.images.values():
        if not im.has_pose:
            continue
        c = im.camera
        s = FULL_W / c.width
        p = np.array(c.params, float).copy()
        assert c.model_name == "OPENCV", c.model_name
        p[:4] *= s
        T = im.cam_from_world().matrix()
        cams[im.name] = Cam(im.name, p, T[:, :3], T[:, 3], image_id=im.image_id, camera_id=im.camera_id)
    return m, cams


def triangulate(obs, cams, iters=10):
    """Multi-view triangulation. obs: list of (name, (u,v)) in full-res pixels.
    Linear (midpoint/DLT on normalized coords) then Gauss-Newton on reprojection error.
    Returns X (3,), per-view residual vectors (N,2) in pixels."""
    A = []
    for n, uv in obs:
        c = cams[n]
        xn = c.undistort(np.array([uv]))[0]
        P = np.c_[c.R, c.t]
        A.append(xn[0] * P[2] - P[0])
        A.append(xn[1] * P[2] - P[1])
    _, _, vt = np.linalg.svd(np.array(A))
    X = vt[-1, :3] / vt[-1, 3]
    for _ in range(iters):
        r, J = [], []
        for n, uv in obs:
            c = cams[n]
            p0, _ = c.project(X[None])
            r.append(p0[0] - uv)
            Jn = np.zeros((2, 3))
            for k in range(3):
                dX = np.zeros(3); dX[k] = 1e-6 * max(1.0, np.abs(X).max())
                Jn[:, k] = (c.project((X + dX)[None])[0][0] - p0[0]) / dX[k]
            J.append(Jn)
        r, J = np.concatenate(r), np.vstack(J)
        dx = np.linalg.lstsq(J, -r, rcond=None)[0]
        X = X + dx
        if np.linalg.norm(dx) < 1e-12:
            break
    res = np.array([cams[n].project(X[None])[0][0] - np.asarray(uv) for n, uv in obs])
    return X, res


def raw_to_display(uv, orientation, w=FULL_W, h=FULL_H):
    """Map raw-sensor continuous pixel coords to EXIF-display coords (what a viewer shows)."""
    uv = np.atleast_2d(np.asarray(uv, float))
    x, y = uv[:, 0], uv[:, 1]
    if orientation in (None, 1):
        return np.c_[x, y]
    if orientation == 3:
        return np.c_[w - x, h - y]
    if orientation == 6:  # displayed = raw rotated 90 deg clockwise
        return np.c_[h - y, x]
    if orientation == 8:  # displayed = raw rotated 90 deg counter-clockwise
        return np.c_[y, w - x]
    raise ValueError(orientation)


def display_to_raw(uv, orientation, w=FULL_W, h=FULL_H):
    uv = np.atleast_2d(np.asarray(uv, float))
    X, Y = uv[:, 0], uv[:, 1]
    if orientation in (None, 1):
        return np.c_[X, Y]
    if orientation == 3:
        return np.c_[w - X, h - Y]
    if orientation == 6:
        return np.c_[Y, h - X]
    if orientation == 8:
        return np.c_[w - Y, X]
    raise ValueError(orientation)


def exif_orientation(path):
    from PIL import Image
    return Image.open(path).getexif().get(274, 1)


def load_raw(path):
    """Load an original JPEG as an RGB float array on the RAW sensor grid (no EXIF rotation)."""
    from PIL import Image
    im = Image.open(path)
    im.load()
    return np.asarray(im.convert("RGB"), dtype=np.float32)


def fit_plane(P, w=None):
    P = np.asarray(P, float)
    w = np.ones(len(P)) if w is None else np.asarray(w, float)
    c = (P * w[:, None]).sum(0) / w.sum()
    _, s, vt = np.linalg.svd((P - c) * np.sqrt(w)[:, None])
    return c, vt[2], vt


def save_json(path, obj):
    pathlib.Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(obj, f, indent=1, default=lambda o: o.tolist() if hasattr(o, "tolist") else str(o))
