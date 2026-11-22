"""USAGE: tools/py.sh templates/arms.py [--out templates/out] [--geom-json templates/out/arms_geom.json] [--rev REV]
Arm templates (make 2: one template, flipped for the left arm), 1:1, against model v24:
  arms_plan   the plan outline seen from straight above (chair X-Y), front to the right, outboard edge down;
  arms_side   the side profile seen from outside the right arm (chair Y-Z), front to the right: top line, underside
              (inner bottom arris = the deepest line, CUT) and the outer bottom arris (the underside bevels up to it, REF).
Inputs: parts/arms.json design (top arrises, plan), parts/arm_underside.json design (h_outer / h_inner drops below the outer
top arris), and parts/model_v24.glb ARM_R (the built arm: carried back to y 40, end coped to BLEG_R) for the silhouettes, the
back-leg cope and the joints: FLEG_R (front leg top under the arm), BLEG_R (front face at the arm's end), DOMINO_AR (ASSUMED
vertical Domino arm/front leg) and DOMINO_RAR (Domino through the back leg into the arm's end; position measured, depth ASSUMED).
Both views share the stations S0..S9 at chair y = 50, 100 .. 500 (vertical lines in both drawings).
Writes <out>/arms_plan_* and <out>/arms_side_* (tiled Letter PDF, full 1:1 PDF, DXF, preview PNG) and a geometry json
(templates/check_arm_overlay.py draws it on the rectified photos). Tiny compute (<1 s, < 300 MB)."""
import json, argparse, subprocess, sys, os, numpy as np
import trimesh
from shapely.geometry import Polygon, LineString, MultiLineString, box
from shapely.ops import unary_union, polygonize
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tplkit as K
from tplkit import fmt, frac32

ap = argparse.ArgumentParser()
ap.add_argument("--out", default="templates/out"); ap.add_argument("--geom-json", default=None); ap.add_argument("--rev", default=None)
ap.add_argument("--model", default="parts/model_v24.glb")
a = ap.parse_args()

def ghash(p):
    try: return subprocess.run(["git", "log", "-1", "--format=%h", "--", p], capture_output=True, text=True).stdout.strip() or "uncommitted"
    except Exception: return "?"
REV = a.rev or ghash("parts/arms.json") + "/" + ghash("parts/arm_underside.json") + "/" + ghash(a.model)

AJ = json.load(open("parts/arms.json")); D = AJ["design"]; UJ = json.load(open("parts/arm_underside.json"))["design"]
pin, pout = np.array(D["inner_x_of_y"]["poly_in_(y-300)"]), np.array(D["outer_x_of_y"]["poly_in_(y-300)"])
pz, pzx, pf = np.array(D["top_z_of_y"]["poly_in_(y-300)"]), np.array(D["top_z_of_y"]["cross_slope_outer_minus_inner_poly"]), np.array(D["front_y_of_x"]["poly"])
xin = lambda y: np.polyval(pin, np.asarray(y, float) - 300); xout = lambda y: np.polyval(pout, np.asarray(y, float) - 300)
ztop_o = lambda y: np.polyval(pz, np.asarray(y, float) - 300) + 0.5 * np.polyval(pzx, np.asarray(y, float) - 300)   # outer top arris
ztop_i = lambda y: np.polyval(pz, np.asarray(y, float) - 300) - 0.5 * np.polyval(pzx, np.asarray(y, float) - 300)
uy = np.array(UJ["y"]); h_o = lambda y: np.interp(y, uy, UJ["h_outer_mm"]); h_i = lambda y: np.interp(y, uy, UJ["h_inner_mm"])
slope = lambda y: np.degrees(np.arctan(np.polyval(np.polyder(pz), np.asarray(y, float) - 300)))
ci, co = D["corners"]["front_inner"], D["corners"]["front_outer"]

# ---------------- model v24 meshes ----------------
S = trimesh.load(a.model); G = S.geometry
ARM, FL, BL, DA, DR = (G[k] for k in ("ARM_R", "FLEG_R", "BLEG_R", "DOMINO_AR", "DOMINO_RAR"))

def silhouette(m, cols):
    T = m.vertices[m.faces][:, :, cols]
    polys = [Polygon(t) for t in T]; polys = [p for p in polys if p.area > 1e-4]
    u = unary_union([p.buffer(0.02) for p in polys]).buffer(-0.02)
    if u.geom_type != "Polygon": u = max(u.geoms, key=lambda g: g.area)
    return Polygon(u.exterior)          # holes ignored (none expected)

