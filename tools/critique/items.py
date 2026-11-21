"""USAGE: python3 -I tools/critique/items.py STATS.json [OUT.json]
Phase 6 critique, step 3: from the per-stretch statistics (stats.py) to a ranked list of fix ITEMS.
A stretch counts when it is a silhouette, holds >= 6 photos in all (left + right, non-held-out), its symmetric gap is beyond
the region's tolerance and beyond 2 se. Neighbouring counting stretches of the same edge with the same sign (gaps of one
stretch allowed) form one item. Item value = median of its stretches' symmetric gaps; ranked by |value| / tolerance, then by
length. Each item carries the antisymmetric range, the held-out symmetric values and an owner (whose file would fix it)."""
import sys, json
d = json.load(open(sys.argv[1]))
EDGE_WORDS = {"top": "top", "bottom": "bottom", "outer": "outer face", "inner": "inner face", "front": "front", "back": "back"}


def owner(mem, edge, stretch):
    ax, v = stretch.split(); v = int(v)
    if mem in ("FLEG", "BLEG") and v < 100: return "joinery session (feet on the rockers: `tools/joinery.py`, leg placement)"
    if mem == "FLEG" and v >= 590: return "joinery session (leg top / arm joint) or hub front-leg outline"
    if mem == "FLEG": return "hub (front-leg outline: `parts/side_frame.json`, `tools/build_model.py` front leg)"
    if mem == "BLEG": return "joinery session (back-leg outline code in `tools/build_model.py`)"
    if mem == "ARM": return ("hub (`parts/arm_underside.json`)" if "bottom" in edge else
                            "crest-arms data, frozen (`parts/arms.json`): a doubt, fix through a new hub file")
    if mem == "CREST": return "crest-arms data, frozen (`parts/crest.json`): a doubt, fix through a new hub file"
    if mem == "ROCKER": return "hub (rocker block of `tools/build_model.py`; `parts/rocker_profile.json` is not to change)"
    if mem == "SEAT": return "hub (SEAT in `tools/build_model.py`, `parts/seat_*.json`)"
    if mem.startswith("SLAT"): return "hub (slats in `tools/build_model.py`)"
    return "?"


regs = [e for e in d["regions"] if e["kind"] == "sil" and "symmetric" in e]
by = {}
for e in regs: by.setdefault((e["member"], e["edge"], e["stretch"].split()[0]), []).append(e)
items = []
for (mem, edge, ax), rs in by.items():
    rs.sort(key=lambda e: int(e["stretch"].split()[1]))
    def counts(e):
        se = e.get("sym_se") or 0
        return e.get("n_photos", 0) >= 6 and abs(e["symmetric"]) > e["tol_mm"] and abs(e["symmetric"]) > 2 * se
    cur = []
    def flush():
        if not cur: return
        sy = sorted(e["symmetric"] for e in cur); med = sy[len(sy) // 2] if len(sy) % 2 else 0.5 * (sy[len(sy) // 2 - 1] + sy[len(sy) // 2])
        an = [e["antisymmetric"] for e in cur if e.get("antisymmetric") is not None]
        ho = [e["held_symmetric"] for e in cur if e.get("held_symmetric") is not None]
        lo, hi = int(cur[0]["stretch"].split()[1]), int(cur[-1]["stretch"].split()[1]) + 50
        tol = min(e["tol_mm"] for e in cur)
        items.append(dict(member=mem, edge=edge, axis=ax, from_mm=lo, to_mm=hi, n_stretches=len(cur), symmetric_median=round(med, 2),
                          symmetric_range=[round(sy[0], 2), round(sy[-1], 2)], antisymmetric_range=[round(min(an), 2), round(max(an), 2)] if an else None,
                          paired=all(e.get("paired") for e in cur), one_side=sorted({e.get("one_side") for e in cur if e.get("one_side")}),
                          held_out=[round(v, 2) for v in ho], photos=sum(e.get("n_photos", 0) for e in cur), tol_mm=tol,
                          score=round(abs(med) / tol, 2), owner=owner(mem, edge, cur[0]["stretch"]),
                          regions=[e["region"] for e in cur], se_max=round(max((e.get("sym_se") or 0) for e in cur), 2)))
        cur.clear()
    prev = None
    for e in rs:
        v = int(e["stretch"].split()[1])
        if counts(e):
            if cur and (v - int(cur[-1]["stretch"].split()[1]) > 100 or (e["symmetric"] > 0) != (cur[-1]["symmetric"] > 0)): flush()
            cur.append(e)
    flush()
items.sort(key=lambda i: (-i["score"], -i["n_stretches"]))
for k, i in enumerate(items): i["rank"] = k + 1
if len(sys.argv) > 2: json.dump(items, open(sys.argv[2], "w"), indent=1)
for i in items:
    an = i["antisymmetric_range"]; ho = i["held_out"]
    print(f"{i['rank']:2d} {i['member']:7s} {i['edge']:12s} {i['axis']} {i['from_mm']:5d}..{i['to_mm']:5d} sym {i['symmetric_median']:+5.2f} [{i['symmetric_range'][0]:+.2f},{i['symmetric_range'][1]:+.2f}] "
          f"anti {('%+.2f..%+.2f' % tuple(an)) if an else '  one-sided ' + ','.join(i['one_side'])} tol {i['tol_mm']} photos {i['photos']} held {ho} | {i['owner'][:40]}")
