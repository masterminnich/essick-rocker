"""USAGE: work/toolkit/rk.sh tools/rocker_ends/zoom.py ORTHODIR SIDE END PHOTO U0 U1 V0 V1 OUT [PX_PER_MM 14] [TRACE.json] [MIN_STRENGTH 1.5]
One orthophoto of a rocker end (tools/rocker_ends/ortho.py) enlarged with a 5 mm grid (labels every 10), for seeding an edge by eye and
for checking a trace on a SINGLE photo. With TRACE.json (tools/rocker_ends/trace.py) the seed (yellow) and that photo's snapped points
are drawn (red: strong; grey: weaker than MIN_STRENGTH, default 1.5 per mm, or stuck at the edge of the search band); a "design" entry is drawn white."""
import sys, json, cv2, numpy as np
d, S, end, ph = sys.argv[1:5]; u0, u1, v0, v1 = map(float, sys.argv[5:9]); out = sys.argv[9]; k = float(sys.argv[10]) if len(sys.argv) > 10 else 14.0
W = json.load(open(f"{d}/windows.json"))[f"{S}_{end}"]; res = W["res_mm"]; U0, V1 = W["u_range"][0], W["v_range"][1]
im = cv2.imread(f"{d}/{S}_{end}_{ph}.png"); c0, c1, r0, r1 = int((u0 - U0) / res), int((u1 - U0) / res), int((V1 - v1) / res), int((V1 - v0) / res)
t = cv2.resize(im[r0:r1, c0:c1], None, fx=k * res, fy=k * res, interpolation=cv2.INTER_CUBIC); px = lambda p: (int(round((p[0] - u0) * k)), int(round((v1 - p[1]) * k)))
for g in np.arange(np.ceil(u0 / 5) * 5, u1, 5):
    x = int((g - u0) * k); cv2.line(t, (x, 0), (x, t.shape[0]), (255, 255, 0) if g % 10 == 0 else (150, 150, 0), 1)
    if g % 10 == 0: cv2.putText(t, str(int(g)), (x + 2, 12), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (255, 255, 0), 1)
for g in np.arange(np.ceil(v0 / 5) * 5, v1, 5):
    y = int((v1 - g) * k); cv2.line(t, (0, y), (t.shape[1], y), (255, 255, 0) if g % 10 == 0 else (150, 150, 0), 1)
    if g % 10 == 0: cv2.putText(t, str(int(g)), (2, y - 2), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (255, 255, 0), 1)
if len(sys.argv) > 11:
    T = json.load(open(sys.argv[11]))[f"{S}_{end}"]
    for name in ("top", "bot"):
        if name in T.get("seed", {}): cv2.polylines(t, [np.array([px(p) for p in T["seed"][name]], np.int32)], False, (0, 255, 255), 1, cv2.LINE_AA)
        if name in T.get("design", {}): cv2.polylines(t, [np.array([px(p) for p in T["design"][name]], np.int32)], False, (255, 255, 255), 1, cv2.LINE_AA)
    sn = T.get("snapped", {}).get(ph)
    if sn:
        Q = np.array(T["outline"]) + np.array(sn["off"])[:, None] * np.array(T["normal"]); MIN = float(sys.argv[12]) if len(sys.argv) > 12 else 1.5
        for q, g, e in zip(Q[::2], sn["strength"][::2], sn["at_band_edge"][::2]): cv2.circle(t, px(q), 2, (0, 0, 255) if g >= MIN and not e else (160, 160, 160), -1, cv2.LINE_AA)
cv2.putText(t, f"{S} {end} IMG_{ph}", (8, t.shape[0] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 3); cv2.putText(t, f"{S} {end} IMG_{ph}", (8, t.shape[0] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 1)
cv2.imwrite(out, t, [cv2.IMWRITE_JPEG_QUALITY, 90]); print(out, t.shape)
