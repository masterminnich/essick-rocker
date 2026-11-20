"""USAGE: python -I tools/build_model.py --out parts/model_v1 [--params parts/overrides.json]
Assemble the first parametric 3D model of the chair (design intent: left/right symmetric) from
  - the traced side-frame profiles (rocker, front leg, back leg lower part): work/parts/side*/, parts/rocker_profile.json
  - the chair point cloud (back legs upper part, arms, crest, slats, seat surface): work/dense/chair_dense.npy
  - a few sizes not yet measured from photos (member thickness across the chair), taken from tape close-ups or assumed.
Writes <out>.glb (all parts, mm, chair frame), <out>_params.json (every number with its provenance) and prints a summary.
Every dimension is tagged: fitted (traced outline), cloud (point-cloud fit), tape (read off a tape close-up), assumed.
Tiny compute (a 17k-point cloud and small meshes)."""
import sys, json, argparse
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import numpy as np, trimesh
from shapely.geometry import Polygon
from scipy.interpolate import SmoothBivariateSpline
from scipy.spatial import Delaunay
from rocker.sideframe import side_plane, to_plane, from_plane

ap = argparse.ArgumentParser(); ap.add_argument("--out", required=True); ap.add_argument("--params", default=None)
a = ap.parse_args()
PRM = {  # sizes not (yet) measured from photos
    "rocker_width_across": (31.0, "tape", "IMG_1493 read 1.20 in at the rear tip, +-1/16; assumed constant along the rocker"),
    "fleg_thickness_across": (33.0, "cloud+tape", "cloud inner-face depth 29-35 mm; IMG_1495 read 1.27 in"),
    "bleg_thickness_across": (38.0, "cloud+tape", "cloud 32-40 mm; IMG_1494 read 1.34-1.6 in"),
    "arm_thickness": (25.0, "assumed", "not measurable yet; caliper A1-A3 will replace"),
    "seat_edge_thickness": (40.0, "fitted", "side-edge face traced 39-45 mm at the back, thinner to the front; constant here"),
    "crest_height": (77.5, "tape", "IMG_1555 read 3.05 in"),
}
if a.params: PRM.update({k: tuple(v) for k, v in json.load(open(a.params)).items()})
P = lambda k: PRM[k][0]
C = np.load(ROOT / "work/dense/chair_dense.npy"); C = C[C[:, 2] > 6][:, :3]
Cm = C.copy(); Cm[:, 0] = np.abs(Cm[:, 0])          # mirrored onto the right side (design intent)
report = {}; meshes = {}


def rpoly(x, y, deg, clip=2.0, iters=6):
    keep = np.ones(len(x), bool)
    for _ in range(iters):
        c = np.polyfit(x[keep], y[keep], deg); keep = np.abs(y - np.polyval(c, x)) < clip
    return c, float(np.sqrt(np.mean((y[keep] - np.polyval(c, x[keep])) ** 2))), float(keep.mean())


def extrude_side(poly_uv, depth0, depth1, sign):
    """polygon in side-plane (u, v), solid between inward depths depth0..depth1"""
    pg = Polygon(poly_uv).buffer(0)
    m = trimesh.creation.extrude_polygon(pg, depth1 - depth0)
    V = np.c_[m.vertices[:, 0], m.vertices[:, 1], m.vertices[:, 2] + depth0]
    m.vertices = from_plane(V, sign)
    if sign < 0: m.invert()
    m.fix_normals(); return m


def sweep(centers, e1s, e2s, w1, w2):
    """rectangular bar: section half-extents w1/2 along e1, w2/2 along e2 at each centre"""
    n = len(centers); V = []; F = []
    for c, e1, e2, a1, a2 in zip(centers, e1s, e2s, w1, w2):
        V += [c - e1 * a1 / 2 - e2 * a2 / 2, c + e1 * a1 / 2 - e2 * a2 / 2, c + e1 * a1 / 2 + e2 * a2 / 2, c - e1 * a1 / 2 + e2 * a2 / 2]
    for i in range(n - 1):
        b = 4 * i
        for k in range(4):
            p, q = b + k, b + (k + 1) % 4; F += [[p, q, q + 4], [p, q + 4, p + 4]]
    F += [[0, 2, 1], [0, 3, 2]]; e = 4 * (n - 1); F += [[e, e + 1, e + 2], [e, e + 2, e + 3]]
    m = trimesh.Trimesh(np.array(V), np.array(F), process=False); m.fix_normals(); return m


def sheet_tables(sheet):
    """(z, y, arc length v) tables of a sheet written by tools/sheet_ortho.py (tabulated or polynomial profile)"""
    if "table" in sheet: tb = np.array(sheet["table"]); zt_ = np.linspace(tb[0, 0], tb[-1, 0], 2000); yt_ = np.interp(zt_, tb[:, 0], tb[:, 1])
    else: zt_ = np.linspace(sheet["z"][0], sheet["z"][1], 2000); yt_ = np.polyval(np.array(sheet["coef"]), zt_)
    return zt_, yt_, np.r_[0, np.cumsum(np.hypot(np.diff(zt_), np.diff(yt_)))]


def mirror(m):
    m2 = m.copy(); m2.vertices = m2.vertices * [-1, 1, 1]; m2.invert(); return m2