def section(m, origin, normal, cols):
    seg = trimesh.intersections.mesh_plane(m, normal, origin)
    return [LineString(s[:, cols]) for s in seg]

def sec_poly(m, origin, normal, cols):
    """outer boundary of a plane section (endpoints rounded so polygonize closes the loops; holes such as mortises dropped)"""
    seg = trimesh.intersections.mesh_plane(m, normal, origin)
    ps = list(polygonize(unary_union([LineString(np.round(s_[:, cols], 3)) for s_ in seg])))
    if not ps: return None
    u = unary_union(ps); u = u if u.geom_type == "Polygon" else max(u.geoms, key=lambda g: g.area)
    return Polygon(u.exterior)

plan = silhouette(ARM, [0, 1])          # (x, y)
side = silhouette(ARM, [1, 2])          # (y, z)
plan = plan.simplify(0.05); side = side.simplify(0.05)
px_ = np.array(plan.exterior.coords)[:-1]; sd_ = np.array(side.exterior.coords)[:-1]
y_back, y_front = float(px_[:, 1].min()), float(px_[:, 1].max())

# front leg top under the arm
fv = FL.vertices; tp = fv[fv[:, 2] > fv[:, 2].max() - 15]; yc, xc = float(tp[:, 1].mean()), float(tp[:, 0].mean())
fl_top = float(fv[:, 2].max())
fl_plan = sec_poly(FL, [0, 0, fl_top - 10], [0, 0, 1], [0, 1])                       # leg section 10 mm below its top
fl_side = [l for l in section(FL, [xc, 0, 0], [1, 0, 0], [1, 2])]                    # leg faces at the leg's centre x
win_f = box(yc - 60, fl_top - 45, yc + 60, fl_top + 2)
fl_side = [l.intersection(win_f) for l in fl_side]; fl_side = [l for l in fl_side if not l.is_empty]
fl_c = fl_plan.centroid
fl_y = (float(np.array(fl_plan.exterior.coords)[:, 1].min()), float(np.array(fl_plan.exterior.coords)[:, 1].max()))

# back leg: its front face where the arm's end is coped to it
z_end_mid = float((ztop_o(45) + ztop_o(45) - h_i(45)) / 2)
bl_plan = sec_poly(BL, [0, 0, z_end_mid], [0, 0, 1], [0, 1])
bl_plan_line = bl_plan.exterior.intersection(box(185, y_back - 2, 245, 60))
x_o45, x_i45 = float(xout(45)), float(xin(45))
win_b = box(y_back - 12, float(ztop_o(45) - h_i(45)) - 10, y_back + 25, float(ztop_o(45)) + 10)       # the leg's front face at the arm's end only
bl_side_o = [l.intersection(win_b) for l in section(BL, [x_o45 - 1.5, 0, 0], [1, 0, 0], [1, 2])]
bl_side_i = [l.intersection(win_b) for l in section(BL, [x_i45 + 1.5, 0, 0], [1, 0, 0], [1, 2])]

# Dominos: plan footprint (AR) / mortise in the arm (RAR), side view clipped to the arm
da_plan = silhouette(DA, [0, 1]); dr_plan = silhouette(DR, [0, 1]).intersection(plan)
da_c = DA.vertices.mean(0)
zb = lambda x, y: ztop_o(y) - (h_i(y) + (x - xin(y)) / (xout(y) - xin(y)) * (h_o(y) - h_i(y)))   # underside z (as tools/build_model.py)
yy = np.linspace(y_back - 5, y_front + 5, 200)
above = Polygon(np.vstack([np.c_[yy, zb(da_c[0], yy)], [[yy[-1], 900], [yy[0], 900]]]))
da_side = silhouette(DA, [1, 2]).intersection(above)
dr_side = silhouette(DR, [1, 2]).intersection(side)

