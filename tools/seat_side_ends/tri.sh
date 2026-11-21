#!/bin/zsh
# USAGE: tools/seat_side_ends/tri.sh SIDE(L|R) TAG [PHOTOS]   env SEEDX, DDEG   (PHOTOS comma-separated; default = the photos of parts/seat_edge.json's plan solve)
# Triangulates the seat's side-edge top arris on the plan sheet (work/parts/side{L,R}/sp, the sheet of PR #8) with tools/edge_tri.py and the
# settings of parts/seat_plan_seeds_{L,R}.json, but with the seed carried on from y 110 back to the back leg and from y 400 forward to the
# front leg (both seeds below). Writes work/seatside/TAG.json and TAG_dump.json (each photo's own trace). Tiny compute, a few seconds.
cd "$(dirname "$0")/../.."
S=$1; TAG=$2
if [ "$S" = R ]; then
  IN="215,250"; SP=1548; PH="1547,1548,1549,1479,1480,1481,1474,1475,1476,1477,1478,1472,1473"
  SEED="224,82 227,95 231,110 237,140 244,180 250.5,220 256.5,260 261,300 265,340 267,380 267.5,410 268,430 268.5,447"
else
  IN="-215,250"; SP=1538; PH="1537,1538,1539,1518,1517,1522,1521,1509,1510"
  SEED="-224.5,84 -226.5,95 -228.5,110 -235,140 -241,180 -246.5,220 -250,260 -252.5,300 -258,340 -263.5,380 -265.5,410 -266,428 -266.5,443"
fi
[ -n "$3" ] && PH=$3
[ -n "$SEEDX" ] && SEED=$SEEDX   # env SEEDX: another seed (e.g. the stretch in front of the front leg), DDEG: depth polynomial degree (1)
mkdir -p "work/seatside/$(dirname $TAG)"
D="work/seatside/${TAG}_dump.json"; [ -f "$D" ] && /bin/rm "$D"
work/toolkit/rk.sh tools/edge_tri.py work/parts/side$S/sp --seed="$SEED" --inside=$IN --mode all --band 7 --ddeg ${DDEG:-1} --depth-guess -2 \
  --seed-photo $SP --photos $PH --max-photos 20 --name seat${S}_plan --dump "$D" --out work/seatside/${TAG}.json