# ---------------------------------------------------------------- rocker
rp = json.load(open(ROOT / "parts/rocker_profile.json")); U = np.array(rp["u"]); rtop = np.array(rp["mean_top"]); rbot = np.array(rp["mean_bot"])
RVL = rp["right_vs_left"]
def rigid(q, th_deg, su, sv, inverse=False):
    th = np.radians(th_deg); c, s_ = np.cos(th), np.sin(th); q = np.asarray(q, float)
    if inverse:
        d = q - [su, sv]; return np.c_[c * d[:, 0] + s_ * d[:, 1], -s_ * d[:, 0] + c * d[:, 1]]
    return np.c_[c * q[:, 0] - s_ * q[:, 1] + su, s_ * q[:, 0] + c * q[:, 1] + sv]
def to_mean(q):   # left-frame side-plane coordinates -> the half-way frame between the left and right frames (design intent)
    return rigid(q, RVL["rotation_deg"] / 2, RVL["shift_u_mm"] / 2, RVL["shift_v_mm"] / 2, inverse=True)
def pooled_edges(name):
    """both sides' traced edges in the LEFT side-plane frame (right side moved by the rigid fit found on the rockers)"""
    A, B = [], []
    for S in "LR":
        d = json.load(open(ROOT / f"work/parts/side{S}/{name}.json")); ea, eb = np.array(d[name + "_a"]), np.array(d[name + "_b"])
        if S == "R": ea, eb = (rigid(e, RVL["rotation_deg"], RVL["shift_u_mm"], RVL["shift_v_mm"]) for e in (ea, eb))
        A.append(ea); B.append(eb)
    return np.vstack(A), np.vstack(B)
rock_poly = to_mean(np.r_[np.c_[U, rtop], np.c_[U[::-1], rbot[::-1]]])
meshes["ROCKER_R"] = extrude_side(rock_poly, 0, P("rocker_width_across"), +1); meshes["ROCKER_L"] = mirror(meshes["ROCKER_R"])
report["rocker"] = {"profile": "fitted (face orthophoto, both sides averaged)", "length_traced_mm": float(U[-1] - U[0]),
                    "face_height_mm": [float(np.min(rtop - rbot)), float(np.max(rtop - rbot))], "rocking_radius_mm": rp["rocking_radius_mm"],
                    "left_right_shape_rms_mm": rp["right_vs_left"]["residual_rms_mm"]}

# ---------------------------------------------------------------- legs in the side plane
fa, fb = pooled_edges("fleg")                     # a = rear edge, b = front edge (travel is upward)
vv = np.linspace(95, 628, 120)
c_fr, n_fr, k_fr = rpoly(fa[:, 1], fa[:, 0], 4); c_ff, n_ff, k_ff = rpoly(fb[:, 1], fb[:, 0], 4)
fl_rear, fl_front = np.polyval(c_fr, vv), np.polyval(c_ff, vv)
# cut the foot along the rocker's top edge
def foot_cut(vv, uu):
    out = []
    for v_, u_ in zip(vv, uu):
        out.append([u_, max(v_, np.interp(u_, U, rtop))])
    return np.array(out)
fl_poly = to_mean(np.r_[foot_cut(vv, fl_rear), foot_cut(vv, fl_front)[::-1]])
SFL = json.load(open(ROOT / "parts/side_frame.json"))["lines"] if (ROOT / "parts/side_frame.json").exists() else None
def sf_line(*keys):
    """triangulated side-frame line(s) (tools/edge_tri.py -> side_fit.py -> side_mirror.py, L+R averaged) in model side-plane coords (u, v, depth inward)"""
    Q = np.vstack([to_plane(np.c_[SFL[k]["x_abs"], SFL[k]["y"], SFL[k]["z"]], +1) for k in keys]); return Q[np.argsort(Q[:, 1])]
def sf_at(Q, v, col):
    """value of a line at heights v: linear between samples (bridges the seat joint), straight-line extension beyond the ends"""
    out = np.interp(v, Q[:, 1], Q[:, col]); lo, hi = v < Q[0, 1], v > Q[-1, 1]
    if lo.any(): c = np.polyfit(Q[:6, 1], Q[:6, col], 1); out[lo] = np.polyval(c, v[lo])
    if hi.any(): c = np.polyfit(Q[-6:, 1], Q[-6:, col], 1); out[hi] = np.polyval(c, v[hi])
    return out
def loft4(sec):
    """solid through 4-cornered sections: sec (n, 4, 3)"""
    n = len(sec); V = sec.reshape(-1, 3); F = []
    for i in range(n - 1):
        b = 4 * i
        for k in range(4):
            p_, q_ = b + k, b + (k + 1) % 4; F += [[p_, q_, q_ + 4], [p_, q_ + 4, p_ + 4]]
    F += [[0, 2, 1], [0, 3, 2]]; e = 4 * (n - 1); F += [[e, e + 1, e + 2], [e, e + 2, e + 3]]
    m = trimesh.Trimesh(V, np.array(F), process=False); m.fix_normals(); return m
