"""USAGE: tools/py.sh templates/rocker.py [--stack-mm 31.75] [--lam-mm 3.175] [--model 24] [--out templates/out] [--geom-json templates/out/rocker_geom.json]
Rocker side template + two-part bending form (form and caul) for the laminations, 1:1, from the rocker outline of model v24
exactly as tools/build_model.py builds it: parts/rocker_profile.json mean_top / mean_bot, the bottom corrected by
parts/rocker_bottom.json (traced directly), the two ends from parts/rocker_ends.json (triangulated tail tip and round nose), all
carried to the build's half-way design frame (to_mean). Checked against the ROCKER_R mesh of parts/model_v<N>.glb (outline
vertices must sit on mesh vertices). Thickness across from parts/rocker_section.json. Leg landings = where the v<N> FLEG_R /
BLEG_R meshes sit on the rocker top (mesh sections across the rocker's thickness), leg rake from model_v<N>_joinery.json.
Drawing frame = the build's design frame: u along the rocker, front to the right, v up (world z); the floor is the horizontal
tangent at the rocker's lowest point. Writes <out>/rocker_template_* and <out>/rocker_bending_form_* (tiled Letter PDF,
full 1:1 PDF, DXF, preview PNG) and a geometry json (used by templates/check_overlay.py; it carries the design -> left-sheet
transform). Tiny compute (a few s, < 300 MB)."""
import json, argparse, subprocess, sys, os, importlib.util, numpy as np
from scipy.signal import savgol_filter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tplkit as K
from tplkit import fmt, frac32

ap = argparse.ArgumentParser()
ap.add_argument("--stack-mm", type=float, default=10 * 3.175, help="glued lamination stack thickness (default 10 x 1/8 in)")
ap.add_argument("--lam-mm", type=float, default=3.175)
ap.add_argument("--model", type=int, default=24, help="model version whose mesh the outline is checked against / legs taken from")
ap.add_argument("--out", default="templates/out"); ap.add_argument("--geom-json", default=None)
ap.add_argument("--rev", default=None)
a = ap.parse_args()

def ghash(p):
    try: return subprocess.run(["git", "log", "-1", "--format=%h", "--", p], capture_output=True, text=True).stdout.strip() or "uncommitted"
    except Exception: return "?"
REV = a.rev or ghash(f"parts/model_v{a.model}.glb")
_sp = importlib.util.spec_from_file_location("sideframe", "rocker/sideframe.py"); SF_ = importlib.util.module_from_spec(_sp); _sp.loader.exec_module(SF_)

def unit(v): v = np.asarray(v, float); return v / np.linalg.norm(v)

# ---------------- outline: tools/build_model.py's rocker, line for line ----------------
rp = json.load(open("parts/rocker_profile.json")); U = np.array(rp["u"]); rtop = np.array(rp["mean_top"]); rbot = np.array(rp["mean_bot"]); RVL = rp["right_vs_left"]
def rigid(q, th_deg, su, sv, inverse=False):
    th = np.radians(th_deg); c, s_ = np.cos(th), np.sin(th); q = np.asarray(q, float)
    if inverse:
        d = q - [su, sv]; return np.c_[c * d[:, 0] + s_ * d[:, 1], -s_ * d[:, 0] + c * d[:, 1]]
    return np.c_[c * q[:, 0] - s_ * q[:, 1] + su, s_ * q[:, 0] + c * q[:, 1] + sv]
