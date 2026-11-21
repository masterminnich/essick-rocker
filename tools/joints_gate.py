"""USAGE: python3 -I tools/joints_gate.py MODEL_joints.json [MODEL_joinery.json]      (plain python, json only)
The assembly check's verdict, run by tools/model.sh after every build. Reads what tools/audit_joints.py measured and prints one
line per joint, then PASS or FAIL (exit 1). Rules (mm, cm3):
  every part is a closed solid
  a pair that is a joint touches: gap 0 and a contact face of at least MIN_CONTACT cm2 within 1 mm
  no pair runs into another: overlap below MAX_OVERLAP cm3 (booleans leave slivers of about 0.01)
  a pair that must stay clear (arm / seat, slat / back leg, slat / slat) keeps a gap of at least MIN_CLEAR mm
The numbers behind each rule are in the json; this file only applies the thresholds."""
import sys, json
MAX_OVERLAP, MIN_CONTACT, MIN_CLEAR = 0.05, 3.0, 5.0
CLEAR = {"ARM_R~SEAT", "SLAT_R~BLEG_R", "SLAT_C~SLAT_R"}
J = json.load(open(sys.argv[1])); bad = []
for k, p in J["parts"].items():
    if not p.get("watertight"): bad.append(f"{k} is not a closed solid")
for k, r in J["pairs"].items():
    ov, gap, con = r.get("overlap_cm3"), r.get("min_gap_mm"), r.get("area_within_1mm_cm2")
    if "overlap_err" in r or gap is None: bad.append(f"{k}: could not be measured ({r.get('overlap_err', r.get('note', ''))})"); continue
    if k in CLEAR:
        ok = ov <= MAX_OVERLAP and gap >= MIN_CLEAR; what = f"clear by {gap} mm"
    else:
        ok = ov <= MAX_OVERLAP and gap == 0 and con >= MIN_CONTACT; what = f"contact {con} cm2, overlap {ov} cm3, gap {gap} mm"
    print(f"  {'ok  ' if ok else 'FAIL'} {k:20s} {what}")
    if not ok: bad.append(f"{k}: {what}")
if len(sys.argv) > 2:
    R = json.load(open(sys.argv[2]))
    for k, p in R.get("parts", {}).items():
        if not p.get("watertight"): bad.append(f"{k} is not a closed solid after joinery")
    for o in R.get("open", []): print("  open:", o)
print("assembly check:", "PASS" if not bad else "FAIL"); [print("  ", b) for b in bad]
sys.exit(1 if bad else 0)