if SFL:
    # three triangulated lines per leg: front outline and rear ridge on the outer face, rear arris on the inner face (the rear face is bevelled / rounded)
    QF, QR, QI = sf_line("fleg_front_lo", "fleg_front_hi"), sf_line("fleg_rear_lo", "fleg_rear_hi"), sf_line("fleg_rearfar_lo", "fleg_rearfar_hi")
    uF, dF, uR, uI, dI = sf_at(QF, vv, 0), sf_at(QF, vv, 2), sf_at(QR, vv, 0), sf_at(QI, vv, 0), sf_at(QI, vv, 2); uI = np.minimum(uI, uR)
    rt_m = to_mean(np.c_[U, rtop]); cut = lambda u_: np.maximum(vv, np.interp(u_, rt_m[:, 0], rt_m[:, 1]))
    sec = np.stack([np.c_[uF, cut(uF), dF], np.c_[uR, cut(uR), dF], np.c_[uI, cut(uI), dI], np.c_[uF, cut(uF), dI]], 1)
    meshes["FLEG_R"] = loft4(from_plane(sec.reshape(-1, 3), +1).reshape(-1, 4, 3)); meshes["FLEG_L"] = mirror(meshes["FLEG_R"])
    old_w = fl_front - fl_rear
    report["front_leg"] = {"profile": "triangulated per line from near-frontal side photos (tools/edge_tri.py), L and R averaged; outlines +-1 mm, rear outer-face ridge is a soft line +-2 mm",
                           "outer_face_width_mm": {f"v{int(v)}": float(np.interp(v, vv, uF - uR)) for v in (150, 300, 360, 500, 600)},
                           "overall_side_view_width_mm": {f"v{int(v)}": float(np.interp(v, vv, uF - uI)) for v in (150, 300, 360, 500, 600)},
                           "thickness_across_mm": {f"v{int(v)}": float(np.interp(v, vv, dI - dF)) for v in (150, 300, 500, 600)},
                           "left_right_fore_aft_mm": {k: SFL[k]["lr_diff_y_mean_mm"] for k in SFL if k.startswith("fleg")},
                           "previous_trace_width_mm": {f"v{int(v)}": float(np.interp(v, vv, old_w)) for v in (150, 300, 500, 600)},
                           "note": "seat joint (v 370-470) is bridged linearly; the earlier 8-photo median trace was 13-27 mm too wide (thickness parallax)"}
else:
    meshes["FLEG_R"] = extrude_side(fl_poly, 0, P("fleg_thickness_across"), +1); meshes["FLEG_L"] = mirror(meshes["FLEG_R"])
    report["front_leg"] = {"profile": "fitted (side face orthophoto, L+R pooled)", "edge_scatter_mm": [n_fr, n_ff], "inlier_share": [k_fr, k_ff],
                           "width_side_view_mm": {f"v{int(v)}": float(np.interp(v, vv, fl_front - fl_rear)) for v in (150, 300, 380, 450, 600)}}

ba, bb = pooled_edges("bleg")                     # a = rear edge (rough), b = front edge (good)
vb = np.linspace(40, 470, 80)
c_bf, n_bf, k_bf = rpoly(bb[(bb[:, 1] < 480), 1], bb[(bb[:, 1] < 480), 0], 4)
c_br, n_br, k_br = rpoly(ba[(ba[:, 1] < 480), 1], ba[(ba[:, 1] < 480), 0], 4, clip=4.0)
bl_front = np.polyval(c_bf, vb); bl_rear = np.polyval(c_br, vb); bl_low_src = "fitted (side face orthophoto; front edge good, rear edge rough)"
if SFL:        # below the seat: triangulated front outline and inner rear arris replace the old traces; their correction at the top of that range is carried up to the arm
    for key, cf, tgt in (("bleg_front_lo", c_bf, "f"), ("bleg_rearfar_lo", c_br, "r")):
        Q = sf_line(key); corr = np.interp(vb, Q[:, 1], Q[:, 0] - np.polyval(cf, Q[:, 1]))
        if tgt == "f": bl_front = bl_front + corr; corr_f = corr
        else: bl_rear = bl_rear + corr; corr_r = corr
    bl_low_src = (f"below the seat (v 65-270): triangulated front outline and inner rear arris (tools/edge_tri.py, L+R averaged, +-1 mm); the old rear trace was {corr_r.min():+.0f}..{corr_r.max():+.0f} mm off "
                  f"(front {corr_f.min():+.1f}..{corr_f.max():+.1f}); above v 270 the old trace with the correction at v 270 held")
    if (ROOT / "parts/back_legs.json").exists() and "table" in json.load(open(ROOT / "parts/back_legs.json"))["sheet"]:
        # through the seat joint (v 270-440) nothing is traced: bridge the rear edge with a cubic from the triangulated inner rear arris below the seat
        # to the back outer arris triangulated from the front photos above it (parts/back_legs.json), instead of the old side trace
        _B = json.load(open(ROOT / "parts/back_legs.json")); _z, _y, _s = sheet_tables(_B["sheet"]); z0_ = float(np.interp(_B["v_range"][0] + 10, _s, _z)); zk = np.arange(z0_, z0_ + 90, 6.0)      # only where the back view was actually traced
        _v = np.clip(np.interp(zk, _z, _s), _B["v_range"][0] + 10, _B["v_range"][1] - 10); Qu = to_plane(np.c_[np.polyval(_B["symmetric"]["outer"], _v), np.interp(zk, _z, _y), zk], +1)
        Ql = sf_line("bleg_rearfar_lo"); Ql = Ql[Ql[:, 1] > Ql[-1, 1] - 90]; cb = np.polyfit(np.r_[Ql[:, 1], Qu[:, 1]], np.r_[Ql[:, 0], Qu[:, 0]], 3)
        mid = (vb > Ql[-1, 1]) & (vb < Qu[0, 1]); up = vb >= Qu[0, 1]; old_mid = bl_rear[mid | up].copy()
        bl_rear[mid] = np.polyval(cb, vb[mid]); bl_rear[up] = np.interp(vb[up], Qu[:, 1], Qu[:, 0])
        fitres = np.r_[Ql[:, 0], Qu[:, 0]] - np.polyval(cb, np.r_[Ql[:, 1], Qu[:, 1]])
        bl_low_src += (f"; rear edge v {Ql[-1, 1]:.0f}-{Qu[0, 1]:.0f} (seat joint, not traced) bridged by a cubic between the triangulated lines either side (fit {np.sqrt(np.mean(fitres ** 2)):.1f} mm rms); "
                       f"it moved the rear edge there by {np.min(bl_rear[mid | up] - old_mid):+.0f}..{np.max(bl_rear[mid | up] - old_mid):+.0f} mm")
