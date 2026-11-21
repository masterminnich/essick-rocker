# Critique, pass 3: model v24 against every solved photo

This is the rerun after critique fix 3, edge 1: the underside edge of the seat's front roll (PR #34). It uses the method, tools, photos and fixed held-out list of pass 1, unchanged: see `reports/critique_v22.md` and `tools/critique/README.md`.

- **Data:** `reports/critique_v24.json`.
- **Figure:** `figures/critique/ranked_v24.png`.
- **Sign:** **+ = the model sticks out beyond the wood; − = the model lies inside the wood.**
- **Run:** 93 photos in 50 s, peak 0.86 GB; 1506 regions, 36 items.
- **Against the trial build's run (`work/trial/v24`):** every region median is identical. The trial run listed 37 items; this one lists 36. The difference is ROCKER bottom/inner y 50..100 (−0.97), which sat at the tolerance line. Its `joint_frac` (the share of points near another part, which picks the tolerance) is sampled and changes slightly between runs on identical meshes, so items at the line can come and go. The model is the same: `_shapes`, `_edges`, `_params` and the glb are byte-identical to the trial's.

## What changed in the model

**Only SEAT** (`parts/seat_front_face.json`). The bottom arris of the front roll is now the outline of PR #15's traced tube, not its spine: 0.90-1.00 mm lower and 0.40-0.50 mm further forward along |x| 8-262. The corner point at |x| 268 is unchanged.

- `_shapes`: 533 of 5892 seat vertices move, at most 1.00 mm, all at y 461..537, z 370..405. Every other part is vertex-identical.
- Joined model: only SEAT changes. The front-leg lap trim removes 24.59 cm³ instead of 24.55.
- The seat's back half does not move, so the slat ends sit exactly as in v23.

## Seat: v23 → v24

**Mean |gap|, mm: ranking photos / held-out photos.**

| region | v23 | v24 |
|---|---|---|
| bottom/front silhouette | 1.85 / 2.18 | 1.50 / 1.96 |
| same, left/right mean \|sym\| | 1.58 / 2.26 | 0.95 / 2.12 |
| bottom/front crease | 0.85 / 1.40 | 1.05 / 1.06 |
| same, \|sym\| | 0.60 / 1.26 | 0.97 / 0.40 |
| front face (silhouette) | 0.71 / 1.19 | 0.71 / 1.18 |
| top/back edge | 1.84 / 1.67 | 1.84 / 1.68 |

- **Held-out, like for like** (stretches with the same held-out photos in both runs): the silhouette is better in 9 of 9.
- **The item bottom/front x 0..50 (−2.17, held −3.81) is gone.**
- **bottom/front x 200..250** went from −2.54 (#20) to −2.01 (#27), held −3.18. It is the right half only: the right front is 2.6 mm lower than the left and the design is the mean.
- **The underside near the front corners** (`bottom` at y 450-500, x 200-250) moved by up to 1 mm, mixed in sign, on 2-25 low side views. The underside's fade behind the edge is still assumed (PR #15's open list).
- **The crease reads about 0.4 mm more outside in the low ranking views.** That fits a slightly eased arris; it belongs with 6c edge radii.

## Everything else

- **Across all 1716 non-seat region medians,** the mean change in |gap| is −0.001 mm (ranking) and −0.000 (held-out).
- **The five worst other items are unchanged** (#1-#5 below). Front leg inner/back z 600, R: held-out 1.98 → 1.90.

## The other critique-3 edge: the seat's top back edge at the slats

**Item #10, +1.78 (held-out −0.1..1.7). Measurement only, no change: see PR #35 and the M list in PLAN.md.**

## Ranked list, v24 (top 20; held-out medians in brackets)

| # | member | edge | stretch | sym gap | held-out | owner |
|---|---|---|---|---|---|---|
| 1 | back leg | outer/inner | z 0..50 | +4.07 (L only) | — | joinery |
| 2 | back leg | front/back | z 50..100 | +3.96 (L only) | 3.50 | joinery |
| 3 | front leg | inner/back | z 600..650 | +3.44 (R only) | 1.90 | joinery |
| 4 | crest | bottom/front | x 0..100 | +2.94 (L only) | 0.49, 1.42 | crest.json (frozen) |
| 5 | front leg | outer/back | z 150..600 | −2.75 (L only) | −4.2..−2.1 | hub / joinery |
| 6 | arm | top/outer | y 0..50 | −2.46 | −2.56 | arms.json (frozen) |
| 7 | crest | bottom/back | x 50..250 | +2.44 | 0.5..2.1 | crest.json (frozen) |
| 8 | back leg | inner/front | z 0..100 | +2.08 (R only) | 2.50, 2.15 | joinery |
| 9 | back leg | bottom/front | z 0..50 | +1.80 | −0.81 | joinery |
| 10 | seat | top/back | x 0..200 | +1.78 (L only) | −0.1..1.7 | hub |
| 11 | front leg | inner/front | z 400..450 | +1.76 | 1.93 | hub |
| 12 | seat | outer | y 500..550 | −3.48 (R only) | −1.27 | hub |
| 13 | back leg | inner/back | z 50..100 | +3.01 | 3.00 | joinery |
| 14 | back leg | inner/back | z 300..350 | −1.50 | — | joinery |
| 15 | front leg | inner/front | z 600..650 | +1.46 | −0.15 | joinery |
| 16 | side slats | inner/front | z 850..1000 | +2.90 | 1.3..3.0 | hub |
| 17 | arm | bottom/inner | y 50..100 | +1.43 | 1.67 | hub |
| 18 | rocker | bottom/inner | y −300..−50 | −2.74 | −3.7..−1.2 | hub (R placement: joinery) |
| 19 | front leg | inner/front | z 250..300 | +2.56 | 3.60 | hub |
| 20 | rocker | top/outer | y 300..650 | −2.27 | −3.1..0.1 | hub |

The seat's other items: #22 bottom/back x 150..200 (−1.11), #27 bottom/front x 200..250 (−2.01, R only), #30 top y 400..450 (+1.89), #36 outer/front y 500..550 (−1.61).

**The next hub items are the rocker's top at the nose and the tail (#20) and the arm underside's inner edge (#17).**
