# ESSICK seat: measured top surface from blue-tape dots

Chair frame, mm (solve/metric_frame.json): +X = chair's right as you sit, +Y forward, +Z up, table top Z = 0,
mirror plane X = 0. Design intent symmetric: Joe dotted the **right half**; the left half is its mirror image.

## Result in one paragraph

110 tape dots were triangulated from 15 photos (median 7 photos per dot, 1.3 px rms, 0.11 mm median 1-sigma along the
surface normal). 103 are on the seat top, 7 on the front face. A thin-plate spline through the mirrored top dots
predicts a left-out interior dot to **1.18 mm rms (max 3.2 mm)**, inside the 1/16" (1.6 mm) tolerance and better than
the 1.8 mm cloud polynomial it replaces. The seat is a saddle: two thigh hollows 18-24 mm below the rim, a ridge
(pommel) up the centre from y ≈ 300 that reaches rim height at the front edge, and a rolled front face.

## Files

| file | what |
|---|---|
| `dots.csv` | all 110 dots: x, y, z, per-axis sigma, sigma along the normal, photos used, rms |
| `front_face.csv` | the 7 front-face dots (ids 91, 94, 96, 100, 107, 108, 109) and how far below the top dot in the same column |
| `surface.json` | thin-plate formula (centres, weights, affine terms; checked against scipy to 4e-11 mm), the best polynomial (x^6 y^4, even in x) with coefficients, every model's CV numbers, rim table, sections, outline, asymmetry |
| `surface_grid.csv` | 10 mm grid inside the dotted region (both halves): z (spline), z (polynomial), depth below rim |
| `figures/depth_map.png` | depth below rim, plan view |
| `figures/sections.png` | transverse sections y = 150, 350, 510 and longitudinal x = 0, 120, 200, with dots and raw cloud |
| `figures/surface_3d.png` | shaded 3D view |
| `poses_dot_photos.json` | the 15 refined dot-photo poses |

Reproduce: `tools/py.sh -m 2 -t 5 tools/seat_surface.py` (180 MB, 3 s).

## Surface model, chosen by leave-one-dot-out cross-validation

A dot and its mirror image are left out together, so the mirror copy cannot leak the answer.

| model | LOO rms (mm) | LOO max | fit rms |
|---|---|---|---|
| polynomial even in x, x^4 y^4 | 4.13 | 15.6 | 3.13 |
| polynomial even in x, **x^6 y^4** (best polynomial) | 2.33 | 9.3 | 1.76 |
| polynomial even in x, x^8 y^5 | 4.96 | 25.6 | 1.45 |
| thin-plate spline, smoothing 0 | 1.58 | 6.9 | 0.00 |
| **thin-plate spline, smoothing 20** (chosen: ties for best LOO, smoother) | 1.59 | 6.9 | 0.06 |

- Interior dots (96, still inside the others' hull when left out): **1.18 mm rms, 3.2 mm max**.
- Edge dots (7, extrapolated when left out): 4.2 mm rms. Treat the surface as reliable only inside the dotted region
  (|x| ≤ 251, y 64-530).
- LOO is a pessimistic number: it doubles the local dot spacing. At the dots themselves the surface carries the dot
  error (0.1-0.2 mm); between dots, on the ~35 mm spacing, expect about 1 mm.
- Polynomials can't follow the pommel ridge and the hollows at the same time; that's why the cloud polynomial stalled at 1.8 mm.

## Shape (rim = highest point of the surface across each station)

| station | rim z | lowest point | depth below rim | centreline depth |
|---|---|---|---|---|
| y = 150 | 356.0 | 338.2 at x = 0 | 17.9 | 17.9 (single bowl) |
| y = 350 | 395.7 | 377.0 at \|x\| = 104 | 18.7 | 5.4 (pommel) |
| y = 510 | 424.2 | 399.8 at \|x\| = 104 | 24.4 | 1.3 (pommel at rim height) |

Rim height by y: 344.8 (y 100), 366.0 (200), 385.1 (300), 404.6 (400), 423.1 (500). A quadratic,
z = -4.3e-5 y² + 0.2231 y + 322.6, matches it to 0.94 mm rms (max 2.8). The table in `surface.json` is exact.

Front edge (`front_face.csv`): the front face drops 11-35 mm below the top in the same column: 19 mm at x = 67,
11 mm at x = 117, 16 mm at x = 165, 23 mm at x = 218, 35 mm at x = 254 (corner). On the centreline the roll-over
drops 21-30 mm.

Plan outline: no dots sit on the edge itself (the outermost dot is at x = 254). `surface.json → outline_cloud` gives an
approximate half-width per y from the raw cloud: about 230 at y 70, 250 at y 210, 258 at y 290, 262-267 at y 410-430
and 265 at y 520. It is cloud-derived and noisy (±10 mm, legs and arm joints contaminate some bands), so it is good
for a sketch, not a template.

## Errors, honestly

- **Pose method.** The 17 dot photos had no usable matches against the original model (the seat grain differs between
  sessions). They were posed through a half-resolution joint SfM with 10 of the original photos (25 photos, 0.79 px).
  That SfM was tied to the chair frame through 8 of those original cameras: centre residuals 0.9-2.4 mm, rotation
  residuals 0.06-0.19°, common rotation 0.04° about x (sd 0.05°), so the dot frame is not pitched relative to the chair
  frame. Poses were then refined on the dots by resection: per-photo 0.8-1.7 px.
- **Pose refinement did not move the dots.** Dots from the unrefined joint-SfM poses agree with the refined ones to
  0.5-0.7 mm rms per axis, with no slope in y (0.006 mm per 100 mm).
- **Photos.**
  - 15 of 17 photos are used.
  - IMG_1608 did not register.
  - IMG_1605 registered weakly (26 points) and is excluded.
  - IMG_1614 is posed but was skipped by the pose fix (11 pairs).
  - IMG_1507 (an old photo) was misregistered in the joint model and left out of the alignment.
- **Dots vs the raw cloud.**
  - Overall, cloud minus surface has a median of +0.12 mm on the right half (1666 cloud points, cloud noise 2.3 mm).
  - Along y it slopes: +2.0 mm at y 140-220, +1.4 at 220-300, +0.4 at 300-380, -1.1 at 380-460 and -1.8 at
    460-540. That is about 1 mm per 100 mm, the same on both halves.
  - The alignment check rules out a tilt of the dots (0.04°, against the 0.6° this would need). So most likely the old
    photo set saw the seat at grazing angles and the cloud carries a front/back bias there; the dot photos looked
    straight down.
  - **I trust the dots over the cloud on the seat, but this is inferred, not proven.** A tape-measure check of the
    front rim height against the back rim height (about 78 mm rise from y 100 to y 500) would settle it.
- **As-measured asymmetry.**
  - The dots can't measure it: they are on the right half only.
  - Against the cloud, in the same y bands, the left half sits 0.3 mm (140-220), 0.3 (220-300), 0.3 (300-380),
    -0.4 (380-460) and +1.0 (460-540) relative to the right.
  - Overall medians: left +0.31, right +0.12, so left minus right is +0.19 mm.
  - Sparse bands (y < 140: 50 left points) disagree by up to 3 mm and are not trustworthy.
  - So the chair is symmetric to about 0.5 mm wherever the cloud is dense. That is within what the cloud can resolve,
    not a measured zero.
- **Tape thickness.** Not subtracted. Painter's tape is about 0.1 mm, below every other error here.

## What's not done

- The seat edge outline as a template (needs dots on the edge or a dedicated edge trace in the photos).
- The left half is the mirror of the right by design; no left-side dots exist.
