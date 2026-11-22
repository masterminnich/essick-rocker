"""USAGE: git show f3b1348:templates/out/rocker_geom.json > /tmp/rocker_geom_old.json
       tools/py.sh templates/rocker_vs_old.py --old /tmp/rocker_geom_old.json [--new templates/out/rocker_geom.json]
Difference between the v9-era rocker template (PR #6, left-sheet frame) and the current one (model v24, design frame, carried to
the left sheet with its to_left): distance from each outline to the other (both ways), per region, as drawn and after the best
rigid fit (2D ICP); overall length, leg marks, bend numbers. Tiny compute."""
import json, argparse, numpy as np
from scipy.spatial import cKDTree
ap = argparse.ArgumentParser(); ap.add_argument("--old", required=True); ap.add_argument("--new", default="templates/out/rocker_geom.json"); a = ap.parse_args()
O, N = json.load(open(a.old)), json.load(open(a.new))
def dens(p, ds=0.5):
    p = np.vstack([p, p[:1]]); s = np.r_[0, np.cumsum(np.linalg.norm(np.diff(p, axis=0), axis=1))]; ss = np.arange(0, s[-1], ds)
    return np.c_[np.interp(ss, s, p[:, 0]), np.interp(ss, s, p[:, 1])]
TL = N["to_left"]; th = np.radians(TL["rotation_deg"]); c, s = np.cos(th), np.sin(th)
nl = np.array(N["outline"]); nl = np.c_[c * nl[:, 0] - s * nl[:, 1] + TL["shift_u_mm"], s * nl[:, 0] + c * nl[:, 1] + TL["shift_v_mm"]]
po, pn = dens(np.array(O["outline"])), dens(nl)
def report(pn, tag):
    to, tn = cKDTree(po), cKDTree(pn); dn = to.query(pn)[0]; do = tn.query(po)[0]
    print(f"{tag}: new->old max {dn.max():.2f} rms {np.sqrt(np.mean(dn ** 2)):.2f} | old->new max {do.max():.2f} rms {np.sqrt(np.mean(do ** 2)):.2f}")
    for name, lo, hi in (("tail end u<-400", -600, -400), ("middle -400..560", -400, 560), ("nose end u>560", 560, 700)):
        k = (pn[:, 0] >= lo) & (pn[:, 0] < hi); k2 = (po[:, 0] >= lo) & (po[:, 0] < hi)
        d = np.r_[dn[k], do[k2]]
        print(f"   {name}: max {d.max():.2f} rms {np.sqrt(np.mean(d ** 2)):.2f}")
    return dn
report(pn, "as drawn (left sheet)")
# best rigid fit of new onto old (ICP, middle only so the re-drawn ends do not drive it)
q = pn.copy(); rot = 0.0; m = (q[:, 0] > -400) & (q[:, 0] < 560); to = cKDTree(po)
for _ in range(30):
    i = to.query(q[m])[1]; A, B = q[m], po[i]; ca, cb = A.mean(0), B.mean(0); H = (A - ca).T @ (B - cb); U_, _, Vt = np.linalg.svd(H)
    R = Vt.T @ U_.T
    if np.linalg.det(R) < 0: Vt[1] *= -1; R = Vt.T @ U_.T
    q = (q - ca) @ R.T + cb; rot += np.degrees(np.arctan2(R[1, 0], R[0, 0]))
print(f"rigid fit on the middle: rot {rot:+.2f} deg, shift of the centroid {np.round(q[m].mean(0) - pn[m].mean(0), 2).tolist()} mm")
report(q, "after best rigid fit")
# top and bottom edges in the middle, vertical difference (as drawn)
def edge(p, top):
    k = (p[:, 0] > -400) & (p[:, 0] < 560); p = p[k]; uu = np.arange(-395, 556, 5.0); out = []
    for u in uu:
        w = p[np.abs(p[:, 0] - u) < 1.0]; out.append(w[:, 1].max() if top else w[:, 1].min())
    return uu, np.array(out)
for nm, top in (("top", True), ("bottom", False)):
    uu, vo = edge(po, top); _, vn = edge(pn, top); d = vn - vo; i = np.argmax(np.abs(d))
    print(f"{nm} edge, new - old (v, as drawn, u -395..555): mean {d.mean():+.2f}, max |d| {np.abs(d).max():.2f} at u {uu[i]:.0f}, rms {np.sqrt(np.mean(d ** 2)):.2f}")
print(f"overall length: old {O['total_length']:.1f}, new {N['total_length']:.1f} ({N['total_length'] - O['total_length']:+.1f})")
print(f"tail tip: old {O['tip']}, new (left sheet) {nl[0].round(1).tolist()}; front-most u: old {O['front_end_u']:.1f}, new (left sheet) {nl[:, 0].max():.1f}")
for k in ("bleg_rear_lo", "bleg_front_lo", "fleg_rear_lo", "fleg_front_lo"):
    lo, ln = O["legs"][k], N["legs"][k]; ul = c * ln["u"] - s * ln["v"] + TL["shift_u_mm"]
    print(f"  {k}: old u {lo['u']:.1f}, new u {ln['u']:.1f} (design) = {ul:.1f} (left sheet) -> {ul - lo['u']:+.1f}")
print(f"bend R min convex/concave: old {O['R_min'][0]:.0f}/{O['R_min'][1]:.0f}, new {N['R_min'][0]:.0f}/{N['R_min'][1]:.0f}; S reverses: old u {O['u_inflection']:.0f} ({O['u_rest'] - O['u_inflection']:.0f} behind rest), new u {[round(x) for x in N['u_inflection']]} (rest u {N['u_rest']:.0f})")
print(f"tiles: old {O['tiles']}, new {N['tiles']}")
