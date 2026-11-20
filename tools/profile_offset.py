"""USAGE: python -I tools/profile_offset.py --profile parts/back_profile.json --key slats --new slats_back_c --bands "v0 v1 off; v0 v1 off; ..."
Make a corrected side profile: move the base profile along its normal (positive = towards the back of the chair) by an
offset that varies along the part, given per band of v (arc length from the profile start, mm) as found by
tools/sheet_ortho.py --sweep --score-v. Offsets are interpolated between band centres. Writes a tabulated profile."""
import json, argparse, numpy as np
ap = argparse.ArgumentParser(); ap.add_argument("--profile", required=True); ap.add_argument("--key", required=True); ap.add_argument("--new", required=True); ap.add_argument("--bands", required=True)
ap.add_argument("--note", default=""); a = ap.parse_args()
P = json.load(open(a.profile)); pr = P[a.key]
if "table" in pr: tb = np.array(pr["table"]); zt = np.linspace(tb[0, 0], tb[-1, 0], 2000); yt = np.interp(zt, tb[:, 0], tb[:, 1])
else: zt = np.linspace(pr["z"][0], pr["z"][1], 2000); yt = np.polyval(np.array(pr["coef"]), zt)
d = np.gradient(yt, zt); st = np.r_[0, np.cumsum(np.hypot(np.diff(zt), np.diff(yt)))]
B = np.array([[float(x) for x in b.split()] for b in a.bands.split(";") if b.strip()]); vc = (B[:, 0] + B[:, 1]) / 2
off = np.interp(st, vc, B[:, 2]); k = np.ones(81) / 81; off = np.convolve(np.r_[off[:1].repeat(40), off, off[-1:].repeat(40)], k, "valid")     # smooth over ~30 mm
nrm = np.hypot(1, d); y2 = yt - off / nrm; z2 = zt + off * d / nrm; o = np.argsort(z2)
P[a.new] = {"table": np.c_[z2[o][::5], y2[o][::5]].tolist(), "from": a.key, "bands": B.tolist(), "note": a.note}
json.dump(P, open(a.profile, "w"), indent=1); print(a.new, "offsets at band centres:", np.interp(vc, st, off).round(1).tolist())
