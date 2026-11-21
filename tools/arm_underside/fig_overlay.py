"""USAGE: work/toolkit/rk.sh tools/arm_underside/fig_overlay.py SIDE(L|R) PHOTO OUT.jpg YA:YB [YA:YB ...]   env PXMM (10), INNER=1 (draw the inner bottom arris too),
DROPS=FILE.json (from tools/arm_underside/glb_drops.py: draw the drops read off two BUILT models instead of the design; LABELS="old|new" names them)
Before/after overlay of the arm's underside on ONE real photo: crops of the photo around stations YA..YB of one arm, enlarged to PXMM pixels per mm
at the arm, with the model's lines projected into it: the outer top arris (white), the bottom arris of the OLD model (orange: the assumed 25 mm
square to the top) and of the NEW one (blue: parts/arm_underside.json design). Lines hang from THIS arm's own outer top arris
(parts/arms.json left/right) lowered by this photo's own top-arris trace offset (tools/arm_underside/inputs/traces_*.json "top@PHOTO", a
straight line in y, as solve.py registers every photo), so each figure shows the drops exactly as they were measured: from the top line the
photo sees. Drops: old = 25 / cos(top slope); new = parts/arm_underside.json design (left/right mean). One panel per window, stacked."""
import sys, json, os, numpy as np, cv2
sys.path.insert(0, ".")
from rocker.cameras import Cameras
from PIL import Image, ImageOps
side, n, out = sys.argv[1:4]; wins = [tuple(float(v) for v in w.split(":")) for w in sys.argv[4:]]; PX = float(os.environ.get("PXMM", 10)); INNER = os.environ.get("INNER") == "1"
GD = json.load(open(os.environ["DROPS"])) if os.environ.get("DROPS") else None; LB = os.environ.get("LABELS", "old model (25 mm assumed)|new (traced)").split("|")
sg = 1.0 if side == "R" else -1.0; c = Cameras.load(); name = f"IMG_{n}.JPG"
D = json.load(open("parts/arms.json"))["design"]; U = json.load(open("parts/arm_underside.json"))["design"]
pin, pout, pz, pzx = (np.array(D[k][q]) for k, q in (("inner_x_of_y", "poly_in_(y-300)"), ("outer_x_of_y", "poly_in_(y-300)"), ("top_z_of_y", "poly_in_(y-300)"), ("top_z_of_y", "cross_slope_outer_minus_inner_poly")))
v = lambda p, y: np.polyval(p, y - 300)
A = json.load(open("parts/arms.json"))[{"L": "left", "R": "right"}[side]]
O = np.array(A["outer_top_arris_xyz"]); O = O[np.argsort(O[:, 1])]; I_ = np.array(A["inner_top_arris_xyz"]); I_ = I_[np.argsort(I_[:, 1])]
TR = {}
for f in ("above", "below"): TR.update(json.load(open(f"tools/arm_underside/inputs/traces_{f}_{side}.json")))
tt = np.array(TR[f"top@{n}"]["yd"]); tt = tt[(tt[:, 0] >= 60) & (tt[:, 0] <= 480)]; reg = np.polyfit(tt[:, 0], tt[:, 1], 1)     # this photo's top arris, d below parts/arms.json
def ext(y, P, i):
    out = np.interp(y, P[:, 1], P[:, i])
    for lo in (True, False):
        m = (y < P[0, 1]) if lo else (y > P[-1, 1]); sel = (P[:, 1] < P[0, 1] + 40) if lo else (P[:, 1] > P[-1, 1] - 40)
        if m.any(): out[m] = np.polyval(np.polyfit(P[sel, 1], P[sel, i], 1), y[m])
    return out
def line(y, which):
    y = np.atleast_1d(np.asarray(y, float)); zo = ext(y, O, 2) - np.polyval(reg, y); zi = zo - v(pzx, y); old = 25.0 / np.cos(np.arctan(v(np.polyder(pz), y)))
    xo, xi = ext(y, O, 0), ext(y, I_, 0)
    x, z = {"top": (xo, zo), "top_in": (xi, zi), "old": (xo, zo - old), "new": (xo, zo - np.interp(y, U["y"], U["h_outer_mm"])),
            "old_in": (xi, zi - old), "new_in": (xi, zo - np.interp(y, U["y"], U["h_inner_mm"]))}[which]
    if GD and which in ("old", "new", "old_in", "new_in"):   # drops read off the built model (below the outer top arris, both faces)
        t_, f_ = which.split("_")[0], "inner" if which.endswith("_in") else "outer"
        x, z = (xi if f_ == "inner" else xo), zo - np.interp(y, GD["y"], np.nan_to_num(np.array(GD[side][f"{t_}_{f_}"], float), nan=np.nanmean(GD[side][f"{t_}_{f_}"][-6:])))
    return np.c_[x, y, z]