HALF = (RVL["rotation_deg"] / 2, RVL["shift_u_mm"] / 2, RVL["shift_v_mm"] / 2)
to_mean = lambda q: rigid(q, *HALF, inverse=True)          # left sheet -> design frame
to_left = lambda q: rigid(q, *HALF)                        # design frame -> left sheet (photos)
rends = json.load(open("parts/rocker_ends.json"))["design"]; r_tail, r_nose = rends["tail"], rends["nose"]; mid = (U > r_tail["blend_u"][0]) & (U < r_nose["blend_u"][0])
rbc = json.load(open("parts/rocker_bottom.json"))["correction"]
bot_dv = lambda q: np.c_[q[:, 0], q[:, 1] + np.interp(q[:, 0], rbc["u"], rbc["dv_mm"], left=0.0, right=0.0)]
rbot = rbot + np.interp(U, rbc["u"], rbc["dv_mm"], left=0.0, right=0.0); r_tail_bot = bot_dv(np.array(r_tail["bot"])); r_nose_bot = bot_dv(np.array(r_nose["bot"]))
outline = to_mean(np.r_[np.array(r_tail["top"])[::-1], np.c_[U, rtop][mid], np.array(r_nose["top"]), r_nose_bot[::-1][1:], np.c_[U, rbot][mid][::-1], r_tail_bot[:-1]])
i_nose = len(r_tail["top"]) + int(mid.sum()) + len(r_nose["top"]) - 1      # nose top corner (landmark)
tip = outline[0]; nose_c = outline[i_nose]
top_br = outline[:i_nose + 1]                                              # tail tip -> nose top corner along the top
bot_br = np.vstack([outline[i_nose:], outline[:1]])[::-1]                   # tail tip -> nose top corner along the bottom

# ---------------- check: the outline is the v<N> mesh's outline ----------------
import trimesh
from scipy.spatial import cKDTree
SC = trimesh.load(f"parts/model_v{a.model}.glb")
def world(name):
    for n in SC.graph.nodes_geometry:
        T, gn = SC.graph[n]
        if gn == name: return trimesh.Trimesh(trimesh.transformations.transform_points(SC.geometry[name].vertices, T), SC.geometry[name].faces, process=False)
    raise KeyError(name)
RM = SF_.to_plane(world("ROCKER_R").vertices, +1)
mesh_dev = float(cKDTree(RM[:, :2]).query(outline)[0].max())
assert mesh_dev < 0.05, f"outline is {mesh_dev:.2f} mm off the v{a.model} ROCKER_R mesh: build_model.py's rocker changed, update this file"

# ---------------- floor, heights ----------------
i_low = int(np.argmin(outline[:, 1])); u_rest = float(outline[i_low, 0]); v_floor = float(outline[i_low, 1])
def br_fn(br):
    o = np.argsort(br[:, 0]); return lambda u: np.interp(u, br[o, 0], br[o, 1])
top_br_m = top_br[top_br[:, 0] <= nose_c[0]]; topv = br_fn(top_br_m)
bb = bot_br[: int(np.argmax(bot_br[:, 0])) + 1]; botv = br_fn(bb)                  # bottom up to its furthest-forward point
u_front = float(outline[:, 0].max()); L_total = u_front - float(outline[:, 0].min())
def resample(p, ds):
    s = np.r_[0, np.cumsum(np.linalg.norm(np.diff(p, axis=0), axis=1))]; ss = np.arange(0, s[-1], ds)
    return np.c_[np.interp(ss, s, p[:, 0]), np.interp(ss, s, p[:, 1])]
def curvature(p, ds, win):
    q = np.c_[savgol_filter(p[:, 0], win, 3), savgol_filter(p[:, 1], win, 3)]
    d1 = np.gradient(q, ds, axis=0); d2 = np.gradient(d1, ds, axis=0)
    return (d1[:, 0] * d2[:, 1] - d1[:, 1] * d2[:, 0]) / np.linalg.norm(d1, axis=1) ** 3
def perp_height(u):
    """perpendicular face height at u: from the bottom point, along the bottom normal, to the top curve"""
    p = np.array([u, botv(u)]); t = unit([1, (botv(u + 1) - botv(u - 1)) / 2]); n = np.array([-t[1], t[0]])
    ss = np.linspace(0, 45, 4501); q = p[None] + ss[:, None] * n[None]
    j = np.argmin(np.abs(q[:, 1] - topv(q[:, 0]))); return p, q[j], float(ss[j])
