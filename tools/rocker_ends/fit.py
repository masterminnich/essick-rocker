"""USAGE: work/toolkit/rk.sh tools/rocker_ends/fit.py TRACE.json ORTHODIR [OUT parts/rocker_ends.json]
Step 3 of 3 (ortho -> trace -> fit). Turns the per-photo outlines of the four rocker ends (tools/rocker_ends/trace.py) into
 - one outline per end and side: every photo is slid in the face plane (two numbers per photo, its pose error at that end of the
   chair; started from trace.py's coarse placing, fitted with the weights that make an outline say as much about its place along the
   rocker as across it), the median over photos is taken point by point and smoothed over 4.5 mm. A photo's points are dropped where
   its camera looks ONTO the surface next to the face (see consensus), and everywhere a mark on the face was bridged by hand in the
   seed (seeds.json "bridge"). The outline's place = the median of the photos' slides;
 - the design ends (symmetric chair): the right rocker's outline carried into the left rocker's frame by the rigid fit of
   parts/rocker_profile.json; each side's end slid square to its top edge (one number) until that edge lies on the existing mean_top
   where both exist (the shape of an end is measured to a few tenths of a mm, its place in the plane only to 1-2 mm, and the legs
   already stand on the existing profile); then left and right averaged point by point (points matched by the share of the way to the
   landmark: the tail's tip, the nose's top corner), and the average faired over 12 mm except within 12 mm of the landmark;
 - how the design ends meet the existing profile (parts/rocker_profile.json mean_top / mean_bot), blended over a short stretch;
 - how far left and right differ: in shape (distance between the two outlines, away from the landmark) and in where the landmark sits.
Writes parts/rocker_ends.json; tools/build_model.py reads "design" only. The numbers printed are the ones quoted in LEDGER.md and the PR."""
import sys, json, numpy as np
from scipy.signal import savgol_filter
T = json.load(open(sys.argv[1])); W = json.load(open(sys.argv[2] + "/windows.json")); outf = sys.argv[3] if len(sys.argv) > 3 else "parts/rocker_ends.json"
RP = json.load(open("parts/rocker_profile.json")); RVL = RP["right_vs_left"]; U = np.array(RP["u"]); MIN_STRENGTH, MIN_PTS = 1.5, 40
SEEDS = json.load(open("tools/rocker_ends/inputs/seeds.json")); WIDTH, STRIP_MAX, TOP_NV = 31.0, 0.3, 0.7      # rocker's width across (tape); widest strip of a neighbouring surface tolerated, mm; normal's upward share above which a point counts as top edge
def rigid(q, inverse=False):
    th = np.radians(RVL["rotation_deg"]); c, s = np.cos(th), np.sin(th); q = np.asarray(q, float); su, sv = RVL["shift_u_mm"], RVL["shift_v_mm"]
    if inverse: d = q - [su, sv]; return np.c_[c * d[:, 0] + s * d[:, 1], -s * d[:, 0] + c * d[:, 1]]
    return np.c_[c * q[:, 0] - s * q[:, 1] + su, s * q[:, 0] + c * q[:, 1] + sv]
def uweight(nrm):
    """as in trace.py: weights that make the outline say as much about its place along the rocker as across it"""
    a, b = nrm[:, 0] ** 2, nrm[:, 1] ** 2; den = (a * a).sum() - (a * b).sum(); return 1 + (min(100.0, max(0.0, (b.sum() - a.sum()) / den)) if den > 1e-6 else 100.0) * a
