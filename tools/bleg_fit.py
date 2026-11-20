"""USAGE: python -I tools/bleg_fit.py --dir work/parts/back/t --sheet work/parts/back/t/b3_plane.json --out parts/back_legs.json
Fair edges of the two back legs seen from behind, from the triangulated arris traces written by tools/edge_tri.py
(DIR/blegR_in.json, blegR_out.json, blegL_in.json, blegL_out.json; sheet coordinates u = across the chair, v = length up
the leg's back arris, mm). Each edge: robust 4th-order u(v) checked against the raw trace. Reports width across, the
left/right mirror agreement (after removing a constant sideways offset of the pair) and the design-intent (averaged) edges.
Tiny compute."""
import json, argparse, numpy as np
ap = argparse.ArgumentParser(); ap.add_argument("--dir", required=True); ap.add_argument("--sheet", required=True); ap.add_argument("--out", required=True)
ap.add_argument("--inner-forward", type=float, default=0.0, help="how far the inner back arris sits forward of the outer one (the --depth-fixed used for the inner edges, sign flipped)"); a = ap.parse_args()
F = {}; info = {}; raw = {}
for k in ("blegR_in", "blegR_out", "blegL_in", "blegL_out"):
    j = json.load(open(f"{a.dir}/{k}.json")); e = np.array(j[k]); keep = np.ones(len(e), bool); raw[k] = e; info[k] = j[k + "_info"]
    for _ in range(8): c = np.polyfit(e[keep, 1], e[keep, 0], 4); keep = np.abs(e[:, 0] - np.polyval(c, e[:, 1])) < 2.0
    chk = max(abs(np.median(e[np.abs(e[:, 1] - v0) < 25, 0]) - np.polyval(c, v0)) for v0 in np.arange(125, 720, 50))
    F[k] = {"coef": c.tolist(), "scatter_mm": float(np.std(e[keep, 0] - np.polyval(c, e[keep, 1]))), "clean": float(keep.mean()), "max_dev_from_raw_mm": float(chk),
            "photos": info[k]["photos"], "triangulated": info[k]["triangulated"], "view_residual_rms_mm": info[k]["residual_rms_mm"], "arris_off_sheet_mm": info[k]["depth_mm"]}
    print(f"{k:10s} scatter {F[k]['scatter_mm']:.2f} mm, clean stations {keep.mean():.0%}, worst gap fair curve vs raw trace {chk:.2f} mm, photos {','.join(info[k]['photos'])}")
V = np.array([110, 250, 400, 550, 725.0]); ev = lambda k: np.polyval(F[k]["coef"], V)
wr = ev("blegR_out") - ev("blegR_in"); wl = ev("blegL_in") - ev("blegL_out")
print("v up the leg (mm):         ", V.astype(int).tolist())
print("right leg width across:    ", wr.round(1).tolist()); print("left leg width across:     ", wl.round(1).tolist())
print("inner edge R / L mirrored: ", ev("blegR_in").round(1).tolist(), (-ev("blegL_in")).round(1).tolist())
print("outer edge R / L mirrored: ", ev("blegR_out").round(1).tolist(), (-ev("blegL_out")).round(1).tolist())
d = np.r_[ev("blegR_in") + ev("blegL_in"), ev("blegR_out") + ev("blegL_out")]; u0 = float(np.median(d) / 2); d2 = d - 2 * u0
print(f"left/right mirror disagreement: rms {np.sqrt(np.mean(d ** 2)):.2f} mm, max {np.abs(d).max():.2f}; the pair sits {u0:+.2f} mm to the chair's right of the centre plane; "
      f"with that removed rms {np.sqrt(np.mean(d2 ** 2)):.2f}, max {np.abs(d2).max():.2f} mm")
sym = {"inner": ((np.array(F["blegR_in"]["coef"]) - np.array(F["blegL_in"]["coef"])) / 2).tolist(), "outer": ((np.array(F["blegR_out"]["coef"]) - np.array(F["blegL_out"]["coef"])) / 2).tolist()}
ws = np.polyval(sym["outer"], V) - np.polyval(sym["inner"], V)
print("design-intent width across:", ws.round(1).tolist(), "| in", (ws / 25.4).round(2).tolist(), "| outside-to-outside:", (2 * np.polyval(sym["outer"], V)).round(1).tolist())
json.dump({"fits": F, "symmetric": sym, "v_range": [100, 735], "sheet": json.load(open(a.sheet)), "pair_offset_u_mm": u0, "inner_arris_forward_mm": a.inner_forward, "mirror_rms_after_offset_mm": float(np.sqrt(np.mean(d2 ** 2))),
           "widths_mm": {"v": V.tolist(), "right": wr.tolist(), "left": wl.tolist(), "design": ws.tolist()},
           "method": "edge triangulation on the unrolled back view (tools/edge_tri.py): outer edges solved for position and depth from 3 clean photos; inner edges from the 2 clean photos with the inner arris taken inner_arris_forward_mm forward of the outer one (leg faces toed out with the side frame, about 8.5 deg)"}, open(a.out, "w"), indent=1)
