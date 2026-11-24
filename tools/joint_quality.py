"""USAGE: python -I tools/joint_quality.py MODEL.glb OUT.json [--side R|L ...]
Checks the three things Joe saw at the arm / back-leg joint (2026-11-23, gap.png and yuck.png), on the arm near the leg:
  flush       the step where the arm's outer and inner faces meet the leg's outer and inner faces: arm side-face points within
              0.5 mm of the leg vs the leg's side face at the same y, z (mm; 0 = flush, + = arm proud). flush_band, reported
              only: the v25 band measure (arm points up to 6 mm in front of the leg vs the leg 4 mm behind its front)
  shards      wood thinner than 1 mm: from each arm face near the leg, the distance to the arm's own opposite surface, counted
              only where that surface faces back (normals within 45 degrees of opposite), so a point near an ordinary
              square corner, whose ray leaves through the neighbouring face, is not a shard
  corners     sharp short edges near the end: edges under 0.5 mm whose faces meet at more than 20 degrees. A "double corner"
              is a step like that; a clean end has none (coplanar sliver triangles are invisible and not counted)
  dots        the arm end's 4 corners vs the GREEN dots (parts/joint_rules.json arm_back_leg): the leg's front corners, where its side
              planes (tools/joint_ends.side_planes) meet its front face, at each corner's own height (mm; pass <= 0.3)
  bulge       (a) the arm's end outline on the leg's front face past the leg's side planes, (b) within 5 mm of the leg, each arm
              side face off the straight line between its own top and bottom edges (sections every 0.5 mm); pass: both <= 0.3 mm
The Domino mortise in the arm end (DOMINO_AR*) is a real hole; everything within 1 mm of the Domino is left out and counted.
Flush is measured against the leg's own surface next to each arm point, not a fitted plane.
Pass thresholds: |flush median| <= 0.3 mm, no shard points, no sharp short edges, corners on the dots, no bulge. Prints a table and writes OUT.json."""
import sys, json
import numpy as np, trimesh

sys.path.insert(0, __file__.rsplit("/", 1)[0]); import joint_ends as je

