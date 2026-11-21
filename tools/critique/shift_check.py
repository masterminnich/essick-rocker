"""USAGE: work/toolkit/rk.sh tools/critique/shift_check.py BASE_RUN SHIFTED_RUN PART DX DY DZ [OUT.json]
Sanity check of the critique tool: measure.py run once on the model as built (BASE_RUN) and once with one part moved by
(DX, DY, DZ) mm (`measure.py ... --shift PART DX DY DZ`, SHIFTED_RUN). For every outline point of PART measured in both runs
(same static point index), the change of its gap should equal the shift projected on the point's measuring direction m
(square to the line of sight and to the edge, outward): expected = shift . m. Prints the slope of measured vs expected
(1 = the tool recovers the shift), and the median and spread of (measured - expected) for points where |expected| > 1 mm."""
import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import PARTS  # noqa
import numpy as np
base, shif, part = sys.argv[1:4]; d = np.array([float(v) for v in sys.argv[4:7]])
pi = PARTS.index(part); E, M, K = [], [], []
for f in sorted(Path(shif).glob("IMG_*.npz")):
    S = dict(np.load(f)); B = dict(np.load(Path(base) / f.name))
    for R in (S, B): R["key"] = R["si"].astype(np.int64)
    s = (S["part"] == pi) & (S["st"] == 0); b = (B["part"] == pi) & (B["st"] == 0)
    ks, kb = S["key"][s], B["key"][b]
    common, i_s, i_b = np.intersect1d(ks, kb, return_indices=True)
    gs, gb = S["gap"][s][i_s], B["gap"][b][i_b]
    exp = B["m"][b][i_b] @ d
    E.append(exp); M.append(gs - gb); K.append(S["kind"][s][i_s])
E, M, K = np.concatenate(E), np.concatenate(M), np.concatenate(K)
out = {}
for nm, sel in (("sil", K == 1), ("crease", K == 2)):
    big = sel & (np.abs(E) > 1.0)
    if big.sum() < 10: continue
    slope = float(np.sum(E[big] * M[big]) / np.sum(E[big] ** 2))
    r = M[big] - E[big]
    out[nm] = dict(points=int(big.sum()), slope=round(slope, 3), median_expected=round(float(np.median(np.abs(E[big]))), 2),
                   median_measured_over_expected=round(float(np.median(M[big] / E[big])), 3),
                   residual_median=round(float(np.median(r)), 3), residual_spread=round(float(1.4826 * np.median(np.abs(r - np.median(r)))), 3),
                   within_0_5mm=round(float(np.mean(np.abs(r) < 0.5)), 3))
    print(f"{part} shifted {d.tolist()}: {nm}: {big.sum()} points with |expected| > 1 mm, median |expected| {out[nm]['median_expected']:.2f}; slope {slope:.3f}; "
          f"median measured/expected {out[nm]['median_measured_over_expected']:.3f}; residual {out[nm]['residual_median']:+.3f} +- {out[nm]['residual_spread']:.3f}; "
          f"{100 * out[nm]['within_0_5mm']:.0f}% within 0.5 mm")
if len(sys.argv) > 7:
    Path(sys.argv[7]).write_text(json.dumps(dict(part=part, shift_mm=d.tolist(), base=base, shifted=shif, **out), indent=1))
