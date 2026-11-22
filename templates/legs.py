"""USAGE: tools/py.sh templates/legs.py [--model parts/model_v24.glb] [--shapes parts/model_v24_shapes.glb] [--out templates/out]
                 [--geom-json templates/out/legs_geom.json]
Front leg and back leg side-profile templates, 1:1, from the model the build actually makes (model v24: tools/build_model.py legs from
parts/side_frame*.json and parts/back_legs.json, back leg as one board PR #14/#16, joinery PR #17, arm Domino PR #18, feet PR #19,
rear Dominos PR #22, front Domino PR #24, crest pin PR #5). The model legs are left/right mirrors, so one template per leg, flipped.
Drawing frame per leg: the plane fitted to the RIGHT leg's outer and inner faces (n outboard); v = the chair's up direction in that
plane, v = 0 at the table (floor); u = forward in that plane, shifted so the rearmost point of the outline is u = 0. Shown: the right
leg's outer face, front to the right. CUT = the leg's outline seen square to its face (silhouette of the joined part: foot cut to the
rocker, top cut to the crest / arm). REF = the outer-face and inner-face outlines (sections 0.8 mm inside each face) where they differ.
MARK = joints taken from the joined model: contact faces with seat, arm, crest and rocker (distance < 1 mm between the parts' surfaces)
and every Domino mortise (Domino solid inside the traced leg), centre crossed.
Writes <out>/legs_front_*, <out>/legs_back_* (tiled Letter PDF, full 1:1 PDF, R12 DXF, preview PNG) and a geometry json used by
templates/check_legs_overlay.py. Tiny compute (< 300 MB, a few seconds)."""
import json, argparse, subprocess, sys, os, numpy as np
import trimesh
from scipy.spatial import cKDTree
from shapely.geometry import Polygon, MultiPoint, LineString, Point
from shapely.ops import unary_union
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tplkit as K
from tplkit import fmt, frac32

ap = argparse.ArgumentParser()
ap.add_argument("--model", default="parts/model_v24.glb"); ap.add_argument("--shapes", default="parts/model_v24_shapes.glb")
ap.add_argument("--params", default="parts/model_v24_params.json"); ap.add_argument("--joinery", default="parts/model_v24_joinery.json")
ap.add_argument("--out", default="templates/out"); ap.add_argument("--geom-json", default=None); ap.add_argument("--rev", default=None)
a = ap.parse_args()
np.random.seed(7)

def ghash(p):
    try: return subprocess.run(["git", "log", "-1", "--format=%h", "--", p], capture_output=True, text=True).stdout.strip() or "uncommitted"
    except Exception: return "?"
REV = a.rev or ghash(a.model)
MODEL = os.path.basename(a.model).replace(".glb", "")
GJ = trimesh.load(a.model).geometry; GS = trimesh.load(a.shapes).geometry
PRM = json.load(open(a.params)); JN = json.load(open(a.joinery))
SHEET_N = np.array(json.load(open("work/parts/sideR/o_plane.json"))["n"])       # right side frame's sheet normal (outboard)


def unit(v): v = np.asarray(v, float); return v / np.linalg.norm(v)


def winding(mesh, P, chunk=400):
    """generalized winding number of points P (N,3) w.r.t. a closed mesh: ~1 inside, ~0 outside (no rtree needed)"""
    T = mesh.triangles; out = np.zeros(len(P))
    for i in range(0, len(P), chunk):
        A = T[None, :, 0, :] - P[i:i + chunk, None, :]; B = T[None, :, 1, :] - P[i:i + chunk, None, :]; C = T[None, :, 2, :] - P[i:i + chunk, None, :]
        la, lb, lc = (np.linalg.norm(X, axis=2) for X in (A, B, C))
        det = np.einsum("ijk,ijk->ij", A, np.cross(B, C))
        den = la * lb * lc + np.einsum("ijk,ijk->ij", A, B) * lc + np.einsum("ijk,ijk->ij", B, C) * la + np.einsum("ijk,ijk->ij", C, A) * lb
        out[i:i + chunk] = np.arctan2(det, den).sum(1) / (2 * np.pi)
    return out


def face_plane(m, sgn):
    """area-weighted plane through the triangles facing sgn * sheet normal (cos > 0.85): (centroid, outboard normal, rms, max, area)"""
    fn = m.face_normals; k = (fn @ SHEET_N) * sgn > 0.85
    C = m.triangles_center[k]; w = m.area_faces[k]; c = (C * w[:, None]).sum(0) / w.sum()
    # normal = area-weighted mean face normal. (A least-squares plane through the points is NOT used: the lofted faces twist a little
    # along the leg, rms 3-4 mm, and the point fit then tilts the plane 5 deg in plan on the front leg, skewing the profile by 3 mm.)
    n = unit((fn[k] * w[:, None]).sum(0) * sgn)
    if n @ SHEET_N < 0: n = -n                                                   # always outboard, for both faces
    r = (C - c) @ n; return c, n, float(np.sqrt((w * r ** 2).sum() / w.sum())), float(np.abs(r).max()), float(w.sum())


