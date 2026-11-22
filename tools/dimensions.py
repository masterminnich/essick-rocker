"""USAGE: tools/py.sh tools/dimensions.py [--model 24] [--check]

Writes parts/model_vN_dimensions.json: the named dimensions the review viewer draws on the chair and asks Joe to check.

Rule: every dimension is traceable to a parts file. For each one this script
  1. takes the station (where along the part) and the expected value from a parts file (`file`, `file_key`, `file_value_mm`),
  2. finds the two end points ON THE MODEL (parts/model_vN.glb): a ray through the named part at that station
     (entry and exit point), a mesh vertex picked by a rule, or a point the parts file itself gives in chair coordinates,
  3. stores value_mm = the straight distance between the two end points (or, for kind "height", the end point's z),
     and `agrees_mm` = value_mm - file_value_mm. A dimension whose end points cannot be found on the model is left out.

Chair frame (PLAN.md): mm, +X chair's right, +Y forward, +Z up, table top Z = 0. Symmetric dimensions are placed on the
RIGHT part with "mirror": true (the viewer draws them on the left part with x -> -x when that part is tapped).
Light: loads one 1 MB glb and casts a few hundred rays. Run through tools/py.sh (trimesh).
"""
import argparse, json, subprocess, sys
from pathlib import Path
import numpy as np
import trimesh

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from rocker.sideframe import side_plane, to_plane, from_plane  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--model", type=int, default=24)
ap.add_argument("--check", action="store_true", help="print the table only, write nothing")
a = ap.parse_args()

J = lambda p: json.load(open(ROOT / p))
GLB = f"parts/model_v{a.model}.glb"
scene = trimesh.load(ROOT / GLB)
M = {}
for node in scene.graph.nodes_geometry:
    T, g = scene.graph[node]; m = scene.geometry[g].copy(); m.apply_transform(T); M[node] = m


def _ray(part, start, d):
    """Moller-Trumbore against every triangle of the part (no spatial index needed: <= 16k faces): hit distances t >= 0"""
    tri = M[part].triangles; e1 = tri[:, 1] - tri[:, 0]; e2 = tri[:, 2] - tri[:, 0]
    h = np.cross(d, e2); det = np.einsum("ij,ij->i", e1, h); ok = np.abs(det) > 1e-12; inv = np.where(ok, 1 / np.where(ok, det, 1), 0)
    s = start - tri[:, 0]; uu = np.einsum("ij,ij->i", s, h) * inv; q = np.cross(s, e1); vv = (q @ d) * inv; t = np.einsum("ij,ij->i", e2, q) * inv
    hit = ok & (uu >= 0) & (vv >= 0) & (uu + vv <= 1) & (t >= 0)
    return np.sort(t[hit])


def line_hits(part, o, d):
    """every point where the infinite line through o along d crosses the part's surface, in order along d"""
    d = np.asarray(d, float); d /= np.linalg.norm(d); start = np.asarray(o, float) - d * 4000
    t = _ray(part, start, d)
    if not len(t): return []
    t = t[np.r_[True, np.diff(t) > 1e-3]]                      # a ray through a shared edge reports the point twice
    return [start + ti * d for ti in t]


def through(part, o, d):
    """entry and exit points of the line through the part (outermost pair)"""
    h = line_hits(part, o, d)
    if len(h) < 2: raise LookupError(f"no crossing of {part} at {np.round(o, 1)} along {d}")
    return h[0], h[-1]


def first_hit(part, o, d):
    """first surface point met going from o along d (o outside the part)"""
    d = np.asarray(d, float); d /= np.linalg.norm(d); o = np.asarray(o, float); t = _ray(part, o, d)
    if not len(t): raise LookupError(f"ray from {np.round(o, 1)} misses {part}")
    return o + t[0] * d


def interp_tab(tab, x):
    tab = np.asarray(tab, float); return float(np.interp(x, tab[:, 0], tab[:, 1]))


def poly_y(c, y):                                             # seat_edge.json polys are in (y - 250)
    return float(np.polyval(c, y - 250.0))


# side-plane frame of the rockers (work/ is not in git: read it from this checkout or from the main checkout)
def _plane_files():
    roots = [ROOT]
    try:
        common = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--path-format=absolute", "--git-common-dir"], capture_output=True, text=True).stdout.strip()
        if common: roots.append(Path(common).parent)
    except OSError:
        pass
    for r in roots:
        f = [r / "work/parts/rockerL/o_plane.json", r / "work/parts/rockerR/o_plane.json"]
        if all(p.exists() for p in f): return tuple(str(p) for p in f)
    raise SystemExit("work/parts/rocker{L,R}/o_plane.json not found (needed for the rocker's side-plane frame)")