def consensus(t):
    Q, N, s = np.array(t["outline"]), np.array(t["normal"]), np.array(t["s"]); phs = list(t["snapped"])
    O = np.array([t["snapped"][p]["off"] for p in phs]); ok = (np.array([t["snapped"][p]["strength"] for p in phs]) >= MIN_STRENGTH) & ~np.array([t["snapped"][p]["at_band_edge"] for p in phs]).astype(bool)
    # which edge a photo shows: where the camera stands on the outward side of the outline it looks ONTO the surface next to the face (the end
    # surface of the nose from in front, the underside from below) and that surface lies on the orthophoto as a strip beyond the arris,
    # WIDTH * (camera - point).normal / camera height wide. Arris and strip are both wood, the snap then finds the strip's far edge. Such
    # points are dropped; what is left there is the arris seen as a silhouette. The top edge is kept: every camera looks onto the top face,
    # which is lit from above and reads clearly against the face.
    C = np.array([[W[key]["photos"][p]["cam_u"], W[key]["photos"][p]["cam_v"]] for p in phs], float); h = np.array([W[key]["photos"][p]["cam_height"] for p in phs], float)
    strip = WIDTH * ((C[:, None, :] - Q[None]) * N[None]).sum(2) / h[:, None]; seen = (strip > STRIP_MAX) & (N[:, 1] < TOP_NV)[None]; nseen = (ok & seen).sum(1); ok &= ~seen
    br = np.array(t.get("bridged", [0] * len(Q)), bool); ok &= ~br[None]; wt = np.sqrt(uweight(N)); use = ok.sum(1) >= MIN_PTS; sh = np.array([t["snapped"][p].get("placed_u_v_mm", [0.0, 0.0]) for p in phs], float); sh[use] -= np.median(sh[use], 0); inl = ok.copy()      # start from trace.py's coarse placing
    for _ in range(10):
        Oc = np.where(ok & use[:, None], O - sh @ N.T, np.nan); c = np.nanmedian(Oc, 0); c = np.interp(s, s[np.isfinite(c)], c[np.isfinite(c)])
        for i in np.where(use)[0]:
            r = O[i] - c; m = ok[i] & (np.abs(r - N @ sh[i]) < 1.2); inl[i] = m
            if m.sum() >= 20: A = np.r_[N[m] * wt[m, None], 1.5 * np.eye(2)]; sh[i] = np.linalg.lstsq(A, np.r_[r[m] * wt[m], 0, 0], rcond=None)[0]
        sh[use] -= np.median(sh[use], 0)
    Oc = np.where(ok & use[:, None], O - sh @ N.T, np.nan); n = np.isfinite(Oc).sum(0); c = np.nanmedian(Oc, 0); few = n < 3; c = np.interp(s, s[~few], c[~few]); c = savgol_filter(c, 9, 2)
    mad = 1.4826 * np.nanmedian(np.abs(Oc - c), 0); P = Q + c[:, None] * N; photos = {}
    for i, p in enumerate(phs):
        r = (O[i] - N @ sh[i] - c)[inl[i]]; w = W[key]["photos"][p]
        photos[p] = {"used": bool(use[i]), "points": int(ok[i].sum()), "slide_u_v_mm": sh[i].round(2).tolist(), "rms_after_slide_mm": round(float(np.sqrt(np.mean(r ** 2))), 2) if use[i] and len(r) else None,
                     "share_within_1.2mm": round(float(inl[i].sum() / max(1, ok[i].sum())), 2), "points_dropped_looking_onto_the_next_surface": int(nseen[i]), "angle_deg": w["angle_deg"], "cam_u_v_height": [w["cam_u"], w["cam_v"], w["cam_height"]]}
    return P, s, n, mad, photos, few, br
def landmark(P, end):
    if end == "tail": return int(np.argmin(P[:, 0]))
    i0 = int(np.argmax(P[:, 0])); top = P[:i0][P[:i0, 0] < P[i0, 0] - 12]; a, b = np.polyfit(top[:, 0], top[:, 1], 1); t = np.array([1, a]) / np.hypot(1, a); nu = np.array([-t[1], t[0]]); return int(np.argmax(P @ (t + nu)))
def near(Pa, Pb):
    """distance from each point of Pa to the polyline Pb"""
    a, b = Pb[:-1], Pb[1:]; ab = b - a; L2 = np.maximum((ab ** 2).sum(1), 1e-12); return np.array([np.hypot(*(a + np.clip(((q - a) * ab).sum(1) / L2, 0, 1)[:, None] * ab - q).T).min() for q in Pa])
def fair(H):
    """the averaged outline (equal steps along its length, ending at the landmark) faired over 12 mm; within 12 mm of the landmark it is left as it is (the tail's tip turns on a few mm)"""
    s = np.r_[0, np.cumsum(np.hypot(*np.diff(H, axis=0).T))]; k = max(5, int(12.0 / (s[-1] / (len(H) - 1))) | 1); w = np.clip((s[-1] - s - 6.0) / 6.0, 0, 1)[:, None]; return w * savgol_filter(H, k, 3, axis=0) + (1 - w) * H
