"""USAGE: python -I tools/tube_show.py PREFIX OUT.jpg SCALE GRID "U0 U1 V0 V1" PHOTO[,PHOTO..] TUBE.json [TUBE.json ...]
By-eye check of tools/tube_tri.py on SINGLE rectified photos: each photo's own trace (red dots, every 4 mm) and the fitted
tube's outline for that camera (cyan line) over a zoomed, gridded crop. One panel per photo, stacked. Tiny compute."""
import sys, json, cv2, numpy as np
prefix, out, scale, G = sys.argv[1], sys.argv[2], float(sys.argv[3]), float(sys.argv[4]); U0, U1, V0, V1 = map(float, sys.argv[5].split()); photos = sys.argv[6].split(","); tubes = [json.load(open(f)) for f in sys.argv[7:]]
pj = json.load(open(prefix + "_plane.json")); (u0, u1), (v0, v1), res = pj["urange"], pj["vrange"], pj["res"]; k = scale / res; px = lambda uv: (int(round((uv[0] - U0) * k)), int(round((V1 - uv[1]) * k))); ims = []
for p in photos:
    im = cv2.imread(f"{prefix}_{p}.png"); im = cv2.resize(im[int((v1 - V1) / res):int((v1 - V0) / res), int((U0 - u0) / res):int((U1 - u0) / res)], None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    for v in np.arange(np.ceil(V0 / G) * G, V1, G):
        r = px((U0, v))[1]; cv2.line(im, (0, r), (im.shape[1], r), (0, 255, 255), 1); cv2.putText(im, f"{v:.0f}", (3, r - 3), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 255), 1)
    for u in np.arange(np.ceil(U0 / G) * G, U1, G):
        c = px((u, V0))[0]; cv2.line(im, (c, 0), (c, im.shape[0]), (0, 255, 255), 1); cv2.putText(im, f"{u:.0f}", (c + 3, im.shape[0] - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 255), 1)
    for t in tubes:
        if p not in t["per_photo"]: continue
        d = t["per_photo"][p]; F = np.array(d["fitted_uv"]); cv2.polylines(im, [np.array([px(q) for q in F], np.int32)], False, (255, 255, 0), 1, cv2.LINE_AA)
        for q in d["traced_uv"][::2]: cv2.circle(im, px(q), 2, (0, 0, 255), -1, cv2.LINE_AA)
    cv2.putText(im, "IMG_" + p, (60, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2); ims.append(cv2.copyMakeBorder(im, 0, 6, 0, 0, cv2.BORDER_CONSTANT, value=(255, 255, 255)))
cv2.imwrite(out, np.vstack(ims), [cv2.IMWRITE_JPEG_QUALITY, 90])