# ---------------- numbers ----------------
ST = np.arange(50, 501, 50)
fine = np.linspace(y_back, co[1], 2000); zt = ztop_o(fine)
s_top = np.r_[0, np.cumsum(np.hypot(np.diff(fine), np.diff(zt)))]                 # along the outer top arris from the end
along = lambda y: float(np.interp(y, fine, s_top))
L_plan = y_front - y_back; L_top = along(co[1]); W = (px_[:, 0].max() - px_[:, 0].min())
rot_side = side.minimum_rotated_rectangle; rs = np.array(rot_side.exterior.coords)[:4]
e = np.linalg.norm(np.diff(np.vstack([rs, rs[:1]]), axis=0), axis=1)[:4]; blank_t, blank_l = float(e.min()), float(e.max())
k_ = int(np.argmax(e)); dv = rs[(k_ + 1) % 4] - rs[k_]; board_pitch = float(abs(np.degrees(np.arctan2(dv[1], dv[0]))))
board_pitch = 180 - board_pitch if board_pitch > 90 else board_pitch          # the blank's long edge vs level, in side view
rot_plan = plan.minimum_rotated_rectangle; rp = np.array(rot_plan.exterior.coords)[:4]
ep = np.linalg.norm(np.diff(np.vstack([rp, rp[:1]]), axis=0), axis=1)[:4]; blank_w = float(ep.min())
y_cope = float(np.array(bl_plan_line.coords if bl_plan_line.geom_type == "LineString" else [c for g in bl_plan_line.geoms for c in g.coords])[:, 1].max())
# error if the sides are cut square to the top instead of vertical (chair): x'(y) * h * sin(slope)
yg = np.linspace(55, 480, 200)
err_o = np.abs(np.gradient(xout(yg), yg) * h_o(yg) * np.sin(np.radians(slope(yg))))
err_i = np.abs(np.gradient(xin(yg), yg) * h_i(yg) * np.sin(np.radians(slope(yg))))
# L/R from parts/arms.json (shape only: the common +x shift of both arms removed)
LR = AJ["left_vs_right"]["stations"]; dW = np.array([s["d_width_mm"] for s in LR]); ys_lr = np.array([s["y"] for s in LR])
dO = np.array([s["d_outer_mm"] for s in LR]); dO_shape = dO - dO.mean(); dZ = np.array([s["d_z_mm"] for s in LR])
lr = dict(width_rms=float(np.sqrt(np.mean(dW ** 2))), width_rms_y180=float(np.sqrt(np.mean(dW[ys_lr >= 180] ** 2))),
          width_max_y180=float(np.abs(dW[ys_lr >= 180]).max()), outer_shape_rms=float(np.sqrt(np.mean(dO_shape ** 2))),
          outer_shape_max=float(np.abs(dO_shape).max()), z_max=float(np.abs(dZ).max()),
          h_outer_LmR_max=float(np.nanmax(np.abs(np.array([v for v in json.load(open("parts/arm_underside.json"))["left_vs_right"]["h_outer_L_minus_R_mm"] if v is not None])))))

# ---------------- plan drawing: (X, Y) = (chair y, -chair x): front to the right, outboard down ----------------
P = lambda xy: np.c_[np.asarray(xy)[:, 1], -np.asarray(xy)[:, 0]]
xb = float(px_[:, 0].max()) + 8.0                       # straight REF baseline, 8 mm outboard of the outermost point
pi = [dict(kind="cut", pts=P(px_), closed=True)]
pi.append(dict(kind="line", pts=[[y_back - 8, -xb], [y_front + 8, -xb]], style="hidden"))
pi.append(dict(kind="text", xy=(y_back + 150, -xb - 5), s=f"REF baseline: straight, parallel to the chair's fore-aft axis, {xb:.0f} mm from the chair centre line", size=6, color=K.REF, box=False))
for j, y in enumerate(ST):
    a_, b_ = float(xin(y)), float(xout(y))
    pi.append(dict(kind="line", pts=[[y, -a_ + 4], [y, -a_ - 3]], style="mark")); pi.append(dict(kind="line", pts=[[y, -b_ + 3], [y, -b_ - 4]], style="mark"))
    pi.append(dict(kind="line", pts=[[y, -b_ - 4], [y, -xb]], style="ref"))
    pi.append(dict(kind="text", xy=(y, -a_ + 8), s=f"S{j}", size=6, color=K.MARK, box=False))
    pi.append(dict(kind="dim", p1=(y, -xb), p2=(y, -b_), off=0.0, label=f"{xb - b_:.1f}", size=4.8))
    pi.append(dict(kind="text", xy=(y + 0.5, (-a_ - b_) / 2), s=f"{b_ - a_:.1f}", size=5, rot=90, box=False))
