"""USAGE: tools/py.sh templates/seat.py [--contour-mm 4] [--stations 50,150,250,350,450] [--out templates/out] [--geom-json PATH]
Seat, 1:1, from the model v24 SEAT mesh (parts/model_v24.glb = after joinery: leg cuts, Domino and slat mortises; and
parts/model_v24_shapes.glb = before joinery). The model's seat is the symmetric design (L/R mean) built by tools/build_model.py
from parts/seat_edge.json (sides), seat_front.json + seat_front_face.json (scalloped rolled front), seat_back.json (bowed back),
seat_scoop.json (side under-bevel) and seat/surface.json (dished top).
Outputs (prefix <out>/):
  seat_plan_*      plan outline in the plane of the flat underside (true size on the blank): CUT = largest extent (top arris /
                   front roll), REF = underside outline (bottom arris: the bevels run from it), REF thin = thickness contours
                   of the dished top above the underside, MARK = leg faces, Domino and slat mortises, section stations S1-S5.
  seat_sections_*  cross-section templates at the stations (across the seat) and on the centre line (front-back), each one
                   drawn on the underside as base line: cut the top line out of hardboard for a carving gauge.
Frame (drawing): X = chair x (+ = chair's right), Y = distance along the underside plane, forward, from the back edge on the
centre line; W = height above the underside plane. Writes a geometry json for templates/check_seat_overlay.py. Tiny compute."""
import json, argparse, subprocess, sys, os, numpy as np
import trimesh
from shapely.geometry import Polygon, MultiPolygon, LineString, Point
from shapely.ops import unary_union
from scipy.interpolate import LinearNDInterpolator
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tplkit as K
from tplkit import fmt, frac32

ap = argparse.ArgumentParser()
ap.add_argument("--contour-mm", type=float, default=4.0); ap.add_argument("--stations", default="50,150,250,350,450")
ap.add_argument("--out", default="templates/out"); ap.add_argument("--geom-json", default=None); ap.add_argument("--rev", default=None)
a = ap.parse_args()

def ghash(p):
    try: return subprocess.run(["git", "log", "-1", "--format=%h", "--", p], capture_output=True, text=True).stdout.strip() or "uncommitted"
    except Exception: return "?"
REV = a.rev or ghash("parts/model_v24.glb")
G = trimesh.load("parts/model_v24.glb").geometry; GS = trimesh.load("parts/model_v24_shapes.glb").geometry
M = G["SEAT"]; MS = GS["SEAT"]
JN = json.load(open("parts/model_v24_joinery.json")); PR = json.load(open("parts/model_v24_params.json"))["parts"]["seat"]
E = json.load(open("parts/seat_edge.json")); FR = json.load(open("parts/seat_front.json")); BK = json.load(open("parts/seat_back.json"))

# ---------------- board frame: robust plane through the downward faces (the flat underside) ----------------
fn, fc = M.face_normals, M.triangles_center; P = fc[fn[:, 2] < -0.9]; keep = np.ones(len(P), bool)
for _ in range(8):
    A_ = np.c_[P[:, 1] - 250.0, np.ones(len(P))]; co = np.linalg.lstsq(A_[keep], P[keep, 2], rcond=None)[0]; r = P[:, 2] - A_ @ co; keep = np.abs(r) < 1.5
SLOPE, Z250 = float(co[0]), float(co[1]); PLANE_RMS = float(r[keep].std()); TILT = float(np.degrees(np.arctan(SLOPE)))
A3 = np.c_[P[keep, 0], P[keep, 1] - 250.0, np.ones(keep.sum())]; cross_slope = float(np.linalg.lstsq(A3, P[keep, 2], rcond=None)[0][0])
NN = np.hypot(1.0, SLOPE); EV = np.array([0, 1.0, SLOPE]) / NN; EN = np.array([0, -SLOPE, 1.0]) / NN; O = np.array([0, 250.0, Z250])
def uvw(X): X = np.asarray(X, float) - O; return np.c_[X[:, 0], X @ EV, X @ EN]
def sil(mesh):
    q = uvw(mesh.vertices)[:, :2]; T = q[mesh.faces]
    ar = (T[:, 1, 0] - T[:, 0, 0]) * (T[:, 2, 1] - T[:, 0, 1]) - (T[:, 1, 1] - T[:, 0, 1]) * (T[:, 2, 0] - T[:, 0, 0])
    U = unary_union([Polygon(t) for t in T[np.abs(ar) > 1e-6]]).buffer(0.02).buffer(-0.02)
    return max(U.geoms, key=lambda g: g.area) if isinstance(U, MultiPolygon) else U
