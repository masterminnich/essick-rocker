"""USAGE: work/toolkit/rk.sh tools/critique/stats.py RUNDIR OUT.json [--holdout tools/critique/holdout.json] [--min-photos 3] [--min-points 15]
Phase 6 critique, step 2: robust statistics of the gaps written by measure.py.

Region = member (ARM, FLEG, BLEG, ROCKER, SLAT_LR = the two side slats, SEAT, CREST, SLAT_C) x kind (sil / crease) x edge
(the classes of the edge's two faces in the part's mirrored frame: e.g. "outer/top" = the outer top arris; one word = a
silhouette across a smooth face) x stretch (50 mm of the along-coordinate: y, z or x = |x|), separately for the LEFT and RIGHT
member (SEAT, CREST, SLAT_C: left and right halves, x < -15 / x > 15; |x| <= 15 is "C").
Per region and side, every photo gives the median of its points; the region's value is the MEDIAN OVER PHOTOS (one photo
cannot dominate), its spread 1.4826 x the MAD over photos, se = 1.2533 x spread / sqrt(n photos).
Paired regions: symmetric = (left + right) / 2 = what a symmetric model can fix; antisymmetric = (left - right) / 2 = the
chair's (or the solve's) own left/right difference, which the left/right-mean design cannot fix (reported, not ranked).
Ranking uses the NON-held-out photos only and SILHOUETTES only (a crease is a tone edge between two lit faces; on an eased
arris it moves with the light, so creases are reported, not ranked); held-out medians are reported next to them.
Tolerance per region: 0.8 mm if most of its points lie within 20 mm of another part (joints, hard points), else 1.6 mm.
Sign: + = the model sticks out beyond the wood, - = the model lies inside the wood."""
import sys, json, argparse
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import PARTS, CLASSES, BIN_MM  # noqa
import numpy as np

ap = argparse.ArgumentParser(); ap.add_argument("run"); ap.add_argument("out")
ap.add_argument("--holdout", default=str(Path(__file__).resolve().parent / "holdout.json"))
ap.add_argument("--min-photos", type=int, default=3); ap.add_argument("--min-points", type=int, default=15)
a = ap.parse_args()
HO = set(json.load(open(a.holdout))["held_out"])
AXN = ["y", "z", "x"]   # x = |x|
MEMBER = {"ARM_L": "ARM", "ARM_R": "ARM", "FLEG_L": "FLEG", "FLEG_R": "FLEG", "BLEG_L": "BLEG", "BLEG_R": "BLEG",
          "ROCKER_L": "ROCKER", "ROCKER_R": "ROCKER", "SLAT_L": "SLAT_LR", "SLAT_R": "SLAT_LR"}

recs = []   # (region, side, photo, held, gaps, joint fraction, k)
status = {}
for f in sorted(Path(a.run).glob("IMG_*.npz")):
    name = f.stem + ".JPG"; R = dict(np.load(f)); held = name in HO
    part = np.array(PARTS)[R["part"]]
    mem = np.array([MEMBER.get(p, p) for p in part])
    side = np.where(R["side"] > 0, "R", np.where(R["side"] < 0, "L", "C"))
    kind = np.where(R["kind"] == 1, "sil", "crease")
    c1, c2 = R["c1"], R["c2"]
    edge = np.where(c1 == c2, np.array(CLASSES)[c1], np.char.add(np.char.add(np.array(CLASSES)[c1], "/"), np.array(CLASSES)[c2]))
    b0 = (np.floor(R["along"] / BIN_MM) * BIN_MM).astype(int)
    stretch = np.char.add(np.char.add(np.array(AXN)[R["ax"]], " "), b0.astype(str))
    key = np.char.add(np.char.add(np.char.add(np.char.add(np.char.add(np.char.add(mem, "|"), kind), "|"), edge), "|"), stretch)
    full = np.char.add(np.char.add(key, "#"), side)
    for kk in np.unique(full):
        s = full == kk
        st = R["st"][s]
        d = status.setdefault(kk, np.zeros(6, int))
        d += [s.sum(), (st < 10).sum(), (st == 0).sum(), (st == 1).sum(), (st == 2).sum(), (st == 3).sum()]
        ok = s & (R["st"] == 0)
        if ok.sum():
            reg, sd = kk.split("#")
            recs.append((reg, sd, name, held, R["gap"][ok].astype(float), float(R["joint"][ok].mean()), float(np.median(R["k"][ok]))))