args = sys.argv[1:]; glb, out = args[0], args[1]
sides = [args[i + 1] for i, a in enumerate(args) if a == "--side"] or ["R", "L"]
sc = trimesh.load(glb, force="scene")
M = {n: g.copy().apply_transform(sc.graph.get(n)[0]) for n, g in ((n, sc.geometry[sc.graph.get(n)[1]]) for n in sc.graph.nodes_geometry)}
res = {}
for S in sides:
    arm, leg = M[f"ARM_{S}"], M[f"BLEG_{S}"]; sg = 1.0 if S == "R" else -1.0
    # where the arm meets the leg: arm vertices within 2 mm of the leg
    d = np.abs(trimesh.proximity.signed_distance(leg, arm.vertices)); end = arm.vertices[d < 2.0]
    c = end.mean(0); dom = M[f"DOMINO_RA{S}"]
    from scipy.spatial import cKDTree
    away = lambda X: np.abs(trimesh.proximity.signed_distance(dom, X)) > 1.0
    # flush = the step where the arm's side face meets the leg's (the crease along the leg's front corner): arm side-face points
    # within 0.5 mm of the leg, each against the leg's side face at the same y and z. Also kept for comparison with v25's reports
    # (flush_band): arm side-face points up to 6 mm in front of the leg against the leg's face 4 mm behind its front at the same z.
    # A band like that reads the arm's own angle in plan (it meets the leg about 13 degrees off square, as traced) as a step.
    P, fi = trimesh.sample.sample_surface_even(arm, 120000, radius=0.4, seed=2); N = arm.face_normals[fi]
    near = (P[:, 1] > end[:, 1].min() - 1) & (P[:, 1] < end[:, 1].max() + 6) & (np.abs(P[:, 2] - c[2]) < 40)
    LP, lfi = trimesh.sample.sample_surface_even(leg, 200000, radius=0.3, seed=3); LN = leg.face_normals[lfi]
    lz = (np.abs(LP[:, 2] - c[2]) < 45) & (LP[:, 1] > end[:, 1].min() - 12) & (LP[:, 1] < end[:, 1].max() + 2)
    lz &= ~np.all((LP > dom.bounds[0] - 1.0) & (LP < dom.bounds[1] + 1.0), axis=1)   # not the walls of the Domino's mortise through the leg (they face +-x too)
    fl, flb = {}, {}
    inbox = np.all((P > dom.bounds[0] - 1.0) & (P < dom.bounds[1] + 1.0), axis=1)   # the Domino mortise in the arm end has +-x walls too
    for key, nsg in (("outer", sg), ("inner", -sg)):
        s = near & (N[:, 0] * nsg > 0.9); ls = lz & (LN[:, 0] * nsg > 0.9)
        t = cKDTree(LP[ls][:, 1:]); dq, j = t.query(P[s][:, 1:] * [0, 1] + [c[1] - 4, 0])   # same z, 4 mm behind the face
        off = (P[s, 0] - LP[ls][j, 0]) * nsg   # + = arm proud of the leg face, - = set back
        flb[key] = {"n": int(s.sum()), "median_mm": round(float(np.median(off)), 2), "p05_mm": round(float(np.percentile(off, 5)), 2),
                    "p95_mm": round(float(np.percentile(off, 95)), 2)}
        # the step at the crease: arm side-face points within 0.5 mm of the leg vs the leg's side face at the same (y, z)
        s = (N[:, 0] * nsg > 0.9) & (np.abs(P[:, 2] - c[2]) < 40) & (P[:, 1] < end[:, 1].max() + 3) & ~inbox & ((P[:, 0] - c[0]) * nsg > 8); s[s] = trimesh.proximity.closest_point(leg, P[s])[1] < 0.5
        dq, j = t.query(P[s][:, 1:]); off = ((P[s, 0] - LP[ls][j, 0]) * nsg)[dq < 2.0]   # only where the leg's side face is beside it
        if not len(off): off = np.array([np.nan])
        fl[key] = {"n": int((dq < 2.0).sum()), "of": int(s.sum()), "median_mm": round(float(np.median(off)), 2), "p05_mm": round(float(np.percentile(off, 5)), 2),
                   "p95_mm": round(float(np.percentile(off, 95)), 2), "leg_sample_dist_median_mm": round(float(np.median(dq[dq < 2.0])), 2) if (dq < 2.0).any() else None}
    # shards: thickness along -normal from arm faces within 40 mm of the end (away from the Domino)
    zone = np.linalg.norm(P - c, axis=1) < 40
    Q, NQ = P[zone], N[zone]; ok = away(Q)
    loc, ri, ti = arm.ray.intersects_location(Q - NQ * 0.02, -NQ, multiple_hits=False)
    th = np.full(len(Q), np.inf); opp = (arm.face_normals[ti] * NQ[ri]).sum(1) < -0.707
    th[ri[opp]] = np.linalg.norm(loc[opp] - Q[ri[opp]], axis=1)
    thin = (th < 1.0) & ok
    # corners: sharp short edges near the end (away from the Domino)
    E = arm.face_adjacency_edges; ang = np.degrees(arm.face_adjacency_angles)
    mid = arm.vertices[E].mean(1); el = np.linalg.norm(arm.vertices[E[:, 0]] - arm.vertices[E[:, 1]], axis=1)
    ez = np.linalg.norm(mid - c, axis=1) < 40; edom = ez & ~away(mid)
    step = ez & ~edom & (el < 0.5) & (ang > 20)
    fz = np.linalg.norm(arm.triangles_center - c, axis=1) < 40
    th_ok = th[ok & np.isfinite(th)]
    # dots: the arm end's 4 corners (end vertices extreme in +-x, +-z) vs the leg's front corners at the same heights
    lb0, lb1 = dom.bounds[0] - 1.0, dom.bounds[1] + 1.0   # (cheap: leave out the Domino's box, it runs through the leg's middle)
    PL = je.side_planes(leg, c, keep=lambda X: ~np.all((X > lb0) & (X < lb1), axis=1)); ev = arm.vertices[d < 0.5]; ctr = ev.mean(0); span = np.ptp(ev, 0) + 1e-9
    dots = {}
    for nm, sx_, sz_ in (("top_outer", sg, 1), ("top_inner", -sg, 1), ("bottom_outer", sg, -1), ("bottom_inner", -sg, -1)):
        cp = ev[np.argmax(sx_ * (ev[:, 0] - ctr[0]) / span[0] + sz_ * (ev[:, 2] - ctr[2]) / span[2])]
        pk = PL["plus_x" if sx_ > 0 else "minus_x"]; zc = float(cp[2])
        fq = lambda Y: np.c_[je.plane_x(pk, Y, zc) - sx_ * 0.4, Y, np.full(len(Y), zc)]
        Ys = np.arange(cp[1] + 25, cp[1] - 40, -0.5); k0 = int(np.argmax(leg.contains(fq(Ys))))   # first inside, coming back from the front
        yg = float(je.first_inside(leg, fq, Ys[k0:k0 + 1], Ys[k0 - 1:k0])[0])
        g = np.array([float(je.plane_x(pk, yg, zc)), yg, zc])
        dots[nm] = {"corner": np.round(cp, 2).tolist(), "green": np.round(g, 2).tolist(), "dist_mm": round(float(np.linalg.norm(cp - g)), 3)}
    # bulge: (a) the arm's end outline, ON the leg's front face (vertices within 0.5 mm of the leg), past the leg's side planes;
    # (b) within 5 mm of the leg, each side face of the arm vs the straight line between its own top and bottom edges, in
    # sections across the arm every 0.5 mm (option 2 of the pilot bulged here). (c), only reported: arm points within 5 mm of the
    # leg past the side planes; the arm leaves the leg at its traced angle, so in front of the leg this is the arm's own splay.
    pe = ev[:, 0] - je.plane_x(PL["plus_x"], ev[:, 1], ev[:, 2]); ie = je.plane_x(PL["minus_x"], ev[:, 1], ev[:, 2]) - ev[:, 0]
    pe, ie = (pe, ie) if sg > 0 else (ie, pe)
    chord = []
    for yq in np.arange(ev[:, 1].min() + 0.25, ev[:, 1].max() + 5.0, 0.5):
        sec = arm.section(plane_origin=[0, yq, 0], plane_normal=[0, 1, 0])
        if sec is None: continue
        V = sec.vertices[np.abs(sec.vertices[:, 2] - c[2]) < 45][:, [0, 2]]; mc = V.mean(0); sp_ = np.ptp(V, 0) + 1e-9
        ext = lambda a_, b_: V[np.argmax(a_ * (V[:, 0] - mc[0]) / sp_[0] + b_ * (V[:, 1] - mc[1]) / sp_[1])]
        for nm, sx_ in (("outer", sg), ("inner", -sg)):
            p_, q_ = ext(sx_, 1), ext(sx_, -1); n_ = np.array([q_[1] - p_[1], p_[0] - q_[0]])
            if np.linalg.norm(n_) < 2.0: continue                     # no side face in this section (it is all end face)
            n_ = n_ / np.linalg.norm(n_) * np.sign(n_[0]) * sx_
            W = V[(V[:, 1] > min(p_[1], q_[1]) + 0.3) & (V[:, 1] < max(p_[1], q_[1]) - 0.3)]
            W = W[(W - p_) @ n_ > -3.0]                               # this side's outline only
            if len(W): chord.append((nm, float(yq), float(((W - p_) @ n_).max())))
    cd = {nm: max([v for k_, y_, v in chord if k_ == nm], default=0.0) for nm in ("outer", "inner")}
    nb = (P[:, 1] < end[:, 1].max() + 8) & (np.abs(P[:, 2] - c[2]) < 45)
    nb[nb] = trimesh.proximity.closest_point(leg, P[nb])[1] < 5.0
    po = (P[:, 0] - je.plane_x(PL["plus_x"], P[:, 1], P[:, 2])); pi_ = (je.plane_x(PL["minus_x"], P[:, 1], P[:, 2]) - P[:, 0])
    po, pi_ = (po, pi_) if sg > 0 else (pi_, po)
    bulge = {"end_outline_past_outer_mm": round(float(pe.max()), 3), "end_outline_past_inner_mm": round(float(ie.max()), 3),
             "face_off_edge_line_outer_mm": round(cd["outer"], 3), "face_off_edge_line_inner_mm": round(cd["inner"], 3), "sections": len(chord),
             "info_within_5mm_past_side_planes_mm": {"outer": round(float(po[nb].max()), 3), "inner": round(float(pi_[nb].max()), 3), "of": int(nb.sum())}}
    bulge["pass"] = bool(max(pe.max(), ie.max(), cd["outer"], cd["inner"]) <= 0.3)
    r = {"flush": fl, "shards": {"thin_points": int(thin.sum()), "of": int(len(Q)), "thin_area_mm2": round(float(thin.sum() / len(Q) * arm.area_faces[fz].sum()), 1),
                                 "min_thickness_mm": round(float(th_ok.min()), 2) if len(th_ok) else None,
                                 "left_out_at_domino": int((~ok).sum()), "locations": np.round(Q[thin][:20], 1).tolist()},
         "corners": {"sharp_short_edges": int(step.sum()), "left_out_at_domino": int(edom.sum()), "faces_near_end": int(fz.sum()),
                     "locations": np.round(mid[step][:20], 1).tolist()},
         "flush_band": flb, "dots": dots, "bulge": bulge, "watertight": bool(arm.is_watertight)}
    r["pass"] = bool(np.isfinite(fl["outer"]["median_mm"]) and np.isfinite(fl["inner"]["median_mm"]) and abs(fl["outer"]["median_mm"]) <= 0.3 and abs(fl["inner"]["median_mm"]) <= 0.3 and r["shards"]["thin_points"] == 0 and r["corners"]["sharp_short_edges"] == 0
                     and max(v["dist_mm"] for v in dots.values()) <= 0.3 and bulge["pass"])
    res[f"ARM_{S}~BLEG_{S}"] = r
    print(f"ARM_{S}~BLEG_{S}: outer {fl['outer']['median_mm']:+.2f} mm, inner {fl['inner']['median_mm']:+.2f} mm, "
          f"shard points {r['shards']['thin_points']} (min {r['shards']['min_thickness_mm']} mm), sharp short edges {r['corners']['sharp_short_edges']}, "
          f"corners to dots max {max(v['dist_mm'] for v in dots.values()):.2f} mm, bulge: end past sides {max(bulge['end_outline_past_outer_mm'], bulge['end_outline_past_inner_mm']):+.2f} mm, "
          f"faces off their edge lines {max(bulge['face_off_edge_line_outer_mm'], bulge['face_off_edge_line_inner_mm']):+.2f} mm  -> {'PASS' if r['pass'] else 'FAIL'}")
json.dump({"model": glb, "joints": res}, open(out, "w"), indent=1); print(out)