SA, SB = sil(M), sil(MS)                                  # after / before joinery
V0 = float(LineString([(0, -400), (0, 400)]).intersection(SA).bounds[1])     # back edge on the centre line
def D(p): p = np.asarray(p, float); return np.c_[p[:, 0], p[:, 1] - V0]      # (u, v) -> drawing (X, Y)
def chair_y(Y, w=0.0): return float((O + EV * (Y + V0) + EN * w)[1])

cutA = np.asarray(SA.exterior.coords)[:-1]; cutB = np.asarray(SB.exterior.coords)[:-1]
# 3D of the cut outline (for the overlay): the highest mesh vertex that projects within 0.6 mm of each outline vertex
Q = uvw(M.vertices)
from scipy.spatial import cKDTree
kt = cKDTree(Q[:, :2]); out3 = []
for p in cutA:
    ii = kt.query_ball_point(p, 0.6) or [kt.query(p)[1]]; j = ii[int(np.argmax(Q[ii, 2]))]; out3.append(M.vertices[j])
out3 = np.array(out3)

# ---------------- underside outline (bottom arris) = section 0.8 mm above the plane ----------------
def section_uv(mesh, w):
    s = mesh.section(plane_origin=O + EN * w, plane_normal=EN)
    if s is None: return []
    return [uvw(d)[:, :2] for d in s.discrete]
und = max(section_uv(M, 0.8), key=lambda p: Polygon(p).area if len(p) > 2 else 0)

# ---------------- top surface (height above the underside) on a 2 mm grid ----------------
QS = uvw(MS.vertices); up = MS.face_normals @ EN > 0.25; vid = np.unique(MS.faces[up]); TQ = QS[vid]      # before joinery: no mortise floors
TOP = LinearNDInterpolator(TQ[:, :2], TQ[:, 2])
gu, gv = np.arange(-270, 271, 2.0), np.arange(np.floor(V0) - 4, SA.bounds[3] + 4, 2.0); GU, GV = np.meshgrid(gu, gv)
from matplotlib.path import Path as MPath
inside = MPath(np.asarray(SA.buffer(-1.0).exterior.coords)).contains_points(np.c_[GU.ravel(), GV.ravel()]).reshape(GU.shape)
GW = TOP(GU, GV); GW[~inside] = np.nan
inner = MPath(np.asarray(SA.buffer(-30.0).exterior.coords)).contains_points(np.c_[GU.ravel(), GV.ravel()]).reshape(GU.shape)
wmax, wmin = float(np.nanmax(GW)), float(np.nanmin(GW)); GWi = np.where(inner, GW, np.nan); wdish = float(np.nanmin(GWi)); imin = np.unravel_index(np.nanargmin(GWi), GW.shape)
dish_low = (float(GU[imin]), float(GV[imin] - V0))
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
levels = np.arange(np.ceil(wmin / a.contour_mm) * a.contour_mm, wmax, a.contour_mm)
cs = plt.contour(GU, GV, GW, levels=levels); contours = []
for lev, segs in zip(cs.levels, cs.allsegs):
    for sg in segs:
        if len(sg) > 8 and np.sum(np.linalg.norm(np.diff(sg, axis=0), axis=1)) > 40: contours.append((float(lev), sg))
plt.close("all")

# ---------------- joinery footprints ----------------
def foot_below(mesh, wtop):
    """plan footprint of the part of a mesh lying below height wtop (above the underside)"""
    try: c = mesh.slice_plane(O + EN * wtop, -EN, cap=True)
    except Exception: c = None
    if c is None or len(c.faces) == 0: return None
    return sil(c)
