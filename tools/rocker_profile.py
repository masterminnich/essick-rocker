"""USAGE: python -I tools/rocker_profile.py --left work/parts/rockerL/trace.json --right work/parts/rockerR/trace.json --out parts/rocker_profile.json [--plot parts/rocker_profile.png]
Turn the traced top/bottom edges of the two rockers' outer side faces into one fair side profile (design intent):
 - robust smoothing-spline fit of each edge (kinks and mis-traces rejected),
 - bottom edge in the table-contact zone taken as top edge minus the face height interpolated from the reliable zones
   (there the bottom arris is hidden in its own contact shadow),
 - right rocker rigidly aligned (2D rotation + shift) onto the left; residual = shape repeatability left vs right,
 - mean profile, face height along the length, best-fit rocking radius over the contact zone.
Plane coordinates: u = along the rocker (front positive), v = up, mm. Tiny compute."""
import json, argparse, numpy as np
from scipy.interpolate import UnivariateSpline
from scipy.optimize import least_squares
ap = argparse.ArgumentParser(); ap.add_argument("--left", required=True); ap.add_argument("--right", required=True); ap.add_argument("--out", required=True); ap.add_argument("--plot", default=None)
ap.add_argument("--contact", nargs=2, type=float, default=[45, 345]); ap.add_argument("--urange", nargs=2, type=float, default=[-480, 620])
a = ap.parse_args()
U = np.arange(a.urange[0], a.urange[1] + 0.1, 5.0)

def robust_spline(u, v, s_per_pt=0.15, iters=5, clip=1.0):
    o = np.argsort(u); u, v = u[o], v[o]; keep = np.r_[True, np.diff(u) > 1e-6]; u, v = u[keep], v[keep]
    w = np.ones(len(u))
    for _ in range(iters):
        sp = UnivariateSpline(u, v, w=w, k=3, s=s_per_pt * w.sum())
        r = np.abs(v - sp(u)); w = (r < clip).astype(float) + 1e-3
    return sp, (r < clip).mean(), np.sqrt(np.mean(r[r < clip] ** 2))

def side(fn):
    d = json.load(open(fn)); ea, eb = np.array(d["rocker_a"]), np.array(d["rocker_b"])
    top, ft, nt = robust_spline(ea[:, 0], ea[:, 1])
    rel = (eb[:, 0] < a.contact[0]) | (eb[:, 0] > a.contact[1])
    # reject bottom mis-traces: face height must follow a smooth trend along the rocker (clip at 1.5 mm)
    w = np.linalg.norm(ea - eb, axis=1); good = rel.copy()
    for _ in range(6):
        pf = np.polyfit(ea[good, 0], w[good], 4); good = rel & (np.abs(w - np.polyval(pf, ea[:, 0])) < 1.5)
    rel = good
    bot_rel, fb, nb = robust_spline(eb[rel, 0], eb[rel, 1])
    # face height where the bottom is reliable, measured vertically then converted with the slope
    ur = U[(U < a.contact[0] - 10) | (U > a.contact[1] + 10)]
    slope = top.derivative()(ur); h = (top(ur) - bot_rel(ur)) * np.cos(np.arctan(slope))
    hs = UnivariateSpline(ur, h, k=2, s=len(ur) * 0.25)
    hU = hs(U); slopeU = top.derivative()(U)
    bot = top(U) - hU / np.cos(np.arctan(slopeU))
    return dict(top=top(U), bot=bot, height=hU, top_fit_inlier=ft, top_noise=nt, bot_fit_inlier=fb, bot_noise=nb)

L, R = side(a.left), side(a.right)
# rigid 2D alignment of right onto left using both edges
def tf(p, u, v):
    c, s = np.cos(p[0]), np.sin(p[0]); return c * u - s * v + p[1], s * u + c * v + p[2]
def res(p):
    out = []
    for key in ("top", "bot"):
        u2, v2 = tf(p, U, R[key]); out.append(np.interp(U[8:-8], u2, v2) - L[key][8:-8])
    return np.concatenate(out)
fit = least_squares(res, [0, 0, 0]); r = res(fit.x)
Ra = {}
for key in ("top", "bot"):
    u2, v2 = tf(fit.x, U, R[key]); Ra[key] = np.interp(U, u2, v2)
