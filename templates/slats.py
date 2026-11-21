"""USAGE: tools/py.sh templates/slats.py [--stack-mm 10] [--lam-mm 2.5] [--out templates/out] [--geom-json templates/out/slats_geom.json]
Back slats, 1:1: (1) flat outlines of the centre slat and the outer slat (back face, unrolled along the bend; the slats bend in
one direction only, so the paper template wraps onto the bent blank exactly), (2) one two-part bending form (form + caul) for
all three slats, from parts/slats.json (edges = symmetric design fits in the unrolled back view; bend = the tabulated back-face
side profiles of the centre and outer slats, averaged), templates/slat_ends.json (seat ends read by eye) and parts/crest.json
(crest bottom face, for the top ends).
Frames: flat outline u = across the chair (+ = chair's right, seen from behind = back face up), v = arc length along the back
face (up). Bending form drawn upright as in the chair: x = chair Y (forward to the right), y = chair Z (up), mm.
Writes <out>/slat_template_*, <out>/slat_bending_form_* and a geometry json for templates/check_slat_overlay.py. Tiny compute."""
import json, argparse, subprocess, sys, os, numpy as np
from scipy.interpolate import UnivariateSpline
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tplkit as K
from tplkit import fmt, frac32

ap = argparse.ArgumentParser()
ap.add_argument("--stack-mm", type=float, default=10.0, help="glued stack = slat thickness (parts/slats.json thickness_mm, weak; M4)")
ap.add_argument("--lam-mm", type=float, default=2.5)
ap.add_argument("--out", default="templates/out"); ap.add_argument("--geom-json", default=None); ap.add_argument("--rev", default=None)
a = ap.parse_args()

def ghash(p):
    try: return subprocess.run(["git", "log", "-1", "--format=%h", "--", p], capture_output=True, text=True).stdout.strip() or "uncommitted"
    except Exception: return "?"
REV = a.rev or ghash("parts/slats.json")
SL = json.load(open("parts/slats.json")); SE = json.load(open("templates/slat_ends.json")); CR = json.load(open("parts/crest.json"))
SY = SL["symmetric"]; VR = SL["v_range"]; OFF = SL["set_offset_u_mm"]; JA = SE["joinery_allowance_mm"]

def edge(c, v):
    """design edge u(v): 4th-order fit inside v_range; below it held constant (edges run plumb to the seat on IMG_1502), above it
    carried on along the end tangent (the last 9 mm under the crest)"""
    v = np.asarray(v, float); c = np.asarray(c); d = np.polyder(c); out = np.polyval(c, np.clip(v, *VR))
    lo, hi = v < VR[0], v > VR[1]
    out[hi] += np.polyval(d, VR[1]) * (v[hi] - VR[1]); return out

def profile(key):
    tb = np.array(SL[key]["table"]); zz = np.linspace(tb[0, 0], tb[-1, 0], 6000); yy = np.interp(zz, tb[:, 0], tb[:, 1])
    s = np.r_[0, np.cumsum(np.hypot(np.diff(zz), np.diff(yy)))]
    t0 = np.array([yy[8] - yy[0], zz[8] - zz[0]]); t0 /= np.linalg.norm(t0)
    t1 = np.array([yy[-1] - yy[-9], zz[-1] - zz[-9]]); t1 /= np.linalg.norm(t1)
    def at(v):
        v = np.atleast_1d(np.asarray(v, float)); p = np.stack([np.interp(v, s, yy), np.interp(v, s, zz)], 1)
        lo, hi = v < 0, v > s[-1]
        p[lo] = np.array([yy[0], zz[0]]) + np.outer(v[lo], t0); p[hi] = np.array([yy[-1], zz[-1]]) + np.outer(v[hi] - s[-1], t1)
        return p
    return at, s

def crest_bottom(x):
    """crest bottom face at |x|: rear and front arris (y, z), design even polys"""
    E = CR["edges"]; ax = abs(x)
    ev = lambda c: sum(ck * ax ** (2 * k) for k, ck in enumerate(c))
    return np.array([ev(E["bottom_rear"]["design"]["y_even_poly"]), ev(E["bottom_rear"]["design"]["z_even_poly"])]), \
           np.array([ev(E["bottom_front"]["design"]["y_even_poly"]), ev(E["bottom_front"]["design"]["z_even_poly"])])

def top_v(at, x):
    R, F = crest_bottom(x); n = np.array([-(F - R)[1], (F - R)[0]])          # normal of the crest bottom strip
    vv = np.arange(650, 800, 0.05); side = (at(vv) - R) @ n; i = np.where(np.diff(np.sign(side)))[0][0]
    return float(vv[i])

