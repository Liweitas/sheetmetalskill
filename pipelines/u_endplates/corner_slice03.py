# 03 lid-corner closure: horizontal sections through each corner bend zone (Z from H-Ro-0.3 up, step 0.012); >1 piece = open slit, gap = min distance between pieces. usage: FC corner_slice03.py LID.step OUT.json
import sys,json;sys.path.insert(0,'/opt/freecad-dl/FreeCAD-1.1.1/usr/lib')
import FreeCAD as F,Part
V=F.Vector
L=Part.read(sys.argv[1]);bb=L.BoundBox;ro=1.8
out={}
for cn,(sx,sy) in {'X0Y0':(-1,-1),'XLY0':(1,-1),'X0YW':(-1,1),'XLYW':(1,1)}.items():
    C=V((bb.XMin+ro) if sx<0 else (bb.XMax-ro),(bb.YMin+ro) if sy<0 else (bb.YMax-ro),bb.ZMax-ro)
    LOC=L.common(Part.makeBox(10,10,10,V(C.x-5,C.y-5,C.z-5)))
    rows=[]
    for k in range(0,101):
        z=bb.ZMax-ro-0.3+k*0.012
        ws=LOC.slice(V(0,0,1),z);fs=sorted([Part.Face(w) for w in ws if w.isClosed()],key=lambda f:-f.Area);pieces=[]
        for f in fs:
            if any(p.common(f).Area>1e-9 for p in pieces):continue
            pieces.append(f)
        g=min((a.distToShape(b)[0] for i,a in enumerate(pieces) for b in pieces[i+1:]),default=0.0)
        rows.append([round(z,4),len(pieces),g])
    op=[r for r in rows if r[1]>1 and r[2]>1e-6]
    out[cn]={'z_scan':[rows[0][0],rows[-1][0],0.012],'open_z_range':[op[0][0],op[-1][0]] if op else None,'max_gap_mm':max((r[2] for r in rows),default=0),
             'z_at_max':max(rows,key=lambda r:r[2])[0],'rows':rows}
    print(cn,out[cn]['open_z_range'],out[cn]['max_gap_mm'],out[cn]['z_at_max'])
json.dump(out,open(sys.argv[2],'w'))
