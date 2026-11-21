"""USAGE: python3 -I tools/rocker_thickness/section.py work/thick/fit.json parts/rocker_section.json
Step 4. The design thickness across the rocker, per station, from fit.py's per-photo readings:
  - per side and station, the median over the photos taken from OUTBOARD of that rocker (camera on the outer-face side). Those see the
    inner arris as the far edge against the floor, and the outer arris as the near edge over the dark outer face: both traced cleanly
    (spread 0.2-1.0 mm). From inboard the far edge is the outer arris against a light floor of the same tone as the wood, and the trace
    often wanders into the top face (by eye: IMG_1529, 1559, 1496 at u 400-520); inboard medians are kept as a check only.
  - a station is dropped by eye where a leg's shadow crosses the top face (DROP below), and when its outboard spread (1.4826 x MAD) is over 2.0 mm or fewer than 6 outboard photos see it;
  - design = the mean of left and right (one side where only one is kept), then smoothed [1 2 1]/4 over neighbouring stations;
  - outside the stations the end value is held (the tail tip u -488.2, the nose end u ~660)."""
import sys, json, statistics as stt
F = json.load(open(sys.argv[1])); outp = sys.argv[2]
def ms(t):
    m = stt.median(t); return m, 1.4826 * stt.median([abs(x - m) for x in t])
DROP = {("L", 80.0): "the back leg's shadow lies across the top face just in front of the foot and the inner trace follows it (by eye: IMG_1528, 1522, 1509)"}
sides = {}
for S in "LR":
    rows = {}
    for st in F["sides"][S]:
        P = list(st["photos"].values()); o = [r for r in P if r["s"] > 0]; i = [r for r in P if r["s"] < 0]
        if len(o) < 3: continue
        m, sp = ms([r["T"] for r in o]); mi, spi = ms([r["T"] for r in i]) if len(i) >= 3 else (None, None)
        rows[st["u"]] = dict(T=round(m, 2), spread=round(sp, 2), n=len(o), kept=bool(sp <= 2.0 and len(o) >= 6 and (S, st["u"]) not in DROP), note=DROP.get((S, st["u"])),
                             d_out=round(stt.median([r["d_out"] for r in o]), 2), d_in=round(stt.median([r["d_in"] for r in o]), 2),
                             inboard_T=None if mi is None else round(mi, 2), inboard_spread=None if spi is None else round(spi, 2), inboard_n=len(i))
    sides[S] = rows
us = sorted(set(sides["L"]) | set(sides["R"]))
def interp(S, u):
    k = sorted(x for x, r in sides[S].items() if r["kept"]); lo = [x for x in k if x <= u]; hi = [x for x in k if x >= u]
    if not lo: return sides[S][hi[0]]["T"]
    if not hi: return sides[S][lo[-1]]["T"]
    a, b = lo[-1], hi[0]
    return sides[S][a]["T"] if a == b else sides[S][a]["T"] + (sides[S][b]["T"] - sides[S][a]["T"]) * (u - a) / (b - a)
raw = []
for u in us:
    v = [interp(S, u) for S in "LR" if sides[S].get(u, {}).get("kept")]
    raw.append(sum(v) / len(v) if v else (interp("L", u) + interp("R", u)) / 2)
sm = lambda r: [(r[max(j - 1, 0)] + 2 * r[j] + r[min(j + 1, len(r) - 1)]) / 4 for j in range(len(r))]
des = sm(raw)
# the outer face: per station the mean of the two sides' outer-arris positions (outboard median d_out; each side's own position is moved
# by the pose of each photo and by how that rocker sits, the mean of left and right is the design's), only where both sides are kept
# Not in the tail (u < -340): there the right side's outer trace sits 6-7 mm inward with most of its stations dropped, and the critique's
# outer arrises (left and right within 1.5 mm of the model at y -500..-400) do not confirm it; a trial that held the u -340 value (+0.9)
# to the tip made the tail's critique worse. So the offset runs linearly from its u -340 value to 0 at u -420 and is 0 on to the tip
# (the traced tail end of PR #23 keeps its outer face).
both = [u for u in us if u >= -340 and sides["L"].get(u, {}).get("kept") and sides["R"].get(u, {}).get("kept")]
dmean = {u: (sides["L"][u]["d_out"] + sides["R"][u]["d_out"]) / 2 for u in both}
def dint(u):
    lo = [x for x in both if x <= u]; hi = [x for x in both if x >= u]
    if u <= -420: return 0.0
    if not lo: return dmean[hi[0]] * (u + 420) / (hi[0] + 420)
    if not hi: return dmean[lo[-1]]
    a, b = lo[-1], hi[0]; return dmean[a] if a == b else dmean[a] + (dmean[b] - dmean[a]) * (u - a) / (b - a)