def resample(P, n): s = np.r_[0, np.cumsum(np.hypot(*np.diff(P, axis=0).T))]; f = np.linspace(0, s[-1], n); return np.c_[np.interp(f, s, P[:, 0]), np.interp(f, s, P[:, 1])]
out = {"frame": "plane of each rocker's outer side face (work/parts/rocker{L,R}/o_plane.json, as parts/rocker_profile.json): u along the rocker (front positive), v up, mm",
       "method": "per-photo orthophotos of each end on the face plane at 0.25 mm per pixel (tools/rocker_ends/ortho.py). trace.py, round 0: the side face grown from points picked by eye in one photo, that outline "
                 "placed in every photo (slide of up to 10 mm) and snapped to where the colour stops being the face's. Round 1: the photos slid onto each other by round 0, the median over photos of "
                 "'unlike the face' taken and its outline used as the seed (marks on the face that reach the edge bridged by hand), placed and snapped again. fit.py: photos slid onto each other (pose error at the "
                 "chair's ends, two numbers per photo), points dropped where a camera looks onto the neighbouring surface, median over photos. Inputs: tools/rocker_ends/inputs/seeds.json.",
       "caveats": ["the top edge is the tone edge between the lit top face and the side face; on an eased arris it reads a little below the true top surface, and the bottom silhouette a little above the true underside (radius not measured)",
                   "the ends are modelled square across the rocker's width; any rounding in plan view is not modelled",
                   "each photo is slid, not turned; where an end sits along the rocker is known to about 1 mm per side (median of the photos' slides)"],
       "left": {}, "right": {}}
SIDE = {"L": "left", "R": "right"}; A = {}
for key, t in T.items():
    S, end = key.split("_"); P, s, n, mad, photos, few, br = consensus(t); it = landmark(P, end); used = [p for p, v in photos.items() if v["used"]]
    sl = np.array([photos[p]["slide_u_v_mm"] for p in used]); rm = [photos[p]["rms_after_slide_mm"] for p in used]
    Pa = P if S == "L" else rigid(P)
    A[key] = {"P": Pa, "it": it}
    out[SIDE[S]][end] = {"outline_uv": P.round(2).tolist(), "landmark_uv": P[it].round(2).tolist(), "landmark": "tip (rearmost point)" if end == "tail" else "top corner",
                         "extreme_u": round(float(P[:, 0].min() if end == "tail" else P[:, 0].max()), 2), "photos_per_point": {"min": int(n.min()), "median": int(np.median(n))},
                         "spread_between_photos_mm": {"median": round(float(np.nanmedian(mad)), 2), "p90": round(float(np.nanpercentile(mad, 90)), 2)},
                         "share_of_outline_seen_by_fewer_than_3_photos": round(float(few.mean()), 3), "photos": photos,
                         "photo_slides_mm": {"sd_u": round(float(sl[:, 0].std()), 2), "sd_v": round(float(sl[:, 1].std()), 2), "max": round(float(np.abs(sl).max()), 2)}, "provenance": "triangulated (one plane, %d photos)" % len(used)}
    runs = [[round(float(P[a, 0]), 1), round(float(P[a, 1]), 1), round(float(s[b] - s[a]), 1)] for a, b in zip(np.where(np.diff(np.r_[0, few.astype(int)]) == 1)[0], np.where(np.diff(np.r_[few.astype(int), 0]) == -1)[0])]
    out[SIDE[S]][end]["stretches_bridged_fewer_than_3_photos_u_v_length"] = runs; print("  bridged (u, v, length):", runs)
    out[SIDE[S]][end]["bridged_by_hand_mm"] = round(float(br.sum() * 0.5), 1); out[SIDE[S]][end]["bridged_by_hand"] = SEEDS[key].get("bridge_note", "") if br.any() else ""
    print(f"{key}: {len(used)} photos used of {len(photos)}; slides sd u {sl[:, 0].std():.2f} v {sl[:, 1].std():.2f} max {np.abs(sl).max():.2f}; rms after slide {min(rm):.2f}-{max(rm):.2f}; spread between photos median {np.nanmedian(mad):.2f} p90 {np.nanpercentile(mad, 90):.2f}; "
          f"photos per point min {n.min()} median {int(np.median(n))}; landmark {P[it].round(1).tolist()} extreme u {out[SIDE[S]][end]['extreme_u']}")
