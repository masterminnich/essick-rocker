"""USAGE: work/toolkit/rk.sh tools/seat_back/solve.py [EDGES tools/seat_back/inputs/edges.json] [TRACES_PREFIX tools/seat_back/inputs/traces] [OUT work/seat_back/solved.json]
Step 3 of 4 (sheet -> trace -> solve -> fit) for the seat's BACK EDGE. Each of the three edges (top arris, hard line, bottom arris) is
triangulated as ONE smooth 3D curve across the chair, X(x) = (x, y(x), z(x)), from all its per-photo traces at once with
tools/curve_tri.py (Legendre polynomials; residual = distance on the rear sheet between the curve seen through that photo's camera
and the photo's trace; soft-L1, 1 mm). Three solves per edge:
  free   left and right independent (degree 6 for the top arris, 4 for the other two)
  even   y and z even in x: the symmetric design version
  leave-one-photo-out of the even solve: how far the curve moves when any one photo is dropped (the honest error figure)
Writes OUT: per edge the free and even curves every mm, each photo's rms, 1-sigma from the fit, the leave-one-out moves.
Tiny compute (a few thousand points, about 40 small least-squares fits)."""
import sys, json, subprocess, os, numpy as np
ef = sys.argv[1] if len(sys.argv) > 1 else "tools/seat_back/inputs/edges.json"; tp = sys.argv[2] if len(sys.argv) > 2 else "tools/seat_back/inputs/traces"
outf = sys.argv[3] if len(sys.argv) > 3 else "work/seat_back/solved.json"; E = json.load(open(ef)); pre = E["sheet"]["prefix"]; tmp = outf + ".tmp"; DEG = {"top": 6, "hard": 4, "bottom": 4}
def run(edge, photos, even, deg):
    g = tmp + ".g.json"; json.dump({edge + "_xyz": E["edges"][edge]["xyz"]}, open(g, "w")); x0, x1 = E["edges"][edge]["x_solve"]
    cmd = [sys.executable, "-I", "tools/curve_tri.py"] + sum([["--trace", f"{pre}:{p}:{tp}_{edge}.json:{edge}"] for p in photos], []) + ["--x", str(x0), str(x1), "--guess-json", f"{g}:{edge}", "--deg", str(deg), "--name", edge, "--out", tmp] + (["--even"] if even else [])
    r = subprocess.run(cmd, capture_output=True, text=True); assert r.returncode == 0, r.stderr[-600:]
    R = json.load(open(tmp)); os.remove(tmp); os.remove(g); return np.array(R[edge + "_xyz"]), R[edge + "_info"]
out = {"edges_file": ef, "traces": tp}
for edge, Ed in E["edges"].items():
    photos = list(Ed["photos"]); deg = DEG[edge]; Xf, If = run(edge, photos, False, deg); Xe, Ie = run(edge, photos, True, deg)
    inner = np.abs(Xe[:, 0]) <= np.abs(Xe[:, 0]).max() - 40; loo = {}
    for p in photos:
        Xl, _ = run(edge, [q for q in photos if q != p], True, deg); d = Xl - Xe
        loo[p] = {"y_inner": round(float(np.abs(d[inner, 1]).max()), 2), "y_whole": round(float(np.abs(d[:, 1]).max()), 2), "z_inner": round(float(np.abs(d[inner, 2]).max()), 2), "z_whole": round(float(np.abs(d[:, 2]).max()), 2)}
    T = json.load(open(f"{tp}_{edge}.json")); band = E["band_mm"]
    out[edge] = {"degree": deg, "x_range": Ed["x_solve"], "free_xyz": Xf.round(3).tolist(), "even_xyz": Xe.round(3).tolist(),
                 "photos": {p["photo"]: {"rms_even_mm": round(p["rms_mm"], 2), "rms_free_mm": round(q["rms_mm"], 2), "points": p["n"], "trace_moved_from_seed_mm_median": round(float(np.median(T[f"{edge}@{p['photo']}_moved_mm"])), 2),
                                         "trace_at_band_limit_share": round(float(np.mean(np.abs(np.array(T[f"{edge}@{p['photo']}_moved_mm"])) > band - 0.25)), 3), "x_ranges": Ed["photos"][p["photo"]]} for p, q in zip(Ie["photos"], If["photos"])},
                 "sigma_fit_mm": {"even": {c: Ie.get(f"sigma_{c}_mm") for c in "yz"}, "free": {c: If.get(f"sigma_{c}_mm") for c in "yz"}}, "leave_one_photo_out_mm": loo,
                 "left_minus_mirrored_right_mm": {c: {"rms": round(float(np.sqrt(np.mean((Xf[:, i] - Xf[::-1, i]) ** 2))), 2), "max": round(float(np.abs(Xf[:, i] - Xf[::-1, i]).max()), 2)} for c, i in (("y", 1), ("z", 2))}}
    o = out[edge]; print(f"{edge}: {len(photos)} photos; rms on the sheet {min(v['rms_even_mm'] for v in o['photos'].values()):.2f}-{max(v['rms_even_mm'] for v in o['photos'].values()):.2f} mm (even), "
                         f"{min(v['rms_free_mm'] for v in o['photos'].values()):.2f}-{max(v['rms_free_mm'] for v in o['photos'].values()):.2f} (free); centre y {Xe[len(Xe)//2, 1]:.1f} z {Xe[len(Xe)//2, 2]:.1f}; ends y {Xe[0, 1]:.1f} z {Xe[0, 2]:.1f}")
    print("   leave one photo out, worst: y inner %.2f whole %.2f, z inner %.2f whole %.2f mm" % tuple(max(v[k] for v in loo.values()) for k in ("y_inner", "y_whole", "z_inner", "z_whole")), "| worst photo for y:", max(loo, key=lambda p: loo[p]["y_whole"]))
    print("   left - mirrored right:", o["left_minus_mirrored_right_mm"], "| at the band limit:", {p: v["trace_at_band_limit_share"] for p, v in o["photos"].items() if v["trace_at_band_limit_share"] > 0.02})
json.dump(out, open(outf, "w")); print("wrote", outf)