# front leg footprint + Domino
pi.append(dict(kind="line", pts=P(np.array(fl_plan.exterior.coords)), style="mark"))
pi.append(dict(kind="text", xy=(fl_c.y - 2, -fl_c.x + 28), s="FRONT LEG top\n(under the arm)", size=5.5, color=K.MARK))
pi.append(dict(kind="line", pts=P(np.array(da_plan.exterior.coords)), style="hidden"))
pi.append(dict(kind="text", xy=(float(da_c[1]) + 36, -float(da_c[0]) - 20), s="Domino mortise in the underside,\n10 x 24, 15 deep (ASSUMED)", size=5, color=K.REF))
# back leg cope
blc = np.array(bl_plan_line.coords) if bl_plan_line.geom_type == "LineString" else np.vstack([np.array(g.coords) for g in bl_plan_line.geoms])
pi.append(dict(kind="line", pts=P(blc[np.argsort(blc[:, 0])]), style="mark"))
pi.append(dict(kind="text", xy=(y_back - 20, -(x_o45 + x_i45) / 2), s="BACK LEG\nfront face:\nend coped\nto it", size=5.5, color=K.MARK, ha="right"))
if not dr_plan.is_empty:
    pi.append(dict(kind="line", pts=P(np.array(dr_plan.exterior.coords)), style="hidden"))
    pi.append(dict(kind="text", xy=(y_back + 4, -xin(y_back) + 13), s="Domino in the end (through the back leg), 24 x 10, depth ASSUMED", size=5, color=K.REF, ha="left"))
pi.append(dict(kind="text", xy=(220, -xin(220) + 12), s="INSIDE edge (toward the seat)", size=6.5, ha="left", box=False))
pi.append(dict(kind="text", xy=(260, -xout(260) - 18), s="OUTSIDE edge", size=6.5, box=False))
# overall dims
pi.append(dict(kind="dim", p1=(y_back, -xb), p2=(y_front, -xb), off=-16, label=f"overall length in plan (chair fore-aft) {fmt(L_plan)}"))
pi.append(dict(kind="dim", p1=(ci[1], -ci[0]), p2=(co[1], -co[0]), off=14, label=f"front end {fmt(np.hypot(co[0] - ci[0], co[1] - ci[1]))}", size=5.5))
pi.append(dict(kind="dim", p1=(y_back, -xb), p2=(fl_y[0], -xb), off=-28, label=f"end to front-leg rear face {fmt(fl_y[0] - y_back)}", size=5.5))
pi.append(dict(kind="text", xy=(y_back + 5, -xin(y_back) + 50),
    s="ARM, PLAN from straight above, 1:1  (make 2)\nShown: RIGHT arm, front to the right, outside edge down. Flip it for the left arm.\n"
      "Plan of the finished arm (side faces VERTICAL in the chair). Figures at each station: width (inside the arm) and the\n"
      "outside edge's distance from the REF baseline = the blank's jointed edge (arms_side is glued on that edge). Do NOT lay this\n"
      f"paper on the sloping top (it is the view from above: along the top the arm is {L_top:.0f} mm). Set out by stations instead: square\n"
      "S0-S9 across the top and the underside from arms_side, measure the offsets from the jointed edge at each, join with a batten.",
    size=6.5, ha="left", va="bottom"))

