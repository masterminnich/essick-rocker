"""USAGE: tools/py.sh templates/rocker.py [--stack-mm 31.75] [--lam-mm 3.175] [--out templates/out] [--geom-json templates/out/rocker_geom.json]
Rocker side template + two-part bending form (form and caul) for the laminations, 1:1, from parts/rocker_profile.json
(mean_top / mean_bot, design intent), the ends from templates/rocker_ends.json (fitted by eye on rectified single photos)
and the leg landings from parts/side_frame.json (triangulated leg lines extrapolated to the rocker top).
Drawing frame = the left rocker's side-face sheet (work/parts/rockerL/o_plane.json): u along the rocker, front to the right,
v up, v = 0 is the table (floor). Writes <out>/rocker_template_* and <out>/rocker_bending_form_* (tiled Letter PDF, full 1:1
PDF, DXF, preview PNG) and a geometry json (used by templates/check_overlay.py). Tiny compute (<1 s, <200 MB)."""
import json, argparse, subprocess, sys, os, numpy as np
from scipy.interpolate import CubicSpline
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tplkit as K
from tplkit import fmt, frac32

ap = argparse.ArgumentParser()
ap.add_argument("--stack-mm", type=float, default=10 * 3.175, help="glued lamination stack thickness (default 10 x 1/8 in)")
ap.add_argument("--lam-mm", type=float, default=3.175)
ap.add_argument("--out", default="templates/out"); ap.add_argument("--geom-json", default=None)
ap.add_argument("--rev", default=None)
a = ap.parse_args()

def ghash(p):
    try: return subprocess.run(["git", "log", "-1", "--format=%h", "--", p], capture_output=True, text=True).stdout.strip() or "uncommitted"
    except Exception: return "?"
REV = a.rev or ghash("parts/rocker_profile.json")

P = json.load(open("parts/rocker_profile.json")); E = json.load(open("templates/rocker_ends.json"))
U = np.array(P["u"]); T = np.array(P["mean_top"]); B = np.array(P["mean_bot"])
csT, csB = CubicSpline(U, T), CubicSpline(U, B)

def bez(p0, p1, p2, p3, n=24):
    t = np.linspace(0, 1, n)[:, None]
    return (1 - t) ** 3 * p0 + 3 * (1 - t) ** 2 * t * p1 + 3 * (1 - t) * t ** 2 * p2 + t ** 3 * p3

def unit(v): v = np.asarray(v, float); return v / np.linalg.norm(v)

# ---------------- outline ----------------
R = E["rear"]; F = E["front"]
uA, uB = R["blend_top_u"], R["blend_bot_u"]; tip = np.array(R["tip"]); k = R["tip_handle"]
A = np.array([uA, csT(uA)]); tA = unit([1, csT(uA, 1)]); Bp = np.array([uB, csB(uB)]); tB = unit([1, csB(uB, 1)])
dA = np.linalg.norm(A - tip) / 2.2; dB = np.linalg.norm(Bp - tip) / 2.2
nose_top = bez(A, A - tA * dA, tip + np.array([0, k]), tip)            # from the top curve down to the tip
nose_bot = bez(tip, tip - np.array([0, k]), Bp - tB * dB, Bp)          # from the tip on to the bottom curve
uf = F["end_u"]; rb = F["bot_corner_r"]
def extT(u): return csT(min(u, U[-1])) + (csT(U[-1], 1) * (u - U[-1]) if u > U[-1] else 0)
def extB(u): return csB(min(u, U[-1])) + (csB(U[-1], 1) * (u - U[-1]) if u > U[-1] else 0)
# bottom front corner: fillet of radius rb between the bottom line (slope s) and the plumb end u = uf
s = csB(U[-1], 1); tb = unit([1, s]); nb = np.array([-tb[1], tb[0]])                 # nb points up/inward
# centre c: distance rb from the end line (c_u = uf - rb) and rb above the bottom line
cu = uf - rb; # bottom line through (U[-1], B[-1]) with direction tb: point on line at u=cu
pl = np.array([cu, extB(cu)]); cv = pl[1] + rb / tb[0]                                # vertical offset of rb normal distance
c = np.array([cu, cv])
foot_b = c - nb * rb; foot_e = np.array([uf, cv])
ang0 = np.arctan2(*(foot_b - c)[::-1]); ang1 = 0.0
arc = c + rb * np.stack([np.cos(np.linspace(ang0, ang1, 20)), np.sin(np.linspace(ang0, ang1, 20))], 1)
top_end = np.array([uf, extT(uf)])
uu_top = np.arange(uA, U[-1] + 0.1, 2.5)
top = np.stack([uu_top, csT(uu_top)], 1); top = np.vstack([top, [top_end]])
uu_bot = np.arange(uB, foot_b[0], 2.5)
bot = np.stack([uu_bot, [extB(u) for u in uu_bot]], 1)
# closed outline, clockwise from the nose: top (rear->front), end, corner arc, bottom (front->rear), nose
outline = np.vstack([tip[None], nose_top[::-1][1:], top[1:], [foot_e], arc[::-1][1:], bot[::-1], nose_bot[::-1][1:-1]])

