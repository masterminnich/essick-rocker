"""Orthophotos: resample a photo onto a plane in 3D, so that things lying in that plane appear at true shape.

    plane = Plane(origin, u, v)                 # origin (3,), unit axes u, v spanning the plane (frame of cams)
    img = ortho(cams, "IMG_1544.JPG", plane, (umin, umax), (vmin, vmax), res)   # res = plane units per pixel
Pixel (col, row) of the result is the plane point origin + (umin + col*res)*u + (vmax - row*res)*v  (v up).
Memory: processes the output in row chunks; the source photo (36 MB decoded) is loaded once.
"""
from dataclasses import dataclass
import numpy as np
import cv2
from PIL import Image


@dataclass
class Plane:
    origin: np.ndarray
    u: np.ndarray
    v: np.ndarray

    def __post_init__(self):
        self.origin = np.asarray(self.origin, float)
        self.u = np.asarray(self.u, float) / np.linalg.norm(self.u)
        v = np.asarray(self.v, float)
        v = v - self.u * (v @ self.u)
        self.v = v / np.linalg.norm(v)

    @property
    def n(self):
        return np.cross(self.u, self.v)

    def to3d(self, uv):
        uv = np.atleast_2d(uv)
        return self.origin + uv[:, :1] * self.u + uv[:, 1:2] * self.v

    def to2d(self, X):
        d = np.atleast_2d(X) - self.origin
        return np.stack([d @ self.u, d @ self.v], 1)

    def dist(self, X):
        return (np.atleast_2d(X) - self.origin) @ self.n

    def intersect(self, o, d):
        """ray origin o (3,), directions d (N,3) -> plane coords (N,2)"""
        t = ((self.origin - o) @ self.n) / (d @ self.n)
        return self.to2d(o + t[:, None] * d)


def load_raw(cams, name):
    """Raw sensor pixel array (no EXIF rotation), BGR."""
    p = cams.drive / cams._key(name)
    return cv2.cvtColor(np.asarray(Image.open(p).convert("RGB")), cv2.COLOR_RGB2BGR)


def ortho(cams, name, plane, urange, vrange, res, raw=None, chunk=400):
    view = cams[name]
    raw = load_raw(cams, name) if raw is None else raw
    us = np.arange(urange[0], urange[1], res)
    vs = np.arange(vrange[1], vrange[0], -res)
    out = np.zeros((len(vs), len(us), 3), np.uint8)
    for r0 in range(0, len(vs), chunk):
        vv = vs[r0:r0 + chunk]
        U, V = np.meshgrid(us, vv)
        X = plane.to3d(np.stack([U.ravel(), V.ravel()], 1))
        uv = view.project(X).astype(np.float32)
        mx = uv[:, 0].reshape(U.shape); my = uv[:, 1].reshape(U.shape)
        mx = np.nan_to_num(mx, nan=-10); my = np.nan_to_num(my, nan=-10)
        out[r0:r0 + chunk] = cv2.remap(raw, mx, my, cv2.INTER_LINEAR, borderValue=(0, 0, 0))
    return out


def pix_to_plane(urange, vrange, res, cr):
    cr = np.atleast_2d(cr).astype(float)
    return np.stack([urange[0] + cr[:, 0] * res, vrange[1] - cr[:, 1] * res], 1)


def plane_to_pix(urange, vrange, res, uv):
    uv = np.atleast_2d(uv).astype(float)
    return np.stack([(uv[:, 0] - urange[0]) / res, (vrange[1] - uv[:, 1]) / res], 1)