marks = []        # (name, polygon in (u,v), centre (u,v,w), note)
def topw(u, v): return float(TOP(u, v))
for k in ("SLAT_L", "SLAT_C", "SLAT_R"):
    q = uvw(G[k].vertices); c = q[q[:, 2] < q[:, 2].min() + 3].mean(0); wt = topw(c[0], c[1]) + 2.0
    f = foot_below(G[k], wt)
    if f is not None:
        f = f.intersection(SA)
        marks.append((k, f, [float(c[0]), float(c[1]), float(q[:, 2].min())], f"slat mortise: {q[:, 2].min():.0f} mm above underside at the bottom, top surface {wt - 2:.0f}"))
for k in ("DOMINO_FL", "DOMINO_FR", "DOMINO_BL", "DOMINO_BR", "DOMINO_RSL", "DOMINO_RSR"):
    q = uvw(G[k].vertices); f = sil(G[k]).intersection(SB.buffer(0.5))
    if f.area > 1: marks.append((k, f, [float(x) for x in q.mean(0)], f"Domino 24 x 10, centre {q[:, 2].mean():.0f} mm above underside"))
legs = {}
for k in ("BLEG_L", "BLEG_R", "FLEG_L", "FLEG_R"):
    wmid = 15.0; s = section_uv(G[k], wmid)
    if s:
        p = max(s, key=lambda p: Polygon(p).area if len(p) > 2 else 0); legs[k] = p
cut_regions = [g for g in getattr(SB.difference(SA), "geoms", [SB.difference(SA)]) if g.area > 50]

# ---------------- sections ----------------
ST = [float(s) for s in a.stations.split(",")]
def xsec(Y):
    s = M.section(plane_origin=O + EV * (Y + V0), plane_normal=EV)
    if s is None: return None
    best = max(s.discrete, key=len); q = uvw(best); return np.c_[q[:, 0], q[:, 2]]
def lsec():
    s = M.section(plane_origin=O, plane_normal=[1.0, 0, 0])
    best = max(s.discrete, key=len); q = uvw(best); return np.c_[q[:, 1] - V0, q[:, 2]]
secs = [(Y, xsec(Y)) for Y in ST]; LS = lsec()

# ---------------- numbers ----------------
W_all = SA.bounds[2] - SA.bounds[0]; D_all = SA.bounds[3] - SA.bounds[1]
def width_at(Y, poly=SA):
    g = LineString([(-400, Y + V0), (400, Y + V0)]).intersection(poly); return g.length if not g.is_empty else 0.0
back_corner = float(np.max(cutA[:, 0]))
front_tip = float(LineString([(0, -400), (0, 400)]).intersection(SA).bounds[3]) - V0
horn = cutA[np.argmax(cutA[:, 1])]; hollow_v = float(min(LineString([(x, 0), (x, 400)]).intersection(SA).bounds[3] for x in np.arange(100, 160, 2.0)))
def fv(x): return float(LineString([(x, 0), (x, 400)]).intersection(SA).bounds[3]) - V0
hollow_x = float(np.arange(60, 220, 1.0)[np.argmin([fv(x) for x in np.arange(60, 220, 1.0)])]); hollow_Y = fv(hollow_x)
horn_Y = float(cutA[np.abs(cutA[:, 0]) > 200, 1].max() - V0); horn_X = float(np.abs(cutA[np.argmax(np.where(np.abs(cutA[:, 0]) > 200, cutA[:, 1], -1e9)), 0]))
# angle of the front and back faces against the board (centre-line long section)
def face_angle(sec, front=True):
    """angle of the front / back face from square to the underside (deg; + = top further out), from the centre-line section's corner points"""
    s = sec[(sec[:, 0] > sec[:, 0].max() - 10) & (sec[:, 1] > 3) & (sec[:, 1] < 34)] if front else sec[(sec[:, 0] < sec[:, 0].min() + 3) & (sec[:, 1] > 15)]
    if len(s) < 2: return None
    lo, hi = s[np.argmin(s[:, 1])], s[np.argmax(s[:, 1])]; d = (hi[0] - lo[0]) * (1 if front else -1)
    return float(np.degrees(np.arctan2(d, hi[1] - lo[1])))
fa, ba = face_angle(LS, True), face_angle(LS, False)
thick_centre = {f"S{i + 1}": float(np.interp(0.0, *[s[np.argsort(s[:, 0])][:, j] for j in (0, 1)])) if s is not None else None for i, (Y, s) in enumerate(secs)}
def top_line(sec):
    """upper envelope of a closed section, as a function of u"""
    xs = np.arange(np.ceil(sec[:, 0].min()), np.floor(sec[:, 0].max()) + 0.01, 1.0); P_ = Polygon(sec).buffer(0)
    t = []
    for x in xs:
        g = LineString([(x, -50), (x, 200)]).intersection(P_); t.append(g.bounds[3] if not g.is_empty else np.nan)
    return xs, np.array(t)
