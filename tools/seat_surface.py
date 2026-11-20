"""USAGE: tools/py.sh -m 2 -t 5 tools/seat_surface.py
Seat top surface from the blue-tape dots (seat/dots.csv), design intent = symmetric about X = 0.
 1. Split dots: FRONT FACE (y > 500 and more than 9 mm below a dot in the same column, |dx| < 15 mm, within 30 mm) vs TOP.
    (Same column only: the thigh troughs climb steeply sideways, so x-neighbours are legitimately 10+ mm higher.)
 2. Mirror the top dots to -x (dots with |x| < 3 mm are not duplicated).
 3. Fit (a) polynomials even in x, z = sum a_ij (x/250)^(2i) ((y-300)/250)^j, several degree pairs, and
        (b) thin-plate smoothing splines (scipy RBFInterpolator), several smoothing values.
    Choose by leave-one-dot-out cross-validation (a dot and its mirror image are left out together).
 4. Rim reference: z_rim(y) = highest point of the fitted surface across the station y (|x| within the dotted region,
    sampled every 2 mm in x and y); depth below rim = z_rim(y) - z(x, y).  (The outermost dots sit on the trough walls,
    not on the rim, so a line through them misses by 2+ mm.)
 5. As-measured asymmetry: the dots cover the RIGHT half only (x 0..254 mm), so left/right is measured against the chair
    cloud: left-half cloud points vs the surface, right-half cloud points vs the surface (cloud noise ~2 mm, so regional
    MEDIANS resolve ~0.3-0.5 mm).
Outputs (seat/): surface.json (formula + coefficients + CV numbers), surface_grid.csv (10 mm grid inside the measured
region, mirrored), depth_map.png, sections.png (3 transverse stations + centreline), front_face.csv, REPORT.md.
Compute: tiny (< 300 MB, seconds)."""
import sys, json, csv
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent; sys.path.insert(0, str(ROOT))
import numpy as np
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from scipy.interpolate import RBFInterpolator
from scipy.spatial import Delaunay, cKDTree

OUT = ROOT / "seat"
R = list(csv.DictReader(open(OUT / "dots.csv")))
X = np.array([[float(r[k]) for k in ("x_mm", "y_mm", "z_mm")] for r in R])
SN = np.array([float(r["s_normal_mm"]) for r in R]); ids = np.array([int(r["id"]) for r in R])

# ---------------------------------------------------------------- 1. front face vs top
front = np.zeros(len(X), bool)
for i, p in enumerate(X):
    if p[1] < 500: continue
    nb = (np.abs(X[:, 0] - p[0]) < 15) & (np.hypot(X[:, 0] - p[0], X[:, 1] - p[1]) < 30) & (np.arange(len(X)) != i)
    if nb.any() and X[nb, 2].max() - p[2] > 9: front[i] = True
T = X[~front]; F = X[front]
print("top dots", len(T), " front-face dots", len(F), "ids", ids[front].tolist())

# ---------------------------------------------------------------- 2. mirror
def mirror(P):
    m = np.abs(P[:, 0]) >= 3
    Q = P[m].copy(); Q[:, 0] *= -1
    return np.r_[P, Q], np.r_[np.arange(len(P)), np.flatnonzero(m)]
M, src = mirror(T)

# ---------------------------------------------------------------- 3. fits + leave-one-dot-out CV
def pfeat(x, y, dx, dy):
    u, v = (np.asarray(x) / 250.0) ** 2, (np.asarray(y) - 300.0) / 250.0
    return np.stack([u ** i * v ** j for i in range(dx + 1) for j in range(dy + 1)], 1)
def fit_poly(P, dx, dy):
    c = np.linalg.lstsq(pfeat(P[:, 0], P[:, 1], dx, dy), P[:, 2], rcond=None)[0]
    return lambda x, y: pfeat(x, y, dx, dy) @ c, c
def fit_tps(P, s):
    r = RBFInterpolator(P[:, :2], P[:, 2], kernel="thin_plate_spline", smoothing=s)
    return lambda x, y: r(np.c_[np.atleast_1d(x), np.atleast_1d(y)]), None
def loo(fitter):
    e = []
    for k in range(len(T)):
        keep = src != k
        f, _ = fitter(M[keep]); e.append(float(f(T[k:k + 1, 0], T[k:k + 1, 1])[0] - T[k, 2]))
    e = np.array(e); return float(np.sqrt((e ** 2).mean())), float(np.abs(e).max()), e