PLANES = _plane_files()
_o, U_R, V_R, N_R = side_plane(+1, PLANES)                   # right rocker: u forward along it, v up, n outward


def _to_pl(X):
    d = np.atleast_2d(X) - _o; return np.stack([d @ U_R, d @ V_R, -(d @ N_R)], 1)


def _from_pl(u, v, dd):
    return _o + u * U_R + v * V_R - dd * N_R


# ---------------------------------------------------------------------------------------------------- the dimensions
DIMS, SKIPPED = [], []
GROUPS = {1: "Check these first · we guessed", 2: "Tape and photos disagree", 3: "From photos and tape"}
mm_in = lambda mm: mm / 25.4


def add(id, part, name, p1, p2, *, source, tol, group, file, file_key, file_value, note, m=None, kind="length",
        mirror=True, look=None, extra=None, value=None):
    p1 = np.asarray(p1, float); p2 = np.asarray(p2, float)
    v = float(np.linalg.norm(p2 - p1)) if value is None else float(value)
    d = dict(id=id, part=part, name=name, kind=kind, p1=[round(float(c), 2) for c in p1], p2=[round(float(c), 2) for c in p2],
             value_mm=round(v, 2), source=source, tolerance_mm=tol, group=group, group_name=GROUPS[group],
             file=file, file_key=file_key, file_value_mm=file_value,
             agrees_mm=None if file_value is None else round(v - file_value, 2), mirror=mirror, note=note)
    if m: d["reading"] = m
    if look: d["look_from"] = look                             # which side the viewer turns the chair to (chair-frame direction to the camera)
    if extra: d.update(extra)
    DIMS.append(d)


def attempt(fn):
    try:
        fn()
    except (LookupError, KeyError, ValueError, IndexError) as e:
        SKIPPED.append(f"{fn.__name__}: {e}")


AU = J("parts/arm_underside.json")["design"]; AY = np.array(AU["y"])


def arm_section_x(y):
    """outer and inner x of the right arm's top at station y (slice of the mesh)"""
    s = M["ARM_R"].section(plane_origin=[0, y, 0], plane_normal=[0, 1, 0])
    if s is None: raise LookupError(f"ARM_R has no section at y {y}")
    V = s.vertices; top = V[V[:, 2] > V[:, 2].max() - 6]
    return float(top[:, 0].max()), float(top[:, 0].min())


def arm_drop(y, side):
    xo, xi = arm_section_x(y); x = xo - 0.6 if side == "outer" else xi + 0.6
    return through("ARM_R", [x, y, 600], [0, 0, -1])


# ---- group 1: we guessed or could not settle ----------------------------------------------------------------------------
def m6_arm_front():
    y = 500.0; top, bot = arm_drop(y, "outer"); h = float(np.interp(y, AY, AU["h_outer_mm"])); tol = float(np.interp(y, AY, AU["tolerance_outer_mm"]))
    add("arm_front_thickness", "ARM_R", "Arm thickness, front end", top, bot, source="guess", tol=round(tol, 1), group=1, m="M6",
        file="parts/arm_underside.json", file_key=f"design.h_outer_mm at y {y:.0f}", file_value=round(h, 2), look=[1, 0.25, 0.1],
        note="Outside face, straight up and down, about 1 1/4 in. back from the front tip. No photo sees the front end, so the model carries the line straight on.")


def m15_arm_inner(y, tag):
    def f():
        top, bot = arm_drop(y, "inner"); h = float(np.interp(y, AY, AU["h_inner_mm"])); tol = float(np.interp(y, AY, AU["tolerance_inner_mm"]))
        add(f"arm_inner_thickness_{tag}", "ARM_R", f"Arm thickness, inside face, {'near the back leg' if tag == 'back' else 'near the front'}",
            top, bot, source="photos", tol=round(tol, 1), group=1, m="M15", file="parts/arm_underside.json", file_key=f"design.h_inner_mm at y {y:.0f}",
            file_value=round(h, 2), look=[-1, 0.3, 0.15],
            note="Inside face (toward the seat), straight up and down. The photos see this face only from one angle; the left and right arms read differently.")
    f.__name__ = f"m15_arm_inner_{tag}"; return f


RS = J("parts/rocker_section.json")["design"]; RU = np.array(RS["u"])


def rocker_across(u):
    T = float(np.interp(u, RU, RS["T_mm"])); dout = float(np.interp(u, RU, RS["d_outer_mm"]))
    c = _from_pl(u, 0.0, dout + T / 2)                       # inside the rocker at this u, at table height; go up to find its top and bottom
    zz = through("ROCKER_R", [c[0], c[1], 400], [0, 0, -1]); zm = (zz[0][2] + zz[1][2]) / 2
    p, q = through("ROCKER_R", [c[0], c[1], zm], -N_R)         # outer face -> inner face, square to the side plane
    return p, q, T


