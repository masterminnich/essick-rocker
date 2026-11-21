"""USAGE: work/toolkit/rk.sh tools/rocker_ends/trace.py ORTHODIR OUT.json [BAND_MM 2.5] [PRIOR.json] [LEVEL 5]
Step 2 of 3 (ortho -> trace -> fit). Outline of the outer side face at each rocker end, in every orthophoto.
 seed   - in the seed photo (tools/rocker_ends/inputs/seeds.json; the squarest view) the side face is grown from points picked by eye
          inside it: pixels whose colour is like the face's (Mahalanobis distance in Lab to the picked patches), the connected piece
          holding the first point; its outline beyond u_inner, smoothed over 2 mm, is the seed. CHECK IT BY EYE (zoom.py ... OUT.json).
 place  - before snapping, the seed is slid as a whole onto each photo (photos sit up to 7 mm apart at the chair's ends, more than the band):
          the slide within 10 mm, in 0.5 mm steps, that puts most of the outline on a rise of "unlike the face", the points that face
          along the rocker (the tip, the nose's end) counting for more, so that the ends land on each other. fit.py refines it.
          The face's colour is then read again from the picked patches slid the same way.
 snap   - in every photo: along the seed's normal, within +-BAND_MM, the place where "unlike the face" rises fastest going outward
          (each photo with its own face colour from the same patches): that says WHICH edge is the face's. Its place is then moved, within
          1 mm, to where the colour itself changes fastest (the half-way point of the blurred step). Kept with its strength (rise of
          "unlike" per mm); weak = wood behind wood; points whose refinement ran to the 1 mm limit are flagged like points at the band's edge.
 again  - with PRIOR.json (the output of tools/rocker_ends/fit.py on a first trace) the seed is no longer one photo's outline (which has
          bumps of its own, up to 4 mm: glare, grain, shadow) but the outline of the ALL-PHOTO MEDIAN of "unlike the face": every photo
          slid back by its own slide from that fit, the median taken pixel by pixel, the face grown in it as in the seed photo. Only photos
          that see the end of the rocker as a silhouette go into the median (camera above the rocker and not beyond its end: see fit.py).
          Marks on the face that reach its edge are bridged in that seed (seeds.json "bridge"). Run trace -> fit -> trace PRIOR -> fit.
          LEVEL = the value of "unlike" (clamped at 8) where the median is cut. 5 and not lower: an eased arris reads as a paler band 1-2 mm wide inside
          the silhouette (the bottom of the right tail), and a cut at 3.5 wanders through it. The median picture is written beside OUT.json (<OUT>_<end>_median.png) to look at.
Output per end: seed {top, bot} (top = the top arris to the tip, bot = the bottom arris / nose curve to the tip; both run from the chair
toward the end), s (arc length of the whole outline: top from the inner end to the tip, then bot back), snapped[photo] = offsets along
the outward normal (mm) and strengths. Tiny compute (small images, a few seconds)."""
import sys, json, cv2, numpy as np
d, outf = sys.argv[1:3]; BAND = float(sys.argv[3]) if len(sys.argv) > 3 else 2.5; PRIOR = json.load(open(sys.argv[4])) if len(sys.argv) > 4 else None
REFINE = 1.0; WIDTH, STRIP_MAX, TOP_NV, REACH = 31.0, 0.3, 0.7, 10.0; LEVEL = float(sys.argv[5]) if len(sys.argv) > 5 else 5.0; GR = np.mgrid[-REACH:REACH + 1e-9:0.5, -REACH:REACH + 1e-9:0.5].reshape(2, -1).T
W = json.load(open(f"{d}/windows.json")); SEEDS = json.load(open("tools/rocker_ends/inputs/seeds.json")); OUT = {}
def unlike(S, end, ph, inside, win, shift=(0.0, 0.0)):
    res = win["res_mm"]; U0, V1 = win["u_range"][0], win["v_range"][1]; im = cv2.imread(f"{d}/{S}_{end}_{ph}.png")
    lab = cv2.cvtColor(cv2.GaussianBlur(im, (0, 0), 1.0), cv2.COLOR_BGR2LAB).astype(np.float32); pix = []
    for u, v in np.asarray(inside, float) + np.asarray(shift, float):
        c, r = int(round((u - U0) / res)), int(round((V1 - v) / res))
        if 8 <= r < lab.shape[0] - 8 and 8 <= c < lab.shape[1] - 8: pix.append(lab[r - 8:r + 9, c - 8:c + 9].reshape(-1, 3))
    pix = np.vstack(pix); mu = pix.mean(0); C = np.cov((pix - mu).T) + 9.0 * np.eye(3); Ci = np.linalg.inv(C); x = lab - mu
    return np.sqrt(np.einsum("ijk,kl,ijl->ij", x, Ci, x)), lab
