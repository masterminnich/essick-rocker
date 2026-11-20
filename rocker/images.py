"""Image loading (raw sensor orientation) and display-oriented crops with a raw-coordinate grid."""
from functools import lru_cache
from pathlib import Path
import numpy as np
import cv2

from . import ROOT
from .orientation import raw_to_disp, disp_to_raw, to_display_array, exif_orientation, disp_size

DRIVE = ROOT / "drive"


def img_path(name, drive=DRIVE):
    n = name if name.upper().endswith(".JPG") else f"IMG_{name}.JPG" if str(name).isdigit() else name
    return Path(drive) / n


@lru_cache(maxsize=6)
def load_raw(name, drive=str(DRIVE)):
    """BGR uint8 array in raw sensor orientation (EXIF ignored)."""
    p = img_path(name, drive)
    a = cv2.imread(str(p), cv2.IMREAD_COLOR | cv2.IMREAD_IGNORE_ORIENTATION)
    if a is None:
        raise FileNotFoundError(p)
    return a


def orient_of(name, drive=DRIVE):
    return exif_orientation(str(img_path(name, drive)))


def mid_scale(name, mid_dir=ROOT / "work/mid"):
    """disp_fullres = mid_px * factor (mid copies are orientation-corrected, long side 1600)."""
    p = Path(mid_dir) / img_path(name).name
    if p.exists():
        from PIL import Image
        with Image.open(p) as im:
            return 4032.0 / max(im.size)
    return 4032.0 / 1600


def _nice(step):
    for s in (1, 2, 5, 10, 20, 25, 50, 100, 200, 250, 500, 1000):
        if s >= step:
            return s
    return 1000


def to_raw(name, xy, space):
    """Convert a point given in 'raw', 'disp' (full-res displayed) or 'mid' (work/mid viewing copy) to raw."""
    xy = np.asarray(xy, float)
    o = orient_of(name)
    if space == "raw":
        return xy
    if space == "disp":
        return disp_to_raw(xy, o)
    if space == "mid":
        return disp_to_raw((xy + 0.5) * mid_scale(name) - 0.5, o)
    raise ValueError(space)