def m12_rocker_mid():
    u = 340.0; p, q, T = rocker_across(u)
    add("rocker_thickness_mid", "ROCKER_R", "Rocker thickness, between the legs", p, q, source="photos", tol=1.6, group=1, m="M12",
        file="parts/rocker_section.json", file_key=f"design.T_mm at u {u:.0f}", file_value=round(T, 2), look=[0.35, 0.2, 1],
        note="Across the rocker, outside face to inside face, about a foot in front of the back leg. The photos may read the eased corners short; one caliper reading settles it.")


def m13_seat_back_edge():
    SB = J("parts/seat_back.json")["design"]; ax = 150.0; X = np.array(SB["abs_x"])
    y = float(np.interp(ax, X, SB["top_arris"]["y"])); z = float(np.interp(ax, X, SB["top_arris"]["z"]))
    p = first_hit("SEAT", [ax, y + 4, z + 60], [0, 0, -1])      # on the model's top surface just in front of the arris
    ER = J("parts/edge_radii.json")["families"]["seat_top_back_edge"]
    add("seat_back_edge_round", "SEAT", "Seat back edge between the slats: how round?", [ax, y, z], [ax, y, z], kind="radius", value=0.0,
        source="guess", tol=None, group=1, m="M13", file="parts/seat_back.json + parts/edge_radii.json",
        file_key=f"design.top_arris at |x| {ax:.0f}; families.seat_top_back_edge ({ER['short']})", file_value=0.0, look=[0.2, -1, 0.9],
        note="Where the seat top meets its back face, between a side slat and the back leg. The model has a sharp corner; the photos hint at a round of 3/16 in. or more, or a top that rolls off. A coin held in the corner tells.",
        extra=dict(surface_check_mm=round(float(np.linalg.norm(p[[1, 2]] - [y + 4, z])), 2)))


def seat_front_corner():
    SF = J("parts/seat_front.json")["design"]; c = SF["corner"]; y = 515.0
    SFF = J("parts/seat_front_face.json")["design"]
    zt = interp_tab(SFF["top_of_roll_z_of_abs_x"], 250.0) - 6.0
    p, q = through("SEAT", [0, y, zt], [-1, 0, 0])
    add("seat_front_corners", "SEAT", "Seat width across the front corners", p, q, source="photos", tol=2.0 * 2, group=1, m="seat front corner",
        file="parts/seat_front.json", file_key="design.corner.abs_x (x2)", file_value=round(2 * c["abs_x"], 2), look=[0.1, 1, 0.5],
        note="Outside to outside of the seat, just in front of the front legs, a little below the top. The left side traced 3 mm narrower than the model there; the right would not solve.")


def m16_rocker_tail():
    ER = J("parts/edge_radii.json")["families"]["rocker_ends_in_plan"]
    V = M["ROCKER_R"].vertices; tip = V[np.argmin(V[:, 1])]
    add("rocker_tail_round", "ROCKER_R", "Rocker tail tip: corner round, seen from above", tip, tip, kind="radius", value=0.0, source="photos",
        tol=ER["tol_mm"], group=1, m="M16", file="parts/edge_radii.json", file_key="families.rocker_ends_in_plan", file_value=0.0, look=[0.3, -0.6, 1],
        note=f"The model's tail tip is square. One photo reads its corners as rounds of about {ER['radius_mm']} mm (1/8 in.). A coin or a radius gauge tells.",
        extra=dict(photos_mm=ER["radius_mm"]))


def m16_arm_edge():
    ER = J("parts/edge_radii.json")["families"]["arm"]; y = 300.0; xo, _ = arm_section_x(y)
    top = first_hit("ARM_R", [xo - 0.6, y, 800], [0, 0, -1])
    add("arm_edge_round", "ARM_R", "Arm top outside edge: how round?", top, top, kind="radius", value=0.0, source="guess", tol=None, group=1, m="M16",
        file="parts/edge_radii.json", file_key="families.arm (" + ER["short"] + ")", file_value=0.0, look=[1, 0.2, 0.6],
        note="The arm's top outside corner. No photo shows it close enough; the model has it sharp.")


