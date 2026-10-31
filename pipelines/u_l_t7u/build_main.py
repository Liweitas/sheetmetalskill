# v2.8.2 pipeline u_l_t7u (DEFAULT structure): vendored from 干画图3's /workspace/orders/box-180x420x175/addendum-tools (S-201-1-20261021-007-v1).
# v2.8.2 changes: hardcoded order/skill/tmp paths -> env SM_ORDER (order folder) + this folder; job features from release_config.json.
# Revision E main geometry (outside skill adapter, HOLD):
#  * U+L with L COVERING U, covering edges of L set back S (cfg.L_COVER_SETBACK, default 0 = flush, user t16u 2026-10-26; was 0.2) (U trimmed to L inner envelope y>=t, z>=t, Ri round)
#  * LID (rev t7u) = skill 03 lid geometry rebuilt by lid_t7u.py (asserted identical to the skill LID at seam=corner_gap, setback=0)
#    with seam=0 (short skirts closed against long-skirt inner face, straight AND bend zone) and long (covering) skirts set back SL (cfg.LID_LONG_SKIRT_SETBACK, default 0 = flush; was 0.2)
#    (S-201-1-20261021-007-v1 / box-180x420x175, same workflow as S-201-1-20261025-002-v1: same structure as 003, NO handle, 2x O12 roof holes near the left short edge (t13u); params in cfg.py)
#  * native SheetMetal unfold (skill measured_unfold/get_unfold), skill cad_dxf.write_dxf CUT, separate BEND DXF
# usage: FreeCAD-python build_main_E.py resolved_job.json skill_LID.step outdir
import sys,json,math,hashlib,itertools
from pathlib import Path
SK=str(Path(__file__).resolve().parents[2]/'scripts')   # v2.8.2: relative skill scripts
sys.path.insert(0,'/opt/freecad-dl/FreeCAD-1.1.1/usr/lib');sys.path.insert(0,SK)
import os;sys.path.insert(0,os.environ.get('SHEETMETAL_PATH',os.path.expanduser('~/.local/share/FreeCAD/Mod/SheetMetal')))
import FreeCAD as F, Part, TechDraw
import SheetMetalNewUnfolder as NU
from measured_unfold import get_unfold
from formed_isometric import track_bends, records as bend_records
from cad_dxf import write_dxf, dxf_record
from cut_dxf import parse_dxf
import dxf_topology as DT
def write_dxf_ext(path,face):
    # same entity format as skill cad_dxf.write_dxf; skill topology check is applied to outer+circles,
    # the non-circular cutout loop gets its own closure / containment / no-intersection checks
    pairs=[(0,"SECTION"),(2,"HEADER"),(9,"$INSUNITS"),(70,4),(0,"ENDSEC"),(0,"SECTION"),(2,"ENTITIES")]
    records=[];indices=[]
    for wire in [face.OuterWire]+[w for w in face.Wires if not w.isSame(face.OuterWire)]:
        loop=[];wr=[dxf_record(e) for e in wire.Edges]
        if wire.isClosed() and all(isinstance(e.Curve,Part.Circle) for e in wire.Edges):
            c0=wire.Edges[0].Curve
            if all((e.Curve.Center-c0.Center).Length<1e-7 and abs(e.Curve.Radius-c0.Radius)<1e-7 for e in wire.Edges) and abs(wire.Length-2*math.pi*c0.Radius)<1e-5:
                wr=[{"type":"CIRCLE","center":[c0.Center.x,c0.Center.y],"radius":c0.Radius}]
        for r in wr:
            loop.append(len(records));records.append(r);pairs.extend([(0,r["type"]),(8,"CUT")])
            if r["type"]=="LINE":pairs.extend([(10,r["p"][0]),(20,r["p"][1]),(11,r["q"][0]),(21,r["q"][1])])
            else:
                pairs.extend([(10,r["center"][0]),(20,r["center"][1]),(40,r["radius"])])
                if r["type"]=="ARC":pairs.extend([(50,r["start"]),(51,r["end"])])
        indices.append(loop)
    pairs.extend([(0,"ENDSEC"),(0,"EOF")]);path.write_text("\n".join(str(v) for pair in pairs for v in pair)+"\n")
    ents=parse_dxf(path)
    other=[l for l in indices[1:] if not (len(l)==1 and ents[l[0]]['type']=='CIRCLE')]
    std=[i for l in [indices[0]]+[l for l in indices[1:] if l not in other] for i in l]
    sub=[ents[i] for i in std];DT.validate_planar(sub,list(range(len(indices[0]))))
    checks=[]
    for l in other:
        # skill validator's 1e-7 tangent test is too strict for line-arc tangency (R3 corners); own check at 1e-6
        loopents=[ents[i] for i in l];E=[DT.ends(e) for e in loopents]
        gaps=[min(DT.dist(E[i][k],E[j][m]) for j in range(len(E)) if j!=i for m in (0,1)) for i in range(len(E)) for k in (0,1)]
        if max(gaps)>1e-6:raise ValueError('cutout loop not closed')
        for e in loopents:
            for f in [ents[i] for i in std]:
                if DT.intersections(e,f):raise ValueError('cutout loop intersects other contour')
            for f in [ents[i] for i in std if ents[i]['type']=='CIRCLE']:
                if DT.distance(e,DT.xy(f))<float(f[40])+DT.GUARD:raise ValueError('cutout too close to hole')
        outer_poly=[p for i in indices[0] for p in DT.sampled(ents[i])]
        if not all(DT.inside(DT.ends(e)[0],outer_poly) for e in loopents):raise ValueError('cutout outside outer contour')
        checks.append({'entities':len(l),'types':[e['type'] for e in loopents],'closure_max_gap_mm':max(gaps),'inside_outer':True,'no_intersection_with_outer_or_holes':True})
    def entity_edge(e):
        if e['type']=='LINE':return Part.makeLine(V(float(e[10]),float(e[20]),0),V(float(e[11]),float(e[21]),0))
        c=V(float(e[10]),float(e[20]),0);r=float(e[40])
        if e['type']=='CIRCLE':return Part.makeCircle(r,c)
        st=math.radians(float(e[50]));sw=(math.radians(float(e[51]))-st)%(2*math.pi)
        pt=lambda u:c+V(r*math.cos(st+u*sw),r*math.sin(st+u*sw),0)
        return Part.Arc(pt(0),pt(.5),pt(1)).toShape()
    reb=[Part.Face(Part.Wire(Part.__sortEdges__([entity_edge(ents[i]) for i in l]))) for l in indices]
    act=reb[0]
    for h in reb[1:]:act=act.cut(h)
    diff=abs(face.cut(act).Area)+abs(act.cut(face).Area)
    if not act.isValid() or diff>1e-5:raise ValueError('DXF differs from flat face '+str(diff))
    return records,indices,diff,checks
