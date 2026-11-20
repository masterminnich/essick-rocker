# ESSICK rocker: parts and landmarks

Conventions follow PLAN.md: left/right as seated; +X right, +Y forward, +Z up; mm internally.
Dimensions here are tape readings (see measurements/tape_readings.csv), not solved values.
Design is taken as mirror-symmetric about X=0 unless a photo contradicts it.

## Parts

| ID | What it looks like | How it is probably made | Joints |
|---|---|---|---|
| ROCKER_L, ROCKER_R | Long runners, about 1.2" wide (1493). Short front tip, square-ended, slightly upturned, a few inches ahead of the front leg (1496, 1578, 1579). The rear is long and upswept in an S-curve, ending in a rounded tip well behind the back leg (1471, 1500, 1507). Underside is a continuous rocking arc. | Bent lamination (glue lines worth checking in 1500/1493 crops); top face follows the bottom at constant depth except at the leg seats. | Legs land on the rocker top with leg width ≈ rocker width; no visible plug at leg/rocker. |
| FLEG_L, FLEG_R | Front legs, rectangular with rounded arrises. Lateral width at the rocker is ~1.27" (1495). Depth is ~1.56" just below the seat and ~1.15" between seat and arm (1497/1498), so the leg narrows above the seat. They rise past the seat side to carry the arm. | Solid, shaped (sculpted taper above seat). | Notched seat joint (Maloof style) at the seat's front corners, with an oval dark cross-grain plug on the outer face at seat level. Leg to arm: the leg end shows on the arm top (1528/1529). Leg to rocker as above. |
| BLEG_L, BLEG_R | Back legs. Seen from the side they curve, raking back above the seat. About 1.34" at the rocker (1494, low confidence) and ~1.55" lateral just below the crest (1556). The top ends roughly flush with the crest top and is rounded. | Solid, band-sawn curve, sculpted. | Notched seat joint at the seat's rear corners, with a plug on the outer face. The arm's rear end joins the back-leg front face. The crest is let in between the legs at the top. Leg to rocker. |
| SEAT | Thick, deeply dished seat. The front edge is scalloped: a centre ridge/peak between two thigh hollows, with raised front corners ("ears") that sit forward of the front legs (1496, 1558, 1562). Behind the slats there is a narrow ledge. The side edges are undercut/chamfered below (1570–1576). | Glued-up slab, carved. | Takes all four legs at notched corner joints. The three slats enter the seat top directly. |
| ARM_L, ARM_R | Flat arms, wider at the front, curving outward in plan (1537–1549, 1544). The front end is square-cut with rounded edges. | Solid, band-sawn plan, shaped. | Front: on the FLEG top (leg end exposed). Rear: into the BLEG front face. |
| CREST | Crest rail between the back legs. The top edge is arched up in the middle (1574, 1501); it is curved in plan (1544). About 3.05" tall at the slat gaps (1555). | Solid or laminated (curved in plan); not determinable. | Ends into BLEG_L/R; slat tops into its bottom edge. |
| SLAT_L, SLAT_C, SLAT_R | Three slats: a wide centre slat and two narrower outer slats. SLAT_C is ~3.0" at the seat (1551/1552) and ~3.87" just under the crest (1553). SLAT_R is ~1.6" at the seat (1551). Seen from the side the slats are curved (an S, giving lumbar support). The outer slats are twisted to follow the back's curve in plan. Gaps are ~1.0–1.1" at the seat and ~1.35" at the top. | Probably bent laminations (PLAN.md); thin. | Bottom: into a mortise in the seat top. Top: into the crest bottom (dark marks at the SLAT_C top corners, 1553). |

There are no stretchers. The count of 3 slats is confirmed in 1491, 1501, 1540, 1558 and 1574.

## Landmarks (stable IDs; L/R mirror pairs)

- PLUG_FLEG_{L,R}_SEAT_OUT: centre of the oval plug, outer face of the front leg at the seat. Seen in 1488/1489 (R), and 1519, 1570, 1572 and 1573 (L).
- PLUG_BLEG_{L,R}_SEAT_OUT: centre of the small plug, outer face of the back leg at the seat. Seen in 1488 (R), 1519 and 1572 (L), and 1500.
- SEAT_FRONT_PEAK: the centre peak of the seat front edge (top of edge). Seen in 1496, 1558, 1562 and 1534.
- SEAT_EAR_{L,R}: the front outer corner of the seat top, at the ears. Seen in 1496, 1558 and 1562.
- FLEG_{L,R}_ARM_TOP: the exposed front-leg end on the arm top. Seen in 1528 and 1529.
- ARM_{L,R}_FRONT_OUT / _FRONT_IN: the arm front-end corners.
- ROCKER_{L,R}_FRONT_TIP: the front end-face, top corner, centre. Seen in 1496 and 1579.
- ROCKER_{L,R}_REAR_TIP: the rear tip extreme. Seen in 1471, 1500 and 1507.
- FLEG_{L,R}_ROCKER_FRONT / BLEG_{L,R}_ROCKER_REAR: where the leg's front or rear face meets the rocker top.
- CREST_TOP_MID: the crest top edge at X=0. CREST_{L,R}_END_TOP: where the crest top meets a leg.
- BLEG_{L,R}_TOP: the back-leg top, at the outer corner.
- SLAT_C_TOP_{L,R}: where the SLAT_C side edges meet the crest bottom (dark marks). Seen in 1553 and 1574.
- SLAT_{L,C,R}_BASE_{L,R}: where the slat edges meet the seat top. Seen in 1551 and 1500.
- Scale points: SQ_HEEL (the outer corner of the framing square), SQ_BODY_END and SQ_TONGUE_END, and the inch numbers along both. RULER_ZERO is the centre hole of the Biscuit Buddy, and RULER_END_{L,R} its ends (see scale_objects.md).

## Template notes

- **Rockers:** a free curve on the bottom; the top is offset at constant thickness. Lay out from the side profiles (1471 for R, 1507 for L). Tolerance is 1/16". The front tips are short; the rear sweep is long.
- **Front legs:** straight in side view below the seat. They taper above the seat (1.56" to 1.15" deep). Cant and splay come from the front views (1496, 1558, 1562): the legs lean outward toward the rockers, and the rockers are farther apart than the seat-level leg spacing. The amount needs the solve.
- **Back legs:** a free curve in side view. They splay in rear view (1501, 1502): the rocker spacing at the rear is wider than the back-leg tops. Treat the crest-to-seat run as a tapering curve.
- **Seat:** the plan outline is mostly straight sides with a scalloped front edge (two arcs meeting at a centre peak). The dish is a free surface, so templates can only cover the outline and the edge profiles.
- **Arms:** a free curve in plan, roughly straight in side view, sloping down toward the back.
- **Crest:** the top edge is an arc in elevation and the rail is curved in plan, probably one radius each.
- **Slats:** curved in side view (an S), and they flare in elevation. Their edges are straight lines from about 3.0" at the seat to about 3.9" at the top for SLAT_C.
