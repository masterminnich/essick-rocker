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
ap.add_argument("--legacy", action="store_true", help="v3 crest and arms from the cloud instead of parts/crest.json + parts/arms.json")
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
meshes["FLEG_R"] = extrude_side(fl_poly, 0, P("fleg_thickness_across"), +1); meshes["FLEG_L"] = mirror(meshes["FLEG_R"])
report["front_leg"] = {"profile": "fitted (side face orthophoto, L+R pooled)", "edge_scatter_mm": [n_fr, n_ff], "inlier_share": [k_fr, k_ff],
                       "width_side_view_mm": {f"v{int(v)}": float(np.interp(v, vv, fl_front - fl_rear)) for v in (150, 300, 380, 450, 600)}}

ba, bb = pooled_edges("bleg")                     # a = rear edge (rough), b = front edge (good)
vb = np.linspace(40, 470, 80)
c_bf, n_bf, k_bf = rpoly(bb[(bb[:, 1] < 480), 1], bb[(bb[:, 1] < 480), 0], 4)
c_br, n_br, k_br = rpoly(ba[(ba[:, 1] < 480), 1], ba[(ba[:, 1] < 480), 0], 4, clip=4.0)
bl_front = np.polyval(c_bf, vb); bl_rear = np.polyval(c_br, vb); bl_w = bl_front - bl_rear
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
def sheet_tables(sheet):
    """(z, y, arc length v) tables of a sheet written by tools/sheet_ortho.py (tabulated or polynomial profile)"""
    if "table" in sheet: tb = np.array(sheet["table"]); zt_ = np.linspace(tb[0, 0], tb[-1, 0], 2000); yt_ = np.interp(zt_, tb[:, 0], tb[:, 1])
    else: zt_ = np.linspace(sheet["z"][0], sheet["z"][1], 2000); yt_ = np.polyval(np.array(sheet["coef"]), zt_)
    return zt_, yt_, np.r_[0, np.cumsum(np.hypot(np.diff(zt_), np.diff(yt_)))]
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
        dy = np.interp(rear[:, 2], zt_b, yt_b) + toe - rear[:, 1]; rear_gap = dy[(vleg > v_lo) & (vleg < v_hi)]
        allc = np.c_[allc[:, 0], allc[:, 1] + t * dy, allc[:, 2]]; tan, e_acr, e_side = _frame(allc)
        bl_src += f"; rear face moved onto the triangulated back arris (was off by {np.median(rear_gap):+.1f} mm median, {np.abs(rear_gap).max():.1f} max)"
