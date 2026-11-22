"""USAGE: tools/py.sh templates/crest.py [--allow-mm 19.05] [--mortise-mm 19.05] [--out templates/out] [--geom-json templates/out/crest_geom.json]
Crest rail, 1:1, three templates: (1) crest_plan = the rail seen square onto its top face (back face as one line, the top-front and
bottom-front arrises, shoulders, slat mortises on the bottom face, the blank), (2) crest_back = the back face UNROLLED (top and
bottom arches, shoulders, the arch carried over the leg tops, slat mortises), (3) crest_sections = card gauges of the cross-section
at x 0, 100, 200 and at the shoulder (with the slat mortises at x 0 and 100).
The crest is SAWN FROM SOLID and shaped (no bending form): see templates/LEDGER.md 2026-11-21 crest.
Inputs: parts/crest.json (four arrises, design even polynomials; lean; joints), parts/model_v24_shapes.glb (slats SLAT_C/L/R
where they enter the crest, BLEG_R inner face beside the crest), parts/edge_radii.json (arris rounds, a shaping note).
RAIL FRAME (all three drawings): the back face is a cylinder ruled along the back legs' lean (crest.json back_face_lean_deg, 9.9 deg:
its bottom-rear arris was carried down from the top-rear one along that lean), so it is developable and a square bandsaw cut once
the blank is tipped by the lean. x = across the chair (+ = chair's right), w = forward square to the rulings, h = up the rulings.
w = 0 at the back face at x 0; h = 0 on the chord of the bottom-rear arris at the shoulders. Tiny compute (<1 s, <300 MB)."""
import json, argparse, subprocess, sys, os, numpy as np
import trimesh
from shapely.geometry import Polygon, LineString, MultiLineString
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tplkit as K
from tplkit import fmt, frac32

ap = argparse.ArgumentParser()
ap.add_argument("--allow-mm", type=float, default=19.05, help="joinery allowance (tenon) past each shoulder: joint hidden, ASSUMED")
ap.add_argument("--mortise-mm", type=float, default=19.05, help="slat mortise depth; matches slat_template's 3/4 in allowance (ASSUMED)")
ap.add_argument("--out", default="templates/out"); ap.add_argument("--geom-json", default=None); ap.add_argument("--rev", default=None)
a = ap.parse_args()

def ghash(p):
    try: return subprocess.run(["git", "log", "-1", "--format=%h", "--", p], capture_output=True, text=True).stdout.strip() or "uncommitted"
    except Exception: return "?"
REV = a.rev or ghash("parts/crest.json")
CJ = json.load(open("parts/crest.json")); ER = json.load(open("parts/edge_radii.json"))
E = {k: CJ["edges"][k]["design"] for k in ("top_rear", "top_front", "bottom_front", "bottom_rear")}
TH = np.radians(CJ["section"]["back_face_lean_deg"]["deg"]); cT, sT = np.cos(TH), np.sin(TH)
ev = lambda c, x: sum(ck * np.abs(np.asarray(x, float)) ** (2 * k) for k, ck in enumerate(c))
XSH = CJ["joints"]["design_shoulder_half_length"]["mm"]; XOUT = (abs(CJ["joints"]["left"]["leg_outer_face_x"]["mm"]) + CJ["joints"]["right"]["leg_outer_face_x"]["mm"]) / 2
JA, MD = a.allow_mm, a.mortise_mm

def yz(k, x): return np.stack([ev(E[k]["y_even_poly"], x), ev(E[k]["z_even_poly"], x)], -1)
def to_wh_raw(y, z): return y * cT + z * sT, -y * sT + z * cT
W0 = float(to_wh_raw(*yz("top_rear", 0.0))[0])
xq = np.array([-XSH, XSH]); H0 = float(np.mean(to_wh_raw(*yz("bottom_rear", xq).T)[1]))
def to_wh(y, z): w, h = to_wh_raw(np.asarray(y, float), np.asarray(z, float)); return w - W0, h - H0
def from_wh(w, h): w, h = np.asarray(w) + W0, np.asarray(h) + H0; return w * cT - h * sT, w * sT + h * cT       # -> y, z
def arris(k, x): p = yz(k, x); return np.stack(to_wh(p[..., 0], p[..., 1]), -1)          # (w, h) of an arris at x