def m11_domino():
    D = J("parts/dominos.json"); x = M["DOMINO_FR"].vertices[:, 0].max() - 3.0     # 3 mm in from its outer end (the end itself is rounded over)
    F = M["DOMINO_FR"].section(plane_origin=[x, 0, 0], plane_normal=[1, 0, 0]).vertices
    C = F - F.mean(0); w, E = np.linalg.eigh(C.T @ C); t = C @ E[:, -1]; p, q = F[np.argmin(t)], F[np.argmax(t)]
    add("domino_end", "DOMINO_FR", "Domino end on the front leg, long way", p, q, source="guess", tol=D["visible_end_mm"]["reading_tolerance_mm"], group=1, m="M11",
        file="parts/dominos.json", file_key="design.tenon_section_mm[0]", file_value=float(D["design"]["tenon_section_mm"][0]), look=[1, 0.15, 0.1],
        note="The Domino's end where it shows on the outside of the front leg under the seat. The photos read 25-26 mm with the glue line; we took it as a 10 mm Festool Domino.")


def m4_slat_thickness():
    S = J("parts/slats.json"); z = 640.0
    f = [line_hits("SLAT_C", [0, 0, zz], [0, 1, 0])[-1] for zz in (z - 20, z + 20)]   # front face, 20 mm below and above
    tng = (f[1] - f[0]) / np.linalg.norm(f[1] - f[0]); nrm = np.array([0, tng[2], -tng[1]])   # square to the slat in the side view
    hy = line_hits("SLAT_C", [0, 0, z], [0, 1, 0]); mid = (hy[0] + hy[-1]) / 2; p, q = through("SLAT_C", mid, nrm)
    add("slat_thickness", "SLAT_C", "Centre slat thickness", p, q, source="guess", tol=2.0, group=1, m="M4",
        file="parts/slats.json", file_key="thickness_mm", file_value=float(S["thickness_mm"]), look=[1, 0.1, 0.2],
        note="Front face to back face, half way up. The photos only say 'about 10 mm'; it is the thickness of the bent lamination stack.")


# ---- group 2: two sources disagree ------------------------------------------------------------------------------------
def m3_crest_height():
    C = J("parts/crest.json"); x = -75.0
    ev = lambda c, xx: sum(ck * abs(xx) ** (2 * k) for k, ck in enumerate(c))
    tr, br = C["edges"]["top_rear"]["design"], C["edges"]["bottom_rear"]["design"]
    p = [x, ev(tr["y_even_poly"], x), ev(tr["z_even_poly"], x)]; q = [x, ev(br["y_even_poly"], x), ev(br["z_even_poly"], x)]
    chk = C["section"]["height_tape_check"]
    add("crest_height", "CREST", "Crest rail height, back face", p, q, source="photos", tol=C["edges"]["top_rear"]["tol_mm"] + 0.6, group=2, m="M3",
        file="parts/crest.json", file_key="edges.top_rear / bottom_rear design at x -75 (section.height_tape_check.model_at_x-75_mm)",
        file_value=chk["model_at_x-75_mm"], look=[-0.2, -1, 0.15], mirror=False,
        note="Top edge to bottom edge on the back face, in the gap between the left slat and the centre slat. The tape (photo 1555) read 3 1/16 in.; the photos say less. A tape hooked over a rounded edge reads long.",
        extra=dict(tape_mm=chk["tape_IMG_1555_mm"]))


def m5_slat_width():
    C = J("parts/crest.json"); P = J("parts/model_v%d_params.json" % a.model)["parts"]["slats"]
    z = C["key_points"]["bottom_centre_z"]["mm"] - 15.0
    hy = line_hits("SLAT_C", [0, 0, z], [0, 1, 0]); ym = (hy[0][1] + hy[-1][1]) / 2
    p, q = through("SLAT_C", [0, ym, z], [1, 0, 0])
    add("slat_width_top", "SLAT_C", "Centre slat width, just under the crest", p, q, source="photos", tol=1.0, group=2, m="M5",
        file=f"parts/model_v{a.model}_params.json (from parts/slats.json)", file_key="parts.slats.centre_width_mm.under_crest",
        file_value=round(P["centre_width_mm"]["under_crest"], 2), look=[0, -1, 0.1], mirror=False,
        note="Across the centre slat about 5/8 in. below the crest. The tape (photo 1553) read 3 7/8 in.; the edge traces say a little wider.",
        extra=dict(tape_mm=round(3.87 * 25.4, 1)))


def rocker_ends_pts():
    E = J(f"parts/model_v{a.model}_params.json")["parts"]["rocker"]
    V = M["ROCKER_R"].vertices; P = _to_pl(V)
    RV = J("parts/rocker_profile.json")["right_vs_left"]        # the landmarks are in the left side-plane frame; the build moves them half way (build_model.to_mean)
    th = np.radians(RV["rotation_deg"] / 2); c, s_ = np.cos(th), np.sin(th)
    def to_mean(q):
        d = np.asarray(q, float) - [RV["shift_u_mm"] / 2, RV["shift_v_mm"] / 2]; return [c * d[0] + s_ * d[1], -s_ * d[0] + c * d[1]]
    def pick(uv):
        uv = to_mean(uv)
        dd = np.hypot(P[:, 0] - uv[0], P[:, 1] - uv[1]); near = dd < 4
        if not near.any(): raise LookupError(f"no rocker vertex near uv {uv}")
        dmin = P[near, 2].min(); ok = near & (P[:, 2] < dmin + 0.6)
        return V[ok][np.argmin(dd[ok])]
    return pick(E["tail_tip_uv"]), pick(E["nose_top_corner_uv"]), E