from corner03 import profile
from lid_t7u import lid_t7u,cut_holes
sys.path.insert(0,__import__('os').path.dirname(__import__('os').path.abspath(__file__)));import cfg
V=F.Vector
job=json.load(open(sys.argv[1]));lid_src=sys.argv[2];out=Path(sys.argv[3]);out.mkdir(parents=True,exist_ok=False)
L,W,H,t,ri,g,q,skirt,cg,K=[job[k] for k in ('L','W','H','t','Ri','g','q','skirt','corner_gap','K_ANSI')]
assert job['method']=='u_wrap_bottom_l'
S=cfg.L_COVER_SETBACK      # L cover setback; user t16u 2026-10-26: L盖U，不留缝隙，不退让0.2mm -> default 0 (old orders: 0.2)
EPS=0.01                   # cross-check variant only
ro=ri+t;hb=H-t-q
# box-180x420x175 t13u: two O12 roof holes near the LEFT SHORT edge (x=0), along Y, pitch 30, symmetric about Y=W/2,
# hole CENTRE 50 from the lid outer edge (lid outer face x=-1.5) -> centre x=48.5 (box datum), edge 44. No handle.
CUT=None;RD=cfg.ROOF_D
# v2.8.2: the 007 job asserts below (2 roof holes exactly as cfg, no handle) only run when cfg has roof holes; otherwise the
# job must carry NO roof/handle holes at all (default = none, never invented).
ROOF16=sorted(tuple(h['point'][:2]) for h in job['holes'] if h['part_id']=='LID' and RD and abs(h['diameter']-RD)<1e-9)
if cfg.ROOF_PTS:
    assert ROOF16==sorted(cfg.ROOF_PTS),ROOF16
    assert ROOF16[0][0]==ROOF16[1][0] and abs((ROOF16[0][1]+ROOF16[1][1])/2-W/2)<1e-9 and abs(ROOF16[1][1]-ROOF16[0][1]-cfg.ROOF_PITCH)<1e-9
    assert abs(ROOF16[0][0]-RD/2+(g+t)-cfg.ROOF_EDGE_TO_LID_EDGE)<1e-9
