"""USAGE: tools/py.sh templates/check_legs_overlay.py --geom templates/out/legs_geom.json --out figures/templates/legs_overlay.jpg
              [--photos L:o:1507,L:o:1506,R:o:1474,R:o:1470,L:ub:1507,R:ub:1470]
Draw the front- and back-leg template outlines (green: the cut line lifted onto the leg's outer face plane) and the joint marks
(magenta: contact faces and Domino centres) on
rectified side photos (work/parts/side{L,R}/<sheet>_<photo>.png, 0.5 mm/px; 'o' = the side-frame sheet, 'ub' = the sheet fitted to
the upper back leg). The left side is the model's mirror (x -> -x).
Numeric check: along the cut outline every 3 mm, the strongest grey-level edge within +-5 mm along the outline normal; prints the
median |offset| and the share within 1.6 mm per leg and photo (edges hidden behind the arm or seat give outliers; the median is the
number). Output: per photo one column (sheet at 1/3 size, then 2x zooms of foot, seat joint and top of each leg). Tiny compute."""
import json, argparse, numpy as np
from PIL import Image, ImageDraw, ImageFilter
ap = argparse.ArgumentParser(); ap.add_argument("--geom", required=True); ap.add_argument("--out", required=True)
ap.add_argument("--photos", default="L:o:1507,L:o:1506,R:o:1474,R:o:1470,L:ub:1507,R:ub:1470"); a = ap.parse_args()
G = json.load(open(a.geom))


def sheet(side, sh):
    pl = json.load(open(f"work/parts/side{side}/{sh}_plane.json"))
    return np.array(pl["origin"]), np.array(pl["u"]), np.array(pl["v"]), pl["res"], pl["urange"], pl["vrange"]


def to_px(X, side, S):
    O, eu, ev, res, ur, vr = S; X = np.asarray(X, float) * ([-1, 1, 1] if side == "L" else [1, 1, 1])
    Q = X - O; return np.stack([(Q @ eu - ur[0]) / res, (vr[1] - Q @ ev) / res], 1)


def edge_offsets(gray, P, res, step_mm=3.0, win_mm=5.0):
    """P: closed outline in px. Strongest gradient along the normal within +-win; returns offsets (mm) of points with a usable edge"""
    P = np.vstack([P, P[:1]]); seg = np.linalg.norm(np.diff(P, axis=0), axis=1); s = np.r_[0, np.cumsum(seg)]
    ss = np.arange(0, s[-1], step_mm / res); Q = np.stack([np.interp(ss, s, P[:, 0]), np.interp(ss, s, P[:, 1])], 1)
    T = np.gradient(Q, axis=0); T /= np.linalg.norm(T, axis=1)[:, None] + 1e-9; N = np.stack([-T[:, 1], T[:, 0]], 1)
    k = np.arange(-win_mm / res, win_mm / res + 1); H, W = gray.shape; out = []
    for q, n in zip(Q, N):
        R = q[None] + k[:, None] * n[None]; xi, yi = np.round(R[:, 0]).astype(int), np.round(R[:, 1]).astype(int)
        if xi.min() < 0 or yi.min() < 0 or xi.max() >= W or yi.max() >= H: continue
        prof = gray[yi, xi]; g = np.abs(np.gradient(prof))
        if g.max() < 4.0: continue                              # no edge worth the name (flat background or shadow)
        out.append(k[np.argmax(g)] * res)
    return np.array(out)


cols = []; report = []
for spec in a.photos.split(","):
    side, sh, ph = spec.split(":"); S = sheet(side, sh)
    im = Image.open(f"work/parts/side{side}/{sh}_{ph}.png").convert("RGB"); d = ImageDraw.Draw(im)
    gray = np.asarray(im.convert("L").filter(ImageFilter.GaussianBlur(1.5)), float)
    legs = ("front", "back") if sh == "o" else ("back",)
    zooms = []
    for key in legs:
        g = G[key]; P = to_px(g["outline_outer_xyz"], side, S)
        if sh == "ub":                                             # the ub sheet only covers the upper back leg: score above v 600
            vv = np.array(g["outline_uv"])[:, 1]; Pm = P[vv > 600]
        else:
            Pm = P
        off = edge_offsets(gray, P if sh == "o" else Pm, S[3]) if len(Pm) > 10 else np.array([])
        if len(off): report.append(f"{side} {sh}_{ph} {key}: {len(off)} pts, median |off| {np.median(np.abs(off)):.2f} mm, within 1.6 mm {np.mean(np.abs(off) <= 1.6) * 100:.0f} %, median signed {np.median(off):+.2f}")
        d.line([tuple(p) for p in np.vstack([P, P[:1]])], fill=(0, 255, 60), width=1)
        for cn, c in g["contacts"].items():
            Q = to_px(c["xyz_sample"], side, S)
            for q in Q[::3]: d.point(tuple(q), fill=(255, 40, 200))
        for mn, m in g["mortises"].items():
            q = to_px([m["centre_xyz"]], side, S)[0]; d.line([(q[0] - 8, q[1]), (q[0] + 8, q[1])], fill=(255, 40, 200), width=1); d.line([(q[0], q[1] - 8), (q[0], q[1] + 8)], fill=(255, 40, 200), width=1)
        uvo = np.array(g["outline_uv"]); vmin, vmax = uvo[:, 1].min(), uvo[:, 1].max()
        # densify (the outline is simplified: long straight stretches have no vertices) so the zooms land at the asked height
        t = np.linspace(0, len(uvo), 20 * len(uvo), endpoint=False); i0 = np.floor(t).astype(int) % len(uvo); i1 = (i0 + 1) % len(uvo); f = (t - np.floor(t))[:, None]
        uvo = uvo[i0] * (1 - f) + uvo[i1] * f; P = P[i0] * (1 - f) + P[i1] * f
        picks = [("foot", vmin + 25), ("seat", 330 if key == "back" else 395), ("top", vmax - 30)] if sh == "o" else [("arm", 640), ("upper", 850), ("top", vmax - 30)]
        for nm, vz in picks:
            i = np.argmin(np.abs(uvo[:, 1] - vz)); j = np.argmin(np.abs(uvo[:, 1] - vz) + (np.abs(uvo[:, 0] - uvo[i, 0]) < 15) * 1e3)
            c = (P[i] + P[j]) / 2; half = 60
            zooms.append((f"{key} {nm}", (int(c[0] - half), int(c[1] - half), int(c[0] + half), int(c[1] + half))))
    W, H = im.size; base = im.crop((0, 0, W, H)); small = base.resize((W // 3, H // 3))
    panels = []
    for nm, box in zooms:
        z = im.crop(box).resize((240, 240), Image.NEAREST); ImageDraw.Draw(z).text((3, 3), nm, fill=(255, 255, 0)); panels.append(z)
    colw = max(small.size[0], 2 * 244); rows_ = (len(panels) + 1) // 2
    col = Image.new("RGB", (colw, small.size[1] + 20 + rows_ * 244), "black"); ImageDraw.Draw(col).text((4, 4), f"{side} {sh}_{ph} (IMG_{ph})", fill=(255, 255, 0))
    col.paste(small, (0, 20))
    for i, p in enumerate(panels): col.paste(p, ((i % 2) * 244, small.size[1] + 20 + (i // 2) * 244))
    cols.append(col)
out = Image.new("RGB", (sum(c.size[0] + 8 for c in cols), max(c.size[1] for c in cols)), "black"); x = 0
for c in cols: out.paste(c, (x, 0)); x += c.size[0] + 8
out.save(a.out, quality=88); print("wrote", a.out, out.size)
for r in report: print(" ", r)