def m8_rocker_length(side):
    def f():
        t, n, E = rocker_ends_pts()
        photos = {"L": 1118.6, "R": 1112.3}[side]
        if side == "L": t, n = t * [-1, 1, 1], n * [-1, 1, 1]
        add(f"rocker_length_{side}", f"ROCKER_{side}", f"{'Left' if side == 'L' else 'Right'} rocker, tail tip to front top corner", t, n, source="photos", tol=2.0, group=2,
            m="M8", file=f"parts/model_v{a.model}_params.json (from parts/rocker_ends.json)", file_key="parts.rocker.tail_tip_to_nose_top_corner_mm",
            file_value=round(E["tail_tip_to_nose_top_corner_mm"], 2), look=[1 if side == "R" else -1, 0, 0.1], mirror=False,
            note=f"Straight line, outside face, from the tip of the tail to the top corner of the front end. The model uses one shape for both rockers; this rocker's own photos say {photos} mm. It is also the one check on the scale of the whole model.",
            extra=dict(photos_this_side_mm=photos))
    f.__name__ = f"m8_rocker_length_{side}"; return f


def m9_seat_side(side):
    def f():
        SE = J("parts/seat_edge.json")["design"]; y = 434.0
        hw = poly_y(SE["top_half_width_of_y"]["poly_in_(y-250)"], y); zf = poly_y(SE["top_z_of_y"]["poly_in_(y-250)"], y)
        top = first_hit("SEAT", [hw - 1.0, y, 455], [0, 0, -1])
        if side == "L": top = top * [-1, 1, 1]
        add(f"seat_side_height_{side}", "SEAT", f"Seat side edge off the table, {'left' if side == 'L' else 'right'}, behind the front leg", top, [top[0], top[1], 0.0],
            kind="height", value=top[2], source="photos", tol=1.5, group=2, m="M9", file="parts/seat_edge.json",
            file_key=f"design.top_z_of_y at y {y:.0f} (fit beyond its valid y 110-400)", file_value=round(zf, 2), look=[1 if side == "R" else -1, 0.4, 0.1], mirror=False,
            note="Chair standing on the flat bench: bench top up to the top corner of the seat's side edge, just behind the front leg. The photos say the right side sits 3/16 in. lower than the left; the model uses the average.",
            extra=dict(photos_right_minus_left_mm=[-5.9, -3.7]))
    f.__name__ = f"m9_seat_side_{side}"; return f


def m14_rocker_top(where):
    def f():
        y = 620.0 if where == "nose" else -435.0; zf = 124.6 if where == "nose" else 185.4
        s = M["ROCKER_R"].section(plane_origin=[0, y, 0], plane_normal=[0, 1, 0]); Vs = s.vertices
        top = Vs[np.argmax(Vs[:, 2])]                             # the highest point of the rocker's section at this y
        add(f"rocker_top_{where}", "ROCKER_R", f"Rocker top edge off the table, {'front end' if where == 'nose' else 'near the tail'}", top, [top[0], top[1], 0.0],
            kind="height", value=top[2], source="photos", tol=2.0, group=2, m="M14", file="parts/rocker_profile.json + parts/rocker_ends.json (top outline; HUB_HANDOFF.md M14 quotes the model value)",
            file_key=f"z at y {y:.0f}", file_value=zf, look=[1, 0, 0.05],
            note=("Chair on the flat bench: bench top up to the rocker's top edge " + ("at the front top corner." if where == "nose" else "about 2 in. in from the tail tip.") +
                  " The photos cannot fix the rocker's tilt better than about 1/8 in. over its length; both rockers, please."))
    f.__name__ = f"m14_rocker_top_{where}"; return f


# ---- group 3: from photos, some with a tape check -----------------------------------------------------------------------
def m1_seat_front():
    F = J("parts/seat_front_face.json")["design"]; ax = 10.0
    zt = interp_tab(F["top_of_roll_z_of_abs_x"], ax); zb = interp_tab(F["bottom_arris_z_of_abs_x"], ax); yb = interp_tab(F["bottom_arris_y_of_abs_x"], ax)
    h = interp_tab(F["face_height_top_of_roll_to_bottom_arris_mm"]["of_abs_x"], ax)
    add("seat_front_thickness", "SEAT", "Seat front edge thickness, beside the middle", [ax, yb, zt], [ax, yb, zb], source="photos", tol=2.0, group=3, m="M1",
        file="parts/seat_front_face.json", file_key=f"design.face_height_top_of_roll_to_bottom_arris_mm at |x| {ax:.0f}", file_value=h, look=[0.25, 1, 0.1],
        note="Straight up the front face, 3/8 in. to one side of the point in the middle of the seat front: bottom corner to the top of the rolled edge.")