else:
    assert not ROOF16
OLD_LID_HOLES={6.6:[tuple(h['point'][:2]) for h in job['holes'] if h['part_id']=='LID' and h.get('purpose')=='handle']}
assert len(OLD_LID_HOLES[6.6])==0 and job['mounting_patterns']==[] and cfg.HANDLE_CENTRES==[], 'handles: use pipeline u_endplates handle code or extend here'   # no handle
HCS=[];HC=None;HANDLE_HOLES=[]
assert all(h['part_id']!='LID' or h['diameter'] in ((RD,4.5) if RD else (4.5,)) for h in job['holes'])
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
bbox=lambda s:[round(getattr(s.BoundBox,k),6) for k in ('XMin','YMin','ZMin','XMax','YMax','ZMax')]
def wire_face(points,arcs=None):
    arcs=arcs or {}
    return Part.Face(Part.Wire([Part.Arc(V(*p),V(*arcs[i]),V(*points[(i+1)%len(points)])).toShape() if i in arcs else Part.makeLine(V(*p),V(*points[(i+1)%len(points)])) for i,p in enumerate(points)]))
def u_cross(width,height,xyz):   # copied from skill cad_build.py (identical U section)
    points=[(0,height),(0,ro),(ro,0),(width-ro,0),(width,ro),(width,height),(width-t,height),(width-t,ro),(width-ro,t),(ro,t),(t,ro),(t,height)]
    mids={1:(ro-ro/math.sqrt(2),ro-ro/math.sqrt(2)),3:(width-ro+ro/math.sqrt(2),ro-ro/math.sqrt(2)),7:(width-ro+ri/math.sqrt(2),ro-ri/math.sqrt(2)),9:(ro-ri/math.sqrt(2),ro-ri/math.sqrt(2))}
    return wire_face([xyz(*p) for p in points],{i:xyz(*p) for i,p in mids.items()})
def holes_for(name,shape):
    for h in job['holes']:
        if h['part_id']!=name:continue
        p=V(*h['point']);a=V(*h['axis'])
        shape=shape.cut(Part.makeCylinder(h['diameter']/2,4*ro+4,p-a*(2*ro+2),a)).removeSplitter()
    return shape