# ---------------- back face: one curve w_b(x); arc length for the unrolled view ----------------
xf = np.linspace(-XOUT - 5, XOUT + 5, 2401)
wb = arris("top_rear", xf)[:, 0]; wbr = arris("bottom_rear", xf)[:, 0]
back_dev = float(np.abs(wb - wbr)[np.abs(xf) <= XSH].max())      # bottom-rear vs top-rear in w: same ruling if the lean holds
ds = np.hypot(np.diff(xf), np.diff(wb)); sarc = np.r_[0, np.cumsum(ds)]; sarc -= np.interp(0, xf, sarc)
U = lambda x: np.interp(x, xf, sarc)                         # unrolled coordinate along the back face
WB = lambda x: np.interp(x, xf, wb)

# ---------------- model v24: leg inner face beside the crest, slats into the crest ----------------
SC = trimesh.load("parts/model_v24_shapes.glb").geometry
h_on_back = lambda x, z: (z - (WB(x) + W0) * sT) / cT - H0                     # h of the back-face point at x with chair height z
LG = SC["BLEG_R"]; leg_in = []
for z in np.arange(998, 1067, 4.0):
    s = LG.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
    if s is None: continue
    P = np.vstack([np.vstack([np.linspace(d[i], d[i + 1], 40) for i in range(len(d) - 1)]) for d in s.discrete])   # densified outline
    yb = float(from_wh(WB(218.0), h_on_back(218.0, z))[0])                     # crest back face y beside the leg at this z
    m = (P[:, 1] > yb + 3) & (P[:, 1] < yb + 22) & (P[:, 0] > 200)
    if m.any(): leg_in.append((z, float(P[m, 0].min())))
leg_in = np.array(leg_in)
# shoulder line in the rail frame (on the back face): x of the leg inner face against h
sh_h = np.array([h_on_back(x, z) for z, x in leg_in])   # h of each section level on the back face
XSH_bot, XSH_top = float(np.interp(0.0, sh_h, leg_in[:, 1])), float(np.interp(float(arris("top_rear", XSH)[1]), sh_h, leg_in[:, 1]))

def slat_lines(name, x):
    """the slat's back and front faces at station x as lines w = a + b h (rail frame), from the v24 slat mesh below the crest"""
    s = SC[name].section(plane_origin=[x, 0, 0], plane_normal=[1, 0, 0])
    if s is None: return None
    P = np.vstack([np.vstack([np.linspace(d[i], d[i + 1], 30) for i in range(len(d) - 1)]) for d in s.discrete]); w, h = to_wh(P[:, 1], P[:, 2])
    hb = float(arris("bottom_rear", x)[1]); m = (h > hb - 45) & (h < hb - 3)
    if m.sum() < 6: return None
    w, h = w[m], h[m]; out = []
    # densify the outline, then per 2 mm band of h take the outline's extremes: min w = back face, max w = front face
    bins = np.arange(hb - 45, hb - 3, 2.0); lo_, hi_, hc_ = [], [], []
    for b0 in bins:
        sel = (h >= b0) & (h < b0 + 2)
        if sel.sum(): lo_.append(w[sel].min()); hi_.append(w[sel].max()); hc_.append(b0 + 1)
    if len(hc_) < 6: return None
    hc_, lo_, hi_ = map(np.array, (hc_, lo_, hi_))
    for v_ in (lo_, hi_):
        c_ = np.polyfit(hc_, v_, 1); k_ = np.abs(v_ - np.polyval(c_, hc_)) < 1.0          # one robust refit
        out.append(np.polyfit(hc_[k_], v_[k_], 1) if k_.sum() >= 4 else c_)
    return out            # [back (b, a), front (b, a)] for np.polyval(., h)

def bottom_line(x):
    R, F = arris("bottom_rear", x), arris("bottom_front", x); return R, F

def meet(line, R, F):
    """where a slat face line w(h) meets the bottom-face segment R-F (rail frame)"""
    d = F - R; t = np.linspace(-0.5, 1.5, 4001); P = R + np.outer(t, d)
    f = P[:, 0] - np.polyval(line, P[:, 1]); i = np.where(np.diff(np.sign(f)))[0]
    return P[i[0]] if len(i) else None

