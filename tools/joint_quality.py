"""USAGE: python -I tools/joint_quality.py MODEL.glb OUT.json [--joint NAME ...]     (NAME e.g. ARM_R~BLEG_R; default all)
Quality of the joints built by Joe's dots rule (parts/joint_rules.json), the checks Joe asked for at the arm / back-leg joint
(2026-11-23, gap.png and yuck.png), extended to every rule joint (2026-11-23, figures/joint_dots/dots_other_joints.png):
  ARM_R/L~BLEG_R/L    arm end on the back leg's front face        (arm_back_leg)
  CREST~BLEG_R/L      crest end on the back leg's inner face      (crest_back_leg)
  FLEG_R/L~ROCKER_R/L front foot on the rocker's top              (foot_rocker)
  BLEG_R/L~ROCKER_R/L back foot on the rocker's top               (foot_rocker)
  FLEG_R/L~ARM_R/L    front-leg top under the arm                 (front_leg_arm)
Each joint is A (the member whose end sits on B) meeting B. Both are first turned into one frame (FRAMES): x' = the axis A's side
faces run flush along (+ = outer / front), y' = along A, away from B, z' = the third axis. The arm on the right is the identity;
every other joint is a rotation or a mirror of it, so one set of checks serves all ten.
  flush       A's side faces vs B's side faces at the crease (A side-face points within 0.5 mm of B vs B's side face at the same
              y', z'; mm, 0 = flush, + = A proud). crease_max_proud_mm, reported: the largest such step for A side-face points
              within 1.5 mm of B. flush_band, reported only: the v25 band measure. Not for the front-leg top (it is inset by design)
  shards      wood thinner than 1 mm near the end (from each face, the distance to A's own surface behind it, where that faces back)
  corners     sharp short edges near the end: under 0.5 mm, faces meeting at more than 20 degrees
  dots        A's 4 end corners (its vertices on B, within 0.5 mm; 1.5 mm for the crest, whose top lip stands above B) vs the GREEN dots: B's corner lines, where B's side face (a plane fitted within PLANE_WIN of the corner; for the arm, as in v26,
              of the end's centre) meets
              B's surface, at each corner's own height (mm; pass <= 0.3). Where a corner stands above B (the crest's top lip,
              joint_rules.json crest_back_leg top_lip) the dot is B's corner line carried straight up. Front-leg top: the corner's
              distance to the arm's surface
  bulge       (a) A's end outline on B past B's side faces (B's own surface samples at the same y', z'; v26 used planes fitted
              over 120 mm, still reported; front-leg top: past the arm's side planes means NOT inset, pass < 0),
              (b) within 5 mm of B, each A side face's trace off the straight line between its ends (sections every 0.5 mm),
              pass: both <= 0.3 mm. (c), reported: A points within 5 mm of B past the side planes
  gap         daylight between A's end face and B: each end-face sample's distance to B's surface (pass: max <= 0.2 mm). Samples
              whose normal does not meet B within 10 mm (the crest's top lip, above the leg top) are counted, not measured
Domino mortises (DOMINO_*) are real holes; samples within 1 mm of a Domino are left out and counted.
Pass: |flush median| <= 0.3 mm, no shard points, no sharp short edges, corners on the dots, no bulge, no gap.
Prints one line per joint and writes OUT.json. Small compute: about a minute per joint, < 1.5 GB."""
import sys, json
import numpy as np, trimesh
from scipy.spatial import cKDTree

sys.path.insert(0, __file__.rsplit("/", 1)[0]); import joint_ends as je

