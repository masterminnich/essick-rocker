"""USAGE: tools/py.sh templates/check_arm_overlay.py --geom templates/out/arms_geom.json --out figures/templates/arms_overlay.jpg
    [--top ../rocking-chair-crest/work/parts/top] [--strips ../rocking-chair/work/armu/strip] [--plan R:1544,R:1549,L:1544,L:1538]
    [--side R:1469,R:1477,L:1504,L:1516]
Check the arm templates against rectified photos (read only, from the crest and hub work trees):
  PLAN: the template's top outline (design top arrises, 3D) drawn on the overhead sheets of each arm (tools/face_ortho.py,
        <top>/a{R,L}_<photo>.png, 0.4 mm/px; plane in <top>/a{R,L}_plane.json): each 3D point goes where that photo's camera ray
        through it meets the sheet plane (rocker.cameras), so points off the plane land where the photo shows them (the left
        sheet's plane sits ~15 mm above the arm top at the front).
  SIDE: the template's top line and outer bottom arris drawn on the unrolled outer-face strips of tools/arm_underside/strip.py
        (<strips>/{R,L}_<photo>.npy: column = chair y 50..520 at 1 mm, row = drop d below that arm's own traced outer top arris,
        -20..90 at 0.25 mm), resampled to 2 px/mm both ways.
The design is the mirrored L/R mean; each arm is drawn moved rigidly by its own mean offset from the design (parts/arms.json
stations, y >= 180: dx; outer top arris: dz), so the check is of SHAPE; the offsets are printed and written on the panels.
Green = outline / top, cyan = outer bottom arris, magenta = stations (plan) / front-leg faces' y range (side). Tiny compute."""
import json, argparse, sys, numpy as np
from PIL import Image, ImageDraw
sys.path.insert(0, ".")
from rocker.cameras import Cameras
ap = argparse.ArgumentParser(); ap.add_argument("--geom", required=True); ap.add_argument("--out", required=True)
ap.add_argument("--top", default="../rocking-chair-crest/work/parts/top"); ap.add_argument("--strips", default="../rocking-chair/work/armu/strip")
ap.add_argument("--plan", default="R:1544,R:1549,L:1544,L:1538"); ap.add_argument("--side", default="R:1469,R:1477,L:1504,L:1516")
a = ap.parse_args()
G = json.load(open(a.geom)); AJ = json.load(open("parts/arms.json")); D = AJ["design"]; UJ = json.load(open("parts/arm_underside.json"))["design"]
pin, pout = np.array(D["inner_x_of_y"]["poly_in_(y-300)"]), np.array(D["outer_x_of_y"]["poly_in_(y-300)"])
pz, pzx = np.array(D["top_z_of_y"]["poly_in_(y-300)"]), np.array(D["top_z_of_y"]["cross_slope_outer_minus_inner_poly"])
ztop_o = lambda y: np.polyval(pz, np.asarray(y, float) - 300) + 0.5 * np.polyval(pzx, np.asarray(y, float) - 300)
h_o = lambda y: np.interp(y, UJ["y"], UJ["h_outer_mm"])
off = {}
for S, key in (("R", "right"), ("L", "left")):
    sg = 1 if S == "R" else -1; st = [s for s in AJ[key]["stations"] if s["y"] >= 180]
    dx = np.mean([(s["x_inner"] * sg - np.polyval(pin, s["y"] - 300) + s["x_outer"] * sg - np.polyval(pout, s["y"] - 300)) / 2 for s in st]) * sg
    O = np.array(AJ[key]["outer_top_arris_xyz"]); O = O[np.argsort(O[:, 1])]; m = (O[:, 1] > 80) & (O[:, 1] < 480)
    dz = float(np.mean(O[m, 2] - ztop_o(O[m, 1]))); off[S] = (float(dx), dz, O)
    print(f"{S}: rigid offset from the design dx {dx:+.1f} mm, dz {dz:+.1f} mm")
T3 = np.array(G["top_outline_3d_right"]); CAM = Cameras.load()
def on_sheet(X, ph, O_, n_):
    """sheet-plane point where the camera ray of photo ph through 3D point(s) X meets the plane (O_, n_)"""
    C = np.asarray(CAM[f"IMG_{ph}.JPG"].center, float); X = np.atleast_2d(X); t = ((O_ - C) @ n_) / ((X - C) @ n_)
    return C + t[:, None] * (X - C)