cands = {}
for dx in (2, 3, 4):
    for dy in (3, 4, 5):
        cands[f"poly x^{2*dx} y^{dy}"] = (lambda P, dx=dx, dy=dy: fit_poly(P, dx, dy))
for s in (0.0, 1.0, 5.0, 20.0, 80.0):
    cands[f"tps s={s:g}"] = (lambda P, s=s: fit_tps(P, s))
cv = {}
for name, fz in cands.items():
    rms, mx, e = loo(fz); f, _ = fz(M); fr = f(T[:, 0], T[:, 1]) - T[:, 2]
    cv[name] = dict(loo_rms=rms, loo_max=mx, fit_rms=float(np.sqrt((fr ** 2).mean())), fit_max=float(np.abs(fr).max()))
    print(f"{name:16s} LOO rms {rms:.2f} max {mx:.2f} | fit rms {cv[name]['fit_rms']:.2f} max {cv[name]['fit_max']:.2f}")
lo = min(v["loo_rms"] for v in cv.values())
best = max((k for k in cv if k.startswith("tps") and cv[k]["loo_rms"] <= lo + 0.01), key=lambda k: float(k.split("=")[1]),
           default=min(cv, key=lambda k: cv[k]["loo_rms"]))
bestpoly = min((k for k in cv if k.startswith("poly")), key=lambda k: cv[k]["loo_rms"])
print("best:", best, " best polynomial:", bestpoly)
surf, _ = cands[best](M)
# interior LOO: dots that stay inside the convex hull of the others (no extrapolation)
_, _, e_all = loo(cands[best])
interior = np.array([Delaunay(M[src != k][:, :2]).find_simplex(T[k, :2]) >= 0 for k in range(len(T))])
loo_int = dict(n=int(interior.sum()), rms=float(np.sqrt((e_all[interior] ** 2).mean())), max=float(np.abs(e_all[interior]).max()),
               edge_n=int((~interior).sum()), edge_rms=float(np.sqrt((e_all[~interior] ** 2).mean())))
print("LOO interior", loo_int)
# explicit thin-plate formula, verified against scipy: z = sum_i w_i r_i^2 ln r_i + a0 + a1*x + a2*y  (x, y, r in mm)
sm = float(best.split("=")[1]) if best.startswith("tps") else 0.0
Np = len(M); K = lambda A, B: (lambda r: np.where(r > 0, r ** 2 * np.log(np.maximum(r, 1e-12)), 0.0))(np.linalg.norm(A[:, None] - B[None], axis=2))
Pm = np.c_[np.ones(Np), M[:, :2]]
Asys = np.block([[K(M[:, :2], M[:, :2]) + sm * np.eye(Np), Pm], [Pm.T, np.zeros((3, 3))]])
sol = np.linalg.solve(Asys, np.r_[M[:, 2], np.zeros(3)]); tw, ta = sol[:Np], sol[Np:]
tps_eval = lambda x, y: K(np.c_[np.atleast_1d(x), np.atleast_1d(y)], M[:, :2]) @ tw + ta[0] + ta[1] * np.atleast_1d(x) + ta[2] * np.atleast_1d(y)
chk = np.c_[np.random.default_rng(0).uniform(-200, 200, 200), np.random.default_rng(1).uniform(100, 500, 200)]
tps_dev = float(np.abs(tps_eval(chk[:, 0], chk[:, 1]) - surf(chk[:, 0], chk[:, 1])).max()); print("explicit TPS vs scipy max dev mm", tps_dev)
dxp, dyp = int(bestpoly.split("x^")[1].split()[0]) // 2, int(bestpoly.split("y^")[1])
psurf, pcoef = fit_poly(M, dxp, dyp)
_, _, e_best = loo(cands[best])

# ---------------------------------------------------------------- 4. rim line + grid + depth
outer = T[T[:, 0] > 215]
hull = Delaunay(M[:, :2])
ry = np.arange(np.floor(T[:, 1].min()), np.ceil(T[:, 1].max()) + 1, 2.0); rz = []; rxm = []
for y0 in ry:
    xs = np.arange(-T[:, 0].max(), T[:, 0].max() + 0.1, 2.0); ok = hull.find_simplex(np.c_[xs, np.full_like(xs, y0)]) >= 0
    if ok.sum() < 3: rz.append(np.nan); rxm.append(np.nan); continue
    z = surf(xs[ok], np.full(ok.sum(), y0)); rz.append(z.max()); rxm.append(abs(xs[ok][np.argmax(z)]))
