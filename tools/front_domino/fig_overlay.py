"""Zoomed overlays on single photos (straightened leg-face orthophotos, 12 px/mm): measured arrises (white), measured Domino centre
(white cross), model Domino outline v18 (orange) and after the fix (blue). USAGE: rk.sh work/fdom/fig_overlay.py OUT.jpg L:1508 R:1488 ..."""
import sys, json, cv2, numpy as np; sys.path.insert(0, "work/fdom")
from shear import straight, K, VD
SC = 12; S0, S1, V0, V1 = -32, 24, -6, 44
OR, BL, WH = (52, 104, 235), (214, 120, 42), (255, 255, 255)        # BGR of #eb6834, #2a78d6
B = json.load(open("work/fdom/dcheck_model_v18.json")); A = json.load(open("work/fdom/dcheck_trial.json")); P = json.load(open("work/fdom/raw/planes.json"))
AN = json.load(open("work/fdom/analysis.json"))
def px(s, v): return int(round((s - S0) * SC)), int(round((V1 - v) * SC))
def stadium(cu, cv, a=24.0, b=10.0, tilt=15.0, n=40):
    r = b / 2; h = a / 2 - r; t = np.linspace(-np.pi / 2, np.pi / 2, n)
    Q = np.r_[np.c_[h + r * np.cos(t), r * np.sin(t)], np.c_[-h - r * np.cos(t), -r * np.sin(t)]]; c, s_ = np.cos(np.radians(tilt)), np.sin(np.radians(tilt))
    Q = Q @ np.array([[c, s_], [-s_, c]]) + [cu, cv]; return np.c_[Q[:, 0] + K * (Q[:, 1] - VD), Q[:, 1]]
tiles = []
for spec in sys.argv[2:]:
    leg, ph = spec.split(":"); L = f"FLEG_{leg}"
    for k, x in (("origin", B[leg]["plane"]["origin"]), ("u", B[leg]["plane"]["u"])):
        assert np.abs(np.array(P[L][k]) - x).max() < 0.1, (L, k, P[L][k], x)
    im, ss, vs = straight(L, ph, (S0, S1), (V0, V1), 1 / SC)
    lab = cv2.cvtColor(im, cv2.COLOR_BGR2Lab); lab[:, :, 0] = cv2.createCLAHE(2.0, (4, 4)).apply(lab[:, :, 0]); im = cv2.cvtColor(lab, cv2.COLOR_Lab2BGR)
    row = next(r for r in AN[leg]["rows"] if r["photo"] == ph); D = json.load(open(f"work/fdom/dom_{leg}.json"))[ph]
    for g in range(-30, 25, 10):                                              # light 10 mm grid
        x, _ = px(g, 0); cv2.line(im, (x, im.shape[0] - 14), (x, im.shape[0]), WH, 1); cv2.putText(im, str(g), (x + 2, im.shape[0] - 3), 0, 0.38, WH, 1, cv2.LINE_AA)
    for s in (row["rear"], row["front"]):                                     # measured arrises, dashed
        x, _ = px(s, 0)
        for y in range(0, im.shape[0] - 20, 14): cv2.line(im, (x, y), (x, y + 8), WH, 2, cv2.LINE_AA)
    mid = (row["rear"] + row["front"]) / 2; x, y = px(mid, -4); cv2.line(im, (x, y - 10), (x, y + 10), WH, 2)
    for M, col in ((B, OR), (A, BL)):
        Q = stadium(M[leg]["json_centre_u"], M[leg]["end_v"]); pts = np.array([px(*q) for q in Q], np.int32)
        cv2.polylines(im, [pts], True, (0, 0, 0), 4, cv2.LINE_AA); cv2.polylines(im, [pts], True, col, 2, cv2.LINE_AA)
        x, y = px(M[leg]["json_centre_u"], M[leg]["end_v"]); cv2.circle(im, (x, y), 4, col, -1, cv2.LINE_AA)
    x, y = px(D["centre_s"], D["centre_v"]); cv2.line(im, (x - 9, y), (x + 9, y), WH, 2); cv2.line(im, (x, y - 9), (x, y + 9), WH, 2)
    side = "left" if leg == "L" else "right"
    hdr = np.full((58, im.shape[1], 3), 252, np.uint8)
    cv2.putText(hdr, f"IMG_{ph}  {side} front leg  (camera {abs(row['az']):.0f} deg {'in front' if row['az'] > 0 else 'behind'})", (6, 20), 0, 0.55, (11, 11, 11), 1, cv2.LINE_AA)
    cv2.putText(hdr, f"photo: Domino {row['offset']:+.2f} mm from the arris middle   model: v18 {B[leg]['offset']:+.2f}  ->  new {A[leg]['offset']:+.2f}", (6, 44), 0, 0.5, (78, 81, 82), 1, cv2.LINE_AA)
    tiles.append(np.vstack([hdr, im]))
key = np.full((34, tiles[0].shape[1] * 2, 3), 252, np.uint8)
items = [("white dashed: measured leg arrises; white tick: their middle; white cross: measured Domino centre", WH, 6)]
cv2.putText(key, "white dashed = measured arrises, tick = their middle, cross = measured Domino centre;", (6, 14), 0, 0.45, (11, 11, 11), 1, cv2.LINE_AA)
cv2.putText(key, "orange = model v18 Domino end, blue = after this fix. + = toward the front of the leg; the leg's front is on the right", (6, 29), 0, 0.45, (11, 11, 11), 1, cv2.LINE_AA)
rows = [np.hstack(tiles[i:i + 2]) for i in range(0, len(tiles), 2)]
sep = np.full((6, rows[0].shape[1], 3), 252, np.uint8)
out = [key]; [out.extend([r, sep]) for r in rows]
cv2.imwrite(sys.argv[1], np.vstack(out[:-1]), [cv2.IMWRITE_JPEG_QUALITY, 90]); print("wrote", sys.argv[1], np.vstack(out[:-1]).shape)
