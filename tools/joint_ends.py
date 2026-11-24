"""Joint ends built ON the other part, with clean topology (Joe, 2026-11-23: "the wood sits flush ... the wooden piece glitches
into the other and creates a shard ... the corner of one of the pieces of wood has two corners").
Used by tools/build_model.py for the joints listed in parts/joint_rules.json. No booleans: a member is a structured grid of
points (ns along it x nt across x nl through its thickness), its end row is placed exactly on the other part's surface, and the
solid is the grid's six boundary sheets. So the end has exactly four corners, lies on the other part, and leaves no slivers.

  side_planes(part, centre, keep) the part's two side faces near `centre`, fitted as planes x = a + b*y + c*z
  blend_weight(Y, Y0, L)          1 at the joint (Y <= Y0), 0 from Y0 + L on, smoothstep between (zero slope at both ends)
  first_inside(part, f, lo, hi)   per column: the parameter where the curve f(Y) enters `part` (bisection on containment)
  block_solid(G)                  closed mesh from an (ns, nt, nl, 3) grid
The dots rule for any member end (parts/joint_rules.json; Joe, 2026-11-23, "a dot at each corner of the piece of wood ... basically a
rectangular prism"):
  face_planes(part, centre, ax)   side_planes for any axis: the part's two faces square to world axis `ax`, fitted as planes
  plane_at(pl, X)                 the plane's `ax` coordinate at the other two coordinates of X
  enter(part, f, s_out, s_in)     per column: where the curve f(S) first enters `part`, scanning from s_out (outside) to s_in, then bisection
  dots_end(...)                   green dots, red dots and the per-edge corrections for one end of a member
  corrected(p, ...)               the member with those corrections: bilinear across its section, fading as (1 - u)^2 over L"""
import numpy as np, trimesh


def side_planes(part, centre, dy=60.0, dz=60.0, keep=None):
    """keep: optional P -> bool mask of surface samples to use (e.g. leave out a mortise's walls, which also face +-x)"""
    P, fi = trimesh.sample.sample_surface_even(part, 80000, radius=0.7, seed=4); N = part.face_normals[fi]
    near = (np.abs(P[:, 1] - centre[1]) < dy) & (np.abs(P[:, 2] - centre[2]) < dz)
    if keep is not None: near[near] = keep(P[near])
    out = {}
    for key, sg in (("plus_x", 1.0), ("minus_x", -1.0)):
        s = near & (N[:, 0] * sg > 0.95)
        A = np.c_[np.ones(s.sum()), P[s, 1], P[s, 2]]; c, *_ = np.linalg.lstsq(A, P[s, 0], rcond=None)
        out[key] = {"coef": c, "rms_mm": float(np.sqrt(np.mean((A @ c - P[s, 0]) ** 2))), "n": int(s.sum())}
    return out


def plane_x(pl, Y, Z):
    c = pl["coef"]; return c[0] + c[1] * Y + c[2] * Z


def blend_weight(Y, Y0, L):
    u = np.clip((np.asarray(Y, float) - Y0) / L, 0.0, 1.0); return 1.0 - u * u * (3.0 - 2.0 * u)


def first_inside(part, f, lo, hi, iters=24):
    """f(Y) -> (k, 3) points for an array Y of k parameters (one per column). For each column, the Y where the point crosses
    `part`'s surface, assuming f(lo) is inside and f(hi) outside. Returns Y (k,)."""
    a = np.asarray(lo, float).copy(); b = np.asarray(hi, float).copy()
    ia, ib = part.contains(f(a)), part.contains(f(b))
    assert ia.all() and not ib.any(), f"first_inside: bracket does not straddle the surface ({(~ia).sum()} columns outside at lo, e.g. {np.round(f(a)[~ia][:3], 1).tolist()}; {ib.sum()} inside at hi)"
    for _ in range(iters):
        m = (a + b) / 2; ins = part.contains(f(m)); a = np.where(ins, m, a); b = np.where(ins, b, m)
    return (a + b) / 2


def block_solid(G):
    G = np.asarray(G, float); ns, nt, nl, _ = G.shape
    S, T, L = np.meshgrid(np.arange(ns), np.arange(nt), np.arange(nl), indexing="ij"); ID = (S * nt + T) * nl + L
    F = []
    for idx in (ID[:, :, 0], ID[:, :, -1], ID[:, 0, :], ID[:, -1, :], ID[0, :, :], ID[-1, :, :]):
        a, b, c, d = idx[:-1, :-1].ravel(), idx[1:, :-1].ravel(), idx[1:, 1:].ravel(), idx[:-1, 1:].ravel()
        F.append(np.c_[a, b, c]); F.append(np.c_[a, c, d])
    m = trimesh.Trimesh(G.reshape(-1, 3), np.vstack(F), process=True); m.remove_unreferenced_vertices(); m.fix_normals()
    assert m.is_volume, "block_solid: not a closed volume"
    return m


def face_planes(part, centre, ax, win=60.0, keep=None, thr=0.95):
    """the part's two faces square to world axis `ax` (normals +-ax within acos(thr)) near `centre`, each fitted as a plane
    X[ax] = a + b X[o0] + c X[o1] (o = the other two axes, in order), from samples within `win` mm of centre in those two axes
    (win: one value, or one per axis o0, o1: keep it narrow along the part's length where its face is curved).
    keep: optional P -> bool mask of samples to use. Keys 'plus' and 'minus' (the face whose normal points to +ax / -ax)."""
    P, fi = trimesh.sample.sample_surface_even(part, 80000, radius=0.7, seed=4); N = part.face_normals[fi]
    o = [i for i in range(3) if i != ax]; near = np.all(np.abs(P[:, o] - np.asarray(centre, float)[o]) < np.broadcast_to(np.asarray(win, float), (2,)), axis=1)
    if keep is not None: near[near] = keep(P[near])
    out = {}
    for key, sg in (("plus", 1.0), ("minus", -1.0)):
        s = near & (N[:, ax] * sg > thr); assert s.sum() > 30, f"face_planes: only {s.sum()} samples on the {key} face"
        A = np.c_[np.ones(s.sum()), P[s][:, o]]; c, *_ = np.linalg.lstsq(A, P[s, ax], rcond=None)
        out[key] = {"coef": c, "ax": ax, "rms_mm": float(np.sqrt(np.mean((A @ c - P[s, ax]) ** 2))), "n": int(s.sum())}
    return out