# ---- design: each side's end is set on the existing profile, then left and right are averaged
# The SHAPE of an end is known to a few tenths of a mm, its PLACE in the face plane only to 1-2 mm (the photos' pose error at the chair's ends,
# see photo_slides_mm). parts/rocker_profile.json has the same weakness but is what the legs stand on, so each end is slid square to its
# top edge (one number) until its TOP edge lies on mean_top over REG, the stretch where both exist and the old top edge is good.
REG = {"tail": (-430.0, -318.0), "nose": (571.0, 606.0)}; BL = {"tail": (-330.0, -400.0), "nose": (572.0, 590.0)}; CUT = {"tail": -316.0, "nose": 570.0}; design = {}; N1 = 400; AWAY = 15.0
old = lambda k, u: np.interp(u, U, RP[k]); slope_top = np.gradient(np.array(RP["mean_top"]), U)
def register(P, it, end):
    lo, hi = REG[end]; d = np.zeros(2)
    for _ in range(5):
        top = P[:it + 1] + d; m = (top[:, 0] >= lo) & (top[:, 0] <= hi); a = np.interp(top[m, 0], U, slope_top); h = np.hypot(1, a); nrm = np.c_[-a, np.ones(m.sum())] / h[:, None]
        r = (top[m, 1] - old("mean_top", top[m, 0])) / h; nb = nrm.mean(0); nb /= np.linalg.norm(nb); d -= r.mean() * nb          # one number: across the edge. Along the edge the end stays where the photos put it
    top = P[:it + 1] + d; m = (top[:, 0] >= lo) & (top[:, 0] <= hi); r0 = P[:it + 1][m, 1] - old("mean_top", P[:it + 1][m, 0]); r = top[m, 1] - old("mean_top", top[m, 0])
    return d, float(np.sqrt(np.mean(r0 ** 2))), float(np.sqrt(np.mean(r ** 2)))
def cut(P, uc, end):
    """P runs from the inner end outward; start it exactly at u = uc"""
    inside = P[:, 0] > uc if end == "tail" else P[:, 0] < uc; i = int(np.argmin(inside)); f = (uc - P[i - 1, 0]) / (P[i, 0] - P[i - 1, 0]); return np.r_[[P[i - 1] + f * (P[i] - P[i - 1])], P[i:]]
