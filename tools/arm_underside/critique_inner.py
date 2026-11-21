"""USAGE: work/toolkit/rk.sh tools/arm_underside/critique_inner.py work/critique/v24 OUT.json
Arm inner bottom arris from the critique's per-photo points, made pose-free in z against the same photo's own outer top arris.
Per photo, arm, y bin: e_bot = median(gap/(-m_z)) on the bottom/inner silhouette (model arris too LOW by e_bot, vertical),
a_top = median(gap/m_z) on the top/outer silhouette (model top too HIGH by a_top). err_h_inner = e_bot + a_top = how much the
model's drop (inner bottom arris below outer top arris) is too big; a vertical pose shift cancels. Only points with |m_z| > 0.5."""
import sys, json, numpy as np
from pathlib import Path
sys.path.insert(0, 'tools/critique'); from common import PARTS, CLASSES
run = sys.argv[1]; HO = set(json.load(open('tools/critique/holdout.json'))['held_out'])
bins = [(50, 100), (100, 200), (200, 300), (300, 400), (400, 450)]
rows = []
for f in sorted(Path(run).glob('IMG_*.npz')):
    R = dict(np.load(f)); C = np.array(CLASSES)
    edge = np.where(R['c1'] == R['c2'], C[R['c1']], np.char.add(np.char.add(C[R['c1']], '/'), C[R['c2']]))
    for S in 'LR':
        base = (R['part'] == PARTS.index('ARM_' + S)) & (R['kind'] == 1) & (R['st'] == 0)
        for y0, y1 in bins:
            b = base & (R['along'] >= y0) & (R['along'] < y1)
            sb = b & (edge == 'bottom/inner') & (R['m'][:, 2] < -0.5)
            st_ = b & (edge == 'top/outer') & (R['m'][:, 2] > 0.5)
            if sb.sum() < 8: continue
            e = float(np.median(R['gap'][sb] / -R['m'][sb, 2]))
            a = float(np.median(R['gap'][st_] / R['m'][st_, 2])) if st_.sum() >= 8 else None
            rows.append(dict(photo=f.stem[4:], held=f.stem + '.JPG' in HO, side=S, y=[y0, y1], n=int(sb.sum()), e_bot=e, a_top=a,
                             err=(e + a if a is not None else None), mz=float(np.median(R['m'][sb, 2])), pxmm=float(np.median(R['pxmm'][sb]))))
json.dump(rows, open(sys.argv[2], 'w'))
mad = lambda x: 1.4826 * np.median(np.abs(np.array(x) - np.median(x))) if len(x) > 1 else float('nan')
for S in 'LR':
    for y0, y1 in bins:
        for grp in (False, True):
            r = [q for q in rows if q['side'] == S and q['y'] == [y0, y1] and q['held'] == grp]
            if not r: continue
            E = [q['e_bot'] for q in r]; P = [q for q in r if q['err'] is not None]; D = [q['err'] for q in P]
            print(f"{S} y {y0}-{y1} {'held' if grp else 'rank'}: bottom-only {np.median(E):+.2f} ({len(E)} ph, spr {mad(E):.2f})"
                  + (f" | pose-free drop error {np.median(D):+.2f} ({len(D)} ph, spr {mad(D):.2f}, px/mm {np.median([q['pxmm'] for q in P]):.1f}) photos " + ' '.join(f"{q['photo']}:{q['err']:+.1f}" for q in P) if D else ''))