# ---------------- leg landings ----------------
pl_ = json.load(open("work/parts/rockerL/o_plane.json")); O, eu, ev = (np.array(pl_[k]) for k in ("origin", "u", "v"))
SF = json.load(open("parts/side_frame.json"))["lines"]
def landing(key, zmax_rel=80):
    l = SF[key]; z = np.array(l["z"]); y = np.array(l["y"]); x = -np.array(l["x_abs"])
    Q = np.stack([x, y, z], 1) - O; uu, vv = Q @ eu, Q @ ev
    m = vv < vv.min() + zmax_rel; p = np.polyfit(vv[m], uu[m], 1)
    # intersect u = p(v) with the top curve
    vv_ = np.linspace(vv.min() - 80, vv.min(), 4000); uu_ = np.polyval(p, vv_)
    i = np.argmin(np.abs(vv_ - csT(uu_))); return float(uu_[i]), float(vv_[i]), float(vv.min() - vv_[i]), p
legs = {}
for key, name in (("bleg_rear_lo", "back leg, rear face"), ("bleg_front_lo", "back leg, front face"),
                  ("fleg_rear_lo", "front leg, rear face"), ("fleg_front_lo", "front leg, front face")):
    u0, v0, extrap, p = landing(key); legs[key] = dict(u=u0, v=v0, extrap_mm=extrap, slope_du_dv=float(p[0]), name=name)

# ---------------- key numbers ----------------
i0 = int(np.argmin(B)); u_rest = float(U[i0])
fine = np.linspace(U[0], U[-1], 4000); hh = (csT(fine) - csB(fine)) * np.cos(np.arctan(csT(fine, 1)))
L_total = uf - tip[0]
d1, d2 = csB(fine, 1), csB(fine, 2); kap = d2 / (1 + d1 ** 2) ** 1.5
R_min_up = 1 / kap[kap > 0].max(); R_min_down = 1 / (-kap[kap < 0]).max(); u_infl = float(fine[np.where(np.diff(np.sign(kap)))[0][0]])
stations = np.arange(-400, 601, 100)

def perp_height(u):
    """perpendicular face height at u: from the bottom point, along the bottom normal, to the top curve"""
    p = np.array([u, csB(u)]); t = unit([1, csB(u, 1)]); n = np.array([-t[1], t[0]])
    ss = np.linspace(0, 45, 4501); q = p[None] + ss[:, None] * n[None]
    j = np.argmin(np.abs(q[:, 1] - csT(q[:, 0]))); return p, q[j], float(ss[j])

items = [dict(kind="cut", pts=outline, closed=True)]
xl = tip[0] - 10, uf + 10
items.append(dict(kind="line", pts=[[xl[0], 0], [xl[1], 0]], style="hidden", label="FLOOR / table line (v = 0), tangent to the rocker at the rest point", label_at=0))
items[-1]["label_at"] = 1
items.append(dict(kind="line", pts=[[u_rest, -6], [u_rest, csT(u_rest) + 8]], style="centre"))
items.append(dict(kind="text", xy=(u_rest, csT(u_rest) + 14), s=f"REST POINT (lowest point on the floor)\nrocking radius R {fmt(P['rocking_radius_mm'], 0)}", size=6.5))
# stations
for j, su in enumerate(stations):
    items.append(dict(kind="line", pts=[[su, csB(su) - 4], [su, csB(su) + 3]], style="mark"))
    items.append(dict(kind="line", pts=[[su, csT(su) - 3], [su, csT(su) + 4]], style="mark"))
    items.append(dict(kind="text", xy=(su, csT(su) + 8), s=f"S{j + 1}", size=6, color=K.MARK))