d_raw = [dint(u) for u in us]; d_des = sm(d_raw)
out = {"what": "the rockers' thickness across (outer face to inner face, square to the side plane), measured on the top face in single photos (tools/rocker_thickness/); read by tools/build_model.py, which extrudes the rocker outline from depth d_outer(u) (the outer face) to d_outer(u) + T(u) inward, instead of from 0 to a constant 31 mm",
       "frame": "u along the rocker in the build's design frame (the half-way frame the outline is extruded in, as parts/rocker_ends.json's design); tail tip u -488.2, nose top corner u 626.7; T in mm; d_outer in mm INWARD from the old model's outer face (side_plane), negative = outward",
       "rule": "T(u) and d_outer(u) linear between the design stations, the end values held beyond them (tail tip to u -480, u 620 to the nose end). d_outer is the mean of the two sides' measured outer arris (outboard medians) where both sides are kept, from u -340 on; it runs to 0 at u -420 and is 0 to the tail tip. The side outlines (rocker_profile, rocker_ends, rocker_bottom) are unchanged; both rockers get the design mean (the right is a mirror of the left, as before). The left/right difference in the outer face's position (right: 5-6 mm inward at the rear, 4-5 mm outward at the front; left: 2-4 mm outward at the rear, 0-2 mm inward at the nose) is how each rocker sits, not its section: not modelled (placement, joinery session).",
       "design": {"u": us, "T_mm": [round(x, 2) for x in des], "T_raw_mm": [round(x, 2) for x in raw],
                  "d_outer_mm": [round(x, 2) for x in d_des], "d_outer_raw_mm": [round(x, 2) for x in d_raw]},
       "tolerance_mm": {"per_station_reading": "0.2-1.0 (outboard spread / sqrt(n) about 0.1-0.3)", "absolute": 1.6,
                        "absolute_why": "the arris easing bias of the trace is calibrated only by the tape at the tail tip (IMG_1493: 1.20 in = 30.5 +-1.6 mm, 15-25 mm from the tip, u about -470): the ribbon reads 29.3 (left) and 30.2 (right) there, so the bias is -0.8 +-1.6 mm, i.e. not resolved; T is not corrected for it",
                        "left_vs_right": "the two rockers differ by up to 1.5 mm (right thicker between the legs, thinner at the nose); the design is their mean"},
       "left": sides["L"], "right": sides["R"],
       "old_model": {"T_mm": 31.0, "source": "tape IMG_1493 at the tail tip, assumed constant"},
       "method": "per photo and side: an orthophoto ribbon on the model's top face (u 1 mm x d 0.1 mm, d inward from the model's outer face), only the columns where the joined model shows the rocker's top unoccluded and the camera sees the top face > 8 deg; both arrises traced as the strongest Lab step in an outer (d -7..9) and inner (d 22..41) band with contrast >= 8 and within 1 mm of the 21-column running median; per station (+-10 mm) the photo's median d_in - d_out over >= 5 columns; photos with >= 5 stations. Thickness is a difference of two arrises in one photo, so a pose or height error moves both and cancels; the parallax term from an inner/outer height difference fitted with both camera sides is |k| < 0.6 mm almost everywhere (fit.py), and the outboard readings show no trend with elevation (8-80 deg).",
       "provenance": "tools/rocker_thickness/{ribbon,trace,fit,section}.py on the 92 solved photos; by-eye checks tools/rocker_thickness/view.py (figures/rocker_thickness/)"}
json.dump(out, open(outp, "w"), indent=1)
for u, r, d in zip(us, raw, des):
    L, R = sides["L"].get(u), sides["R"].get(u)
    f = lambda q: "  --  " if q is None else ("%5.2f%s" % (q["T"], " " if q["kept"] else "x"))
    print("u %5.0f  L %s  R %s  raw %5.2f  design %5.2f   outer: L %s R %s design %+5.2f" % (u, f(L), f(R), r, d,
          "  -  " if L is None else "%+5.2f" % L["d_out"], "  -  " if R is None else "%+5.2f" % R["d_out"], d_des[us.index(u)]))
