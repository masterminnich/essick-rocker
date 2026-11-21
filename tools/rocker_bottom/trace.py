"""USAGE: work/toolkit/rk.sh tools/rocker_bottom/trace.py RIBBONDIR OUT.json [SEEDS.json tools/rocker_bottom/inputs/seeds.json]
Step 2 of 3 (ribbon -> trace -> fit). The top and bottom arris of each rocker's outer side face in every photo's ribbon
(tools/rocker_bottom/ribbon.py), at stations every 1 mm along u, as t = distance square to the side's own top edge in
parts/rocker_profile.json. Per photo and station (the ribbon averaged over 1 mm along u):
 face    - the face's colour (Lab, mean and covariance) from the rows inside the face, t -7..-19, over +-25 mm along the rocker; "unlike the
           face" = Mahalanobis distance to it (as tools/rocker_ends/trace.py).
 place   - the photo's pose error moves both edges together by up to several mm; per 50 mm block the shift that puts the most rise of
           "unlike the face" on the two seeded edges (see the code), median over 3 blocks; seeds, bands and face rows follow it.
 edges   - BOTH edges the same way: walking outward from inside the face (8 mm in from the seed), the first place where "unlike the face"
           (clamped at 8) passes LEVEL (5, as the rocker ends' median cut in PR #23) and stays above it; sub-row crossing, then moved within
           0.4 mm to where the colour itself changes fastest. So an edge is where the FACE stops: at the top the tone edge to the lit top
           face (or what lies behind), at the bottom the tone edge to the table, the floor, or (near where the rocker stands on the table)
           the black gap under the rocker. Dead end, kept for the record: a two-class rule (face vs what lies beyond) put the bottom on the
           far side of that black gap, 1-4 mm too low near the contact.
 kept    - inside the band, "unlike" <= 3.5 on average 1-3 mm inside and >= 6 at 0.4-1.2 mm beyond, and (bottom only) the camera does not
           look onto the underside there: a camera below the bottom edge's tangent sees the underside as a strip beyond the arris,
           WIDTH * (camera - point).normal / camera height wide; > 0.3 mm = dropped (as fit.py of the rocker ends). Photos listed in SEEDS
           "drop" are not used.
Output per side: u (stations), and per photo: top_t, bot_t (NaN where not found), top_ok, bot_ok, separations, and the camera's place.
CHECK the points by eye on single photos: tools/rocker_bottom/view.py ... OUT.json. Tiny compute (small images, seconds per photo)."""
import sys, json, cv2, numpy as np
d, outf = sys.argv[1:3]; SEEDS = json.load(open(sys.argv[3] if len(sys.argv) > 3 else "tools/rocker_bottom/inputs/seeds.json"))
R = json.load(open(f"{d}/ribbons.json")); g = R["grid"]; us = np.arange(g["u0"], g["u1"] + 1e-9, g["du"]); ts = np.arange(g["t1"], g["t0"] - 1e-9, -g["dt"])
WIDTH, STRIP_MAX, LEVEL, FACE = 31.0, 0.3, SEEDS.get("level", 5.0), (-7.0, -19.0); LEVEL_BOT = SEEDS.get("level_bot", LEVEL); CAM_V_MIN = SEEDS.get("cam_v_min", 30.0)
ST = np.arange(np.ceil(g["u0"]) + 1, g["u1"] - 1 + 1e-9, 1.0); OUT = {"note": __doc__.split("\n")[1], "grid": g, "seeds": SEEDS}
row = lambda t: (g["t1"] - np.asarray(t, float)) / g["dt"]
def corr(S, key, u):
    """per-stretch correction of the seed, picked by eye (seeds.json [S][key] = [[u, dt], ...], linear between, constant beyond)"""
    c = SEEDS.get(S, {}).get(key, []); return np.interp(u, [p[0] for p in c], [p[1] for p in c]) if c else np.zeros_like(u)