hh_u = np.arange(-480, 601, 5.0); hh = np.array([perp_height(u)[2] for u in hh_u])
RS = json.load(open("parts/rocker_section.json"))["design"]; T_of = lambda u: float(np.interp(u, RS["u"], RS["T_mm"])); D_of = lambda u: float(np.interp(u, RS["u"], RS["d_outer_mm"]))

# ---------------- leg landings from the v<N> mesh ----------------
o_, eu_, ev_, en_ = SF_.side_plane(+1)
J = json.load(open(f"parts/model_v{a.model}_joinery.json"))["joints"]
def landing(name):
    m = world(name); rows = []
    for d in np.arange(-3.0, 41.0, 1.0):
        sec = m.section(plane_origin=o_ - d * en_, plane_normal=en_)
        if sec is None: continue
        Q = SF_.to_plane(sec.vertices, +1); gap = Q[:, 1] - topv(Q[:, 0]); k = gap < 1.0
        if k.sum() >= 2: rows.append((d, Q[k, 0].min(), Q[k, 0].max()))
    rows = np.array(rows); ax_ = np.array(J[name + "_foot"]["leg_axis"]); slope = float((ax_ @ eu_) / (ax_ @ ev_))
    d0 = D_of(rows[:, 1].mean()); outer = rows[np.argmin(np.abs(rows[:, 0] - (d0 + 0.5)))]
    # rear = the rear edge on the leg's outer face (what shows on the rocker's outer face); rearfar = the furthest-back point of the foot
    # across the thickness (the inner rear arris: the back legs' rear face is bevelled); front = the front face (flat, square across)
    return dict(rear=float(outer[1]), rearfar=float(rows[:, 1].min()), front=float(rows[:, 2].max()), outer_front=float(outer[2]),
                depth_mm=[float(rows[0, 0]), float(rows[-1, 0])], slope_du_dv=slope)
LG = {"BLEG": landing("BLEG_R"), "FLEG": landing("FLEG_R")}
legs = {}
for nm, side in (("BLEG", "bleg"), ("FLEG", "fleg")):
    for face in ("rear", "front", "rearfar"):
        u0 = LG[nm][face]; legs[f"{side}_{face}_lo"] = dict(u=u0, v=float(topv(u0)), slope_du_dv=LG[nm]["slope_du_dv"],
                                                            name=f"{'back' if nm == 'BLEG' else 'front'} leg, " + {"rear": "rear edge on the outer face", "front": "front face", "rearfar": "rear of the foot on the inner face"}[face])

# ---------------- key numbers ----------------
bot_rs = resample(bot_br, 2.0); kap_b = curvature(bot_rs, 2.0, 21)
# the form's working face: the bottom between the two end rounds (where the bottom's radius first stays above 150 mm, from each end)
okk = np.abs(kap_b) < 1 / 150.0
j0 = next(j for j in range(len(okk)) if okk[j:j + 5].all()); j1 = len(okk) - 1 - next(j for j in range(len(okk)) if okk[::-1][j:j + 5].all())
u_form0, u_form1 = float(bot_rs[j0, 0]), float(bot_rs[j1, 0])
wk = bot_rs[j0:j1 + 1]; kap_w = curvature(wk, 2.0, 41)                         # bending radius over ~80 mm windows
R_min_down = float(1 / (-kap_w[kap_w < 0]).max()) if (kap_w < 0).any() else np.inf
R_min_up = float(1 / kap_w[kap_w > 0].max()) if (kap_w > 0).any() else np.inf
# where the bend changes hand: drop the near-straight samples (|R| > 3000 mm), then each sign change is put mid-way across the gap
sg = np.where(kap_w > 1 / 3000, 1, np.where(kap_w < -1 / 3000, -1, 0)); nz = np.where(sg != 0)[0]
u_infl = [float((wk[i, 0] + wk[j, 0]) / 2) for i, j in zip(nz[:-1], nz[1:]) if sg[i] != sg[j]]
while any(b_ - a_ < 40 for a_, b_ in zip(u_infl[:-1], u_infl[1:])):          # a blip shorter than 40 mm is not a bend: drop the pair
    k_ = next(k for k in range(len(u_infl) - 1) if u_infl[k + 1] - u_infl[k] < 40); del u_infl[k_:k_ + 2]