def largest_loop(sec):
    if sec is None: return None
    best = None
    for d in sec.discrete:
        if best is None or len(d) > len(best): best = d
    return best


class Frame:
    def __init__(s, m):
        co, no, s.out_rms, s.out_max, s.out_area = face_plane(m, +1); ci, ni, s.in_rms, s.in_max, s.in_area = face_plane(m, -1)
        s.n = no; s.n_in = ni; s.c = (co + ci) / 2; s.t_planes = float((co - ci) @ s.n); s.face_angle_deg = float(np.degrees(np.arccos(np.clip(no @ ni, -1, 1))))
        z = np.array([0, 0, 1.0]); s.ev = unit(z - (z @ s.n) * s.n); s.eu = unit(np.cross(s.ev, s.n))
        if s.eu[1] < 0: s.eu = -s.eu
        s.o = s.c - (s.c[2] / s.ev[2]) * s.ev; s.u0 = 0.0
        s.d_out = float((co - s.c) @ s.n); s.d_in = float((ci - s.c) @ s.n)          # n = the OUTER face's normal: the face the template lies on
    def uv(s, P): P = np.atleast_2d(P) - s.o; return np.stack([P @ s.eu - s.u0, P @ s.ev], 1)
    def dn(s, P): return (np.atleast_2d(P) - s.c) @ s.n
    def xyz(s, UV, d):
        """drawing (u, v) + depth d along n from the mid-plane -> chair xyz (o lies on the mid-plane)"""
        UV = np.atleast_2d(UV); return s.o + np.outer(UV[:, 0] + s.u0, s.eu) + np.outer(UV[:, 1], s.ev) + d * s.n


def silhouette(m, F):
    P = F.uv(m.vertices); polys = []
    for f in m.faces:
        q = P[f]
        if abs((q[1, 0] - q[0, 0]) * (q[2, 1] - q[0, 1]) - (q[2, 0] - q[0, 0]) * (q[1, 1] - q[0, 1])) > 1e-6: polys.append(Polygon(q))
    U = unary_union(polys)
    if U.geom_type != "Polygon": U = max(U.geoms, key=lambda g: g.area)
    return Polygon(U.exterior).simplify(0.05)


def patches(leg, F, others, thr=1.0, n_leg=160000):
    """contact faces: leg surface points within thr mm of another part's surface. Returns {part: dict(uv, face, area_cm2, ...)}"""
    Pl, fi = trimesh.sample.sample_surface(leg, n_leg, seed=3)
    dA = leg.area / n_leg; res = {}
    lo, hi = leg.bounds[0] - 12, leg.bounds[1] + 12
    for nm in others:
        o = GJ[nm]; tc = o.triangles_center; k = np.all((tc > lo) & (tc < hi), 1)
        if k.sum() == 0: continue
        sub = o.submesh([np.where(k)[0]], append=True); Po, _ = trimesh.sample.sample_surface(sub, max(20000, int(sub.area / 0.25)), seed=4)
        d, _ = cKDTree(Po).query(Pl, distance_upper_bound=thr + 1); sel = d < thr
        if sel.sum() < 30: continue
        fn = leg.face_normals[fi[sel]]
        comp = {"outer face": fn @ F.n, "inner face": -(fn @ F.n), "front edge": fn @ F.eu, "rear edge": -(fn @ F.eu), "top end": fn @ F.ev, "bottom end": -(fn @ F.ev)}
        lab = {kk: float((vv > 0.6).sum()) for kk, vv in comp.items()}; tot = sum(lab.values()) or 1
        faces = {kk: round(vv / tot, 2) for kk, vv in lab.items() if vv / tot > 0.08}
        uv = F.uv(Pl[sel]); res[nm] = dict(uv=uv, xyz=Pl[sel], faces=faces, main=max(lab, key=lab.get), area_cm2=float(sel.sum() * dA / 100),
                                           v_range=[float(uv[:, 1].min()), float(uv[:, 1].max())], u_range=[float(uv[:, 0].min()), float(uv[:, 0].max())],
                                           dn_range=[float(F.dn(Pl[sel]).min()), float(F.dn(Pl[sel]).max())])
    return res