im = np.array(ImageOps.exif_transpose(Image.open(f"drive/{name}")).convert("RGB"))[:, :, ::-1]
BLUE, ORANGE, WHITE, INK = (214, 120, 42), (52, 104, 235), (250, 250, 250), (11, 11, 11)
panels = []
for ya, yb in wins:
    ys = np.arange(ya, yb + 0.1, 1.0); L = {k: c.project_disp(name, line(ys, k)) for k in ("top", "old", "new", "old_in", "new_in", "top_in")}
    keys = ("top", "old", "new") + (("old_in", "new_in") if INNER else ())
    allp = np.vstack([L[k] for k in keys]); ym = (ya + yb) / 2
    pxmm = np.linalg.norm(c.project_disp(name, line([ym], "top") - [0, 0, 10.0])[0] - c.project_disp(name, line([ym], "top"))[0]) / 10.0
    sc = PX / pxmm; pad = 12 * pxmm
    x0, y0 = np.maximum((allp.min(0) - pad).astype(int), 0); x1, y1 = (allp.max(0) + pad).astype(int); x1, y1 = min(x1, im.shape[1]), min(y1, im.shape[0])
    cr = cv2.resize(im[y0:y1, x0:x1], (int((x1 - x0) * sc), int((y1 - y0) * sc)), interpolation=cv2.INTER_CUBIC)
    P = lambda k: np.round((L[k] - [x0, y0]) * sc).astype(np.int32)
    for k in keys:
        col = WHITE if k == "top" else ORANGE if k.startswith("old") else BLUE
        pts = P(k)
        if k.endswith("_in"):          # dashed: the inner arris (behind the underside, seen from below)
            for i in range(0, len(pts) - 1, 6): cv2.polylines(cr, [pts[i:i + 4]], False, col, 3, cv2.LINE_AA)
        else: cv2.polylines(cr, [pts], False, col, 3, cv2.LINE_AA)
    for yt in range(int(np.ceil(ya / 50) * 50), int(yb) + 1, 50):            # station ticks on the top line
        p = np.round((c.project_disp(name, line([yt], "top"))[0] - [x0, y0]) * sc).astype(int)
        cv2.circle(cr, tuple(p), 6, WHITE, -1, cv2.LINE_AA); cv2.putText(cr, f"y {yt}", (p[0] + 8, p[1] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, WHITE, 2, cv2.LINE_AA)
    panels.append(cr); print(f"window y {ya:.0f}-{yb:.0f}: {pxmm:.2f} px/mm in the photo, shown at {PX:.0f} px/mm, crop {x1 - x0}x{y1 - y0} px")
H = 70
txt = [("IMG_" + n + (" right" if side == "R" else " left") + " arm", INK), ("top arris (as this photo sees it)", (140, 140, 140)), (LB[0], ORANGE), (LB[1], BLUE)] + ([("dashed = inner bottom arris", INK)] if INNER else [])
tw = 16 + sum(cv2.getTextSize(t, cv2.FONT_HERSHEY_SIMPLEX, 0.95, 2)[0][0] + 36 + (50 if col in (ORANGE, BLUE) or t.startswith("top") else 0) for t, col in txt)
W = max(max(p.shape[1] for p in panels), tw); head = np.full((H, W, 3), (251, 252, 252), np.uint8)
x = 16
for t, col in txt:
    if col in (ORANGE, BLUE) or t.startswith("top"): cv2.line(head, (x, 38), (x + 40, 38), col, 5, cv2.LINE_AA); x += 50
    cv2.putText(head, t, (x, 47), cv2.FONT_HERSHEY_SIMPLEX, 0.95, col if col != (140, 140, 140) else INK, 2, cv2.LINE_AA); x += cv2.getTextSize(t, cv2.FONT_HERSHEY_SIMPLEX, 0.95, 2)[0][0] + 36
rows = [head] + [np.pad(p, ((8, 0), (0, W - p.shape[1]), (0, 0)), constant_values=252) for p in panels]
cv2.imwrite(out, np.vstack(rows), [cv2.IMWRITE_JPEG_QUALITY, 88]); print(out)