def m2_seat_side():
    SE = J("parts/seat_edge.json"); D = SE["design"]; y = 250.0
    xt = poly_y(D["top_half_width_of_y"]["poly_in_(y-250)"], y); zt = poly_y(D["top_z_of_y"]["poly_in_(y-250)"], y); zb = poly_y(D["bottom_z_of_y"]["poly_in_(y-250)"], y)
    top = first_hit("SEAT", [xt - 0.8, y, 600], [0, 0, -1])
    add("seat_side_thickness", "SEAT", "Seat side edge thickness, half way back", top, [top[0], y, zb], source="photos", tol=SE["edge_thickness"]["tol_mm"], group=3, m="M2",
        file="parts/seat_edge.json", file_key="edge_thickness.vertical_top_to_bottom_arris_mm.mean (design top_z - bottom_z at y 250)",
        file_value=round(zt - zb, 2), look=[1, 0.25, -0.15],
        note="On the side of the seat half way between the legs, straight up: from the bottom corner of the under-bevel to the top corner.")


def m7_crest_top():
    C = J("parts/crest.json"); V = M["CREST"].vertices; c = V[np.argmax(V[:, 2])]
    top = first_hit("CREST", [0.0, c[1], 1300], [0, 0, -1])
    add("crest_top_height", "CREST", "Top of the crest off the table, in the middle", top, [top[0], top[1], 0.0], kind="height", value=top[2], source="photos",
        tol=C["key_points"]["top_centre_z"]["tol_mm"] + 1.0, group=3, m="M7", file="parts/crest.json + model params overall.bbox_max_mm",
        file_key="highest point of the crest at x 0 (key_points.top_centre_z is the REAR arris, 1078.5)",
        file_value=J(f"parts/model_v{a.model}_params.json")["parts"]["overall"]["bbox_max_mm"][2], look=[0.3, 1, 0.15], mirror=False,
        note="Chair on the flat bench: bench top up to the highest point of the crest rail in the middle. The tallest number on the chair, and a check on the scale of the whole model.")


def m10_scallop():
    F = J("parts/seat_front.json")["design"]; FF = J("parts/seat_front_face.json")["design"]
    tab = np.asarray(F["front_y_of_abs_x"], float); tip = np.array([0.0, F["pommel_tip"]["y"]]); cor = np.array([F["corner"]["abs_x"], F["corner"]["y"]])
    d = cor - tip; nrm = np.array([d[1], -d[0]]) / np.linalg.norm(d); gap = (tab - tip) @ nrm
    i = int(np.argmax(np.where((tab[:, 0] > 20) & (tab[:, 0] < 250), gap, -1))); P = tab[i]; Q = tip + ((P - tip) @ d) / (d @ d) * d
    z = interp_tab(FF["top_of_roll_z_of_abs_x"], P[0])
    add("seat_scallop", "SEAT", "Seat front: depth of the hollow", [P[0], P[1], z], [Q[0], Q[1], z], source="photos", tol=2.5, group=3, m="M10",
        file="parts/seat_front.json", file_key="design.front_y_of_abs_x (straightedge from pommel_tip to corner)", file_value=21.3, look=[0.1, 0.5, 1],
        note="Lay a straightedge across the front of the seat touching the middle point and one front corner; this is the biggest gap to the seat's front edge in the hollow.")


def tail_thickness():
    u = -470.0; p, q, T = rocker_across(u)
    add("rocker_thickness_tail", "ROCKER_R", "Rocker thickness near the tail tip", p, q, source="taped", tol=1.6, group=3, m=None,
        file="parts/rocker_section.json", file_key=f"design.T_mm at u {u:.0f} (tape IMG_1493: 30.5)", file_value=round(T, 2), look=[0.4, -0.5, 1],
        note="Across the rocker 5/8 to 1 in. from the tail tip. The tape (photo 1493) read 1 3/16 in.", extra=dict(tape_mm=30.5))