SLATS = {}
for name, x0, x1 in (("SLAT_C", -60, 60), ("SLAT_R", 60, 150), ("SLAT_L", -150, -60)):
    xs = np.arange(x0, x1 + 0.01, 0.25); rows = []
    for x in xs:
        L_ = slat_lines(name, x)
        if L_ is None: continue
        R, F = bottom_line(x); pb, pf = meet(L_[0], R, F), meet(L_[1], R, F)
        if pb is None or pf is None: continue
        rows.append((x, pb[0], pf[0], pb[1], pf[1]))
    r = np.array(rows); t_ = r[:, 2] - r[:, 1]; r = r[np.abs(t_ - np.median(t_)) < 2.0]        # drop the few bad fits at the slat edges
    v = SC[name].vertices
    vin = v[v[:, 2] > 990]; zb = ev(E["bottom_rear"]["z_even_poly"], vin[:, 0])
    SLATS[name] = dict(x=[float(r[:, 0].min()), float(r[:, 0].max())], rows=r,
                       model_depth_mm=float((to_wh(vin[:, 1], vin[:, 2])[1] - arris("bottom_rear", vin[:, 0])[:, 1]).max()))
xC = 0.0; xR = float(np.mean(SLATS["SLAT_R"]["x"]))

# ---------------- envelope (blank) ----------------
xx = np.linspace(-XSH, XSH, 441)
A = {k: arris(k, xx) for k in E}
w_lo = float(min(A[k][:, 0].min() for k in E)); w_hi = float(max(A[k][:, 0].max() for k in E))
h_lo = float(min(A[k][:, 1].min() for k in E)); h_hi = float(max(A[k][:, 1].max() for k in E))
h_hi_leg = float(arris("top_rear", XOUT)[1])
BLANK_L = 2 * (U(XSH) + JA) + 50.0

def items_common(it, y0, y1, lab=True):
    it.append(dict(kind="line", pts=[[0, y0], [0, y1]], style="centre"))
    if lab: it.append(dict(kind="text", xy=(0, y1 + 3), s="CL", size=6))

# ================= 1. PLAN (square onto the top face) =================
pi = []
xe = np.linspace(-XSH, XSH, 221)
back = np.stack([xe, WB(xe)], 1); bfront = np.stack([xe, arris("bottom_front", xe)[:, 0]], 1); tfront = np.stack([xe, arris("top_front", xe)[:, 0]], 1)
pi.append(dict(kind="cut", pts=np.vstack([back, bfront[::-1]]), closed=True))             # saw line: back face + bottom-front arris
pi.append(dict(kind="cut", pts=tfront, closed=False))                                      # top-front arris: shape the front face to it
for sg in (-1, 1):
    xa = np.linspace(sg * XSH, sg * (XSH + JA), 12)
    pi.append(dict(kind="line", pts=np.stack([xa, WB(xa)], 1), style="hidden"))
    pi.append(dict(kind="line", pts=np.stack([xa, arris("bottom_front", xa)[:, 0]], 1), style="hidden"))
    xt = sg * (XSH + JA); pi.append(dict(kind="line", pts=[[xt, float(WB(xt))], [xt, float(arris("bottom_front", xt)[0])]], style="hidden"))
    # shoulders: top (on this face) and bottom (2 mm further in on the model leg)
    for xs_, lbl in ((XSH_top, "shoulder (top)"), (XSH_bot, "")):
        pi.append(dict(kind="line", pts=[[sg * xs_, float(WB(xs_)) - 4], [sg * xs_, float(arris("bottom_front", xs_)[0]) + 4]], style="mark"))
    pi.append(dict(kind="text", xy=(sg * (XSH - 12), float(WB(XSH)) - 8), s=f"shoulder\nleg inner face", size=5.2, color=K.MARK))
    # back-leg top beside the crest (end grain, flush with the crest's back and front at the top)
    xl = np.linspace(sg * XSH_top, sg * XOUT, 10)
    pi.append(dict(kind="line", pts=np.vstack([np.stack([xl, WB(xl)], 1), np.stack([xl[::-1], arris("top_front", np.abs(xl[::-1]))[:, 0]], 1), [[xl[0], float(WB(xl[0]))]]]), style="ref"))
    pi.append(dict(kind="text", xy=(sg * (XSH + XOUT) / 2, float(WB(XOUT)) + 32), s="back leg top\n(end grain, flush)", size=5.2, color=K.REF))
    # stations
    for xs_ in (100.0, 200.0):
        x_ = sg * xs_; pi.append(dict(kind="line", pts=[[x_, float(WB(x_)) - 3], [x_, float(WB(x_)) + 3]], style="ref"))
        pi.append(dict(kind="line", pts=[[x_, float(arris("bottom_front", x_)[0]) - 3], [x_, float(arris("bottom_front", x_)[0]) + 3]], style="ref"))
        pi.append(dict(kind="text", xy=(x_, float(WB(x_)) - 6), s=f"X{xs_:.0f}", size=5.2, color=K.REF))
