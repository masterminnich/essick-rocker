"""The two side frames (rocker + front leg + back leg share one outer plane per side). Symmetric design-intent plane."""
import json
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parent.parent


def side_plane(sign, planes=("work/parts/rockerL/o_plane.json", "work/parts/rockerR/o_plane.json")):
    """sign=+1 right, -1 left. Returns origin, u (forward-ish, horizontal), v (up-ish), n (outward)."""
    jl, jr = (json.load(open(ROOT / p)) for p in planes)
    nl, nr = np.array(jl["n"]), np.array(jr["n"])
    n = (nr + nl * [-1, 1, 1]) / 2; n /= np.linalg.norm(n)
    x0 = (jr["origin"][0] - jl["origin"][0]) / 2
    n = n * [sign, 1, 1]; o = np.array([sign * x0, 0, 0.0])
    u = np.cross([0, 0, 1.0], n); u /= np.linalg.norm(u)
    if u[1] < 0: u = -u
    v = np.cross(n, u)
    if v[2] < 0: v = -v
    return o, u, v, n


def to_plane(X, sign):
    o, u, v, n = side_plane(sign); d = np.atleast_2d(X) - o
    return np.stack([d @ u, d @ v, -(d @ n)], 1)        # u, v, depth inward from the outer face


def from_plane(uvd, sign):
    o, u, v, n = side_plane(sign); uvd = np.atleast_2d(uvd)
    return o + uvd[:, :1] * u + uvd[:, 1:2] * v - uvd[:, 2:3] * n