def summarise(rows):
    if not rows: return None
    med = np.array([np.median(r[4]) for r in rows]); npt = sum(len(r[4]) for r in rows)
    m = float(np.median(med)); spread = float(1.4826 * np.median(np.abs(med - m))) if len(med) > 1 else float("nan")
    return dict(n_photos=len(rows), n_points=int(npt), median=round(m, 3), spread=round(spread, 3),
                se=round(1.2533 * spread / np.sqrt(len(rows)), 3) if len(rows) > 1 else None,
                joint_frac=round(float(np.average([r[5] for r in rows], weights=[len(r[4]) for r in rows])), 2),
                ease_k=round(float(np.median([r[6] for r in rows])), 3), photos=sorted(r[2][4:8] for r in rows))


by = {}
for r in recs: by.setdefault((r[0], r[1]), []).append(r)
regions = sorted({r[0] for r in recs} | {k.split("#")[0] for k in status})
out = []
for reg in regions:
    mem, kind, edge, stretch = reg.split("|")
    e = dict(region=reg, member=mem, kind=kind, edge=edge, stretch=stretch, sides={})
    for sd in ("L", "R", "C"):
        rows = by.get((reg, sd), [])
        tr = summarise([r for r in rows if not r[3]]); ho = summarise([r for r in rows if r[3]])
        cnt = status.get(f"{reg}#{sd}")
        if cnt is None: continue
        e["sides"][sd] = dict(train=tr, held=ho, outline_points=int(cnt[0]), searched=int(cnt[1]), measured=int(cnt[2]),
                              low_contrast=int(cnt[3]), ambiguous=int(cnt[4]), at_band_end=int(cnt[5]))
    ok = lambda sd: (sd in e["sides"] and e["sides"][sd]["train"] and e["sides"][sd]["train"]["n_photos"] >= a.min_photos
                     and e["sides"][sd]["train"]["n_points"] >= a.min_points)
    okh = lambda sd: sd in e["sides"] and e["sides"][sd]["held"] is not None
    jf = np.mean([e["sides"][s]["train"]["joint_frac"] for s in e["sides"] if e["sides"][s]["train"]] or [0])
    e["tol_mm"] = 0.8 if jf > 0.5 else 1.6
    if ok("L") and ok("R"):
        L, R_ = e["sides"]["L"]["train"], e["sides"]["R"]["train"]
        e["symmetric"] = round((L["median"] + R_["median"]) / 2, 3); e["antisymmetric"] = round((L["median"] - R_["median"]) / 2, 3)
        e["sym_se"] = round(0.5 * np.hypot(L["se"] or 0, R_["se"] or 0), 3); e["paired"] = True
        if okh("L") and okh("R"):
            e["held_symmetric"] = round((e["sides"]["L"]["held"]["median"] + e["sides"]["R"]["held"]["median"]) / 2, 3)
        e["n_photos"] = L["n_photos"] + R_["n_photos"]
    else:
        one = [s for s in ("L", "R", "C") if ok(s)]
        if one:
            s = one[0]; T = e["sides"][s]["train"]
            e["symmetric"] = T["median"]; e["antisymmetric"] = None; e["sym_se"] = T["se"]; e["paired"] = False; e["one_side"] = s
            if okh(s): e["held_symmetric"] = e["sides"][s]["held"]["median"]
            e["n_photos"] = T["n_photos"]
    if "symmetric" in e and kind == "sil":     # creases (tone edges between two faces) are reported, not ranked
        e["score"] = round(abs(e["symmetric"]) / e["tol_mm"], 3)
    out.append(e)
ranked = sorted([e for e in out if "score" in e], key=lambda e: -e["score"])
for i, e in enumerate(ranked): e["rank"] = i + 1
allp = sorted({r[2] for r in recs})
res = dict(run=a.run, sign="+ = model outside the wood (too big), - = model inside the wood", holdout=sorted(HO),
           photos_used=len([p for p in allp if p not in HO]), photos_held=len([p for p in allp if p in HO]),
           min_photos=a.min_photos, min_points=a.min_points, bin_mm=BIN_MM, regions=out)
Path(a.out).write_text(json.dumps(res, indent=1))
print(f"{len(out)} regions, {len(ranked)} ranked; photos used {res['photos_used']}, held out {res['photos_held']}")
print(f"{'rk':>3} {'region':52s} {'sym':>6} {'anti':>6} {'se':>5} {'tol':>4} {'nL':>3} {'nR':>3} {'held':>6}")
for e in ranked[:60]:
    sL = e["sides"].get("L", {}).get("train") or {}; sR = e["sides"].get("R", {}).get("train") or {}
    an = e.get("antisymmetric"); hs = e.get("held_symmetric")
    print(f"{e['rank']:3d} {e['region']:52s} {e['symmetric']:+6.2f} {an if an is not None else float('nan'):+6.2f} {e['sym_se'] or 0:5.2f} {e['tol_mm']:4.1f} {sL.get('n_photos', 0):3d} {sR.get('n_photos', 0):3d} {hs if hs is not None else float('nan'):+6.2f}")
