"""USAGE: work/toolkit/rk.sh tools/rocker_ends/fig_photos.py ORTHODIR [OUT figures/rocker_ends/photos.jpg]
The four rocker ends, each on ONE orthophoto of its own side face (grid in face-plane mm, ticks every 10 mm):
  white   - the model before (parts/rocker_profile.json alone: ends cut square at u -480 and 620)
  magenta - the model now (parts/rocker_ends.json "design": left and right averaged, so it is not exactly either rocker)
  cyan    - this rocker's own outline as traced in all its photos (parts/rocker_ends.json left / right)
All three are slid by this photo's own slide (its pose error at this end of the chair, parts/rocker_ends.json photos[..].slide_u_v_mm).
The two model outlines are also set on THIS rocker's top edge (minus its "set_on_existing_profile" slide, written in each panel): the model's
profile is the average of the two rockers and sits up to 2.4 mm off either one (the right one mostly); this figure is about the ends' shape."""
import sys, json, cv2, numpy as np
d = sys.argv[1]; out = sys.argv[2] if len(sys.argv) > 2 else "figures/rocker_ends/photos.jpg"; W = json.load(open(f"{d}/windows.json")); E = json.load(open("parts/rocker_ends.json")); RP = json.load(open("parts/rocker_profile.json"))
U = np.array(RP["u"]); RVL = RP["right_vs_left"]; D = E["design"]
def to_right(q):
    th = np.radians(RVL["rotation_deg"]); c, s = np.cos(th), np.sin(th); dd = np.asarray(q, float) - [RVL["shift_u_mm"], RVL["shift_v_mm"]]; return np.c_[c * dd[:, 0] + s * dd[:, 1], -s * dd[:, 0] + c * dd[:, 1]]
old = np.r_[np.c_[U, RP["mean_top"]], np.c_[U, RP["mean_bot"]][::-1], [[U[0], RP["mean_top"][0]]]]; mid = (U > D["tail"]["blend_u"][0]) & (U < D["nose"]["blend_u"][0])
new = np.r_[np.array(D["tail"]["top"])[::-1], np.c_[U, RP["mean_top"]][mid], np.array(D["nose"]["top"]), np.array(D["nose"]["bot"])[::-1][1:], np.c_[U, RP["mean_bot"]][mid][::-1], np.array(D["tail"]["bot"])]
PAN = [("L_tail", "1506", (-505, -385), 60, "left rocker, tail", 8.0), ("R_tail", "1471", (-505, -385), 60, "right rocker, tail", 8.0), ("L_nose", "1505", (552, 648), 76, "left rocker, nose", 10.0), ("R_nose", "1471", (552, 648), 76, "right rocker, nose", 10.0)]
def text(t, s, org, sc=0.55, col=(255, 255, 255)): cv2.putText(t, s, org, cv2.FONT_HERSHEY_SIMPLEX, sc, (0, 0, 0), 3, cv2.LINE_AA); cv2.putText(t, s, org, cv2.FONT_HERSHEY_SIMPLEX, sc, col, 1, cv2.LINE_AA)
tiles = []
for key, ph, (u0, u1), hv, title, K in PAN:
    S, end = key.split("_"); w = W[key]; res = w["res_mm"]; U0, V1 = w["u_range"][0], w["v_range"][1]; e = E["left" if S == "L" else "right"][end]; sl = np.array(e["photos"][ph]["slide_u_v_mm"]); P = np.array(e["outline_uv"]) + sl; reg = np.array(e["set_on_existing_profile"]["slide_u_v_mm"])
    m = (P[:, 0] > u0) & (P[:, 0] < u1); vc = (P[m, 1].min() + P[m, 1].max()) / 2; v0, v1 = vc - hv / 2, vc + hv / 2; im = cv2.imread(f"{d}/{key}_{ph}.png")
    c0, c1, r0, r1 = int((u0 - U0) / res), int((u1 - U0) / res), int((V1 - v1) / res), int((V1 - v0) / res); t = cv2.resize(im[r0:r1, c0:c1], None, fx=K * res, fy=K * res, interpolation=cv2.INTER_CUBIC)
    px = lambda Q: np.int32(np.round(np.c_[(Q[:, 0] - u0) * K, (v1 - Q[:, 1]) * K] * 8))
    for poly, col, th in ((old, (255, 255, 255), 2), (new, (255, 0, 255), 2)):
        Q = (poly - reg if S == "L" else to_right(poly - reg)) + sl; cv2.polylines(t, [px(Q)], False, (0, 0, 0), th + 2, cv2.LINE_AA, 3); cv2.polylines(t, [px(Q)], False, col, th, cv2.LINE_AA, 3)
    cv2.polylines(t, [px(P)], False, (255, 255, 0), 1, cv2.LINE_AA, 3)
    for g in np.arange(np.ceil(u0 / 10) * 10, u1, 10): x = int((g - u0) * K); cv2.line(t, (x, 0), (x, 8), (255, 255, 255), 1); text(t, str(int(g)), (x + 3, 20), 0.45)
    for g in np.arange(np.ceil((v0 + 82 / K) / 10) * 10, v1, 10): y = int((v1 - g) * K); cv2.line(t, (0, y), (8, y), (255, 255, 255), 1); text(t, str(int(g)), (11, y + 5), 0.45)
    text(t, f"{title}, IMG_{ph}", (12, t.shape[0] - 62), 0.6)
    for i, (s_, col) in enumerate((("white: model before", (255, 255, 255)), ("magenta: model now (left and right averaged); both models moved %+.1f, %+.1f mm onto this rocker" % tuple(-reg), (255, 0, 255)), ("cyan: this rocker as traced in all its photos", (255, 255, 0)))): text(t, s_, (12, t.shape[0] - 42 + 17 * i), 0.5, col)
    tiles.append(t)
wd = max(t.shape[1] for t in tiles); pad = lambda t: cv2.copyMakeBorder(t, 0, 6, 0, wd - t.shape[1] + 6, cv2.BORDER_CONSTANT, value=(251, 252, 252))
cv2.imwrite(out, np.vstack([np.hstack([pad(tiles[0]), pad(tiles[1])]), np.hstack([pad(tiles[2]), pad(tiles[3])])]), [cv2.IMWRITE_JPEG_QUALITY, 90]); print("wrote", out)
