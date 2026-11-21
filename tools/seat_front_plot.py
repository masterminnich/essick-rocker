"""USAGE: python -I tools/seat_front_plot.py [--out figures/seat_front/plan.jpg] [--scale 4]
Plan drawing of the seat's front edge from parts/seat_front.json: right and left solves (each also mirrored onto the other side,
thin), the symmetric design outline, the old straight front line, and the seat session's tape dots (seat/dots.csv,
seat/front_face.csv) that were not used in the solve. True scale, 10 mm grid. Tiny compute."""
import json, argparse, csv
from pathlib import Path
import numpy as np, cv2
ROOT = Path(__file__).resolve().parent.parent
ap = argparse.ArgumentParser(); ap.add_argument("--out", default=str(ROOT / "figures/seat_front/plan.jpg")); ap.add_argument("--scale", type=float, default=4.0); a = ap.parse_args()
d = json.load(open(ROOT / "parts/seat_front.json")); S = a.scale; X0, X1, Y0, Y1 = -290, 290, 470, 560; top = 120
W, H = int((X1 - X0) * S), int((Y1 - Y0) * S) + top; im = np.full((H, W, 3), 255, np.uint8)
px = lambda x, y: (int(round((x - X0) * S)), int(round((Y1 - y) * S)) + top)        # forward (+y) is up
F = cv2.FONT_HERSHEY_SIMPLEX
for x in range(X0, X1 + 1, 10):
    cv2.line(im, px(x, Y0), px(x, Y1), (225, 225, 225) if x % 50 else (170, 170, 170), 1)
    if x % 50 == 0: cv2.putText(im, str(x), (px(x, Y0)[0] + 4, H - 8), F, 0.6, (90, 90, 90), 2)
for y in range(Y0, Y1 + 1, 10):
    cv2.line(im, px(X0, y), px(X1, y), (225, 225, 225) if y % 50 else (170, 170, 170), 1); y < Y1 and cv2.putText(im, str(y), (4, px(0, y)[1] - 4), F, 0.6, (90, 90, 90), 2)
poly = lambda P, col, th: cv2.polylines(im, [np.array([px(x, y) for x, y in P], np.int32)], False, col, th, cv2.LINE_AA)
R = np.array(d["right"]["outline_xy"]); L = np.array(d["left"]["outline_abs_x_y"]); D = np.array(d["design"]["front_y_of_abs_x"])
old = 513.6                                                                              # model v9: straight front line
for x in range(-268, 268, 16): cv2.line(im, px(x, old), px(x + 8, old), (120, 120, 120), 2, cv2.LINE_AA)
poly(np.r_[np.c_[-D[::-1, 0], D[::-1, 1]], D], (0, 0, 0), 5)
RED, BLUE, GREEN = (40, 40, 230), (220, 120, 0), (0, 150, 0)
poly(R, RED, 2); poly(np.c_[-R[:, 0], R[:, 1]], RED, 1); poly(np.c_[-L[:, 0], L[:, 1]], BLUE, 2); poly(L, BLUE, 1)
dots = {int(r["id"]): (float(r["x_mm"]), float(r["y_mm"])) for r in csv.DictReader(open(ROOT / "seat/dots.csv"))}
face = [int(r["id"]) for r in csv.DictReader(open(ROOT / "seat/front_face.csv"))]
for i, (x, y) in dots.items():
    if y < Y0 + 2 or abs(x) > 285: continue
    if i in face: cv2.circle(im, px(x, y), 9, GREEN, 3, cv2.LINE_AA); cv2.putText(im, str(i), (px(x, y)[0] + 12, px(x, y)[1] + 24), F, 0.65, GREEN, 2)
    else: cv2.circle(im, px(x, y), 5, (150, 150, 150), -1, cv2.LINE_AA)
t = [("black: design outline (mean of right and mirrored left)", (0, 0, 0)), ("red: right solve (thin: mirrored)", RED), ("blue: left solve (thin: mirrored)", BLUE),
     ("green rings: tape dots on the front face (not used in the solve)", GREEN), ("grey dots: tape dots on the seat top; dashed: model v9 front line", (110, 110, 110))]
cv2.putText(im, "Seat front edge in plan (chair frame, mm; forward is up; grid 10 mm)", (12, 34), F, 0.95, (0, 0, 0), 2)
for k, (s, c) in enumerate(t): cv2.putText(im, s, (12 + (k % 3) * 760, 70 + (k // 3) * 32), F, 0.68, c, 2)
Path(a.out).parent.mkdir(parents=True, exist_ok=True); cv2.imwrite(a.out, im, [cv2.IMWRITE_JPEG_QUALITY, 90]); print(a.out, im.shape)