mean_top, mean_bot = (L["top"] + Ra["top"]) / 2, (L["bot"] + Ra["bot"]) / 2
# rocking radius: circle through the mean bottom edge over the contact zone
m = (U > a.contact[0] - 120) & (U < a.contact[1] + 60)
def cres(p): return np.hypot(U[m] - p[0], mean_bot[m] - p[1]) - p[2]
cf = least_squares(cres, [150, 2500, 2500])
out = {"u": U.tolist(), "left": {k: (v.tolist() if hasattr(v, "tolist") else float(v)) for k, v in L.items()},
       "right_aligned_to_left": {k: v.tolist() for k, v in Ra.items()}, "mean_top": mean_top.tolist(), "mean_bot": mean_bot.tolist(),
       "right_vs_left": {"rotation_deg": float(np.degrees(fit.x[0])), "shift_u_mm": float(fit.x[1]), "shift_v_mm": float(fit.x[2]),
                         "residual_rms_mm": float(np.sqrt(np.mean(r ** 2))), "residual_max_mm": float(np.abs(r).max())},
       "rocking_radius_mm": float(cf.x[2]), "rocking_radius_fit_rms_mm": float(np.sqrt(np.mean(cf.fun ** 2))),
       "face_height_mm": {"left": L["height"].tolist(), "right": R["height"].tolist()}}
json.dump(out, open(a.out, "w"), indent=1)
print(f"edge trace noise (rms about the fair curve): L top {L['top_noise']:.2f} bot {L['bot_noise']:.2f} | R top {R['top_noise']:.2f} bot {R['bot_noise']:.2f} mm")
print(f"inlier share: L top {L['top_fit_inlier']:.2f} bot {L['bot_fit_inlier']:.2f} | R top {R['top_fit_inlier']:.2f} bot {R['bot_fit_inlier']:.2f}")
print(f"right vs left as found: rotation {np.degrees(fit.x[0]):+.3f} deg, shift u {fit.x[1]:+.2f}, v {fit.x[2]:+.2f} mm")
print(f"after alignment, left vs right shape: rms {np.sqrt(np.mean(r ** 2)):.2f} mm, max {np.abs(r).max():.2f} mm")
hh = (L["height"] + R["height"]) / 2
for uu in (-450, -300, -150, 0, 150, 300, 450, 600):
    i = int(np.argmin(np.abs(U - uu))); print(f"  u {uu:5d}: face height L {L['height'][i]:.2f}  R {R['height'][i]:.2f}  mean {hh[i]:.2f} mm ({hh[i] / 25.4:.3f} in)")
print(f"rocking radius over the contact zone: {cf.x[2]:.0f} mm ({cf.x[2] / 25.4:.1f} in), fit rms {np.sqrt(np.mean(cf.fun ** 2)):.2f} mm")
print(f"overall: length along u {U[-1] - U[0]:.0f} mm; tail rise {mean_top[0]:.0f} mm; front tip rise {mean_top[-1]:.0f} mm; lowest bottom {mean_bot.min():.1f} mm at u = {U[np.argmin(mean_bot)]:.0f}")
if a.plot:
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    fig, ax = plt.subplots(3, 1, figsize=(13, 9), gridspec_kw={"height_ratios": [3, 1.3, 1.3]})
    ax[0].plot(U, L["top"], "b-", lw=1, label="left rocker"); ax[0].plot(U, L["bot"], "b-", lw=1)
    ax[0].plot(U, Ra["top"], "r-", lw=1, label="right rocker (aligned)"); ax[0].plot(U, Ra["bot"], "r-", lw=1)
    ax[0].plot(U, mean_top, "k--", lw=0.8, label="mean (design intent)"); ax[0].plot(U, mean_bot, "k--", lw=0.8)
    ax[0].set_aspect("equal"); ax[0].grid(alpha=.3); ax[0].legend(); ax[0].set_title("Rocker outer side face, true shape (mm). Front of chair to the right.")
    ax[1].plot(U, L["top"] - Ra["top"], "g-", label="top edge: left minus right"); ax[1].plot(U, L["bot"] - Ra["bot"], "m-", label="bottom edge: left minus right")
    ax[1].axhspan(-1.6, 1.6, color="k", alpha=.06); ax[1].axhspan(-0.8, 0.8, color="k", alpha=.08); ax[1].grid(alpha=.3); ax[1].legend(); ax[1].set_ylabel("mm")
    ax[1].set_title("Left vs right after rigid alignment (bands: 1/32 in and 1/16 in)")
    ax[2].plot(U, L["height"], "b-", label="left"); ax[2].plot(U, R["height"], "r-", label="right"); ax[2].grid(alpha=.3); ax[2].legend(); ax[2].set_ylabel("mm"); ax[2].set_title("Side-face height along the rocker")
    plt.tight_layout(); plt.savefig(a.plot, dpi=110)