for S in "LR":
    side = R["sides"][S]; s5 = us[::20]; seed_b = np.interp(ST, s5, side["seed_bottom_t"]) + corr(S, "bot", ST); seed_t = corr(S, "top", ST)
    top_v = np.interp(ST, s5, side["top_v"]); a = np.gradient(top_v, ST); nn = np.c_[-a, np.ones_like(a)] / np.hypot(1, a)[:, None]
    BT, BB = SEEDS.get("band_top", 3.0), SEEDS.get("band_bot", 4.0); res = {"u": ST.tolist(), "seed_bot_t": seed_b.round(2).tolist(), "seed_top_t": seed_t.round(2).tolist(), "photos": {}}
    for ph, info in side["photos"].items():
        if ph in SEEDS.get("drop", []): continue
        im = cv2.imread(f"{d}/{S}_{ph}.png"); valid = im.sum(2) > 0
        lab = cv2.cvtColor(cv2.GaussianBlur(im, (0, 0), 1.0), cv2.COLOR_BGR2LAB).astype(np.float32)
        # average over 1 mm along u: one column per station
        cols = np.clip(np.round((ST - g["u0"]) / g["du"]).astype(int), 2, len(us) - 3); L = np.mean([lab[:, cols + k] for k in (-2, -1, 0, 1, 2)], 0)       # (rows, stations, 3)
        V = np.all([valid[:, cols + k] for k in (-2, -1, 0, 1, 2)], 0)
        seen = np.interp(ST, s5, info["seen_5mm"]) > 0.99
        # place: the photo's pose error moves both edges together by up to several mm (IMG_1488: 4.5 mm), more than the bands. Per 50 mm block,
        # the shift dt (-8..8 mm) that puts the most rise of "unlike the face" on the seeded top (going up) AND bottom (going down) edges;
        # median over 3 neighbouring blocks; the seeds, bands and face rows then follow it.
        PL = np.arange(-8.0, 8.0 + 1e-9, 0.2); bs = np.arange(0, len(ST), 50); shb = np.full(len(bs), np.nan); fr0 = (ts <= -10.0) & (ts >= -16.0)
        for q, b0 in enumerate(bs):
            j = np.arange(b0, min(b0 + 50, len(ST))); j = j[seen[j] & V.all(0)[j]]
            if len(j) < 15: continue
            F = L[fr0][:, j].reshape(-1, 3); mu = F.mean(0); Ci = np.linalg.inv(np.cov((F - mu).T) + 9.0 * np.eye(3)); x = L[:, j] - mu
            Dm = np.minimum(np.sqrt(np.einsum("rjk,kl,rjl->rj", x, Ci, x)), 8.0); gD = -np.gradient(Dm, g["dt"], axis=0)
            rt = np.clip(np.round(row(seed_t[j][None] + PL[:, None])).astype(int), 0, len(ts) - 1); rb = np.clip(np.round(row(seed_b[j][None] + PL[:, None])).astype(int), 0, len(ts) - 1)
            sc = (np.clip(gD[rt, np.arange(len(j))[None]], 0, 3) + np.clip(-gD[rb, np.arange(len(j))[None]], 0, 3)).mean(1); shb[q] = PL[int(np.argmax(sc))]
        if np.isfinite(shb).any():
            shb = np.interp(np.arange(len(bs)), np.where(np.isfinite(shb))[0], shb[np.isfinite(shb)]); shb = np.array([np.median(shb[max(0, q - 1):q + 2]) for q in range(len(bs))])
        else: shb = np.zeros(len(bs))
        shift = np.interp(ST, ST[bs] + 25.0, shb); seed_t_p = seed_t + shift; seed_b_p = seed_b + shift
        fr = (ts <= FACE[0]) & (ts >= FACE[1]); top_t = np.full(len(ST), np.nan); bot_t = np.full(len(ST), np.nan); top_ok = np.zeros(len(ST), bool); bot_ok = np.zeros(len(ST), bool)
        sep_t = np.zeros(len(ST)); sep_b = np.zeros(len(ST)); under = np.zeros(len(ST), bool)
        C = np.array([info["cam_u"], info["cam_v"]]); Pb = np.c_[ST, top_v] + seed_b_p[:, None] * nn; strip = WIDTH * ((C - Pb) * (-nn)).sum(1) / info["cam_height"]; under = strip > STRIP_MAX
        for blk in range(0, len(ST), 20):
            j = np.arange(blk, min(blk + 20, len(ST))); w = np.arange(max(0, blk - 15), min(len(ST), blk + 35))
            if not seen[j].any(): continue
            fr = (ts <= FACE[0] + shift[j].mean()) & (ts >= FACE[1] + shift[j].mean()); F = L[fr][:, w].reshape(-1, 3); Fv = V[fr][:, w].reshape(-1)
            if Fv.sum() < 200: continue
            F = F[Fv]; mu = F.mean(0); Ci = np.linalg.inv(np.cov((F - mu).T) + 9.0 * np.eye(3))
            for i in j:
                if not seen[i] or not V[:, i].all(): continue
                x = L[:, i] - mu; Dc = np.minimum(np.sqrt(np.einsum("rk,kl,rl->r", x, Ci, x)), 8.0); cg = np.linalg.norm(np.gradient(L[:, i], g["dt"], axis=0), axis=1)
                for key, r_from, r_lim, stp, lo, hi in (("top", row(seed_t_p[i] - 8.0), row(seed_t_p[i] + BT + 1.0), -1, seed_t_p[i] - BT, seed_t_p[i] + BT),
                                                        ("bot", row(seed_b_p[i] + 8.0), row(seed_b_p[i] - BB - 1.0), 1, seed_b_p[i] - BB, seed_b_p[i] + BB)):
                    r, hit = int(round(r_from)), None
                    lev = LEVEL if key == "top" else LEVEL_BOT
                    while 2 <= r < len(ts) - 3 and (r - r_lim) * stp < 0:
                        if Dc[r - stp] < lev and Dc[r] >= lev and Dc[r + stp] >= lev and Dc[r + 2 * stp] >= lev: hit = r; break
                        r += stp
                    if hit is None: continue
                    rc = (hit - stp) + stp * (lev - Dc[hit - stp]) / (Dc[hit] - Dc[hit - stp])          # sub-row crossing
                    cand = np.arange(max(0, int(round(rc)) - 2), min(len(ts), int(round(rc)) + 3)); kc = cand[np.argmax(cg[cand])]; tt = float(ts[kc])
                    ins = Dc[np.clip(np.arange(int(rc) - 15 * stp, int(rc) - 5 * stp, stp), 0, len(ts) - 1)].mean(); bey = Dc[np.clip(np.arange(int(rc) + 2 * stp, int(rc) + 6 * stp, stp), 0, len(ts) - 1)].mean()
                    ok = ins <= lev - 1.5 + 0.5 * (key == "bot") and bey >= lev + 1.0 and lo < tt < hi
                    if key == "top": top_t[i], top_ok[i], sep_t[i] = tt, ok, bey - ins
                    else: bot_t[i], bot_ok[i], sep_b[i] = tt, ok and not under[i] and info["cam_v"] >= CAM_V_MIN, bey - ins
        res["photos"][ph] = {"top_t": [None if not np.isfinite(v) else round(float(v), 3) for v in top_t],
                             "bot_t": [None if not np.isfinite(v) else round(float(v), 3) for v in bot_t], "top_ok": top_ok.astype(int).tolist(), "bot_ok": bot_ok.astype(int).tolist(),
                             "sep_top": sep_t.round(2).tolist(), "sep_bot": sep_b.round(2).tolist(), "looks_onto_underside": under.astype(int).tolist(),
                             "cam_u_v_height": [info["cam_u"], info["cam_v"], info["cam_height"]], "placed_shift_t": shift.round(2).tolist()}
        print(S, ph, "shift %s" % np.round(shb, 1).tolist(), "top kept %d bot kept %d of %d seen (under %d)" % (top_ok.sum(), bot_ok.sum(), seen.sum(), (under & seen).sum()), flush=True)
    OUT[S] = res
json.dump(OUT, open(outf, "w"))