rep={'contract':'manual-E-main-v1 (outside skill adapter; HOLD)','params':dict(L=L,W=W,H=H,t=t,Ri=ri,g=g,q=q,skirt=skirt,corner_gap_bend_zone=cg,K_ANSI=K,body_height=hb,L_cover_setback=S),'parts':{}}
# ---------- U (trimmed to L inner envelope) ----------
U_full=u_cross(L,W,lambda x,p:(x,W-p,0)).extrude(V(0,0,hb))
Zb=hb+5;Yb=W+5
keep=wire_face([(-5,t,Zb),(-5,t,ro),(-5,ro,t),(-5,Yb,t),(-5,Yb,Zb)],{1:(-5,ro-ri/math.sqrt(2),ro-ri/math.sqrt(2))}).extrude(V(L+10,0,0))
U=holes_for('U',U_full.common(keep).removeSplitter())
# ---------- L (covers U, setback S on covering edges and top) ----------
top=hb-S
prof=[(S,0,top),(S,0,ro),(S,ro,0),(S,W-S,0),(S,W-S,t),(S,ro,t),(S,t,ro),(S,t,top)]
arcs={1:(S,ro-ro/math.sqrt(2),ro-ro/math.sqrt(2)),5:(S,ro-ri/math.sqrt(2),ro-ri/math.sqrt(2))}
Lp=wire_face(prof,arcs).extrude(V(L-2*S,0,0))
rc=ro-S   # back bottom corners concentric with U outer corner arcs (centres (ro,W-ro),(L-ro,W-ro))
xy=[(S,-5,-5),(L-S,-5,-5),(L-S,W-ro,-5),(L-ro,W-S,-5),(ro,W-S,-5),(S,W-ro,-5)]
xarcs={2:(L-ro+rc/math.sqrt(2),W-ro+rc/math.sqrt(2),-5),4:(ro-rc/math.sqrt(2),W-ro+rc/math.sqrt(2),-5)}
Lp=Lp.common(wire_face(xy,xarcs).extrude(V(0,0,hb+10))).removeSplitter()
Lpart=holes_for('L',Lp)
# ---------- LID ----------
lid0=Part.read(lid_src);assert len(lid0.Solids)==1
# no handle holes -> skill LID used as is (no plug/re-cut step)
# ---------- rev t7u: lid corner closure = long skirt covers short skirt end (setback SL, default 0), no gap ----------
SEAM=0.0                  # short (180, W) skirts butt the long-skirt inner face: zero gap in straight skirt and at bend-zone skirt tangent
SL=cfg.LID_LONG_SKIRT_SETBACK   # long skirts = covering skirts; exposed end setback from the short-skirt outer face (default 0 = flush, user t16u; old 0.2)
_rep_lid,_i=lid_t7u(job,cg,0.0);_rep_lid=cut_holes(job,_rep_lid)
repro={'sym_diff_vs_skill_LID':abs(_rep_lid.cut(lid0).Volume)+abs(lid0.cut(_rep_lid).Volume),'vol':_rep_lid.Volume,'skill_vol':lid0.Volume}
assert repro['sym_diff_vs_skill_LID']<1e-4,repro
def mk(seam,setback):
    s,inter=lid_t7u(job,seam,setback);s=cut_holes(job,s)
    assert inter<=1e-5 and s.isValid() and len(s.Solids)==1,(seam,setback,inter);return s.Solids[0],inter
LID,lid_bend_inter=mk(SEAM,SL)
LID_eps,_=mk(EPS,SL)    # unfold cross-check variant
hx=L/2+g+t;hy=W/2+g+t;straight=skirt-ro
rep['lid']={'source_skill_LID_step':lid_src,'source_sha256':sha(lid_src),'vol_skill_LID':lid0.Volume,'vol_LID_t7u':LID.Volume,
 'skill_reproduction_check':repro,'corner_rev':'t7u','corner_seam_mm':SEAM,'long_skirt_cover_setback_mm':SL,'covering_skirts':'long (420, L) skirts cover the short (180, W) skirt ends',
 'bend_solids_pairwise_intersection_mm3':lid_bend_inter,
 'long_skirt_x_extent_box':[-g-t+SL,L+g+t-SL],'short_skirt_outer_x_box':[-g-t,L+g+t],'long_skirt_inner_y_box':[-g,W+g],
 'roof_holes_16':ROOF16,'roof_hole_d':RD,'handle_holes':HANDLE_HOLES,'handle_centre':HC,'handle_centres':HCS,'old_roof_holes':{str(k):v for k,v in OLD_LID_HOLES.items()},'cutout':CUT}