rz = np.array(rz); g = np.isfinite(rz); ry, rz, rxm = ry[g], rz[g], np.array(rxm)[g]
zr = lambda y: np.interp(y, ry, rz)
rc = np.polyfit(ry, rz, 2); rim_res = rz - np.polyval(rc, ry)
gx, gy = np.meshgrid(np.arange(-250, 251, 10.0), np.arange(60, 541, 10.0))
inside = hull.find_simplex(np.c_[gx.ravel(), gy.ravel()]) >= 0
G = np.c_[gx.ravel(), gy.ravel()][inside]
gz = surf(G[:, 0], G[:, 1]); gpz = psurf(G[:, 0], G[:, 1]); depth = zr(G[:, 1]) - gz
with open(OUT / "surface_grid.csv", "w") as f:
    f.write(f"x_mm,y_mm,z_mm ({best}),z_poly_mm ({bestpoly}),depth_below_rim_mm\n")
    for p, z1, z2, d in zip(G, gz, gpz, depth): f.write(f"{p[0]:.0f},{p[1]:.0f},{z1:.2f},{z2:.2f},{d:.2f}\n")
deep = int(np.argmax(depth))

# ---------------------------------------------------------------- 5. asymmetry vs the cloud
C = np.load(ROOT / "work/dense/chair_dense.npy")[:, :3]
cin = hull.find_simplex(C[:, :2]) >= 0
Cs = C[cin]; dc = Cs[:, 2] - surf(Cs[:, 0], Cs[:, 1]); Cs, dc = Cs[np.abs(dc) < 8], dc[np.abs(dc) < 8]
asym = {}
for lab, m in (("right (x>20)", Cs[:, 0] > 20), ("left (x<-20)", Cs[:, 0] < -20)):
    asym[lab] = dict(n=int(m.sum()), median=float(np.median(dc[m])), mad_sigma=float(1.48 * np.median(np.abs(dc[m] - np.median(dc[m])))))
bands = []
for y0 in range(60, 540, 80):
    row = {"y": f"{y0}-{y0 + 80}"}
    for lab, sgn in (("R", 1), ("L", -1)):
        m = (Cs[:, 1] >= y0) & (Cs[:, 1] < y0 + 80) & (sgn * Cs[:, 0] > 20)
        row[lab] = (float(np.median(dc[m])), int(m.sum())) if m.sum() >= 15 else (np.nan, int(m.sum()))
    bands.append(row)
print("cloud minus surface:", asym)
for b in bands: print("  y", b["y"], "R %.2f (%d)" % b["R"], "L %.2f (%d)" % b["L"])

# ---------------------------------------------------------------- plan outline (cloud, approximate)
OL = []
for y0 in range(0, 560, 20):
    m = (C[:, 1] >= y0) & (C[:, 1] < y0 + 20) & (np.abs(C[:, 2] - zr(y0 + 10)) < 30) & (np.abs(C[:, 0]) < 340)
    if m.sum() >= 20: OL.append((y0 + 10, float(np.percentile(np.abs(C[m, 0]), 98)), int(m.sum())))
OL = np.array(OL); print("outline |x| by y:", [(int(a), round(b)) for a, b, _ in OL])

# ---------------------------------------------------------------- front face
with open(OUT / "front_face.csv", "w") as f:
    f.write("id,x_mm,y_mm,z_mm,top_surface_z_above_mm\n")
    for i in np.flatnonzero(front):
        p = X[i]; nb = (np.abs(X[:, 0] - p[0]) < 15) & (np.hypot(X[:, 0] - p[0], X[:, 1] - p[1]) < 30) & ~front
        f.write(f"{ids[i]},{p[0]:.2f},{p[1]:.2f},{p[2]:.2f},{X[nb, 2].max() - p[2]:.1f}\n")