TBp = [
    "Plan: the v24 arm (parts/model_v24.glb ARM_R) projected straight down = parts/arms.json design: inner/outer top arrises triangulated from 8 overhead",
    "  photos of both arms, right arm and mirrored left averaged, smooth fits (rms 0.56 inner, 1.02 outer); front end a straight line (rms 3.2).",
    f"  Tolerance: max(1.6 mm, half the left/right difference) on the edges; front end along the arm +-2.5 mm. Sides vertical (underside json).",
    f"Back end: not seen from above (traces stop at y 66-68); the model carries the arm on to the back leg and copes it to the leg's front face (v24 joinery).",
    "  Scribe the end to the actual leg. Front leg footprint: v24 FLEG_R section 10 mm below its top (placement +-3 mm, joinery session).",
    "Joints: arm/front leg is hidden (the oval on the left arm top is a board feature, not a tenon: parts/joints.json); the model's vertical",
    "  10 mm Domino there is ASSUMED. Arm/back leg: a Domino end shows on the leg's rear face (measured); its depth into the arm is ASSUMED.",
    f"Left/right: one template, flipped. The model's arms are mirror images; measured width differs L-R {lr['width_rms_y180']:.1f} mm rms ({lr['width_max_y180']:.1f} max) from",
    f"  y 180 (more behind it, where the left inner trace follows a shading line), outer edge shape {lr['outer_shape_rms']:.1f} rms. Fit each to its own legs.",
    f"Generated by templates/arms.py from parts/arms.json, parts/arm_underside.json, {a.model} @ {REV}.",
]
KDp = [("Overall length in plan", L_plan, "chair fore-aft, coped end to front corner"),
       ("Width at S1 / S5 / S9", f"{xout(100) - xin(100):.1f} / {xout(300) - xin(300):.1f} / {xout(500) - xin(500):.1f} mm", "y 100 / 300 / 500"),
       ("Overall width in plan", W, "the arm sweeps outboard toward the front"),
       ("Front end", float(np.hypot(co[0] - ci[0], co[1] - ci[1])), "straight, inside corner 13.7 mm behind the outside one"),
       ("Front leg on the arm (rear..front)", f"{fl_y[0] - y_back:.1f} .. {fl_y[1] - y_back:.1f} mm from the end", "chair fore-aft"),
       ("Blank", f"{np.ceil(blank_t + 2):.0f} x {np.ceil(xb - px_[:, 0].min() + 2):.0f} x {np.ceil(blank_l + 6):.0f} mm", "thick x wide x long, edge jointed = REF baseline")]
spec_p = dict(name="arms_plan", title="ESSICK rocker - arm plan template (make 2, flip for the left)", rev=REV, items=pi, title_block=TBp, key_dims=KDp)

# ---------------- side drawing: (X, Y) = (chair y, chair z), seen from outside the right arm ----------------
z_lvl = float(np.floor(sd_[:, 1].min() / 5) * 5 - 10)
si = [dict(kind="cut", pts=sd_, closed=True)]
yo = np.linspace(y_back + 2, co[1] - 0.5, 160); ob = np.c_[yo, ztop_o(yo) - h_o(yo)]
si.append(dict(kind="line", pts=ob, style="ref", label="outer bottom arris: bevel the underside up to this line on the outer face", label_at=100, size=5.5))
si.append(dict(kind="line", pts=[[y_back - 10, z_lvl], [y_front + 10, z_lvl]], style="hidden"))
si.append(dict(kind="text", xy=(y_back + 110, z_lvl - 4), s=f"LEVEL line: {z_lvl:.0f} mm above the floor (chair standing on a level floor at rest)", size=6, color=K.REF, box=False))
for j, y in enumerate(ST):
    t, bo, bi = float(ztop_o(y)), float(ztop_o(y) - h_o(y)), float(ztop_o(y) - h_i(y))
    si.append(dict(kind="line", pts=[[y, t - 3], [y, t + 4]], style="mark")); si.append(dict(kind="line", pts=[[y, bi - 4], [y, bi + 3]], style="mark"))
    si.append(dict(kind="line", pts=[[y, z_lvl], [y, bi - 4]], style="ref"))
    si.append(dict(kind="text", xy=(y, t + 9), s=f"S{j}\n{along(y):.0f}", size=5.5, color=K.MARK, box=False))
    si.append(dict(kind="text", xy=(y + 4, (t + bo) / 2), s=f"{h_o(y):.1f}", size=5, rot=90, box=False))
    if j % 2 == 0: si.append(dict(kind="dim", p1=(y, z_lvl), p2=(y, t), off=0.0, label=f"{t - z_lvl:.1f}", size=4.8))
# joints
for l in fl_side:
    for g in (l.geoms if hasattr(l, "geoms") else [l]):
        if g.length > 2: si.append(dict(kind="line", pts=np.array(g.coords), style="mark"))
si.append(dict(kind="text", xy=(yc, fl_top - 52), s="FRONT LEG faces\n(at the leg's centre)", size=5.5, color=K.MARK))
for ls_, st in ((bl_side_o, "mark"), (bl_side_i, "hidden")):
    for l in ls_:
        for g in (l.geoms if hasattr(l, "geoms") else [l]):
            if g.length > 2: si.append(dict(kind="line", pts=np.array(g.coords), style=st))
