"""Draw chair-frame geometry onto photos through the solved cameras (lens distortion applied).

    scene = Scene()
    scene.add_points(XYZ, labels)                 # (N,3) chair frame
    scene.add_polyline(P, closed=False)           # (N,3); segments are densified so distortion bends them
    scene.add_mesh_edges(V, E)                    # vertices (N,3), edges (M,2) -- or Scene.from_obj(path)
    img = render(cams, "IMG_1470.JPG", scene, max_side=1600)                 # whole photo, display-oriented
    img = render(cams, "IMG_1470.JPG", scene, crop=((x, y), 150, 4))          # crop: centre raw, half-size, zoom
No occlusion handling: hidden geometry is drawn too (the critique loop must decide visibility separately).
"""
import numpy as np
import cv2

from .images import downscaled_display, render_crop
from .orientation import raw_to_disp

COLORS = [(0, 255, 255), (255, 200, 0), (0, 255, 0), (0, 128, 255), (255, 255, 255), (0, 0, 255)]


class Scene:
    def __init__(self):
        self.points, self.labels, self.polylines, self.colors_pl, self.colors_pt = [], [], [], [], []

    def add_points(self, X, labels=None, color=(0, 255, 255)):
        X = np.atleast_2d(np.asarray(X, float))
        self.points += list(X); self.labels += list(labels if labels is not None else [""] * len(X))
        self.colors_pt += [color] * len(X)
        return self

    def add_polyline(self, P, closed=False, color=(255, 200, 0), step=None):
        P = np.asarray(P, float)
        if closed:
            P = np.vstack([P, P[:1]])
        self.polylines.append(densify(P, step)); self.colors_pl.append(color)
        return self

    def add_mesh_edges(self, V, E, color=(0, 255, 0), step=None):
        V = np.asarray(V, float)
        for a, b in E:
            self.add_polyline(V[[a, b]], color=color, step=step)
        return self

    @classmethod
    def from_obj(cls, path, color=(0, 255, 0)):
        V, E = [], set()
        for line in open(path):
            t = line.split()
            if not t:
                continue
            if t[0] == "v":
                V.append([float(v) for v in t[1:4]])
            elif t[0] in ("f", "l"):
                idx = [int(s.split("/")[0]) - 1 for s in t[1:]]
                ring = idx + [idx[0]] if t[0] == "f" else idx
                for a, b in zip(ring[:-1], ring[1:]):
                    E.add((min(a, b), max(a, b)))
        return cls().add_mesh_edges(V, sorted(E), color=color)


def densify(P, step=None, n_min=1):
    """Insert points so no 3D segment is longer than step (default: 1/40 of the polyline's extent)."""
    if len(P) < 2:
        return P
    ext = np.ptp(P, axis=0).max()
    step = step or max(ext / 40, 1e-9)
    out = [P[0]]
    for a, b in zip(P[:-1], P[1:]):
        k = max(n_min, int(np.ceil(np.linalg.norm(b - a) / step)))
        out += list(a + (b - a) * (np.arange(1, k + 1) / k)[:, None])
    return np.array(out)


def project_scene(cams, name, scene):
    v = cams[name]
    pts = v.project(np.array(scene.points)) if scene.points else np.zeros((0, 2))
    pls = [v.project(P) for P in scene.polylines]
    return pts, pls


def render(cams, name, scene, max_side=1600, crop=None, thickness=2, point_radius=6):
    """Return a BGR image (display orientation). crop = (centre_raw, half_raw, zoom) for a zoomed crop."""
    pts, pls = project_scene(cams, name, scene)
    if crop is not None:
        c, half, zoom = crop
        img, _ = render_crop(name, c, half=half, zoom=zoom, crosshair=False,
                             marks=[(p, l, col) for p, l, col in zip(pts, scene.labels, scene.colors_pt) if np.isfinite(p).all()],
                             polylines=list(zip(pls, scene.colors_pl)))
        return img
    o = cams[name].orient
    img, f = downscaled_display(name, max_side)
    SH = 4

    def P(q):
        return (int(round(q[0] * (1 << SH))), int(round(q[1] * (1 << SH))))

    def tf(uv):
        return (raw_to_disp(uv, o) + 0.5) * f - 0.5

    lim = 4 * max(img.shape)
    for pl, col in zip(pls, scene.colors_pl):
        q = tf(pl)
        for a, b in zip(q[:-1], q[1:]):
            if np.isfinite(a).all() and np.isfinite(b).all() and abs(a).max() < lim and abs(b).max() < lim:
                cv2.line(img, P(a), P(b), col, thickness, cv2.LINE_AA, SH)
    for uv, lab, col in zip(pts, scene.labels, scene.colors_pt):
        q = tf(uv[None])[0]
        if not np.isfinite(q).all() or abs(q).max() > lim:
            continue
        cv2.circle(img, P(q), point_radius << SH, (0, 0, 0), thickness + 2, cv2.LINE_AA, SH)
        cv2.circle(img, P(q), point_radius << SH, col, thickness, cv2.LINE_AA, SH)
        if lab:
            org = (int(q[0]) + point_radius + 3, int(q[1]) - point_radius - 2)
            cv2.putText(img, lab, org, cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 3, cv2.LINE_AA)
            cv2.putText(img, lab, org, cv2.FONT_HERSHEY_SIMPLEX, 0.5, col, 1, cv2.LINE_AA)
    return img
