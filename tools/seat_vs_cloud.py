import sys; sys.path.insert(0,'.')
import numpy as np, csv
from scipy.spatial import cKDTree
R=list(csv.DictReader(open('seat/dots.csv'))); X=np.array([[float(r[k]) for k in ('x_mm','y_mm','z_mm')] for r in R])
C=np.load('work/dense/chair_dense.npy'); seat_z=lambda y:338+0.155*y
S=C[(np.abs(C[:,0])<300)&(C[:,1]>-60)&(C[:,1]<580)&(C[:,2]>seat_z(C[:,1])-22)&(C[:,2]<seat_z(C[:,1])+45)]
t=cKDTree(S[:,:2]); out=[]
for x in X:
    idx=t.query_ball_point(x[:2],8)
    if len(idx)<4: out.append(np.nan); continue
    P=S[idx]; P=P[np.abs(P[:,2]-np.median(P[:,2]))<6]
    # local plane fit -> height at the dot
    A=np.c_[P[:,0]-x[0],P[:,1]-x[1],np.ones(len(P))]; c=np.linalg.lstsq(A,P[:,2],rcond=None)[0]; out.append(x[2]-c[2])
d=np.array(out); ok=np.isfinite(d)
print('dots with >=4 cloud pts within 8 mm:',ok.sum(),'of',len(d))
print('dot z - local cloud plane: median %.2f  mean %.2f  rms %.2f  MAD*1.48 %.2f'%(np.median(d[ok]),d[ok].mean(),np.sqrt((d[ok]**2).mean()),1.48*np.median(np.abs(d[ok]-np.median(d[ok])))))
print('percentiles 5,25,50,75,95', np.percentile(d[ok],[5,25,50,75,95]).round(2))
# mirrored check: dots at +x vs cloud at -x
Sm=S.copy(); Sm[:,0]*=-1; tm=cKDTree(Sm[:,:2]); o2=[]
for x in X:
    idx=tm.query_ball_point(x[:2],8)
    if len(idx)<4: o2.append(np.nan); continue
    P=Sm[idx]; P=P[np.abs(P[:,2]-np.median(P[:,2]))<6]; A=np.c_[P[:,0]-x[0],P[:,1]-x[1],np.ones(len(P))]; o2.append(x[2]-np.linalg.lstsq(A,P[:,2],rcond=None)[0][2])
o2=np.array(o2); ok2=np.isfinite(o2); print('dot z - MIRRORED (left-side) cloud: n %d median %.2f MAD*1.48 %.2f'%(ok2.sum(),np.median(o2[ok2]),1.48*np.median(np.abs(o2[ok2]-np.median(o2[ok2])))))