cs_tbl = []
for i, (Y, s) in enumerate(secs):
    xs, t = top_line(s); inn = np.abs(xs) < (xs.max() - xs.min()) / 2 - 20; cs_tbl.append(dict(name=f"S{i + 1}", Y=Y, chair_y=chair_y(Y), half_width=float((xs.max() - xs.min()) / 2), centre_w=float(np.interp(0, xs, t)),
                                          min_w=float(np.nanmin(np.where(inn, t, np.nan))), max_w=float(np.nanmax(t)), u_of_min=float(xs[np.nanargmin(np.where(inn, t, np.nan))])))

# L/R asymmetry numbers (measured, not modelled)
LR = dict(side_half_width=E["left_vs_right"]["top_half_width_plan_mm"], side_bottom_half_width=E["left_vs_right"]["bottom_half_width_mm"],
          front_y=FR["left_vs_right"]["y_mm"], side_top_z=E["left_vs_right"]["top_z_plan_mm"])

# ---------------- plan drawing ----------------
items = [dict(kind="line", pts=D(cutB), style="hidden"), dict(kind="cut", pts=D(cutA), closed=True),
         dict(kind="line", pts=D(np.vstack([und, und[:1]])), style="ref")]
yb, yf = -12.0, SA.bounds[3] - V0 + 10
items.append(dict(kind="line", pts=[(0, yb), (0, yf)], style="centre"))
items.append(dict(kind="text", xy=(0, yf + 5), s="CL", size=7, color=K.REF))
for lev, sg in contours:
    p = D(sg); items.append(dict(kind="line", pts=p, style="hidden"))
for lev in sorted(set(l for l, _ in contours)):
    segs = [D(sg) for l, sg in contours if l == lev]; sg = max(segs, key=len)
    j = int(np.argmin(np.abs(sg[:, 0] - (60 + 0.3 * lev)) + 1e3 * (sg[:, 0] < 0)))   # label on the right half
    items.append(dict(kind="text", xy=tuple(sg[j]), s=f"{lev:.0f}", size=6, color=K.REF))
for name, f, c, note in marks:
    for g in getattr(f, "geoms", [f]):
        if g.geom_type == "Polygon" and g.area > 1: items.append(dict(kind="line", pts=D(np.asarray(g.exterior.coords)), style="mark"))
    lab = {"SLAT_L": "slat", "SLAT_C": "centre slat", "SLAT_R": "slat"}.get(name, "Domino")
    off = (0, 14) if name.startswith("SLAT") else ((-24 if c[0] > 0 else 24), (8 if "F" in name.split("_")[1][:1] else -10))
    if name.startswith("DOMINO_RS"): off = ((-30 if c[0] > 0 else 30), 12)
    items.append(dict(kind="text", xy=(c[0] + off[0], c[1] - V0 + off[1]), s=f"{lab}\n{c[2]:.0f} up" if not name.startswith("SLAT") else lab, size=5.5, color=K.MARK))
for k, p in legs.items():
    items.append(dict(kind="line", pts=D(np.vstack([p, p[:1]])), style="mark"))
    c = p.mean(0); items.append(dict(kind="text", xy=(c[0] + (18 if c[0] > 0 else -18), c[1] - V0 + (22 if k.startswith("F") else -16)), s=("front leg" if k.startswith("F") else "back leg"), size=6, color=K.MARK))
for g in cut_regions:
    c = g.centroid; items.append(dict(kind="text", xy=(c.x, c.y - V0), s="leg\ncuts", size=4.5, color=K.REF, box=False))
for i, Y in enumerate(ST):
    g = LineString([(-400, Y + V0), (400, Y + V0)]).intersection(SA); x0, x1 = g.bounds[0], g.bounds[2]
    items.append(dict(kind="line", pts=[(x0 - 8, Y), (x1 + 8, Y)], style="mark"))
    items.append(dict(kind="text", xy=(x1 + 16, Y), s=f"S{i + 1}", size=7, color=K.MARK))
    items.append(dict(kind="text", xy=(x0 - 16, Y), s=f"S{i + 1}", size=7, color=K.MARK))