atC, sC = profile("sheet_centre"); atO, sO = profile("sheet_outer")
half = lambda v: edge(SY["centre_half"], v); oin = lambda v: edge(SY["outer_in"], v); oout = lambda v: edge(SY["outer_out"], v)
vbC = SE["seat"]["centre_v"]; vbO = SE["seat"]["outer_v_in_out"]
vtC = top_v(atC, 0.0); vtO = top_v(atO, float(oin(np.array([720.]))[0] + oout(np.array([720.]))[0]) / 2)

def outline(left, right, vb_l, vb_r, vt, n=120):
    vl = np.linspace(vb_l, vt, n); vr = np.linspace(vt, vb_r, n)
    return np.vstack([np.stack([left(vl), vl], 1), np.stack([right(vr), vr], 1)])
negh = lambda v: -half(v)
outC = outline(negh, half, vbC[0], vbC[1], vtC); outO = outline(oin, oout, vbO[0], vbO[1], vtO)
def allowance(left, right, vb_l, vb_r, vt):
    ex = lambda v0, v1: np.linspace(v0, v1, 20)
    bot = [np.stack([left(ex(vb_l, vb_l - JA)), ex(vb_l, vb_l - JA)], 1), np.stack([right(ex(vb_r - JA, vb_r)), ex(vb_r - JA, vb_r)], 1)]
    top = [np.stack([left(ex(vt, vt + JA)), ex(vt, vt + JA)], 1), np.stack([right(ex(vt + JA, vt)), ex(vt + JA, vt)], 1)]
    return [np.vstack([bot[0], bot[1]]), np.vstack([top[0], top[1]])]

# ---------------- flat template ----------------
items = []
ST = np.arange(0, 701, 100)
for nm, o, (L, R_), vb, vt in (("C", outC, (negh, half), vbC, vtC), ("O", outO, (oin, oout), vbO, vtO)):
    items.append(dict(kind="cut", pts=o, closed=True))
    for p in allowance(L, R_, vb[0], vb[1], vt): items.append(dict(kind="line", pts=p, style="hidden"))
    vm = float(np.mean(vb))
    for j, s_ in enumerate(ST):
        v = np.array([vm + s_]); xl, xr = float(L(v)[0]), float(R_(v)[0])
        if v[0] >= vt - 5: continue
        items.append(dict(kind="line", pts=[[xl, v[0]], [xr, v[0]]], style="ref"))
        items.append(dict(kind="line", pts=[[xl, v[0]], [xl + 6, v[0]]], style="mark")); items.append(dict(kind="line", pts=[[xr - 6, v[0]], [xr, v[0]]], style="mark"))
        if s_ > 0: items.append(dict(kind="text", xy=((xl + xr) / 2, v[0] + 3), s=f"S{j}  {s_:.0f}", size=5.5, color=K.MARK))
    # widths at the seat, mid and under the crest
    for v0, off in ((vm + 2, -10), (vm + 350, 0), (vt - 2, 10)):
        v = np.array([v0]); xl, xr = float(L(v)[0]), float(R_(v)[0])
        items.append(dict(kind="dim", p1=(xl, v0), p2=(xr, v0), off=off, label=f"{frac32(xr - xl)} ({xr - xl:.1f})", size=5.5))
items.append(dict(kind="line", pts=[[0, vbC[0] - JA - 8], [0, vtC + JA + 8]], style="centre"))
# lengths
items.append(dict(kind="dim", p1=(-75, np.mean(vbC)), p2=(-75, vtC), off=0, label=f"centre slat, seat to crest {fmt(vtC - np.mean(vbC))} along the back face", size=5.5, rot=90))
xo_ = float(oout(np.array([400.]))[0]) + 18
items.append(dict(kind="dim", p1=(xo_, np.mean(vbO)), p2=(xo_, vtO), off=0, label=f"outer slat {fmt(vtO - np.mean(vbO))}", size=5.5))
for nm, (L, R_), vb, vt in (("C", (negh, half), vbC, vtC), ("O", (oin, oout), vbO, vtO)):
    items.append(dict(kind="text", xy=(float((L(np.array([vt]))[0] + R_(np.array([vt]))[0]) / 2), vt + JA + 5), s="crest (+3/4 in joinery allowance, dashed)" if nm == "C" else "crest", size=5))
    items.append(dict(kind="text", xy=(float((L(np.array([vb[0]]))[0] + R_(np.array([vb[0]]))[0]) / 2), vb[0] - JA - 6), s="seat (+3/4 in allowance)" if nm == "C" else "seat", size=5))