# leg landings
for key, l in legs.items():
    v_top = csT(l["u"]); vv = np.array([v_top - 2, v_top + 45]); uu = l["u"] + l["slope_du_dv"] * (vv - l["v"])
    items.append(dict(kind="line", pts=np.stack([uu, vv], 1), style="mark"))
for side, (kr, kf) in (("BACK LEG", ("bleg_rear_lo", "bleg_front_lo")), ("FRONT LEG", ("fleg_rear_lo", "fleg_front_lo"))):
    um = (legs[kr]["u"] + legs[kf]["u"]) / 2
    items.append(dict(kind="text", xy=(um, csT(um) + 58), s=f"{side} lands here\n(leg faces, extrapolated)", size=6, color=K.MARK))
# face heights (perpendicular)
for su in (-400, -200, 0, 200, 400, 560):
    p, q, h = perp_height(su)
    items.append(dict(kind="dim", p1=p, p2=q, off=0.0, label=f"{frac32(h)} ({h:.1f})", size=5.5))
# chain of positions along the floor, below the datum
chain = [("rear tip", tip[0]), ("back leg rear", legs["bleg_rear_lo"]["u"]), ("back leg front", legs["bleg_front_lo"]["u"]),
         ("rest point", u_rest), ("front leg rear", legs["fleg_rear_lo"]["u"]), ("front leg front", legs["fleg_front_lo"]["u"]), ("front end", uf)]
for (n1, x1), (n2, x2) in zip(chain[:-1], chain[1:]):
    items.append(dict(kind="dim", p1=(x1, 0), p2=(x2, 0), off=-14, size=5.5))
items.append(dict(kind="dim", p1=(tip[0], 0), p2=(uf, 0), off=-30, label=f"overall length, tip to front end, along the floor: {fmt(L_total)}"))
# heights: rear tip, tail top, front end top
items.append(dict(kind="dim", p1=(tip[0], 0), p2=(tip[0], tip[1]), off=12, label=f"tip {frac32(tip[1])} ({tip[1]:.1f})", size=5.5))
items.append(dict(kind="dim", p1=(uf, 0), p2=(uf, top_end[1]), off=-14, label=f"{frac32(top_end[1])} ({top_end[1]:.1f})", size=5.5))
items.append(dict(kind="dim", p1=(uf, 0), p2=(uf, foot_e[1]), off=-4, label=f"{frac32(foot_e[1])}", size=5))
items.append(dict(kind="text", xy=(uf - 30, foot_e[1] - 18), s=f"R {fmt(rb, 0)}", size=5.5))
items.append(dict(kind="text", xy=(-150, 128),
    s="ROCKER, side profile, 1:1  (make 2)\nShown: right rocker's outer face, front to the right. Flip it for the left rocker.\n"
      "Bent lamination: glue up on the bending form (rocker_bending_form), bottom edge comes off the form;\n"
      "then lay this on the blank, match the bottom edge and stations S1-S11, and cut the top line and both ends.",
    size=7, ha="left", va="center"))

