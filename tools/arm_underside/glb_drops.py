"""USAGE: tools/safe_run.sh -- uv run -q --no-project --with numpy --with scipy --with trimesh --with rtree python -I tools/arm_underside/glb_drops.py OLD.glb NEW.glb OUT.json
Reads the arm's thickness back off BUILT models (the joined chair glb): at each station y, a vertical ray just inside the outer face
(0.7 mm in from parts/arms.json design outer line) and just inside the inner face gives the top and the underside of ARM_R / ARM_L.
Writes the drops (top minus underside, vertical) per side for both models, plus the difference to parts/arm_underside.json design, so
tools/arm_underside/fig_overlay.py (env DROPS=OUT.json) can draw what the MODEL is, not what the design file says."""
import sys, json, numpy as np, trimesh
old, new, out = sys.argv[1:4]
D = json.load(open("parts/arms.json"))["design"]; U = json.load(open("parts/arm_underside.json"))["design"]
pin, pout = np.array(D["inner_x_of_y"]["poly_in_(y-300)"]), np.array(D["outer_x_of_y"]["poly_in_(y-300)"])
ys = np.arange(45.0, 501.0, 5.0); R = {"y": ys.tolist()}
for tag, path in (("old", old), ("new", new)):
    G = trimesh.load(path).geometry
    for S, sg in (("R", 1.0), ("L", -1.0)):
        m = G[f"ARM_{S}"]
        def tb(x):   # top and underside z along vertical rays at (x, ys)
            T, B_ = [], []
            for xi, yi in zip(x, ys):
                loc, _, _ = m.ray.intersects_location([[xi, yi, 0.0]], [[0, 0, 1.0]]); ok = len(loc) >= 2
                T.append(float(loc[:, 2].max()) if ok else np.nan); B_.append(float(loc[:, 2].min()) if ok else np.nan)
            return np.array(T), np.array(B_)
        to, bo = tb(sg * (np.polyval(pout, ys - 300) - 0.7)); _, bi = tb(sg * (np.polyval(pin, ys - 300) + 0.7))
        R.setdefault(S, {})[f"{tag}_outer"] = np.round(to - bo, 2).tolist(); R[S][f"{tag}_inner"] = np.round(to - bi, 2).tolist()   # both drops below the OUTER top arris, as in parts/arm_underside.json
for S in ("R", "L"):
    for face in ("outer", "inner"):
        d = np.array(R[S][f"new_{face}"]) - np.interp(ys, U["y"], U[f"h_{face}_mm"]); ok = ~np.isnan(d)
        R[S][f"new_minus_design_{face}"] = {"max_abs_mm": round(float(np.abs(d[ok]).max()), 2), "mean_mm": round(float(d[ok].mean()), 2), "n": int(ok.sum()),
                                            "worst_y": float(ys[ok][np.argmax(np.abs(d[ok]))]), "nan_y": ys[~ok].tolist(),
                                            "per_y_first": {str(int(y)): round(float(v), 2) for y, v in zip(ys[:6], d[:6])}}
        print(S, face, R[S][f"new_minus_design_{face}"], "new at y 60/200/300/400/480:", [R[S][f"new_{face}"][int((y - 45) / 5)] for y in (60, 200, 300, 400, 480)],
              "old:", [R[S][f"old_{face}"][int((y - 45) / 5)] for y in (60, 200, 300, 400, 480)])
json.dump(R, open(out, "w"), indent=0)
