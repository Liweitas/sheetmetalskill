# v2.8.3 pipeline u_endplates (vendored from /workspace/orders/box-400x220x150/tools/build.py, S-201-1-20261021-001-v1 t46u).
# FreeCAD 1.1.1 + SheetMetal 0.8.21. Changes vs. the order copy are marked 'v2.8.2'. usage: FC build.py OUT_WORK_DIR  (env SM_JOB=brief.json)
# parts: U (bottom+2 long walls, X t..L-t), END_L / END_R (skill u_external_ends OUTER cover plates, 0 bends, full U end profile, seam 0, inset 0, top flush), LID (4 skirts, skill 03 sloped bend-root corners, corner_gap=CORNER_GAP)
import sys,json,math,hashlib,itertools,os
from pathlib import Path
SK=str(Path(__file__).resolve().parents[2]/'scripts')   # v2.8.2: skill scripts relative to this pipeline
sys.path.insert(0,'/opt/freecad-dl/FreeCAD-1.1.1/usr/lib');sys.path.insert(0,SK)
sys.path.insert(0,os.environ.get('SHEETMETAL_PATH',os.path.expanduser('~/.local/share/FreeCAD/Mod/SheetMetal')))
sys.path.insert(0,str(Path(__file__).parent))
import FreeCAD as F, Part, TechDraw
import SheetMetalNewUnfolder as NU
from measured_unfold import get_unfold
from formed_isometric import track_bends, records as bend_records
from cad_dxf import write_dxf
from cfg import *
V=F.Vector
out=Path(sys.argv[1]);out.mkdir(parents=True,exist_ok=False)
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
bbox=lambda s:[round(getattr(s.BoundBox,k),6) for k in ('XMin','YMin','ZMin','XMax','YMax','ZMax')]
s2=1/math.sqrt(2)
def wf(pts,arcs={}):
    return Part.Face(Part.Wire([Part.Arc(V(*p),V(*arcs[i]),V(*pts[(i+1)%len(pts)])).toShape() if i in arcs else Part.makeLine(V(*p),V(*pts[(i+1)%len(pts)])) for i,p in enumerate(pts)]))
def lbend(m,flen):
    """bend+flange L-section in local 2D (a,b): panel along +b at a in [0,t] starting at b=ro;
    flange along +a at b in [0,t]... returns points/arcs in local coords; m maps (a,b)->3D"""
    P=[(0,ro),(ro,0),(flen,0),(flen,t),(ro,t),(t,ro)]
    A={0:(ro-ro*s2,ro-ro*s2),4:(ro-ri*s2,ro-ri*s2)}
    return wf([m(*p) for p in P],{k:m(*v) for k,v in A.items()})
# ---------------- U ----------------
def ucs(y,z):return (t+SEAM,y,z)   # skill cad_build.py L62: U starts at X=t+seam
P=[(0,Hb),(0,ro),(ro,0),(W-ro,0),(W,ro),(W,Hb),(W-t,Hb),(W-t,ro),(W-ro,t),(ro,t),(t,ro),(t,Hb)]
A={1:(ro-ro*s2,ro-ro*s2),3:(W-ro+ro*s2,ro-ro*s2),7:(W-ro+ri*s2,ro-ri*s2),9:(ro-ri*s2,ro-ri*s2)}
U=wf([ucs(*p) for p in P],{k:ucs(*v) for k,v in A.items()}).extrude(V(L-2*t-2*SEAM,0,0))
holes=[]   # pairs list
def cyl(d,p,axis,ln=12):
    a=V(*axis);return Part.makeCylinder(d/2,ln,V(*p)-a*(ln/2),a)
for x in LONG_X:
    for y,side in ((0,'S'),(W,'N')):
        holes.append({'id':f'{side}{LONG_X.index(x)+1}','side':'长边Y=0' if y==0 else f'长边Y={W:g}','body_part':'U','point':[x,y,ZH],'axis':[0,1,0]})
for y in SHORT_Y:
    for x,side in ((0,'W'),(L,'E')):
        holes.append({'id':f'{side}{SHORT_Y.index(y)+1}','side':'短边X=0' if x==0 else f'短边X={L:g}','body_part':'END_L' if x==0 else 'END_R','point':[x,y,ZH],'axis':[1,0,0]})
