"""USAGE: python3 -I tools/edge_radii/band.py PROFILE.json PXMM WOOD_T0 WOOD_T1 SIL_T0 SIL_T1
Phase 6c: width of the tone band of an eased arris on a profile written by prof.py.
  plateau  = median L* of the flat face, t in [WOOD_T0, WOOD_T1] (px)
  silhouette = steepest step of L* (Lab gradient) for t in [SIL_T0, SIL_T1] (where the wood meets what is behind it)
  band     = from the silhouette back toward the face, to the last place where |L* - plateau| is still >= 10 % (B10) / 50 %
             (B50) of the band's extreme |L* - plateau| (taken between the face window and 2 px short of the silhouette, so the step itself does not count)
Prints B10 and B50 in px and mm (PXMM = native px per mm at that edge, from the tape), the band's sign (highlight or
shade), its contrast, and the blur (FWHM of the silhouette step's gradient, the resolution of the band widths). Geometry (see the README): a round of radius r on a square arris seen square to the face shows its
whole round as a band r wide between the tangent line and the silhouette; the tone only departs visibly from the face's
some way into the round, so r >= B10, and r <= B10 / (1 - sin 30 deg) = 2 B10 if the tone departs within 30 deg of the face."""
import sys, json

d = json.load(open(sys.argv[1])); pxmm = float(sys.argv[2])
w0, w1, s0, s1 = map(float, sys.argv[3:7])
t, L, g = d["t"], d["L"], d["grad"]
pl = sorted(L[i] for i in range(len(t)) if w0 <= t[i] <= w1); pl = pl[len(pl) // 2]
cand = [i for i in range(len(t)) if s0 <= t[i] <= s1]
isil = max(cand, key=lambda i: g[i]); tsil = t[isil]
lo, hi = (min(w1, tsil), max(w1, tsil)) if w1 < tsil else (min(w0, tsil), max(w0, tsil))
inner = [i for i in range(len(t)) if lo <= t[i] <= hi and abs(t[i] - tsil) >= 2.0]   # wood side, off the step itself
iext = max(inner, key=lambda i: abs(L[i] - pl)); ext = L[iext] - pl
step = -1 if tsil > w1 else 1          # walk from the silhouette toward the face


def back_to(frac):
    i = iext
    while 0 <= i + step < len(t) and lo <= t[i + step] <= hi and abs(L[i + step] - pl) >= frac * abs(ext):
        i += step
    return t[i]


r10, r50 = back_to(0.10), back_to(0.50)
a_ = b_ = isil                          # blur: full width at half maximum of the silhouette's gradient peak
while a_ > 0 and g[a_ - 1] >= 0.5 * g[isil]: a_ -= 1
while b_ < len(t) - 1 and g[b_ + 1] >= 0.5 * g[isil]: b_ += 1
fw = t[b_] - t[a_]
B10, B50 = abs(tsil - r10), abs(tsil - r50)
print(json.dumps(dict(profile=sys.argv[1], pxmm=pxmm, plateau_L=round(pl, 1), silhouette_t=tsil, extreme_t=t[iext],
                      extreme_dL=round(ext, 1), kind="highlight" if ext > 0 else "shade", t10=r10, t50=r50,
                      step_fwhm_px=fw, step_fwhm_mm=round(fw / pxmm, 2), B10_px=round(B10, 2), B50_px=round(B50, 2), B10_mm=round(B10 / pxmm, 2), B50_mm=round(B50 / pxmm, 2),
                      r_bracket_mm=[round(B10 / pxmm, 2), round(2 * B10 / pxmm, 2)])))
