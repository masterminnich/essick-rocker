# Seat ledger (branch `seat`)

## Done
- [x] Drive sync: 17 dot photos IMG_1595-1614, contact sheet (tools/seat_contact.py).
- [x] Registration against the original model by SIFT bank + PnP: FAILED (weak cross-session matches; 0 inliers). Kept
      for the record (tools/seat_register.py).
- [x] Half-res joint SfM, dot photos + 10 original photos (tools/seat_sfm.py: 25 photos, 0.79 px, 2.1 GB, 95 s), tied to
      the chair frame through 8 original cameras (tools/seat_align.py --exclude 1507: 0.9-2.4 mm, 0.06-0.19°).
- [x] Blue-tape detection + epipolar matching + triangulation (tools/seat_dots.py), poses refined on the dots
      (tools/seat_posefix.py, 3 rounds). 110 dots, median 7 photos, 1.3 px, 0.11 mm normal sigma.
- [x] Front face vs top split (same-column rule): 7 front-face, 103 top.
- [x] Surface (tools/seat_surface.py): thin-plate spline on mirrored dots, LOO 1.18 mm interior (1.59 all);
      depth map, 3 transverse + longitudinal sections, 3D view, rim table, cloud outline (approx.), asymmetry vs cloud.
- [x] Tilt check (tools/seat_tiltcheck.py, tools/seat_aligncheck.py): dots vs cloud slope ~1 mm/100 mm in y; not from
      pose refinement (joint vs posefix dots: no slope) nor alignment (0.04° pitch). Attributed to cloud bias (inferred).
- [x] seat/REPORT.md.

## Now
- [→] PR seat -> main with the journey and figures.

## Next
- [ ] Optional: tape-measure the back and front rim heights to confirm the dots over the cloud (expected rise ~78 mm, y 100 -> 500).
- [ ] Optional: dots on the seat edge (or an edge trace) for a plan-outline template.