for h in holes:
    if h['body_part']=='U':U=U.cut(cyl(D_BODY,[h['point'][0],h['point'][1]+(t/2 if h['point'][1]==0 else -t/2),ZH],h['axis']))
U=U.removeSplitter()
# ---------------- END plates ----------------
def endplate():
    # skill scripts/cad_build.py L63-65 verbatim profile (u_external_ends): inset=END_INSET, eradius=ro-inset, etop=Hb if top_flush
    inset=END_INSET;eradius=ro-inset;etop=Hb if END_TOP_FLUSH else Hb-inset
    pts=[(0,inset,etop),(0,inset,ro),(0,ro,inset),(0,W-ro,inset),(0,W-inset,ro),(0,W-inset,etop)]
    arcs={1:(0,ro-eradius*s2,ro-eradius*s2),3:(0,W-ro+eradius*s2,ro-eradius*s2)}
    s=wf(pts,arcs).extrude(V(t,0,0))
    for y in SHORT_Y:s=s.cut(cyl(D_BODY,[t/2,y,ZH],[1,0,0]))
    return s.removeSplitter()
EL=endplate()
ER=EL.copy();ER=ER.mirror(V(L/2,0,0),V(1,0,0))
# ---------------- LID ----------------
X0,X1,Y0,Y1=-g-t,L+g+t,-g-t,W+g+t       # lid outer
ZT=H;zb=H-skirt
# 03 corner scheme (skill references/lid-defaults03.md §03方案定义). Geometry = skill scripts/cad_build.py lid03() (L36-58) replicated
# with this job's values: long skirts full outer length; short skirts set back t+corner_gap; bend surfaces trimmed so each corner
# has 2 sloped edges at the bend root in the flat. corner_gap = CORNER_GAP (user explicit 0, '不要有缝').
import itertools as _it
def _reflect(s_,axis):
    m=F.Matrix();setattr(m,["A11","A22","A33"][axis],-1);return s_.transformed(m)
def lid03():
    cg=CORNER_GAP;Hh=H;hx=L/2+g+t;hy=W/2+g+t;cx=hx-ro;cy=hy-ro;cz=Hh-ro;bottom=Hh-skirt;straight=skirt-ro
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
        assert face.isValid(),"03 cylindrical trim face invalid"
        return face.makeOffsetShape(-t,1e-7,fill=True)
    b1=bend(cx,hx,cy);b2=bend(hy-ro,hy-t-cg,cx)
    m=F.Matrix();m.A11=0;m.A13=1;m.A31=-1;m.A33=0;b2=b2.transformed(m)
    bends=[b1,_reflect(b1,2),b2,_reflect(b2,0)]
    ov=max(abs(a_.common(b_).Volume) for a_,b_ in _it.combinations(bends,2))
    assert ov<=1e-5,("03 lid bend corners intersect",ov)
    roof=Part.makeBox(2*cx,t,2*cy,V(-cx,Hh-t,-cy))
    longwall=Part.makeBox(2*hx,straight,t,V(-hx,bottom,hy-t))
    shortwall=Part.makeBox(t,straight,2*(hy-t-cg),V(hx-t,bottom,-hy+t+cg))
    lid=roof.multiFuse(bends+[longwall,_reflect(longwall,2),shortwall,_reflect(shortwall,0)]).removeSplitter()
    tr=F.Matrix();tr.A22=0;tr.A23=-1;tr.A32=1;tr.A33=0;lid=lid.transformed(tr);lid.translate(V(L/2,W/2,0))
    return lid,ov
LID,_bend_ov=lid03()
for h in holes:
    p=list(h['point'])
    if h['axis']==[0,1,0]:p[1]=Y0+t/2 if p[1]==0 else Y1-t/2
    else:p[0]=X0+t/2 if p[0]==0 else X1-t/2
    LID=LID.cut(cyl(D_LID,p,h['axis']))
HH=handle_holes()
for h in HH:LID=LID.cut(cyl(D_HDL,[h['x'],h['y'],ZT-t/2],[0,0,1]))
LID=LID.removeSplitter()
# reference handle bodies (envelope only, marked REFERENCE; not sheet metal, not supplier geometry)
def handle_ref(cx):
    b=Part.makeBox(HREF_BX,HREF_BY,HREF_BT,V(cx-HREF_BX/2,HANDLE_CY-HREF_BY/2,ZT))
    p1=Part.makeBox(10,10,HREF_POST,V(cx-5,HANDLE_CY-50,ZT+HREF_BT));p2=Part.makeBox(10,10,HREF_POST,V(cx-5,HANDLE_CY+40,ZT+HREF_BT))
    bar=Part.makeBox(10,100,HREF_BAR,V(cx-5,HANDLE_CY-50,ZT+HREF_BT+HREF_POST))
    sh=b.fuse([p1,p2,bar]).removeSplitter()
    for h in HH:sh=sh.cut(cyl(D_HDL,[h['x'],h['y'],ZT+HREF_BT/2],[0,0,1],ln=HREF_BT+2))
    return sh.removeSplitter().Solids[0]