x0, x1 = SA.bounds[0], SA.bounds[2]
items.append(dict(kind="dim", p1=(x0, SA.bounds[3] - V0), p2=(x1, SA.bounds[3] - V0), off=22, label=f"overall width {fmt(W_all)}"))
items.append(dict(kind="dim", p1=(x1, SA.bounds[1] - V0), p2=(x1, SA.bounds[3] - V0), off=-26, label=f"overall depth {fmt(D_all)} (on the underside plane)"))
items.append(dict(kind="dim", p1=(0, 0), p2=(0, front_tip), off=-12, label=f"{fmt(front_tip)} centre line"))
items.append(dict(kind="dim", p1=(-hollow_x, hollow_Y), p2=(-hollow_x, horn_Y), off=40, label=f"scallop {hollow_Y - horn_Y:+.1f}"))
for Yd in (100.0, 200.0, 300.0):
    w_ = width_at(Yd); items.append(dict(kind="text", xy=(0, Yd + 6), s=f"width at Y {Yd:.0f}: {fmt(w_)}", size=5.5, color=K.DIMC))
items.append(dict(kind="text", xy=(dish_low[0], dish_low[1] - 7), s=f"+ lowest {wdish:.1f}", size=5.5, color=K.REF, box=False))
items.append(dict(kind="line", pts=[(dish_low[0] - 3, dish_low[1]), (dish_low[0] + 3, dish_low[1])], style="ref"))
items.append(dict(kind="line", pts=[(dish_low[0], dish_low[1] - 3), (dish_low[0], dish_low[1] + 3)], style="ref"))
items.append(dict(kind="text", xy=(-150, front_tip + 40), s="FRONT", size=9, color=K.REF))
items.append(dict(kind="text", xy=(0, -30), s="BACK", size=9, color=K.REF))
NOTE = (f"Lay on the FLAT UNDERSIDE of the blank (symmetric: either way up).\n"
        f"Heavy = largest extent: the top arris (sides, back), the front roll (front).\n"
        f"Thin grey = underside outline (bottom arris): the side and back\n"
        f"under-bevels run from it up at about 46 deg; the front face is not bevelled.\n"
        f"Dashed grey = height of the dished top above the underside, every {a.contour_mm:.0f} mm.\n"
        f"Red = leg faces (at {15:.0f} mm up), Domino and slat mortises, stations.\n"
        f"Dashed outline at the legs = the model seat before the leg cuts.\n"
        f"Blank: at least {fmt(W_all + 20)} x {fmt(D_all + 20)} x {fmt(np.ceil(wmax + 3))} thick.\n"
        f"Front face: vertical in the chair = {abs(fa) if fa is not None else 10:.0f} deg off square to the\n"
        f"underside, top leaning forward. Back face: {abs(ba) if ba is not None else 0:.0f} deg off square.")
items.append(dict(kind="text", xy=(-262, -45), s=NOTE, size=6.2, ha="left", va="top"))
TB = [f"Model v24 SEAT mesh (parts/model_v24.glb after joinery; _shapes.glb before), projected onto its flat underside: plane z = {Z250:.2f} + {SLOPE:.4f} (y - 250),",
      f"  tilt {TILT:.1f} deg, fitted to the mesh's downward faces (rms {PLANE_RMS:.2f} mm; across x {cross_slope * 1000:.2f} mm/m). Y = distance along that plane from the back edge on the centre line",
      f"  (Y 0 = chair y {chair_y(0):.1f}). Tolerances (parts files): sides +-1.5, front +-2, back +-1.6 mm; side ends y 45-110 / 400-446: traced, agree within 0.5 (PR #30).",
      f"SYMMETRIC (design = L/R mean). Measured asymmetry, not drawn: side top arris R - mirrored L {LR['side_half_width']['mean']:+.1f} mm half-width (sd {LR['side_half_width']['sd']:.1f}),",
      f"  bottom arris {LR['side_bottom_half_width']['mean']:+.1f} (sd {LR['side_bottom_half_width']['sd']:.1f}); front outline {LR['front_y']['mean']:+.1f} (sd {LR['front_y']['sd']:.1f}). The top-arris figure is a 1.9 mm sideways shift on the",
      f"  chair's centre plane with the same total width (the bottom arrises agree), so one symmetric template; the R front corner sits 3.6-3.9 mm LOWER (PR #25): height, not plan.",
      f"Contours: dished top from seat/surface.json (103 tape dots, right half mirrored; 1.2 mm rms) carried to the measured edges. Joinery positions = model v24 joinery",
      f"  (parts/model_v24_joinery.json): Domino depths ASSUMED, slat mortise depth NOT measured; leg-cut shapes from the leg meshes. Scribe joints to the real legs.",
      f"Generated by templates/seat.py from parts/model_v24.glb @ {REV}."]
