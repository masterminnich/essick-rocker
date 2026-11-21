"""USAGE: python -I tools/audit_joints.py parts/model_v9.glb [out.json]
Structure/assembly audit of a model: for every pair of parts that should be joined, the overlap volume (boolean
intersection, manifold3d), the closest distance when they do not touch, and whether each mesh is watertight.
Small meshes, < 1 GB, seconds."""
import sys, json, itertools
import numpy as np, trimesh
sc = trimesh.load(sys.argv[1]); G = {k: g for k, g in sc.geometry.items()}
out = {"parts": {}, "pairs": {}}
for k, g in G.items():
    out["parts"][k] = {"watertight": bool(g.is_watertight), "volume_cm3": round(float(abs(g.volume)) / 1000, 1) if g.is_watertight else None,
                       "bbox_min": g.bounds[0].round(1).tolist(), "bbox_max": g.bounds[1].round(1).tolist()}
JOIN = [("ROCKER_R", "FLEG_R"), ("ROCKER_R", "BLEG_R"), ("FLEG_R", "SEAT"), ("BLEG_R", "SEAT"), ("FLEG_R", "ARM_R"), ("BLEG_R", "ARM_R"),
        ("BLEG_R", "CREST"), ("BLEG_L", "CREST"), ("SLAT_C", "SEAT"), ("SLAT_R", "SEAT"), ("SLAT_C", "CREST"), ("SLAT_R", "CREST"), ("SLAT_L", "CREST"),
        ("ARM_R", "SEAT"), ("SLAT_R", "BLEG_R"), ("SLAT_C", "SLAT_R"), ("DOMINO_FR", "FLEG_R"), ("DOMINO_FR", "SEAT"), ("DOMINO_BR", "BLEG_R"), ("DOMINO_BR", "SEAT"),
        ("DOMINO_AR", "FLEG_R"), ("DOMINO_AR", "ARM_R")]
from trimesh.proximity import ProximityQuery
for a_, b_ in [p for p in JOIN if p[0] in G and p[1] in G]:
    A, B = G[a_], G[b_]; r = {}
    try:
        I = trimesh.boolean.intersection([A, B], engine="manifold"); r["overlap_cm3"] = round(float(abs(I.volume)) / 1000, 2) if len(I.vertices) else 0.0
        if len(I.vertices): r["overlap_bbox"] = [I.bounds[0].round(0).tolist(), I.bounds[1].round(0).tolist()]
    except Exception as e: r["overlap_err"] = str(e)[:80]
    # closest distance: sample A's surface, query B
    P, _ = trimesh.sample.sample_surface(A, 3000, seed=1)
    # unsigned distance from a dense sample of B (KD-tree; light on memory), signed by an inside test when B is closed (+ inside B)
    from scipy.spatial import cKDTree
    Q, _ = trimesh.sample.sample_surface_even(B, 300000, radius=0.8, seed=1); d, _ = cKDTree(Q).query(P)
    if B.is_watertight:
        d = np.where(B.contains(P), d, -d)
        if -3.0 < d.max() <= 0:             # no sample inside B and the parts are close: refine the gap with exact closest points for the nearest 400 samples
            # (hub, v15 build: only when the KD-tree gap is under 3 mm. On pairs that stand well clear, e.g. ARM_R~SEAT at 134 mm, closest_point
            #  pulls in a large share of B's triangles for every sample and the job went over the 3 GB cap; those pairs do not need it)
            near = np.argsort(-d)[:400]; near = near[d[near] > -3.0]; d[near] = -trimesh.proximity.closest_point(B, P[near])[1]
        r["max_penetration_mm"] = round(float(max(d.max(), 0)), 1); r["min_gap_mm"] = round(float(max(-d.max(), 0)), 1)
    else:
        r["min_dist_mm"] = round(float(d.min()), 1); r["note"] = f"{b_} is not watertight"
    r["area_within_1mm_cm2"] = round(float((np.abs(d) < 1.5).mean() * A.area / 100), 1)
    out["pairs"][f"{a_}~{b_}"] = r; print(a_, b_, r)
for k, v in out["parts"].items(): print(k, v["watertight"], v["volume_cm3"], v["bbox_min"], v["bbox_max"])
if len(sys.argv) > 2: json.dump(out, open(sys.argv[2], "w"), indent=1)
