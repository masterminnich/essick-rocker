"""USAGE: python -I tools/joinery.py IN.glb OUT.glb   (needs trimesh, manifold3d, pymeshfix, rtree)
Post-build joinery: turns the traced parts of a model built by tools/build_model.py into parts that fit together the way the
chair is actually built. Every joint becomes either two faces in contact or a joint body (Domino) sitting in cut mortises,
so tools/audit_joints.py should find no accidental overlaps and no floating parts. Writes OUT.glb and OUT_joinery.json
(every operation, what it removed, and the provenance of each joint).

Joints (chair frame mm, right side; left = mirror):
  front leg / seat   leg lapped on the OUTSIDE of the seat's side edge; seat edge trimmed to the leg's inner face; through-Domino
  back leg / seat    seat side edge BUTTS the leg's front edge, outer faces flush; seat cut to the leg; Domino across the joint line
  legs / rockers     feet carried down onto the rocker top and cut to its curve (hidden fastener not modelled: not seen)
  arm / back leg     arm end coped to the leg (hidden tenon not modelled: not seen)
  arm / front leg    leg top already cut to the arm underside by build_model.py (round through-tenon: TODO, see report)
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
    # 3 feet onto the rocker top: carry the bottom 20 mm of each leg down 5 mm, then cut it to the rocker's curve
    for L in (FL, BL):
        z0 = M[L].bounds[0, 2]
        foot = M[L].slice_plane([0, 0, z0 + 20], [0, 0, -1], cap=True)
        unite(L, shifted(foot, [0, 0, -5]), f"{L} foot carried 5 mm down (it floated 0.8-1.8 mm above the rocker)")
        cut(L, M[RK], f"{L} foot cut to the rocker's top edge (contact face; the fastener between them is hidden and NOT modelled)")
    # 4 arm coped to the back leg
    cut(AR, M[BL], f"{AR} end coped to {BL} (it ran 4 mm into the leg; the arm's hidden joint into the leg is NOT modelled)")
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
# 6 crest coped to the back legs; slats into mortises in the seat and the crest
for L in ("BLEG_R", "BLEG_L"): cut("CREST", M[L], f"crest end coped to {L} (the crest's joint into the leg is hidden and NOT modelled)")
for s_ in ("SLAT_C", "SLAT_R", "SLAT_L"):
    cut("SEAT", M[s_], f"mortise for {s_} in the seat (depth = how far the traced slat runs in; NOT measured)")
    cut("CREST", M[s_], f"mortise for {s_} in the crest (depth = how far the traced slat runs in; NOT measured)")
rep["open"] = ["arm / front leg: round end grain on the arm top over the leg (IMG_1528) = through round tenon or plug: not modelled yet",
               "legs / rockers, arm / back leg, crest / back legs: the joints are hidden; contact faces only",
               "Domino depth not visible; slat mortise depth not measured",
               "leg feet sit about 3 mm off the rocker faces in x (rocker width is a tape value, 31 mm); not changed"]
out = trimesh.Scene()
for k, m in M.items(): out.add_geometry(m, node_name=k, geom_name=k)
out.export(dst)
rep["parts"] = {k: {"volume_cm3": round(vol(m), 1), "watertight": bool(m.is_watertight)} for k, m in M.items()}
json.dump(rep, open(str(Path(dst).with_suffix("")) + "_joinery.json", "w"), indent=1); print(json.dumps(rep, indent=1))