meshes["BLEG_R"] = sweep(allc, e_acr, e_side, w_acr, w_side); meshes["BLEG_L"] = mirror(meshes["BLEG_R"])
report["back_leg"] = {"lower": "fitted (side face orthophoto; front edge good, rear edge rough)", "upper": "cloud (centreline + extents, mirrored L+R)",
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
# rim: blend the spline to the flat rim line near the outline so the edge is clean
dist = np.array([pg.exterior.distance(Point(p)) for p in pts2]); wgt = np.clip(dist / 25, 0, 1); zt = wgt * zt + (1 - wgt) * np.maximum(zt, zedge - 2)
zbm = seat_z(pts2[:, 1]) + 4 - P("seat_edge_thickness")
nP = len(pts2); V = np.r_[np.c_[pts2, zt], np.c_[pts2, zbm]]; F = list(T) + [[q[0] + nP, q[2] + nP, q[1] + nP] for q in T]
nb = len(outline); base = nP - nb
for i in range(nb):
    p, q = base + i, base + (i + 1) % nb; F += [[p, q, q + nP], [p, q + nP, p + nP]]
seat = trimesh.Trimesh(V, np.array(F), process=True); seat.fix_normals(); meshes["SEAT"] = seat
dish = float((seat_z(pts2[:, 1]) + 4 - zt).max())
report["seat"] = {"outline": "cloud (98th percentile half-width per station; front-edge scallops NOT modelled)", "surface": "cloud (polynomial surface even in x, mirrored L+R)",
                  "surface_fit_rms_mm": float(np.sqrt(np.mean(rs ** 2))), "n_surface_points": int(len(St)), "depth_y_mm": [y_back, y_front],
                  "half_width_mm": {"back": float(half[0]), "mid": float(half[len(half) // 2]), "front": float(half[-1])},
                  "max_scoop_below_rim_mm": dish, "rim_tilt_deg": float(np.degrees(np.arctan(0.155)))}

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

# ---------------------------------------------------------------- crest rail and arms from the overhead photos (parts/crest.json, parts/arms.json)
def grid_solid(top, bot, ns, nt):
    """closed solid from two (ns x nt x 3) grids of matching topology: top surface, bottom surface, four side strips"""
    T, B = np.asarray(top).reshape(-1, 3), np.asarray(bot).reshape(-1, 3); V = np.r_[T, B]; o = ns * nt; F = []
    idx = lambda i, j: i * nt + j
    for i in range(ns - 1):
        for j in range(nt - 1):
            a_, b_, c_, d_ = idx(i, j), idx(i + 1, j), idx(i + 1, j + 1), idx(i, j + 1)
            F += [[a_, b_, c_], [a_, c_, d_], [a_ + o, c_ + o, b_ + o], [a_ + o, d_ + o, c_ + o]]
    ring = [idx(i, 0) for i in range(ns)] + [idx(ns - 1, j) for j in range(1, nt)] + [idx(i, nt - 1) for i in range(ns - 2, -1, -1)] + [idx(0, j) for j in range(nt - 2, 0, -1)]
    for k in range(len(ring)):
        p, q = ring[k], ring[(k + 1) % len(ring)]; F += [[p, q + o, q], [p, p + o, q + o]]
    m = trimesh.Trimesh(V, np.array(F), process=True); m.fix_normals(); return m


TOPF = ROOT / "parts/crest.json", ROOT / "parts/arms.json"
if a.legacy or not all(f.exists() for f in TOPF):
    report["crest_arms_source"] = "legacy cloud crest and arms (v3)"
else:
    CJ = json.load(open(TOPF[0])); ev = lambda c, x: sum(ck * np.abs(x) ** (2 * k) for k, ck in enumerate(c))
    E = {k: CJ["edges"][k]["design"] for k in ("top_rear", "top_front", "bottom_front", "bottom_rear")}
    jx = (abs(CJ["joints"]["left"]["leg_inner_face_x"]["mm"]) + abs(CJ["joints"]["right"]["leg_inner_face_x"]["mm"])) / 2
    xo_ = (abs(CJ["joints"]["left"]["leg_outer_face_x"]["mm"]) + abs(CJ["joints"]["right"]["leg_outer_face_x"]["mm"])) / 2
    xs_ = np.linspace(-jx - 2, jx + 2, 89)       # 2 mm into each leg so the parts meet
    corner = lambda k: np.c_[xs_, ev(E[k]["y_even_poly"], xs_), ev(E[k]["z_even_poly"], xs_)]
    TR, TF, BF, BR = (corner(k) for k in ("top_rear", "top_front", "bottom_front", "bottom_rear"))
    tt = np.linspace(0, 1, 5)[None, :, None]
    top = TR[:, None] * (1 - tt) + TF[:, None] * tt; bot = BR[:, None] * (1 - tt) + BF[:, None] * tt
    meshes["CREST"] = grid_solid(top, bot, len(xs_), 5)
    # back-leg tops end flush with the crest's top arch (crest.json joints: "leg tops flush, arch carried over them")
    xl = (jx + xo_) / 2; sx = (ev(E["top_rear"]["z_even_poly"], xl + 1) - ev(E["top_rear"]["z_even_poly"], xl - 1)) / 2
    yr_, yf_ = ev(E["top_rear"]["y_even_poly"], xl), ev(E["top_front"]["y_even_poly"], xl); zr_, zf_ = ev(E["top_rear"]["z_even_poly"], xl), ev(E["top_front"]["z_even_poly"], xl)
    sy = (zf_ - zr_) / (yf_ - yr_); p0 = np.array([xl, yr_, zr_]); nrm = np.array([-sx, -sy, 1.0]); nrm /= np.linalg.norm(nrm)
    bl_top_before = float(meshes["BLEG_R"].vertices[:, 2].max())
    for k_, sg in (("BLEG_R", 1), ("BLEG_L", -1)):
        p_, n_ = p0 * [sg, 1, 1], nrm * [sg, 1, 1]
        try: meshes[k_] = meshes[k_].slice_plane(p_, -n_, cap=True)
        except Exception: meshes[k_] = meshes[k_].slice_plane(p_, -n_, cap=False)
    report["crest"] = {"source": "parts/crest.json (four arrises triangulated from overhead + rear photos; design = even polynomials)",
                       "span_between_legs_mm": float(2 * jx), "top_centre_z": float(ev(E["top_rear"]["z_even_poly"], 0)), "top_at_leg_centre_z": float(zr_),
                       "back_leg_top_cut": {"before_z_max": bl_top_before, "plane_point": p0.round(1).tolist(), "slope_dzdx": float(sx), "slope_dzdy": float(sy)}}
    # arms: design version (right arm; left = mirror)
    AJ = json.load(open(TOPF[1])); D_ = AJ["design"]; th = AJ["thickness"]["value_mm"]
    pin, pout = np.array(D_["inner_x_of_y"]["poly_in_(y-300)"]), np.array(D_["outer_x_of_y"]["poly_in_(y-300)"])
    pz, pzx, pf = np.array(D_["top_z_of_y"]["poly_in_(y-300)"]), np.array(D_["top_z_of_y"]["cross_slope_outer_minus_inner_poly"]), np.array(D_["front_y_of_x"]["poly"])
    y_back = min(D_["y_back"], 40.0)              # carried on into the back leg (the joint itself is not seen from above)
    ci_, co_ = D_["corners"]["front_inner"], D_["corners"]["front_outer"]; ns, nt = 70, 7
    S_, T_ = np.meshgrid(np.linspace(0, 1, ns), np.linspace(0, 1, nt), indexing="ij")
    yend = ci_[1] + T_ * (co_[1] - ci_[1]); Y = y_back + S_ * (yend - y_back)
    X = np.polyval(pin, Y - 300) + T_ * (np.polyval(pout, Y - 300) - np.polyval(pin, Y - 300))
    Y = np.where(S_ == 1, np.polyval(pf, X), Y)   # front row exactly on the design front line
    Z = np.polyval(pz, Y - 300) + (T_ - 0.5) * np.polyval(pzx, Y - 300)
    slope = np.arctan(np.polyval(np.polyder(pz), Y - 300)); Zb = Z - th / np.cos(slope)
    am = grid_solid(np.dstack([X, Y, Z]), np.dstack([X, Y, Zb]), ns, nt); meshes["ARM_R"] = am; meshes["ARM_L"] = mirror(am)
    # front-leg tops vs the arm underside
    fv = meshes["FLEG_R"].vertices; tp = fv[fv[:, 2] > fv[:, 2].max() - 15]; yc, xc = float(tp[:, 1].mean()), float(tp[:, 0].mean())
    zu = float(np.polyval(pz, yc - 300) - th / np.cos(np.arctan(np.polyval(np.polyder(pz), yc - 300))))
    fl = {"leg_top_z": float(fv[:, 2].max()), "arm_underside_z_at_leg": zu, "leg_top_xy": [round(xc, 1), round(yc, 1)],
          "arm_x_range_at_leg": [float(np.polyval(pin, yc - 300)), float(np.polyval(pout, yc - 300))]}
    if fl["leg_top_z"] > zu:
        su = np.polyval(np.polyder(pz), yc - 300); n_ = np.array([0, -su, 1.0]); n_ /= np.linalg.norm(n_); p_ = np.array([xc, yc, zu])
        for k_, sg in (("FLEG_R", 1), ("FLEG_L", -1)):
            try: meshes[k_] = meshes[k_].slice_plane(p_ * [sg, 1, 1], -n_, cap=True)
            except Exception: meshes[k_] = meshes[k_].slice_plane(p_ * [sg, 1, 1], -n_, cap=False)
        fl["action"] = "cut at the arm underside (it ran through the arm)"
    else: fl["action"] = f"left as traced: it stops {zu - fl['leg_top_z']:.1f} mm below the arm underside (assumed arm thickness {th} mm)"
    report["arm"] = {"source": "parts/arms.json design (triangulated top arrises of both arms, mirrored mean)", "y_range": [float(y_back), float(max(ci_[1], co_[1]))],
                     "back_extension": f"carried from y {D_['y_back']} back to {y_back} into the back leg (not seen)", "thickness_mm": th, "front_leg_top": fl}
    report["crest_arms_source"] = "parts/crest.json + parts/arms.json"

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