# slat mortises on the bottom face (seen through the top)
MORT_PLAN = {}
for name, S_ in SLATS.items():
    r = S_["rows"]; poly = np.vstack([np.stack([r[:, 0], r[:, 1]], 1), np.stack([r[::-1, 0], r[::-1, 2]], 1)])
    MORT_PLAN[name] = poly; pi.append(dict(kind="line", pts=np.vstack([poly, poly[:1]]), style="mark"))
    pi.append(dict(kind="text", xy=(float(r[:, 0].mean()), float(r[:, 2].max()) + 5), s=f"mortise {name[-1]}", size=5.2, color=K.MARK))
items_common(pi, w_lo - 12, w_hi + 8)
pi.append(dict(kind="dim", p1=(-XSH_top, w_hi + 14), p2=(XSH_top, w_hi + 14), off=0, label=f"shoulder to shoulder at the top {fmt(2 * XSH_top)} (straight across)", size=5.5))
pi.append(dict(kind="dim", p1=(-XSH - JA, w_lo - 20), p2=(XSH + JA, w_lo - 20), off=0, label=f"with {frac32(JA)} joinery allowance each end {fmt(2 * (XSH + JA))}", size=5.5))
for x_, lab_ in ((0.0, "X0"),):
    pi.append(dict(kind="dim", p1=(x_ + 6, float(WB(x_))), p2=(x_ + 6, float(arris("bottom_front", x_)[0])), off=0, label=f"{float(arris('bottom_front', x_)[0] - WB(x_)):.1f}", size=5))
    pi.append(dict(kind="dim", p1=(x_ - 6, float(WB(x_))), p2=(x_ - 6, float(arris("top_front", x_)[0])), off=0, label=f"{float(arris('top_front', x_)[0] - WB(x_)):.1f}", size=5))
bow = float(WB(XSH) - WB(0))
pi.append(dict(kind="line", pts=[[-XSH, float(WB(XSH))], [XSH, float(WB(XSH))]], style="ref"))
pi.append(dict(kind="text", xy=(40, float(WB(XSH)) - 3.5), s=f"bow of the back face {fmt(bow)} (chord at the shoulders)", size=5, color=K.REF))
pi.append(dict(kind="text", xy=(-XSH - 25, w_lo - 34),
    s="CREST RAIL - PLAN, square onto the top face, 1:1. Chair's front is UP the page, chair's right on the right.\n"
      "Heavy closed line = the saw line: back face (one line: top-rear and bottom-rear arrises lie on the same lean) and\n"
      "the bottom-front arris (the rail is thicker at the bottom). Heavy open line = top-front arris: after the arches are\n"
      "sawn, shape the front face down to it (front face leans back 12-19 deg in the chair, back face 9.9; gauges crest_sections).\n"
      f"Red: shoulders on the legs' inner faces (top {XSH_top:.1f} / bottom {XSH_bot:.1f} from CL on the model leg) and the three\n"
      f"slat mortises where the slats meet the BOTTOM face. Dashed: {frac32(JA)} joinery allowance (joint hidden; assumed).\n"
      "Ticks X100 / X200 match the section gauges. Blank: see the key dimensions.",
    size=6.0, ha="left", va="top"))

# ================= 2. BACK FACE, UNROLLED =================
bi = []
xb = np.linspace(-XSH, XSH, 221); ub = U(xb)
top = np.stack([ub, arris("top_rear", xb)[:, 1]], 1); bot = np.stack([ub, arris("bottom_rear", xb)[:, 1]], 1)
# shoulder ends follow the model leg's inner face (x against h)
def sh_pts(sg):
    hh = np.linspace(float(arris("bottom_rear", XSH)[1]), float(arris("top_rear", XSH)[1]), 12)
    xs_ = np.interp(hh, sh_h, leg_in[:, 1]); return np.stack([sg * U(xs_), hh], 1)
