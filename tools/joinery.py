"""USAGE: python -I tools/joinery.py IN.glb OUT.glb   (needs trimesh, manifold3d, pymeshfix, rtree)
Post-build joinery: turns the traced parts of a model built by tools/build_model.py into parts that fit together the way the
chair is actually built. Every joint becomes either two faces in contact or a joint body (Domino) sitting in cut mortises,
so tools/audit_joints.py should find no accidental overlaps and no floating parts. Writes OUT.glb and OUT_joinery.json
(every operation, what it removed, and the provenance of each joint).

Joints (chair frame mm, right side; left = mirror):
  front leg / seat   leg lapped on the OUTSIDE of the seat's side edge; seat edge trimmed to the leg's inner face; through-Domino
  back leg / seat    seat side edge BUTTS the leg's front edge, outer faces flush; seat cut to the leg; Domino across the joint line;
                     a second Domino driven in from BEHIND across the seam between the leg's inner face and the seat's back edge
                     (seen from behind: parts/joints.json back_leg_rear)
  legs / rockers     feet carried down onto the rocker top and cut to its curve (hidden fastener not modelled: not seen)
  arm / back leg     arm end coped to the leg; a Domino driven in from BEHIND through the leg into the arm's end (its end shows on
                     the leg's rear face: parts/joints.json back_leg_rear; how far it goes into the arm is ASSUMED)
  arm / front leg    leg top cut to the arm underside by build_model.py; a hidden vertical 10 mm Domino along the leg axis, from the
                     leg top into the arm (ASSUMED: parts/joints.json; the oval on the left arm top is not over the leg, see there)
  crest / back legs  crest ends coped to the legs (hidden joint not modelled)
  slats              their stub ends become tenons; mortises cut into the seat and the crest
Domino sizes and positions: parts/dominos.json (measured on leg-face orthophotos; 10 mm Domino, 24 x 10 section).
Small compute: manifold booleans on ~10k-face meshes, a few seconds."""
import sys, json
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
import numpy as np, trimesh

src, dst = sys.argv[1], sys.argv[2]
sc = trimesh.load(src); M = {k: g.copy() for k, g in sc.geometry.items()}
rep = {"source": src, "ops": [], "joints": {}, "open": []}
vol = lambda m: float(m.volume) / 1000.0


def fixed(m):
    if m.is_volume: return m
    import pymeshfix
    f = pymeshfix.MeshFix(np.asarray(m.vertices), np.asarray(m.faces)); f.repair(joincomp=False, remove_smallest_components=True)
    r = trimesh.Trimesh(f.points, f.faces); assert r.is_volume, "mesh repair failed"; return r


def cut(name, tool, why):
    before = vol(M[name]); M[name] = trimesh.boolean.difference([M[name], tool], engine="manifold")
    rep["ops"].append({"part": name, "removed_cm3": round(before - vol(M[name]), 2), "why": why})


def unite(name, extra, why):
    before = vol(M[name]); M[name] = trimesh.boolean.union([M[name], extra], engine="manifold")
    rep["ops"].append({"part": name, "added_cm3": round(vol(M[name]) - before, 2), "why": why})


def shifted(m, d):
    c = m.copy(); c.apply_translation(d); return c


for k in M: M[k] = fixed(M[k])
if "SEAT" in M: rep["ops"].append({"part": "SEAT", "why": "seat mesh closed with pymeshfix (it had open edges along the scalloped front top edge: build_model.py's Delaunay "
                                                          "triangle filter drops slivers there). Root cause belongs in build_model.py."})
D = json.load(open(ROOT / "parts/dominos.json")); sec = D["design"]["tenon_section_mm"]


def stadium_prism(length_a, width_b, depth, n=24):
    """2D stadium (long axis a, short b) in the (y, z) plane, extruded along -x from x = 0 (outer face) to x = -depth"""
    r = width_b / 2; h = length_a / 2 - r; t1 = np.linspace(-np.pi / 2, np.pi / 2, n); t2 = t1 + np.pi
    P = np.r_[np.c_[h + r * np.cos(t1), r * np.sin(t1)], np.c_[-h + r * np.cos(t2), r * np.sin(t2)]]
    from shapely.geometry import Polygon
    m = trimesh.creation.extrude_polygon(Polygon(P), depth + 0.6)           # local (a, b, w)
    V = m.vertices; m.vertices = np.c_[-(V[:, 2] - 0.6), V[:, 0], V[:, 1]]  # x = -w (+0.6 proud of the face, trimmed below), y = a, z = b
    m.fix_normals(); return m