# straight-skirt seam probes: mid-thickness of short skirt, just inside the former 0.4 gap (must be material now)
pr=[]
for xs in (-g-t/2, L+g+t/2):
    for y in (-g+0.2,W+g-0.2):
        pr.append(s_in:=LID.isInside(V(xs,y,H-skirt+straight/2),1e-7,True))
rep['lid']['straight_seam_points_in_material']=pr
# setback probes: long skirt mid-thickness at x=-1.4 (inside setback, must be air) and x=-1.2 (material)
if SL>0:
    rep['lid']['setback_probe']={'inside_setback_air':[not LID.isInside(V(-g-t+SL/2,y,H-skirt+straight/2),1e-7,True) for y in (-g-t/2,W+g+t/2)],
     'beyond_setback_material':[LID.isInside(V(-g-t+SL+0.1,y,H-skirt+straight/2),1e-7,True) for y in (-g-t/2,W+g+t/2)]}
else:  # user t16u: flush long-skirt end -> material right at the short-skirt outer face
    rep['lid']['setback_probe']={'flush_end_material':[LID.isInside(V(-g-t+0.1,y,H-skirt+straight/2),1e-7,True) for y in (-g-t/2,W+g+t/2)]}
parts={'U':U,'L':Lpart,'LID':LID}
def export(s,path,n):
    assert s.isValid() and len(s.Solids)==n,path
    s.exportStep(str(path));b=Part.read(str(path))
    assert b.isValid() and len(b.Solids)==n and abs(b.Volume-s.Volume)<max(.01,s.Volume*1e-7),path
    return b
for n,s in parts.items():
    b=export(s,out/(n+'.step'),1);rep['parts'][n]={'formed_step':n+'.step','sha256':sha(out/(n+'.step')),'bbox':bbox(b),'volume_mm3':b.Volume}
asm=Part.makeCompound(list(parts.values()));export(asm,out/'ASSEMBLY.step',3)
shifts={'U':[0,0,0],'L':[-(L*.35+20),0,0],'LID':[0,0,skirt+hb*.5]}
ex=[]
for n,s in parts.items():
    c=s.copy();c.translate(V(*shifts[n]));ex.append(c)
exc=Part.makeCompound(ex);export(exc,out/'EXPLODED.step',3)
rep['assembly']={'bbox':bbox(asm),'body_bbox':bbox(Part.makeCompound([U,Lpart])),'exploded_translations_mm':shifts,'exploded_bbox':bbox(exc)}
rep['intersections']={a+'/'+b:abs(parts[a].common(parts[b]).Volume) for a,b in itertools.combinations(parts,2)}
ub=U.BoundBox;lb=Lpart.BoundBox
rep['L_covers_U_measured']={'L_x_setback_left':lb.XMin-ub.XMin,'L_x_setback_right':ub.XMax-lb.XMax,'L_bottom_back_setback_y':ub.YMax-lb.YMax,'L_top_setback_z':ub.ZMax-lb.ZMax,
 'U_front_edge_y':ub.YMin,'U_bottom_edge_z':ub.ZMin,'L_front_face_y':lb.YMin,'L_bottom_face_z':lb.ZMin,
 'U_front_edge_hidden_behind_L':ub.YMin==t,'setback':S,'note':'L front panel covers U side-wall front edges; L bottom covers U bottom edges; covering edges of L are '+(f'{S:g} inside U outer faces' if S else 'flush with U outer faces (0 gap, 0 setback, user t16u)')}
# ---------- unfold ----------
doc=F.newDocument('E_main')
def plane_face(shape):
    fs=[f for f in shape.Faces if isinstance(f.Surface,Part.Plane) and abs(abs(f.normalAt(0,0).z)-1)<1e-6 and abs(f.CenterOfMass.z)<1e-5]
    return max(fs,key=lambda f:f.Area)