outline_b = np.vstack([bot, sh_pts(1), top[::-1], sh_pts(-1)[::-1]])
bi.append(dict(kind="cut", pts=outline_b, closed=True))
for sg in (-1, 1):
    u0, u1 = sg * U(XSH), sg * (U(XSH) + JA); hb_, ht_ = float(arris("bottom_rear", XSH)[1]), float(arris("top_rear", XSH)[1])
    bi.append(dict(kind="line", pts=[[u0, hb_], [u1, hb_], [u1, ht_], [u0, ht_]], style="hidden"))
    # arch carried on over the leg top: the leg is trimmed flush to it after glue-up
    xl = np.linspace(XSH, XOUT, 12); bi.append(dict(kind="line", pts=np.stack([sg * U(xl), arris("top_rear", xl)[:, 1]], 1), style="mark"))
    bi.append(dict(kind="text", xy=(sg * U((XSH + XOUT) / 2 + 6), float(arris("top_rear", XOUT)[1]) + 9), s="arch runs on over\nthe leg top: trim\nthe leg flush to it", size=5.0, color=K.MARK))
    bi.append(dict(kind="line", pts=[[sg * U(XOUT), float(arris("top_rear", XOUT)[1]) - 6], [sg * U(XOUT), float(arris("top_rear", XOUT)[1]) + 3]], style="mark"))
    bi.append(dict(kind="line", pts=sh_pts(sg), style="mark"))
    bi.append(dict(kind="text", xy=(sg * (U(XSH) - 16), (hb_ + ht_) / 2), s="shoulder\n(leg inner\nface)", size=5.0, color=K.MARK))
    for xs_ in (100.0, 200.0):
        u_ = sg * U(xs_); hb2, ht2 = float(arris("bottom_rear", xs_)[1]), float(arris("top_rear", xs_)[1])
        bi.append(dict(kind="line", pts=[[u_, hb2], [u_, hb2 + 5]], style="ref")); bi.append(dict(kind="line", pts=[[u_, ht2 - 5], [u_, ht2]], style="ref"))
        bi.append(dict(kind="text", xy=(u_, ht2 - 9), s=f"X{xs_:.0f}", size=5.2, color=K.REF))
# slat mortises: where each slat's back face meets the bottom edge, and the mortise depth (hidden)
for name, S_ in SLATS.items():
    x0, x1 = S_["x"]; u0, u1 = U(x0), U(x1); h0, h1 = float(arris("bottom_rear", x0)[1]), float(arris("bottom_rear", x1)[1])
    bi.append(dict(kind="line", pts=[[u0, h0 - 4], [u0, h0 + 4]], style="mark")); bi.append(dict(kind="line", pts=[[u1, h1 - 4], [u1, h1 + 4]], style="mark"))
    xm = np.linspace(x0, x1, 20); bi.append(dict(kind="line", pts=np.vstack([[u0, h0], [u0, h0 + MD], *np.stack([U(xm), arris("bottom_rear", xm)[:, 1] + MD], 1), [u1, h1 + MD], [u1, h1]]), style="hidden"))
    bi.append(dict(kind="text", xy=((u0 + u1) / 2, (h0 + h1) / 2 + MD / 2), s=f"mortise {name[-1]}\n{x1 - x0:.1f} wide", size=5.2, color=K.MARK))