# v2.8.2: handles/reference envelopes only when the brief asks for them
HREF={f'HANDLE_REF_{"L" if cx<L/2 else "R"}':handle_ref(cx) for cx in HANDLE_CX} if HANDLE_REF else {}
parts={'U':U,'END_L':EL,'END_R':ER,'LID':LID}
for n,s in {**parts,**HREF}.items():assert s.isValid() and len(s.Solids)==1,(n,s.isValid(),len(s.Solids))
rep={'version':VER,'params':dict(L=L,W=W,H=H,t=t,Ri=ri,Ro=ro,K_ANSI=K,g=g,q=q,qmin=qmin,Hb=Hb,skirt=skirt,seam_gap=SEAM,end_inset=END_INSET,end_top_flush=END_TOP_FLUSH,ZH=ZH,BA=BA,OSSB=OSSB,BD=BD,D_body=D_BODY,D_lid=D_LID),'parts':{},'holes':holes}
def export(s,path,n):
    s.exportStep(str(path));b=Part.read(str(path))
    assert b.isValid() and len(b.Solids)==n and abs(b.Volume-s.Volume)<max(.01,s.Volume*1e-7),path
    return b
for n,s in parts.items():
    b=export(s,out/(n+'.step'),1);rep['parts'][n]={'bbox':bbox(b),'size':[round(b.BoundBox.XLength,6),round(b.BoundBox.YLength,6),round(b.BoundBox.ZLength,6)],'volume_mm3':b.Volume,'mass_kg':b.Volume*DENSITY}
for n,s in HREF.items():
    b=export(s,out/(n+'.step'),1);rep['parts'][n]={'reference_only':True,'bbox':bbox(b),'size':[round(b.BoundBox.XLength,6),round(b.BoundBox.YLength,6),round(b.BoundBox.ZLength,6)]}
allp={**parts,**HREF}
asm=Part.makeCompound(list(allp.values()));export(asm,out/'ASSEMBLY.step',len(allp))
shifts={'U':[0,0,0],'END_L':[-80,0,0],'END_R':[80,0,0],'LID':[0,0,90],'HANDLE_REF_L':[0,0,150],'HANDLE_REF_R':[0,0,150]}
ex=[]
for n,s in allp.items():
    c=s.copy();c.translate(V(*shifts[n]));ex.append(c)
exc=Part.makeCompound(ex);export(exc,out/'EXPLODED.step',len(allp))
rep['assembly']={'bbox':bbox(asm),'body_bbox':bbox(Part.makeCompound([U,EL,ER])),'exploded_shifts':shifts}
rep['intersections_mm3']={a+'/'+b:abs(allp[a].common(allp[b]).Volume) for a,b in itertools.combinations(allp,2)}
rep['min_distance_mm']={a+'/'+b:allp[a].distToShape(allp[b])[0] for a,b in itertools.combinations(allp,2)}
# ---- handle hole checks ----
X0i,X1i,Y0i,Y1i=X0+ro,X1-ro,Y0+ro,Y1-ro   # lid top flat (bend tangent) limits
hc=[]
for h in HH:
    x,y=h['x'],h['y'];r=D_HDL/2
    p=V(x,y,ZT-t/2);ln=Part.makeLine(V(x,y,ZT-5),V(x,y,ZT+5))
    open_=max(LID.common(Part.makeLine(V(x+(r-.02)*math.cos(a),y+(r-.02)*math.sin(a),ZT-3),V(x+(r-.02)*math.cos(a),y+(r-.02)*math.sin(a),ZT+1))).Length for a in [k*math.pi/6 for k in range(12)])
    mat=min(LID.common(Part.makeLine(V(x+(r+.05)*math.cos(a),y+(r+.05)*math.sin(a),ZT-3),V(x+(r+.05)*math.cos(a),y+(r+.05)*math.sin(a),ZT+1))).Length for a in [k*math.pi/6 for k in range(12)])
    edge_to_lid_outer=min(x-X0,X1-x,y-Y0,Y1-y)-r
    edge_to_bend_tangent=min(x-X0i,X1i-x,y-Y0i,Y1i-y)-r
    sk=[(hh['point'],hh['id']) for hh in holes]
    # 3D distance hole-edge to skirt fixing hole edge (lid frame: skirt holes on lid skirt faces)
    def skpt(pt):
        q_=list(pt)
        if q_[1]==0:q_[1]=Y0
        elif q_[1]==W:q_[1]=Y1
        elif q_[0]==0:q_[0]=X0
        else:q_[0]=X1
        return q_
    dsk=min((math.dist([x,y,ZT],skpt(pt))-r-D_LID/2,i) for pt,i in sk)
    hc.append({**h,'d':D_HDL,'axis_line_lid_material_mm':LID.common(ln).Length,'open_at_r':open_,'material_at_r_plus_min':mat,
      'edge_to_lid_outer':edge_to_lid_outer,'edge_to_bend_tangent':edge_to_bend_tangent,'edge_to_nearest_skirt_hole_3d':dsk[0],'nearest_skirt_hole':dsk[1]})