reverses = len(u_infl) > 0
stations = np.arange(-400, 601, 100)

items = [dict(kind="cut", pts=outline, closed=True)]
xl = tip[0] - 10, u_front + 10
items.append(dict(kind="line", pts=[[xl[0], v_floor], [xl[1], v_floor]], style="hidden", label="FLOOR / table line, tangent to the rocker at the rest point", label_at=1))
items.append(dict(kind="line", pts=[[u_rest, v_floor - 6], [u_rest, topv(u_rest) + 8]], style="centre"))
items.append(dict(kind="text", xy=(u_rest, topv(u_rest) + 14), s=f"REST POINT (lowest point on the floor)\nrocking radius R {fmt(rp['rocking_radius_mm'], 0)}", size=6.5))
for j, su in enumerate(stations):
    items.append(dict(kind="line", pts=[[su, botv(su) - 4], [su, botv(su) + 3]], style="mark"))
    items.append(dict(kind="line", pts=[[su, topv(su) - 3], [su, topv(su) + 4]], style="mark"))
    items.append(dict(kind="text", xy=(su, topv(su) + 8), s=f"S{j + 1}  T {T_of(su):.1f}", size=5.5, color=K.MARK))
for key, l in legs.items():
    vv = np.array([l["v"] - 2, l["v"] + 45]); uu = l["u"] + l["slope_du_dv"] * (vv - l["v"])
    items.append(dict(kind="line", pts=np.stack([uu, vv], 1), style="hidden" if "rearfar" in key else "mark"))
for nm, side, lab in (("BLEG", "bleg", "BACK LEG"), ("FLEG", "fleg", "FRONT LEG")):
    um = (LG[nm]["rear"] + LG[nm]["front"]) / 2
    items.append(dict(kind="text", xy=(um + LG[nm]["slope_du_dv"] * 60, topv(um) + 62), s=f"{lab} lands here\n(model v{a.model} foot; dashed: rear\nof the foot on the inner face)", size=6, color=K.MARK))
for su in (-400, -200, 0, 200, 400, 560):
    p, q, h = perp_height(su)
    items.append(dict(kind="dim", p1=p, p2=q, off=0.0, label=f"{frac32(h)} ({h:.1f})", size=5.5))
chain = [("tail tip", float(tip[0])), ("back leg rear", LG["BLEG"]["rear"]), ("back leg front", LG["BLEG"]["front"]),
         ("rest point", u_rest), ("front leg rear", LG["FLEG"]["rear"]), ("front leg front", LG["FLEG"]["front"]), ("nose", u_front)]
for (n1, x1), (n2, x2) in zip(chain[:-1], chain[1:]):
    items.append(dict(kind="dim", p1=(x1, v_floor), p2=(x2, v_floor), off=-14, size=5.5))
items.append(dict(kind="dim", p1=(float(tip[0]), v_floor), p2=(u_front, v_floor), off=-30, label=f"overall length, tail tip to nose, along the floor: {fmt(L_total)}"))
h_tip = float(tip[1] - v_floor); h_nose = float(nose_c[1] - v_floor)
items.append(dict(kind="dim", p1=(tip[0], v_floor), p2=(tip[0], tip[1]), off=12, label=f"tip {frac32(h_tip)} ({h_tip:.1f})", size=5.5))
items.append(dict(kind="dim", p1=(nose_c[0], v_floor), p2=(nose_c[0], nose_c[1]), off=-14, label=f"{frac32(h_nose)} ({h_nose:.1f})", size=5.5))
items.append(dict(kind="text", xy=(nose_c[0] - 22, nose_c[1] + 10), s="nose top corner", size=5.5))
items.append(dict(kind="text", xy=(-150, 128),
    s="ROCKER, side profile, 1:1  (make 2)\nShown: right rocker's outer face, front to the right. Flip it for the left rocker.\n"
      "Bent lamination: glue up on the bending form (rocker_bending_form), bottom edge comes off the form;\n"
      "then lay this on the blank, match the bottom edge and stations S1-S11, and cut the top line and both ends.\n"
      "T = thickness across at the station (mm, outer face to inner face).",
    size=7, ha="left", va="center"))