def place_domino(center, tilt_deg, depth, side):
    m = stadium_prism(sec[0], sec[1], depth)
    t = np.radians(tilt_deg); R = np.eye(4); R[1:3, 1:3] = [[np.cos(t), -np.sin(t)], [np.sin(t), np.cos(t)]]   # long axis tilted front end up
    m.apply_transform(R)
    if side < 0: m.vertices[:, 0] *= -1; m.invert()
    m.apply_translation(center); return m


def domino_along(c, w, long_dir, a, b, d_down, d_up, n=24):
    """Domino body: stadium (long a along long_dir, short b) extruded along unit axis w from c - w*d_down to c + w*d_up"""
    w = np.asarray(w, float) / np.linalg.norm(w); l = np.asarray(long_dir, float) - w * (np.asarray(long_dir, float) @ w)
    l /= np.linalg.norm(l); s = np.cross(w, l); r = b / 2; h = a / 2 - r; t1 = np.linspace(-np.pi / 2, np.pi / 2, n); t2 = t1 + np.pi
    P = np.r_[np.c_[h + r * np.cos(t1), r * np.sin(t1)], np.c_[-h + r * np.cos(t2), r * np.sin(t2)]]
    from shapely.geometry import Polygon
    m = trimesh.creation.extrude_polygon(Polygon(P), d_down + d_up); V = m.vertices
    m.vertices = np.asarray(c, float) + np.outer(V[:, 0], l) + np.outer(V[:, 1], s) + np.outer(V[:, 2] - d_down, w)
    m.fix_normals(); return m


def leg_depth_at(leg, p, side):
    """thickness across of the leg at point p on its outer face (ray inward)"""
    ray = trimesh.ray.ray_triangle.RayMeshIntersector(M[leg])
    o = np.array(p, float) + [side * 5.0, 0, 0]; loc, _, _ = ray.intersects_location([o], [[-side, 0, 0]])
    xs = np.sort(np.abs(loc[:, 0])) if len(loc) else np.array([abs(p[0]), abs(p[0]) - 33])
    return float(xs.max() - xs.min()) if len(xs) > 1 else 33.0


for side, S in ((1, "R"), (-1, "L")):
    FL, BL, RK, AR = f"FLEG_{S}", f"BLEG_{S}", f"ROCKER_{S}", f"ARM_{S}"
    # 1 front leg / seat: lap. The model's leg overlapped the seat edge by 4-9 mm; trim the seat to the leg's inner face (contact face)
    cut("SEAT", M[FL], f"{FL} lap: seat side edge trimmed to the leg's inner face")
    # 2 back leg / seat: butt, outer faces flush. Remove the seat inside the leg and the sliver outboard of the leg's outer face
    tool = trimesh.boolean.union([M[BL], shifted(M[BL], [side * 6, 0, 0]), shifted(M[BL], [side * 12, 0, 0])], engine="manifold")
    cut("SEAT", tool, f"{BL} butt joint: seat side edge stops at the leg (front face), nothing of the seat inside or outside the leg")
    # 3 feet onto the rocker top. The leg is swept ALONG ITS OWN AXIS (convex hull of the bottom slab and its copy 12 mm further
    #   down the axis: the leg is straight and convex there), so its faces carry on with no step. Then everything below the rocker's
    #   top is cut away with the rocker widened across its own direction in plan (it toes in ~10 deg), so nothing hangs down beside the rocker's side faces.
    R = M[RK]; RV = np.asarray(R.vertices)
    for L in (FL, BL):
        z0 = M[L].bounds[0, 2]
        cs = [M[L].section([0, 0, 1], [0, 0, z]).vertices.mean(0) for z in (z0 + 25, z0 + 90)]
        a = cs[1] - cs[0]; a /= np.linalg.norm(a)                                                     # leg axis near the foot, upward
        slab = M[L].slice_plane([0, 0, z0 + 15], [0, 0, -1], cap=True)
        sweep = trimesh.convex.convex_hull(np.r_[slab.vertices, slab.vertices - a * 12.0])
        unite(L, sweep, f"{L} foot extended 12 mm along the leg axis (it floated 0.8-1.8 mm above the rocker)")
        yc = slab.bounds.mean(0)[1]; near = RV[np.abs(RV[:, 1] - yc) < 60][:, :2]                    # the rocker in plan under this foot
        _, _, vt = np.linalg.svd(near - near.mean(0)); nrm = np.r_[-vt[0][1], vt[0][0], 0.0]       # across the rocker, in plan
        wide = trimesh.boolean.union([shifted(R, nrm * k + [0, 0, dz]) for k in range(-16, 17, 2) for dz in (0, -30)], engine="manifold")
        above = trimesh.boolean.union([shifted(R, [0, 0, dz]) for dz in range(0, 61, 5)], engine="manifold")   # over the rocker's footprint
        wide = trimesh.boolean.union([trimesh.boolean.difference([wide, above], engine="manifold"), R], engine="manifold")  # there: the rocker itself
        cut(L, wide, f"{L} foot cut to the rocker's top surface across the full width (contact face; the fastener is hidden and NOT modelled)")
        rep["joints"][f"{L}_foot"] = {"leg_axis": a.round(3).tolist(), "method": "swept along the leg axis, cut by the widened rocker"}
    # 4 arm coped to the back leg
    cut(AR, M[BL], f"{AR} end coped to {BL} (it ran 4 mm into the leg; the Domino through the leg into the arm's end is added in 5c)")
    cut(AR, M[FL], f"{AR} underside vs {FL} top: contact face")
    # 5 Dominos
    for L, key, base_depth in ((FL, "front_leg", None), (BL, "back_leg", 25.0)):
        c = np.array(D["joints"][key]["centre_xyz"], float); c[0] = abs(c[0]) * side
        tilt = D["design"]["long_axis_tilt_deg"]["front" if key == "front_leg" else "back"]
        depth = base_depth if base_depth else leg_depth_at(L, c, side) + 25.0
        dom = place_domino(c, tilt, depth, side)
        dom = trimesh.boolean.intersection([dom, trimesh.boolean.union([M[L], M["SEAT"]], engine="manifold")], engine="manifold")   # end flush with the actual faces
        name = f"DOMINO_{'F' if key == 'front_leg' else 'B'}{S}"; M[name] = dom
        cut(L, dom, f"mortise for {name} in {L}"); cut("SEAT", dom, f"mortise for {name} in the seat edge")
        rep["joints"][name] = {"centre_xyz": c.round(1).tolist(), "section_mm": sec, "depth_mm": round(depth, 1), "tilt_deg": tilt,
                               "provenance": "section + position measured on leg-face orthophotos (parts/dominos.json); depth ASSUMED (" +
                                             ("leg thickness + 25 mm into the seat edge" if key == "front_leg" else "25 mm, straddling the leg/seat joint line") + ")"}