# ---------------------------------------------------------------- plots
fig, ax = plt.subplots(figsize=(9, 9))
D = np.full(gx.shape, np.nan); D.ravel()[np.flatnonzero(inside)] = depth
cs = ax.contourf(gx, gy, D, levels=np.arange(np.floor(np.nanmin(D)), np.ceil(np.nanmax(D)) + 1, 2), cmap="Blues")
cl = ax.contour(gx, gy, D, levels=np.arange(0, np.ceil(np.nanmax(D)) + 1, 5), colors="k", linewidths=0.6); ax.clabel(cl, fmt="%d", fontsize=8)
ax.scatter(T[:, 0], T[:, 1], s=10, c="#d2451e", label="tape dots (measured, right half)")
ax.scatter(-T[:, 0], T[:, 1], s=10, facecolors="none", edgecolors="#d2451e", linewidths=0.6, label="mirrored")
ax.scatter(F[:, 0], F[:, 1], s=22, marker="s", c="k", label="front-face dots")
ax.plot(G[deep, 0], G[deep, 1], "k+", ms=14)
plt.colorbar(cs, ax=ax, label="depth below rim (mm)"); ax.set_aspect("equal"); ax.legend(loc="lower right", fontsize=8)
ax.set_xlabel("x (mm, + = chair's right)"); ax.set_ylabel("y (mm, + = forward)")
ax.set_title(f"Seat depth below rim (rim = highest point across each station)\nsurface: thin-plate spline ({best}) on mirrored dots")
ax.plot(OL[:, 1], OL[:, 0], "k--", lw=0.8, label="seat edge (cloud, approx.)"); ax.plot(-OL[:, 1], OL[:, 0], "k--", lw=0.8)
ax.legend(loc="lower right", fontsize=8)
plt.tight_layout(); plt.savefig(OUT / "figures/depth_map.png", dpi=110); plt.close()

ys = [np.percentile(T[:, 1], 15), np.percentile(T[:, 1], 50), np.percentile(T[:, 1], 85)]
ys = [float(round(y / 10) * 10) for y in ys]
fig, axs = plt.subplots(4, 1, figsize=(11, 16))
sec = {}
for a, y0 in zip(axs[:3], ys):
    xs = np.arange(-250, 251, 2.0); ok = hull.find_simplex(np.c_[xs, np.full_like(xs, y0)]) >= 0
    z = surf(xs[ok], np.full(ok.sum(), y0)); sec[f"y={y0:.0f}"] = dict(x=xs[ok].tolist(), z=np.round(z, 2).tolist())
    a.plot(xs[ok], z, "k-", lw=1.2, label="fitted surface")
    a.plot(xs[ok], zr(np.full(ok.sum(), y0)), "k--", lw=0.6, label="rim (station max)")
    m = np.abs(T[:, 1] - y0) < 12; a.plot(T[m, 0], T[m, 2], "o", c="#d2451e", ms=4, label="dots within 12 mm")
    mc = (np.abs(C[:, 1] - y0) < 4) & (np.abs(C[:, 0]) < 300) & (np.abs(C[:, 2] - zr(y0)) < 40)
    a.plot(C[mc, 0], C[mc, 2], ".", c="0.6", ms=2, label="cloud within 4 mm (both halves)")
    a.set_title(f"transverse section y = {y0:.0f} mm  (depth at x=0: {zr(y0) - surf(0, y0)[0]:.1f} mm)"); a.set_aspect(3); a.grid(alpha=0.3)
    a.legend(fontsize=7, loc="upper center", ncol=4, bbox_to_anchor=(0.5, -0.12)); a.set_ylabel("z mm (3x vert.)")
yy = np.arange(T[:, 1].min(), T[:, 1].max(), 2.0)
for x0, st in ((0, "k-"), (120, "k-."), (200, "k:")):
    ok = hull.find_simplex(np.c_[np.full_like(yy, x0), yy]) >= 0
    axs[3].plot(yy[ok], surf(np.full(ok.sum(), x0), yy[ok]), st, lw=1, label=f"x = {x0}")
    sec[f"x={x0}"] = dict(y=yy[ok].tolist(), z=np.round(surf(np.full(ok.sum(), x0), yy[ok]), 2).tolist())
axs[3].plot(yy, zr(yy), "k--", lw=0.6, label="rim (station max)"); axs[3].plot(F[:, 1], F[:, 2], "ks", ms=4, label="front-face dots")
axs[3].set_title("longitudinal sections (z exaggerated 3x)"); axs[3].set_aspect(3); axs[3].grid(alpha=0.3); axs[3].legend(fontsize=7)
plt.tight_layout(); plt.savefig(OUT / "figures/sections.png", dpi=100); plt.close()

