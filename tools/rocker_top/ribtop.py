"""USAGE: python3 -I tools/rocker_top/ribtop.py work/rbot/trace3.json OUT.json [REF_U0,REF_U1]
Top edge of each rocker in single photos (PR #29 ribbon traces, t = square distance to that side's own traced top in rocker_profile.json,
+ = wood above the profile). Per photo: remove (a) a constant = median over the reference stretch, (b) a line fitted over the reference stretch;
read the median residual in the test stretches. Pose-free for a shift (a) or a shift + rotation (b)."""
import sys, json, numpy as np
T = json.load(open(sys.argv[1])); REF = tuple(map(float, sys.argv[3].split(","))) if len(sys.argv) > 3 else (-100.0, 300.0)
TESTS = {"tail -344..-300": (-344, -300), "tail -300..-250": (-300, -250), "rear -250..-150": (-250, -150), "mid -100..0": (-100, 0), "mid 0..100": (0, 100), "mid 100..200": (100, 200), "mid 200..300": (200, 300), "front 300..400": (300, 400), "nose 400..500": (400, 500), "nose 500..589": (500, 590)}
HO = set(x[4:8] for x in json.load(open('tools/critique/holdout.json'))['held_out'])
out = {}
for S in "LR":
    u = np.array(T[S]["u"]); res = {}
    print(f"== {S}: photo  cam(u,v,h)  | per test stretch: residual after shift / after shift+rotation (mm, + = wood above profile)")
    for ph, P in T[S]["photos"].items():
        t = np.array([np.nan if v is None else v for v in P["top_t"]], float); ok = np.array(P["top_ok"], bool) & np.isfinite(t)
        r = ok & (u >= REF[0]) & (u <= REF[1])
        if r.sum() < 100: continue
        c0 = np.median(t[r]); cf = np.polyfit(u[r], t[r], 1)
        row = {}
        for k, (a, b) in TESTS.items():
            s = ok & (u >= a) & (u < b)
            if s.sum() < 15: continue
            row[k] = (float(np.median(t[s] - c0)), float(np.median(t[s] - np.polyval(cf, u[s]))), int(s.sum()))
        res[ph] = dict(row=row, slope_mrad=float(cf[0] * 1000), ref_n=int(r.sum()), cam=P["cam_u_v_height"])
        print(f"{S} {ph}{'*' if ph in HO else ' '} cam {np.round(P['cam_u_v_height']).astype(int).tolist()} slope {cf[0]*1000:+.2f} mrad | " + "  ".join(f"{k.split()[1]}: {v[0]:+.2f}/{v[1]:+.2f}" for k, v in row.items()))
    for k in TESTS:
        A = np.array([res[p]["row"][k][:2] for p in res if k in res[p]["row"]])
        if len(A) < 2: continue
        mad = lambda x: 1.4826 * np.median(np.abs(x - np.median(x)))
        print(f"  {S} {k}: n {len(A)}  shift-only median {np.median(A[:,0]):+.2f} (spread {mad(A[:,0]):.2f})  shift+rot median {np.median(A[:,1]):+.2f} (spread {mad(A[:,1]):.2f})")
    sl = np.array([res[p]['slope_mrad'] for p in res]); print(f"  {S} ref-stretch slope mrad median {np.median(sl):+.3f} spread {1.4826*np.median(np.abs(sl-np.median(sl))):.3f}")
    out[S] = res
json.dump(out, open(sys.argv[2], "w"), indent=0)