def plane_at(pl, X):
    o = [i for i in range(3) if i != pl["ax"]]; X = np.atleast_2d(X); c = pl["coef"]; return c[0] + c[1] * X[:, o[0]] + c[2] * X[:, o[1]]


def enter(part, f, s_out, s_in, step=0.5):
    """f(S) -> (k, 3) for S of shape (k,), one parameter per column. For each column, the S where f first enters `part`, scanning from
    s_out (must be outside) towards s_in in steps of about `step`, then bisection between the last point outside and the first inside."""
    s_out = np.atleast_1d(np.asarray(s_out, float)); s_in = np.broadcast_to(np.asarray(s_in, float), s_out.shape).astype(float)
    n = int(np.ceil(np.abs(s_in - s_out).max() / step)) + 1; fr = np.linspace(0.0, 1.0, n)
    assert not part.contains(f(s_out)).any(), "enter: a column starts inside"
    k0 = np.full(len(s_out), -1)
    for i in range(1, n):
        todo = k0 < 0
        if not todo.any(): break
        S = s_out + fr[i] * (s_in - s_out); ins = part.contains(f(S)); k0[todo & ins] = i
    assert (k0 > 0).all(), f"enter: {(k0 < 0).sum()} columns never enter"
    lo = s_out + fr[k0] * (s_in - s_out); hi = s_out + fr[k0 - 1] * (s_in - s_out)
    return first_inside(part, f, lo, hi)


def dots_end(other, p, edges, ax, planes, s_out, s_in, msd, inset=0.4, clamp=None):
    """Joe's dots rule for ONE end of a member that ends on `other`.
    p(S, T, Lc) -> (k, 3): the member as traced (and carried on straight past its end), S along it, T and Lc in [0, 1] across and through.
    edges: {name: (t, l, key)}: the member's 4 long edges (t, l in {0, 1}) and the face of `other` each must run flush into: 'plus' or
           'minus' (planes[key], the face whose normal points to +ax / -ax), or None (that edge only ends ON `other`, no correction).
    msd: +1 if the member lies at larger S than this end, -1 at smaller S. s_out: an S on the member side, outside `other`; s_in: past the joint.
    GREEN dot of an edge: the edge's own line with its `ax` coordinate put on the face plane, where it enters `other` (containment is
    tested `inset` mm inside the plane), i.e. the corner of `other` at the height of this edge. RED dot: where the traced edge enters
    `other`. Correction of an edge: d_e = green[ax] - traced edge[ax] at the dot's S (the other coordinates follow from the edge itself).
    planes: face_planes(other, ...) for all edges, or a function (edge name, red dot) -> face_planes fitted locally at that edge.
    clamp: optional X -> X keeping a point within `other` (only to bracket the bisection, as for the arm). Returns green, red, cor
    ({name: (s_e, d_e)} for corrected edges) and the planes used per edge."""
    green, red, cor, used = {}, {}, {}, {}
    for nm, (te, le, key) in edges.items():
        f0 = lambda S: (clamp(p(S, np.full(len(S), te), np.full(len(S), le))) if clamp else p(S, np.full(len(S), te), np.full(len(S), le)))
        sr = float(enter(other, f0, [s_out], [s_in])[0]); red[nm] = p(np.array([sr]), np.array([te]), np.array([le]))[0]
        if key is None: green[nm] = red[nm]; continue
        pl = planes(nm, red[nm]) if callable(planes) else planes; used[nm] = pl[key]
        pk = pl[key]; sgi = -inset if key == "plus" else inset
        def fq(S, te=te, le=le, pk=pk, sgi=sgi):
            X = p(S, np.full(len(S), te), np.full(len(S), le)).copy(); X[:, ax] = plane_at(pk, X) + sgi
            return clamp(X) if clamp else X
        sg = float(enter(other, fq, [s_out], [s_in])[0]); X = p(np.array([sg]), np.array([te]), np.array([le]))[0].copy()
        g = X.copy(); g[ax] = float(plane_at(pk, g)[0]); green[nm] = g; cor[nm] = (sg, float(g[ax] - X[ax]))
    return green, red, cor, used


def corrected(p, edges, cor, ax, L, msd):
    """p plus the dots correction of one end: at (S, T, Lc) the sum over the corrected edges of w_e * d_e * (1 - u)^2, w_e bilinear in
    (T, Lc) (1 on edge e, 0 on the others: each face stays the straight surface between its two edges), u = msd * (S - s_e) / L capped
    at 1 (full at the edge's own dot, zero with zero slope at L from it; past the dot, inside `other`, it carries on smoothly)."""
    def pc(S, T, Lc):
        X = p(S, T, Lc).copy(); S = np.asarray(S, float); T = np.asarray(T, float); Lc = np.asarray(Lc, float)
        for nm, (se, de) in cor.items():
            te, le, _ = edges[nm]; w = (T if te else 1 - T) * (Lc if le else 1 - Lc)
            X[:, ax] = X[:, ax] + w * de * (1.0 - np.minimum(msd * (S - se) / L, 1.0)) ** 2
        return X
    return pc
