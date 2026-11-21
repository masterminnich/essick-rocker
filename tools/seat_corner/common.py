"""Shared helpers for tools/seat_corner/ (the 3 mm question at the seat's front corners)."""
import numpy as np, trimesh
from scipy.spatial import cKDTree


def seat_top_z_fn(glb, part="SEAT"):
    """z of the model's seat top straight above (x, y): the highest up-facing triangle containing the point (no rtree needed)."""
    m = trimesh.load(glb).geometry[part]
    F = np.asarray(m.faces)[np.asarray(m.face_normals)[:, 2] > 0.15]; V = np.asarray(m.vertices); T = V[F]
    tree = cKDTree(T[:, :, :2].mean(1))

    def top_z(xy, k=16):
        xy = np.atleast_2d(np.asarray(xy, float)); _, idx = tree.query(xy, k=k); z = np.full(len(xy), np.nan)
        for j in range(k):
            t = T[idx[:, j]]; a, b, c = t[:, 0, :2], t[:, 1, :2], t[:, 2, :2]
            v0, v1, v2 = b - a, c - a, xy - a; den = v0[:, 0] * v1[:, 1] - v1[:, 0] * v0[:, 1]
            with np.errstate(divide="ignore", invalid="ignore"):
                s = (v2[:, 0] * v1[:, 1] - v1[:, 0] * v2[:, 1]) / den; r = (v0[:, 0] * v2[:, 1] - v2[:, 0] * v0[:, 1]) / den
            inside = (s >= -1e-9) & (r >= -1e-9) & (s + r <= 1 + 1e-9) & (np.abs(den) > 1e-12)
            zz = t[:, 0, 2] + s * (t[:, 1, 2] - t[:, 0, 2]) + r * (t[:, 2, 2] - t[:, 0, 2])
            upd = inside & (np.isnan(z) | (zz > z)); z[upd] = zz[upd]
        return z
    return top_z
