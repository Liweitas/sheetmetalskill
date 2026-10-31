# Probe the formed LID corner (x=0,y=0 corner, box coords) on the ideal closed mid-surface (mitre of the two R(ri+t/2) bends,
# straight skirts at mid-thickness). A sample that is NOT inside material = opening through the shell.
import sys,math,json
sys.path.insert(0,'/opt/freecad-dl/FreeCAD-1.1.1/usr/lib')
import FreeCAD as F,Part
V=F.Vector
def probe(s,t=1.0,ri=0.8,H=133.0,g=0.5,skirt=15.0,n=60):
    ro=ri+t;rm=ri+t/2;o=-g-t;ax=o+ro;az=H-ro   # bend axes at x=ax (short) / y=ax (long), z=az
    pts=[]
    # bend-zone mitre: long-bend cylinder, x>=y
    for i in range(n+1):
        th=math.pi/2*i/n
        y=ax-rm*math.sin(th);z=az+rm*math.cos(th)
        for k in range(n+1):
            x=y+(ax+3-y)*k/n
            pts.append(('bend_long',th,(x,y,z)))
            pts.append(('bend_short',th,(y,x,z)))     # mirror x<->y: short bend
    # straight skirt corner: long skirt mid y=o+t/2 for x in [o+t/2, 3]; short skirt mid x=o+t/2 for y in [o+t/2,3]
    m=o+t/2
    for i in range(n+1):
        z=H-skirt+(skirt-ro)*i/n
        for k in range(n+1):
            x=m+(3-m)*k/n
            pts.append(('straight_long',None,(x,m,z)));pts.append(('straight_short',None,(m,x,z)))
    out={}
    miss=[]
    for tag,th,p in pts:
        ins=s.isInside(V(*p),1e-6,True)
        out.setdefault(tag,[0,0]);out[tag][0]+=1
        if not ins:out[tag][1]+=1;miss.append((tag,[round(c,3) for c in p]))
    return out,miss
if __name__=='__main__':
    s=Part.read(sys.argv[1]).Solids[0]
    # v2.8.2 fix: H defaulted to 133.0 (003's height) - on any other height every sample is 'open' (007 at H175: 3721/3721).
    # H = argv[2] if given, else the formed LID top (bbox ZMax).
    H=float(sys.argv[2]) if len(sys.argv)>2 else s.BoundBox.ZMax
    o,m=probe(s,H=H)
    print(json.dumps({'samples_and_open':o,'open_examples':m[:12],'open_bbox':[min(p[1][i] for p in m) for i in range(3)]+[max(p[1][i] for p in m) for i in range(3)] if m else None}))