items_common(bi, h_lo - 10, h_hi + 6)
bi.append(dict(kind="line", pts=[[-U(XSH) - JA - 8, 0], [U(XSH) + JA + 8, 0]], style="ref"))
bi.append(dict(kind="text", xy=(-U(XSH) + 40, -3.5), s="h = 0: chord of the bottom arris at the shoulders", size=5, color=K.REF))
hc_t, hc_b = float(arris("top_rear", 0)[1]), float(arris("bottom_rear", 0)[1]); hs_t, hs_b = float(arris("top_rear", XSH)[1]), float(arris("bottom_rear", XSH)[1])
bi.append(dict(kind="dim", p1=(8, hc_b), p2=(8, hc_t), off=0, label=f"{fmt(hc_t - hc_b)}", size=5.5))
bi.append(dict(kind="dim", p1=(U(XSH) - 28, hs_b), p2=(U(XSH) - 28, hs_t), off=0, label=f"{hs_t - hs_b:.1f}", size=5.2))
bi.append(dict(kind="dim", p1=(-U(XSH), h_hi + 12), p2=(U(XSH), h_hi + 12), off=0, label=f"shoulder to shoulder ALONG the bowed back face {fmt(2 * U(XSH))} (unrolled)", size=5.5))
bi.append(dict(kind="text", xy=(-U(XSH) - JA, h_lo - 16),
    s="CREST RAIL - BACK FACE UNROLLED, 1:1. Seen from behind: chair's right on the right.\n"
      "The back face is ruled along the lean, so it unrolls exactly: after the plan is sawn, wrap this on the back face with CL on\n"
      "the centre and the shoulder marks on the plan's shoulder marks, trace both arches and saw them square to the back face\n"
      "(the top and bottom faces are square to it). Red: shoulders (model leg inner face; it leans out 2 mm over the height), the\n"
      f"arch carried on over the leg tops, and the slat mortises (width on the bottom edge; dashed = {frac32(MD)} deep, assumed to match\n"
      "slat_template's allowance; joint not seen). Lengths here are along the face, 1.5 mm longer each side than straight across.",
    size=6.0, ha="left", va="top"))

# ================= 3. SECTION GAUGES =================
si = []; STN = [0.0, 100.0, 200.0, XSH]; SEC = {}; gx = 0.0
for j, x in enumerate(STN):
    Q = np.array([arris(k, x) for k in ("top_rear", "top_front", "bottom_front", "bottom_rear")]); Q[:, 0] -= WB(x)   # back face at w = 0
    hs = 0.0; Qd = Q + [gx, 0]
    si.append(dict(kind="cut", pts=Qd, closed=True))
    # card border (REF) and plumb-in-the-chair line
    cx0, cx1, cy0, cy1 = gx - 14, gx + Q[:, 0].max() + 14, Q[:, 1].min() - 22, Q[:, 1].max() + 26
    si.append(dict(kind="line", pts=[[cx0, cy0], [cx1, cy0], [cx1, cy1], [cx0, cy1], [cx0, cy0]], style="ref"))
    zc = Qd[[0, 3]].mean(0); pl = np.array([sT, cT]) * 0                                   # plumb in the chair = z axis in (w, h)
    zdir = np.array([sT, cT])                                                              # chair z in rail frame: w = z sin, h = z cos
    p0 = np.array([gx - 9, Q[:, 1].min() + 2]); si.append(dict(kind="line", pts=[p0, p0 + zdir * 40], style="ref"))
    si.append(dict(kind="text", xy=tuple(p0 + zdir * 44), s="plumb", size=4.6, color=K.REF))
    th_t = float(np.hypot(*(Q[1] - Q[0]))); th_b = float(np.hypot(*(Q[2] - Q[3]))); hgt = float(Q[0, 1] - Q[3, 1])
    fl = float(np.degrees(np.arctan2(Q[2, 0] - Q[1, 0], Q[1, 1] - Q[2, 1])))               # front face vs back face (rail frame)
    si.append(dict(kind="dim", p1=tuple(Qd[0]), p2=tuple(Qd[1]), off=-6, label=f"{th_t:.1f}", size=5))
    si.append(dict(kind="dim", p1=tuple(Qd[3]), p2=tuple(Qd[2]), off=6, label=f"{th_b:.1f}", size=5))
    si.append(dict(kind="dim", p1=tuple(Qd[3]), p2=tuple(Qd[0]), off=-4.5, label=f"{hgt:.1f}", size=5))
    nm = "SHOULDER" if j == 3 else f"X{x:.0f}"
    si.append(dict(kind="text", xy=(gx + Q[:, 0].max() / 2, cy1 - 7), s=f"{nm}\n" + (f"x {x:.1f}" if j == 3 else f"x {x:.0f} and {-x:.0f}" if x else "x 0 (centre)"), size=6))
    si.append(dict(kind="text", xy=(gx + Q[:, 0].max() / 2, cy0 + 7), s=f"front {fl + np.degrees(TH):.1f} deg\nback {np.degrees(TH):.1f} deg", size=4.8))
    SEC[nm] = dict(x=x, quad_wh=Q.tolist(), thickness_top=th_t, thickness_bottom=th_b, height_back=hgt, front_lean_chair_deg=fl + float(np.degrees(TH)))
    # slat mortise in this section
    for name in (("SLAT_C",) if x == 0 else ("SLAT_R",) if SLATS["SLAT_R"]["x"][0] < x < SLATS["SLAT_R"]["x"][1] else ()):
        L_ = slat_lines(name, x); R, F = bottom_line(x); pb, pf = meet(L_[0], R, F), meet(L_[1], R, F)
        db = np.array([np.polyval(np.polyder(L_[0]), 0), 1.0]); db /= np.linalg.norm(db)
        df = np.array([np.polyval(np.polyder(L_[1]), 0), 1.0]); df /= np.linalg.norm(df)
        M = np.array([pb, pb + db * MD, pf + df * MD, pf]); M[:, 0] -= WB(x); M[:, 0] += gx
        si.append(dict(kind="line", pts=np.vstack([M, M[:1]]), style="mark"))
        si.append(dict(kind="line", pts=[M[0], M[0] - db * 14], style="ref")); si.append(dict(kind="line", pts=[M[3], M[3] - df * 14], style="ref"))
        si.append(dict(kind="text", xy=tuple(M[:2].mean(0) + [-10, 4]), s=f"mortise {name[-1]}\n{np.hypot(*(pf - pb)):.1f}", size=4.6, color=K.MARK))
        SEC[nm]["mortise_" + name] = dict(back=(pb - [WB(x), 0]).tolist(), front=(pf - [WB(x), 0]).tolist(), angle_to_h_deg=float(np.degrees(np.arctan(np.polyval(np.polyder(L_[0]), 0)))))
    gx += Q[:, 0].max() + 40