wsum = lambda key: [round(float(l), 1) for l in (legs[key]["u"], legs[key]["v"])]
TB = [
    "Side profile: both rockers' outer side faces traced on face orthophotos (7 photos each), faired, right aligned onto left and averaged",
    f"  (design intent). Edge noise 0.4 mm rms; left vs right after alignment {P['right_vs_left']['residual_rms_mm']:.1f} mm rms, "
    f"{P['right_vs_left']['residual_max_mm']:.1f} mm max. Curves +-1/16 in (1.6 mm) except the last 60 mm of the tail (L/R differ up to 8 mm): +-3 mm.",
    "Rear nose and front end: fitted by eye on rectified single photos IMG_1507 (left) and IMG_1472 (right), 0.5 mm/px sheets: front end +-2 mm,",
    "  nose tip +-3 mm. Bottom edge in the table-contact zone = top edge minus the face height from the clear zones (bottom arris in shadow).",
    f"Leg landings: triangulated leg lines (parts/side_frame.json) extrapolated {min(l['extrap_mm'] for l in legs.values()):.0f}-"
    f"{max(l['extrap_mm'] for l in legs.values()):.0f} mm down to the rocker top: +-2 mm. The leg seats on the rocker are hand-fitted; scribe to the leg.",
    "Scale: framing-square tick comb, two legs agree to 0.085 % (about 1 mm over this rocker). Not measured by hand: anything here (M8, rocker",
    "  tip to tip, would check the scale). Rocker width across (31 mm, tape) is not on this template.",
    f"Generated by templates/rocker.py from parts/rocker_profile.json @ {REV}, templates/rocker_ends.json, parts/side_frame.json.",
]
KD = [("Overall length (along floor)", L_total, "rear tip to front end"),
      ("Rocking radius", P["rocking_radius_mm"], "fitted over the contact zone, rms 0.04 mm"),
      ("Face height, max / at tail tip", f"{frac32(hh.max())} / {frac32(hh[0])}  ({hh.max():.1f} / {hh[0]:.1f} mm)", "perpendicular to the edge"),
      ("Rear tip above floor", float(tip[1]), "nose point"),
      ("Front end, top corner above floor", float(top_end[1]), "plumb end"),
      ("Back leg on rocker (rear..front face)", f"{frac32(legs['bleg_front_lo']['u'] - legs['bleg_rear_lo']['u'])} ({legs['bleg_front_lo']['u'] - legs['bleg_rear_lo']['u']:.1f} mm)", "along u, at the rocker top"),
      ("Front leg on rocker (rear..front face)", f"{frac32(legs['fleg_front_lo']['u'] - legs['fleg_rear_lo']['u'])} ({legs['fleg_front_lo']['u'] - legs['fleg_rear_lo']['u']:.1f} mm)", "along u, at the rocker top"),
      ("Back leg front face to front leg rear face", legs["fleg_rear_lo"]["u"] - legs["bleg_front_lo"]["u"], "clear span along u")]
spec_t = dict(name="rocker_template", title="ESSICK rocker - rocker side template (make 2)", rev=REV, items=items, title_block=TB, key_dims=KD)

# ---------------- bending form ----------------
S = a.stack_mm; EXT = 60.0
uu = np.arange(U[0], U[-1] + 0.1, 2.5)
bc = np.stack([uu, csB(uu)], 1)
t0 = unit([1, csB(U[0], 1)]); t1 = unit([1, csB(U[-1], 1)])
work = np.vstack([bc[0] - t0 * EXT, bc, bc[-1] + t1 * EXT])            # lower form's working surface = rocker bottom, extended
tang = np.gradient(work, axis=0); tang /= np.linalg.norm(tang, axis=1)[:, None]; nrm = np.stack([-tang[:, 1], tang[:, 0]], 1)
caul_w = work + nrm * S                                                      # caul surface = bottom offset by the stack
# resample caul by u order (offset can bunch on the concave side)
GAP = 70.0                                                                   # drawing gap between form and caul (they nest in use)
base = work[:, 1].min() - 50; topc = caul_w[:, 1].max() + 40
form = np.vstack([work, [[work[-1, 0], base], [work[0, 0], base]]])
caul = np.vstack([caul_w + [0, GAP], [[caul_w[-1, 0], topc + GAP], [caul_w[0, 0], topc + GAP]]])
fi = [dict(kind="cut", pts=form, closed=True), dict(kind="cut", pts=caul, closed=True)]
fi.append(dict(kind="line", pts=caul_w - [0, 0] , style="hidden"))
fi.append(dict(kind="text", xy=(work[0, 0] + 230, base + 22), s="LOWER FORM  (working face = rocker bottom = rocking surface)", size=8))
fi.append(dict(kind="text", xy=(work[0, 0] + 230, topc + GAP - 18), s=f"CAUL  (working face = rocker bottom offset {fmt(S)} = the stack)", size=8))
fi.append(dict(kind="text", xy=(250, (base + work[:, 1].min()) / 2 + 60 - 25), s="dashed: caul face where it sits on a full stack in the press", size=6, color=K.REF))
for j, su in enumerate(stations):
    p = np.array([su, csB(su)]); i = np.argmin(np.abs(work[:, 0] - su)); n = nrm[i]
    fi.append(dict(kind="line", pts=[p - n * 8, p], style="mark")); fi.append(dict(kind="text", xy=tuple(p - n * 13), s=f"S{j + 1}", size=6, color=K.MARK))
    q = caul_w[i] + [0, GAP]; fi.append(dict(kind="line", pts=[q, q + n * 8], style="mark"))
    fi.append(dict(kind="line", pts=[[su, base], [su, base + 6]], style="mark")); fi.append(dict(kind="line", pts=[[caul_w[i, 0], topc + GAP], [caul_w[i, 0], topc + GAP - 6]], style="mark"))