for key, sd in SEEDS.items():
    if key == "note": continue
    S, end = key.split("_"); win = W[key]; res = win["res_mm"]; U0, V1 = win["u_range"][0], win["v_range"][1]
    uv = lambda c, r: np.c_[U0 + np.asarray(c, float) * res, V1 - np.asarray(r, float) * res]
    def grow(m):
        """the face = the connected piece of mask m holding the first picked point; its outline beyond u_inner, starting on the top arris"""
        m = cv2.morphologyEx(m.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
        n, lb = cv2.connectedComponents(m); c0, r0 = int(round((sd["inside"][0][0] - U0) / res)), int(round((V1 - sd["inside"][0][1]) / res)); comp = (lb == lb[r0, c0]).astype(np.uint8)
        cs, _ = cv2.findContours(comp, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE); P = uv(cs[0][:, 0, 0], cs[0][:, 0, 1])
        beyond = P[:, 0] < sd["u_inner"] if sd["tip"] == "min" else P[:, 0] > sd["u_inner"]
        # the outline is a closed loop: rotate it to start at a point on the inner side, keep the run beyond u_inner that holds the tip
        i0 = int(np.argmax(~beyond)); P = np.roll(P, -i0, 0); beyond = np.roll(beyond, -i0); runs = []; a = None
        for i, b in enumerate(beyond):
            if b and a is None: a = i
            if (not b or i == len(beyond) - 1) and a is not None: runs.append((a, i)); a = None
        a, b = max(runs, key=lambda r: r[1] - r[0]); Q = P[a:b]
        return Q[::-1] if Q[0, 1] < Q[-1, 1] else Q                          # start on the top arris (higher v at the inner end)
    cen = np.mean(sd["inside"], 0); offs = np.arange(-BAND, BAND + 1e-9, 0.05); offs2 = np.arange(-BAND - REFINE, BAND + REFINE + 1e-9, 0.05)
    def fair(Q, k=None):
        """smooth over 2 mm, resample every 0.5 mm, outward normals"""
        k = k or int(round(2.0 / res)) | 1; pad = np.r_[np.repeat(Q[:1], k // 2, 0), Q, np.repeat(Q[-1:], k // 2, 0)]; Q = np.c_[np.convolve(pad[:, 0], np.ones(k) / k, "valid"), np.convolve(pad[:, 1], np.ones(k) / k, "valid")]
        s = np.r_[0, np.cumsum(np.hypot(*np.diff(Q, axis=0).T))]; sn = np.arange(0, s[-1], 0.5); Q = np.c_[np.interp(sn, s, Q[:, 0]), np.interp(sn, s, Q[:, 1])]
        t = np.gradient(Q, axis=0); t /= np.linalg.norm(t, axis=1)[:, None]; nrm = np.c_[t[:, 1], -t[:, 0]]; return Q, nrm * np.sign(np.sum((Q - cen) * nrm, 1).mean()), sn
    def bridge(Q, spans):
        """marks ON the face that reach its edge (a white scuff, finish worn off an arris) are not the outline: between the two points of each span
        (seeds.json 'bridge') the seed is replaced by the smooth curve that leaves and arrives along the outline's own direction. Returns the seed
        and which of its points were bridged (fit.py takes no snapped points there)."""
        flag = np.zeros(len(Q), bool)
        for p0, p1 in spans:
            i0, i1 = sorted((int(np.argmin(np.hypot(*(Q - p0).T))), int(np.argmin(np.hypot(*(Q - p1).T))))); m0 = Q[i0] - Q[i0 - 8]; m1 = Q[i1 + 8] - Q[i1]; L = np.linalg.norm(Q[i1] - Q[i0]); m0, m1 = L * m0 / np.linalg.norm(m0), L * m1 / np.linalg.norm(m1)
            t = np.linspace(0, 1, int(L / 0.25) + 2)[:, None]; B = (2 * t ** 3 - 3 * t ** 2 + 1) * Q[i0] + (t ** 3 - 2 * t ** 2 + t) * m0 + (-2 * t ** 3 + 3 * t ** 2) * Q[i1] + (t ** 3 - t ** 2) * m1
            Q = np.r_[Q[:i0], B, Q[i1 + 1:]]; flag = np.r_[flag[:i0], np.ones(len(B), bool), flag[i1 + 1:]]
        s = np.r_[0, np.cumsum(np.hypot(*np.diff(Q, axis=0).T))]; Q, nrm, sn = fair(Q, 1); return Q, nrm, sn, np.interp(sn, s, flag.astype(float)) > 0.5
    def uweight(nrm):
        """weights that make the outline say as much about its place ALONG the rocker as across it. A tail is two long edges 8 degrees apart and a
        tip of ten points: unweighted, its place along the rocker is anybody's guess within 3 mm and the tips of the photos do not land on each other"""
        a, b = nrm[:, 0] ** 2, nrm[:, 1] ** 2; den = (a * a).sum() - (a * b).sum(); return 1 + (min(100.0, max(0.0, (b.sum() - a.sum()) / den)) if den > 1e-6 else 100.0) * a
    def place(Q, nrm, Dp, ph):
        """where the outline sits in this photo: the slide (within REACH mm, 0.5 mm steps) that puts most of the outline on a rise of 'unlike the face'.
        Points where this camera looks onto the neighbouring surface (see fit.py) do not vote."""
        w = win["photos"][ph]; C = np.array([w["cam_u"], w["cam_v"]], float); ok = ~((WIDTH * ((C - Q) * nrm).sum(1) / w["cam_height"] > STRIP_MAX) & (nrm[:, 1] < TOP_NV))
        gy, gx = np.gradient(Dp.astype(np.float32)); X = Q[ok][None] + GR[:, None, :]; mx = ((X[..., 0] - U0) / res).astype(np.float32); my = ((V1 - X[..., 1]) / res).astype(np.float32)
        g = (cv2.remap(gx, mx, my, cv2.INTER_LINEAR) * nrm[ok, 0] - cv2.remap(gy, mx, my, cv2.INTER_LINEAR) * nrm[ok, 1]) / res; wt = uweight(nrm)[ok]; sc = (np.clip(g, 0, 3) * wt).sum(1) / wt.sum(); return GR[sc.argmax()], float(sc.max()), float(sc[len(GR) // 2])
    def snap(Q, nrm, ph, shift=None):
        D, lab = unlike(S, end, ph, sd["inside"], win); Dp = cv2.GaussianBlur(np.minimum(D, 8.0), (0, 0), 1.2); score = None
        if shift is None:
            shift, *score = place(Q, nrm, Dp, ph); D, lab = unlike(S, end, ph, sd["inside"], win, shift); Dp = cv2.GaussianBlur(np.minimum(D, 8.0), (0, 0), 1.2)
        shift = np.asarray(shift, float); Q = Q + shift; X = Q[:, None, :] + offs[None, :, None] * nrm[:, None, :]
        mx = ((X[..., 0] - U0) / res).astype(np.float32); my = ((V1 - X[..., 1]) / res).astype(np.float32); prof = cv2.remap(Dp, mx, my, cv2.INTER_LINEAR)
        g = np.gradient(prof, 0.05, axis=1); j = g.argmax(1); o1 = offs[j]; edge = (j < 3) | (j > len(offs) - 4)
        # which edge is now known; its PLACE is where the colour itself changes fastest (the half-way point of the blurred step), looked for within
        # REFINE mm. The rise of "unlike" alone sits at the inner foot of the blur: 0.2-0.6 mm inside the wood on every edge (measured, LEDGER).
        lab = cv2.GaussianBlur(lab, (0, 0), 0.8); X = Q[:, None, :] + offs2[None, :, None] * nrm[:, None, :]; mx = ((X[..., 0] - U0) / res).astype(np.float32); my = ((V1 - X[..., 1]) / res).astype(np.float32)
        gc = np.linalg.norm(np.gradient(np.stack([cv2.remap(np.ascontiguousarray(lab[..., c]), mx, my, cv2.INTER_LINEAR) for c in range(3)], -1), 0.05, axis=1), axis=2)
        o2 = offs2[np.where(np.abs(offs2[None, :] - o1[:, None]) <= REFINE, gc, -1.0).argmax(1)]
        return o2 + nrm @ shift, g[np.arange(len(j)), j], edge | (np.abs(o2 - o1) > REFINE - 0.075), shift, score        # offsets are always from the unshifted seed
    if PRIOR:
        pr = PRIOR["left" if S == "L" else "right"][end]; M = []; inmed = []
        for ph, v in pr["photos"].items():
            w = win["photos"][ph]; past_end = w["cam_u"] > pr["extreme_u"] - 25 if sd["tip"] == "max" else w["cam_u"] < pr["extreme_u"] + 10
            if not v["used"] or past_end or w["cam_v"] < 250: continue
            sh = np.array(v["slide_u_v_mm"]); D, _ = unlike(S, end, ph, sd["inside"], win, sh); A = np.float32([[1, 0, sh[0] / res], [0, 1, -sh[1] / res]]); inmed.append(ph)
            M.append(cv2.warpAffine(np.minimum(D, 8.0), A, (D.shape[1], D.shape[0]), flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP, borderValue=8.0))      # the photo slid back: median frame x = photo x + slide
        M = cv2.GaussianBlur(np.median(M, 0), (0, 0), 1.0); cv2.imwrite(f"{outf[:-5]}_{key}_median.png", np.clip(M * 31.875, 0, 255).astype(np.uint8)); Q, nrm, sn = fair(grow(M < LEVEL)); Q, nrm, sn, bridged = bridge(Q, sd.get("bridge", []))
    else:
        if "hand" in sd: Q = np.array(sd["hand"]["top"] + sd["hand"]["bot"][::-1][1:], float); s0 = np.r_[0, np.cumsum(np.hypot(*np.diff(Q, axis=0).T))]; sq = np.arange(0, s0[-1], res); Q = np.c_[np.interp(sq, s0, Q[:, 0]), np.interp(sq, s0, Q[:, 1])]
        else: Q = grow(unlike(S, end, sd["photo"], sd["inside"], win)[0] < 3.0)
        Q, nrm, sn = fair(Q)
        # second pass: the seed photo's own snapped points (weak ones dropped, running median over 4 mm) become the seed for every photo
        o, g, e, _, _ = snap(Q, nrm, sd["photo"], (0.0, 0.0)); ok = (g >= 1.5) & ~e; o = np.interp(sn, sn[ok], o[ok]); o = np.array([np.median(o[max(0, i - 4):i + 5]) for i in range(len(o))]); Q, nrm, sn = fair(Q + o[:, None] * nrm)
    it = int(np.argmin(Q[:, 0]) if sd["tip"] == "min" else np.argmax(Q[:, 0])); snapped = {}
    if not PRIOR: bridged = np.zeros(len(Q), bool)
    for ph in win["photos"]:
        o, g, e, sh, sc = snap(Q, nrm, ph); snapped[ph] = {"off": o.round(2).tolist(), "strength": g.round(2).tolist(), "at_band_edge": e.astype(int).tolist(), "placed_u_v_mm": sh.tolist(), "placing_score_best_and_unslid": np.round(sc, 2).tolist()}
    OUT[key] = {"seed_photo": sd["photo"], "seed": {"top": Q[:it + 1].round(2).tolist(), "bot": Q[it:][::-1].round(2).tolist()}, "outline": Q.round(3).tolist(), "normal": nrm.round(4).tolist(), "s": sn.round(2).tolist(), "tip_index": it, "band_mm": BAND, "snapped": snapped, "bridged": bridged.astype(int).tolist()}
    if PRIOR: OUT[key]["seed_from_median_of"] = inmed
    print(key, "seed from", "the median of %d photos (%s)" % (len(inmed), " ".join(inmed)) if PRIOR else sd["photo"], "points", len(Q), "length %.0f mm" % sn[-1], "tip", Q[it].round(1).tolist(), "inner ends", Q[0].round(1).tolist(), Q[-1].round(1).tolist())
json.dump(OUT, open(outf, "w"))