si.append(dict(kind="text", xy=(y_back - 14, ztop_o(y_back) + 22), s="BACK LEG front face\n(solid: at the outer face,\ndashed: at the inner face)", size=5.5, color=K.MARK, ha="right"))
for pg in (da_side, dr_side):
    if not pg.is_empty:
        g = pg if pg.geom_type == "Polygon" else max(pg.geoms, key=lambda q: q.area)
        si.append(dict(kind="line", pts=np.array(g.exterior.coords), style="hidden"))
si.append(dict(kind="text", xy=(float(da_c[1]) + 30, float(zb(da_c[0], da_c[1])) + 24), s="Domino mortise\n15 deep (ASSUMED)", size=5, color=K.REF))
si.append(dict(kind="text", xy=(float(dr_plan.centroid.y) + 36, ztop_o(60) + 14), s="Domino from the back leg, depth ASSUMED", size=5, color=K.REF))
# dims
si.append(dict(kind="dim", p1=(y_back, z_lvl), p2=(y_front, z_lvl), off=-14, label=f"overall length (chair fore-aft) {fmt(L_plan)}"))
for y in (y_back + 5, 500.0):
    si.append(dict(kind="dim", p1=(y, ztop_o(y) - h_i(y)), p2=(y, ztop_o(y)), off=(-10 if y < 100 else 12),
                   label=f"{frac32(h_i(y))} ({h_i(y):.1f}) inner", size=5))
si.append(dict(kind="text", xy=(y_back + 150, ztop_o(y_back + 150) + 46),
    s="ARM, SIDE PROFILE from outside, 1:1  (make 2)\nShown: RIGHT arm's outer face, front to the right. Flip it for the left arm.\n"
      "Heavy line = top and the INNER bottom arris (the deepest line, cut to it first); the underside slopes across,\n"
      "up to the thin outer-bottom-arris line on the outer face. Small figures: thickness on the outer face (vertical).\n"
      f"Glue it on the blank's jointed EDGE (the edge face is the REF baseline of arms_plan), the arm's length at {board_pitch:.0f} deg to the edge\n"
      "line of the blank (it fits a board this thick); cut the profile square to that face. S-labels: station / mm along the top from the end.\n"
      "Then set out the plan (arms_plan) on top AND underneath; the sides are VERTICAL in the chair (LEVEL line level), not square to the\n"
      f"sloping top: saw outside both lines and plane to them (square to the top would put the bottom edge up to {max(err_o.max(), err_i.max()):.1f} mm off).",
    size=6.5, ha="left", va="bottom"))
TBs = [
    "Top line: parts/arms.json design outer top arris (triangulated, z +-2 mm; fit rms 0.08). Underside: parts/arm_underside.json design: outer and",
    "  inner bottom arrises traced on side photos of both arms (L/R mean), straight across between them (tools/build_model.py since v21).",
    f"  Tolerance outer {min(UJ['tolerance_outer_mm']):.1f}-{max(UJ['tolerance_outer_mm']):.1f} mm, inner {min(UJ['tolerance_inner_mm']):.1f}-{max(UJ['tolerance_inner_mm']):.1f} mm. Not seen: back 20 mm (y 40-60) and the front end beyond y 490,",
    "  continued straight (readings M6 front-end thickness, M15 inside face). Edge radii not measured (M16): drawn sharp.",
    f"Silhouette = v24 ARM_R seen along the chair's x axis. L/R: underside h_outer L-R <= {lr['h_outer_LmR_max']:.1f} mm; tops differ up to {lr['z_max']:.1f} mm at the front",
    "  (asymmetry or a roll of the frame): one template, flipped. Joints as on arms_plan (front leg placement +-3 mm; Dominos ASSUMED depth).",
    f"Generated by templates/arms.py from parts/arms.json, parts/arm_underside.json, {a.model} @ {REV}.",
]
KDs = [("Thickness, outer face, at the back leg", float(h_o(y_cope)), f"vertical, y {y_cope:.0f} (cope); inner {h_i(y_cope):.1f}"),
       ("Thickness, outer face, front end", float(h_o(co[1] - 5)), f"vertical; inner {h_i(co[1] - 5):.1f}  (M6 open)"),
       ("Thickness square to the top, back / front", f"{h_o(y_cope) * np.cos(np.radians(slope(y_cope))):.1f} / {h_o(co[1] - 5) * np.cos(np.radians(slope(co[1] - 5))):.1f} mm", "outer face"),
       ("Top rises, end to front", float(ztop_o(co[1]) - ztop_o(y_back)), f"slope {slope(y_back):.0f} deg at the back, {slope(co[1]):.0f} at the front"),
       ("Length along the top", L_top, "outer top arris, end to front corner"),
       ("Profile fits a board", f"{blank_t:.1f} x {blank_l:.0f} mm", f"min rectangle, at {board_pitch:.0f} deg to level")]
