# Critique, pass 2: model v23 against every solved photo

This is the rerun after critique fix 1, the rocker's thickness across (PR #32). It uses the method, tools, photos and fixed held-out list of pass 1, unchanged: see `reports/critique_v22.md` and `tools/critique/README.md`.

- **Data:** `reports/critique_v23.json`.
- **Figure:** `figures/critique/ranked_v23.png`.
- **Sign:** **+ = the model sticks out beyond the wood; − = the model lies inside the wood.**
- **Run:** 93 photos in 50 s, peak 0.85 GB; 1506 regions, 38 items. The items are identical to the trial build's run, `work/trial/v23`.

## What changed in the model

**Only ROCKER_L/R** (`parts/rocker_section.json`): the thickness across now runs from 29.7 mm at the tail tip to 36.2 mm between the legs (it was 31 throughout). The outer face moved by the measured L+R mean:

- 0 in the tail;
- up to 1.2 mm inward at the rear;
- up to 2.25 mm outward from u 200 to 400.

**Knock-on changes in the joined model:**

- **The front-leg feet** were re-cut by joinery's unchanged foot logic: the lip at the outer edge is gone, and the lowest point rose 2.61 mm.
- **The back-leg feet:** 0.02 cm³; the lowest point rose 0.22 mm.
- **The arm Dominos** moved 0.1-0.5 mm.

## Rocker: v22 → v23

**Grouped mean |gap|, mm: ranking photos / held-out photos.**

| region | v22 | v23 |
|---|---|---|
| all rocker silhouettes | 1.53 / 1.64 | 1.45 / 1.52 |
| bottom/inner, rear (y −300..100) | 2.57 / 2.80 | 1.99 / 2.05 |
| top/inner, front | 1.84 / 1.80 | 0.85 / 1.72 |
| top/outer, front | 2.11 / 2.17 | 1.88 / 1.90 |
| top/outer, rear | 1.01 / 1.21 | 0.96 / 1.05 |
| bottom/outer, front | 1.16 / 1.64 | 1.21 / 1.28 |
| bottom/outer, rear | 1.21 / 1.40 | 1.23 / 1.23 |
| bottom/inner, front | 1.06 / 0.99 | 1.51 / 1.23 |
| top/inner, rear | 1.38 / 1.73 | 1.68 / 1.75 |
| bottom, tail | 1.66 / 1.78 | 2.05 / 1.82 |

- **Rocker items:** 9 (score sum 16.07) → 7 (9.29).
- **Fixed:** the pass-1 item top/inner y −50..450 (−2.04) is gone.
- **Smaller:** bottom/inner went from −3.15 at #5 to −2.74 at #18, y −300..−50. Its held-out photos read −3.7, −2.8, −3.0, −2.9 and −1.2.
- **What is left on the inner face is mostly the right rocker.** Median inward shift of the wood face beyond the model, v23:

| | L | R |
|---|---|---|
| top/inner, rear | −0.3 | +1.7 |
| bottom/inner, rear | −0.7 | +1.9 |
| bottom/inner, front | −0.8 | −3.3 |

The R rocker's outer face reads 5-7.5 mm inward at the tail and 4-5 mm outward at the front. That looks like a yaw of about 0.6°, which is placement (the joinery session's), not section.

## Everything else

- **Across all non-rocker regions,** the mean change in |gap| is −0.01 mm (ranking) and −0.00 (held-out).
- **The pass-1 item front leg top/outer z 50 (−2.88)** is gone. It was the foot lip.
- **Back leg outer/back z 0, R** went from +3.60 to +3.93 (held-out 2.22 → 2.16) and fell below the list.
- **Front leg inner/back z 600, R** went from +3.24 to +3.44 (held-out 2.60 → 1.98).

## Ranked list, v23 (top 20; held-out medians in brackets)

| # | member | edge | stretch | sym gap | held-out | owner |
|---|---|---|---|---|---|---|
| 1 | back leg | outer/inner | z 0..50 | +4.07 (L only) | — | joinery |
| 2 | back leg | front/back | z 50..100 | +3.96 (L only) | 3.5 | joinery |
| 3 | front leg | inner/back | z 600..650 | +3.44 (R only) | 1.98 | joinery |
| 4 | crest | bottom/front | x 0..100 | +2.94 | 0.49, 1.42 | crest.json (frozen) |
| 5 | front leg | outer/back | z 150..600 | −2.75 | −2.1..−4.2 | hub / joinery |
| 6 | arm | top/outer | y 0..50 | −2.46 | −2.56 | arms.json (frozen) |
| 7 | crest | bottom/back | x 50..250 | +2.44 | 0.5..2.1 | crest.json (frozen) |
| 8 | back leg | inner/front | z 0..100 | +2.08 | 2.5, 2.15 | joinery |
| 9 | back leg | bottom/front | z 0..50 | +1.80 | −0.81 | joinery |
| 10 | seat | top/back | x 0..200 | +1.78 | −0.1..1.7 | hub |
| 11 | front leg | inner/front | z 400..450 | +1.76 | 1.93 | hub |
| 12 | seat | outer | y 500..550 | −3.40 (R only) | −1.27 | hub |
| 13 | back leg | inner/back | z 50..100 | +3.01 | 3.0 | joinery |
| 14 | back leg | inner/back | z 300..350 | −1.50 | — | joinery |
| 15 | front leg | inner/front | z 600..650 | +1.46 | −0.15 | joinery |
| 16 | side slats | inner/front | z 850..1000 | +2.90 | 1.3..3.0 | hub |
| 17 | arm | bottom/inner | y 50..100 | +1.43 | 1.67 | hub |
| 18 | rocker | bottom/inner | y −300..−50 | −2.74 | −1.2..−3.7 | hub (R placement: joinery) |
| 19 | front leg | inner/front | z 250..300 | +2.56 | 3.6 | hub |
| 20 | seat | bottom/front | x 200..250 | −2.54 | — | hub |

**The next hub item is the side slats' inner front edge (#16, plus #34 and #35 lower down).**