ARM, CRR, CRL = [[1, 0, 0], [0, 1, 0], [0, 0, 1]], [[0, 1, 0], [-1, 0, 0], [0, 0, 1]], [[0, 1, 0], [1, 0, 0], [0, 0, 1]]
FTR, FTL, TOP = [[1, 0, 0], [0, 0, 1], [0, 1, 0]], [[-1, 0, 0], [0, 0, 1], [0, 1, 0]], [[1, 0, 0], [0, 0, -1], [0, 1, 0]]
MIR = lambda R: [[-v for v in R[0]]] + R[1:]
FRAMES = {   # joint: (A, B, rotation/mirror into the frame, Dominos, kind, rule, PLANE_WIN (y', z') for B's side planes)
    "ARM_R~BLEG_R": ("ARM_R", "BLEG_R", ARM, ["DOMINO_RAR"], "flush", "arm_back_leg", (60.0, 60.0)),
    "ARM_L~BLEG_L": ("ARM_L", "BLEG_L", MIR(ARM), ["DOMINO_RAL"], "flush", "arm_back_leg", (60.0, 60.0)),
    "CREST~BLEG_R": ("CREST", "BLEG_R", CRR, [], "flush", "crest_back_leg", (60.0, 15.0)),
    "CREST~BLEG_L": ("CREST", "BLEG_L", CRL, [], "flush", "crest_back_leg", (60.0, 15.0)),
    "FLEG_R~ROCKER_R": ("FLEG_R", "ROCKER_R", FTR, [], "flush", "foot_rocker", (60.0, 15.0)),
    "FLEG_L~ROCKER_L": ("FLEG_L", "ROCKER_L", FTL, [], "flush", "foot_rocker", (60.0, 15.0)),
    "BLEG_R~ROCKER_R": ("BLEG_R", "ROCKER_R", FTR, [], "flush", "foot_rocker", (60.0, 15.0)),
    "BLEG_L~ROCKER_L": ("BLEG_L", "ROCKER_L", FTL, [], "flush", "foot_rocker", (60.0, 15.0)),
    "FLEG_R~ARM_R": ("FLEG_R", "ARM_R", TOP, ["DOMINO_AR"], "end", "front_leg_arm", (60.0, 15.0)),
    "FLEG_L~ARM_L": ("FLEG_L", "ARM_L", [[-1, 0, 0], [0, 0, -1], [0, 1, 0]], ["DOMINO_AL"], "end", "front_leg_arm", (60.0, 15.0)),
}


def _chunk(f, m, X, n=1500):
    X = np.asarray(X, float); return np.concatenate([f(m, X[i:i + n]) for i in range(0, len(X), n)]) if len(X) else np.zeros(0)


dist = lambda m, X: _chunk(lambda m_, x_: trimesh.proximity.closest_point(m_, x_)[1], m, X)   # in chunks: memory
sdist = lambda m, X: _chunk(trimesh.proximity.signed_distance, m, X)


def frame(m, R):
    T = np.eye(4); T[:3, :3] = np.asarray(R, float); return m.copy().apply_transform(T)   # (trimesh flips the faces of a mirror)


