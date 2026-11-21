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
ap.add_argument("--arm-slab", action="store_true", help="the old arm (model v20 and before): an assumed 25 mm slab square to the traced top, instead of the measured underside in parts/arm_underside.json")
a = ap.parse_args()
PRM = {  # sizes not (yet) measured from photos
    "rocker_width_across": (31.0, "tape", "IMG_1493 read 1.20 in at the rear tip, +-1/16; assumed constant along the rocker"),
    "fleg_thickness_across": (33.0, "cloud+tape", "cloud inner-face depth 29-35 mm; IMG_1495 read 1.27 in"),
    "bleg_thickness_across": (38.0, "cloud+tape", "cloud 32-40 mm; IMG_1494 read 1.34-1.6 in"),
    "arm_thickness": (25.0, "assumed", "not measurable yet; caliper A1-A3 will replace"),
    "seat_edge_thickness": (40.0, "fitted", "only used without parts/seat_edge.json (or --legacy): side-edge face traced 39-45 mm at the back, thinner to the front; constant here"),
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
# the two ends (parts/rocker_ends.json, tools/rocker_ends/): the tail thins to a slim rounded tip, the nose is cut to a round end. Each end's
# top and bot run from blend_u[0], where they equal the profile above, out to the landmark (the tail's tip, the nose's top corner).
rends = json.load(open(ROOT / "parts/rocker_ends.json"))["design"]; r_tail, r_nose = rends["tail"], rends["nose"]; mid = (U > r_tail["blend_u"][0]) & (U < r_nose["blend_u"][0])
# the bottom edge traced directly between the ends (parts/rocker_bottom.json, tools/rocker_bottom/): bottom v = mean_bot + dv(u), also on the
# tail end's bottom inside its blend zone (dv fades to 0 at u -400); dv is 0 outside its stations, so the top edge, the feet and the contact stay
rb_file = ROOT / "parts/rocker_bottom.json"; rbc = json.load(open(rb_file))["correction"] if rb_file.exists() else {"u": [0.0, 1.0], "dv_mm": [0.0, 0.0]}
bot_dv = lambda q: np.c_[q[:, 0], q[:, 1] + np.interp(q[:, 0], rbc["u"], rbc["dv_mm"], left=0.0, right=0.0)]
rbot = rbot + np.interp(U, rbc["u"], rbc["dv_mm"], left=0.0, right=0.0); r_tail_bot = bot_dv(np.array(r_tail["bot"])); r_nose_bot = bot_dv(np.array(r_nose["bot"]))
rock_poly = to_mean(np.r_[np.array(r_tail["top"])[::-1], np.c_[U, rtop][mid], np.array(r_nose["top"]), r_nose_bot[::-1][1:], np.c_[U, rbot][mid][::-1], r_tail_bot[:-1]])
meshes["ROCKER_R"] = extrude_side(rock_poly, 0, P("rocker_width_across"), +1); meshes["ROCKER_L"] = mirror(meshes["ROCKER_R"])
report["rocker"] = {"profile": "top fitted (face orthophoto, both sides averaged); bottom " + ("traced in single photos between the ends (parts/rocker_bottom.json), fitted where it agrees" if rb_file.exists() else "fitted"), "length_traced_mm": float(U[-1] - U[0]),
                    "ends": "triangulated (parts/rocker_ends.json: each end traced in 11 to 18 photos, left and right averaged)", "tail_tip_uv": r_tail["landmark_uv"], "nose_top_corner_uv": r_nose["landmark_uv"],
                    "tail_tip_to_nose_top_corner_mm": float(np.hypot(*(np.array(r_nose["landmark_uv"]) - r_tail["landmark_uv"]))), "length_overall_mm": float(np.ptp(rock_poly[:, 0])),
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
    pin_rep = {}; _cf = ROOT / "parts/crest.json"
    if _cf.exists() and not a.legacy:
        # the crest's top-rear arris was solved in y and z and runs on over the leg top, so at the leg it is a measured point on the leg's rear face;
        # above the side trace the rear only had the back-view arris (weak fore-aft). Ramp the rear line from the end of the side trace onto that point.
        _C = json.load(open(_cf)); _ev = lambda c_, x_: sum(ck * abs(x_) ** (2 * k) for k, ck in enumerate(c_)); _d = _C["edges"]["top_rear"]["design"]
        _xl = float(np.mean([abs(_C["joints"][s_][f_]["mm"]) for s_ in ("left", "right") for f_ in ("leg_inner_face_x", "leg_outer_face_x")]))
        y_tr, z_tr = float(_ev(_d["y_even_poly"], _xl)), float(_ev(_d["z_even_poly"], _xl)); gap = y_tr - float(np.interp(z_tr, z_, r_new))
        r_new = r_new + gap * np.clip((z_ - zR[-1]) / (z_tr - zR[-1]), 0, 1.2)
        pin_rep = {"point_xyz": [round(_xl, 1), round(y_tr, 1), round(z_tr, 1)], "rear_moved_at_top_mm": gap, "ramp_from_z": float(zR[-1]),
                   "note": "rear line pinned to the crest's top-rear arris at the leg centre (parts/crest.json); the arris slants across the leg top (about -179.0 at the inner face, -176.2 at the outer), the model's leg section does not"}
    one_board = {}
    if not a.legacy:
        # ONE BOARD (audit PR #12): the leg is one continuous piece of wood. Nothing is measured between the lower leg's lines (top z ~265) and the
        # side trace above the arm (z0 ~608); the stitching there (cubic rear bridge + linear ramp) put a 27 mm kink in the leg. Fit one smoothing
        # spline per outline through the measured stretches only, so the unmeasured band is bridged by the smoothest curve the measurements allow.
        from scipy.interpolate import make_smoothing_spline
        zlo_f = float(SFL["bleg_front_lo"]["z"][-1]); zlo_r = float(max(SFL["bleg_rearfar_lo"]["z"][-1], SFL["bleg_rear_lo"]["z"][-1]))
        def _board(yline, zlo, lam):
            meas = (z_ <= zlo) | (z_ >= z0); sp = make_smoothing_spline(z_[meas], yline[meas], lam=lam); y_ = sp(z_); r_ = (y_ - yline)[meas]
            return y_, {"measured_z": [[float(z_.min()), zlo], [z0, float(z_.max())]], "fit_rms_mm": float(np.sqrt(np.mean(r_ ** 2))), "fit_max_mm": float(np.abs(r_).max()),
                        "moved_in_gap_mm": [float((y_ - yline)[~meas].min()), float((y_ - yline)[~meas].max())]}
        lam_b = 2e3            # stiffness: residual on the measured stretches stays under the line tolerance (+-1 mm) while the gap carries no wiggle
        f_new, one_board["front"] = _board(f_new, zlo_f, lam_b); r_new, one_board["rear"] = _board(r_new, zlo_r, lam_b)
    allc = np.c_[allc[:, 0], (f_new + r_new) / 2, allc[:, 2]]; tan, e_acr, e_side = _frame(allc); w_side = (f_new - r_new) * np.abs(e_side[:, 1])
    inr = (z_ >= z0) & (z_ <= zR[-1])
    bl_up_src = (f"z {z0:.0f}-{zF[-1]:.0f}: front outline triangulated in side view from 4 cameras standing behind the leg on each side (solve residual 0.6 / 0.5 mm L / R); z {z0:.0f}-{zR[-1]:.0f}: rear edge traced in side view "
                 f"in 2 cameras standing in front of the leg on each side, depth held on the back outer arris (residual 0.45 / 0.7 mm); L and R averaged. Above z {zR[-1]:.0f} the rear follows the back-view arris, "
                 f"shifted to meet the side trace" + (f" and ramped onto the crest's top-rear arris at the leg top (moved {pin_rep['rear_moved_at_top_mm']:+.1f} mm there)" if pin_rep else "") + f"; z {zj:.0f}-{z0:.0f} (arm joint) is a linear ramp from the lower leg. Across-width still from the back view.")
    up_rep = {"front_moved_mm": [float(dF[inr].min()), float(dF[inr].max())], "rear_moved_mm": [float(dR[inr].min()), float(dR[inr].max())],
              "left_right_fore_aft_mm": {k: {"mean": SFL[k]["lr_diff_y_mean_mm"], "rms_about_mean": SFL[k]["lr_diff_y_rms_about_mean_mm"]} for k in ("bleg_front_hi", "bleg_rear_hi")},
              "width_fore_aft_mm": {f"z{int(z)}": float(np.interp(z, z_, f_new - r_new)) for z in (620, 700, 800, 900, 1000)},
              "width_square_to_leg_mm": {f"z{int(z)}": float(np.interp(z, z_, w_side)) for z in (620, 700, 800, 900, 1000)}, "crest_pin": pin_rep, "one_board": one_board}
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
# side edge between the legs: measured top arris (plan outline) and bottom arris (parts/seat_edge.json, tools/seat_edge_fit.py)
edge_rep = None; _ef = ROOT / "parts/seat_edge.json"
if _ef.exists() and not a.legacy:
    _E = json.load(open(_ef))["design"]; _y0, _y1 = _E["y_range"]; _pv = lambda k, y: np.polyval(_E[k]["poly_in_(y-250)"], np.clip(y, _y0, _y1) - 250.0)
    half_cloud = half.copy(); d_end = [float(_pv("top_half_width_of_y", yy) - np.clip(np.polyval(c_hw, yy), 150, 300)) for yy in (_y0, _y1)]
    # outside the measured range the cloud outline is kept, shifted by its mismatch at the end of the range and faded out over 60 mm
    fade = np.where(ys < _y0, np.clip(1 - (_y0 - ys) / 60, 0, 1) * d_end[0], np.where(ys > _y1, np.clip(1 - (ys - _y1) / 60, 0, 1) * d_end[1], 0.0))
    _in = (ys >= _y0) & (ys <= _y1); half = np.where(_in, _pv("top_half_width_of_y", ys), half_cloud + fade)
    edge_rep = {"source": "parts/seat_edge.json (top and bottom arris of the side edge triangulated on both sides, symmetric mean)", "measured_y_range": [_y0, _y1],
                "outline_minus_cloud_outline_mm": {"mean": float(np.mean((half - half_cloud)[_in])), "min": float(np.min((half - half_cloud)[_in])), "max": float(np.max((half - half_cloud)[_in]))},
                "outline_beyond_range": "cloud outline shifted by %+.1f mm (back) / %+.1f mm (front) at the end of the range, faded out over 60 mm" % tuple(d_end)}
# the front and back edges get a point every ~10 mm too: with only the two corner points the front wall's top edge was one straight line from corner to
# corner, bridging over the thigh hollows of the measured surface (seen as a flat horizon in the level photo 1491)
_fx = lambda h: np.linspace(h, -h, int(2 * h // 10) + 1)[1:-1]
front_pts = np.c_[_fx(half[-1]), np.full(len(_fx(half[-1])), y_front)]
# front edge in plan: measured (parts/seat_front.json, tools/seat_front_fit.py): scalloped, pommel point at the centre, hollows either side, corners forward again.
# The sides run on from the end of the measured side range (y 400) straight to the front corner (that stretch is hidden in the front-leg joint)
front_rep = None; _ff = ROOT / "parts/seat_front.json"; front_y = None
if _ff.exists() and edge_rep and not a.legacy:
    _F = json.load(open(_ff))["design"]; _fxy = np.array(_F["front_y_of_abs_x"]); _xcn, _ycn = float(_F["corner"]["abs_x"]), float(_F["corner"]["y"]); front_y = lambda x: np.interp(np.abs(x), _fxy[:, 0], _fxy[:, 1])
    _k = ys < _y1 - 1e-6; _h1 = float(_pv("top_half_width_of_y", _y1)); y_front_cloud = y_front; half_front_cloud = float(half[-1])
    ys = np.r_[ys[_k], np.linspace(_y1, _ycn, 15)]; half = np.r_[half[_k], np.linspace(_h1, _xcn, 15)]; y_front = float(_fxy[:, 1].max())
    _xf = np.linspace(_xcn, -_xcn, 2 * int(_xcn // 8) + 1)[1:-1]; front_pts = np.c_[_xf, front_y(_xf)]
    front_rep = {"source": "parts/seat_front.json (rolled front edge traced in 8 overhead photos, tube solve, symmetric mean)", "tol_mm": _F["tol_mm"], "pommel_tip_y": float(front_y(0.0)), "hollow": _F["hollow"],
                 "corner": [_xcn, _ycn], "was": "straight line at y %.1f from corner to corner (half-width %.1f)" % (y_front_cloud, half_front_cloud),
                 "front_minus_old_straight_line_mm": {"pommel": float(front_y(0.0) - y_front_cloud), "hollow": float(_fxy[:, 1].min() - y_front_cloud), "corner": float(_ycn - y_front_cloud)}}
# section of the front edge: measured (parts/seat_front_face.json, tools/seat_front_face_fit.py). The top edge is rolled over: the plan outline is the furthest-forward line of the roll,
# its top sits one radius behind and one radius above. Three rows of points carry it (top of the roll, 45 degrees, plan outline = top of the front face); the bottom of the face is the measured bottom arris
face_rep = None; _fc = ROOT / "parts/seat_front_face.json"; roll_pts = np.zeros((0, 2))
if _fc.exists() and front_rep and not a.legacy:
    _FD = json.load(open(_fc))["design"]; _rr = float(_FD["roll_radius_mm"]["value"]); _tz = np.array(_FD["top_of_roll_z_of_abs_x"]); _bzc = np.array(_FD["bottom_arris_z_of_abs_x_with_corner"])
    _q = _rr * (1 - np.sin(np.pi / 4)); roll_pts = np.r_[np.c_[_xf, front_y(_xf) - _q], np.c_[_xf, front_y(_xf) - _rr]]
    face_rep = {"source": "parts/seat_front_face.json (top of the rolled edge: 8 overhead + 6 level/low front photos in one tube solve; bottom arris: 9 front photos; symmetric mean)", "roll_radius_mm": _rr, "roll_radius_provenance": "assumed"}
# back edge: measured (parts/seat_back.json, tools/seat_back/). In plan a bow between the two back legs (furthest back on the centre line, meeting each leg flush with its rear face);
# in section the top arris, a flat back face leaning forward going down, the hard line, a flat 45 degree under-bevel (a lens: deepest on the centre line), the bottom arris.
# The side outline now stops at y 45, INSIDE the back leg's footprint, and runs straight to the end of the bow at |x| 192 (inside the leg's inner face at 187.3-188.3): that
# corner lies wholly inside the leg, which cuts it away (joinery.py), so nothing of the seat is left behind or outboard of the leg. Before: one straight vertical edge at the cloud's 1st percentile, running on behind the legs
back_rep = None; _bkf = ROOT / "parts/seat_back.json"; back_pts = np.c_[-_fx(half[0]), np.full(len(_fx(half[0])), y_back)]; y_grid0 = y_back
if _bkf.exists() and edge_rep and not a.legacy:
    _BK = json.load(open(_bkf))["design"]; _bx = np.array(_BK["abs_x"]); _bt = lambda k, c: (lambda v: (lambda x: np.interp(np.abs(x), _bx, v)))(np.array(_BK[k][c]))
    b_yT, b_zT, b_yH, b_zH, b_yB = _bt("top_arris", "y"), _bt("top_arris", "z"), _bt("hard_line", "y"), _bt("hard_line", "z"), _bt("bottom_arris", "y"); _xtip = float(_BK["lens_tip_abs_x"]); _xj, _ys0 = 192.0, 45.0
    _k = ys > _ys0 + 2.0; _half_back_cloud = float(half[0]); half = np.r_[np.interp(_ys0, ys, half), half[_k]]; ys = np.r_[_ys0, ys[_k]]
    _xb = np.linspace(-_xj, _xj, 2 * int(_xj // 8) + 1); back_pts = np.c_[_xb, b_yT(_xb)]
    y_grid0 = y_back - 20.0                                   # the 10 mm grid keeps its old phase (the surface in front of the back edge is triangulated as before)
    back_rep = {"source": "parts/seat_back.json (top arris, hard line and bottom arris of the back edge triangulated in 11, 7 and 10 photos from behind; symmetric solves)",
                "was": "straight vertical edge at y %.1f (1st percentile of the cloud), half-width %.1f, running on behind the back legs" % (y_back, _half_back_cloud),
                "top_arris_y": {f"x{int(x)}": float(b_yT(x)) for x in (0, 60, 120, 150, 180)}, "top_arris_minus_old_straight_edge_mm": {f"x{int(x)}": float(b_yT(x) - y_back) for x in (0, 60, 120, 150, 180)},
                "corner": "side outline stops at y %.0f inside the back leg and runs straight to the end of the bow at |x| %.0f (inside the leg); the leg cuts the corner" % (_ys0, _xj), "lens_tip_abs_x": _xtip}
    y_back = float(b_yT(0.0))
outline = np.r_[np.c_[half, ys], front_pts, np.c_[-half[::-1], ys[::-1]], back_pts]
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
pg = Polygon(outline); gx, gy = np.meshgrid(np.arange(-290, 291, 10), np.arange(y_grid0, y_front + 1, 10))
from shapely.geometry import Point
ins = np.array([pg.contains(Point(p)) for p in np.c_[gx.ravel(), gy.ravel()]])
if face_rep: ins &= (front_y(gx.ravel()) - gy.ravel()) > _rr + 5          # no grid points inside the roll
pts2 = np.r_[np.c_[gx.ravel(), gy.ravel()][ins], roll_pts, outline]
# keep the triangles inside the outline. The test is the centroid strictly inside the polygon: with a 0.5 mm allowance (as before) part of the thin fan Delaunay puts OUTSIDE a
# hollow of the scalloped front edge was kept, which left open and three-faced edges there (the seat was not watertight, model audit PR #12)
tri = Delaunay(pts2); _sx = pts2[tri.simplices]; cent = _sx.mean(1); _e1, _e2 = _sx[:, 1] - _sx[:, 0], _sx[:, 2] - _sx[:, 0]; _ar = 0.5 * np.abs(_e1[:, 0] * _e2[:, 1] - _e1[:, 1] * _e2[:, 0])
keep = np.array([pg.contains(Point(c)) for c in cent]) & (_ar > 1e-6); T = tri.simplices[keep]
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
    if edge_rep:
        # the strip between the dotted region and the outline (|x| > the dots' limit): the shifted cloud polynomial falls away too fast there, so it is
        # tilted to reach the measured top-arris height at the outline (parts/seat_edge.json); nothing changes inside the dotted region
        _yy = pts2[:, 1]; _hw = np.maximum(np.interp(_yy, ys, half), mx1 + 1.0); _hc = np.interp(np.clip(_yy, _y0, _y1), ys, half); _yc = np.clip(_yy, max(_y0, my0), min(_y1, my1)); _xm = np.minimum(_hc, mx1)
        _old_edge = spl.ev(_hc, _yc) + tps(_xm, _yc) - spl.ev(_xm, _yc); _fy = np.clip(1 - np.maximum(_y0 - _yy, _yy - _y1) / 60, 0, 1)
        _t = np.clip((np.abs(pts2[:, 0]) - mx1) / (_hw - mx1), 0, 1); _dz = _fy * _t * (_pv("top_z_of_y", _yc) - _old_edge); zt = zt + _dz
        edge_rep["strip_beyond_dots_raised_mm"] = {"max": float(_dz.max()), "min": float(_dz.min()), "note": "top surface outside the dotted region tilted to meet the measured top arris at the outline"}
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
if face_rep:
    _nR = len(_xf); _iB = int(ins.sum()) + np.arange(_nR); _iC = _iB + _nR; _iF = len(pts2) - len(outline) + len(half) + np.arange(_nR); _px, _py = pts2[:, 0], pts2[:, 1]
    # top of the roll: the surface is moved to the measured height on the line one radius behind the plan outline; the correction fades out over 30 mm behind that line.
    # Outside the solved range (|x| under 8, over 262) the correction found at the end of the range is held
    _k = (_xf >= _tz[0, 0]) & (_xf <= _tz[-1, 0]); _o = np.argsort(_xf[_k]); _dzin = (np.interp(_xf[_k], _tz[:, 0], _tz[:, 1]) - zt[_iC][_k])[_o]; _dzx = lambda x: np.interp(np.abs(x), _xf[_k][_o], _dzin)
    _zc_before = zt[_iC].copy(); zt = zt + np.clip(1 - np.maximum(front_y(_px) - _rr - _py, 0) / 30.0, 0, 1) * _dzx(_px)
    zt[_iB] = zt[_iC] - _q; zt[_iF] = zt[_iC] - _rr
    # front corners: the corner point and the side arris just behind it come down with the roll (assumed: the horn's end is rounded over, not traced)
    _so = np.arange(len(pts2) - len(outline), len(pts2)); _sd = np.setdiff1d(_so, _iF); _cd = _ycn - _py[_sd]; _cm = (_cd < 16) & (_py[_sd] > _y1)
    zt[_sd[_cm]] -= _rr * (1 - _cd[_cm] / 16.0)
    face_rep["top_of_roll_moved_mm"] = {"note": "measured top of the roll minus the surface the model had on that line (seat/surface.json carried to the edge)", "mean": float(_dzin.mean()), "min": float(_dzin.min()), "max": float(_dzin.max()),
                                        "at_x": {f"x{int(round(x))}": float(_dzx(x)) for x in (8, 40, 80, 130, 180, 230, 260)}, "fades_out_over_mm_behind_the_roll": 30}
if back_rep:
    # top of the back edge = the measured top arris. Behind the dotted region (seat/surface.json starts at y 64) the surface was the cloud polynomial carried back, which climbed
    # 16 mm toward the back edge on the centre line (the slats' feet stand there and pulled the fit up). Now: STRAIGHT in y from the measured surface at the dots' limit to the
    # measured top arris (a ruled strip between two measured lines; nothing changes inside the dotted region)
    _ib = len(pts2) - len(back_pts) + np.arange(len(_xb)); _zb0 = zt[_ib].copy(); _r = _xb >= 0; _dzb = lambda x: np.interp(np.minimum(np.abs(x), _xj), _xb[_r], (b_zT(_xb) - _zb0)[_r])
    _ax = np.minimum(np.abs(pts2[:, 0]), _xj); _py_ = pts2[:, 1]
    if seat_src:
        _m = _py_ < my0; _zl = tps(np.clip(pts2[_m, 0], mx0, mx1), np.full(int(_m.sum()), my0)); zt[_m] = b_zT(_ax[_m]) + (_zl - b_zT(_ax[_m])) * np.clip((_py_[_m] - b_yT(_ax[_m])) / (my0 - b_yT(_ax[_m])), 0, 1)
    else: zt = zt + np.clip(1 - (_py_ - b_yT(_ax)) / 60.0, 0, 1) * _dzb(pts2[:, 0])
    back_rep["top_behind_dots"] = {"note": "top surface between the back edge and the dotted region (y %.0f): straight in y from the measured top arris to the measured surface at the dots' limit (fitted: no dots there). "
                                           "moved_at_edge_mm = measured top arris z minus the old cloud polynomial read ON THE NEW EDGE LINE (the old surface was an extrapolation there, pulled up by the slats' feet)" % (my0 if seat_src else 0.0), "moved_at_edge_mm": {f"x{int(x)}": float(_dzb(np.array([float(x)]))[0]) for x in (0, 60, 120, 150, 180)},
                                   "slope_in_y": {f"x{int(x)}": float((tps(np.array([float(x)]), np.array([my0]))[0] - b_zT(x)) / (my0 - b_yT(x))) for x in (0, 60, 120, 150, 180)} if seat_src else None}
scoop_rep = None; scoop_h = None; _sf = ROOT / "parts/seat_scoop.json"
zbm = seat_z(pts2[:, 1]) + 4 - P("seat_edge_thickness")     # underside: NOT measured; this plane matched the lower edge in side photo 1507 by eye
xbm = pts2[:, 0].copy()
if edge_rep:
    # underside = the plane through the two measured bottom arrises (flat across: assumed); the side face leans under, so the underside is narrower than
    # the top by the measured ratio at each y (front and back faces stay vertical)
    zbm_old = zbm.copy(); zbm = np.polyval(_E["bottom_z_of_y"]["poly_in_(y-250)"], pts2[:, 1] - 250.0); _top = np.interp(pts2[:, 1], ys, half)
    # bottom half-width: measured in the range; in front of it the measured straight line is carried on for 60 mm (in the level photo 1491 the bottom arris runs
    # straight on to the front leg), never closer than 2 mm to the top outline; behind the range the ratio at its end is held
    _bh = np.where(pts2[:, 1] > _y1, np.minimum(np.polyval(_E["bottom_half_width_of_y"]["poly_in_(y-250)"], np.minimum(pts2[:, 1], _y1 + 60) - 250.0), _top - 2.0),
                   _top * _pv("bottom_half_width_of_y", pts2[:, 1]) / _pv("top_half_width_of_y", pts2[:, 1]))
    # under-bevel of the side edge (parts/seat_scoop.json, tools/seat_scoop/): the edge face is VERTICAL from the plan outline down to the hard line; from there a flat bevel
    # runs in and down to the underside. The hard line's height above the underside is a lens: most at mid-length, nothing at the legs (there the edge face is the full thickness).
    # This replaces the single straight wall from top arris to bottom arris above (a chord across the corner at the hard line)
    if _sf.exists():
        _SD = json.load(open(_sf))["design"]; _gt = _SD["hard_line_height_above_underside_of_y"]; _gy, _gh = np.array(_gt["y"]), np.array(_gt["height_mm"]); _bev = np.radians(_SD["bevel_angle_deg"]["value"])
        scoop_h = lambda y: np.interp(y, _gy, _gh, left=0.0, right=0.0); _bh_old = _bh.copy(); _bh = _top - scoop_h(pts2[:, 1]) / np.tan(_bev)
        _so_ = np.arange(len(pts2) - len(outline), len(pts2))[:len(half)]; _yy_ = pts2[_so_, 1]; _m_ = (_yy_ >= _y0) & (_yy_ <= _y1)
        scoop_rep = {"source": "parts/seat_scoop.json (hard line and bottom arris triangulated on both side edges: right 14 and 8 photos, left 12 and 7; design = left/right mean, built symmetric)", "y_range": [float(_gy[0]), float(_gy[-1])],
                     "max_height_of_hard_line_above_underside_mm": float(_gh.max()), "bevel_angle_deg": float(np.degrees(_bev)), "max_bevel_run_mm": float(_gh.max() / np.tan(_bev)), "edge_face": "vertical from the plan outline to the hard line",
                     "bottom_half_width_minus_old_straight_wall_mm": {f"y{int(y)}": float(np.interp(y, _yy_, (_bh - _bh_old)[_so_])) for y in (110, 150, 200, 250, 300, 350, 400)},
                     "outside_y_range": "edge face vertical for the full thickness (was: leaning under at the ratio found at the end of the measured range)"}
    _ratio = _bh / _top
    if front_y is not None:      # the front face is vertical (tape dots on it sit on the plan outline within about 1 mm): the side lean fades out over the last 40 mm before the front edge
        _ratio = 1 + (_ratio - 1) * np.clip((front_y(pts2[:, 0]) - pts2[:, 1]) / 40.0, 0, 1)
    xbm = pts2[:, 0] * _ratio
    if face_rep:
        # bottom of the front face = the measured bottom arris. It stands 2-4 mm above the side-arris plane carried forward: the underside is raised by that much at the front, fading out
        # over 60 mm behind the front edge (ASSUMED shape; the underside itself is not measured). Beyond |x| 240 the arris rounds up into the horn's end: that extra fades out over 25 mm
        _fya = front_y(_px); _pl = np.polyval(_E["bottom_z_of_y"]["poly_in_(y-250)"], _fya - 250.0); _ax = np.abs(_px)
        _g = np.interp(np.minimum(_ax, 240.0), _bzc[:, 0], _bzc[:, 1]) - np.polyval(_E["bottom_z_of_y"]["poly_in_(y-250)"], front_y(np.minimum(_ax, 240.0)) - 250.0)
        _e = np.interp(_ax, _bzc[:, 0], _bzc[:, 1]) - _pl - _g; _back = _fya - _py
        zbm = zbm + np.clip(1 - _back / 60.0, 0, 1) * _g + np.clip(1 - _back / 25.0, 0, 1) * np.where(_ax > 240, _e, 0.0)
        face_rep["underside_raised_at_front_mm"] = {"note": "measured bottom arris minus the side-arris plane carried forward; fades out over 60 mm behind the front edge (assumed)", "min": float(_g[_iF].min()), "max": float(_g[_iF].max())}
        face_rep["bottom_corner_extra_mm"] = {"note": "beyond |x| 240 the bottom arris rounds up into the end of the front corner; extra rise over the line above, fades out over 25 mm behind the front edge (assumed)", "at_corner": float(np.interp(_xcn, _bzc[:, 0], _bzc[:, 1]) - np.interp(240.0, _bzc[:, 0], _bzc[:, 1]))}
    edge_rep["underside_moved_mm"] = {f"y{int(y)}": float(np.polyval(_E["bottom_z_of_y"]["poly_in_(y-250)"], y - 250.0) - (seat_z(y) + 4 - P("seat_edge_thickness"))) for y in (100, 300, 500)}
    edge_rep["min_thickness_mm"] = float((zt - zbm).min()); _o = pts2[-len(outline):]; _s = (_o[:, 1] >= _y0) & (_o[:, 1] <= _y1)
    edge_rep["model_top_at_outline_minus_measured_top_arris_z_mm"] = {"mean": float(np.mean((zt[-len(outline):] - _pv("top_z_of_y", _o[:, 1]))[_s])), "min": float(np.min((zt[-len(outline):] - _pv("top_z_of_y", _o[:, 1]))[_s])), "max": float(np.max((zt[-len(outline):] - _pv("top_z_of_y", _o[:, 1]))[_s]))}
    _r = _o[:, 0] > 0; _k = np.argsort(_o[_r, 1]); edge_rep["top_at_outline_by_y"] = {f"y{int(y)}": {"model_z": float(np.interp(y, _o[_r, 1][_k], zt[-len(outline):][_r][_k])), "measured_arris_z": float(_pv("top_z_of_y", y)), "half_width": float(_pv("top_half_width_of_y", y))} for y in (110, 160, 210, 260, 310, 360, 400)}
ybm = pts2[:, 1].copy()
if back_rep:
    # underside at the back: the bottom arris sits IN FRONT of the top arris (back face leaning forward + the under-bevel: 19.2 mm on the centre line). The underside's points are moved
    # forward by that much at the edge, fading out over 60 mm (40 mm at the legs), and stay on the underside plane (the measured bottom arris is on that plane within 0.5 mm)
    _ax = np.minimum(np.abs(pts2[:, 0]), _xj); _sh = (b_yB(_ax) - b_yT(_ax)) * np.clip(1 - (pts2[:, 1] - b_yT(_ax)) / np.interp(_ax, [150.0, _xj], [60.0, 40.0]), 0, 1); ybm = pts2[:, 1] + _sh
    _pzb = _E["bottom_z_of_y"]["poly_in_(y-250)"]; zbm = zbm + np.polyval(_pzb, ybm - 250.0) - np.polyval(_pzb, pts2[:, 1] - 250.0)
    back_rep["underside_edge_in_front_of_top_arris_mm"] = {f"x{int(x)}": float(b_yB(x) - b_yT(x)) for x in (0, 60, 120, 150, 180)}
nP = len(pts2); V = np.r_[np.c_[pts2, zt], np.c_[xbm, ybm, zbm]]; F = list(T) + [[q[0] + nP, q[2] + nP, q[1] + nP] for q in T]
nb = len(outline); base = nP - nb
# walls: top ring -> middle ring -> bottom ring. The middle ring is the hard line along the two sides (plan outline x, underside z + lens height). Beyond the tips of the lens it
# stays on the wall 0.3 mm above the bottom arris (the hard line runs out INTO the bottom arris; a middle ring that jumped to half height there made one long sliver triangle on the
# 46 degree plane at each tip, drawn as a stray edge on the overlays). On the front and back edges it is halfway down the wall (one flat face as before)
Vm = 0.5 * (V[base:nP] + V[base + nP:2 * nP])
if scoop_rep:
    _oi = np.arange(nb); _side = (_oi < len(half)) | ((_oi >= len(half) + len(front_pts)) & (_oi < 2 * len(half) + len(front_pts))); _hh = scoop_h(outline[:, 1])
    _zb_ = V[base + nP:2 * nP, 2]; _zt_ = V[base:nP, 2]; _k = _side & (_hh > 0.3); Vm[_k] = np.c_[outline[_k, 0], outline[_k, 1], _zb_[_k] + np.minimum(_hh[_k], 0.8 * (_zt_ - _zb_)[_k])]
    _n = _side & ~_k; _Vt, _Vb = V[base:nP], V[base + nP:2 * nP]; Vm[_n] = _Vb[_n] + (_Vt[_n] - _Vb[_n]) * (0.3 / np.maximum(_zt_ - _zb_, 1.0))[_n, None]
    scoop_rep["wall_points_on_the_hard_line"] = int(_k.sum()); scoop_rep["edge_face_height_mm"] = {f"y{int(y)}": float(np.interp(y, outline[:len(half), 1], (_zt_ - Vm[:, 2])[:len(half)])) for y in (110, 150, 200, 250, 300, 350, 400)}
if back_rep:
    # back edge: the middle ring is the measured hard line inside the lens; beyond its tips 0.3 mm above the bottom arris, as on the sides
    _bi = nb - len(back_pts) + np.arange(len(back_pts)); _x = outline[_bi, 0]; _Vt, _Vb = V[base:nP][_bi], V[base + nP:2 * nP][_bi]; _lens = (np.abs(_x) < _xtip) & (b_zH(_x) - _Vb[:, 2] > 0.3)
    Vm[_bi] = np.where(_lens[:, None], np.c_[_x, b_yH(_x), b_zH(_x)], _Vb + (_Vt - _Vb) * (0.3 / np.maximum(_Vt[:, 2] - _Vb[:, 2], 1.0))[:, None])
    _c = int(np.argmin(np.abs(_x) + 1e3 * ~_lens)); _f = _Vt[_c] - Vm[_bi][_c]; _g = Vm[_bi][_c] - _Vb[_c]
    back_rep["section_on_centre_line"] = {"top_arris_yz": _Vt[_c, 1:].tolist(), "hard_line_yz": Vm[_bi][_c, 1:].tolist(), "bottom_arris_yz": _Vb[_c, 1:].tolist(), "back_face_lean_deg": float(np.degrees(np.arctan2(-_f[1], _f[2]))), "back_face_height_mm": float(np.hypot(_f[1], _f[2])),
                                          "bevel_angle_deg": float(np.degrees(np.arctan2(_g[2], -_g[1]))), "bevel_width_mm": float(np.hypot(_g[1], _g[2]))}
    back_rep["wall_points_on_the_hard_line"] = int(_lens.sum()); back_rep["model_top_at_edge_minus_measured_top_arris_z_mm"] = float(np.abs(_Vt[:, 2] - b_zT(_x)).max())
V = np.r_[V, Vm]; mid0 = 2 * nP
for i in range(nb):
    j = (i + 1) % nb; p, q, pm, qm = base + i, base + j, mid0 + i, mid0 + j; F += [[p, q, qm], [p, qm, pm], [pm, qm, q + nP], [pm, q + nP, p + nP]]
seat = trimesh.Trimesh(V, np.array(F), process=True); seat.fix_normals(); meshes["SEAT"] = seat; seat_closed = bool(seat.is_watertight and seat.is_winding_consistent)
dish = float(((zrim if seat_src else zedge) - zt).max())
report["seat"] = {"outline": "cloud (98th percentile half-width per station; front-edge scallops NOT modelled)", "surface": "cloud (polynomial surface even in x, mirrored L+R)",
                  "surface_fit_rms_mm": float(np.sqrt(np.mean(rs ** 2))), "n_surface_points": int(len(St)), "depth_y_mm": [y_back, y_front],
                  "half_width_mm": {"back": float(half[0]), "mid": float(half[len(half) // 2]), "front": float(half[-1])},
                  "max_scoop_below_rim_mm": dish, "rim_tilt_deg": float(np.degrees(np.arctan(0.155)))}
report["seat"]["mesh_closed"] = seat_closed; report["seat"]["mesh_volume_cm3"] = float(abs(seat.volume)) / 1000.0 if seat_closed else None
if seat_src:
    report["seat"].update(seat_src); report["seat"]["rim_tilt_deg"] = float(np.degrees(np.arctan(np.polyfit(ry, rz, 1)[0])))
    report["seat"]["underside"] = "assumed plane (z = 342 + 0.155 y - edge thickness); checked by eye against the lower edge in IMG_1507 only"
    _e = np.abs(np.abs(pts2[:, 0]) - 240) < 12
    report["seat"]["thickness_near_edge_mm"] = {f"y{int(y)}": float(np.median((zt - zbm)[_e & (np.abs(pts2[:, 1] - y) < 25)])) for y in (100, 300, 500)}
if edge_rep:
    report["seat"]["outline"] = "sides y %.0f-%.0f: triangulated top arris, L+R mean (+-1.5 mm); front, back and corners: cloud (98th percentile half-width per station; the front and back edges are straight in plan, their top follows the surface height)" % (_y0, _y1)
if front_rep:
    report["seat"]["outline"] = ("sides y %.0f-%.0f: triangulated top arris, L+R mean (+-1.5 mm); front edge: triangulated rolled edge, L+R mean (+-%.0f mm; parts/seat_front.json), scalloped in plan; "
                                 "side from y %.0f to the front corner: straight (hidden in the leg joint); back edge and back corners: cloud, straight in plan") % (_y0, _y1, front_rep["tol_mm"], _y1)
if edge_rep and "ends" in json.load(open(_ef)):   # report text only: the side outline's two extrapolated ends checked against the photos (PR #30)
    _en = json.load(open(_ef))["ends"]; edge_rep["ends_check"] = {"provenance": _en["provenance"], "what": _en["what"], "hidden": _en["hidden"]}
    report["seat"]["outline"] += "; side outline toward the back leg (y 81-110) and toward the front leg (y 400-435): extrapolated, then %s (parts/seat_edge.json ends)" % _en["provenance"]
if front_rep:
    _o = pts2[-len(outline):]; _fr = np.abs(_o[:, 1] - front_y(_o[:, 0])) < 1e-6; _zf = zt[-len(outline):]
    front_rep["top_z_along_front_edge"] = {f"x{int(x)}": float(np.interp(x, _o[_fr, 0][::-1], _zf[_fr][::-1])) for x in (0, 40, 80, 130, 180, 230, 260)}
    front_rep["front_edge_height_top_to_underside_mm"] = {f"x{int(x)}": float(np.interp(x, _o[_fr, 0][::-1], (_zf - zbm[-len(outline):])[_fr][::-1])) for x in (0, 40, 80, 130, 180, 230, 260)}
    report["seat"]["front_edge"] = front_rep; report["seat"]["depth_y_mm"] = [y_back, y_front]
if face_rep:
    _k = np.argsort(_xf); _at = lambda v, x: float(np.interp(x, _xf[_k], v[_k])); _X = (0, 40, 80, 130, 180, 230, 260)
    front_rep["top_z_along_front_edge"] = {f"x{x}": _at(zt[_iC], x) for x in _X}; front_rep["top_z_along_front_edge_was"] = {f"x{x}": _at(_zc_before, x) for x in _X}
    front_rep["front_edge_height_top_to_underside_mm"] = {f"x{x}": _at(zt[_iC] - zbm[_iF], x) for x in _X}
    face_rep["bottom_of_front_face_z"] = {f"x{x}": _at(zbm[_iF], x) for x in _X}; face_rep["top_of_front_face_z"] = {f"x{x}": _at(zt[_iF], x) for x in _X}
    face_rep["face"] = "vertical (measured lean of the bottom arris against the top outline is within +-2 mm for |x| < 240)"; face_rep["min_height_of_flat_face_below_the_roll_mm"] = float((zt - zbm)[_iF].min())
    _nf = np.setdiff1d(np.arange(len(pts2)), np.r_[_iF, _iB]); edge_rep["min_thickness_mm"] = float((zt - zbm)[_nf].min())
    report["seat"]["outline"] = report["seat"]["outline"].replace("scalloped in plan;", "scalloped in plan, rolled over (radius %.0f assumed), top height and bottom arris triangulated (parts/seat_front_face.json);" % _rr)
    report["seat"]["front_face"] = face_rep
if edge_rep:
    report["seat"]["underside"] = "plane through the two triangulated bottom arrises of the side edge (+-2.5 mm at the edge; flat across is ASSUMED, no measurement between them)"
    report["seat"]["side_edge"] = edge_rep
    if scoop_rep:
        report["seat"]["side_edge_scoop"] = scoop_rep
    if back_rep:
        report["seat"]["outline"] = report["seat"]["outline"].replace("back edge and back corners: cloud, straight in plan", "back edge: triangulated bow between the back legs, L+R mean (+-1.6 mm; parts/seat_back.json); behind |x| 192 the outline closes inside the legs").replace("front, back and corners: cloud", "back edge: triangulated bow (parts/seat_back.json); front and corners: cloud"); report["seat"]["back_edge"] = back_rep; report["seat"]["depth_y_mm"] = [y_back, y_front]
        report["seat"]["underside"] = "plane through the triangulated bottom arrises of the side edge (+-2.5 mm at the edge); flat across: not measured, but it mirrors the room without distortion in IMG_1492"

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
    UJ = None
    if not a.arm_slab:
        # underside from parts/arm_underside.json: drops of the outer and inner bottom arrises below the OUTER top arris, straight across between them
        UJ = json.load(open(ROOT / "parts/arm_underside.json"))["design"]; uy = np.array(UJ["y"])
        hu = lambda y, t: np.interp(y, uy, UJ["h_inner_mm"]) + t * (np.interp(y, uy, UJ["h_outer_mm"]) - np.interp(y, uy, UJ["h_inner_mm"]))
        zb = lambda x, y: np.polyval(pz, y - 300) + 0.5 * np.polyval(pzx, y - 300) - hu(y, (x - np.polyval(pin, y - 300)) / (np.polyval(pout, y - 300) - np.polyval(pin, y - 300)))
        Zb = np.polyval(pz, Y - 300) + 0.5 * np.polyval(pzx, Y - 300) - hu(Y, T_)      # outer top arris z minus the drop at this point across
    else:
        slope = np.arctan(np.polyval(np.polyder(pz), Y - 300)); Zb = Z - th / np.cos(slope)
        zb = lambda x, y: np.polyval(pz, y - 300) - th / np.cos(np.arctan(np.polyval(np.polyder(pz), y - 300)))
    am = grid_solid(np.dstack([X, Y, Z]), np.dstack([X, Y, Zb]), ns, nt); meshes["ARM_R"] = am; meshes["ARM_L"] = mirror(am)
    # front-leg tops vs the arm underside
    fv = meshes["FLEG_R"].vertices; tp = fv[fv[:, 2] > fv[:, 2].max() - 15]; yc, xc = float(tp[:, 1].mean()), float(tp[:, 0].mean())
    zu = float(zb(xc, yc))
    fl = {"leg_top_z": float(fv[:, 2].max()), "arm_underside_z_at_leg": zu, "leg_top_xy": [round(xc, 1), round(yc, 1)],
          "arm_x_range_at_leg": [float(np.polyval(pin, yc - 300)), float(np.polyval(pout, yc - 300))]}
    if fl["leg_top_z"] > zu:
        if UJ: su = float(zb(xc, yc + 1) - zb(xc, yc - 1)) / 2; sx_ = float(zb(xc + 1, yc) - zb(xc - 1, yc)) / 2      # the underside's own slopes at the leg
        else: su = np.polyval(np.polyder(pz), yc - 300); sx_ = 0.0
        n_ = np.array([-sx_, -su, 1.0]); n_ /= np.linalg.norm(n_); p_ = np.array([xc, yc, zu])
        for k_, sg in (("FLEG_R", 1), ("FLEG_L", -1)):
            try: meshes[k_] = meshes[k_].slice_plane(p_ * [sg, 1, 1], -n_, cap=True)
            except Exception: meshes[k_] = meshes[k_].slice_plane(p_ * [sg, 1, 1], -n_, cap=False)
        fl["action"] = "cut at the arm underside (it ran through the arm)"
    else: fl["action"] = f"left as traced: it stops {zu - fl['leg_top_z']:.1f} mm below the arm underside" + ("" if UJ else f" (assumed arm thickness {th} mm)")
    report["arm"] = {"source": "parts/arms.json design (triangulated top arrises of both arms, mirrored mean)", "y_range": [float(y_back), float(max(ci_[1], co_[1]))],
                     "back_extension": f"carried from y {D_['y_back']} back to {y_back} into the back leg (not seen)", "front_leg_top": fl,
                     **({"underside": "parts/arm_underside.json design (outer/inner bottom arrises traced on side photos of both arms, left/right mean)",
                         "thickness_vertical_outer_mm": {str(y): round(float(np.interp(y, uy, UJ["h_outer_mm"])), 1) for y in (40, 100, 200, 300, 400, 500)},
                         "thickness_vertical_inner_mm": {str(y): round(float(np.interp(y, uy, UJ["h_inner_mm"])), 1) for y in (40, 100, 200, 300, 400, 500)}} if UJ else {"thickness_mm": th})}
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