si.append(dict(kind="text", xy=(-14, h_lo - 30),
    s="CREST RAIL - SECTION GAUGES, 1:1. Seen from the chair's RIGHT end (front to the right); the left half is the mirror.\n"
      "Back face vertical on the page (it leans 9.9 deg back in the chair: grey 'plumb' line). Glue to card, cut the card on its\n"
      "border and cut the section out: the window checks the shaped rail at X0, X100 / X200 (both sides) and at the shoulder.\n"
      f"Red: slat mortises at X0 (centre slat) and X100 (outer slat), {frac32(MD)} deep along the slat (assumed); grey = slat faces.\n"
      "Arrises: ease to about 1.5 mm radius (measured r 0.9-1.8 top rear, 1.1-2.2 bottom rear, parts/edge_radii.json).",
    size=6.0, ha="left", va="top"))

# ---------------- title blocks ----------------
TB = [
    "Arrises: four 3D curves triangulated from overhead (1545/1547/1548/1549, 1544, 1542) and rear (1502/1501/1503) photos; design = L/R",
    "  mirrored even polynomials (parts/crest.json). Tol: top-rear 1.0 mm; top-front, bottom-rear, bottom-front 1.6 mm. ASSUMED in crest.json:",
    "  bottom-rear depth (carried down the back legs' 9.9 deg lean), top/bottom faces square to the back face (front z = rear z + 4.4).",
    f"  Fits valid to |x| 212 (top-rear 249): 6 mm extrapolated to the shoulder. Back-face check: bottom-rear vs top-rear w differ <= {back_dev:.1f} mm.",
    "Shoulders: back legs' inner faces (crest.json, back view, +-0.8; model v24 leg inner face beside the crest, used for the shoulder line).",
    "Slat mortises: slats of model v24 where their faces meet the crest bottom face; depth not seen (assumed). Leg/crest joint hidden.",
    "Not measured by hand: M3 (height at the centre: photos 74.7 at x -75 vs tape IMG_1555 77.5), M7 (table to crest top, model 1082.7).",
    "Critique v24 worst: bottom/front +2.9 mm at x 0..100 (lower edge may sit low on the chair; a round explains <= 0.9 of it).",
    f"Generated by templates/crest.py from parts/crest.json @ {REV}, parts/model_v24_shapes.glb.",
]
thc = float(arris("bottom_front", 0)[0] - WB(0)); tht = float(arris("top_front", 0)[0] - WB(0))
KD = [("Shoulder to shoulder (top, straight)", 2 * XSH_top, f"bottom {2 * XSH_bot:.1f}; along the back face {2 * U(XSH):.1f}"),
      ("Height at the centre (back face)", hc_t - hc_b, f"{hs_t - hs_b:.1f} at the shoulder"),
      ("Thickness at the centre, top / bottom", f"{frac32(tht)} / {frac32(thc)}  ({tht:.1f} / {thc:.1f} mm)", "square to the back face"),
      ("Bow of the back face", bow, "plan, chord at the shoulders"),
      ("Blank (rail frame) L x W x H", f"{frac32(BLANK_L)} x {frac32(w_hi - w_lo + 3)} x {frac32(h_hi - h_lo + 3)}  ({BLANK_L:.0f} x {w_hi - w_lo + 3:.0f} x {h_hi - h_lo + 3:.0f} mm)",
       "incl. allowance + 25 mm waste/end; W = stock thickness"),
      ("Joinery allowance / slat mortise depth", f"{frac32(JA)} / {frac32(MD)}", "ASSUMED (joints hidden)")]