pp=[(a,b) for a,b in itertools.combinations(HH,2)]
rep['handle_holes']=hc
rep['handle_pattern_check']={}
for tag in sorted({h['handle'] for h in HH}):   # v2.8.2: no handles -> empty
    hs={h['id'][3:]:h for h in HH if h['handle']==tag}
    rep['handle_pattern_check'][tag]={'wide_pitch':abs(hs['W2']['y']-hs['W1']['y']),'narrow_pitch':abs(hs['N2']['y']-hs['N1']['y']),'row_spacing':abs(hs['W1']['x']-hs['N1']['x']),
       'wide_row_x':hs['W1']['x'],'narrow_row_x':hs['N1']['x'],'wide_row_toward_centre':abs(hs['W1']['x']-L/2)<abs(hs['N1']['x']-L/2)}
rep['handle_mirror_ok']=len(HANDLE_CX)!=2 or all(any(abs(a['x']+b['x']-L)<1e-9 and abs(a['y']-b['y'])<1e-9 for b in HH if b['handle']=='R') for a in HH if a['handle']=='L')
rep['handle_min_hole_edge_spacing']=min((math.dist([a['x'],a['y']],[b['x'],b['y']])-D_HDL for a,b in pp),default=None)
# rivet tail / rivet-nut envelope under lid top: Ø12 x 12 below lid inner face (generic envelope, model 待确认)
tails=Part.makeCompound([Part.makeCylinder(6,12,V(h['x'],h['y'],ZT-t-12)) for h in HH])
if HH: rep['rivet_tail_envelope']={'envelope':'Ø12 x 12 below lid inner face (generic, rivet model 待确认)','min_dist_to_body':min(tails.distToShape(p_)[0] for p_ in (U,EL,ER)),'intersect_body_mm3':sum(abs(tails.common(p_).Volume) for p_ in (U,EL,ER))}
# screwdriver access: horizontal lines from each skirt screw outward 200 mm vs handle bodies; lid lift-off path: handles move with lid
acc=[]
for hh in holes:
    pt=V(*skpt(hh['point']));a=V(*hh['axis']);sgn=-1 if (hh['point'][1]==0 and hh['axis']==[0,1,0]) or (hh['point'][0]==0 and hh['axis']==[1,0,0]) else 1
    if not HREF: continue   # v2.8.2: no handle bodies -> nothing to clear
    ln=Part.makeLine(pt,pt+a*sgn*200)
    cone=Part.makeCone(4,30,200,pt,a*sgn)   # screwdriver + hand envelope (Ø8 at screw growing to Ø60)
    acc.append({'id':hh['id'],'min_dist_axis_to_handle':min(ln.distToShape(s_)[0] for s_ in HREF.values()),'cone_intersect_handle_mm3':sum(abs(cone.common(s_).Volume) for s_ in HREF.values())})