bl_w = bl_front - bl_rear
low_center_uvd = np.c_[to_mean(np.c_[(bl_front + bl_rear) / 2, vb]), np.full(len(vb), P("bleg_thickness_across") / 2)]
low_center = from_plane(low_center_uvd, +1)
# upper part from the cloud (mirrored): points of the back legs above the arm joint
m = (Cm[:, 0] > 165) & (Cm[:, 2] > 520) & (Cm[:, 2] < 1075) & (Cm[:, 1] < 60)
B = Cm[m]
cy, ny, ky = rpoly(B[:, 2], B[:, 1], 3, clip=30); ymid = np.polyval(cy, B[:, 2])
B = B[np.abs(B[:, 1] - ymid) < 32]                   # drop slat / crest points far from the leg band
zz = np.linspace(540, 1070, 12); cen = []; wside = []; wacr = []
for z0 in zz:
    s = B[np.abs(B[:, 2] - z0) < 28]
    if len(s) < 12: cen.append([np.nan] * 3); wside.append(np.nan); wacr.append(np.nan); continue
    x_lo, x_hi = np.percentile(s[:, 0], [3, 97]); y_lo, y_hi = np.percentile(s[:, 1], [3, 97])
    cen.append([(x_lo + x_hi) / 2, (y_lo + y_hi) / 2, z0]); wacr.append(x_hi - x_lo); wside.append(y_hi - y_lo)
cen = np.array(cen); ok = np.isfinite(cen[:, 0])
cx_u = np.polyfit(zz[ok], cen[ok, 0], 2); cy_u = np.polyfit(zz[ok], cen[ok, 1], 3)
zu = np.linspace(low_center[-1, 2] + 15, 1085, 40)
up_center = np.c_[np.polyval(cx_u, zu), np.polyval(cy_u, zu), zu]
# blend lower (trace) into upper (cloud) centreline
zl = low_center[:, 2]; zb = np.r_[zl, zu]
allc = np.vstack([low_center, up_center])
tan = np.gradient(allc, axis=0); tan /= np.linalg.norm(tan, axis=1, keepdims=True)
o_, u_, v_, n_ = side_plane(+1)
e_acr = n_ - tan * (tan @ n_)[:, None]; e_acr /= np.linalg.norm(e_acr, axis=1, keepdims=True)
e_side = np.cross(tan, e_acr)
w_side_up = np.interp(zu, zz[ok], np.array(wside)[ok] * np.cos(np.arctan(np.abs(np.polyval(np.polyder(cy_u), zz[ok])))))
_t2 = np.gradient(low_center_uvd[:, :2], axis=0); _t2 /= np.linalg.norm(_t2, axis=1, keepdims=True)
w_side = np.r_[bl_w * np.abs(_t2[:, 1]), w_side_up]        # horizontal width -> width perpendicular to the leg
w_side = np.convolve(np.r_[w_side[:1].repeat(3), w_side, w_side[-1:].repeat(3)], np.ones(7) / 7, "valid")
w_acr = np.full(len(allc), P("bleg_thickness_across")); bl_src = "v1 (side plane + assumed thickness)"
if (ROOT / "parts/back_legs.json").exists():
    BL = json.load(open(ROOT / "parts/back_legs.json")); zt_b, yt_b, st_b = sheet_tables(BL["sheet"])
    vleg = np.interp(allc[:, 2], zt_b, st_b); v_lo, v_hi = BL["v_range"]; vc = np.clip(vleg, v_lo + 10, v_hi - 10)
    xin, xout = np.polyval(BL["symmetric"]["inner"], vc), np.polyval(BL["symmetric"]["outer"], vc)
    t = np.clip((allc[:, 2] - allc[0, 2]) / (np.interp(v_lo + 10, st_b, zt_b) - allc[0, 2]), 0, 1)       # 0 at the rocker, 1 where the back-view trace starts
    xc_new = (1 - t) * allc[:, 0] + t * (xin + xout) / 2; w_acr = (1 - t) * w_acr + t * (xout - xin)
    allc = np.c_[xc_new, allc[:, 1:]]; bl_src = "fitted (unrolled back view, by-eye seeded edges, L+R averaged) above the seat; blended to the side plane at the rocker"
    def _frame(c):
        tn = np.gradient(c, axis=0); tn /= np.linalg.norm(tn, axis=1, keepdims=True)
        ea = np.tile([1.0, 0, 0], (len(c), 1)); ea = ea - tn * np.sum(tn * ea, 1)[:, None]; ea /= np.linalg.norm(ea, axis=1, keepdims=True); return tn, ea, np.cross(tn, ea)
    tan, e_acr, e_side = _frame(allc)
    if "table" in BL["sheet"]:            # the sheet is the triangulated back OUTER arris: put the leg's rear face on it (mid-face is toe/2 forward of the outer arris)
        es = e_side * np.sign(-e_side[:, 1:2]); rear = allc + es * (w_side / 2)[:, None]; toe = float(BL.get("inner_arris_forward_mm", 0.0)) / 2
        dy = np.where(rear[:, 2] >= zt_b[0], np.interp(rear[:, 2], zt_b, yt_b) + toe - rear[:, 1], 0.0); rear_gap = dy[(vleg > v_lo) & (vleg < v_hi)]
        allc = np.c_[allc[:, 0], allc[:, 1] + t * dy, allc[:, 2]]; tan, e_acr, e_side = _frame(allc)
        bl_src += f"; rear face moved onto the triangulated back arris (was off by {np.median(rear_gap):+.1f} mm median, {np.abs(rear_gap).max():.1f} max)"