pl_spec = dict(name="crest_plan", title="ESSICK rocker - crest rail, plan (square onto the top face)", rev=REV, items=pi, title_block=TB, key_dims=KD)
bk_spec = dict(name="crest_back", title="ESSICK rocker - crest rail, back face unrolled (arches, shoulders, mortises)", rev=REV, items=bi, title_block=TB, key_dims=KD)
sc_spec = dict(name="crest_sections", title="ESSICK rocker - crest rail, section gauges X0 / X100 / X200 / shoulder", rev=REV, items=si, title_block=TB, key_dims=KD)

os.makedirs(a.out, exist_ok=True)
Lp = K.write_all(pl_spec, a.out); Lb = K.write_all(bk_spec, a.out); Ls = K.write_all(sc_spec, a.out)
# geometry for the overlay check: arrises back in the chair frame (x, y, z) and marks
X3 = lambda k, xs: np.c_[xs, yz(k, xs)]
xo = np.linspace(-XSH, XSH, 221)
geom = dict(frame="chair mm", arrises={k: X3(k, xo).tolist() for k in E},
            arch_over_leg={str(sg): X3("top_rear", sg * np.linspace(XSH, XOUT, 12)).tolist() for sg in (-1, 1)},
            shoulders=dict(top=XSH_top, bottom=XSH_bot, leg_inner_face_z_x=leg_in.tolist(), crest_json=XSH),
            slats={k: dict(x=v["x"], model_depth_mm=v["model_depth_mm"],
                           bottom_back=[[float(r[0]), *map(float, from_wh(r[1], r[3]))] for r in v["rows"]],
                           bottom_front=[[float(r[0]), *map(float, from_wh(r[2], r[4]))] for r in v["rows"]]) for k, v in SLATS.items()},
            lean_deg=float(np.degrees(TH)), back_dev=back_dev, bow=bow, unrolled_half=float(U(XSH)), sections=SEC,
            blank=dict(L=BLANK_L, W=w_hi - w_lo + 3, H=h_hi - h_lo + 3), outer_leg_x=XOUT,
            tiles=dict(plan=[Lp["rows"], Lp["cols"]], back=[Lb["rows"], Lb["cols"]], sections=[Ls["rows"], Ls["cols"]]))
json.dump(geom, open(a.geom_json or f"{a.out}/crest_geom.json", "w"), indent=1)
print(f"crest: shoulders top {2 * XSH_top:.1f} bottom {2 * XSH_bot:.1f} (crest.json {2 * XSH:.1f}); along back face {2 * U(XSH):.1f}; bow {bow:.1f}; back dev {back_dev:.2f}")
print(f"       height centre {hc_t - hc_b:.1f} shoulder {hs_t - hs_b:.1f}; thick top {tht:.1f} bottom {thc:.1f}; blank {BLANK_L:.0f} x {w_hi - w_lo + 3:.0f} x {h_hi - h_lo + 3:.0f}")
for k, v in SLATS.items(): print(f"       {k}: x {v['x'][0]:.1f}..{v['x'][1]:.1f} ({v['x'][1] - v['x'][0]:.1f} wide), w {v['rows'][:, 1].min():.1f}..{v['rows'][:, 2].max():.1f}, model depth {v['model_depth_mm']:.1f}")
for k, v in SEC.items(): print(f"       {k}: top {v['thickness_top']:.1f} bot {v['thickness_bottom']:.1f} h {v['height_back']:.1f} front lean {v['front_lean_chair_deg']:.1f}")
print(f"tiles: plan {Lp['rows']}x{Lp['cols']}, back {Lb['rows']}x{Lb['cols']}, sections {Ls['rows']}x{Ls['cols']}")