# 3D view: shaded surface (mirrored), measured dots, front-face dots
from matplotlib.colors import LightSource
fig = plt.figure(figsize=(11, 8)); ax3 = fig.add_subplot(projection="3d")
Z = np.full(gx.shape, np.nan); Z.ravel()[np.flatnonzero(inside)] = gz
rgb = LightSource(azdeg=315, altdeg=40).shade(np.nan_to_num(Z, nan=np.nanmin(Z)), cmap=plt.cm.copper, vert_exag=2, blend_mode="soft")
ax3.plot_surface(gx, gy, Z, facecolors=rgb, rstride=1, cstride=1, linewidth=0, antialiased=True, shade=False)
ax3.scatter(T[:, 0], T[:, 1], T[:, 2] + 1.5, s=8, c="#1f5fbf", depthshade=False, label="blue-tape dots")
ax3.scatter(F[:, 0], F[:, 1], F[:, 2], s=14, c="k", marker="s", depthshade=False, label="front-face dots")
ax3.set_box_aspect((500, 480, 100 * 2)); ax3.view_init(elev=32, azim=-62)
ax3.set_xlabel("x mm"); ax3.set_ylabel("y mm (forward)"); ax3.set_zlabel("z mm (2x)"); ax3.legend(loc="upper left", fontsize=8)
ax3.set_title("Seat top surface from 103 tape dots (mirrored about x = 0), z exaggerated 2x")
plt.tight_layout(); plt.savefig(OUT / "figures/surface_3d.png", dpi=110); plt.close()

json.dump(dict(frame="chair frame mm (solve/metric_frame.json): +X chair's right, +Y forward, +Z up, table top Z=0",
               design_intent="symmetric about X=0: right-half dots mirrored",
               best=best, cv=cv,
               polynomial=dict(name=bestpoly, formula="z = sum_ij c[i*(dy+1)+j] * u^i * v^j,  u=(x/250)^2, v=(y-300)/250",
                               dx=dxp, dy=dyp, coef=pcoef.tolist()),
               loo_interior=loo_int,
               tps=dict(formula="z = sum_i w[i]*r_i^2*ln(r_i) + a[0] + a[1]*x + a[2]*y,  r_i = |(x,y) - centre_i| in mm",
                        smoothing=sm, centres=np.round(M[:, :2], 3).tolist(), w=tw.tolist(), a=ta.tolist(), check_vs_scipy_max_mm=tps_dev),
               outline_cloud=dict(note="approximate seat edge |x| per y from the chair cloud (98th pct of points near rim height)",
                                  y=OL[:, 0].tolist(), half_width=np.round(OL[:, 1], 1).tolist()),
               rim=dict(definition="z_rim(y) = max over x of the fitted surface at station y (dotted region)",
                        y=ry.tolist(), z=np.round(rz, 2).tolist(), at_abs_x=rxm.tolist(),
                        quadratic_approx=dict(formula="z = c0*y^2 + c1*y + c2", c=rc.tolist(),
                                              rms=float(np.sqrt((rim_res ** 2).mean())), max=float(np.abs(rim_res).max()))),
               deepest=dict(x=float(G[deep, 0]), y=float(G[deep, 1]), depth_mm=float(depth[deep])),
               measured_region=dict(x=[-float(T[:, 0].max()), float(T[:, 0].max())], y=[float(T[:, 1].min()), float(T[:, 1].max())]),
               asymmetry_cloud_minus_surface=asym, asymmetry_bands=bands, sections=sec,
               dots=dict(n=len(X), top=int(len(T)), front_face=int(len(F)), s_normal_median=float(np.median(SN)),
                         s_normal_p90=float(np.percentile(SN, 90)))), open(OUT / "surface.json", "w"), indent=1)
print("rim (station max) quadratic approx z = %.3g y2 + %.4f y + %.1f, deviation rms %.2f max %.2f (n=%d)" % (rc[0], rc[1], rc[2], np.sqrt((rim_res ** 2).mean()), np.abs(rim_res).max(), len(ry)))
print("deepest point x %.0f y %.0f depth %.1f mm" % (G[deep, 0], G[deep, 1], depth[deep]))
print("stations", ys)