def unfold(name,shape,nb,lid=False):
    ob=doc.addObject('Part::Feature',name+'_u');ob.Shape=shape
    faces=[i for i,f in enumerate(shape.Faces) if isinstance(f.Surface,Part.Plane)]
    if lid:faces=[i for i in faces if abs(shape.Faces[i].CenterOfMass.z-H)<1e-5 and shape.Faces[i].normalAt(0,0).z>.999]
    root=max(faces,key=lambda i:shape.Faces[i].Area)
    with track_bends(NU):(_,flat,lines,normal,bends),tm=get_unfold(NU.BendAllowanceCalculator.from_single_value(K,'ansi'),ob,'Face'+str(root+1),t)
    assert len(bends)==nb,(name,len(bends))
    rot=F.Placement(V(),F.Rotation(normal,V(0,0,1))).toMatrix();lines=lines.transformed(rot);flat=flat.transformed(rot)
    bb=flat.BoundBox;d=V(-bb.XMin,-bb.YMin,-bb.ZMax);flat.translate(d);lines.translate(d)
    comb=F.Placement(d,F.Rotation()).toMatrix().multiply(rot)
    bl=[[[p.x,p.y] for p in e.discretize(Number=2)] for e in lines.Edges]
    recs=bend_records(bends,comb,root+1,normal,bl)
    return flat,lines,recs,tm,comb
def write_bend(path,lines):
    pairs=[(0,'SECTION'),(2,'HEADER'),(9,'$INSUNITS'),(70,4),(0,'ENDSEC'),(0,'SECTION'),(2,'ENTITIES')]
    for e in lines.Edges:
        a,b=e.Vertexes[0].Point,e.Vertexes[-1].Point;pairs+= [(0,'LINE'),(8,'BEND'),(10,a.x),(20,a.y),(11,b.x),(21,b.y)]
    pairs+=[(0,'ENDSEC'),(0,'EOF')];path.write_text('\n'.join(str(v) for p in pairs for v in p)+'\n')
flats={}
for name,shape,nb in (('U',U,2),('L',Lpart,1)):
    flat,lines,recs,tm,comb=unfold(name,shape,nb);face=plane_face(flat)
    assert abs(flat.Volume/face.Area-t)<1e-5
    export(flat,out/(name+'_UNFOLD.step'),1)
    r,idx,diff=write_dxf(out/(name+'.dxf'),face);write_bend(out/(name+'_BEND.dxf'),lines)
    flats[name]=face
    rep['parts'][name].update(flat_size=[face.BoundBox.XLength,face.BoundBox.YLength],flat_area=face.Area,dxf_native_area_diff=diff,bend_records=recs,thickness=tm,dxf_sha256=sha(out/(name+'.dxf')),
      dxf_circles=sorted(round(2*x['radius'],4) for x in r if x['type']=='CIRCLE'),dxf_arcs=sum(x['type']=='ARC' for x in r),bend_lines=[[[p.x,p.y] for p in e.discretize(Number=2)] for e in lines.Edges])
# LID (rev t7u): native unfold of the t7u solid itself (no flat patch)
flat,lines,recs,tm,comb=unfold('LID',LID,4,True);pface=plane_face(flat)
assert abs(flat.Volume/pface.Area-t)<1e-5
BA=math.pi/2*(ri+K*t);pr0=profile(t,ri,skirt,SEAM,BA);A,B=pr0['A'],pr0['B'];fx,fy=pface.BoundBox.XLength,pface.BoundBox.YLength
# analytic corner outline (corner03 profile with seam=0, long-flange tip end moved +SL): every point must lie on the flat outer wire
exp_pts=[]
for mx in (False,True):
    for my in (False,True):
        tr=lambda p:(fx-p[0] if mx else p[0], fy-p[1] if my else p[1])
        exp_pts+= [tr(p) for p in ((B-ro+SL,0),(B-ro+SL,A),(B,B),(A,B-ri),(0,B-ri))]