def bleg_top():
    BL = J("parts/model_v%d_params.json" % a.model)["parts"]["back_leg"]; z = 985.0
    V = M["BLEG_R"].vertices; band = V[np.abs(V[:, 2] - z) < 6]; yc = float((band[:, 1].min() + band[:, 1].max()) / 2)
    p, q = through("BLEG_R", [235, yc, z], [1, 0, 0])
    add("bleg_width_top", "BLEG_R", "Back leg width, just below the crest", p, q, source="taped", tol=1.2, group=3, m=None,
        file="parts/back_legs.json (via model params back_leg.width_across_mm) + tape IMG_1556",
        file_key="tape_readings.csv IMG_1556 BLEG_L 1.55 in", file_value=round(1.55 * 25.4, 2), look=[0.2, -1, 0.1],
        note="Across the back leg, seen from behind, just under the crest rail. The tape (photo 1556) read 1 9/16 in.", extra=dict(tape_mm=round(1.55 * 25.4, 1)))


def fleg_across():
    P = J("parts/model_v%d_params.json" % a.model)["parts"]["front_leg"]; z = 150.0
    V = M["FLEG_R"].vertices; band = V[np.abs(V[:, 2] - z) < 4]; yc = float((band[:, 1].min() + band[:, 1].max()) / 2)
    p, q = through("FLEG_R", [270, yc, z], [1, 0, 0])
    add("fleg_thickness", "FLEG_R", "Front leg thickness, side to side, low down", p, q, source="photos", tol=3.0, group=3, m=None,
        file="parts/side_frame.json (via model params front_leg.thickness_across_mm.v150)", file_key="parts.front_leg.thickness_across_mm.v150",
        file_value=round(P["thickness_across_mm"]["v150"], 2), look=[0.2, 1, 0.1],
        note="Across the front leg seen from the front, about 2 in. above the rocker. The tape (photo 1495) read 1 1/4 in. but could not tell the edge from its round.",
        extra=dict(tape_mm=round(1.27 * 25.4, 1)))


def crest_span():
    C = J("parts/crest.json"); xl, xr = C["joints"]["left"]["leg_inner_face_x"]["mm"], C["joints"]["right"]["leg_inner_face_x"]["mm"]
    ev = lambda c, xx: sum(ck * abs(xx) ** (2 * k) for k, ck in enumerate(c))
    z = 1035.0; B = M["BLEG_R"].vertices; band = B[np.abs(B[:, 2] - z) < 15]; y = float((band[:, 1].min() + band[:, 1].max()) / 2)
    p = first_hit("BLEG_L", [0, y, z], [-1, 0, 0]); q = first_hit("BLEG_R", [0, y, z], [1, 0, 0])
    add("crest_span", "CREST", "Crest length between the back legs", p, q, source="photos", tol=1.6, group=3, m=None, file="parts/crest.json",
        file_key="joints.left/right.leg_inner_face_x", file_value=round(xr - xl, 2), look=[0, -1, 0.15], mirror=False,
        note="The crest rail's visible length: inside face of one back leg to the other, along the back of the crest near its bottom.")


def side_slat_width():
    C = J("parts/crest.json"); P = J("parts/model_v%d_params.json" % a.model)["parts"]["slats"]; z = C["key_points"]["bottom_centre_z"]["mm"] - 15.0
    V = M["SLAT_R"].vertices; band = V[np.abs(V[:, 2] - z) < 8]; c = band.mean(0)
    p, q = through("SLAT_R", [c[0], c[1], z], [1, 0, 0])
    add("side_slat_width_top", "SLAT_R", "Side slat width, just under the crest", p, q, source="photos", tol=1.6, group=3, m=None,
        file=f"parts/slats.json (via model params)", file_key="parts.slats.outer_width_mm.under_crest", file_value=round(P["outer_width_mm"]["under_crest"], 2),
        look=[0, -1, 0.1], note="Across one side slat, about 5/8 in. below the crest, seen from behind.")


def overall_width():
    O = J("parts/model_v%d_params.json" % a.model)["parts"]["overall"]; V = M["ARM_R"].vertices; p = V[np.argmax(V[:, 0])]
    add("overall_width", "ARM_R", "Width across the arms, outside to outside", p * [-1, 1, 1], p, source="photos", tol=2.0, group=3, m=None,
        file=f"parts/model_v{a.model}_params.json (from parts/arms.json)", file_key="parts.overall.bbox_max_mm[0] - bbox_min_mm[0]",
        file_value=round(O["bbox_max_mm"][0] - O["bbox_min_mm"][0], 2), look=[0, 1, 0.6], mirror=False,
        note="The widest point of the chair: outside of one arm to the outside of the other.")


