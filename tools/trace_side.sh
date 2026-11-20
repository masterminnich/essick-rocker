#!/bin/bash
# USAGE: tools/trace_side.sh PREFIX CENTERS.sh   -- trace front leg, back leg, arm edge and seat edge in a side-frame orthophoto
source "$2"; P=$1; D=$(dirname $P)
work/toolkit/rk.sh tools/ribbon_trace.py $P --name fleg --half 16 30 --lam 0.8 --center "$FLEG" --out $D/fleg.json
work/toolkit/rk.sh tools/ribbon_trace.py $P --name bleg --half 19 34 --lam 0.8 --center "$BLEG" --out $D/bleg.json
work/toolkit/rk.sh tools/ribbon_trace.py $P --name arm --half 8 20 --lam 0.8 --center "$ARM" --out $D/arm.json
work/toolkit/rk.sh tools/ribbon_trace.py $P --name seat --half 10 28 --lam 0.8 --center "$SEAT" --out $D/seat.json
work/toolkit/rk.sh - $D <<'PY'
import sys, json
D = sys.argv[1]; out = {}
for n in ("fleg", "bleg", "arm", "seat"):
    d = json.load(open(f"{D}/{n}.json")); out[n + "_a"] = d[n + "_a"]; out[n + "_b"] = d[n + "_b"]
json.dump(out, open(f"{D}/side_curves.json", "w"))
PY