ow=pface.OuterWire
corner_dev=max(ow.distToShape(Part.Vertex(V(x,y,0)))[0] for x,y in exp_pts)
assert corner_dev<1e-6,corner_dev
export(flat,out/'LID_UNFOLD.step',1)
r,idx,diff,cutchk=write_dxf_ext(out/'LID.dxf',pface);write_bend(out/'LID_BEND.dxf',lines)
f2,l2,_,_,_=unfold('LIDeps',LID_eps,4,True);fe=plane_face(f2)
xd=abs(pface.cut(fe).Area);xd2=abs(fe.cut(pface).Area)
flats['LID']=pface
rep['parts']['LID'].update(flat_size=[fx,fy],flat_area=pface.Area,
  profile03={'A':A,'B':B,'BA':BA,'seam':SEAM,'long_tip_setback':SL,'corner_outline_flat_bl':[[B-ro+SL,0],[B-ro+SL,A],[B,B],[A,B-ri],[0,B-ri]],'corner_outline_max_dev_mm':corner_dev},
  dxf_native_area_diff=diff,bend_records=recs,thickness=tm,dxf_sha256=sha(out/'LID.dxf'),
  dxf_circles=sorted(round(2*x['radius'],4) for x in r if x['type']=='CIRCLE'),dxf_arcs=sum(x['type']=='ARC' for x in r),dxf_cutout_loop_checks=cutchk,
  eps_variant_crosscheck={'eps_mm':EPS,'t7u_minus_eps_area':xd,'eps_minus_t7u_area':xd2,'expected_t7u_minus_eps':4*(A*EPS+0.5*EPS*BA)},
  bend_lines=[[[p.x,p.y] for p in e.discretize(Number=2)] for e in lines.Edges],flat_map=[comb.A11,comb.A12,comb.A14,comb.A21,comb.A22,comb.A24])
assert abs(xd-4*(A*EPS+0.5*EPS*BA))<1e-5 and xd2<1e-6,(xd,xd2)
# O16 roof holes in flat
c16=[x for x in r if x['type']=='CIRCLE' and abs(2*x['radius']-RD)<1e-6]
assert len(c16)==2,len(c16)
rep['parts']['LID']['flat_roof_holes_16']=sorted([[x['center'][0],x['center'][1]] for x in c16],key=lambda q:(q[0],q[1]))
for n in ('U','L','LID'):
    bl=rep['parts'][n]['bend_lines']
F.closeDocument(doc.Name)
# projections & meshes
proj={}
for name,shape in {**parts,'ASSEMBLY':asm,'EXPLODED':exc}.items():
    proj[name]={}
    for label,dvec in (('front',V(0,-1,0)),('right',V(1,0,0)),('top',V(0,0,1))):
        g_=TechDraw.projectEx(shape,dvec);pol=[]
        for item in g_[:5]:
            for e in item.Edges:
                pol.append([[p.x,p.y] for p in e.discretize(Deflection=.05)])
        proj[name][label]=pol
json.dump(proj,open(out/'projections.json','w'))
mesh={}
for name,shape in {**parts}.items():
    v,f=shape.tessellate(.2);mesh[name]={'v':[list(x) for x in v],'f':[list(x) for x in f]}
json.dump({'parts':mesh,'shifts':shifts},open(out/'mesh.json','w'))
# flat outlines for drawings
fl={}
for n,fc in flats.items():
    fl[n]={'wires':[[[p.x,p.y] for p in w.discretize(Deflection=.02)] for w in fc.Wires],'bbox':[fc.BoundBox.XMin,fc.BoundBox.YMin,fc.BoundBox.XMax,fc.BoundBox.YMax]}
json.dump(fl,open(out/'flats.json','w'))
json.dump(rep,open(out/'E_main_report.json','w'),indent=1,ensure_ascii=False)
print(json.dumps({k:rep[k] for k in ('lid','assembly','intersections','L_covers_U_measured')},indent=1,ensure_ascii=False))
for n in parts:print(n,rep['parts'][n]['bbox'],rep['parts'][n]['volume_mm3'],rep['parts'][n].get('flat_size'),rep['parts'][n].get('dxf_circles'))
print('LID eps',rep['parts']['LID']['eps_variant_crosscheck'],rep['parts']['LID']['flat_roof_holes_16'])