bl_up_src = "cloud (centreline + extents, mirrored L+R)"; up_rep = {}
if SFL and "bleg_front_hi" in SFL and "bleg_rear_hi" in SFL:
    # above the arm: the front outline and the rear edge traced in SIDE view, on a sheet fitted to the leg's own outer face (the leg splays 8 -> 43 mm
    # outside the side plane, so the old side sheet could not be used), each side triangulated on its own and averaged (parts/side_frame.json)
    zF, yF, zR, yR = (np.array(SFL[k][c]) for k in ("bleg_front_hi", "bleg_rear_hi") for c in ("z", "y")); z_ = allc[:, 2]
    wy = w_side / np.abs(e_side[:, 1]); f_old = allc[:, 1] + wy / 2; r_old = allc[:, 1] - wy / 2            # front / rear outline of the leg so far, fore-aft at each height
    z0 = max(zF[0], zR[0]); zj = 450.0                                                                     # zj: top of the seat joint, where the lower leg's lines stop
    def _corr(zL, yL, old):
        d = np.interp(z_, zL, yL) - old; d0 = np.interp(z0, zL, yL) - np.interp(z0, z_, old); d1 = np.interp(zL[-1], zL, yL) - np.interp(zL[-1], z_, old)
        return np.where(z_ < z0, d0 * np.clip((z_ - zj) / (z0 - zj), 0, 1), np.where(z_ > zL[-1], d1, d))   # ramp in below the trace, hold the last correction above it
    dF, dR = _corr(zF, yF, f_old), _corr(zR, yR, r_old); f_new, r_new = f_old + dF, r_old + dR
    allc = np.c_[allc[:, 0], (f_new + r_new) / 2, allc[:, 2]]; tan, e_acr, e_side = _frame(allc); w_side = (f_new - r_new) * np.abs(e_side[:, 1])
    inr = (z_ >= z0) & (z_ <= zR[-1])
    bl_up_src = (f"z {z0:.0f}-{zF[-1]:.0f}: front outline triangulated in side view from 4 cameras standing behind the leg on each side (solve residual 0.6 / 0.5 mm L / R); z {z0:.0f}-{zR[-1]:.0f}: rear edge traced in side view "
                 f"in 2 cameras standing in front of the leg on each side, depth held on the back outer arris (residual 0.45 / 0.7 mm); L and R averaged. Above z {zR[-1]:.0f} the rear follows the back-view arris, "
                 f"shifted to meet the side trace; z {zj:.0f}-{z0:.0f} (arm joint) is a linear ramp from the lower leg. Across-width still from the back view.")
    up_rep = {"front_moved_mm": [float(dF[inr].min()), float(dF[inr].max())], "rear_moved_mm": [float(dR[inr].min()), float(dR[inr].max())],
              "left_right_fore_aft_mm": {k: {"mean": SFL[k]["lr_diff_y_mean_mm"], "rms_about_mean": SFL[k]["lr_diff_y_rms_about_mean_mm"]} for k in ("bleg_front_hi", "bleg_rear_hi")},
              "width_fore_aft_mm": {f"z{int(z)}": float(np.interp(z, z_, f_new - r_new)) for z in (620, 700, 800, 900, 1000)},
              "width_square_to_leg_mm": {f"z{int(z)}": float(np.interp(z, z_, w_side)) for z in (620, 700, 800, 900, 1000)}}
meshes["BLEG_R"] = sweep(allc, e_acr, e_side, w_acr, w_side); meshes["BLEG_L"] = mirror(meshes["BLEG_R"])
report["back_leg"] = {"lower": bl_low_src, "upper": bl_up_src, "upper_side_view": up_rep,
                      "front_edge_scatter_mm": n_bf, "rear_edge_scatter_mm": n_br, "width_side_view_mm": {f"z{int(z)}": float(np.interp(z, zb, w_side)) for z in (100, 300, 450, 600, 800, 1000)},
                      "across": bl_src, "width_across_mm": {f"z{int(z)}": float(np.interp(z, allc[:, 2], w_acr)) for z in (100, 300, 450, 600, 800, 1000)}, "top_centre": up_center[-1].round(1).tolist(), "splay_top_x_mm": float(up_center[-1, 0])}