rows = []
def label(im, s): d = ImageDraw.Draw(im); d.rectangle((0, 0, 7 * len(s) + 6, 13), fill=(0, 0, 0)); d.text((3, 1), s, fill=(255, 255, 0))
# ---------------- plan panels ----------------
for spec in a.plan.split(","):
    S, ph = spec.split(":"); sg = 1 if S == "R" else -1; dx, dz, _ = off[S]
    pl = json.load(open(f"{a.top}/a{S}_plane.json")); O_, eu, ev, n_ = (np.array(pl[k]) for k in ("origin", "u", "v", "n")); res, ur, vr = pl["res"], pl["urange"], pl["vrange"]
    P = T3 * [sg, 1, 1] + [dx, 0, dz]; Q = on_sheet(P, ph, O_, n_) - O_; u, v = Q @ eu, Q @ ev
    pxy = np.stack([(u - ur[0]) / res, (vr[1] - v) / res], 1)
    im = Image.open(f"{a.top}/a{S}_{ph}.png").convert("RGB"); d = ImageDraw.Draw(im)
    d.line([tuple(p) for p in np.vstack([pxy, pxy[:1]])], fill=(0, 255, 60), width=1)
    for y in G["stations_y"]:
        for xx in (np.polyval(pin, y - 300), np.polyval(pout, y - 300)):
            q = on_sheet(np.array([[sg * xx + dx - 4 * sg, y, ztop_o(y) + dz], [sg * xx + dx + 4 * sg, y, ztop_o(y) + dz]]), ph, O_, n_) - O_
            d.line([((q[i] @ eu - ur[0]) / res, (vr[1] - q[i] @ ev) / res) for i in (0, 1)], fill=(255, 40, 200), width=1)
    W, H = im.size; full = im.resize((W // 2, H // 2)); full = full.rotate(-90, expand=True)        # front to the right
    panels = [full]
    for nm, y0, y1 in (("back end", 40, 150), ("middle", 250, 360), ("front end", 430, 520)):
        c3 = np.array([[sg * np.polyval(pin, y - 300) + dx, y, ztop_o(y) + dz] for y in (y0, y1)] + [[sg * np.polyval(pout, y - 300) + dx, y, ztop_o(y) + dz] for y in (y0, y1)]); c3 = on_sheet(c3, ph, O_, n_) - O_
        cu, cv = c3 @ eu, c3 @ ev; x0, x1 = int((cu.min() - ur[0]) / res) - 25, int((cu.max() - ur[0]) / res) + 25
        r0, r1 = int((vr[1] - cv.max()) / res), int((vr[1] - cv.min()) / res)
        c = im.crop((max(0, x0), max(0, r0), min(W, x1), min(H, r1))); c = c.resize((c.size[0] * 2, c.size[1] * 2), Image.NEAREST)
        label(c, f"{S} IMG_{ph} plan {nm}"); panels.append(c)
    label(panels[0], f"{S} IMG_{ph} sheet (dx {dx:+.1f})")
    hh = max(p.size[1] for p in panels); row = Image.new("RGB", (sum(p.size[0] + 6 for p in panels), hh), "black"); x = 0
    for p in panels: row.paste(p, (x, 0)); x += p.size[0] + 6
    rows.append(row)
# ---------------- side panels ----------------
Y0, D0, DD = 50, -20.0, 0.25
yy = np.arange(50, 521, 1.0)
for spec in a.side.split(","):
    S, ph = spec.split(":"); dx, dz, O = off[S]
    A = np.load(f"{a.strips}/{S}_{ph}.npy"); V = (255 * np.clip(A / 255.0, 0, 1) ** 0.5).astype(np.uint8)[:, :, ::-1]
    im = Image.fromarray(V).resize((A.shape[1] * 2, int(A.shape[0] * DD * 2)), Image.BICUBIC); d = ImageDraw.Draw(im)
    # the strip's own top arris (as tools/arm_underside/strip.py: straight on beyond the traced range)
    def ztr(y):
        z = np.interp(y, O[:, 1], O[:, 2]); lo = y < O[0, 1]; hi = y > O[-1, 1]
        for msk, sel in ((lo, O[:, 1] < O[0, 1] + 40), (hi, O[:, 1] > O[-1, 1] - 40)):
            if np.any(msk): z = np.where(msk, np.polyval(np.polyfit(O[sel, 1], O[sel, 2], 1), y), z)
        return z
    yf = np.array(G["side_yz"])[:, 0].max(); ye = yy[yy <= yf]
    to_px = lambda y, z: np.stack([(y - Y0) * 2, (ztr(y) - z - D0) * 2], 1)
    top = to_px(ye, ztop_o(ye) + dz); bot = to_px(ye, ztop_o(ye) + dz - h_o(ye))
    d.line([tuple(p) for p in top], fill=(0, 255, 60), width=1); d.line([tuple(p) for p in bot], fill=(0, 220, 255), width=1)
    d.line([tuple(top[-1]), tuple(bot[-1])], fill=(0, 255, 60), width=1)
    for yv in G["front_leg"]["y_range"]:
        p = to_px(np.array([yv]), ztop_o(yv) + dz - h_o(yv) - 4)[0]; d.line([tuple(p), (p[0], p[1] + 30)], fill=(255, 40, 200), width=1)
    full = im; panels = [full]
    for nm, y0, y1 in (("back", 50, 140), ("front leg", 400, 470), ("front end", 470, 520)):
        c = im.crop((int((y0 - Y0) * 2), 0, int((y1 - Y0) * 2), im.size[1]))
        c = c.resize((c.size[0] * 2, c.size[1] * 2), Image.NEAREST); label(c, f"{S} IMG_{ph} side {nm}"); panels.append(c)
    label(full, f"{S} IMG_{ph} outer face strip (dz {dz:+.1f})")
    hh = max(p.size[1] for p in panels); row = Image.new("RGB", (sum(p.size[0] + 6 for p in panels), hh), "black"); x = 0
    for p in panels: row.paste(p, (x, 0)); x += p.size[0] + 6
    rows.append(row)
out = Image.new("RGB", (max(r.size[0] for r in rows), sum(r.size[1] + 10 for r in rows)), "black"); y = 0
for r in rows: out.paste(r, (0, y)); y += r.size[1] + 10
out.save(a.out, quality=88); print("wrote", a.out, out.size)