# 5b arm / front leg: hidden vertical Domino centred on the leg top's contact face, along the leg axis, long axis fore-aft
J = json.load(open(ROOT / "parts/joints.json"))["arm_front_leg"]["design"]
for side, S in ((1, "R"), (-1, "L")):
    FL, AR = f"FLEG_{S}", f"ARM_{S}"; L = M[FL]; zt = L.bounds[1, 2]
    cs = [L.section([0, 0, 1], [0, 0, z]).vertices.mean(0) for z in (zt - 120, zt - 30)]          # leg centreline near the top
    w = cs[1] - cs[0]; w /= np.linalg.norm(w)
    P, _ = trimesh.sample.sample_surface_even(L, 40000, radius=0.6, seed=1)
    from scipy.spatial import cKDTree
    Q, _ = trimesh.sample.sample_surface_even(M[AR], 60000, radius=0.6, seed=1); d, _ = cKDTree(Q).query(P); top = P[d < 0.8]
    c = top.mean(0)                                                                                   # centre of the contact face
    dom = domino_along(c, w, [0, 1, 0], J["section_mm"][0], J["section_mm"][1], J["depth_in_leg_mm"], J["depth_in_arm_mm"])
    name = f"DOMINO_A{S}"; M[name] = dom
    cut(FL, dom, f"mortise for {name} in the top of {FL}"); cut(AR, dom, f"mortise for {name} in the underside of {AR}")
    rep["joints"][name] = {"centre_xyz": c.round(1).tolist(), "axis": w.round(3).tolist(), "section_mm": J["section_mm"],
                           "depth_mm": [J["depth_in_leg_mm"], J["depth_in_arm_mm"]],
                           "provenance": "ASSUMED, hidden joint (parts/joints.json arm_front_leg)"}
# 5c back leg, REAR face (hub, Joe's fix list item 1; parts/joints.json back_leg_rear): two Domino ends per back leg show from behind.
#    Each is placed ON the leg's rear face (plane fitted to the face around the Domino's height, as tools/rear_ortho.py does) at the
#    measured x and z, long axis level (along x), driven in square to that face. 'seat': across the seam leg / seat back edge, blind.
#    'arm': centred on the leg's width, through the leg and on into the arm's end.
def rear_face(leg, zc):
    L0 = sc.geometry[leg]; S_, fi = trimesh.sample.sample_surface(L0, 80000, seed=1); nr = L0.face_normals[fi]   # the leg as traced: by now M[leg] has mortise walls that also look backward
    P = S_[(nr[:, 1] < -0.8) & (np.abs(S_[:, 2] - zc) < 45)]; o = P.mean(0); _, _, vt = np.linalg.svd(P - o); nn = vt[2] * np.sign(-vt[2][1])
    return o, nn, float(np.sqrt(np.mean(((P - o) @ nn) ** 2)))                                          # point on the face, unit normal pointing backward, fit rms


