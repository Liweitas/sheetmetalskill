# rev t7u LID builder: skill cad_build.lid03 copied verbatim, plus two parameters:
#   seam  : short-skirt (covered) end gap to the long-skirt inner face, straight AND bend zone (skill: corner_gap)
#   setback: long-skirt (covering) exposed end set back from the short-skirt outer face (straight skirt + skirt-side bend end)
# lid_t7u(job, seam=cg, setback=0) reproduces the skill LID exactly (asserted in build_main).
import math,itertools
import FreeCAD as F,Part
V=F.Vector
def reflect(s,axis):
    m=F.Matrix();setattr(m,["A11","A22","A33"][axis],-1);return s.transformed(m)
def box(x,y,z,p):return Part.makeBox(x,y,z,V(*p))
def lid_t7u(j,seam,setback):
    L,W,H,t,ri,g,skirt=[j[k] for k in ("L","W","H","t","Ri","g","skirt")]
    ro=ri+t
    hx=L/2+g+t;hy=W/2+g+t;cx=hx-ro;cy=hy-ro;cz=H-ro;bottom=H-skirt;straight=skirt-ro
    def bend(a0,a1,cyv):
        def pt(i,side):
            u=i/500;theta=math.pi/2*u;span=a0+(a1-a0)*u
            return V(side*span,cz+ro*math.cos(theta),cyv+ro*math.sin(theta))
        def curve(side,reverse=False):
            pts=[pt(i,side) for i in range(501)]
            if reverse:pts.reverse()
            c=Part.BSplineCurve();c.interpolate(pts);return c.toShape()
        wire=Part.Wire([Part.makeLine(pt(0,-1),pt(0,1)),curve(1),Part.makeLine(pt(500,1),pt(500,-1)),curve(-1,True)])
        surf=Part.makeCylinder(ro,2*hx+20,V(-hx-10,cz,cyv),V(1,0,0)).Face1.Surface
        face=Part.Face(surf,wire);face.validate()
        if not face.isValid():raise ValueError("03 cylindrical trim face invalid")
        return face.makeOffsetShape(-t,1e-7,fill=True)
    b1=bend(cx,hx-setback,cy);b2=bend(hy-ro,hy-t-seam,cx)
    m=F.Matrix();m.A11=0;m.A13=1;m.A31=-1;m.A33=0;b2=b2.transformed(m)
    bends=[b1,reflect(b1,2),b2,reflect(b2,0)]
    inter=max(abs(a.common(b).Volume) for a,b in itertools.combinations(bends,2))
    if inter>1e-5:raise ValueError("03 lid bend corners intersect %g"%inter)
    roof=box(2*cx,t,2*cy,(-cx,H-t,-cy))
    longwall=box(2*(hx-setback),straight,t,(-(hx-setback),bottom,hy-t))
    shortwall=box(t,straight,2*(hy-t-seam),(hx-t,bottom,-hy+t+seam))
    lid=roof.multiFuse(bends+[longwall,reflect(longwall,2),shortwall,reflect(shortwall,0)]).removeSplitter()
    tr=F.Matrix();tr.A22=0;tr.A23=-1;tr.A32=1;tr.A33=0;lid=lid.transformed(tr);lid.translate(V(L/2,W/2,0))
    return lid,inter
def cut_holes(j,shape,part='LID'):
    ro=j['Ri']+j['t']
    for h in j['holes']:
        if h['part_id']!=part:continue
        p=V(*h['point']);a=V(*h['axis'])
        shape=shape.cut(Part.makeCylinder(h['diameter']/2,4*ro+4,p-a*(2*ro+2),a)).removeSplitter()
    return shape