TB = [
    f"Outline = model v{a.model}'s rocker (tools/build_model.py; this outline sits on the ROCKER_R mesh vertices to {mesh_dev:.3f} mm). Top: both rockers' outer",
    f"  faces traced on face orthophotos, faired, right aligned onto left and averaged (L vs R {RVL['residual_rms_mm']:.1f} mm rms). Bottom: traced directly in single",
    "  photos between the ends (parts/rocker_bottom.json). Tail tip and nose: triangulated, each end traced in 11-18 photos, L+R averaged (+-1.6 mm).",
    "  Frame: the build's half-way frame between the two rockers' sheets (design intent; each real rocker is about half the L/R difference from it).",
    f"Leg landings: where the v{a.model} leg feet (swept along the leg axis, cut by the rocker) meet the rocker top, side view across the thickness: +-2 mm.",
    "  The leg seats on the rocker are hand-fitted; scribe to the leg.",
    f"Thickness across T (parts/rocker_section.json, top-face arrises traced in single photos): {min(RS['T_mm']):.1f} at the tail to {max(RS['T_mm']):.1f} mm between the legs;",
    f"  the outer face bows {min(RS['d_outer_mm']):+.1f}..{max(RS['d_outer_mm']):+.1f} mm off the plane (not on this sheet). Scale: framing-square tick comb, 0.085 %.",
    f"Generated by templates/rocker.py from model v{a.model} inputs (parts/rocker_profile.json, rocker_bottom.json, rocker_ends.json, rocker_section.json) @ {REV}.",
]
KD = [("Overall length (along floor)", L_total, "tail tip to nose"),
      ("Rocking radius", rp["rocking_radius_mm"], "fitted over the contact zone"),
      ("Face height, max / at u -480", f"{frac32(hh.max())} / {frac32(hh[0])}  ({hh.max():.1f} / {hh[0]:.1f} mm)", "perpendicular to the bottom edge"),
      ("Tail tip above floor", h_tip, "triangulated tip"),
      ("Nose top corner above floor", h_nose, "triangulated corner"),
      ("Thickness across", f"{min(RS['T_mm']):.1f} - {max(RS['T_mm']):.1f} mm", "tail tip - between the legs"),
      ("Back leg on rocker (rear..front)", f"{frac32(LG['BLEG']['front'] - LG['BLEG']['rear'])} ({LG['BLEG']['front'] - LG['BLEG']['rear']:.1f} mm)", "side view, along u"),
      ("Front leg on rocker (rear..front)", f"{frac32(LG['FLEG']['front'] - LG['FLEG']['rear'])} ({LG['FLEG']['front'] - LG['FLEG']['rear']:.1f} mm)", "side view, along u"),
      ("Back leg front to front leg rear", LG["FLEG"]["rear"] - LG["BLEG"]["front"], "clear span along u")]
spec_t = dict(name="rocker_template", title=f"ESSICK rocker - rocker side template (make 2), model v{a.model}", rev=REV, items=items, title_block=TB, key_dims=KD)