for end in ("tail", "nose"):
    halves = {}; reg = {}; lm = []
    for S in "LR":
        P, it = A[f"{S}_{end}"]["P"], A[f"{S}_{end}"]["it"]; d, r0, r1 = register(P, it, end); A[f"{S}_{end}"]["Preg"] = P + d; lm.append(P[it] + d)
        reg[SIDE[S]] = {"slide_u_v_mm": d.round(2).tolist(), "top_edge_off_mean_top_before_mm_rms": round(r0, 2), "after_mm_rms": round(r1, 2)}
        out[SIDE[S]][end]["set_on_existing_profile"] = reg[SIDE[S]]
    for part in ("top", "bot"):
        seg = []
        for S in "LR":
            P, it = A[f"{S}_{end}"]["Preg"], A[f"{S}_{end}"]["it"]; seg.append(resample(cut(P[:it + 1] if part == "top" else P[it:][::-1], CUT[end], end), N1))      # both run from u = CUT to the landmark
        raw = (seg[0] + seg[1]) / 2; halves[part] = fair(raw); halves[part + "_faired_by"] = np.hypot(*(halves[part] - raw).T); halves[part + "_L"], halves[part + "_R"] = seg
        sa = np.r_[0, np.cumsum(np.hypot(*np.diff(seg[0], axis=0).T))]; halves[part + "_LR_gap"] = near(seg[0], seg[1])[sa < sa[-1] - AWAY]      # shape: between the outlines, away from the landmark (there the difference is where the end stops)
    u0, u1 = BL[end]; new = {}; join = {}
    for part, k in (("top", "mean_top"), ("bot", "mean_bot")):
        H = halves[part]; w = np.clip((H[:, 0] - u0) / (u1 - u0), 0, 1); i1 = int(np.argmax(w >= 1)); single = np.arange(len(H)) <= i1 + 2     # up to the end of the blend zone the outline is single-valued in u
        d = H[:, 1] - old(k, H[:, 0]); zone = single & (w > 0) & (w < 1); pre = single & (w == 0)
        join[part] = {"new_minus_old_v_mm": {"inward_of_blend": round(float(d[pre].mean()), 2), "in_blend_zone_mean": round(float(d[zone].mean()), 2), "in_blend_zone_min": round(float(d[zone].min()), 2), "in_blend_zone_max": round(float(d[zone].max()), 2)}}
        v = np.where(single, w * H[:, 1] + (1 - w) * old(k, H[:, 0]), H[:, 1]); keep = w > 0; i0 = int(np.argmax(keep)); new[part] = np.r_[[[u0, float(old(k, u0))]], np.c_[H[keep, 0], v[keep]]]
        sg = -1 if end == "tail" else 1; j = int(np.argmax(np.diff(sg * H[:, 0]) <= 0)) or len(H) - 1; table = {int(uu): round(float(np.interp(sg * uu, sg * H[:j, 0], d[:j])), 2) for uu in (np.arange(-320, -481, -20) if end == "tail" else np.arange(572, 621, 6)) if sg * uu <= sg * H[j - 1, 0]}
        join[part]["new_minus_old_v_mm_at_u"] = table; print(f"  {end} {part}: new - old v at u", table)
    design[end] = {"top": new["top"].round(2).tolist(), "bot": new["bot"].round(2).tolist(), "landmark_uv": ((lm[0] + lm[1]) / 2).round(2).tolist(), "landmark_left_right_uv": [lm[0].round(2).tolist(), lm[1].round(2).tolist()],
                   "set_on_existing_profile": reg, "blend_u": [u0, u1], "meets_old_profile": join,
                   "left_right_shape_gap_mm": {"note": "distance between the left and right outlines (each set on the profile), more than %g mm from the landmark; the design is their average, so each side is half of this from it" % AWAY,
                                               **{p: {"mean": round(float(halves[p + "_LR_gap"].mean()), 2), "max": round(float(halves[p + "_LR_gap"].max()), 2)} for p in ("top", "bot")}},
                   "left_right_landmark_difference_uv_mm": (lm[1] - lm[0]).round(2).tolist(), "faired_by_mm_max": {p: round(float(halves[p + "_faired_by"].max()), 2) for p in ("top", "bot")},
                   "provenance": "triangulated (one plane per side; left and right averaged); place along and across the rocker: fitted to parts/rocker_profile.json", "tol_mm": 1.6}
    A[end] = halves
    print(f"design {end}: landmark {design[end]['landmark_uv']} (L {lm[0].round(1).tolist()} R {lm[1].round(1).tolist()}); set on the profile: {json.dumps(reg)}; L/R shape gap top mean {halves['top_LR_gap'].mean():.2f} max {halves['top_LR_gap'].max():.2f}, bot mean {halves['bot_LR_gap'].mean():.2f} max {halves['bot_LR_gap'].max():.2f}; landmark R - L {(lm[1] - lm[0]).round(2).tolist()}; faired by max {design[end]['faired_by_mm_max']}; meets old profile:", json.dumps(join))
design["note"] = ("left side-plane frame with the right rocker carried onto the left (parts/rocker_profile.json right_vs_left), i.e. the frame of mean_top / mean_bot. Each side's end was first slid onto "
                  "mean_top ('set_on_existing_profile': the end's shape is measured, its place is the existing profile's), then left and right were averaged point by point. Each end: 'top' and 'bot' run from "
                  "blend_u[0] (where they equal the old profile) to the landmark; between blend_u[0] and blend_u[1] old and new are mixed linearly; beyond, the new outline alone. "
                  "The rocker's outline = mean_top from the tail's blend_u[0] to the nose's blend_u[0], the nose's top to its corner, the nose's bot back, mean_bot, the tail's bot out to the tip, the tail's top back.")
out["design"] = design
out["as_averaged"] = {"note": "the two outlines that were averaged, in the design frame (each already slid onto mean_top), from u = %s (tail) / %s (nose) to the landmark" % (CUT["tail"], CUT["nose"]),
                      **{end: {side: {p: A[end][p + "_" + side[0].upper()][::2].round(2).tolist() for p in ("top", "bot")} for side in ("left", "right")} for end in ("tail", "nose")}}
json.dump(out, open(outf, "w"), indent=1); print("wrote", outf)