# ---------------------------------------------------------------- seat
seat_z = lambda y: 338 + 0.155 * y
ms = (Cm[:, 0] < 275) & (Cm[:, 1] > -45) & (Cm[:, 1] < 560) & (Cm[:, 2] > seat_z(Cm[:, 1]) - 22) & (Cm[:, 2] < seat_z(Cm[:, 1]) + 45)
S = Cm[ms]
# plan outline (half): |x| max per y bin, and y range
yb = np.arange(-30, 541, 15); hw = []
for y0 in yb:
    s = S[np.abs(S[:, 1] - y0) < 12]; hw.append(np.percentile(s[:, 0], 98) if len(s) > 15 else np.nan)
hw = np.array(hw); okb = np.isfinite(hw); c_hw, n_hw, _ = rpoly(yb[okb], hw[okb], 3, clip=6)
y_back = float(np.percentile(S[S[:, 0] < 120, 1], 1)); y_front = float(np.percentile(S[S[:, 0] < 120, 1], 99.5))
ys = np.linspace(y_back, y_front, 50); half = np.clip(np.polyval(c_hw, ys), 150, 300)
outline = np.r_[np.c_[half, ys], np.c_[-half[::-1], ys[::-1]]]
# top surface (mirrored cloud), smooth bivariate spline on (|x|, y)
St = S[S[:, 2] > seat_z(S[:, 1]) - 16]
both = St
def feats(x, y):
    xs_, ys_ = (x / 250.0) ** 2, (y - 250.0) / 250.0          # even in x (symmetric seat)
    return np.stack([xs_ ** i * ys_ ** j for i in range(4) for j in range(5)], 1)
Fm = feats(both[:, 0], both[:, 1]); keep = np.ones(len(both), bool)
for _ in range(6):
    coef = np.linalg.lstsq(Fm[keep], both[keep, 2], rcond=None)[0]; rs_all = both[:, 2] - Fm @ coef; keep = np.abs(rs_all) < 4.0
rs = rs_all[keep]
class _S:
    @staticmethod
    def ev(x, y): return feats(np.abs(np.asarray(x, float)), np.asarray(y, float)) @ coef
spl = _S
pg = Polygon(outline); gx, gy = np.meshgrid(np.arange(-290, 291, 10), np.arange(y_back, y_front + 1, 10))
from shapely.geometry import Point
ins = np.array([pg.contains(Point(p)) for p in np.c_[gx.ravel(), gy.ravel()]])
pts2 = np.r_[np.c_[gx.ravel(), gy.ravel()][ins], outline]
tri = Delaunay(pts2); cent = pts2[tri.simplices].mean(1); keep = np.array([pg.buffer(0.5).contains(Point(c)) for c in cent]); T = tri.simplices[keep]
zt = spl.ev(pts2[:, 0], pts2[:, 1]); zedge = seat_z(pts2[:, 1]) + 4
dist = np.array([pg.exterior.distance(Point(p)) for p in pts2]); wgt = np.clip(dist / 25, 0, 1)
seat_src = None; _sp = ROOT / "seat" / "surface.json"
if _sp.exists():
    # measured top surface (seat session: blue-tape dots, thin-plate spline, right half mirrored). Inside the dotted region the
    # spline is used as it is; outside, the cloud polynomial is kept but shifted so that it meets the spline at the region's edge
    SS = json.load(open(_sp)); _c = np.array(SS["tps"]["centres"]); _w = np.array(SS["tps"]["w"]); _a = SS["tps"]["a"]
    def tps(x, y):
        r2 = (np.asarray(x, float)[:, None] - _c[None, :, 0]) ** 2 + (np.asarray(y, float)[:, None] - _c[None, :, 1]) ** 2
        return (_w[None, :] * 0.5 * r2 * np.log(np.maximum(r2, 1e-12))).sum(1) + _a[0] + _a[1] * x + _a[2] * y
    (mx0, mx1), (my0, my1) = SS["measured_region"]["x"], SS["measured_region"]["y"]
    xc, yc = np.clip(pts2[:, 0], mx0, mx1), np.clip(pts2[:, 1], my0, my1); inside = (xc == pts2[:, 0]) & (yc == pts2[:, 1])
    z_cloud = zt.copy(); zt = z_cloud + tps(xc, yc) - spl.ev(xc, yc)
    ry, rz = np.array(SS["rim"]["y"]), np.array(SS["rim"]["z"]); s0, s1 = np.polyfit(ry[:15], rz[:15], 1)[0], np.polyfit(ry[-15:], rz[-15:], 1)[0]
    def rim_z(y): return np.where(y < ry[0], rz[0] + s0 * (y - ry[0]), np.where(y > ry[-1], rz[-1] + s1 * (y - ry[-1]), np.interp(y, ry, rz)))
    zrim = rim_z(pts2[:, 1]); wgt = np.ones(len(pts2))       # no rim lift: the edge strip beyond the dots is the shifted cloud surface
    dz_in = (tps(pts2[inside, 0], pts2[inside, 1]) - z_cloud[inside])
    seat_src = {"surface": f"measured inside |x| <= {mx1:.0f}, y {my0:.0f}-{my1:.0f} (seat/surface.json: {SS['dots']['top']} tape dots on the right half, mirrored; thin-plate spline, "
                           f"leave-one-out {SS['loo_interior']['rms']:.2f} mm rms interior, {SS['loo_interior']['max']:.1f} max); outside that the cloud polynomial shifted to meet it",
                "measured_minus_cloud_polynomial_mm": {"median": float(np.median(dz_in)), "rms": float(np.sqrt(np.mean(dz_in ** 2))), "min": float(dz_in.min()), "max": float(dz_in.max())},
                "rim_z_mm": {f"y{int(y)}": float(rim_z(np.array([float(y)]))[0]) for y in (100, 200, 300, 400, 500)}}
