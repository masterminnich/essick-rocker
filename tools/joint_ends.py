"""Joint ends built ON the other part, with clean topology (Joe, 2026-11-23: "the wood sits flush ... the wooden piece glitches
into the other and creates a shard ... the corner of one of the pieces of wood has two corners").
Used by tools/build_model.py for the joints listed in parts/joint_rules.json. No booleans: a member is a structured grid of
points (ns along it x nt across x nl through its thickness), its end row is placed exactly on the other part's surface, and the
solid is the grid's six boundary sheets. So the end has exactly four corners, lies on the other part, and leaves no slivers.

  side_planes(part, centre, keep) the part's two side faces near `centre`, fitted as planes x = a + b*y + c*z
  blend_weight(Y, Y0, L)          1 at the joint (Y <= Y0), 0 from Y0 + L on, smoothstep between (zero slope at both ends)
  first_inside(part, f, lo, hi)   per column: the parameter where the curve f(Y) enters `part` (bisection on containment)
  block_solid(G)                  closed mesh from an (ns, nt, nl, 3) grid"""
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