rep['screwdriver_access']=acc
# lid-to-body gap measurements (gap datum: lid skirt INNER face to body wall OUTER face)
rep['gap_check']={
 'long_side_Y0':{'lid_skirt_inner_y':Y0+t,'body_outer_y':0.0,'gap':0.0-(Y0+t)},
 'long_side_YW':{'lid_skirt_inner_y':Y1-t,'body_outer_y':W,'gap':(Y1-t)-W},
 'short_side_X0':{'lid_skirt_inner_x':X0+t,'body_outer_x':0.0,'gap':0.0-(X0+t)},
 'short_side_XL':{'lid_skirt_inner_x':X1-t,'body_outer_x':L,'gap':(X1-t)-L},
 'top':{'lid_top_inner_z':ZT-t,'body_top_z':Hb,'q':ZT-t-Hb},
 'lid_root_fillet_vs_body_edge':{'fillet_centre_offset':[ro-t-g,ZT-t-ri-Hb],'dist_to_body_edge':math.hypot(ri-g,ri-q),'Ri':ri,'clearance':ri-math.hypot(ri-g,ri-q),'clearance_if_q0':ri-math.hypot(ri-g,ri)}}
# hole coaxial check: probe lines through each hole axis
co=[]
for h in holes:
    p=V(*h['point']);a=V(*h['axis'])
    line=Part.makeLine(p-a*10,p+a*10)
    bp=parts[h['body_part']]
    lid_in=LID.common(line).Length; body_in=bp.common(line).Length
    # radius check: offset line by r_body-0.01 in Z must miss body material (inside hole) and r_lid-0.01 miss lid
    def miss(shape,r):
        res=[]
        for ang in range(0,360,30):
            d=V(0,0,1)*math.sin(math.radians(ang))+ (V(1,0,0) if h['axis']==[0,1,0] else V(0,1,0))*math.cos(math.radians(ang))
            ln=Part.makeLine(p+d*r-a*10,p+d*r+a*10);res.append(shape.common(ln).Length)
        return max(res)
    co.append({'id':h['id'],'axis_line_material_lid_mm':lid_in,'axis_line_material_body_mm':body_in,
      'lid_open_at_r':miss(LID,D_LID/2-0.02),'body_open_at_r':miss(bp,D_BODY/2-0.02),
      'body_material_at_r_plus':miss(bp,D_BODY/2+0.05),'lid_material_at_r_plus':miss(LID,D_LID/2+0.05)})
rep['hole_coaxial']=co
# ---- end cover checks (skill u_external_ends; user: 端板盖U 不要留缝隙，完全遮盖) ----
cv={}
for n,xo,xi in (('END_L',0.0,t),('END_R',L,L-t)):
    useg=U.slice(V(1,0,0),(t+SEAM+1e-3) if n=='END_L' else (L-t-SEAM-1e-3))     # U end profile wires (YZ)
    uface=Part.Face(Part.Wire(useg[0].Edges)) if len(useg)==1 else None
    eface=[f for f in parts[n].Faces if isinstance(f.Surface,Part.Plane) and abs(abs(f.normalAt(0,0).x)-1)<1e-9 and abs(f.CenterOfMass.x-xi)<1e-6][0]
    # project U profile onto plate inner plane
    up=uface.copy();up.translate(V(xi-up.CenterOfMass.x,0,0))
    ep_full=Part.Face(eface.OuterWire)
    uncovered=up.cut(ep_full).Area
    eb=parts[n].BoundBox;ub=U.BoundBox
    # bottom corner arcs of end plate vs U outer arcs (concentric, same radius)
    arcs_=[e for e in parts[n].Edges if isinstance(e.Curve,Part.Circle) and abs(e.Curve.Axis.x)>.999 and e.Curve.Radius>1]
    cv[n]={'U_end_profile_area_mm2':up.Area,'U_end_profile_uncovered_area_mm2':uncovered,'axial_gap_mm':(ub.XMin-eb.XMax) if n=='END_L' else (eb.XMin-ub.XMax),
           'outline_vs_U_outer':{'Y':[eb.YMin,eb.YMax],'U_Y':[ub.YMin,ub.YMax],'Z':[eb.ZMin,eb.ZMax],'U_Z':[ub.ZMin,ub.ZMax]},
           'corner_arcs':sorted({(round(e.Curve.Center.y,6),round(e.Curve.Center.z,6),round(e.Curve.Radius,6)) for e in arcs_}),
           'U_outer_arc_centres':[[ro,ro,ro],[W-ro,ro,ro]],'exposed_U_end_edge':uncovered>1e-6 or abs(eb.YMin-ub.YMin)>1e-9 or abs(eb.YMax-ub.YMax)>1e-9 or abs(eb.ZMax-ub.ZMax)>1e-9}
