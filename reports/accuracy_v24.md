# Accuracy report, model v24 (2026-11-21)

Model: `parts/model_v24.glb` (main 9ab044b and later; v24 has been unchanged since PR #34). Tolerance: 0.8 mm on joints and
hard points, 1.6 mm on free curves (Joe, 2026-11-20).

Sources. Every number below is taken from a file:
- the critique of v24: `reports/critique_v24.json`, tabulated by `python3 -I tools/critique/accuracy.py`;
- the parts files named in each table;
- PLAN.md (phases 5b-6c, the M list).

Nothing here was read off a picture.

## How to read the critique numbers

The critique projects the model through the 93 solved cameras and measures, along each part's outline, the gap to the wood
edge in the photo:
- **+** means the model is outside the wood (too big); **-** means it is inside.
- Units are mm at the part.

Photos: 76 ranking photos and 15 fixed held-out photos (`tools/critique/holdout.json`). The held-out photos never steered a fix.

Coverage: only silhouettes are scored here. Crease (tone) lines are in `reports/critique_v24.md`.

The design is the left/right MEAN, so each side's photos can see the model 1-3 mm off the real part where the chair is
asymmetric. The symmetric gap (the mean of L and R) is what the design can be judged on. The antisymmetric gap is half the L-R
difference: the chair's own asymmetry plus pose error.

Validation: a 2 mm shift test recovers 0.98-1.0 of the shift (`shift_tests`).

| member | stretches | med \|sym\| (mm) | in tolerance | held-out med \|gap\| (stretches) | med \|L-R\|/2 (pairs) | items | worst item [held-out] |
|---|---|---|---|---|---|---|---|
| ARM | 45 | 0.55 | 93 % | 0.81 (43) | 0.92 (43) | 3 | #6 top/outer y 0..50: -2.46 [-2.6] |
| BLEG | 90 | 0.70 | 82 % | 0.85 (89) | 0.70 (86) | 10 | #1 outer/inner z 0..50: +4.07 |
| CREST | 22 | 1.13 | 59 % | 1.02 (21) | 0.51 (18) | 2 | #4 bottom/front x 0..100: +2.94 [+0.5, +1.4] |
| FLEG | 48 | 0.75 | 71 % | 1.07 (44) | 0.97 (42) | 6 | #3 inner/back z 600..650: +3.44 [+1.9] |
| ROCKER | 104 | 0.77 | 81 % | 0.88 (99) | 0.77 (98) | 6 | #18 bottom/inner y -300..-50: -2.74 [-3.7, -2.8, -3.0, -2.9, -1.2] |
| SEAT | 78 | 0.61 | 85 % | 0.85 (76) | 0.71 (72) | 6 | #10 top/back x 0..200: +1.78 [+1.2, -0.1, +1.7, +1.7] |
| SLAT_C | 26 | 0.49 | 100 % | 0.36 (26) | 1.32 (26) | 0 | - |
| SLAT_LR | 52 | 0.72 | 88 % | 0.67 (52) | 0.85 (51) | 3 | #16 inner/front z 850..1000: +2.90 [+1.9, +1.3, +3.0] |

Column definitions:
- A stretch is one silhouette edge over 50 mm of its length.
- "in tolerance" compares |symmetric| with that stretch's tolerance.
- Held-out uses the held-out photos' per-side medians, L/R averaged.
- For SLAT_C, "L-R" compares its two edges.

All 36 ranked items are in `reports/critique_v24.md`. The table below gives what each part's worst item turned out to be.

## Per part

### Rockers (ROCKER_L/R)
| | |
|---|---|
| Provenance | Side outline, triangulated / fitted: `parts/rocker_profile.json` (u -330..572), plus the ends traced in 11-18 photos per end (`parts/rocker_ends.json`, PR #23), plus the bottom-edge correction (`parts/rocker_bottom.json`, PR #29, up to 2.2 mm). Thickness across (`parts/rocker_section.json`, PR #32) runs from 29.7 mm at the tail tip to 36.2 between the legs, ±1.6. The tape at the tail tip (IMG_1493) reads 30.5 ±1.6. |
| Critique | 104 stretches, median \|sym\| 0.77, 81 % in tolerance. Held-out 0.88. |
| L/R | Median 0.77. Fitted per photo, the right rocker looks turned about 0.6° about z (PR #32), and the left rocker's top is tilted -3.8 mm/m (PR #36). Placement belongs to the joinery session. |
| Worst | #18 bottom/inner: -2.74, the right rocker's placement (joinery request). |
| Assumed / open | Left and right are each placed by the camera poses. Tilt: M14. Thickness between the legs: M12. Tail tip corners in plan are R ≈ 2.8 and not modelled (PR #37). |

### Back legs (BLEG_L/R)
| | |
|---|---|
| Provenance | Triangulated edges on the unrolled back view (`parts/back_legs.json`, `tools/edge_tri.py`). Outline and placement belong to the joinery session. |
| Critique | 90 stretches, 0.70, 82 %. Held-out 0.85. |
| L/R | Median 0.70. |
| Worst | #1 the foot at z 0-50: +4.07 (left only, 11 photos). The real foot is about 3 mm narrower (joinery request). |
| Assumed / open | Stock thickness across ±3 (M11). Arris radii 0.7-1.5 (`parts/edge_radii.json`; the model is sharp). |

### Front legs (FLEG_L/R)
| | |
|---|---|
| Provenance | Per-line triangulation on both sides (`parts/side_frame.json`). The front-leg Domino was re-centred in PR #24. |
| Critique | 48 stretches, 0.75, 71 %. Held-out 1.07, the worst held-out of any member. |
| L/R | Median 0.97. |
| Worst | #3 the top at the arm: +3.44 [+1.9], right only. Over z 150-600 the leg sits about 2 mm forward of the wood (joinery request: placement or tilt). |
| Assumed / open | Leg placement (joinery). Arris radii 0.6-1.1, model sharp. |

### Arms (ARM_L/R)
| | |
|---|---|
| Provenance | Plan and top from overhead photos (`parts/arms.json`, frozen). Underside and thickness traced on side photos of both arms (`parts/arm_underside.json`, PR #27, in the build from v21). |
| Critique | 45 stretches, 0.55, 93 %. Held-out 0.81. |
| L/R | Median 0.92, the largest of the major members: the arms sit about 3.6 mm to +x and the left is about 5 mm higher at the front (`arms.json`). |
| Worst | #6 top/outer at the back leg: -2.46 [-2.6] (a frozen-file doubt). |
| Assumed / open | The inner bottom arris is within spread but asymmetric (PR #36): reading M15 (model h_inner 33.5 at y 150, 23.1 at y 400). Front-end thickness: reading M6 (model h_outer 21.2 at y 510). Arm edge radii are not measured (M16). |

### Seat (SEAT)
| | |
|---|---|
| Provenance | Top from the tape-dot survey (`seat/surface.json`, leave-one-out 1.18 mm). Side edge triangulated (`parts/seat_edge.json`), 42.0 ±3 mm. Front roll as a tube (`parts/seat_front.json`, ±2 mm, forward depth the weak direction) and front face (`parts/seat_front_face.json`, PR #34). Scoop: L/R mean (`parts/seat_scoop.json`, PR #26). Back edge: `parts/seat_back.json`. |
| Critique | 78 stretches, 0.61, 85 %. Held-out 0.85. |
| L/R | Median 0.71. The right front is 2.6 mm lower and the right side frame is pitched about 0.5° nose-down (`parts/lr_skew.json`): reading M9 (model seat side edge top z 411.5 at y 434, both sides). |
| Worst | #10 top/back at the slats: +1.78, cannot be told (r ≥ 4-5 or a roll-off; M13). |
| Assumed / open | Front roll radius 8 (assumed; 4-16 move the outline < 1 mm). Underside flat across by reflection only. Front corner at y 500-550: a reading. Scallop depth 21.3 ±2-3: M10. |

### Crest (CREST)
| | |
|---|---|
| Provenance | Overhead and back photos (`parts/crest.json`, frozen). |
| Critique | 22 stretches, 1.13, 59 %: the weakest member. Held-out 1.02. |
| L/R | Median 0.51. |
| Worst | #4 bottom/front: +2.94 [+0.5, +1.4]. A frozen-file doubt: the lower edge sits low; a round can explain at most 0.9 mm of it (crest bottom arris r 1.1-2.2, PR #37). |
| Assumed / open | Height at the centre: photos 74.7 vs tape IMG_1555 77.5 (M3). Table to crest top: M7 (model z 1082.7). |

### Slats (SLAT_C, SLAT_L/R)
| | |
|---|---|
| Provenance | Edge triangulation (`parts/slats.json`). The side slats' turn is measured (`parts/slat_turn.json`, 7.2° at z 375 to 3.6° at z 1000) but NOT applied (`apply_in_build` false). |
| Critique | Centre: 26 stretches, 0.49, 100 %, held-out 0.36. Sides: 52 stretches, 0.72, 88 %, held-out 0.67. |
| L/R | Sides 0.85. Centre 1.32, between its two edges: the centre slat's position. |
| Worst | #16 inner/front at z 850-1000: +2.90 [+1.9, +1.3, +3.0], the unapplied turn. With the turn applied the trial gave +2.45/+2.54, but held-out edge medians were mixed (PR #33). Joe's yes/no. |
| Assumed / open | Thickness about 10 (M4). Centre slat width: trace 100.0-100.5 vs tape 98.3 (M5). |

## Never hand-checked

Every dimension above is photo-derived (triangulated, fitted or assumed) except the tape readings in
`measurements/tape_readings.csv`. Everything rests on a single framing-square scale (`solve/metric_frame.json`). M7 and M8 are
the only independent checks on that scale:
- M8 (rocker tail tip to nose top corner): the photos say 1118.6 left and 1112.3 right, ±2 each; the model has 1115.7.
- M7 (table to crest top): the model has 1082.7.

Until one of them is read, the whole model shares any error in that one scale.
