"""USAGE: tools/py.sh tools/rocker_bottom/fig_photos.py RIBBONDIR TRACE.json [OUT figures/rocker_bottom/photos.jpg]
Single real photos of both rockers, resampled onto the side's face plane (tools/rocker_bottom/ribbon.py) at 10 px per mm: the model's top edge
(white), its bottom edge before (dashed yellow, v21) and after (green, parts/rocker_bottom.json), hung from the top edge as this photo shows it
(the running median of the top edge traced in it, over 21 mm), so the gap between green / yellow and the wood's lower edge is the face-height
difference this one photo sees; magenta dots: the bottom edge traced in that photo."""
import sys, json, cv2, numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
d, trf = sys.argv[1:3]; out = sys.argv[3] if len(sys.argv) > 3 else "figures/rocker_bottom/photos.jpg"
R = json.load(open(f"{d}/ribbons.json")); TR = json.load(open(trf)); g = R["grid"]; P = json.load(open("parts/rocker_bottom.json")); cu, cdv = np.array(P["correction"]["u"]), np.array(P["correction"]["dv_mm"])
us = np.arange(g["u0"], g["u1"] + 1e-9, g["du"]); Z = 2.0
PANELS = [("L", "1507", -340, -220, "Left rocker, tail: the face is up to 2 mm shallower than the model; the bottom moves up"),
          ("R", "1472", -340, -220, "Right rocker, the same stretch, another camera"),
          ("L", "1508", 120, 240, "Left rocker at the contact with the table: unchanged (dark band below: the rocker's shadow)"),
          ("R", "1473", 460, 575, "Right rocker at the front leg's foot: unchanged, within the tolerance")]
INK, MUTE, SURF = "#0b0b0b", "#52514e", "#fcfcfb"
fig, axs = plt.subplots(len(PANELS), 1, figsize=(12.5, 3.25 * len(PANELS)), facecolor=SURF)
for ax, (S, ph, ua, ub, title) in zip(axs, PANELS):
    im = cv2.imread(f"{d}/{S}_{ph}.png")[:, :, ::-1]; c0, c1 = int(round((ua - g["u0"]) / g["du"])), int(round((ub - g["u0"]) / g["du"]))
    r0, r1 = int((g["t1"] - 6) / g["dt"]), int((g["t1"] + 33) / g["dt"]); crop = im[r0:r1, c0:c1]
    crop = cv2.resize(crop, (int((ub - ua) * 5 * Z), int(crop.shape[0] * Z)), interpolation=cv2.INTER_CUBIC)
    T = TR[S]; tu = np.array(T["u"]); Pp = T["photos"][ph]; sh = np.array(Pp["placed_shift_t"]); sb = np.array(T["seed_bot_t"])
    tp = np.array([np.nan if v is None else v for v in Pp["top_t"]], float); tp[~np.array(Pp["top_ok"], bool)] = np.nan
    sh = np.array([np.nanmedian(tp[max(0, i - 10):i + 11]) if np.isfinite(tp[max(0, i - 10):i + 11]).sum() >= 5 else np.nan for i in range(len(tp))])
    sh = np.interp(tu, tu[np.isfinite(sh)], sh[np.isfinite(sh)])
    m = (tu >= ua) & (tu <= ub); X = (tu[m] - ua) * 5 * Z; Y = lambda t: ((g["t1"] - t) / g["dt"] - r0) * Z
    dv = np.interp(tu[m], cu, cdv, left=0, right=0)
    ax.imshow(crop, extent=(0, crop.shape[1], crop.shape[0], 0))
    ax.plot(X, Y(sh[m]), color="white", lw=1.2, ls=(0, (6, 3)), label="model top edge")
    ax.plot(X, Y(sb[m] + sh[m]), color="#ffd400", lw=1.6, ls=(0, (5, 3)), label="model bottom before (v21)")
    ax.plot(X, Y(sb[m] + sh[m] + dv), color="#19c37d", lw=1.8, label="model bottom after (v22)")
    bt = np.array([np.nan if v is None else v for v in Pp["bot_t"]], float)[m]; ok = np.array(Pp["bot_ok"], bool)[m] & np.isfinite(bt)
    ax.plot(X[ok][::2], Y(bt[ok][::2]), "o", ms=1.6, color="#ff3df5", label="bottom traced in this photo")
    ticks = np.arange(np.ceil(ua / 20) * 20, ub + 1e-9, 20); ax.set_xticks((ticks - ua) * 5 * Z); ax.set_xticklabels([f"{t:.0f}" for t in ticks])
    tt = np.arange(0, -31, -10); ax.set_yticks(Y(tt + np.median(sh[m]))); ax.set_yticklabels([f"{t:.0f}" for t in tt])
    ax.set_title(f"{title}   (IMG_{ph}, 10 px/mm)", loc="left", fontsize=10.5, color=INK)
    ax.set_ylabel("mm below the top edge", color=MUTE, fontsize=9); ax.tick_params(colors=MUTE, labelsize=8.5)
    for s_ in ax.spines.values(): s_.set_visible(False)
axs[0].legend(loc="upper right", fontsize=8.5, ncol=4, framealpha=0.85); axs[-1].set_xlabel("u along the rocker, mm", color=MUTE)
fig.tight_layout(); fig.savefig(out, dpi=110, facecolor=SURF, pil_kwargs={"quality": 88}); print("wrote", out)