rep['end_cover']=cv
# single-layer check on every M4 axis: total body material along the axis line = t (no double layer / no bend zone)
body=Part.makeCompound([U,EL,ER]);export(body,out/'BODY.step',3)
for c_,h in zip(co,holes):
    p=V(*h['point']);a=V(*h['axis'])
    # probe parallel to the axis just outside the hole (r+0.3) at 4 positions: total sheet thickness crossed = layers*t
    lay=[];oth=V(1,0,0) if h['axis']==[0,1,0] else V(0,1,0)
    for d_ in (V(0,0,1),V(0,0,-1),oth,-oth):
        q_=p+d_*(D_BODY/2+0.3);lay.append(body.common(Part.makeLine(q_-a*30,q_+a*30)).Length)
    c_['body_layers_mm_near_axis']=lay
# ---- 03 corner closure after forming (ray probe from the corner bend centre through the R vertex octant) ----
Ro_=ro;A03=skirt-ro;B03=A03+BA
rep['corner03']={'scheme':'03','corner_gap':CORNER_GAP,'Ro':ro,'A':A03,'BA90':BA,'B':B03,'short_skirt_retreat':t+CORNER_GAP,
  'corner_gap_source':CORNER_GAP_SOURCE,'P1':[B03-ro,A03],'P2':[B03,B03],'P3':[A03,B03-(ri-CORNER_GAP)],'bend_pair_overlap_mm3':_bend_ov,'corners':{}}
# closure probe moved to tools/corner_probe03.py (runs on work/LID.step; BOP line probes on the BSpline lid were too slow here)
# ---------------- unfold ----------------
doc=F.newDocument('S201')
def plane_face(shape):
    fs=[f for f in shape.Faces if isinstance(f.Surface,Part.Plane) and abs(abs(f.normalAt(0,0).z)-1)<1e-6 and abs(f.CenterOfMass.z)<1e-5]
    return max(fs,key=lambda f:f.Area)
def unfold(name,shape,nb,rootsel):
    ob=doc.addObject('Part::Feature',name+'_u');ob.Shape=shape
    faces=[i for i,f in enumerate(shape.Faces) if isinstance(f.Surface,Part.Plane) and rootsel(f)]
    root=max(faces,key=lambda i:shape.Faces[i].Area)
    with track_bends(NU):(_,flat,lines,normal,bends),tm=get_unfold(NU.BendAllowanceCalculator.from_single_value(K,'ansi'),ob,'Face'+str(root+1),t)
    assert len(bends)==nb,(name,len(bends))
    rot=F.Placement(V(),F.Rotation(normal,V(0,0,1))).toMatrix();lines=lines.transformed(rot);flat=flat.transformed(rot)
    bb=flat.BoundBox;d=V(-bb.XMin,-bb.YMin,-bb.ZMax);flat.translate(d);lines.translate(d)
    comb=F.Placement(d,F.Rotation()).toMatrix().multiply(rot)
    bl=[[[p.x,p.y] for p in e.discretize(Number=2)] for e in lines.Edges]
    recs=bend_records(bends,comb,root+1,normal,bl)
    return flat,lines,recs,tm
roots={'U':(2,lambda f:f.normalAt(0,0).z<-.999 and abs(f.CenterOfMass.z)<1e-6),
       'LID':(4,lambda f:f.normalAt(0,0).z>.999 and abs(f.CenterOfMass.z-H)<1e-6)}
# END plates: 0 bends -> rigid transform to flat (SKILL.md L78 '零折端板只刚体转平'); outer face to Z=0, viewed from outside
RIG={'END_L':F.Matrix(0,1,0,0, 0,0,1,0, 1,0,0,0, 0,0,0,1),          # X'=Y, Y'=Z, Z'=X   (det +1)
     'END_R':F.Matrix(0,-1,0,W, 0,0,1,0, -1,0,0,L, 0,0,0,1)}        # X'=W-Y, Y'=Z, Z'=L-X (det +1)
