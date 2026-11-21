"""USAGE: python3 -I tools/critique/accuracy.py [reports/critique_v24.json]
Per-member numbers for reports/accuracy_vN.md, from the critique's json only (silhouettes; creases are reported, not ranked):
  regions         silhouette stretches measured (a stretch = one edge, 50 mm along it)
  med |sym|       median over stretches of |symmetric gap| (L/R mean of the per-side medians; ranking photos)
  in tol          share of stretches with |sym| <= their tolerance (0.8 joints, 1.6 free curves)
  held-out        median over stretches of |held-out gap| (L/R mean of the held-out per-side medians where a side has held-out photos)
  |L-R|/2         median over paired stretches of |antisymmetric| (half the left-right difference)
  items, worst    ranked items of this member and the worst one (rank, edge, stretch, value [held-out])
Prints a markdown table."""
import sys, json, statistics as st

d = json.load(open(sys.argv[1] if len(sys.argv) > 1 else "reports/critique_v24.json"))
mem = {}
for r in d["regions"]:
    if r["kind"] != "sil" or r.get("symmetric") is None: continue
    m = mem.setdefault(r["member"], dict(sym=[], tol=[], held=[], anti=[], kcount=0))
    m["sym"].append(abs(r["symmetric"])); m["tol"].append(abs(r["symmetric"]) <= r["tol_mm"])
    h = [s["held_out_median"] for s in r["sides"].values() if s.get("held_out_median") is not None]
    if h: m["held"].append(abs(sum(h) / len(h)))
    if r.get("antisymmetric") is not None: m["anti"].append(abs(r["antisymmetric"]))
items = {}
for it in d["items"]: items.setdefault(it["member"], []).append(it)
print("| member | stretches | med \\|sym\\| (mm) | in tolerance | held-out med \\|gap\\| (stretches) | med \\|L-R\\|/2 (pairs) | items | worst item |")
print("|---|---|---|---|---|---|---|---|")
for k in sorted(mem):
    m = mem[k]; its = sorted(items.get(k, []), key=lambda x: x["rank"])
    w = its[0] if its else None
    ws = (f"#{w['rank']} {w['edge']} {w['axis']} {w['from_mm']}..{w['to_mm']}: {w['symmetric_median']:+.2f}"
          + (f" [{', '.join(f'{x:+.1f}' for x in w['held_out'])}]" if w["held_out"] else "")) if w else "-"
    print(f"| {k} | {len(m['sym'])} | {st.median(m['sym']):.2f} | {100 * sum(m['tol']) / len(m['tol']):.0f} % | "
          f"{(f'{st.median(m['held']):.2f} ({len(m['held'])})') if m['held'] else '-'} | "
          f"{(f'{st.median(m['anti']):.2f} ({len(m['anti'])})') if m['anti'] else '-'} | {len(its)} | {ws} |")