for e, lab in ((U[0], "rocker tail ends ~here"), (U[-1], "rocker front ends ~here")):
    p = np.array([e, csB(e)]); fi.append(dict(kind="line", pts=[p + [0, -12], p + [0, 4]], style="ref"))
fi.append(dict(kind="dim", p1=(work[0, 0], base), p2=(work[-1, 0], base), off=-12, label=f"form length {fmt(work[-1, 0] - work[0, 0])} (rocker + {EXT:.0f} mm each end)"))
fi.append(dict(kind="text", xy=(-120, topc + GAP - 32),
    s=f"Laminations: {round(S / a.lam_mm)} x {frac32(a.lam_mm)} ({a.lam_mm:.2f} mm) = {fmt(S)} stack, strips at least {frac32(35)} wide, {frac32(work[-1, 0] - work[0, 0] - 2 * EXT + 2 * 40)} long.\n"
      f"Rocker face height is {frac32(hh.max())} ({hh.max():.1f} mm) at most, so the stack leaves {S - hh.max():.1f} mm to cut off the top.\n"
      f"Tightest bend: {fmt(R_min_down, 0)} (tail, convex) and {fmt(R_min_up, 0)} (concave); the bottom curve reverses {u_rest - u_infl:.0f} mm behind the rest point (an S): use both halves, not a one-sided form.\n"
      "Cut both halves from stacked ply/MDF at least the strip width; transfer stations S1-S11 to both, square across the faces. No spring-back\n"
      f"allowance is drawn (with {round(S / a.lam_mm)} laminations it is small); check the first glue-up against rocker_template and shim the caul if needed.",
    size=6.6, ha="left", va="top"))
TBf = [f"Working face of the lower form = mean rocker bottom edge (parts/rocker_profile.json mean_bot) extended {EXT:.0f} mm along its end tangents.",
       f"Caul face = that curve offset {S:.2f} mm along its normal (--stack-mm; re-run templates/rocker.py if the stack changes).",
       "Accuracy as the rocker template: +-1.6 mm on the curve, +-3 mm over the tail's last 60 mm. Form outer faces (flat base / top) are free.",
       "The lamination plan (count, thickness) is a suggestion, not measured from the chair: glue lines were not resolved in the photos.",
       f"Generated by templates/rocker.py from parts/rocker_profile.json @ {REV}."]
KDf = [("Stack (laminations)", S, f"{round(S / a.lam_mm)} x {frac32(a.lam_mm)}"), ("Form length", work[-1, 0] - work[0, 0], "working face"),
       ("Tightest bend radius", R_min_down, "tail, convex side"), ("Bottom curve reverses (S) at", u_rest - u_infl, "behind the rest point (station between S2 and S3)")]
spec_f = dict(name="rocker_bending_form", title="ESSICK rocker - lamination bending form (lower form + caul)", rev=REV, items=fi, title_block=TBf, key_dims=KDf)

os.makedirs(a.out, exist_ok=True)
Lt = K.write_all(spec_t, a.out); Lf = K.write_all(spec_f, a.out)
geom = dict(outline=outline.tolist(), legs=legs, tip=tip.tolist(), front_end_u=uf, u_rest=u_rest, total_length=L_total,
            stack_mm=S, R_min=[R_min_down, R_min_up], u_inflection=u_infl, form_work=work.tolist(), caul_work=caul_w.tolist(),
            tiles=dict(template=[Lt["rows"], Lt["cols"]], form=[Lf["rows"], Lf["cols"]]))
json.dump(geom, open(a.geom_json or f"{a.out}/rocker_geom.json", "w"), indent=1)
print(f"rocker: length {L_total:.1f} mm ({frac32(L_total)}), tip v {tip[1]:.1f}, front top {top_end[1]:.1f}, rest u {u_rest:.0f}")
for kk, l in legs.items(): print(f"  {kk:15s} u {l['u']:7.1f} v {l['v']:6.1f} (extrapolated {l['extrap_mm']:.0f} mm)")
print(f"face height max {hh.max():.1f} min {hh.min():.1f}; bend R min {R_min_down:.0f} (convex) {R_min_up:.0f} (concave); inflection u {u_infl:.0f}")
print(f"tiles: template {Lt['rows']}x{Lt['cols']}, form {Lf['rows']}x{Lf['cols']}")
