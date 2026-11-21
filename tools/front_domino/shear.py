"""Straightened orthos: s = u + K*(v - V0) (K = leg lean, model 0.185; V0 = 19.2 the Domino's height), so the leg's edges stand vertical.
USAGE: rk.sh work/fdom/shear.py LEG PHOTOS OUT.jpg [S0 S1 V0 V1 SCALE PER]  -> gridded view; also usable as module: straight(leg, ph, res)"""
import sys, json, cv2, numpy as np
K, VD = 0.185, 19.2
def straight(leg, ph, S=(-45, 35), V=(-40, 80), res=0.1):
    P = json.load(open("work/fdom/raw/planes.json"))[leg]; ur, vr, r0 = P["urange"], P["vrange"], P["res"]
    im = cv2.imread(f"work/fdom/raw/{leg}_{ph}.png"); ss = np.arange(S[0], S[1], res); vs = np.arange(V[1], V[0], -res)
    SS, VV = np.meshgrid(ss, vs); UU = SS - K * (VV - VD)
    mx = ((UU - ur[0]) / r0).astype(np.float32); my = ((vr[1] - VV) / r0).astype(np.float32)
    return cv2.remap(im, mx, my, cv2.INTER_LINEAR), ss, vs
if __name__ == "__main__":
    leg, phs, out = sys.argv[1], sys.argv[2].split(","), sys.argv[3]
    S0, S1, V0, V1, SC = [float(x) for x in sys.argv[4:9]] if len(sys.argv) > 8 else (-45, 35, -40, 80, 5); per = int(sys.argv[9]) if len(sys.argv) > 9 else 3
    T = []
    for ph in phs:
        im, ss, vs = straight(leg, ph, (S0, S1), (V0, V1), 1 / SC)
        lab = cv2.cvtColor(im, cv2.COLOR_BGR2Lab); lab[:, :, 0] = cv2.createCLAHE(3.0, (4, 4)).apply(lab[:, :, 0]); im = cv2.cvtColor(lab, cv2.COLOR_Lab2BGR); base = im.copy()
        for g in range(int(np.ceil(S0 / 5)) * 5, int(S1) + 1, 5):
            x = int(round((g - S0) * SC)); col = (0, 255, 255) if g % 10 == 0 else (255, 200, 0)
            cv2.line(im, (x, 0), (x, im.shape[0]), col, 1)
            if g % 10 == 0: cv2.putText(im, str(g), (x + 2, 12), 0, 0.4, (0, 255, 255), 1, cv2.LINE_AA)
        for g in range(int(np.ceil(V0 / 10)) * 10, int(V1) + 1, 10):
            y = int(round((V1 - g) * SC)); cv2.line(im, (0, y), (im.shape[1], y), (0, 255, 255), 1); cv2.putText(im, str(g), (2, y - 2), 0, 0.4, (0, 255, 255), 1, cv2.LINE_AA)
        im = cv2.addWeighted(im, 0.55, base, 0.45, 0)
        cv2.rectangle(im, (0, im.shape[0] - 20), (60, im.shape[0]), (255, 255, 255), -1); cv2.putText(im, ph, (4, im.shape[0] - 5), 0, 0.55, (0, 0, 0), 1, cv2.LINE_AA); T.append(im)
    rows = [np.hstack(T[i:i+per] + [np.zeros_like(T[0])] * (per - len(T[i:i+per]))) for i in range(0, len(T), per)]
    cv2.imwrite(out, np.vstack(rows), [cv2.IMWRITE_JPEG_QUALITY, 90])
