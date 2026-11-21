"""USAGE: work/toolkit/rk.sh tools/rocker_top/pitch.py work/critique/v24 OUT.json
Per photo and rocker: the critique's top-edge gaps (silhouettes top/outer + top, views with m_z > 0.7, i.e. read mostly vertically)
fitted as gap = a + b*(y - 100) over the whole rocker; b in mm per m (= mrad): + = model above the wood more toward the nose."""
import sys, json, numpy as np
from pathlib import Path
sys.path.insert(0, 'tools/critique')
from common import PARTS, CLASSES
run = sys.argv[1]; HO = set(json.load(open('tools/critique/holdout.json'))['held_out'])
res = {"L": [], "R": []}
for f in sorted(Path(run).glob('IMG_*.npz')):
    R = dict(np.load(f)); name = f.stem; part = np.array(PARTS)[R['part']]; c1, c2 = R['c1'], R['c2']
    edge = np.where(c1 == c2, np.array(CLASSES)[c1], np.char.add(np.char.add(np.array(CLASSES)[c1], '/'), np.array(CLASSES)[c2]))
    for S in "LR":
        s = (part == 'ROCKER_' + S) & (R['kind'] == 1) & np.isin(edge, ['top/outer', 'top']) & (R['st'] == 0) & (R['m'][:, 2] > 0.7)
        if s.sum() < 40: continue
        y = R['along'][s]; g = R['gap'][s]
        if np.ptp(y) < 400: continue
        # robust line: two passes
        b = np.polyfit(y - 100, g, 1); r = g - np.polyval(b, y - 100); k = np.abs(r) < 3 * 1.4826 * np.median(np.abs(r)) + 0.3
        b = np.polyfit(y[k] - 100, g[k], 1)
        res[S].append(dict(photo=name[4:], held=name + '.JPG' in HO, slope=float(b[0] * 1000), off=float(b[1]), n=int(k.sum()), yr=[float(y.min()), float(y.max())]))
for S in "LR":
    A = res[S]
    for grp, sel in (("ranking", [not a['held'] for a in A]), ("held-out", [a['held'] for a in A])):
        B = np.array([[a['slope'], a['off']] for a, q in zip(A, sel) if q])
        if not len(B): continue
        mad = lambda x: 1.4826 * np.median(np.abs(x - np.median(x)))
        print(f"{S} {grp}: {len(B)} photos  slope median {np.median(B[:,0]):+.2f} mm/m (spread {mad(B[:,0]):.2f})  gap at y 100 median {np.median(B[:,1]):+.2f}  photos " + ' '.join(f"{a['photo']}:{a['slope']:+.1f}" for a, q in zip(A, sel) if q))
json.dump(res, open(sys.argv[2], 'w'))