def outline_of(uv, r=1.5):
    g = unary_union([Point(p).buffer(r, 6) for p in uv[:: max(1, len(uv) // 4000)]]).buffer(-r * 0.6)
    gs = [g] if g.geom_type == "Polygon" else list(g.geoms)
    return [np.asarray(x.exterior.coords) for x in gs if x.area > 4.0]


def mortises(legname, F):
    """Domino solids that cut this leg: mortise = Domino volume inside the traced (unjoined) leg"""
    leg_s = GS[legname]; out = {}
    lo, hi = leg_s.bounds[0] - 1, leg_s.bounds[1] + 1
    for nm, d in GJ.items():
        if not (nm.startswith("DOMINO_") and nm.endswith("R")): continue          # right-hand Dominos (the left are mirrors)
        if np.any(d.bounds[1] < lo) or np.any(d.bounds[0] > hi): continue
        b0, b1 = d.bounds; P = b0 + np.random.rand(9000, 3) * (b1 - b0)
        P = P[winding(d, P) > 0.5]; inl = winding(leg_s, P) > 0.5
        if inl.sum() < 40: continue
        V = d.vertices; c = V.mean(0); _, _, Vt = np.linalg.svd(V - c, full_matrices=False); ax = Vt[0]
        Q = P[inl]; R_ = P[~inl]; s_in = (Q - c) @ ax
        depth = float(s_in.max() - s_in.min()); mc = Q.mean(0)
        if len(R_):
            dv = R_.mean(0) - mc; comp = {"outer face": dv @ F.n, "inner face": -(dv @ F.n), "front edge": dv @ F.eu, "rear edge": -(dv @ F.eu), "top end": dv @ F.ev, "bottom end": -(dv @ F.ev)}
            toward = max(comp, key=comp.get)
        else: toward = "none (wholly inside)"
        # which faces does the mortise open on? step 1.5 mm past each end of the in-leg part along the Domino axis
        q0, q1 = Q[np.argsort(s_in)[:30]].mean(0), Q[np.argsort(s_in)[-30:]].mean(0); opens = []
        for qe, sg in ((q0, -1), (q1, +1)):
            pe = qe + sg * ax * 1.5
            if winding(leg_s, pe[None])[0] < 0.5:
                dd = sg * ax; cm = {"outer face": dd @ F.n, "inner face": -(dd @ F.n), "front edge": dd @ F.eu, "rear edge": -(dd @ F.eu), "top end": dd @ F.ev, "bottom end": -(dd @ F.ev)}
                opens.append(max(cm, key=cm.get))
        through = len(opens) == 2
        uv = F.uv(Q); hull = np.asarray(MultiPoint([tuple(p) for p in uv]).convex_hull.exterior.coords)
        aloc = np.array([ax @ F.eu, ax @ F.ev, ax @ F.n])
        out[nm] = dict(centre_uv=F.uv(mc)[0].tolist(), centre_dn_from_outer=float(F.d_out - F.dn(mc)[0]), centre_xyz=mc.tolist(), depth_in_leg_mm=depth,
                       axis_in_leg_frame_uvn=aloc.round(3).tolist(), other_part_side=toward, opens_on=opens, through=through, hull_uv=hull.tolist(),
                       vol_in_leg_cm3=float(inl.sum() / len(P) * d.volume / 1000))
    return out


def chord(poly, v):
    ln = LineString([(-1e4, v), (1e4, v)]); x = poly.intersection(ln)
    if x.is_empty: return None
    b = x.bounds; return b[0], b[2]


def perp_width(poly, v, F_axis_slope):
    c = chord(poly, v)
    if c is None: return None
    um = (c[0] + c[1]) / 2; t = unit([F_axis_slope, 1.0]); nrm = np.array([t[1], -t[0]])
    ln = LineString([tuple(np.array([um, v]) - nrm * 200), tuple(np.array([um, v]) + nrm * 200)]); x = poly.intersection(ln)
    if x.is_empty: return None
    g = list(x.geoms) if hasattr(x, "geoms") else [x]; g = max(g, key=lambda q: q.length); p = np.asarray(g.coords)
    return p[0], p[-1], float(np.linalg.norm(p[-1] - p[0]))


def leg_axis_slope(poly, vlo, vhi):
    vs = np.linspace(vlo, vhi, 30); m = []
    for v in vs:
        c = chord(poly, v)
        if c: m.append((v, (c[0] + c[1]) / 2))
    m = np.array(m); return float(np.polyfit(m[:, 0], m[:, 1], 1)[0])


# ---------------------------------------------------------------- per leg
LEGS = {"front": dict(part="FLEG_R", others=["SEAT", "ARM_R", "ROCKER_R"]),
        "back": dict(part="BLEG_R", others=["SEAT", "ARM_R", "ROCKER_R", "CREST", "SLAT_R"])}
PNAME = {"SEAT": "SEAT", "ARM_R": "ARM", "ROCKER_R": "ROCKER", "CREST": "CREST", "SLAT_R": "SIDE SLAT"}
geom = {}
for key, L in LEGS.items():
    m = GJ[L["part"]]; F = Frame(m)
    sil0 = silhouette(m, F); F.u0 = float(np.asarray(sil0.exterior.coords)[:, 0].min())
    sil = silhouette(m, F); ol = np.asarray(sil.exterior.coords)[:-1]
    # the measured side-frame lines (parts/side_frame.json, the right side; L/R mean) in this frame, and their distance to the cut outline
    SF = json.load(open("parts/side_frame.json"))["lines"]; lines = {}; lchk = {}
    for lk, l in SF.items():
        if not lk.startswith(L["part"][:4].lower()): continue
        X = np.stack([np.array(l["x_abs"]), l["y"], l["z"]], 1); q = F.uv(X); lines[lk] = q
        inside = np.array([sil.contains(Point(p)) for p in q]); dist = np.array([sil.exterior.distance(Point(p)) for p in q]) * np.where(inside, -1, 1)
        lchk[lk] = dict(soft=l["soft"], median=float(np.median(dist)), max_abs=float(np.abs(dist).max()), n=len(q), dn_mean=float(F.dn(X).mean() - F.d_out))
    # thickness across (along n) per height, from the mesh
    thk = {}
    for v in (100, 200, 300, 400, 500, 600, 700, 800, 900, 1000):
        sc = m.section(plane_origin=F.o + v * F.ev, plane_normal=F.ev)
        if sc is not None and len(sc.vertices) > 8: dn = F.dn(sc.vertices); thk[v] = float(dn.max() - dn.min())
    PT = patches(m, F, L["others"]); MO = mortises(L["part"], F)
    vmin, vmax = float(ol[:, 1].min()), float(ol[:, 1].max()); umax = float(ol[:, 0].max())
    slope = leg_axis_slope(sil, vmin + 60, vmax - 60)
    rect = np.asarray(sil.minimum_rotated_rectangle.exterior.coords)[:-1]; e = np.linalg.norm(np.diff(np.vstack([rect, rect[:1]]), axis=0), axis=1)
    blank = sorted([float(e[0]), float(e[1])], reverse=True)
    geom[key] = dict(F=F, sil=sil, ol=ol, lines=lines, lchk=lchk, thk=thk, PT=PT, MO=MO, vmin=vmin, vmax=vmax, umax=umax, slope=slope, rect=rect, blank=blank, part=L["part"])

# ---------------------------------------------------------------- L / R (measured lines; the model is a mirror)
def lr_compare(leg):
    Ld = {**json.load(open("parts/side_frame_L.json"))["lines"], **json.load(open("parts/side_frame_ub_L.json"))["lines"]}
    Rd = {**json.load(open("parts/side_frame_R.json"))["lines"], **json.load(open("parts/side_frame_ub_R.json"))["lines"]}
    A, B, per = [], [], {}
    for kL in Ld:
        if not kL.startswith(leg + "L"): continue
        kR = kL.replace(leg + "L", leg + "R")
        if kR not in Rd: continue
        pl = np.array(Ld[kL]["xyz"]); pr = np.array(Rd[kR]["xyz"]); pl[:, 0] *= -1
        z0, z1 = max(pl[:, 2].min(), pr[:, 2].min()), min(pl[:, 2].max(), pr[:, 2].max()); zz = np.linspace(z0, z1, 15)
        ol_, or_ = np.argsort(pl[:, 2]), np.argsort(pr[:, 2])
        yl = np.interp(zz, pl[ol_, 2], pl[ol_, 1]); yr = np.interp(zz, pr[or_, 2], pr[or_, 1])
        A.append(np.c_[yl, zz]); B.append(np.c_[yr, zz]); per[kL[len(leg) + 2:]] = dict(mean_R_minus_L=round(float(np.mean(yr - yl)), 2), sd=round(float(np.std(yr - yl)), 2), tol=Ld[kL]["tol_mm"])
    A, B = np.vstack(A), np.vstack(B); ca, cb = A.mean(0), B.mean(0); H = (B - cb).T @ (A - ca); U, s, Vt = np.linalg.svd(H); Rm = (U @ Vt).T
    r = np.linalg.norm((B - cb) @ Rm.T + ca - A, axis=1)
    return dict(lines=per, raw_mean_abs=float(np.abs(B[:, 0] - A[:, 0]).mean()), raw_max=float(np.abs(B[:, 0] - A[:, 0]).max()),
                rigid_rot_deg=float(np.degrees(np.arctan2(Rm[1, 0], Rm[0, 0]))), rigid_shift_y=float(ca[0] - cb[0]),
                rigid_rms=float(np.sqrt((r ** 2).mean())), rigid_max=float(r.max()), rigid_max_at_z=float(A[np.argmax(r), 1]))
LR = {k: lr_compare("fleg" if k == "front" else "bleg") for k in LEGS}

# ---------------------------------------------------------------- rocker landing cross-check (rocker template frame = left rocker sheet)
RG = json.load(open("templates/out/rocker_geom.json")) if os.path.exists("templates/out/rocker_geom.json") else None
plL = json.load(open("work/parts/rockerL/o_plane.json")); OL_, euL = np.array(plL["origin"]), np.array(plL["u"])
for key in LEGS:
    g = geom[key]; p = g["PT"].get("ROCKER_R")
    if p is None: continue
    F = g["F"]; ko = F.dn(p["xyz"]) > F.d_out - 4                        # the foot's outer-face end only (the rocker template marks the outer face)
    X = p["xyz"][ko] * [-1, 1, 1]; uu = (X - OL_) @ euL; g["landing_rocker_u"] = [float(uu.min()), float(uu.max())]
    X = p["xyz"] * [-1, 1, 1]; uu = (X - OL_) @ euL; g["landing_rocker_u_fullwidth"] = [float(uu.min()), float(uu.max())]
    if RG:
        k1, k2 = ("bleg_rear_lo", "bleg_front_lo") if key == "back" else ("fleg_rear_lo", "fleg_front_lo")
        g["landing_rocker_template_u"] = [RG["legs"][k1]["u"], RG["legs"][k2]["u"]]

# ---------------------------------------------------------------- drawing
FP = PRM["parts"]["front_leg"]; BP = PRM["parts"]["back_leg"]; AT = PRM["assumed_or_tape"]
DOM_NAME = {"DOMINO_FR": "front-leg / seat Domino (through the leg)", "DOMINO_BR": "back-leg / seat Domino", "DOMINO_AR": "arm / front-leg Domino (ASSUMED)",
            "DOMINO_RSR": "rear Domino, back leg / seat back edge", "DOMINO_RAR": "rear Domino, back leg / arm end"}
JNT = JN["joints"]


def build_spec(key):
    g = geom[key]; F = g["F"]; ol = g["ol"]; sil = g["sil"]; items = [dict(kind="cut", pts=ol, closed=True)]
    name = "front" if key == "front" else "back"
    # the measured arrises (parts/side_frame.json) as thin dashed REF lines: they show where the faces' own edges run inside the cut line
    for lk, q in g["lines"].items():
        items.append(dict(kind="line", pts=q, style="hidden"))
    items.append(dict(kind="text", xy=(g["umax"] / 2, g["vmin"] - 40), s="dashed inside the cut line: measured arrises (parts/side_frame.json):\nfront and rear ridge on the outer face, rear arris on the inner face", size=5.3, color=K.REF))
    # floor and height lines
    u_lo, u_hi = -15, g["umax"] + 15
    items.append(dict(kind="line", pts=[[u_lo - 30, 0], [u_hi + 30, 0]], style="hidden", label="FLOOR / table line (v = 0)", label_at=0))
    for v in range(100, int(g["vmax"]), 100):
        c = chord(sil, v)
        if c is None or v < g["vmin"] + 8: continue
        items.append(dict(kind="line", pts=[[c[0] - 10, v], [c[0] + 4, v]], style="ref")); items.append(dict(kind="line", pts=[[c[1] - 4, v], [c[1] + 10, v]], style="ref"))
        items.append(dict(kind="text", xy=(c[0] - 24, v), s=f"v {v}", size=5.5, color=K.REF))
    # contact faces
    for pn, p in g["PT"].items():
        lab = PNAME[pn]
        if p["main"] in ("outer face", "inner face") and p["area_cm2"] > 2:
            for lp in outline_of(p["uv"]): items.append(dict(kind="line", pts=lp, style="mark"))
            cen = p["uv"].mean(0)
            items.append(dict(kind="text", xy=(cen[0] + (70 if key == "front" else 75), cen[1]), s=f"{lab} on the {p['main']}\n(contact, {p['area_cm2']:.0f} cm2)\nv {p['v_range'][0]:.0f}-{p['v_range'][1]:.0f}", size=5.8, color=K.MARK, ha="left"))
        else:
            # along an edge or an end: ticks square to the outline at the ends of the patch
            uv = p["uv"]
            if p["main"] in ("front edge", "rear edge"): ends = [uv[np.argmin(uv[:, 1])], uv[np.argmax(uv[:, 1])]]
            else: ends = [uv[np.argmin(uv[:, 0])], uv[np.argmax(uv[:, 0])]]
            for q in ends:
                bp = sil.exterior.interpolate(sil.exterior.project(Point(q))); bp = np.array(bp.coords[0])
                cen = np.array(sil.centroid.coords[0]); d = unit(cen - bp) if p["main"] in ("front edge", "rear edge") else np.array([0, 1.0 if p["main"] == "bottom end" else -1.0])
                items.append(dict(kind="line", pts=[bp - d * 6, bp + d * 12], style="mark"))
            m_ = uv.mean(0); out_ = {"front edge": (32, 0), "rear edge": (-32, 0), "top end": (0, 26), "bottom end": (0, -22)}[p["main"]]
            ha = "left" if out_[0] > 0 else ("right" if out_[0] < 0 else "center")
            items.append(dict(kind="text", xy=(m_[0] + out_[0], m_[1] + out_[1]), s=f"{lab} on the {p['main']}\nv {p['v_range'][0]:.0f}-{p['v_range'][1]:.0f}, u {p['u_range'][0]:.0f}-{p['u_range'][1]:.0f}", size=5.8, color=K.MARK, ha=ha))
    # Domino mortises
    for dn_, d in g["MO"].items():
        h = np.asarray(d["hull_uv"]); items.append(dict(kind="line", pts=h, style="mark")); c = d["centre_uv"]
        items.append(dict(kind="line", pts=[[c[0] - 5, c[1]], [c[0] + 5, c[1]]], style="mark")); items.append(dict(kind="line", pts=[[c[0], c[1] - 5], [c[0], c[1] + 5]], style="mark"))
        side = -1 if c[0] < (g["umax"] / 2) else 1
        if dn_ in ("DOMINO_RSR", "DOMINO_RAR", "DOMINO_BR"): side = -1
        if dn_ in ("DOMINO_FR", "DOMINO_AR"): side = 1
        txt = (f"{dn_.replace('DOMINO_', 'D-')}: {DOM_NAME.get(dn_, dn_)}\n10 mm Domino 24 x 10; centre u {c[0]:.1f}, v {c[1]:.1f},\n"
               f"{d['centre_dn_from_outer']:.1f} mm in from the outer face; {'through the leg' if d['through'] else 'depth in leg %.0f' % d['depth_in_leg_mm']}, mortise opens on the {' + '.join(d['opens_on']) or '-'}")
        tx = (g["umax"] + 28) if side > 0 else -28
        items.append(dict(kind="line", pts=[[c[0], c[1]], [tx - 3 * side, c[1] + 0]], style="ref"))
        items.append(dict(kind="text", xy=(tx, c[1]), s=txt, size=5.3, color=K.MARK, ha="left" if side > 0 else "right"))
    # widths square to the leg, overall height
    for v in ((150, 300, 450, 600) if key == "front" else (100, 300, 450, 600, 800, 1000)):
        if v > g["vmax"] - 15 or v < g["vmin"] + 15: continue
        r = perp_width(sil, v, g["slope"])
        if r: items.append(dict(kind="dim", p1=r[0], p2=r[1], off=0.0, label=f"{frac32(r[2])} ({r[2]:.1f})", size=5.2))
    lo_pt = ol[np.argmin(ol[:, 1])]; hi_pt = ol[np.argmax(ol[:, 1])]
    items.append(dict(kind="dim", p1=(g["umax"] + 8, 0), p2=(g["umax"] + 8, g["vmax"]), off=-30 if key == "front" else -20, label=f"top above floor {fmt(g['vmax'])}"))
    items.append(dict(kind="dim", p1=(0, g["vmin"] - 12), p2=(g["umax"], g["vmin"] - 12), off=-10, label=f"{fmt(g['umax'])} overall fore-aft", size=5.5))
    # title text on the drawing
    t = AT["fleg_thickness_across"] if key == "front" else AT["bleg_thickness_across"]
    TH = FP["thickness_across_mm"] if key == "front" else BP["width_across_mm"]
    ths = ", ".join(f"{kk.replace('v', 'v ').replace('z', 'z ')}: {vv:.1f}" for kk, vv in TH.items())
    lr = LR[key]
    head = (f"{'FRONT' if key == 'front' else 'BACK'} LEG, side profile, 1:1  (make 2: one as drawn, one flipped)\n"
            f"Shown: right leg's outer face, front to the right. The left leg is its mirror: flip the template.\n"
            f"Thickness across, model v24 ({'front_leg.thickness_across_mm' if key == 'front' else 'back_leg.width_across_mm'}): {ths} mm;\n"
            f"  square to this face, from the v24 mesh: {min(g['thk'].values()):.1f}-{max(g['thk'].values()):.1f} mm. Stock: at least {frac32(max(g['thk'].values()))} finished.\n"
            f"  (v24 fallback param {key[0]}leg_thickness_across {t['value_mm']:.0f} mm, {t['provenance']}, is not what the build uses.)\n"
            f"Saw to the CUT line. Red = joints (contact faces, Domino mortises with their centres crossed).\n"
            f"Dashed inside the cut line = the measured arrises; the rear one on the outer face is a soft ridge (rear bevel / round).")
    if key == "front":
        tx, ty, ha = g["umax"] + 60, g["vmax"] - 40, "left"
    else:
        tx, ty, ha = g["umax"] + 40, g["vmax"] - 60, "left"
    items.append(dict(kind="text", xy=(tx, ty), s=head, size=6.6, ha=ha, va="top"))
    return items


def lchk_txt(key):
    return "; ".join(f"{k.split('_', 1)[1]} {c['median']:+.1f}" for k, c in geom[key]["lchk"].items()) + " mm (median, - = inside)"


def tb_lines(key):
    g = geom[key]; F = g["F"]; lr = LR[key]
    if key == "front":
        prov = ["Outline: model v24 FLEG (tools/build_model.py): lofted through three triangulated lines per leg (front outline, rear outer-face ridge,",
                "  rear inner arris; parts/side_frame.json from side_frame_L/R, L and R averaged; hard lines +-1 mm, the rear ridge is soft +-2 mm).",
                f"  The seat joint (v 370-470) is bridged linearly (not traced). Top: cut to the arm underside; foot: carried 12 mm down the leg axis and",
                "  cut to the rocker top (PR #19). Front-leg Domino centre measured on 19 photos (PR #24); its depth and the arm Domino are ASSUMED (PR #18)."]
    else:
        prov = ["Outline: model v24 BLEG, one continuous board (PR #14/#16): one smoothing spline per edge through the measured stretches",
                "  (triangulated lower lines z <= 265-270, side-view traces z >= 608; fit rms 0.08 / 0.05 mm). Between z 265 and 608 (seat and arm",
                "  joints) the leg is NOT measured: a smooth guess. Top: flush with the crest's top arch, rear pinned to its arris (PR #5); foot cut to the",
                "  rocker top (PR #19). Rear Dominos (PR #22) and the seat Domino positioned from photos; Domino depths ASSUMED."]
    return prov + [
        f"Frame: the outer face's mean plane (outer / inner faces {F.face_angle_deg:.2f} deg apart). The model's faces are not flat: {F.out_rms:.1f} mm rms off that plane (a bow",
        f"  along the leg); projecting square to the mean plane changes lengths by < 0.1 %. Measured arrises vs the cut line: {lchk_txt(key)}.",
        f"  the face leans {np.degrees(np.arcsin(abs(F.n[2]))):.1f} deg from plumb (splay) and is turned {np.degrees(np.arctan2(-F.n[1], F.n[0])):.1f} deg in plan (toe, as the side frame).",
        f"Left vs right (measured lines, parts/side_frame_L/R + ub): after a rigid fit {lr['rigid_rms']:.1f} mm rms, {lr['rigid_max']:.1f} max (at z {lr['rigid_max_at_z']:.0f});",
        f"  shift {lr['rigid_shift_y']:+.1f} mm fore-aft, {lr['rigid_rot_deg']:+.2f} deg. Inside the 1.6 mm free-curve tolerance in rms, so ONE template, flipped.",
        f"Generated by templates/legs.py from {a.model} @ {REV} (+ {a.shapes}, {a.joinery}). Scale: framing-square scale, 0.085 %."]


def kd_lines(key):
    g = geom[key]; F = g["F"]; out = [("Top above floor (v)", g["vmax"], "highest point of the outline"),
                                       ("Overall fore-aft (u)", g["umax"], "rearmost to foremost point, in the face plane"),
                                       ("Blank (min. rectangle)", f"{frac32(g['blank'][0])} x {frac32(g['blank'][1])}  ({g['blank'][0]:.0f} x {g['blank'][1]:.0f} mm)", "plus thickness, plus allowance"),
                                       ("Max thickness across", f"{frac32(max(g['thk'].values()))} ({max(g['thk'].values()):.1f} mm)", "from the model mesh, square to the face")]
    for pn, p in g["PT"].items():
        out.append((f"{PNAME[pn]} contact", f"v {p['v_range'][0]:.0f}-{p['v_range'][1]:.0f}", f"{p['main']}, {p['area_cm2']:.0f} cm2"))
    for dn_, d in g["MO"].items():
        out.append((dn_.replace("DOMINO_", "Domino "), f"u {d['centre_uv'][0]:.1f} v {d['centre_uv'][1]:.1f}", f"{d['centre_dn_from_outer']:.1f} mm in from outer face; opens on {' + '.join(d['opens_on'])}"))
    return out


os.makedirs(a.out, exist_ok=True); tiles = {}
for key in LEGS:
    spec = dict(name=f"legs_{key}", title=f"ESSICK rocker - {key} leg side template (make 2: as drawn + flipped)", rev=REV, items=build_spec(key),
                title_block=tb_lines(key), key_dims=kd_lines(key))
    Lt = K.write_all(spec, a.out); tiles[key] = [Lt["rows"], Lt["cols"]]

# ---------------------------------------------------------------- geometry json
def jf(F): return dict(origin=F.o.tolist(), eu=F.eu.tolist(), ev=F.ev.tolist(), n=F.n.tolist(), u0=F.u0, centre=F.c.tolist(), d_out=F.d_out, d_in=F.d_in,
                       t_planes=F.t_planes, face_rms=[F.out_rms, F.in_rms], face_max=[F.out_max, F.in_max], face_angle_deg=F.face_angle_deg)
GO = {"model": a.model, "rev": REV, "lr": LR, "tiles": tiles}
for key, g in geom.items():
    F = g["F"]
    GO[key] = dict(part=g["part"], frame=jf(F), outline_uv=g["ol"].tolist(), outline_outer_xyz=F.xyz(g["ol"], F.d_out).tolist(),
                   line_check=g["lchk"],
                   thickness_across=g["thk"], top_v=g["vmax"], bottom_v=g["vmin"], fore_aft=g["umax"], blank=g["blank"], axis_slope_du_dv=g["slope"],
                   contacts={k: {kk: vv for kk, vv in p.items() if kk not in ("uv", "xyz")} | {"xyz_sample": p["xyz"][:: max(1, len(p["xyz"]) // 400)].tolist()} for k, p in g["PT"].items()},
                   mortises=g["MO"], landing_rocker_u=g.get("landing_rocker_u"), landing_rocker_u_fullwidth=g.get("landing_rocker_u_fullwidth"), landing_rocker_template_u=g.get("landing_rocker_template_u"))
json.dump(GO, open(a.geom_json or f"{a.out}/legs_geom.json", "w"), indent=1)

for key, g in geom.items():
    F = g["F"]
    print(f"{key}: top v {g['vmax']:.1f} bottom v {g['vmin']:.1f} fore-aft {g['umax']:.1f} blank {g['blank'][0]:.0f} x {g['blank'][1]:.0f}  thk {min(g['thk'].values()):.1f}-{max(g['thk'].values()):.1f}"
          f"  face rms {F.out_rms:.2f}/{F.in_rms:.2f} max {F.out_max:.1f}/{F.in_max:.1f} angle {F.face_angle_deg:.2f}  splay {np.degrees(np.arcsin(abs(F.n[2]))):.1f} toe {np.degrees(np.arctan2(-F.n[1], F.n[0])):.1f}  tiles {tiles[key]}")
    for lk, c in g["lchk"].items(): print(f"   line {lk:16s} soft {int(c['soft'])} to cut outline median {c['median']:+.2f} max {c['max_abs']:.2f} (n {c['n']}, depth from outer face {c['dn_mean']:+.1f})")
    for pn, p in g["PT"].items(): print(f"   contact {pn:9s} {p['main']:11s} {p['area_cm2']:5.1f} cm2 v {p['v_range'][0]:.0f}-{p['v_range'][1]:.0f} u {p['u_range'][0]:.0f}-{p['u_range'][1]:.0f} faces {p['faces']}")
    for dn_, d in g["MO"].items(): print(f"   {dn_:11s} c uv {np.round(d['centre_uv'], 1).tolist()} in {d['centre_dn_from_outer']:.1f} depth {d['depth_in_leg_mm']:.1f} opens {d['opens_on']} other part -> {d['other_part_side']} axis {d['axis_in_leg_frame_uvn']}")
    if g.get("landing_rocker_u"): print(f"   landing on rocker (rocker template u): model {np.round(g['landing_rocker_u'], 1).tolist()} vs rocker template {np.round(g.get('landing_rocker_template_u'), 1).tolist() if g.get('landing_rocker_template_u') else None}")
for k, l in LR.items(): print(f"L/R {k}: raw mean {l['raw_mean_abs']:.2f} max {l['raw_max']:.2f}; rigid rms {l['rigid_rms']:.2f} max {l['rigid_max']:.2f} at z {l['rigid_max_at_z']:.0f}")
