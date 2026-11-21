"""USAGE: tools/py.sh tools/seat_back/cloud_check.py MODEL_shapes.glb [MODEL_shapes.glb ...]
Check of the seat's TOP surface in the strip between the back edge and the dotted region (y < 64, no tape dots there): the sparse cloud's points on the seat top in that
strip (work/dense/chair_dense.npy, both halves; points more than 6 mm above the new surface are the slats' feet and are left out for every model alike)
against each model's seat top, z of the point minus z of the model under it. Tiny compute."""
import sys, json, numpy as np, trimesh
def ztop(S, x, y):
    T = S.triangles; a, b, c = T[:, 0], T[:, 1], T[:, 2]; d = (b[:, 1] - c[:, 1]) * (a[:, 0] - c[:, 0]) + (c[:, 0] - b[:, 0]) * (a[:, 1] - c[:, 1]); d = np.where(np.abs(d) < 1e-9, np.nan, d)
    l1 = ((b[:, 1] - c[:, 1]) * (x - c[:, 0]) + (c[:, 0] - b[:, 0]) * (y - c[:, 1])) / d; l2 = ((c[:, 1] - a[:, 1]) * (x - c[:, 0]) + (a[:, 0] - c[:, 0]) * (y - c[:, 1])) / d
    l3 = 1 - l1 - l2; k = (l1 >= -1e-9) & (l2 >= -1e-9) & (l3 >= -1e-9); z = l1[k] * a[k, 2] + l2[k] * b[k, 2] + l3[k] * c[k, 2]; return z.max() if k.any() else np.nan
C = np.load("work/dense/chair_dense.npy")[:, :3]; B = json.load(open("parts/seat_back.json"))["design"]; bx = np.array(B["abs_x"]); yT = np.interp(np.abs(C[:, 0]), bx, B["top_arris"]["y"]); zT = np.interp(np.abs(C[:, 0]), bx, B["top_arris"]["z"])
k = (np.abs(C[:, 0]) < 180) & (C[:, 1] > yT + 3) & (C[:, 1] < 63.6) & (C[:, 2] > zT - 4) & (C[:, 2] < zT + 0.19 * (C[:, 1] - yT) + 6); P = C[k]; print("cloud points on the seat top in the strip:", len(P))
for nm in sys.argv[1:]:
    S = trimesh.load(nm).geometry["SEAT"]; d = np.array([p[2] - ztop(S, p[0], p[1]) for p in P]); ok = np.isfinite(d); d_, P_ = d[ok], P[ok]
    print(nm, "n %d: cloud - model median %+.2f mm, rms %.2f, 10-90%% %+.1f..%+.1f" % (ok.sum(), np.median(d_), np.sqrt(np.mean(d_ ** 2)), *np.percentile(d_, [10, 90])))
    for a, b in ((0, 60), (60, 120), (120, 180)):
        m = (np.abs(P_[:, 0]) >= a) & (np.abs(P_[:, 0]) < b); print("    |x| %3d-%3d n %3d median %+.2f rms %.2f" % (a, b, m.sum(), np.median(d_[m]), np.sqrt(np.mean(d_[m] ** 2))) if m.any() else "")