def check(A, B, doms, kind, win, lip=0.5, local=True):
    d = np.full(len(A.vertices), np.inf); nb_ = np.all((A.vertices > B.bounds[0] - 5) & (A.vertices < B.bounds[1] + 5), axis=1)   # (far vertices: no query, memory)
    d[nb_] = np.abs(sdist(B, A.vertices[nb_])); end = A.vertices[d < 2.0]
    c = end.mean(0); w = float(np.ptp(end[:, 0])); hz = float(np.ptp(end[:, 2])) / 2 + 6.0
    boxes = [(D.bounds[0] - 1.0, D.bounds[1] + 1.0) for D in doms]
    inbox = lambda X: np.any([np.all((X > lo) & (X < hi), axis=1) for lo, hi in boxes], axis=0) if boxes else np.zeros(len(X), bool)
    near_dom = lambda X: np.any([np.abs(sdist(D, X)) <= 1.0 for D in doms], axis=0) if doms else np.zeros(len(X), bool)
    crop = lambda m, h: m.submesh([np.all(np.abs(m.triangles_center - c) < h, axis=1)], append=True)   # sampling only (memory)
    Ac = crop(A, [w + 30, 75, hz + 30]); Bc = crop(B, [w + 50, 80, hz + 40])
    P, fi = trimesh.sample.sample_surface_even(Ac, 160000, radius=0.4, seed=2); N = Ac.face_normals[fi]
    k = np.all(np.abs(P - c) < [w + 20, 60, hz + 20], axis=1); P, N = P[k], N[k]
    LP, lfi = trimesh.sample.sample_surface_even(Bc, 240000, radius=0.3, seed=3); LN = Bc.face_normals[lfi]
    lz = (np.abs(LP[:, 2] - c[2]) < hz + 5) & (LP[:, 1] > end[:, 1].min() - 12) & (LP[:, 1] < end[:, 1].max() + 2) & ~inbox(LP)
    pinbox = inbox(P)
    fl, flb = {}, {}
    if kind == "flush":
        near = (P[:, 1] > end[:, 1].min() - 1) & (P[:, 1] < end[:, 1].max() + 6) & (np.abs(P[:, 2] - c[2]) < hz)
        for key, nsg in (("outer", 1.0), ("inner", -1.0)):
            s = near & (N[:, 0] * nsg > 0.9); ls = lz & (LN[:, 0] * nsg > 0.9)
            t = cKDTree(LP[ls][:, 1:]); dq, j = t.query(P[s][:, 1:] * [0, 1] + [c[1] - 4, 0])   # v25 band: same z', 4 mm behind
            off = (P[s, 0] - LP[ls][j, 0]) * nsg
            flb[key] = {"n": int(s.sum()), "median_mm": round(float(np.median(off)), 2), "p05_mm": round(float(np.percentile(off, 5)), 2),
                        "p95_mm": round(float(np.percentile(off, 95)), 2)} if s.any() else {"n": 0}
            s = (N[:, 0] * nsg > 0.9) & (np.abs(P[:, 2] - c[2]) < hz) & (P[:, 1] < end[:, 1].max() + 3) & ~pinbox & ((P[:, 0] - c[0]) * nsg > 0.25 * w)
            dB = np.full(len(P), np.inf); dB[s] = dist(B, P[s])
            for tag, tol in (("crease", 0.5), ("wide", 1.5)):
                s_ = s & (dB < tol); dq, j = t.query(P[s_][:, 1:]); off = ((P[s_, 0] - LP[ls][j, 0]) * nsg)[dq < 2.0]
                if tag == "crease":
                    o_ = off if len(off) else np.array([np.nan])
                    fl[key] = {"n": int((dq < 2.0).sum()), "of": int(s_.sum()), "median_mm": round(float(np.median(o_)), 2),
                               "p05_mm": round(float(np.percentile(o_, 5)), 2), "p95_mm": round(float(np.percentile(o_, 95)), 2)}
                else:
                    fl[key]["crease_max_proud_mm"] = round(float(off.max()), 2) if len(off) else None
                    fl[key]["crease_max_proud_at"] = np.round(P[s_][dq < 2.0][int(np.argmax(off))], 1).tolist() if len(off) else None
    # shards
    zone = np.linalg.norm(P - c, axis=1) < max(40.0, 0.5 * float(np.linalg.norm(np.ptp(end, 0))) + 15)
    Q, NQ = P[zone], N[zone]; ok = ~near_dom(Q)
    th = np.full(len(Q), np.inf)
    for i in range(0, len(Q), 1000):                                          # (in chunks, on the cropped A: memory)
        loc, ri, ti = Ac.ray.intersects_location(Q[i:i + 1000] - NQ[i:i + 1000] * 0.02, -NQ[i:i + 1000], multiple_hits=False)
        opp = (Ac.face_normals[ti] * NQ[i:i + 1000][ri]).sum(1) < -0.707
        th[i + ri[opp]] = np.linalg.norm(loc[opp] - Q[i:i + 1000][ri[opp]], axis=1)
    thin = (th < 1.0) & ok; th_ok = th[ok & np.isfinite(th)]
    # sharp short edges
    E = A.face_adjacency_edges; ang = np.degrees(A.face_adjacency_angles)
    mid = A.vertices[E].mean(1); el = np.linalg.norm(A.vertices[E[:, 0]] - A.vertices[E[:, 1]], axis=1)
    rz = max(40.0, 0.5 * float(np.linalg.norm(np.ptp(end, 0))) + 10)
    ez = np.linalg.norm(mid - c, axis=1) < rz; edom = ez & near_dom(mid); step = ez & ~edom & (el < 0.5) & (ang > 20)
    fz = np.linalg.norm(A.triangles_center - c, axis=1) < rz
    # dots: corners = the end vertices (on B, or within 1.5 mm where they stand above it) extreme in +-x', +-z'
    keep = (lambda X: ~inbox(X)) if boxes else None
    ev = A.vertices[d < 0.5]; evx = A.vertices[d < lip]
    ctr = ev.mean(0); span = np.ptp(ev, 0) + 1e-9; dots = {}
    for nm, sx_, sz_ in (("top_outer", 1, 1), ("top_inner", -1, 1), ("bottom_outer", 1, -1), ("bottom_inner", -1, -1)):
        cand = evx
        cp = cand[np.argmax(sx_ * (cand[:, 0] - ctr[0]) / span[0] + sz_ * (cand[:, 2] - ctr[2]) / span[2])]
        if kind == "end":
            dd = float(dist(B, cp[None])[0]); dots[nm] = {"corner": np.round(cp, 2).tolist(), "dist_mm": round(dd, 3)}; continue
        pl = je.face_planes(B, cp if local else c, 0, win=win, keep=keep)["plus" if sx_ > 0 else "minus"]; zc = float(cp[2]); g = None
        for dz in np.arange(0.0, 3.01, 0.25):                                 # above B (the crest's top lip): B's corner line carried up
            def fq(Y, z_=zc - dz, sx_=sx_, pl=pl):
                X = np.c_[np.zeros(len(Y)), Y, np.full(len(Y), z_)]; X[:, 0] = je.plane_at(pl, X) - sx_ * 0.4; return X
            Ys = np.arange(cp[1] + 25, cp[1] - 40, -0.5); ins = B.contains(fq(Ys))
            if not ins.any(): continue
            k0 = int(np.argmax(ins)); yg = float(je.first_inside(B, fq, Ys[k0:k0 + 1], Ys[k0 - 1:k0])[0])
            g = np.array([0.0, yg, zc]); g[0] = float(je.plane_at(pl, g)[0]); break
        dots[nm] = {"corner": np.round(cp, 2).tolist(), "green": np.round(g, 2).tolist(), "dist_mm": round(float(np.linalg.norm(cp - g)), 3),
                    "dot_carried_up_mm": round(float(dz), 2), "plane_rms_mm": round(pl["rms_mm"], 3)}
    # bulge
    PL = je.face_planes(B, c, 0, win=(60.0, 60.0) if kind == "flush" else (40.0, 40.0), keep=keep)
    pe = ev[:, 0] - je.plane_at(PL["plus"], ev); ie = je.plane_at(PL["minus"], ev) - ev[:, 0]
    chord = []
    for yq in np.arange(ev[:, 1].min() + 0.25, ev[:, 1].max() + 5.0, 0.5):
        # each side face's own trace in the section (segments from faces whose normal is within 45 degrees of +-x'), against the
        # straight line between its two ends (its top and bottom edges, or the edge and the end where the section crosses the end)
        segs, fx = trimesh.intersections.mesh_plane(A, [0, 1, 0], [0, yq, 0], return_faces=True)
        if not len(segs): continue
        nx = A.face_normals[fx][:, 0]; Vs = segs.reshape(-1, 3); nx2 = np.repeat(nx, 2)
        sel = (np.abs(Vs[:, 2] - c[2]) < hz + 10) & (np.abs(Vs[:, 0] - c[0]) < w + 15) & ~inbox(Vs)   # (not the Domino mortise's walls)
        for nm, sx_ in (("outer", 1), ("inner", -1)):
            V = Vs[sel & (nx2 * sx_ > 0.7)][:, [0, 2]]
            if len(V) < 3 or np.ptp(V[:, 1]) < 2.0: continue
            p_, q_ = V[np.argmax(V[:, 1])], V[np.argmin(V[:, 1])]; n_ = np.array([q_[1] - p_[1], p_[0] - q_[0]])
            n_ = n_ / np.linalg.norm(n_) * np.sign(n_[0]) * sx_
            o_ = (V - p_) @ n_; i_ = int(np.argmax(o_))
            chord.append((nm, float(yq), float(o_.max()), [round(float(V[i_][0]), 1), round(float(yq), 1), round(float(V[i_][1]), 1)]))
    cd = {nm: max([v for k_, y_, v, _ in chord if k_ == nm], default=0.0) for nm in ("outer", "inner")}
    cda = {nm: max([(v, a_) for k_, y_, v, a_ in chord if k_ == nm], default=(0.0, None))[1] for nm in ("outer", "inner")}
    nb = (P[:, 1] < end[:, 1].max() + 8) & (np.abs(P[:, 2] - c[2]) < hz + 5)
    nb[nb] = dist(B, P[nb]) < 5.0
    po = P[:, 0] - je.plane_at(PL["plus"], P); pi_ = je.plane_at(PL["minus"], P) - P[:, 0]
    bulge = {"end_outline_past_outer_mm": round(float(pe.max()), 3), "end_outline_past_inner_mm": round(float(ie.max()), 3),
             "face_off_edge_line_outer_mm": round(cd["outer"], 3), "face_off_edge_line_inner_mm": round(cd["inner"], 3), "sections": len(chord), "face_off_edge_line_at": cda,
             "info_within_5mm_past_side_planes_mm": {"outer": round(float(po[nb].max()), 3), "inner": round(float(pi_[nb].max()), 3), "of": int(nb.sum())},
             "side_plane_rms_mm": [round(PL["plus"]["rms_mm"], 3), round(PL["minus"]["rms_mm"], 3)]}
    if kind == "flush":   # against B's own side face at the same (y', z') (a plane fitted over 120 mm misreads a curved face, e.g. the leg's front)
        ps = {}
        for key, nsg in (("outer", 1.0), ("inner", -1.0)):
            ls = lz & (LN[:, 0] * nsg > 0.9); sv = ev[(ev[:, 0] - c[0]) * nsg > 0.25 * w]
            dq, j = cKDTree(LP[ls][:, 1:]).query(sv[:, 1:]); o_ = ((sv[:, 0] - LP[ls][j, 0]) * nsg)[dq < 1.0]
            ps[key] = round(float(o_.max()), 3) if len(o_) else None
        bulge["end_outline_past_side_planes_mm"] = {"outer": bulge.pop("end_outline_past_outer_mm"), "inner": bulge.pop("end_outline_past_inner_mm"), "note": "reported only"}
        bulge["end_outline_past_outer_mm"], bulge["end_outline_past_inner_mm"] = ps["outer"], ps["inner"]
        past = max(v for v in ps.values() if v is not None)
    else:
        past = max(pe.max(), ie.max())
    bulge["pass"] = bool((past <= 0.3 if kind == "flush" else past < 0.0) and max(cd["outer"], cd["inner"]) <= 0.3)
    # gap: A's end face (normals pointing at B, -y') near the end, away from the Dominos, vs B's surface
    ef = (N[:, 1] < -0.5) & (P[:, 1] < end[:, 1].max() + 0.5) & ~pinbox
    ef[ef] = ~near_dom(P[ef]); Pe, Ne = P[ef], N[ef]; gd = np.full(len(Pe), np.inf)
    for i in range(0, len(Pe), 1000):   # over B: the end face's normal meets B within 10 mm (not: the crest's top lip)
        o = Pe[i:i + 1000] - Ne[i:i + 1000] * 0.05; loc, ri, _ = Bc.ray.intersects_location(o, Ne[i:i + 1000], multiple_hits=True)
        if not len(ri): continue
        t_ = np.einsum("ij,ij->i", loc - o[ri], Ne[i:i + 1000][ri]) - 0.05; k_ = (t_ > -0.06) & (t_ < 10.0)
        np.minimum.at(gd, i + ri[k_], np.maximum(t_[k_], 0.0))
    over = np.isfinite(gd); nover = int((~over).sum()); Pe = Pe[over]; gd = dist(B, Pe) if len(Pe) else np.array([np.nan])   # the gap itself: to B's nearest surface
    gap = {"end_face_points": int(ef.sum()), "not_over_B": nover, "max_mm": round(float(gd.max()), 3), "p95_mm": round(float(np.percentile(gd, 95)), 3),
           "median_mm": round(float(np.median(gd)), 3), "over_0.2mm_points": int((gd > 0.2).sum()),
           "at_max": np.round(Pe[int(np.argmax(gd))], 1).tolist() if len(Pe) else None}
    r = {"kind": kind, "flush": fl, "shards": {"thin_points": int(thin.sum()), "of": int(len(Q)), "min_thickness_mm": round(float(th_ok.min()), 2) if len(th_ok) else None,
                                               "left_out_at_domino": int((~ok).sum()), "locations": np.round(Q[thin][:20], 1).tolist()},
         "corners": {"sharp_short_edges": int(step.sum()), "left_out_at_domino": int(edom.sum()), "faces_near_end": int(fz.sum()),
                     "locations": np.round(mid[step][:20], 1).tolist()},
         "flush_band": flb, "dots": dots, "bulge": bulge, "gap": gap, "watertight": bool(A.is_watertight),
         "note": "coordinates in the joint's frame (tools/joint_quality.py FRAMES), not the model's"}
    fok = kind == "end" or all(np.isfinite(fl[k]["median_mm"]) and abs(fl[k]["median_mm"]) <= 0.3 for k in ("outer", "inner"))
    r["pass"] = bool(fok and r["shards"]["thin_points"] == 0 and r["corners"]["sharp_short_edges"] == 0
                     and max(v["dist_mm"] for v in dots.values()) <= 0.3 and bulge["pass"] and gap["max_mm"] <= 0.2)
    return r