def render_crop(name, center_raw, half=60, zoom=8, grid=None, interp="cubic", marks=(), polylines=(),
                ellipses=(), crosshair=True, title=None, grid_alpha=0.55):
    """Upright (display-oriented) crop around center_raw, covering +-half raw px, magnified by zoom.
    Grid lines are drawn at constant RAW coordinates and labelled 'x=...' / 'y=...' so values can be read
    straight off the picture without any orientation arithmetic.
      marks:     [(xy_raw, label, (b,g,r))]           drawn as small rings
      polylines: [(Nx2 raw array, (b,g,r))]
      ellipses:  [(xy_raw, 2x2 cov in raw px, (b,g,r))] 1-sigma ellipses
    Returns (bgr image, info dict)."""
    o = orient_of(name)
    raw = load_raw(name)
    disp = to_display_array(raw, o)
    S = int(round(2 * half * zoom))
    c_disp = raw_to_disp(np.asarray(center_raw, float), o)
    # dst index coord o = zoom*(u - uc) + (S-1)/2  ->  src u = (o - (S-1)/2)/zoom + uc
    M = np.array([[zoom, 0, (S - 1) / 2 - zoom * c_disp[0]], [0, zoom, (S - 1) / 2 - zoom * c_disp[1]]])
    flag = {"cubic": cv2.INTER_CUBIC, "nearest": cv2.INTER_NEAREST, "linear": cv2.INTER_LINEAR}[interp]
    out = cv2.warpAffine(np.ascontiguousarray(disp), M, (S, S), flags=flag, borderMode=cv2.BORDER_CONSTANT, borderValue=(40, 40, 40))

    def to_out(xy_raw):
        d = raw_to_disp(np.atleast_2d(np.asarray(xy_raw, float)), o)
        return d * zoom + M[:, 2]

    SH = 4
    def P(p):
        return (int(round(p[0] * (1 << SH))), int(round(p[1] * (1 << SH))))

    base = out.copy()
    grid = grid or _nice(40 / zoom)
    lo = np.asarray(center_raw) - half - grid
    hi = np.asarray(center_raw) + half + grid
    font = cv2.FONT_HERSHEY_SIMPLEX
    for axis, nm in ((0, "x"), (1, "y")):
        start = int(np.ceil(lo[axis] / grid) * grid)
        for k, val in enumerate(range(start, int(hi[axis]) + 1, grid)):
            a = np.array([[0.0, 0.0], [0.0, 0.0]])
            a[:, axis] = val
            a[:, 1 - axis] = [lo[1 - axis], hi[1 - axis]]
            q = to_out(a)
            major = (val % (grid * 5) == 0)
            col = (0, 230, 255) if major else (0, 170, 200)
            cv2.line(out, P(q[0]), P(q[1]), col, 1, cv2.LINE_AA, SH)
            # label where the line enters the frame (left or top edge)
            if major or zoom * grid >= 60:
                vert = abs(q[0][0] - q[1][0]) < abs(q[0][1] - q[1][1])
                pos = (int(q[0][0] + (q[1][0] - q[0][0]) * ((2 - q[0][1]) / (q[1][1] - q[0][1] + 1e-9))) + 3, 18) if vert else \
                      (3, int(q[0][1] + (q[1][1] - q[0][1]) * ((2 - q[0][0]) / (q[1][0] - q[0][0] + 1e-9))) - 3)
                txt = f"{nm}{val}"
                cv2.putText(out, txt, pos, font, 0.55, (0, 0, 0), 4, cv2.LINE_AA)
                cv2.putText(out, txt, pos, font, 0.55, (0, 255, 255) if major else (0, 200, 230), 1, cv2.LINE_AA)
    out = cv2.addWeighted(out, grid_alpha, base, 1 - grid_alpha, 0)   # translucent grid
    for pl, col in polylines:
        q = to_out(pl)
        ok = np.isfinite(q).all(1)
        for a, b, oa, ob in zip(q[:-1], q[1:], ok[:-1], ok[1:]):
            if oa and ob and max(abs(a).max(), abs(b).max()) < 1e5:
                cv2.line(out, P(a), P(b), col, 1, cv2.LINE_AA, SH)
    for xy, cov, col in ellipses:
        c = to_out(xy)[0]
        w, V = np.linalg.eigh(np.asarray(cov, float))
        # rotate covariance into display orientation: direction vectors
        R = np.c_[to_out(np.asarray(xy) + V[:, 0])[0] - c, to_out(np.asarray(xy) + V[:, 1])[0] - c] / zoom
        ang = np.degrees(np.arctan2(R[1, 1], R[0, 1]))
        ax = np.sqrt(np.clip(w, 0, None)) * zoom
        if np.isfinite(c).all() and ax.max() < 5e4:
            cv2.ellipse(out, P(c), (max(1, int(ax[1] * (1 << SH))), max(1, int(ax[0] * (1 << SH)))), ang, 0, 360, col, 1, cv2.LINE_AA, SH)
    for xy, label, col in marks:
        c = to_out(xy)[0]
        if np.isfinite(c).all() and abs(c).max() < 1e5:
            cv2.circle(out, P(c), 7 << SH, col, 1, cv2.LINE_AA, SH)
            cv2.circle(out, P(c), 1 << SH, col, -1, cv2.LINE_AA, SH)
            if label:
                cv2.putText(out, label, (int(c[0]) + 9, int(c[1]) - 9), font, 0.45, (0, 0, 0), 3, cv2.LINE_AA)
                cv2.putText(out, label, (int(c[0]) + 9, int(c[1]) - 9), font, 0.45, col, 1, cv2.LINE_AA)
    if crosshair:
        m = (S - 1) / 2
        for d0, d1 in (((m - 18, m), (m - 5, m)), ((m + 5, m), (m + 18, m)), ((m, m - 18), (m, m - 5)), ((m, m + 5), (m, m + 18))):
            cv2.line(out, P(d0), P(d1), (0, 0, 255), 1, cv2.LINE_AA, SH)
    cx, cy = np.asarray(center_raw, float)
    head = title or f"{img_path(name).name}  centre raw x={cx:.1f} y={cy:.1f}  zoom {zoom}x  grid {grid}px  orient {o}"
    cv2.rectangle(out, (0, S - 20), (S, S), (0, 0, 0), -1)
    cv2.putText(out, head, (4, S - 6), font, 0.42, (255, 255, 255), 1, cv2.LINE_AA)
    return out, dict(orient=o, zoom=zoom, grid=grid, size=S, center_raw=[cx, cy])


def downscaled_display(name, max_side=1600):
    """Display-oriented image scaled so the long side = max_side; returns (img, factor disp->out)."""
    o = orient_of(name)
    disp = to_display_array(load_raw(name), o)
    f = max_side / max(disp.shape[:2])
    out = cv2.resize(np.ascontiguousarray(disp), None, fx=f, fy=f, interpolation=cv2.INTER_AREA)
    return out, f