spec_s = dict(name="arms_side", title="ESSICK rocker - arm side profile template (make 2, flip for the left)", rev=REV, items=si, title_block=TBs, key_dims=KDs)

os.makedirs(a.out, exist_ok=True)
Lp = K.write_all(spec_p, a.out); Ls = K.write_all(spec_s, a.out)

# ---------------- geometry for the overlay ----------------
yt = np.linspace(D["y_back"], ci[1], 120); yo2 = np.linspace(D["y_back"], co[1], 120); xf = np.linspace(ci[0], co[0], 20)
top3d = np.vstack([np.c_[xin(yt), yt, ztop_i(yt)], np.c_[xf, np.polyval(pf, xf), np.interp(xf, [ci[0], co[0]], [ztop_i(ci[1]), ztop_o(co[1])])],
                   np.c_[xout(yo2), yo2, ztop_o(yo2)][::-1]])
geom = dict(top_outline_3d_right=top3d.tolist(), plan_xy=px_.tolist(), side_yz=sd_.tolist(),
            outer_bottom_yz=ob.tolist(), stations_y=ST.tolist(), y_back=y_back, y_front=y_front, y_cope=y_cope,
            front_leg=dict(centre_xy=[fl_c.x, fl_c.y], y_range=list(fl_y), top_z=fl_top, plan=np.array(fl_plan.exterior.coords).tolist()),
            lengths=dict(plan=L_plan, along_top=L_top, plan_width=W, blank_side=[blank_t, blank_l], board_pitch_deg=board_pitch, ref_baseline_x=xb,
                         blank=[float(np.ceil(blank_t + 2)), float(np.ceil(xb - px_[:, 0].min() + 2)), float(np.ceil(blank_l + 6))]),
            thickness_outer=dict(back=float(h_o(y_cope)), front=float(h_o(co[1] - 5))), square_cut_err_mm=[float(err_o.max()), float(err_i.max())],
            left_right=lr, tiles=dict(plan=[Lp["rows"], Lp["cols"]], side=[Ls["rows"], Ls["cols"]]))
json.dump(geom, open(a.geom_json or f"{a.out}/arms_geom.json", "w"), indent=1)

# ---------------- checks vs the parts files ----------------
from shapely.geometry import Point
pl_b = LineString(np.vstack([px_, px_[:1]])); sd_b = LineString(np.vstack([sd_, sd_[:1]]))
yc_ = np.linspace(80, 470, 40)
e_in = max(pl_b.distance(Point(xin(y), y)) for y in yc_); e_out = max(pl_b.distance(Point(xout(y), y)) for y in yc_)
e_top = max(sd_b.distance(Point(y, ztop_o(y))) for y in yc_); e_bot = max(sd_b.distance(Point(y, ztop_o(y) - h_i(y))) for y in yc_)
print(f"arms: plan length {L_plan:.1f} mm ({frac32(L_plan)}), along top {L_top:.1f}, plan width {W:.1f}, y {y_back:.1f}..{y_front:.1f}, cope at y <= {y_cope:.1f}")
print(f"  thickness outer: back {h_o(y_cope):.1f} (y {y_cope:.0f}) front {h_o(co[1] - 5):.1f}; inner back {h_i(y_cope):.1f} front {h_i(co[1] - 5):.1f}")
print(f"  silhouette vs parts curves (y 80-470, max mm): inner {e_in:.2f} outer {e_out:.2f} top {e_top:.2f} bottom(inner) {e_bot:.2f}")
print(f"  front leg y {fl_y[0]:.1f}..{fl_y[1]:.1f} centre x {fl_c.x:.1f}; Domino AR centre {da_c.round(1).tolist()}; blank side {blank_t:.1f} x {blank_l:.1f} at {board_pitch:.1f} deg, baseline x {xb:.1f}")
print(f"  square-cut error max outer {err_o.max():.2f} inner {err_i.max():.2f}; L/R {json.dumps({k: round(v, 2) for k, v in lr.items()})}")
print(f"  tiles: plan {Lp['rows']}x{Lp['cols']}, side {Ls['rows']}x{Ls['cols']}")
