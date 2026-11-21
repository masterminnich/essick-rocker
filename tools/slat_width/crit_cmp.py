import json, sys, numpy as np
A=json.load(open(sys.argv[1])); B=json.load(open(sys.argv[2])); out=sys.argv[3] if len(sys.argv)>3 else None
ra={x['region']:x for x in A['regions']}; rb={x['region']:x for x in B['regions']}
def held(x):
    v=[x['sides'][s]['held']['median'] for s in x.get('sides',{}) if x['sides'][s].get('held')]
    return v
def tr(x,s): t=x['sides'].get(s,{}).get('train'); return t['median'] if t else None
f=lambda v: '  -  ' if v is None else f"{v:+5.2f}"
rows=[]
keys=[k for k in ra if k.startswith('SLAT_LR|sil') and ra[k].get('symmetric') is not None]
keys.sort(key=lambda k:(ra[k]['edge'], int(ra[k]['stretch'].split()[1])))
print("region                          sym v23->v24   L v23->v24     R v23->v24     rank v23->v24  held v23 -> v24")
for k in keys:
    a,b=ra[k],rb.get(k,{})
    print(f"{k[8:]:30s} {f(a.get('symmetric'))}->{f(b.get('symmetric'))}  {f(tr(a,'L'))}->{f(tr(b,'L'))}  {f(tr(a,'R'))}->{f(tr(b,'R'))}  {a.get('rank','-')!s:>4}->{b.get('rank','-')!s:<4}  {[round(v,2) for v in held(a)]} -> {[round(v,2) for v in held(b)]}")
    rows.append(dict(region=k, v23=dict(sym=a.get('symmetric'),L=tr(a,'L'),R=tr(a,'R'),rank=a.get('rank'),held=held(a),tol=a['tol_mm']), v24=dict(sym=b.get('symmetric'),L=tr(b,'L'),R=tr(b,'R'),rank=b.get('rank'),held=held(b))))
sa=np.array([abs(ra[k]['symmetric']) for k in keys]); sb=np.array([abs(rb[k]['symmetric']) if rb[k].get('symmetric') is not None else np.nan for k in keys])
ha=np.concatenate([np.abs(held(ra[k])) for k in keys if held(ra[k])]); hb=np.concatenate([np.abs(held(rb[k])) for k in keys if held(rb[k])])
oa=sum(abs(ra[k]['symmetric'])>ra[k]['tol_mm'] for k in keys); ob=sum((rb[k].get('symmetric') is not None and abs(rb[k]['symmetric'])>rb[k]['tol_mm']) for k in keys)
print(f"SLAT_LR sil regions {len(keys)}: median |sym| {np.median(sa):.2f} -> {np.nanmedian(sb):.2f}; out of tol {oa} -> {ob}; held |median| median {np.median(ha):.2f} ({len(ha)}) -> {np.median(hb):.2f} ({len(hb)})")
for e in sorted(set(ra[k]['edge'] for k in keys)):
    ks=[k for k in keys if ra[k]['edge']==e]
    h1=np.concatenate([held(ra[k]) for k in ks if held(ra[k])] or [[]]); h2=np.concatenate([held(rb[k]) for k in ks if held(rb[k])] or [[]])
    print(f"   {e:12s} mean sym {np.mean([ra[k]['symmetric'] for k in ks]):+.2f} -> {np.nanmean([rb[k].get('symmetric') or np.nan for k in ks]):+.2f}  held median {np.median(h1) if len(h1) else np.nan:+.2f} -> {np.median(h2) if len(h2) else np.nan:+.2f}  n {len(h1)}/{len(h2)}")
print("five worst other regions (v23 ranking):")
oth=sorted([x for x in A['regions'] if x.get('rank') and not x['member'].startswith('SLAT')], key=lambda x:x['rank'])[:5]
for a in oth:
    b=rb[a['region']]
    print(f"  {a['region']:40s} sym {f(a.get('symmetric'))}->{f(b.get('symmetric'))} rank {a['rank']}->{b.get('rank')} held {[round(v,2) for v in held(a)]} -> {[round(v,2) for v in held(b)]}")
    rows.append(dict(region=a['region'], other=True, v23=dict(sym=a.get('symmetric'),rank=a['rank'],held=held(a)), v24=dict(sym=b.get('symmetric'),rank=b.get('rank'),held=held(b))))
ch=[k for k in ra if not k.startswith('SLAT') and ra[k].get('symmetric') is not None and rb.get(k,{}).get('symmetric') is not None and abs(ra[k]['symmetric']-rb[k]['symmetric'])>0.05]
print("non-slat regions whose symmetric median moved > 0.05 mm:", len(ch), ch[:10])
if out: json.dump(rows, open(out,'w'), indent=1)