flats={}
for n in ('U','END_L','END_R','LID'):
    if n in roots:
        nb,sel=roots[n];flat,lines,recs,tm=unfold(n,parts[n],nb,sel)
    else:
        flat=parts[n].transformed(RIG[n]);recs=[];lines=Part.Compound([]);tm={'method':'rigid transform, 0 bends (SKILL.md L78)','t':t}
        assert abs(flat.Volume-parts[n].Volume)<1e-6
    face=plane_face(flat)
    if n=='LID' and CORNER_GAP==0:
        # t46u: with corner_gap 0 the short-skirt end face lies ON the long-skirt inner face, so the fused formed solid has one shared
        # corner column (t x t x A). SheetMetal's native unfold gives that column to BOTH flaps (long flap full outer length AND a t-wide
        # tab on each short-flap end: outline step (A,B-Ro)->(A,P3y)). Measured: flat net area*t + bend-volume correction - formed volume = 4*t*t*A.
        # Physically that tab would collide with the long-skirt end (t*t*A per corner). The 03 definition (short skirt set back t+gap) puts the
        # short-flap side edge at P3y; trim exactly that tab. Native-vs-provided area then differs by 4*t*A (reported by native03_check, not hidden).
        fb=face.BoundBox;fx_,fy_=fb.XLength,fb.YLength;A3=skirt-ro;B3=A3+BA;y0_=B3-ro;y1_=B3-(ri-CORNER_GAP)
        segs=[e for e in face.OuterWire.Edges if e.Curve.TypeId=='Part::GeomLine' and abs(e.Vertexes[0].Point.x-e.Vertexes[-1].Point.x)<1e-6 and abs(min(e.Vertexes[0].Point.x,fx_-e.Vertexes[0].Point.x)-A3)<1e-6 and abs(e.Length-t)<1e-6]
        assert len(segs)==4 and abs(y1_-y0_-t)<1e-9,(len(segs),y0_,y1_)
        cut=Part.makeCompound([Part.makeBox(A3+1,t+1,3*t,V(x_,y_,-2*t)) for x_ in (-1,fx_-A3) for y_ in (y0_-1,fy_-y1_)])
        # v2.8.3 pipeline: keep the untrimmed native flat as evidence (run.py runs native03 on it too); subdir so it is never staged as a part STEP
        (out/'native_untrimmed').mkdir(exist_ok=True);export(flat,out/'native_untrimmed'/'LID_UNFOLD.step',1);write_dxf(out/'native_untrimmed'/'LID_CUT_raw.dxf',face)
        before=face.Area;flat=flat.cut(cut).removeSplitter();face=plane_face(flat)
        rep['corner03']['gap0_shared_column_trim']={'reason':'native unfold assigns the shared t x t x A corner column to both flaps when corner_gap=0',
          'tab_mm':[A3,t],'tabs':4,'removed_area_mm2':before-face.Area,'short_flap_side_edge_y_before':y0_,'after':y1_,'untrimmed_flat_volume_excess_mm3':4*t*t*A3}
    assert abs(flat.Volume/face.Area-t)<1e-5
    export(flat,out/(n+'_UNFOLD.step'),1)
    if n=='LID':
        rep['parts'][n]['flat_outer_lines']=[[[e.Vertexes[0].Point.x,e.Vertexes[0].Point.y],[e.Vertexes[-1].Point.x,e.Vertexes[-1].Point.y]] for e in face.OuterWire.Edges if e.Curve.TypeId=='Part::GeomLine']
    try:r,idx,diff=write_dxf(out/(n+'_CUT_raw.dxf'),face);dxfval='skill validate_planar'
    except ValueError as ex:
        # line-arc TANGENT joints (R1.8 corners, inset 0): skill 1e-7 test returns 2 numerically split tangent points.
        # Same writer, same readback/area check; only the tangent intersection points are merged at 1e-6 (as u_l_t7u build_main own check).
        import dxf_topology as DT
        _orig=DT.intersections
        def _merged(e,f,_o=_orig):
            pts=_o(e,f);m=[]
            for p_ in pts:
                if not any(math.dist(p_,q_)<1e-6 for q_ in m):m.append(p_)
            ends_=[a for a in (DT.ends(e) if e['type']!='CIRCLE' else []) for b in (DT.ends(f) if f['type']!='CIRCLE' else []) if DT.dist(a,b)<1e-6]
            return [ends_[0] if ends_ and min(math.dist(p_,q_) for q_ in ends_)<1e-6 else p_ for p_ in m]
        DT.intersections=_merged
        try:r,idx,diff=write_dxf(out/(n+'_CUT_raw.dxf'),face)
        finally:DT.intersections=_orig
        dxfval='skill validate_planar with tangent points merged at 1e-6 (first try: %s)'%ex
    rep['parts'][n]['dxf_validation']=dxfval
    flats[n]=face
    rep['parts'][n].update(flat_size=[face.BoundBox.XLength,face.BoundBox.YLength],flat_area=face.Area,dxf_native_area_diff=diff,bend_records=recs,thickness=tm,
      dxf_circles=sorted(round(2*x['radius'],4) for x in r if x['type']=='CIRCLE'),
      flat_circles=[[x['center'][0],x['center'][1],2*x['radius']] for x in r if x['type']=='CIRCLE'],
      bend_lines=[[[p.x,p.y] for p in e.discretize(Number=2)] for e in lines.Edges])
