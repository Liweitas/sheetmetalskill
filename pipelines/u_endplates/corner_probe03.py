# 03 lid-corner closure probe after forming (FreeCAD python). usage: FC corner_probe03.py LID.step OUT.json
# Rays from each corner bend centre C=(X0+ro|X1-ro, Y0+ro|Y1-ro, H-ro) over the outward octant; a ray is OPEN if it meets
# no lid material between 0.5*Ri and 3*Ro (ray-triangle test on a fine tessellation of the lid clipped to an 8 mm box).
import sys,json,math,numpy as np
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent));from cfg import *
sys.path.insert(0,'/opt/freecad-dl/FreeCAD-1.1.1/usr/lib');import FreeCAD as F,Part
V=F.Vector
LID=Part.read(sys.argv[1]);bb=LID.BoundBox
X0,X1,Y0,Y1,ZT=bb.XMin,bb.XMax,bb.YMin,bb.YMax,bb.ZMax
def hits(tri,O,D,tmin,tmax):
    e1=tri[:,1]-tri[:,0];e2=tri[:,2]-tri[:,0];out=[]
    for d in D:
        p=np.cross(d,e2);det=(e1*p).sum(1);ok=np.abs(det)>1e-12;inv=np.where(ok,1/np.where(ok,det,1),0)
        s=O-tri[:,0];u=(s*p).sum(1)*inv;q=np.cross(s,e1);v=(q*d).sum(1)*inv;tt=(e2*q).sum(1)*inv
        m=ok&(u>=-1e-9)&(v>=-1e-9)&(u+v<=1+1e-9)&(tt>=tmin)&(tt<=tmax);out.append(int(m.sum()))
    return np.array(out)
N=60;res={'method':f'ray-triangle on tessellation(0.005) of LID clipped to 8mm box; {(N+1)**2} rays/corner over the outward octant, r in [0.5Ri,3Ro]','corners':{}}
for cn,(sx,sy) in {'X0Y0':(-1,-1),'XLY0':(1,-1),'X0YW':(-1,1),'XLYW':(1,1)}.items():
    C=np.array([(X0+ro) if sx<0 else (X1-ro),(Y0+ro) if sy<0 else (Y1-ro),ZT-ro])
    LOC=LID.common(Part.makeBox(8,8,8,V(*(C-4))))
    pts,fs=LOC.tessellate(0.005);P=np.array([[p.x,p.y,p.z] for p in pts]);tri=P[np.array(fs)]
    dirs=[];ang=[]
    for i in range(N+1):
        for j in range(N+1):
            th=math.pi/2*i/N;ph=math.pi/2*j/N
            dirs.append([sx*math.cos(th)*math.cos(ph),sy*math.cos(th)*math.sin(ph),math.sin(th)]);ang.append((math.degrees(th),math.degrees(ph)))
    D=np.array(dirs);h=hits(tri,C,D,0.5*ri,3*ro);op=h==0
    chord=0.0
    if op.any():
        Do=D[op];chord=float(max(np.linalg.norm(Do[:,None]-Do[None],axis=2).max(),0))*ro
    # straight skirt zone + bend zone of each skirt: horizontal diagonal rays and vertical-plane rays
    sz=[]
    for z_ in (ZT-14.5,ZT-12,ZT-8,ZT-4,ZT-2.0):
        O=np.array([C[0],C[1],z_]);hz=hits(tri,O,np.array([[sx/math.sqrt(2),sy/math.sqrt(2),0]]),0,3.9)[0] if z_>C[2]-4 else None
        if hz is None:
            # outside the 8 mm clip: use BOP on a short line (few calls only)
            ln=Part.makeLine(V(*O),V(O[0]+sx*6,O[1]+sy*6,z_));m=LID.common(ln).Length;sz.append({'z':round(z_,3),'material_mm':m,'closed':bool(m>0.5)})
        else: sz.append({'z':round(z_,3),'crossings':int(hz),'closed':bool(hz>=2)})
    res['corners'][cn]={'centre':C.tolist(),'rays':int(len(D)),'open_rays':int(op.sum()),'open_fraction':float(op.mean()),
        'open_theta_deg_range':[float(min(a[0] for a,o in zip(ang,op) if o)),float(max(a[0] for a,o in zip(ang,op) if o))] if op.any() else None,
        'open_phi_deg_range':[float(min(a[1] for a,o in zip(ang,op) if o)),float(max(a[1] for a,o in zip(ang,op) if o))] if op.any() else None,
        'opening_max_chord_at_Ro_mm':chord,'diagonal_rays_by_z':sz,'triangles':int(len(tri))}
json.dump(res,open(sys.argv[2],'w'),indent=1);print(json.dumps({k:{kk:v[kk] for kk in ('open_rays','open_fraction','opening_max_chord_at_Ro_mm','open_theta_deg_range','open_phi_deg_range')} for k,v in res['corners'].items()},indent=1))
