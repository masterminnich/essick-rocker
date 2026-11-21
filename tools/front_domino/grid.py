"""USAGE: rk.sh work/fdom/grid.py LEG PHOTOS(a,b,..) OUT.jpg [U0 U1 V0 V1] [SCALE px/mm]  gridded view of cached orthos, grid 5 mm, labels every 10."""
import sys, json, cv2, numpy as np
leg, phs, out = sys.argv[1], sys.argv[2].split(","), sys.argv[3]
U0, U1, V0, V1 = [float(x) for x in sys.argv[4:8]] if len(sys.argv) > 7 else (-40, 30, -20, 60); SC = float(sys.argv[8]) if len(sys.argv) > 8 else 4.0
P = json.load(open("work/fdom/raw/planes.json"))[leg]; ur, vr, res = P["urange"], P["vrange"], P["res"]; T = []
for ph in phs:
    im = cv2.imread(f"work/fdom/raw/{leg}_{ph}.png"); c0 = int((U0 - ur[0]) / res); c1 = int((U1 - ur[0]) / res); r0 = int((vr[1] - V1) / res); r1 = int((vr[1] - V0) / res)
    im = cv2.resize(im[r0:r1, c0:c1], None, fx=SC * res, fy=SC * res, interpolation=cv2.INTER_AREA if SC * res < 1 else cv2.INTER_CUBIC)
    lab = cv2.cvtColor(im, cv2.COLOR_BGR2Lab); lab[:, :, 0] = cv2.createCLAHE(3.0, (4, 4)).apply(lab[:, :, 0]); im = cv2.cvtColor(lab, cv2.COLOR_Lab2BGR); base = im.copy()
    for g in range(int(np.ceil(U0 / 5)) * 5, int(U1) + 1, 5):
        x = int(round((g - U0) * SC)); col = (0, 255, 255) if g % 10 == 0 else (200, 200, 0)
        if g % 10 == 0: cv2.line(im, (x, 0), (x, im.shape[0]), col, 1)
        else: cv2.line(im, (x, 0), (x, 8), col, 1); cv2.line(im, (x, im.shape[0] - 8), (x, im.shape[0]), col, 1)
        if g % 10 == 0: cv2.putText(im, str(g), (x + 2, 12), 0, 0.4, (0, 255, 255), 1, cv2.LINE_AA)
    for g in range(int(np.ceil(V0 / 5)) * 5, int(V1) + 1, 5):
        y = int(round((V1 - g) * SC)); col = (0, 255, 255) if g % 10 == 0 else (200, 200, 0)
        if g % 10 == 0: cv2.line(im, (0, y), (im.shape[1], y), col, 1)
        else: cv2.line(im, (0, y), (8, y), col, 1); cv2.line(im, (im.shape[1] - 8, y), (im.shape[1], y), col, 1)
        if g % 10 == 0: cv2.putText(im, str(g), (2, y - 2), 0, 0.4, (0, 255, 255), 1, cv2.LINE_AA)
    im = cv2.addWeighted(im, 0.6, base, 0.4, 0)
    cv2.rectangle(im, (0, im.shape[0] - 20), (70, im.shape[0]), (255, 255, 255), -1); cv2.putText(im, ph, (4, im.shape[0] - 5), 0, 0.55, (0, 0, 0), 1, cv2.LINE_AA); T.append(im)
per = int(sys.argv[9]) if len(sys.argv) > 9 else 4
rows = [np.hstack(T[i:i+per] + [np.zeros_like(T[0])] * (per - len(T[i:i+per]))) for i in range(0, len(T), per)]
cv2.imwrite(out, np.vstack(rows), [cv2.IMWRITE_JPEG_QUALITY, 92])