KD = [("Overall width", W_all, "front corners (horns), largest"), ("Overall depth", D_all, "on the underside plane, back bow to horn"),
      ("Centre line back to pommel", front_tip, "front tip"), ("Width at Y 40 (back legs)", width_at(40.0), "between the leg cuts"),
      ("Scallop (hollow behind horn)", f"{horn_Y - hollow_Y:.1f} mm at |X| {hollow_x:.0f}", "front edge"),
      ("Blank thickness, minimum", float(np.ceil(wmax)), f"highest top point {wmax:.1f} above the underside"),
      ("Deepest point of the dish", f"{wdish:.1f} mm above the underside", f"at X {dish_low[0]:+.0f}, Y {dish_low[1]:.0f}"),
      ("Underside tilt in the chair", f"{TILT:.1f} deg", "rises to the front")]
spec_p = dict(name="seat_plan", title="ESSICK rocker - seat plan outline, true size on the underside (symmetric)", rev=REV, items=items, title_block=TB, key_dims=KD)

# ---------------- sections drawing ----------------
si = []; GAPY = 85.0; yy = 0.0; lab_x = -300.0
for i, (Y, s) in reversed(list(enumerate(secs))):
    if s is None: continue
    t = cs_tbl[i]; p = s + [0, yy]
    si.append(dict(kind="cut", pts=p, closed=True))
    si.append(dict(kind="line", pts=[(-290, yy), (290, yy)], style="ref"))
    si.append(dict(kind="line", pts=[(0, yy - 6), (0, yy + t["max_w"] + 8)], style="centre"))
    si.append(dict(kind="text", xy=(lab_x, yy + 20), s=f"S{i + 1}\nY {Y:.0f}", size=8, color=K.MARK, ha="left"))
    si.append(dict(kind="text", xy=(0, yy - 10), s=f"S{i + 1}: {fmt(t['centre_w'])} on CL, low {t['min_w']:.1f} at |X| {abs(t['u_of_min']):.0f}, "
                                                f"high {t['max_w']:.1f}; width {fmt(2 * t['half_width'])}", size=5.6, color=K.DIMC))
    for xm in (-200, -100, 100, 200): si.append(dict(kind="line", pts=[(xm, yy - 3), (xm, yy + 3)], style="ref"))
    yy += GAPY
yL = yy + 10; LSd = LS + [-(LS[:, 0].max() + LS[:, 0].min()) / 2, yL]; xoff = -(LS[:, 0].max() + LS[:, 0].min()) / 2
si.append(dict(kind="cut", pts=LSd, closed=True)); si.append(dict(kind="line", pts=[(xoff - 20, yL), (xoff + LS[:, 0].max() + 20, yL)], style="ref"))
for i, Y in enumerate(ST):
    si.append(dict(kind="line", pts=[(Y + xoff, yL - 4), (Y + xoff, yL + 50)], style="mark")); si.append(dict(kind="text", xy=(Y + xoff, yL + 56), s=f"S{i + 1}", size=6.5, color=K.MARK))