if __name__ == "__main__":
    args = sys.argv[1:]; glb, out = args[0], args[1]
    only = [args[i + 1] for i, a in enumerate(args) if a == "--joint"]
    sc = trimesh.load(glb, force="scene")
    M = {n: g.copy().apply_transform(sc.graph.get(n)[0]) for n, g in ((n, sc.geometry[sc.graph.get(n)[1]]) for n in sc.graph.nodes_geometry)}
    res = {}
    for jn, (a, b, R, dn, kind, rule, win) in FRAMES.items():
        if only and jn not in only: continue
        try:
            r = check(frame(M[a], R), frame(M[b], R), [frame(M[x], R) for x in dn if x in M], kind, win, lip=1.5 if rule == "crest_back_leg" else 0.5, local=rule != "arm_back_leg")
        except Exception as e:
            r = {"pass": False, "error": f"{type(e).__name__}: {str(e)[:200]}"}; res[jn] = r; print(f"{jn}: could not be measured ({r['error']}) -> FAIL", flush=True); continue
        r["rule"] = rule; res[jn] = r
        fl = r["flush"]; dm = max(v["dist_mm"] for v in r["dots"].values()); bu = r["bulge"]
        fs = f"flush outer {fl['outer']['median_mm']:+.2f} inner {fl['inner']['median_mm']:+.2f} mm (crease max proud {fl['outer']['crease_max_proud_mm']}/{fl['inner']['crease_max_proud_mm']}), " if fl else "flush n/a (inset), "
        print(f"{jn}: {fs}shards {r['shards']['thin_points']}, sharp short edges {r['corners']['sharp_short_edges']}, corners to dots max {dm:.3f} mm, "
              f"end past sides {max(bu['end_outline_past_outer_mm'], bu['end_outline_past_inner_mm']):+.2f} mm, faces off edge lines "
              f"{max(bu['face_off_edge_line_outer_mm'], bu['face_off_edge_line_inner_mm']):+.2f} mm, gap max {r['gap']['max_mm']:.3f} mm  -> {'PASS' if r['pass'] else 'FAIL'}", flush=True)
    json.dump({"model": glb, "joints": res}, open(out, "w"), indent=1)
    print("joint quality:", "PASS" if all(r["pass"] for r in res.values()) else "FAIL"); print(out)