F.closeDocument(doc.Name)
proj={}
for name,shape in {**parts,'ASSEMBLY':asm}.items():
    proj[name]={}
    for label,dvec in (('front',V(0,-1,0)),('right',V(1,0,0)),('top',V(0,0,1))):
        g_=TechDraw.projectEx(shape,dvec);pol=[];hid=[]
        for k,item in enumerate(g_[:10]):
            for e in item.Edges:
                (pol if k<5 else hid).append([[p.x,p.y] for p in e.discretize(Deflection=.05)])
        proj[name][label]={'vis':pol,'hid':hid}
json.dump(proj,open(out/'projections.json','w'))
# section at X=L/2 (YZ) for lid/body gap view (v2.8.2: was hardcoded X=200)
sec={}
for n in ('U','LID'):
    sl=parts[n].slice(V(1,0,0),L/2)
    sec[n]=[[[p.y,p.z] for p in w.discretize(Deflection=.005)] for w in sl]
json.dump(sec,open(out/'section_mid.json','w'))
mesh={}
for name,shape in allp.items():
    v,f=shape.tessellate(.2);mesh[name]={'v':[list(x) for x in v],'f':[list(x) for x in f]}
json.dump({'parts':mesh,'shifts':shifts},open(out/'mesh.json','w'))
# end-cover corner close-ups (fine mesh of the region near X=0,Y=0) + 2D sections for the PDF corner detail
cm={}
for tag,zb_,zt_,names in (('bottom',-1,26,('U','END_L')),('top',124,151,('U','END_L','LID')),('lid03',133,151,('LID',))):
    clip=Part.makeBox(27 if tag!='lid03' else 22,27 if tag!='lid03' else 22,zt_-zb_,V(-2,-2,zb_));cm[tag]={}
    for n in names:
        c=allp[n].common(clip)
        if c.Volume>0:v,f=c.tessellate(.01);cm[tag][n]={'v':[list(x) for x in v],'f':[list(x) for x in f]}
json.dump(cm,open(out/'corner_mesh.json','w'))
csec={}
for n in ('U','END_L','LID'):
    csec[n]={'XY_Z74':[[[p.x,p.y] for p in w.discretize(Deflection=.002)] for w in allp[n].slice(V(0,0,1),round(Hb/2))],
             'XZ_Y110':[[[p.x,p.z] for p in w.discretize(Deflection=.002)] for w in allp[n].slice(V(0,1,0),W/2)]}
# end plate outline (YZ) vs U outer profile at bottom corner
csec['END_L']['YZ_face']=[[[p.y,p.z] for p in w.discretize(Deflection=.002)] for w in EL.slice(V(1,0,0),0.5)]
csec['U']['YZ_X200']=[[[p.y,p.z] for p in w.discretize(Deflection=.002)] for w in U.slice(V(1,0,0),L/2)]
json.dump(csec,open(out/'corner_sections.json','w'))
json.dump({n:{'wires':[[[p.x,p.y] for p in w.discretize(Deflection=.02)] for w in fc.Wires],'bbox':[fc.BoundBox.XMin,fc.BoundBox.YMin,fc.BoundBox.XMax,fc.BoundBox.YMax]} for n,fc in flats.items()},open(out/'flats.json','w'))
json.dump(rep,open(out/'report.json','w'),indent=1,ensure_ascii=False)
for n in parts:print(n,rep['parts'][n]['size'],rep['parts'][n].get('flat_size'),rep['parts'][n]['dxf_circles'])
print(json.dumps({k:rep[k] for k in ('intersections_mm3','min_distance_mm','gap_check')},indent=1))
