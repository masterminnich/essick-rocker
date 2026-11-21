"""USAGE: work/toolkit/rk.sh tools/rocker_bottom/fit.py TRACE.json RIBBONDIR OUT.json [PART.json]
Step 3 of 3 (ribbon -> trace -> fit). Face height of each rocker along u -330..572 from the per-photo traces (tools/rocker_bottom/trace.py):
 per photo  - kept top / bottom points; each edge cleaned against its own running median over 21 mm (points more than 0.8 mm off it dropped);
              the top edge is carried across the stretches where it is hidden (the legs' feet stand on it) by the running median, linearly
              between the two sides (at most 120 mm). Face height h = t(top) - t(bottom), square to the top edge, every 1 mm.
 per station - every 5 mm, each photo's mean h over +-2.5 mm (only where it has >= 3 bottom points there). The photos do not agree on h: it
              runs with how high the camera stands (x = (camera v - edge v) / camera height, the tangent of the view's elevation), by up to
              2 mm per unit of x, the sign changing along the rocker: the two arrises are not in one plane square to the camera rays (the face
              is not quite square to its plane, a few degrees). The outline the model extrudes is the face seen square to its plane, x = 0, so
              per station h = the value at x = 0 of a straight line h(x) fitted over the photos (two passes, residuals over
              max(2.5 rms, 0.6 mm) dropped); spread = 1.4826 * MAD of the residuals; standard error of h(0). Fewer than 4 photos or an x range
              under 0.5: the median, flagged. Fewer than 3 photos: NOT SEEN.
 design      - L/R mean of h (the face height is the same in either side's frame), compared with the model's own face height square to
              mean_top from mean_top / mean_bot (parts/rocker_profile.json); traced bottom v = mean_top - h / cos(top slope) in the design
              (left) frame, its rocking radius over the old fit's range u -75..405 where seen, and its lowest point.
 correction  - with PART.json: the bottom-edge correction the build reads (parts/rocker_bottom.json), see the "rule" written into it.
Numbers printed are the ones quoted in the PR."""
import sys, json, numpy as np
T = json.load(open(sys.argv[1])); R = json.load(open(sys.argv[2] + "/ribbons.json")); outf = sys.argv[3]; partf = sys.argv[4] if len(sys.argv) > 4 else None
RP = json.load(open("parts/rocker_profile.json")); UP = np.array(RP["u"]); g = R["grid"]; us5 = np.arange(g["u0"], g["u1"] + 1e-9, g["du"])[::20]
STEP, HALF, MINPTS, MINPH = 5.0, 2.5, 3, 3; SU = np.arange(-330.0, 572.0 + 1e-9, STEP)
def runmed(x, ok, k=21):
    """running median of x over ok points (k stations), NaN where fewer than 5 ok points in the window"""
    y = np.where(ok, x, np.nan); out = np.full(len(x), np.nan)
    for i in range(len(x)):
        w = y[max(0, i - k // 2):i + k // 2 + 1]; w = w[np.isfinite(w)]
        if len(w) >= 5: out[i] = np.median(w)
    return out
def fill(x, maxgap):
    """linear across NaN gaps of at most maxgap stations; longer gaps stay NaN"""
    i = np.where(np.isfinite(x))[0]; y = x.copy()
    if len(i) < 2: return y
    for a, b in zip(i[:-1], i[1:]):
        if 1 < b - a <= maxgap: y[a:b + 1] = np.interp(np.arange(a, b + 1), [a, b], [x[a], x[b]])
    return y
def at_x0(x, h):
    """h at x = 0 of a line h(x) over the photos; returns h0, standard error, spread of residuals, slope, photos kept, how"""
    if len(h) < 4 or np.ptp(x) < 0.5:
        md = float(np.median(h)); return md, float(1.4826 * np.median(np.abs(h - md)) / np.sqrt(len(h))), float(1.4826 * np.median(np.abs(h - md))), np.nan, len(h), "median"
    keep = np.ones(len(h), bool)
    for _ in range(2):
        A = np.c_[np.ones(keep.sum()), x[keep]]; c = np.linalg.lstsq(A, h[keep], rcond=None)[0]; r = h - (c[0] + c[1] * x)
        rms = np.sqrt(np.mean(r[keep] ** 2)); keep = np.abs(r) <= max(2.5 * rms, 0.6)
        if keep.sum() < 4: keep[:] = True
    A = np.c_[np.ones(keep.sum()), x[keep]]; c = np.linalg.lstsq(A, h[keep], rcond=None)[0]; r = h[keep] - A @ c; n = int(keep.sum())
    s2 = np.sum(r ** 2) / max(n - 2, 1); se = float(np.sqrt(s2 * np.linalg.inv(A.T @ A)[0, 0]))
    return float(c[0]), se, float(1.4826 * np.median(np.abs(r - np.median(r)))), float(c[1]), n, "line"
OUT = {"note": __doc__.split("\n")[1], "stations_u": SU.tolist()}
mt = np.array(RP["mean_top"]); mb = np.array(RP["mean_bot"]); cos_m = np.cos(np.arctan(np.gradient(mt, UP)))
H_MODEL = np.interp(SU, UP, (mt - mb) * cos_m)                                    # the model's face height, square to its top edge
for S in "LR":
    t = T[S]; u = np.array(t["u"]); side = R["sides"][S]; top_v = np.interp(u, us5, side["top_v"]); tv_su = np.interp(SU, us5, side["top_v"])
    H, PH, INFO = [], [], {}
    for ph, P in t["photos"].items():
        tt = np.array(P["top_t"], float); tb = np.array(P["bot_t"], float); ot = np.array(P["top_ok"], bool) & np.isfinite(tt); ob = np.array(P["bot_ok"], bool) & np.isfinite(tb)
        mtp = runmed(tt, ot); ot &= np.abs(tt - mtp) < 0.8; mbp = runmed(tb, ob); ob &= np.abs(tb - mbp) < 0.8
        top = fill(runmed(tt, ot), 120); H.append(np.where(ob, top - tb, np.nan)); PH.append(ph)
        INFO[ph] = {"top_points": int(ot.sum()), "bottom_points": int(ob.sum()), "cam_u_v_height": P["cam_u_v_height"]}
    H = np.array(H); rows = []
    for k, s in enumerate(SU):
        m = np.abs(u - s) <= HALF; vals, who, xs = [], [], []
        for i in range(len(PH)):
            x = H[i, m]; x = x[np.isfinite(x)]
            if len(x) >= MINPTS:
                cu, cv, ch = INFO[PH[i]]["cam_u_v_height"]; vals.append(x.mean()); who.append(PH[i]); xs.append((cv - (tv_su[k] - 13.0)) / ch)
        vals, xs = np.array(vals), np.array(xs)
        if len(vals) >= MINPH: h0, se, spr, slope, nk, how = at_x0(xs, vals); med = float(np.median(vals))
        else: h0 = se = spr = slope = med = np.nan; nk, how = len(vals), "not seen"
        rows.append(dict(h=h0, se=se, spread=spr, slope=slope, n=len(vals), n_kept=nk, how=how, median=med, per={w: round(float(v), 2) for w, v in zip(who, vals)}, x=[round(float(v), 2) for v in xs]))
    old = np.interp(SU, UP, RP["face_height_mm"]["left" if S == "L" else "right"])
    OUT[S] = {"h_mm": [None if not np.isfinite(r["h"]) else round(r["h"], 3) for r in rows], "h_se_mm": [None if not np.isfinite(r["se"]) else round(r["se"], 3) for r in rows],
              "spread_mm": [None if not np.isfinite(r["spread"]) else round(r["spread"], 3) for r in rows], "photos": [r["n"] for r in rows], "how": [r["how"] for r in rows],
              "h_slope_per_x": [None if not np.isfinite(r["slope"]) else round(r["slope"], 2) for r in rows], "h_median_all_photos_mm": [None if not np.isfinite(r["median"]) else round(r["median"], 3) for r in rows],
              "per_photo_h": [r["per"] for r in rows], "per_photo_x": [r["x"] for r in rows], "old_side_h_mm": np.round(old, 3).tolist(), "photo_info": INFO}
    print(f"== {S}: photos {len(PH)}   (h at x=0 | spread se n how | old side h, new-old | median over photos - old)")
    for s in np.arange(-330, 573, 30):
        k = int(np.argmin(np.abs(SU - s))); r = rows[k]
        print(f"  u {SU[k]:5.0f}: h {r['h']:6.2f}  spread {r['spread']:4.2f} se {r['se']:4.2f} n {r['n']:2d} {r['how']:8s}| old {old[k]:6.2f} new-old {r['h'] - old[k]:+5.2f} | median-old {r['median'] - old[k]:+5.2f}")
# ---------------------------------------------------------------- design: L/R mean, against the model
hL, hR = (np.array([np.nan if v is None else v for v in OUT[S]["h_mm"]]) for S in "LR")
sL, sR = (np.array([np.nan if v is None else v for v in OUT[S]["spread_mm"]]) for S in "LR")
both = np.isfinite(hL) & np.isfinite(hR); hD = np.where(both, (hL + hR) / 2, np.where(np.isfinite(hL), hL, hR))
seen_by = np.where(both, "both", np.where(np.isfinite(hL), "left only", np.where(np.isfinite(hR), "right only", "neither")))
dD = hD - H_MODEL
def stretches(mask):
    out, i = [], 0
    while i < len(SU):
        if mask[i]:
            j = i
            while j + 1 < len(SU) and mask[j + 1]: j += 1
            out.append([float(SU[i]), float(SU[j])]); i = j + 1
        else: i += 1
    return out
unseen = {S: stretches(~np.isfinite(h)) for S, h in (("L", hL), ("R", hR))}; unseen["design"] = stretches(~np.isfinite(hD))
top_D = np.interp(SU, UP, mt); cosD = np.interp(SU, UP, cos_m); botD = top_D - hD / cosD; botM = np.interp(SU, UP, mb)
def circle(x, y):
    A = np.c_[x, y, np.ones_like(x)]; b = x ** 2 + y ** 2; c = np.linalg.lstsq(A, b, rcond=None)[0]; xc, yc = c[0] / 2, c[1] / 2; r = np.sqrt(c[2] + xc ** 2 + yc ** 2)
    return float(r), float(xc), float(yc), float(np.sqrt(np.mean((np.hypot(x - xc, y - yc) - r) ** 2)))
rr = (SU >= -75) & (SU <= 405) & np.isfinite(botD); rad = circle(SU[rr], botD[rr]); radM = circle(SU[rr], botM[rr])
lo = int(np.nanargmin(botD)); loM = int(np.argmin(botM))
OUT["design"] = {"frame": "the left side's face plane (the build's design frame before to_mean); h is square to mean_top", "h_mm": np.round(hD, 3).tolist(), "seen_by": seen_by.tolist(),
                 "model_h_mm": np.round(H_MODEL, 3).tolist(), "new_minus_model_mm": np.round(dD, 3).tolist(), "left_minus_right_mm": np.round(hL - hR, 3).tolist(),
                 "bottom_v_traced_mm": np.round(botD, 3).tolist(), "bottom_v_model_mm": np.round(botM, 3).tolist(), "unseen_stretches_u": unseen,
                 "rocking_radius": {"range_u": [-75, 405], "stations": int(rr.sum()), "traced_mm": round(rad[0], 1), "traced_rms_mm": round(rad[3], 2), "model_same_stations_mm": round(radM[0], 1),
                                    "model_same_stations_rms_mm": round(radM[3], 2), "model_file_mm": RP["rocking_radius_mm"]},
                 "lowest_point": {"traced_u_v": [float(SU[lo]), round(float(botD[lo]), 2)], "model_u_v": [float(SU[loM]), round(float(botM[loM]), 2)]}}
print("== design (L/R mean, h at x=0) against the model's face height square to mean_top")
for s in np.arange(-330, 573, 30):
    k = int(np.argmin(np.abs(SU - s)))
    print(f"  u {SU[k]:5.0f}: L {hL[k]:6.2f} R {hR[k]:6.2f} L-R {hL[k] - hR[k]:+5.2f} | design {hD[k]:6.2f} model {H_MODEL[k]:6.2f} new-model {dD[k]:+5.2f} ({seen_by[k]})")
print("unseen (fewer than 3 photos):", unseen)
print("rocking radius over u -75..405 (%d stations): traced %.1f mm rms %.2f | model, same stations %.1f rms %.2f | file %.2f" % (rr.sum(), rad[0], rad[3], radM[0], radM[3], RP["rocking_radius_mm"]))
print("lowest point: traced u %.0f v %.2f | model u %.0f v %.2f" % (SU[lo], botD[lo], SU[loM], botM[loM]))
json.dump(OUT, open(outf, "w"))
if partf:
    # ------------------------------------------------------------ the correction the build reads
    # Where the design differs from the model beyond the tolerance (1.6 mm) and its spread, the tail third: the bottom moves to the traced
    # design h (square to the unchanged mean_top). From u -30 forward the trace agrees with the model within the tolerance and, around the
    # contact (u 90..240), the face's lower edge is too like the rocker's own shadow on the table to beat the model; there the bottom is
    # left exactly as it was (so the lowest point, the rocking radius and the chair's height do not move).
    # dv = new bottom - old bottom (design frame v), smoothed over 35 mm (running median of 7 stations, then a 5-station mean), carried by
    # weight w: 1 for u <= -90, cosine to 0 at u -30. Into the tail end (parts/rocker_ends.json design.tail, which meets the old bottom at
    # u -330 and runs out to its own trace by u -400) dv fades linearly from its value at -330 to 0 at -400: no step, the end's own traced
    # bottom further out unchanged.
    dvr = -(hD - H_MODEL) / cosD; ok = np.isfinite(dvr); dvf = np.interp(SU, SU[ok], dvr[ok])
    dvs = np.array([np.median(dvf[max(0, i - 3):i + 4]) for i in range(len(SU))]); dvs = np.convolve(np.pad(dvs, 2, mode="edge"), np.ones(5) / 5, mode="valid")
    w = np.where(SU <= -90, 1.0, np.where(SU >= -30, 0.0, 0.5 * (1 + np.cos(np.pi * (SU + 90) / 60)))); dv = dvs * w
    ut = np.arange(-400.0, -330.0, 5.0); dvt = dv[0] * (ut + 400.0) / 70.0
    gu = np.r_[ut, SU]; gdv = np.r_[dvt, dv]
    stretch = [{"u": [-400, -330], "provenance": "tail end blend (parts/rocker_ends.json design.tail): moved by the correction at u -330, fading to 0 at u -400", "tol_mm": 1.6},
               {"u": [-330, -90], "provenance": "traced (this file's design h; a median of %d photos per station on the left, %d on the right)" % tuple(np.median(np.array(OUT[S]["photos"])[(SU >= -330) & (SU <= -90)]) for S in "LR"), "tol_mm": 1.6},
               {"u": [-90, -30], "provenance": "traced, blended (cosine) into the model's bottom", "tol_mm": 1.6},
               {"u": [-30, 572], "provenance": "fitted (parts/rocker_profile.json mean_bot), traced and agrees within %.1f mm (largest |new - model| of the design, at u %.0f; around the contact, u 90..240, the face's lower edge is hard to tell from the rocker's own shadow on the table)" % (np.nanmax(np.abs(dD[(SU >= -30)])), SU[SU >= -30][np.nanargmax(np.abs(dD[SU >= -30]))]), "tol_mm": 1.6}]
    part = {"what": "the rockers' bottom edge between the two ends, traced directly in single photos (tools/rocker_bottom/); read by tools/build_model.py on top of parts/rocker_profile.json (unchanged)",
            "frame": OUT["design"]["frame"] + "; the build adds dv to mean_bot and to the tail end's bot, then carries the outline to its half-way frame (to_mean) as before",
            "rule": "bottom v = mean_bot + dv(u), dv linear between the stations below and 0 outside them. The top edge, the legs' feet and joints are untouched.",
            "correction": {"u": gu.tolist(), "dv_mm": np.round(gdv, 3).tolist()},
            "stretches": stretch,
            "design": {"u": SU.tolist(), "h_mm": OUT["design"]["h_mm"], "model_h_mm": OUT["design"]["model_h_mm"], "new_minus_model_mm": OUT["design"]["new_minus_model_mm"], "seen_by": OUT["design"]["seen_by"]},
            "left": {k: OUT["L"][k] for k in ("h_mm", "spread_mm", "h_se_mm", "photos", "how", "old_side_h_mm")},
            "right": {k: OUT["R"][k] for k in ("h_mm", "spread_mm", "h_se_mm", "photos", "how", "old_side_h_mm")},
            "unseen_stretches_u": unseen, "rocking_radius": OUT["design"]["rocking_radius"], "lowest_point": OUT["design"]["lowest_point"],
            "method": "per photo, the face's top and bottom arris square to the top edge on a ribbon orthophoto of that photo on the side's own face plane; per station the photos' "
                      "face heights fitted against the camera's elevation and read at a square view (x = 0); left and right averaged. See tools/rocker_bottom/{ribbon,trace,fit}.py."}
    json.dump(part, open(partf, "w"), indent=1); print("wrote", partf, "dv at u -330 %.2f, -300 %.2f, -240 %.2f, -150 %.2f, -90 %.2f, -60 %.2f, -30 %.2f" % tuple(np.interp([-330, -300, -240, -150, -90, -60, -30], gu, gdv)))