items.append(dict(kind="text", xy=(0, 560), s="CENTRE\nmake 1", size=9))
items.append(dict(kind="text", xy=(float((oin(np.array([560.]))[0] + oout(np.array([560.]))[0]) / 2), 560), s="OUTER\nmake 2", size=7))
items.append(dict(kind="text", xy=(float(oin(np.array([300.]))[0]) + 5, 300), s="inner edge", size=5, rot=90))
gapB = float(oin(np.array([np.mean(vbO) + 5]))[0] - half(np.array([np.mean(vbC) + 5]))[0]); gapT = float(oin(np.array([vtO - 5]))[0] - half(np.array([vtC - 5]))[0])
items.append(dict(kind="text", xy=(-200, 380),
    s="BACK SLATS, flat outline of the BACK face, 1:1\n"
      "Seen from behind: chair's right is on the right. The outer slat\n"
      "shown is the RIGHT one; flip the paper for the LEFT one.\n\n"
      "The slats bend one way only (front to back), so this outline\n"
      "wraps onto the bent blank's back face exactly. Glue up on\n"
      "slat_bending_form, wrap this on with S0 on the seat mark,\n"
      "check S1-S7 land on the form's marks, then trace and cut.\n\n"
      "S0-S7: every 100 mm of arc length up the back face from\n"
      "the seat line. Solid: visible slat, seat to crest.\n"
      f"Dashed: {frac32(JA)} joinery allowance at each end (joints not\n"
      "seen in any photo; size them to your mortises).\n"
      f"Gap centre-outer at the back face: {gapB:.1f} at the seat, {gapT:.1f} under the crest.",
    size=6.4, ha="left", va="top"))
TB = [
    "Edges: traced in the unrolled back view (sheets sc/so, 0.5 mm/px) on the most on-axis clean photo IMG_1502, snapped, faired 4th order,",
    f"  left/right mirrored and averaged (design intent). Edge scatter 0.15-0.83 mm; L/R mirror disagreement up to 3.3 mm (right outer slat",
    "  as built is ~3 mm narrower at the top). Edges: +-1.6 mm. Below v 70 edges run plumb (as on IMG_1502); above v 715 on the end tangent.",
    "Ends: seat ends read by eye where the slats meet the seat top (+-2 mm); crest ends where the back face meets the crest bottom face",
    "  (triangulated arrises, parts/crest.json) (+-3 mm). Joinery into seat and crest: not seen; the dashed allowance is assumed.",
    "Arc length: along the back face profile located by photo consistency in 7 height bands (centre and outer slats separately); a 1 % error in",
    "  the bend would change lengths by < 1 mm. Not measured by hand: M5 (centre width under the crest: trace 99-100 mm vs tape 98.3 mm).",
    f"Generated by templates/slats.py from parts/slats.json @ {REV}, templates/slat_ends.json, parts/crest.json.",
]
wC = lambda v: float(2 * half(np.array([v]))[0]); wO = lambda v: float(oout(np.array([v]))[0] - oin(np.array([v]))[0])
KD = [("Centre slat, seat to crest (back face)", vtC - np.mean(vbC), "arc length, visible part"),
      ("Centre slat width, seat / under crest", f"{frac32(wC(np.mean(vbC) + 2))} / {frac32(wC(vtC - 2))}  ({wC(np.mean(vbC) + 2):.1f} / {wC(vtC - 2):.1f} mm)", "tapers wider upward"),
      ("Outer slat, seat to crest", vtO - np.mean(vbO), "arc length on its centre line"),
      ("Outer slat width, seat / under crest", f"{frac32(wO(np.mean(vbO) + 2))} / {frac32(wO(vtO - 2))}  ({wO(np.mean(vbO) + 2):.1f} / {wO(vtO - 2):.1f} mm)", "both edges curved"),
      ("Thickness (stack)", a.stack_mm, "assumed from photo consistency, weak (M4)"),
      ("Joinery allowance, each end", JA, "assumed")]
spec_t = dict(name="slat_template", title="ESSICK rocker - back slats, flat outlines (centre x1, outer x2)", rev=REV, items=items, title_block=TB, key_dims=KD)

