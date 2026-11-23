"""USAGE: python -I tools/flush_audit.py MODEL.glb [out.json] [--points out_points.npz]   (needs trimesh, rtree, scipy)
Flushness audit of the joints (Joe, 2026-11-23: "the wood should sit flush with the pieces it intersects").
tools/audit_joints.py only asks whether two parts touch somewhere (min gap 0) and do not overlap. A butt or coped joint can pass
that and still show a gap: the end of one member touches the other along one line and stands off it everywhere else.

For every joint (A meets B) this samples A's surface (0.5 mm spacing), keeps the samples that face B (ray along A's outward
normal hits B within REACH mm), and splits them into
  contact  gap <= 0.15 mm (the two surfaces coincide; a coped end)
  open     0.15 < gap <= REACH, and the sample lies within NEAR mm of the contact patch (an end face that should sit on B but
           stands off it; faces far from any contact are design clearance, e.g. the seat's under-bevel behind the leg, and are
           not counted)
and reports per joint: contact area, open area, the largest and 95th-percentile open gap, and where it is (bbox).
Small compute: ~10k-face meshes, ray casts in slices, < 1.5 GB, about a minute."""
import sys, json
import numpy as np, trimesh
from scipy.spatial import cKDTree

REACH, NEAR, TOUCH = 10.0, 12.0, 0.15
JOINTS = [  # (A = the member whose end/face should sit on B, B, what the joint is)
    ("ARM_R", "BLEG_R", "arm end coped to the back leg"), ("ARM_L", "BLEG_L", "arm end coped to the back leg"),
    ("ARM_R", "FLEG_R", "arm underside on the front-leg top"), ("ARM_L", "FLEG_L", "arm underside on the front-leg top"),
    ("FLEG_R", "ARM_R", "front-leg top under the arm"), ("FLEG_L", "ARM_L", "front-leg top under the arm"),
    ("CREST", "BLEG_R", "crest end coped to the back leg"), ("CREST", "BLEG_L", "crest end coped to the back leg"),
    ("SEAT", "BLEG_R", "seat side edge butting the back leg"), ("SEAT", "BLEG_L", "seat side edge butting the back leg"),
    ("SEAT", "FLEG_R", "seat side edge in the front-leg lap"), ("SEAT", "FLEG_L", "seat side edge in the front-leg lap"),
    ("FLEG_R", "ROCKER_R", "front foot on the rocker"), ("FLEG_L", "ROCKER_L", "front foot on the rocker"),
    ("BLEG_R", "ROCKER_R", "back foot on the rocker"), ("BLEG_L", "ROCKER_L", "back foot on the rocker"),
    ("SLAT_C", "SEAT", "slat shoulder on the seat"), ("SLAT_R", "SEAT", "slat shoulder on the seat"), ("SLAT_L", "SEAT", "slat shoulder on the seat"),
    ("SLAT_C", "CREST", "slat shoulder at the crest"), ("SLAT_R", "CREST", "slat shoulder at the crest"), ("SLAT_L", "CREST", "slat shoulder at the crest"),
]


def first_hit(B, P, N):
    """distance along N from P to B's surface (inf if none within REACH); rays start 0.05 mm behind P so coincident faces count"""
    ray = trimesh.ray.ray_triangle.RayMeshIntersector(B); t = np.full(len(P), np.inf)
    for i in range(0, len(P), 400):
        o = P[i:i + 400] - N[i:i + 400] * 0.05
        loc, ri, _ = ray.intersects_location(o, N[i:i + 400], multiple_hits=True)
        if not len(ri): continue
        d = np.einsum("ij,ij->i", loc - o[ri], N[i:i + 400][ri]) - 0.05
        ok = (d > -0.06) & (d < REACH)
        for r_, d_ in zip(ri[ok], d[ok]):
            if d_ < t[i + r_]: t[i + r_] = d_
    return np.maximum(t, 0.0)


def audit(G):
    out = {}; pts = {}
    for a, b, what in JOINTS:
        if a not in G or b not in G: continue
        A, B = G[a], G[b]
        lo, hi = B.bounds[0] - REACH, B.bounds[1] + REACH                       # only A's part near B
        P, fi = trimesh.sample.sample_surface_even(A, 400000, radius=0.5, seed=1); area_per = A.area / len(P)   # mm2 per sample
        keep = np.all((P > lo) & (P < hi), axis=1); P, fi = P[keep], fi[keep]
        Q, _ = trimesh.sample.sample_surface_even(B, 400000, radius=0.5, seed=2); dk, _ = cKDTree(Q).query(P)
        keep = dk < REACH; P, fi = P[keep], fi[keep]; N = A.face_normals[fi]
        g = first_hit(B, P, N); facing = np.isfinite(g) & (g <= REACH)
        contact = facing & (g <= TOUCH)
        if contact.any():
            dc, _ = cKDTree(P[contact]).query(P); open_ = facing & (g > TOUCH) & (dc < NEAR)
        else:
            open_ = np.zeros(len(P), bool)
        r = {"joint": what, "contact_cm2": round(contact.sum() * area_per / 100, 1), "open_cm2": round(open_.sum() * area_per / 100, 1)}
        if open_.any():
            go = g[open_]; r.update({"open_max_mm": round(float(go.max()), 2), "open_p95_mm": round(float(np.percentile(go, 95)), 2),
                                      "open_median_mm": round(float(np.median(go)), 2), "open_over_0.5mm_cm2": round((go > 0.5).sum() * area_per / 100, 2),
                                      "open_bbox": [P[open_].min(0).round(0).tolist(), P[open_].max(0).round(0).tolist()]})
        out[f"{a}~{b}"] = r; pts[f"{a}~{b}"] = np.c_[P[contact | open_], g[contact | open_]]
        print(f"{a}~{b}", r, flush=True)
    return out, pts


if __name__ == "__main__":
    sc = trimesh.load(sys.argv[1]); G = {k: g for k, g in sc.geometry.items()}
    out, pts = audit(G)
    args = sys.argv[2:]
    if args and not args[0].startswith("--"): json.dump(out, open(args[0], "w"), indent=1)
    if "--points" in args: np.savez_compressed(args[args.index("--points") + 1], **{k.replace("~", "__"): v for k, v in pts.items()})