# ---------------- bending form ----------------
S = a.stack_mm; EXT = 60.0
t0 = unit(wk[1] - wk[0]); t1 = unit(wk[-1] - wk[-2])
work = np.vstack([wk[0] - t0 * EXT, wk, wk[-1] + t1 * EXT])
tang = np.gradient(work, axis=0); tang /= np.linalg.norm(tang, axis=1)[:, None]; nrm = np.stack([-tang[:, 1], tang[:, 0]], 1)
caul_w = work + nrm * S
GAP = 70.0
base = work[:, 1].min() - 50; topc = caul_w[:, 1].max() + 40
form = np.vstack([work, [[work[-1, 0], base], [work[0, 0], base]]])
caul = np.vstack([caul_w + [0, GAP], [[caul_w[-1, 0], topc + GAP], [caul_w[0, 0], topc + GAP]]])
two_part = reverses
fi = [dict(kind="cut", pts=form, closed=True), dict(kind="cut", pts=caul, closed=True)]
fi.append(dict(kind="line", pts=caul_w, style="hidden"))
fi.append(dict(kind="text", xy=(work[0, 0] + 230, base + 22), s="LOWER FORM  (working face = rocker bottom = rocking surface)", size=8))
fi.append(dict(kind="text", xy=(work[0, 0] + 230, topc + GAP - 18), s=f"CAUL  (working face = rocker bottom offset {fmt(S)} = the stack)", size=8))
fi.append(dict(kind="text", xy=(250, (base + work[:, 1].min()) / 2 + 35), s="dashed: caul face where it sits on a full stack in the press", size=6, color=K.REF))
for j, su in enumerate(stations):
    i = int(np.argmin(np.abs(work[:, 0] - su))); p = work[i]; n = nrm[i]
    fi.append(dict(kind="line", pts=[p - n * 8, p], style="mark")); fi.append(dict(kind="text", xy=tuple(p - n * 13), s=f"S{j + 1}", size=6, color=K.MARK))
    q = caul_w[i] + [0, GAP]; fi.append(dict(kind="line", pts=[q, q + n * 8], style="mark"))
    fi.append(dict(kind="line", pts=[[p[0], base], [p[0], base + 6]], style="mark")); fi.append(dict(kind="line", pts=[[caul_w[i, 0], topc + GAP], [caul_w[i, 0], topc + GAP - 6]], style="mark"))
for e, lab in ((tip[0], "tail"), (u_front, "nose")):
    fi.append(dict(kind="line", pts=[[e, botv(min(max(e, bb[0, 0]), bb[-1, 0])) - 12], [e, botv(min(max(e, bb[0, 0]), bb[-1, 0])) + 4]], style="ref"))
fi.append(dict(kind="text", xy=(tip[0], botv(tip[0]) + 10), s="tail tip", size=5.5, color=K.REF))
fi.append(dict(kind="text", xy=(u_front, botv(u_front - 1) + 10), s="nose", size=5.5, color=K.REF))
fi.append(dict(kind="dim", p1=(work[0, 0], base), p2=(work[-1, 0], base), off=-12, label=f"form length {fmt(work[-1, 0] - work[0, 0])} (rocker bottom between the end rounds + {EXT:.0f} mm each end)"))
infl_txt = (f"the bottom curve reverses at u {', '.join(f'{x:.0f}' for x in u_infl)} ({', '.join(f'{u_rest - x:.0f}' for x in u_infl)} mm behind the rest point): an S, so use both halves, not a one-sided form."
            if reverses else "the bottom curve bends one way only, so a one-sided form would do; both halves are drawn.")
fi.append(dict(kind="text", xy=(-120, topc + GAP - 32),
    s=f"Laminations: {round(S / a.lam_mm)} x {frac32(a.lam_mm)} ({a.lam_mm:.2f} mm) = {fmt(S)} stack, strips at least {frac32(max(RS['T_mm']) + 4)} wide, {frac32(L_total + 2 * 40)} long.\n"
      f"Rocker face height is {frac32(hh.max())} ({hh.max():.1f} mm) at most, so the stack leaves {S - hh.max():.1f} mm to cut off the top.\n"
      f"Tightest bend: {fmt(R_min_down, 0)} (convex) and {fmt(R_min_up, 0)} (concave), over 80 mm;\n{infl_txt}\n"
      "Cut both halves from stacked ply/MDF at least the strip width; transfer stations S1-S11 to both, square across the faces. No spring-back\n"
      f"allowance is drawn (with {round(S / a.lam_mm)} laminations it is small); check the first glue-up against rocker_template and shim the caul if needed.\n"
      "The tail tip and the nose round are cut from the blank after glue-up (they lie past the form's working face).",
    size=6.6, ha="left", va="top"))