si.append(dict(kind="text", xy=(lab_x, yL + 25), s="CL\nlong", size=8, color=K.MARK, ha="left"))
si.append(dict(kind="text", xy=(xoff + LS[:, 0].min() - 2, yL + 62), s="back", size=6, color=K.REF, ha="left"))
si.append(dict(kind="text", xy=(xoff + LS[:, 0].max(), yL + 62), s="front", size=6, color=K.REF, ha="right"))
si.append(dict(kind="text", xy=(0, yL - 10), s=f"centre line, back to front, {fmt(LS[:, 0].max() - LS[:, 0].min())} on the underside; front face {abs(fa or 0):.0f} deg off square (vertical in the chair)", size=5.6, color=K.DIMC))
si.append(dict(kind="text", xy=(-285, -40), s=("Each section is drawn standing on the underside line (grey). Cut along the TOP line, keep the part above it:\n"
         "a gauge to hold square across the seat at its station (stations marked red on seat_plan). Ticks every 100 mm from the centre line.\n"
         "Sections are the model after joinery: where a station crosses a mortise the gauge shows its notch; ignore it."), size=6.2, ha="left", va="top"))
TBs = [f"Sections of the model v24 SEAT mesh (after joinery) in planes square to the underside: S1-S{len(ST)} across the seat at Y = " + ", ".join(f"{Y:.0f}" for Y in ST) + " mm",
       f"  (Y along the underside from the back edge on the centre line; chair y " + ", ".join(f"{t['chair_y']:.0f}" for t in cs_tbl) + "), and the centre line (X = 0) front to back.",
       "Top: seat/surface.json (tape dots, thin-plate spline, 1.2 mm rms leave-one-out), carried to the triangulated edges. Underside: plane through the side bottom arrises",
       "  (flat across ASSUMED, raised 1-4 mm at the front over the last 60 mm). Side edges: vertical face, hard line, 46 deg under-bevel (seat_scoop.json). Symmetric (L/R mean).",
       f"Generated by templates/seat.py from parts/model_v24.glb @ {REV}."]
KDs = [(t["name"] + f" (Y {t['Y']:.0f})", f"CL {t['centre_w']:.1f}, low {t['min_w']:.1f}, high {t['max_w']:.1f}", "height above the underside, mm") for t in cs_tbl]
spec_s = dict(name="seat_sections", title="ESSICK rocker - seat cross-section gauges (stations S1-S5 + centre line)", rev=REV, items=si, title_block=TBs, key_dims=KDs)

os.makedirs(a.out, exist_ok=True)
Lp = K.write_all(spec_p, a.out); Ls = K.write_all(spec_s, a.out)
geom = dict(plane=dict(z250=Z250, slope=SLOPE, origin=O.tolist(), ev=EV.tolist(), en=EN.tolist(), V0=V0), outline_uv=D(cutA).tolist(), outline_xyz=out3.tolist(),
            underside_uv=D(und).tolist(), marks={n: dict(centre_uvw=c, note=nt) for n, f, c, nt in marks}, legs={k: D(p).tolist() for k, p in legs.items()},
            stations=ST, sections=cs_tbl, sizes=dict(width=W_all, depth=D_all, centre_line=front_tip, wmax=wmax, wmin=wmin, wdish=wdish, dish_low=dish_low, horn_Y=horn_Y, hollow=[hollow_x, hollow_Y],
            front_face_deg=fa, back_face_deg=ba), lr=LR, tiles=dict(plan=[Lp["rows"], Lp["cols"]], sections=[Ls["rows"], Ls["cols"]]))
json.dump(geom, open(a.geom_json or f"{a.out}/seat_geom.json", "w"), indent=1)
print(f"plane: z = {Z250:.2f} + {SLOPE:.4f}(y-250), tilt {TILT:.2f}, rms {PLANE_RMS:.2f}, across {cross_slope * 1000:.2f} mm/m; V0 {V0:.1f} (chair y {chair_y(0):.1f})")
print(f"size: width {W_all:.1f} depth {D_all:.1f} CL {front_tip:.1f}; horn Y {horn_Y:.1f}, hollow X {hollow_x:.0f} Y {hollow_Y:.1f}; top w {wmin:.1f}..{wmax:.1f}, dish low {wdish:.1f} at {np.round(dish_low, 1)}")
print(f"faces: front {fa}, back {ba}; marks {[m[0] for m in marks]}; legs {list(legs)}; cut regions {len(cut_regions)}; contours {len(contours)}")
for t in cs_tbl: print("  ", {k: (round(v, 1) if isinstance(v, float) else v) for k, v in t.items()})
print(f"tiles: plan {Lp['rows']}x{Lp['cols']}, sections {Ls['rows']}x{Ls['cols']}")
