"""USAGE: work/toolkit/rk.sh tools/lr_skew.py [--out parts/lr_skew.json]
Left/right skew of the chair as built: right minus mirrored left HEIGHT of the rocker, the seat's side edge and the arm top, as a
function of y, from the parts files (parts/rocker_profile.json, parts/seat_edge.json, parts/arms.json; read only).
Answers: is the 2-5 mm left/right difference of seat and arms a roll of the frame, or the chair? Tiny compute."""
import json, argparse
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parent.parent
ap = argparse.ArgumentParser(); ap.add_argument("--out", default=str(ROOT / "parts/lr_skew.json")); a = ap.parse_args()
E = json.load(open(ROOT / "parts/seat_edge.json")); A = json.load(open(ROOT / "parts/arms.json")); R = json.load(open(ROOT / "parts/rocker_profile.json"))
# rockers: undo the rigid alignment to get the raw right profile back (rocker_profile.py: ua = c u - s v + du, va = s u + c v + dv); sheet u = y / 0.99
U = np.array(R["u"]); p = R["right_vs_left"]; th = np.radians(p["rotation_deg"]); c, s = np.cos(th), np.sin(th)
def raw_right(k):
    x, y = U - p["shift_u_mm"], np.array(R["right_aligned_to_left"][k]) - p["shift_v_mm"]; return c * x + s * y, -s * x + c * y
rk = {}
for k in ("top", "bot"):
    ur, vr = raw_right(k); vl = np.array(R["left"][k]); rk[k] = (U * 0.99, np.interp(U, ur, vr) - vl, float(vl.min()), float(vr.min()), float(U[np.argmin(vl)] * 0.99), float(ur[np.argmin(vr)] * 0.99))
ys = np.arange(110, 401, 10.0)
def seat(side, key, col):
    P = np.array(E[side][key]); P = P[np.argsort(P[:, 1])]; return np.interp(ys, P[:, 1], P[:, col])
st = A["left_vs_right"]["stations"]; ya = np.array([q["y"] for q in st]); m = (ya >= 110) & (ya <= 400)
rows = {"rocker top (y 0-400)": (rk["top"][0][(rk["top"][0] >= 0) & (rk["top"][0] <= 400)], rk["top"][1][(rk["top"][0] >= 0) & (rk["top"][0] <= 400)]),
        "seat top arris (plan sheet)": (ys, seat("right", "top_arris_plan_xyz", 2) - seat("left", "top_arris_plan_xyz", 2)),
        "seat top arris (side sheet)": (ys, seat("right", "top_arris_side_xyz", 2) - seat("left", "top_arris_side_xyz", 2)),
        "seat bottom arris": (ys, seat("right", "bottom_arris_xyz", 2) - seat("left", "bottom_arris_xyz", 2)),
        "arm top (y 110-400)": (ya[m], np.array([q["d_z_mm"] for q in st])[m])}
out = {"note": "right minus mirrored left height (mm) fitted as a line in y; pitch = slope as an angle (negative = the right side is nose-down against the left); "
               "minus_rocker = the same difference after taking off the rocker's own left/right difference at that y",
       "rockers_lowest_point_above_table_mm": {"left": round(rk["bot"][2], 2), "right": round(rk["bot"][3], 2), "at_y": [round(rk["bot"][4]), round(rk["bot"][5])]},
       "rocker_right_minus_left_top_mm_at_y": {str(int(y0)): round(float(np.interp(y0, rk["top"][0], rk["top"][1])), 1) for y0 in (-400, -300, -200, -100, 0, 100, 200, 300, 400, 500)}, "lines": {}}
rock = lambda y: np.interp(y, rk["top"][0], rk["top"][1])
print(f"rockers: lowest point of the bottom edge left {rk['bot'][2]:.1f} mm at y {rk['bot'][4]:.0f}, right {rk['bot'][3]:.1f} mm at y {rk['bot'][5]:.0f} (both on the table: no roll of the frame)")
print("rocker right - left (top edge) at y:", out["rocker_right_minus_left_top_mm_at_y"])
print(f"{'right minus mirrored left height':32s} {'y110':>6s} {'y250':>6s} {'y400':>6s} {'pitch':>7s} {'scatter':>8s} | minus rocker: y110 y250 y400")
for name, (y, d) in rows.items():
    cf = np.polyfit(y, d, 1); sc = float((d - np.polyval(cf, y)).std()); v = [float(np.polyval(cf, q)) for q in (110, 250, 400)]; mr = [v[i] - float(rock(q)) for i, q in enumerate((110, 250, 400))]
    out["lines"][name] = {"at_y110": round(v[0], 1), "at_y250": round(v[1], 1), "at_y400": round(v[2], 1), "pitch_deg": round(float(np.degrees(np.arctan(cf[0]))), 2), "scatter_mm": round(sc, 2),
                          "minus_rocker_at_y110_y250_y400": [round(q, 1) for q in mr]}
    print(f"{name:32s} {v[0]:+6.1f} {v[1]:+6.1f} {v[2]:+6.1f} {np.degrees(np.arctan(cf[0])):+7.2f} {sc:8.2f} |          {mr[0]:+5.1f} {mr[1]:+5.1f} {mr[2]:+5.1f}")
json.dump(out, open(a.out, "w"), indent=1)