TBf = [f"Working face of the lower form = model v{a.model} rocker bottom (rocker_profile mean_bot + rocker_bottom correction, ends from rocker_ends) from u {u_form0:.0f}",
       f"  to u {u_form1:.0f} (where the end rounds begin: bottom radius < 150 mm), extended {EXT:.0f} mm along its end tangents.",
       f"Caul face = that curve offset {S:.2f} mm along its normal (--stack-mm; re-run templates/rocker.py if the stack changes).",
       "Accuracy as the rocker template: +-1.6 mm on the curve. Form outer faces (flat base / top) are free.",
       "The lamination plan (count, thickness) is a suggestion, not measured from the chair: glue lines were not resolved in the photos.",
       f"Generated by templates/rocker.py from model v{a.model} inputs @ {REV}."]
KDf = [("Stack (laminations)", S, f"{round(S / a.lam_mm)} x {frac32(a.lam_mm)}"), ("Form length", work[-1, 0] - work[0, 0], "working face"),
       ("Tightest bend radius", min(R_min_down, R_min_up), "over 80 mm"),
       ("Bottom curve reverses (S)", f"{len(u_infl)} x, at u {', '.join(f'{x:.0f}' for x in u_infl)}" if reverses else "no", "two-part form" if two_part else "one-sided would do")]
spec_f = dict(name="rocker_bending_form", title=f"ESSICK rocker - lamination bending form (lower form + caul), model v{a.model}", rev=REV, items=fi, title_block=TBf, key_dims=KDf)

os.makedirs(a.out, exist_ok=True)
Lt = K.write_all(spec_t, a.out); Lf = K.write_all(spec_f, a.out)
geom = dict(model=a.model, frame="design (build_model to_mean half-way frame); to_left = rigid(rotation_deg, shift_u, shift_v) forward",
            to_left=dict(rotation_deg=HALF[0], shift_u_mm=HALF[1], shift_v_mm=HALF[2]),
            outline=outline.tolist(), legs=legs, leg_feet=LG, tip=tip.tolist(), nose_corner=nose_c.tolist(), front_u=u_front, u_rest=u_rest, v_floor=v_floor,
            total_length=L_total, mesh_dev_mm=mesh_dev, stack_mm=S, R_min=[R_min_down, R_min_up], u_inflection=u_infl, two_part=two_part,
            form_u=[u_form0, u_form1], form_work=work.tolist(), caul_work=caul_w.tolist(), face_height_mm=[float(hh.min()), float(hh.max())],
            tiles=dict(template=[Lt["rows"], Lt["cols"]], form=[Lf["rows"], Lf["cols"]]))
json.dump(geom, open(a.geom_json or f"{a.out}/rocker_geom.json", "w"), indent=1)
print(f"rocker v{a.model}: mesh dev {mesh_dev:.4f} mm; length {L_total:.1f} mm ({frac32(L_total)}), tip {tip[0]:.1f},{h_tip:.1f}, nose corner {nose_c[0]:.1f},{h_nose:.1f}, front u {u_front:.1f}, rest u {u_rest:.0f} v {v_floor:.2f}")
for nm, l in LG.items(): print(f"  {nm} rear (outer face) {l['rear']:.1f}, rear (inner) {l['rearfar']:.1f}, front {l['front']:.1f} (width {l['front'] - l['rear']:.1f}); depth {l['depth_mm']}; slope {l['slope_du_dv']:.3f}")
print(f"face height {hh.min():.1f}..{hh.max():.1f}; form u {u_form0:.0f}..{u_form1:.0f}; bend R min {R_min_down:.0f} (convex) {R_min_up:.0f} (concave); inflections {[round(x) for x in u_infl]}")
print(f"tiles: template {Lt['rows']}x{Lt['cols']}, form {Lf['rows']}x{Lf['cols']}")
