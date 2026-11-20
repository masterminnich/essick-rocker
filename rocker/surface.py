"""The surface an orthophoto was rectified onto, rebuilt from its PREFIX_plane.json: a flat face (tools/face_ortho.py) or an
"unrolled" sheet (tools/sheet_ortho.py). Gives 3D points and the local frame so sheet coordinates map to the chair frame.

    S = load_surface("work/parts/back/b_plane.json")
    X = S.to3d(uv, d)            # (N,3) chair-frame points; d = distance off the surface along n (towards the viewers)
    eu, ev, n = S.frame(uv)      # unit vectors per point: along u, along v, normal towards the side the photos look from
"""
import json
import numpy as np


class FlatSurface:
    def __init__(self, pj):
        self.o, self.u, self.v, self.n = (np.array(pj[k], float) for k in ("origin", "u", "v", "n"))

    def frame(self, uv):
        k = len(np.atleast_2d(uv)); return np.tile(self.u, (k, 1)), np.tile(self.v, (k, 1)), np.tile(self.n, (k, 1))

    def to3d(self, uv, d=0.0):
        uv = np.atleast_2d(uv); return self.o + uv[:, :1] * self.u + uv[:, 1:2] * self.v + np.reshape(d, (-1, 1)) * self.n


class SheetSurface:
    def __init__(self, pj):
        if "table" in pj: tb = np.array(pj["table"]); zt = np.linspace(tb[0, 0], tb[-1, 0], 4000); yt = np.interp(zt, tb[:, 0], tb[:, 1])
        else: zt = np.linspace(pj["z"][0], pj["z"][1], 4000); yt = np.polyval(np.array(pj["coef"]), zt)
        self.zt, self.yt = zt, yt; self.dy = np.gradient(yt, zt); self.st = np.r_[0, np.cumsum(np.hypot(np.diff(zt), np.diff(yt)))]
        self.offset = float(pj.get("offset", 0)); self.sgn = 1.0 if pj.get("side", "back") == "back" else -1.0

    def _at(self, v):
        z = np.interp(v, self.st, self.zt); y = np.interp(v, self.st, self.yt); d = np.interp(v, self.st, self.dy); return z, y, d, np.hypot(1, d)

    def frame(self, uv):
        uv = np.atleast_2d(uv); z, y, d, nr = self._at(uv[:, 1]); k = len(uv)
        nb = np.c_[np.zeros(k), -1 / nr, d / nr]                      # normal towards the back of the chair
        return np.tile([1.0, 0, 0], (k, 1)), np.c_[np.zeros(k), d / nr, 1 / nr], nb * self.sgn

    def to3d(self, uv, d=0.0):
        uv = np.atleast_2d(uv); z, y, dd, nr = self._at(uv[:, 1]); nb = np.c_[np.zeros(len(uv)), -1 / nr, dd / nr]
        return np.c_[uv[:, 0], y, z] + nb * (self.offset + self.sgn * np.reshape(d, (-1, 1)))


def load_surface(plane_json):
    pj = json.load(open(plane_json)) if not isinstance(plane_json, dict) else plane_json
    return SheetSurface(pj) if pj.get("kind") == "sheet" else FlatSurface(pj)
