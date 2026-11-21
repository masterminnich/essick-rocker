"""USAGE: work/toolkit/rk.sh tools/slat_width/view.py PHOTO OUT.jpg [--slats SLAT_L,SLAT_C,SLAT_R] [--z 800 1000] [--pxmm 10]
         [--widths measurements/slat_widths_v23.npz] [--turn parts/slat_turn.json]
The by-eye check of tools/slat_width/measure.py on ONE photo: each slat resampled straight (horizontal = s, mm across the
slat along measure.py's line n, square to the line of sight; vertical = z, top up) at PXMM px per mm from the single photo,
1 mm per output pixel / PXMM (the photo's own resolution is printed: up-sampling adds no detail).
Drawn: grey ticks every 10 mm; blue = the current model's silhouette edges (parts/slats.json, no turn); orange dots = the
edges measure.py found in this photo (both read on the same line); green (with --turn) = the side slats turned by the design
turn of parts/slat_turn.json (tools/slat_width/turn_fit.py), same width and thickness, seen from this camera."""
import sys, json, argparse
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np, cv2
from rocker.cameras import Cameras
from geo import stations

ap = argparse.ArgumentParser(); ap.add_argument("photo"); ap.add_argument("out")
ap.add_argument("--slats_list", "--slats", default="SLAT_L,SLAT_C,SLAT_R"); ap.add_argument("--z", nargs=2, type=float, default=[800, 1000])
ap.add_argument("--pxmm", type=float, default=10.0); ap.add_argument("--widths", default=None)
ap.add_argument("--slatsfile", default=str(ROOT / "parts/slats.json")); ap.add_argument("--turn", default=None)
ap.add_argument("--margin", type=float, default=12.0)
a = ap.parse_args()
name = a.photo if a.photo.endswith(".JPG") else f"IMG_{a.photo}.JPG"
SL = json.load(open(a.slatsfile)); TH = float(SL["thickness_mm"])
TURN = json.load(open(a.turn))["design"] if a.turn else None
V = Cameras.load()[name]; C = V.center
img = cv2.imread(str(ROOT / "drive" / name), cv2.IMREAD_COLOR | cv2.IMREAD_IGNORE_ORIENTATION)
D = dict(np.load(a.widths)) if a.widths else None
zs = np.arange(a.z[1], a.z[0], -1 / a.pxmm)
panels = []; info = []
for slat in a.slats_list.split(","):
    G = stations(SL, slat, zs)
    wmax = G["w"].max() / 2 + a.margin
    s = np.arange(-wmax, wmax, 1 / a.pxmm)
    rows = np.zeros((len(zs), len(s), 2), np.float32); edges = []; nat = []
    for i in range(len(zs)):
        c, tau, e1, f, w = G["c"][i], G["tau"][i], G["e1"][i], G["f"][i], G["w"][i]
        ray = c - C; ray /= np.linalg.norm(ray); n = np.cross(tau, ray); n /= np.linalg.norm(n)
        if n @ e1 < 0: n = -n
        rows[i] = V.project(c[None, :] + s[:, None] * n[None, :]).astype(np.float32)
        pr = [(sa * w / 2 * e1 + sf * TH / 2 * f) @ n for sa in (-1, 1) for sf in (-1, 1)]
        e2 = None
        if TURN is not None and slat != "SLAT_C":
            th = np.radians(np.interp(c[2], TURN["z_mm"], TURN["turn_deg"])); ew = np.cos(th) * e1 + np.sin(th) * f; et = -np.sin(th) * e1 + np.cos(th) * f
            p2 = [(sa * w / 2 * ew + sf * TH / 2 * et) @ n for sa in (-1, 1) for sf in (-1, 1)]
            e2 = (min(p2), max(p2))
        edges.append((min(pr), max(pr), e2))
        if i % 50 == 0: nat.append(np.linalg.norm(V.project((c + n)[None])[0] - V.project(c[None])[0]))
    P = cv2.remap(img, rows[..., 0], rows[..., 1], cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
    P = np.ascontiguousarray(P)
    toX = lambda v: int(round((v + wmax) * a.pxmm))
    for k in np.arange(np.ceil(-wmax / 10) * 10, wmax, 10):
        cv2.line(P, (toX(k), 0), (toX(k), 12), (160, 160, 160), 1)
    for k, col in ((0, (214, 120, 42)), (1, (214, 120, 42))):     # blue: current model (flat slat)
        cv2.polylines(P, [np.array([[toX(edges[i][k]), i] for i in range(len(zs))], np.int32)], False, col, 2)
    if edges[0][2]:                                                 # green, dashed: the turned design
        for k in (0, 1):
            pts = [[toX(edges[i][2][k]), i] for i in range(len(zs))]
            for j in range(0, len(pts) - 1, 24): cv2.polylines(P, [np.array(pts[j:j + 14], np.int32)], False, (90, 170, 40), 2)
    for zz in np.arange(np.ceil(a.z[0] / 50) * 50, a.z[1], 50):
        y = int(round((a.z[1] - zz) * a.pxmm)); cv2.line(P, (0, y), (14, y), (160, 160, 160), 1)
        cv2.putText(P, f"z{zz:.0f}", (16, y + 5), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (230, 230, 230), 1)
    if D is not None:
        m = (D["photo"] == name) & (D["slat"] == slat)
        for j in np.nonzero(m)[0]:
            y = int(round((a.z[1] - D["z"][j]) * a.pxmm))
            if not 0 <= y < len(zs): continue
            for sv, stv in ((D["s_lo"][j], D["st_lo"][j]), (D["s_hi"][j], D["st_hi"][j])):
                if np.isfinite(sv):
                    cv2.circle(P, (toX(sv), y), 5, (52, 104, 235) if stv == 0 else (120, 120, 120), 2)
    cv2.putText(P, f"{slat} {name} native {np.mean(nat):.1f} px/mm", (16, len(zs) - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (240, 240, 240), 1)
    panels.append(P); info.append((slat, float(np.mean(nat))))
H = max(p.shape[0] for p in panels)
out = np.concatenate([np.pad(p, ((0, H - p.shape[0]), (0, 6), (0, 0)), constant_values=255) for p in panels], 1)
cv2.imwrite(a.out, out, [cv2.IMWRITE_JPEG_QUALITY, 90])
print(a.out, out.shape, info)