JR = json.load(open(ROOT / "parts/joints.json"))["back_leg_rear"]["design"]
for side, S in ((1, "R"), (-1, "L")):
    BL = f"BLEG_{S}"
    for key, other, tag in (("seat", "SEAT", "RS"), ("arm", f"ARM_{S}", "RA")):
        d = JR[key]; z = d["centre_z"]; x = side * d["centre_abs_x"]; o, nn, rms = rear_face(BL, z)
        c = np.array([x, o[1] - (nn[0] * (x - o[0]) + nn[2] * (z - o[2])) / nn[1], z]); w = -nn      # centre of the visible end, on the rear face; w points into the leg
        if key == "arm":
            t = np.arange(0.5, 90.0, 0.25); ins = M[BL].contains(c + np.outer(t, w)); through = float(t[ins].max()) + 0.25   # the leg's thickness along the Domino's axis
            depth = through + d["depth_in_arm_mm"]
        else: through = None; depth = d["depth_mm"]
        raw = domino_along(c, w, [1, 0, 0], d["section_mm"][0], d["section_mm"][1], 2.0, depth)        # 2 mm proud of the rear face, trimmed flush below
        dom = trimesh.boolean.intersection([raw, trimesh.boolean.union([M[BL], M[other]], engine="manifold")], engine="manifold")
        in_leg = vol(trimesh.boolean.intersection([dom, M[BL]], engine="manifold")); in_other = vol(trimesh.boolean.intersection([dom, M[other]], engine="manifold"))
        xs = np.arange(-d["section_mm"][0] / 2 + 0.05, d["section_mm"][0] / 2, 0.1); end_in_leg = 0.1 * int(M[BL].contains(c + w * 3.0 + np.outer(xs, [1.0, 0, 0])).sum())   # along the end's long axis, 3 mm in
        name = f"DOMINO_{tag}{S}"; M[name] = dom
        cut(BL, dom, f"mortise for {name} in the rear face of {BL}"); cut(other, dom, f"mortise for {name} in " + ("the seat's back edge" if key == "seat" else f"the end of {other}"))
        rep["joints"][name] = {"centre_xyz": c.round(1).tolist(), "axis": w.round(4).tolist(), "long_axis": "level, along x", "section_mm": d["section_mm"],
                               "depth_mm": round(depth, 1), "through_the_leg_mm": None if through is None else round(through, 1),
                               "rear_face_fit_rms_mm": round(rms, 2), "volume_cm3": round(vol(dom), 2), "in_leg_cm3": round(in_leg, 2), f"in_{other.split('_')[0].lower()}_cm3": round(in_other, 2),
                               "bodies": int(len(dom.split(only_watertight=False))), "mm_of_the_end_in_the_leg": round(end_in_leg, 1),
                               "provenance": "end seen from behind: position and section measured on rear-face orthophotos (parts/joints.json back_leg_rear); driven square to the rear face and depth: ASSUMED"}
# 6 crest coped to the back legs; slats into mortises in the seat and the crest
for L in ("BLEG_R", "BLEG_L"): cut("CREST", M[L], f"crest end coped to {L} (the crest's joint into the leg is hidden and NOT modelled)")
for s_ in ("SLAT_C", "SLAT_R", "SLAT_L"):
    cut("SEAT", M[s_], f"mortise for {s_} in the seat (depth = how far the traced slat runs in; NOT measured)")
    cut("CREST", M[s_], f"mortise for {s_} in the crest (depth = how far the traced slat runs in; NOT measured)")
rep["open"] = ["arm / front leg: hidden; modelled as an ASSUMED vertical 10 mm Domino (the oval on the left arm top is not over the leg)",
               "legs / rockers, crest / back legs: the joints are hidden; contact faces only",
               "arm / back leg: a Domino end shows on the leg's rear face; how far it runs into the arm's end is ASSUMED (25 mm)",
               "back leg / seat from behind: at the rear the real seam sits 2.5-3.4 mm inboard of the model leg's inner face, so the model's rear Domino at the seat has less of its end in the leg than the photos show (photos: 14.2 of 24 mm; model: 'mm_of_the_end_in_the_leg' of DOMINO_RS*); leg placement, not changed",
               "Domino depth not visible; slat mortise depth not measured",
               "leg feet sit about 3 mm off the rocker faces in x (rocker width is a tape value, 31 mm); not changed"]
out = trimesh.Scene()
for k, m in M.items(): out.add_geometry(m, node_name=k, geom_name=k)
out.export(dst)
rep["parts"] = {k: {"volume_cm3": round(vol(m), 1), "watertight": bool(m.is_watertight)} for k, m in M.items()}
json.dump(rep, open(str(Path(dst).with_suffix("")) + "_joinery.json", "w"), indent=1); print(json.dumps(rep, indent=1))
