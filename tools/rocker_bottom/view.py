"""USAGE: work/toolkit/rk.sh tools/rocker_bottom/view.py RIBBONDIR S PHOTO U_FROM U_TO OUT.jpg [ZOOM 1] [TRACE.json] [SPLIT 1]
A look at ONE photo's ribbon (tools/rocker_bottom/ribbon.py) between stations U_FROM and U_TO, enlarged ZOOM times over the ribbon's
5 px per mm (ZOOM 2 = 10 px per mm). Grid: a station line every 10 mm (labelled every 50), t lines every 5 mm; dashed white t = 0 (the side's
own top edge in parts/rocker_profile.json) and the old bottom edge (yellow). With TRACE.json (tools/rocker_bottom/trace.py) that photo's
snapped top (cyan) and bottom (magenta) points are drawn, crosses where a point was rejected. SPLIT n stacks the range as n strips.
Tiny compute."""
import sys, json, cv2, numpy as np
d, S, ph, ua, ub, outf = sys.argv[1:7]; ua, ub = float(ua), float(ub); Z = float(sys.argv[7]) if len(sys.argv) > 7 else 1.0
TR = json.load(open(sys.argv[8])) if len(sys.argv) > 8 and sys.argv[8] not in ("", "-") else None; SPLIT = int(sys.argv[9]) if len(sys.argv) > 9 else 1
R = json.load(open(f"{d}/ribbons.json")); g = R["grid"]; side = R["sides"][S]; im = cv2.imread(f"{d}/{S}_{ph}.png"); us = np.arange(g["u0"], g["u1"] + 1e-9, g["du"])
k = Z / g["dt"]; kc = Z / g["du"] * g["du"] / g["dt"]           # output pixels per mm along u and t (same scale: 5*Z px per mm)
seedb = np.interp(us, us[::20], side["seed_bottom_t"]); strips = []
for a, b in zip(np.linspace(ua, ub, SPLIT + 1)[:-1], np.linspace(ua, ub, SPLIT + 1)[1:]):
    c0, c1 = int(round((a - g["u0"]) / g["du"])), int(round((b - g["u0"]) / g["du"])); crop = im[:, c0:c1]
    crop = cv2.resize(crop, (int(round((c1 - c0) * g["du"] * 5 * Z)), int(round(crop.shape[0] * Z))), interpolation=cv2.INTER_CUBIC)
    X = lambda u: int(round((u - a) * 5 * Z)); Y = lambda t: int(round((g["t1"] - t) * 5 * Z))
    for t in np.arange(-40, 11, 5): cv2.line(crop, (0, Y(t)), (crop.shape[1], Y(t)), (90, 90, 90), 1)
    for u in np.arange(np.ceil(a / 10) * 10, b, 10):
        cv2.line(crop, (X(u), 0), (X(u), crop.shape[0]), (255, 255, 0) if u % 50 == 0 else (120, 120, 0), 1)
        if u % 50 == 0: cv2.putText(crop, str(int(u)), (X(u) + 2, 12), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 0), 1)
    for t in (-30, -20, -10, 0, 10): cv2.putText(crop, str(t), (2, Y(t) - 2), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (200, 200, 200), 1)
    m = (us >= a) & (us < b); xs = ((us[m] - a) * 5 * Z).astype(int)
    for x, t in list(zip(xs, seedb[m]))[::8]: cv2.circle(crop, (x, Y(t)), 1, (0, 220, 255), -1)
    for x in xs[::16]: cv2.circle(crop, (x, Y(0)), 1, (255, 255, 255), -1)
    if TR and ph in TR[S]["photos"]:
        P = TR[S]["photos"][ph]; tu = np.array(TR[S]["u"])
        for key, col in (("top", (255, 255, 0)), ("bot", (255, 0, 255))):
            t = np.array(P[key + "_t"], float); good = np.array(P[key + "_ok"], bool); mm = (tu >= a) & (tu < b) & np.isfinite(t)
            for u, tt, gd in zip(tu[mm], t[mm], good[mm]):
                if gd: cv2.circle(crop, (X(u), Y(tt)), max(1, int(Z)), col, -1)
                else: cv2.drawMarker(crop, (X(u), Y(tt)), (0, 0, 255), cv2.MARKER_TILTED_CROSS, max(4, int(3 * Z)), 1)
    strips.append(crop)
W = max(s.shape[1] for s in strips); strips = [np.pad(s, ((0, 4), (0, W - s.shape[1]), (0, 0))) for s in strips]; out = np.vstack(strips)
lab = f"{S} IMG_{ph}  u {ua:.0f}..{ub:.0f}  {5 * Z:.0f} px/mm  (native {np.mean([p for p, s in zip(side['photos'][ph]['px_per_mm_5mm'], side['photos'][ph]['seen_5mm']) if s]):.1f})"
cv2.rectangle(out, (0, out.shape[0] - 18), (8 * len(lab) + 8, out.shape[0]), (255, 255, 255), -1); cv2.putText(out, lab, (4, out.shape[0] - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 1, cv2.LINE_AA)
cv2.imwrite(outf, out, [cv2.IMWRITE_JPEG_QUALITY, 92]); print("wrote", outf, out.shape)