# ---------------- bending form ----------------
S = a.stack_mm; EXT = 60.0
mC, mO = float(np.mean(vbC)), float(np.mean(vbO)); aTop = min(vtC - mC, vtO - mO)
aa = np.arange(0, aTop + 0.01, 2.0)
PC = atC(mC + aa); PO = atO(mO + aa)
mc, mo = PC.mean(0), PO.mean(0); H = (PO - mo).T @ (PC - mc); Uu, _, Vt = np.linalg.svd(H); Rm = (Uu @ Vt).T
if np.linalg.det(Rm) < 0: Vt[-1] *= -1; Rm = (Uu @ Vt).T
PO2 = (PO - mo) @ Rm.T + mc; dev = np.linalg.norm(PO2 - PC, axis=1)
PM = (PC + PO2) / 2
spy, spz = UnivariateSpline(aa, PM[:, 0], s=len(aa) * 0.04), UnivariateSpline(aa, PM[:, 1], s=len(aa) * 0.04)
def mean_at(A):
    A = np.asarray(A, float); Ac = np.clip(A, 0, aa[-1]); p = np.stack([spy(Ac), spz(Ac)], 1)
    for e, sel in ((0.0, A < 0), (aa[-1], A > aa[-1])):
        if sel.any():
            t = np.array([spy(e, 1), spz(e, 1)]); t /= np.linalg.norm(t); p[sel] = np.array([spy(e), spz(e)]) + np.outer(A[sel] - e, t)
    return p
yd, zd = spy(aa, 1), spz(aa, 1); ydd, zdd = spy(aa, 2), spz(aa, 2); kap = (yd * zdd - zd * ydd) / (yd ** 2 + zd ** 2) ** 1.5
infl = aa[np.where(np.diff(np.sign(kap)))[0]]
Rpos = 1 / kap[kap > 0].max() if (kap > 0).any() else np.inf; Rneg = 1 / -kap[kap < 0].min() if (kap < 0).any() else np.inf
fit_dev = float(np.abs(np.linalg.norm(mean_at(aa) - PM, axis=1)).max())
A_all = np.arange(-JA - EXT, aTop + JA + EXT + 0.01, 2.0)
work = mean_at(A_all)
tang = np.gradient(work, axis=0); tang /= np.linalg.norm(tang, axis=1)[:, None]; nrm = np.stack([tang[:, 1], -tang[:, 0]], 1)   # forward
if (nrm[:, 0] < 0).mean() > 0.5: nrm = -nrm
caul_w = work + nrm * S
GAP = 70.0
back = work[:, 0].min() - 50; front = caul_w[:, 0].max() + 40
form = np.vstack([work, [[back, work[-1, 1]], [back, work[0, 1]]]])
caul = np.vstack([caul_w + [GAP, 0], [[front + GAP, caul_w[-1, 1]], [front + GAP, caul_w[0, 1]]]])
fi = [dict(kind="cut", pts=form, closed=True), dict(kind="cut", pts=caul, closed=True), dict(kind="line", pts=caul_w, style="hidden")]
def mk(A, lab, ln=8, both=True, style="mark"):
    i = int(np.argmin(np.abs(A_all - A))); p = work[i]; n = nrm[i]
    fi.append(dict(kind="line", pts=[p - n * ln, p], style=style))
    if both: q = caul_w[i] + [GAP, 0]; fi.append(dict(kind="line", pts=[q, q + n * ln], style=style))
    if lab: fi.append(dict(kind="text", xy=tuple(p - n * (ln + 9)), s=lab, size=6, color=K.MARK if style == "mark" else K.REF))
for j, s_ in enumerate(ST):
    if s_ <= aTop: mk(s_, "S0 seat" if j == 0 else f"S{j}")
