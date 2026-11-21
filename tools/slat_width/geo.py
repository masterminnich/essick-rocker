"""The model's slat sections from parts/slats.json, exactly as tools/build_model.py sweeps them (not a CLI)."""
import numpy as np


def tables(sh):
    tb = np.array(sh["table"]); z = np.linspace(tb[0, 0], tb[-1, 0], 4000); y = np.interp(z, tb[:, 0], tb[:, 1])
    return z, y, np.r_[0, np.cumsum(np.hypot(np.diff(z), np.diff(y)))]


def stations(SL, slat, zc_all):
    """at section heights zc_all: centre c (n,3), axis tau, width direction e1 (outward; SLAT_C: +x), forward f
    (square to the back face), width w (along e1), thickness t, sheet arc length v"""
    SY = SL["symmetric"]; TH = float(SL["thickness_mm"])
    key, lo_c, hi_c, sg = (("sheet_centre", SY["centre_half"], SY["centre_half"], -1.0) if slat == "SLAT_C"
                           else ("sheet_outer", SY["outer_in"], SY["outer_out"], 1.0))
    zt, yt, st = tables(SL[key]); ds_t = np.gradient(yt, zt)
    vs = np.interp(zc_all, zt, st)                      # back-face z ~ centre z (t/2 x slope is < 1 mm)
    vcl = np.clip(vs, *SL["v_range"])
    zs, ys, ds = np.interp(vs, st, zt), np.interp(vs, st, yt), np.interp(vs, st, ds_t); nr = np.hypot(1, ds)
    f = np.c_[np.zeros(len(vs)), 1 / nr, -ds / nr]
    tau = np.c_[np.zeros(len(vs)), ds / nr, 1 / nr]
    lo, hi = np.polyval(lo_c, vcl) * sg, np.polyval(hi_c, vcl)
    xm = (lo + hi) / 2; w = hi - lo
    c = np.c_[xm, ys, zs] + f * TH / 2
    e1 = np.tile([1.0, 0, 0], (len(vs), 1))
    if slat == "SLAT_L":
        c[:, 0] *= -1; e1[:] = [-1.0, 0, 0]
    return dict(z=c[:, 2], c=c, tau=tau, e1=e1, f=f, w=w, t=np.full(len(vs), TH), v=vs)
