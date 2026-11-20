"""USAGE: tools/py.sh -m 1 -t 2 tools/seat_tiltcheck.py
Is the dot set tilted? Needs work/seat/dots_joint.csv (dots triangulated from the UNREFINED joint-SfM poses: back up
work/seat/poses.json + seat/dots.csv, run seat_align.py --exclude 1507 and seat_dots.py dots, copy, restore) and
work/seat/dots_posefix.csv (the pose-fixed dots). Prints the joint-vs-posefix difference as planes in x, y and the
dot-minus-local-cloud-plane residual (cloud points within 10 mm in plan) as a plane + by y band. Tiny."""
import numpy as np, csv
from scipy.spatial import cKDTree
L=lambda f: np.array([[float(r[k]) for k in ("x_mm","y_mm","z_mm")] for r in csv.DictReader(open(f))])
A=L("work/seat/dots_joint.csv"); B=L("work/seat/dots_posefix.csv")
d,j=cKDTree(B).query(A,distance_upper_bound=6); ok=np.isfinite(d); a,b=A[ok],B[j[ok]]
D=a-b; print("matched",ok.sum(),"diff mean",D.mean(0).round(2),"rms",np.sqrt((D**2).mean(0)).round(2))
G=np.c_[np.ones(len(b)),b[:,0],b[:,1]]
for k,n in enumerate("xyz"): c=np.linalg.lstsq(G,D[:,k],rcond=None)[0]; print(f" d{n} = {c[0]:.2f} + {c[1]*100:.3f}/100mm*x + {c[2]*100:.3f}/100mm*y")
C=np.load("work/dense/chair_dense.npy")[:,:3]; T=cKDTree(C[:,:2])
for lab,P in (("joint",A),("posefix",B)):
    r=[]
    for p in P:
        ii=T.query_ball_point(p[:2],10)
        if len(ii)<8: r.append(np.nan); continue
        Q=C[ii]; Q=Q[np.abs(Q[:,2]-p[2])<15]
        if len(Q)<8: r.append(np.nan); continue
        c=np.linalg.lstsq(np.c_[np.ones(len(Q)),Q[:,:2]-p[:2]],Q[:,2],rcond=None)[0]; r.append(p[2]-c[0])
    r=np.array(r); m=np.isfinite(r)&(np.abs(np.nan_to_num(r))<8)
    c=np.linalg.lstsq(np.c_[np.ones(m.sum()),P[m,0],P[m,1]],r[m],rcond=None)[0]
    res=r[m]-np.c_[np.ones(m.sum()),P[m,0],P[m,1]]@c
    print(f"{lab}: n={m.sum()} dot-minus-cloud median {np.median(r[m]):.2f}  plane {c[0]:.2f} + {c[1]*100:.3f}/100mm x + {c[2]*100:.3f}/100mm y  (resid rms {np.sqrt((res**2).mean()):.2f})")
    for y0 in (60,180,300,420):
        s=m&(P[:,1]>=y0)&(P[:,1]<y0+120); print(f"   y {y0}-{y0+120}: median {np.median(r[s]):.2f} n={s.sum()}")