# rim: blend the surface to the rim line near the outline so the edge is clean (not inside the measured region)
zt = wgt * zt + (1 - wgt) * np.maximum(zt, zedge - 2)
zbm = seat_z(pts2[:, 1]) + 4 - P("seat_edge_thickness")     # underside: NOT measured; this plane matched the lower edge in side photo 1507 by eye
nP = len(pts2); V = np.r_[np.c_[pts2, zt], np.c_[pts2, zbm]]; F = list(T) + [[q[0] + nP, q[2] + nP, q[1] + nP] for q in T]
nb = len(outline); base = nP - nb
for i in range(nb):
    p, q = base + i, base + (i + 1) % nb; F += [[p, q, q + nP], [p, q + nP, p + nP]]
seat = trimesh.Trimesh(V, np.array(F), process=True); seat.fix_normals(); meshes["SEAT"] = seat
dish = float(((zrim if seat_src else zedge) - zt).max())
report["seat"] = {"outline": "cloud (98th percentile half-width per station; front-edge scallops NOT modelled)", "surface": "cloud (polynomial surface even in x, mirrored L+R)",
                  "surface_fit_rms_mm": float(np.sqrt(np.mean(rs ** 2))), "n_surface_points": int(len(St)), "depth_y_mm": [y_back, y_front],
                  "half_width_mm": {"back": float(half[0]), "mid": float(half[len(half) // 2]), "front": float(half[-1])},
                  "max_scoop_below_rim_mm": dish, "rim_tilt_deg": float(np.degrees(np.arctan(0.155)))}
if seat_src:
    report["seat"].update(seat_src); report["seat"]["rim_tilt_deg"] = float(np.degrees(np.arctan(np.polyfit(ry, rz, 1)[0])))
    report["seat"]["underside"] = "assumed plane (z = 342 + 0.155 y - edge thickness); checked by eye against the lower edge in IMG_1507 only"
    _e = np.abs(np.abs(pts2[:, 0]) - 240) < 12
    report["seat"]["thickness_near_edge_mm"] = {f"y{int(y)}": float(np.median((zt - zbm)[_e & (np.abs(pts2[:, 1] - y) < 25)])) for y in (100, 300, 500)}

# ---------------------------------------------------------------- arms (plank from the cloud)
ma = (Cm[:, 0] > 226) & (Cm[:, 0] < 345) & (Cm[:, 1] > 25) & (Cm[:, 1] < 545) & (Cm[:, 2] > 465 + 0.36 * Cm[:, 1]) & (Cm[:, 2] < 540 + 0.36 * Cm[:, 1])
A = Cm[ma]
ybins = np.arange(40, 540, 20); zt_, xi_, xo_, yb_ = [], [], [], []
for y0 in ybins:
    s_ = A[np.abs(A[:, 1] - y0) < 14]
    if len(s_) < 15: continue
    zt_.append(np.percentile(s_[:, 2], 93)); xi_.append(np.percentile(s_[:, 0], 3)); xo_.append(np.percentile(s_[:, 0], 97)); yb_.append(y0)
yb_ = np.array(yb_); c_zt, n_zt, _ = rpoly(yb_, np.array(zt_), 3, clip=5); c_xi, _, _ = rpoly(yb_, np.array(xi_), 3, clip=6); c_xo, _, _ = rpoly(yb_, np.array(xo_), 3, clip=6)
ya = np.linspace(yb_[0] - 10, yb_[-1] + 10, 40)
cen = np.c_[(np.polyval(c_xi, ya) + np.polyval(c_xo, ya)) / 2, ya, np.polyval(c_zt, ya)]
tan = np.gradient(cen, axis=0); tan /= np.linalg.norm(tan, axis=1, keepdims=True)
e1 = np.tile([1.0, 0, 0], (len(ya), 1)); e1 = e1 - tan * np.sum(tan * e1, 1)[:, None]; e1 /= np.linalg.norm(e1, axis=1, keepdims=True); e2 = np.cross(tan, e1)
e2 = e2 * np.sign(e2[:, 2:3])
cen_mid = cen - e2 * P("arm_thickness") / 2
am = sweep(cen_mid, e1, e2, np.polyval(c_xo, ya) - np.polyval(c_xi, ya), np.full(len(ya), P("arm_thickness")))
meshes["ARM_R"] = am; meshes["ARM_L"] = mirror(am)
report["arm"] = {"top_surface": "cloud (93rd percentile height per station, mirrored L+R)", "top_line_scatter_mm": n_zt, "n_points": int(len(A)),
                 "length_mm": float(ya[-1] - ya[0]), "y_range_mm": [float(ya[0]), float(ya[-1])],
                 "top_height_mm": {"back": float(np.polyval(c_zt, ya[0])), "front": float(np.polyval(c_zt, ya[-1]))},
                 "width_mm": {"back": float(np.polyval(c_xo, ya[2]) - np.polyval(c_xi, ya[2])), "mid": float(np.polyval(c_xo, ya[20]) - np.polyval(c_xi, ya[20])), "front": float(np.polyval(c_xo, ya[-3]) - np.polyval(c_xi, ya[-3]))},
                 "outline": "cloud extents (3-97 percentile), NOT a traced edge; arm edges are sculpted"}

# ---------------------------------------------------------------- crest rail
mc = (C[:, 2] > 1003) & (C[:, 2] < 1095) & (np.abs(C[:, 0]) < 290) & (C[:, 1] < -120)
K = C[mc]
xb = np.arange(-260, 261, 40); yf, yr = [], []
for x0 in xb:
    s = K[np.abs(K[:, 0] - x0) < 26]; yf.append(np.percentile(s[:, 1], 96) if len(s) > 10 else np.nan); yr.append(np.percentile(s[:, 1], 4) if len(s) > 10 else np.nan)
yf, yr = np.array(yf), np.array(yr); g = np.isfinite(yf)
cf = np.polyfit(np.abs(xb[g]), yf[g], 2); cr = np.polyfit(np.abs(xb[g]), yr[g], 2)      # even in x (symmetric)
xs = np.linspace(-258, 258, 45); crest_out = np.r_[np.c_[xs, np.polyval(cf, np.abs(xs))], np.c_[xs[::-1], np.polyval(cr, np.abs(xs[::-1]))]]
ztop = float(np.percentile(K[:, 2], 99.5)); zc0 = ztop - P("crest_height")
cm = trimesh.creation.extrude_polygon(Polygon(crest_out).buffer(0), P("crest_height")); cm.vertices = cm.vertices + [0, 0, zc0]; meshes["CREST"] = cm
report["crest"] = {"plan": "cloud (front/back extents per station, symmetric quadratic)", "thickness_centre_mm": float(np.polyval(cf, 0) - np.polyval(cr, 0)),
                   "thickness_end_mm": float(np.polyval(cf, 250) - np.polyval(cr, 250)), "bow_mm_over_half_span": float(np.polyval(cf, 0) - np.polyval(cf, 250)),
                   "top_z_mm": ztop, "note": "top edge arch and back-leg tilt of the rail NOT modelled (vertical extrusion)"}

# ---------------------------------------------------------------- slats (traced in the unrolled back view)
SLJ = json.load(open(ROOT / "parts/slats.json")); thick = float(SLJ["thickness_mm"]); ex60 = np.tile([1.0, 0, 0], (60, 1))
def slat(sheet, lo_c, hi_c, sign=1.0):
    """sheet = the slat's BACK face; the solid extends thick mm forward of it"""
    zt_s, yt_s, st_s = sheet_tables(sheet); vs = np.linspace(8, min(st_s[-1] - 2, 742), 60); vcl = np.clip(vs, *SLJ["v_range"])
    zs, ys = np.interp(vs, st_s, zt_s), np.interp(vs, st_s, yt_s); ds = np.interp(vs, st_s, np.gradient(yt_s, zt_s)); nr = np.hypot(1, ds)
    nb = np.c_[np.zeros(len(vs)), -1 / nr, ds / nr]; lo, hi = np.polyval(lo_c, vcl) * sign, np.polyval(hi_c, vcl)
    return sweep(np.c_[(lo + hi) / 2, ys, zs] - nb * thick / 2, ex60, nb, hi - lo, np.full(len(vs), thick)), (hi - lo)
SY = SLJ["symmetric"]
meshes["SLAT_C"], wc_ = slat(SLJ["sheet_centre"], SY["centre_half"], SY["centre_half"], -1.0)
meshes["SLAT_R"], wo_ = slat(SLJ["sheet_outer"], SY["outer_in"], SY["outer_out"]); meshes["SLAT_L"] = mirror(meshes["SLAT_R"])
report["slats"] = {"edges": "fitted (unrolled back view, by-eye seeded edges, L+R averaged)", "surface": "back face located by photo consistency in 7 height bands, separately for centre and outer slats",
                   "thickness_mm": thick, "thickness_provenance": "front-face cloud layer vs photo-consistent back face (about 10 mm)",
                   "centre_width_mm": {"near_seat": float(wc_[8]), "under_crest": float(wc_[-5])}, "outer_width_mm": {"near_seat": float(wo_[8]), "under_crest": float(wo_[-5])}}

# ---------------------------------------------------------------- export
scene = trimesh.Scene()
for k, m_ in meshes.items(): scene.add_geometry(m_, node_name=k, geom_name=k)
out = ROOT / a.out; out.parent.mkdir(parents=True, exist_ok=True)
scene.export(str(out) + ".glb")
allv = np.vstack([m_.vertices for m_ in meshes.values()])
report["overall"] = {"bbox_min_mm": allv.min(0).round(1).tolist(), "bbox_max_mm": allv.max(0).round(1).tolist(),
                     "height_in": float(allv[:, 2].max() / 25.4), "width_in": float((allv[:, 0].max() - allv[:, 0].min()) / 25.4), "length_in": float((allv[:, 1].max() - allv[:, 1].min()) / 25.4)}
json.dump({"assumed_or_tape": {k: {"value_mm": v[0], "provenance": v[1], "note": v[2]} for k, v in PRM.items()}, "parts": report}, open(str(out) + "_params.json", "w"), indent=1)
# edges for overlays: every mesh's feature edges as polylines
pl = []
for k, m_ in meshes.items():
    ang = m_.face_adjacency_angles; ed = m_.face_adjacency_edges[ang > np.radians(25)]
    for e in ed: pl.append({"name": k, "points": m_.vertices[e].tolist(), "closed": False})
json.dump(pl, open(str(out) + "_edges.json", "w"))
print(json.dumps(report, indent=1))
