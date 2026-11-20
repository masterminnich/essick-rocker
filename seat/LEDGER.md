# Seat ledger (branch `seat`)

## Done
- [x] 14:4x Drive sync: 17 new photos IMG_1595-1614 (taken 14:13-14:17), all f35=26 (no digital zoom), mixed EXIF
      orientations (6,1,8,3). Blue painter's-tape dashes (~5x15 mm) on the seat scoop (~80) and seat front edge; blue tape
      also on the cardboard sheet on the table. Contact sheet: work/seat/contact_new.jpg (tools/seat_contact.py).

## Now
- [→] Register the dot photos into work/solve/model (chair points only, PnP, fixed intrinsics).

## Next
- [ ] Detect blue tape (colour), match across photos (epipolar), triangulate, per-dot uncertainty -> seat/dots.csv
- [ ] Surface fit, depth-below-rim, 3 sections, L/R asymmetry, report.
