"""USAGE: work/toolkit/rk.sh tools/rocker_thickness/view.py RIBDIR OUT.jpg U0 U1 S:PHOTO [S:PHOTO ...]
By-eye check: ribbon panels at 5 px/mm (isotropic), mm grid every 5 mm (10 mm darker), the model's outer (d 0) and inner (d 31)
arris as thin white lines, the traced arrises per column as cyan (outer) / yellow (inner) dots. With parts/rocker_section.json present the
new model's two faces (design d_outer(u) and d_outer(u) + T(u)) are drawn as orange lines: before (white) / after (orange) on one photo."""
import sys, json
import numpy as np, cv2
rib, outp, u0, u1 = sys.argv[1], sys.argv[2], float(sys.argv[3]), float(sys.argv[4]); PX = 5.0
import os
SEC = json.load(open("parts/rocker_section.json"))["design"] if os.path.exists("parts/rocker_section.json") else None
R = json.load(open(f"{rib}/ribbons.json")); g = R["grid"]; T = json.load(open(f"{rib}/trace.json"))
panels = []
for sp in sys.argv[5:]:
    S, ph = sp.split(":"); img = cv2.imread(f"{rib}/{S}_{ph}.png")
    c0, c1 = int((u0 - g["u0"]) / g["du"]), int((u1 - g["u0"]) / g["du"])
    sub = img[:, c0:c1]; W = int((u1 - u0) * PX); H = int((g["d1"] - g["d0"]) * PX)
    big = cv2.resize(sub, (W, H), interpolation=cv2.INTER_CUBIC)
    for d in np.arange(-10, 46, 5):
        y = int((d - g["d0"]) * PX); cv2.line(big, (0, y), (W, y), (60, 60, 60) if d % 10 else (30, 30, 30), 1)
    for u in np.arange(np.ceil(u0 / 5) * 5, u1, 5):
        x = int((u - u0) * PX); cv2.line(big, (x, 0), (x, H), (60, 60, 60) if u % 10 else (30, 30, 30), 1)
    for d in (0, 31): y = int((d - g["d0"]) * PX); cv2.line(big, (0, y), (W, y), (255, 255, 255), 1)
    if SEC:
        uu = np.arange(u0, u1, 0.5); d0 = np.interp(uu, SEC["u"], SEC["d_outer_mm"]); d1 = d0 + np.interp(uu, SEC["u"], SEC["T_mm"])
        for dd in (d0, d1):
            pts = np.c_[(uu - u0) * PX, (dd - g["d0"]) * PX].astype(np.int32); cv2.polylines(big, [pts], False, (52, 104, 235), 2)
    tr = T["sides"][S][ph]
    for key, col in (("d_out", (255, 255, 0)), ("d_in", (0, 255, 255))):
        v = np.array(tr[key], float)[c0:c1]
        for i, d in enumerate(v):
            if np.isfinite(d): cv2.circle(big, (int((i + 0.5) * PX), int((d - g["d0"]) * PX)), 1, col, -1)
    info = R["sides"][S]["photos"][ph]; el = np.array(info["el"])[c0:c1]; pm = np.array(info["px_per_mm_d"])[c0:c1]
    lab = f"{S} IMG_{ph}  u {u0:.0f}..{u1:.0f}  el {np.nanmin(el):.0f}-{np.nanmax(el):.0f} deg  native {np.nanmin(pm):.1f}-{np.nanmax(pm):.1f} px/mm across  cam {'outboard' if info['cam_side'] > 0 else 'inboard'}"
    bar = np.full((24, W, 3), 255, np.uint8); cv2.putText(bar, lab, (4, 17), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
    panels.append(np.vstack([bar, big]))
cv2.imwrite(outp, np.vstack(panels), [cv2.IMWRITE_JPEG_QUALITY, 90])
