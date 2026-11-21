#!/bin/zsh
# USAGE: tools/seat_side_ends/jackknife.sh   -- the full solve per side (TAG R_ext / L_ext) and one solve per left-out photo (jk/R_<photo>, jk/L_<photo>).
# 2 + 22 runs of tools/edge_tri.py, one after the other, a few seconds each.
cd "$(dirname "$0")/../.."
tools/seat_side_ends/tri.sh R R_ext | cut -c1-160
tools/seat_side_ends/tri.sh L L_ext | cut -c1-160
for S in R L; do
  if [ "$S" = R ]; then ALL=(1547 1548 1549 1479 1480 1481 1474 1475 1476 1477 1478 1472 1473); else ALL=(1537 1538 1539 1518 1517 1522 1521 1509 1510); fi
  for p in $ALL; do
    rest=(); for q in $ALL; do [ "$q" != "$p" ] && rest+=($q); done
    tools/seat_side_ends/tri.sh $S jk/${S}_$p ${(j:,:)rest} > /dev/null 2>&1 || echo "fail $S $p"
  done
done
echo done