def seat_depth():
    SB = J("parts/seat_back.json")["design"]; F = J("parts/seat_front.json")["design"]; FF = J("parts/seat_front_face.json")["design"]
    yb, zb = SB["top_arris"]["y"][0], SB["top_arris"]["z"][0]; yf = F["pommel_tip"]["y"]; zf = interp_tab(FF["top_of_roll_z_of_abs_x"], 8.0)
    pb = first_hit("SEAT", [0, yb + 3, zb + 80], [0, 0, -1]); pf = first_hit("SEAT", [0, yf + 40, zf - 4], [0, -1, 0])
    # the seat slopes down to the back, so a tape laid from the back edge to the front point runs on the slant: draw that line
    add("seat_depth", "SEAT", "Seat depth in the middle, back edge to front point", [0, yb, zb], [0, pf[1], zf], source="photos", tol=2.0, group=3, m=None,
        file="parts/seat_back.json + parts/seat_front.json + parts/seat_front_face.json",
        file_key="design.top_arris (y, z) at x 0 to design.pommel_tip.y at top_of_roll_z (x 8); straight line", file_value=round(float(np.hypot(yf - yb, zf - zb)), 2),
        look=[1, 0.2, 0.5], mirror=False, note="Down the middle of the seat, from its back edge (between the slats) straight to the point at the front, tape held straight, not following the dish.",
        extra=dict(surface_check_mm=round(float(abs(pb[2] - zb)), 2), level_mm=round(float(pf[1] - yb), 2)))


# order inside each group is the order below
for fn in [m6_arm_front, m12_rocker_mid, m13_seat_back_edge, m15_arm_inner(150.0, "back"), m15_arm_inner(400.0, "front"), seat_front_corner,
           m11_domino, m4_slat_thickness, m16_rocker_tail, m16_arm_edge,
           m3_crest_height, m5_slat_width, m8_rocker_length("L"), m8_rocker_length("R"), m9_seat_side("L"), m9_seat_side("R"),
           m14_rocker_top("nose"), m14_rocker_top("tail"),
           m1_seat_front, m2_seat_side, m7_crest_top, m10_scallop, tail_thickness, bleg_top, fleg_across, crest_span,
           side_slat_width, seat_depth, overall_width]:
    attempt(fn)

for i, d in enumerate(sorted(DIMS, key=lambda d: d["group"])): d["order"] = i + 1
DIMS.sort(key=lambda d: d["order"])

QUESTIONS = [dict(id="slat_turn", name="Side slats: turned or flat?", part="SLAT_R", group=1, m="slat turn yes/no",
                  file="parts/slat_turn.json", file_key="apply_in_build (false); design.turn_deg",
                  model="flat", choices=[["flat", "Flat, like the model"], ["turned", "Turned toward the middle"]],
                  turn_deg=[J("parts/slat_turn.json")["design"]["turn_deg"][0], J("parts/slat_turn.json")["design"]["turn_deg"][-1]],
                  note="Look down on the side slats. Are they flat across, like the model, or is each one turned so its outside edge comes forward (about 7 degrees at the seat, 3 1/2 at the top)?")]

print(f"{'id':26s} {'grp':>3s} {'value':>8s} {'file':>8s} {'diff':>6s}  source")
for d in DIMS:
    print(f"{d['id']:26s} {d['group']:3d} {d['value_mm']:8.2f} {d['file_value_mm'] if d['file_value_mm'] is not None else float('nan'):8.2f} {d['agrees_mm'] if d['agrees_mm'] is not None else float('nan'):6.2f}  {d['source']}")
# Left out on purpose: no honest pair of end points on the model.
LEFT_OUT = [dict(id="arm_length", name="Arm length", reason="The arm curves outward in plan, so a straight front-to-back line between "
                 "two points on the arm does not follow it; arms_geom.json lengths.plan (463.9 mm) is measured along the curve. "
                 "Check it against the arm template instead.")]
LEFT_OUT += [dict(id=s.split(":")[0], reason=s) for s in SKIPPED]
for s in SKIPPED: print("SKIPPED", s)
if not a.check:
    out = dict(model=GLB, made_by="tools/dimensions.py", frame="chair frame, mm: +X chair's right, +Y forward, +Z up, table top Z = 0",
               rule="value_mm is measured on the model between p1 and p2 (kind 'height': p1's z); file_value_mm is the parts file's own number; "
                    "mirror true = drawn on the left twin with x -> -x; kind 'radius' has p1 = p2 = the corner and value 0 = sharp in the model",
               sources={"taped": "a tape reading backs it", "photos": "worked out from the photos (tolerance_mm)", "guess": "our guess: no photo or tape settles it"},
               groups=GROUPS, dimensions=DIMS, questions=QUESTIONS, left_out=LEFT_OUT)
    (ROOT / f"parts/model_v{a.model}_dimensions.json").write_text(json.dumps(out, indent=1))
    print("wrote", f"parts/model_v{a.model}_dimensions.json", len(DIMS), "dimensions")