mk(-JA, "", 14, style="ref"); mk(aTop + JA, "", 14, style="ref")
fi.append(dict(kind="text", xy=tuple(work[np.argmin(np.abs(A_all + JA))] + [-40, -8]), s="blank ends", size=5.5, color=K.REF))
mk(aTop, "crest", 16, style="ref")
zmid = float(work[:, 1].mean())
fi.append(dict(kind="text", xy=(back + 10, zmid + 40), s="FORM\n(back face of\nthe slats)", size=8, ha="left"))
fi.append(dict(kind="text", xy=(front + GAP - 10, zmid + 40), s="CAUL\n(front face)", size=8, ha="right"))
fi.append(dict(kind="dim", p1=(back, work[0, 1]), p2=(back, work[-1, 1]), off=-12, label=f"form height {fmt(work[-1, 1] - work[0, 1])}", rot=90))
z_floor = float(mean_at(np.array([0.0]))[0, 1])
fi.append(dict(kind="text", xy=(back + 10, work[0, 1] + 160),
    s=f"Drawn upright as in the chair, front to the right.\nS0 (seat line) is {fmt(z_floor)} above the floor.\n\n"
      f"Laminations: {round(S / a.lam_mm)} x {a.lam_mm:.1f} mm ({frac32(a.lam_mm)}) = {fmt(S)} stack.\n"
      f"Strips at least {frac32(110)} wide (centre slat is {wC(vtC - 2):.0f} mm\nat the top), {frac32(aTop + 2 * JA + 40)} long.\n"
      f"Gentle S bend: total turn {np.degrees(np.ptp(np.arctan2(zd, yd))):.0f} deg, reverses at\n"
      + ", ".join(f"S0+{x:.0f}" for x in infl) + f" mm; tightest R {Rpos:.0f} / {Rneg:.0f} mm.\nUse both halves (an S needs a caul).\n"
      "One form for all 3 slats: their bends differ\n" f"by {dev.max():.1f} mm at most (avg. drawn).\n"
      "Dashed: caul face on a full stack in the press.\nNo spring-back allowance; check the first\nglue-up against slat_template, shim if needed.",
    size=6.2, ha="left", va="bottom"))
TBf = [f"Working face = the slats' back-face side profile: centre and outer slat profiles (parts/slats.json, tabulated, located by photo",
       f"  consistency in 7 height bands; +-2 mm) rigidly aligned (differ by {dev.max():.1f} mm max, {np.sqrt((dev ** 2).mean()):.1f} rms) and averaged, smoothed",
       f"  ({fit_dev:.1f} mm), carried on straight along the end tangents for the joinery allowance and {EXT:.0f} mm form run-out.",
       f"Caul face = working face offset {S:.1f} mm forward (--stack-mm). Thickness 10 mm is weak (photo consistency); M4 would settle it.",
       "The lamination plan is a suggestion: glue lines were not resolved in the photos. Form back / caul front faces are free.",
       f"Generated by templates/slats.py from parts/slats.json @ {REV}."]
KDf = [("Stack (slat thickness)", S, f"{round(S / a.lam_mm)} laminations of {a.lam_mm:.1f} mm"), ("Form working length", float(np.sum(np.linalg.norm(np.diff(work, axis=0), axis=1))), "arc length incl. run-out"),
       ("Tightest bend radius", float(min(Rpos, Rneg)), "within the slat"), ("Seat line (S0) above floor", z_floor, "chair standing on the floor")]
spec_f = dict(name="slat_bending_form", title="ESSICK rocker - back slat bending form (form + caul, all 3 slats)", rev=REV, items=fi, title_block=TBf, key_dims=KDf)

os.makedirs(a.out, exist_ok=True)
Lt = K.write_all(spec_t, a.out); Lf = K.write_all(spec_f, a.out)
geom = dict(set_offset_u_mm=OFF, centre=outC.tolist(), outer_right=outO.tolist(), v_top=[vtC, vtO], v_seat=[vbC, vbO],
            form_work=work.tolist(), stations=ST.tolist(), inflections=infl.tolist(), R_min=[float(Rpos), float(Rneg)], profile_dev_max=float(dev.max()),
            tiles=dict(template=[Lt["rows"], Lt["cols"]], form=[Lf["rows"], Lf["cols"]]))
json.dump(geom, open(a.geom_json or f"{a.out}/slats_geom.json", "w"), indent=1)
print(f"slats: centre v {np.mean(vbC):.1f}..{vtC:.1f} ({vtC - np.mean(vbC):.1f} mm), width {wC(np.mean(vbC) + 2):.1f} -> {wC(vtC - 2):.1f}")
print(f"       outer  v {np.mean(vbO):.1f}..{vtO:.1f} ({vtO - np.mean(vbO):.1f} mm), width {wO(np.mean(vbO) + 2):.1f} -> {wO(vtO - 2):.1f}; gaps {gapB:.1f} / {gapT:.1f}")
print(f"form: profile dev C vs O max {dev.max():.2f} rms {np.sqrt((dev ** 2).mean()):.2f}; smoothing {fit_dev:.2f}; inflections a={infl.round(0)}; R min +{Rpos:.0f} -{Rneg:.0f}; S0 z {z_floor:.1f}")
print(f"tiles: template {Lt['rows']}x{Lt['cols']}, form {Lf['rows']}x{Lf['cols']}")
