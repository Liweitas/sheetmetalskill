"""Native golden-pipeline adapter: open U + two outer end plates, no lid, no holes."""
from pathlib import Path
import sys,os,json,math,itertools,hashlib
SK=Path(__file__).resolve().parents[2];sys.path.insert(0,str(SK/'scripts'));sys.path.insert(0,os.environ['SHEETMETAL_PATH'])
import FreeCAD as F,Part,TechDraw,SheetMetalNewUnfolder as NU
from measured_unfold import get_unfold
from formed_isometric import track_bends,records
from cad_dxf import write_dxf
J=json.loads(Path(os.environ['SM_JOB']).read_text());out=Path(sys.argv[1]);out.mkdir(parents=True,exist_ok=False)
assert J['lid_required'] is False and not any(J.get(k) for k in ['holes','handles','lid_ports','panel_holes','top_fixings'])
L,W,H,t,ri,K=[J[k] for k in ['L','W','H','t','Ri','K']];ro=ri+t;V=F.Vector;s2=1/math.sqrt(2)
assert min(L,W,H)>2*ro and max(L,W)>=H and L>2*t
bbox=lambda s:[getattr(s.BoundBox,k) for k in ['XMin','YMin','ZMin','XMax','YMax','ZMax']]
def face(pts,arcs):return Part.Face(Part.Wire([Part.Arc(V(*p),V(*arcs[i]),V(*pts[(i+1)%len(pts)])).toShape() if i in arcs else Part.makeLine(V(*p),V(*pts[(i+1)%len(pts)])) for i,p in enumerate(pts)]))
# Identical U/end construction to build.py, with Hb=H and every optional feature absent.
pp=[(0,H),(0,ro),(ro,0),(W-ro,0),(W,ro),(W,H),(W-t,H),(W-t,ro),(W-ro,t),(ro,t),(t,ro),(t,H)]
aa={1:(ro-ro*s2,ro-ro*s2),3:(W-ro+ro*s2,ro-ro*s2),7:(W-ro+ri*s2,ro-ri*s2),9:(ro-ri*s2,ro-ri*s2)}
U=face([(t,y,z) for y,z in pp],{i:(t,y,z) for i,(y,z) in aa.items()}).extrude(V(L-2*t,0,0)).removeSplitter()
pp=[(0,0,H),(0,0,ro),(0,ro,0),(0,W-ro,0),(0,W,ro),(0,W,H)];aa={1:(0,ro-ro*s2,ro-ro*s2),3:(0,W-ro+ro*s2,ro-ro*s2)}
EL=face(pp,aa).extrude(V(t,0,0));ER=EL.mirror(V(L/2,0,0),V(1,0,0));P={'U':U,'END_L':EL,'END_R':ER}
def export(s,path,count):
 s.exportStep(str(path));r=Part.read(str(path));assert r.isValid() and len(r.Solids)==count and abs(r.Volume-s.Volume)<max(.01,s.Volume*1e-7);return r
P={n:export(s,out/(n+'.step'),1) for n,s in P.items()}
rep={'version':J['release'],'lid_required':False,'structure':'u_external_ends_body_only','params':{'L':L,'W':W,'H':H,'Hb':H,'t':t,'Ri':ri,'Ro':ro,'K':K,'BA':math.pi/2*(ri+K*t),'BD':2*ro-math.pi/2*(ri+K*t),'lid':None,'q':None,'g':None,'skirt':None},'holes':[],'handle_holes':[],'parts':{}}
asm=export(Part.makeCompound(list(P.values())),out/'ASSEMBLY.step',3);b=asm.BoundBox;assert all(abs(v-e)<1e-6 for v,e in zip([b.XLength,b.YLength,b.ZLength],[L,W,H]))
shifts={'U':[0,0,0],'END_L':[-50,0,0],'END_R':[50,0,0]};ex=[]
for n,s in P.items():c=s.copy();c.translate(V(*shifts[n]));ex.append(c)
export(Part.makeCompound(ex),out/'EXPLODED.step',3)
rep['assembly']={'bbox':bbox(asm),'actual_outer_mm':[b.XLength,b.YLength,b.ZLength],'exploded_shifts':shifts}
rep['intersections_mm3']={a+'/'+b:P[a].common(P[b]).Volume for a,b in itertools.combinations(P,2)};assert max(rep['intersections_mm3'].values())<1e-6
# The centre opening is deliberately free; a lid or a spurious solid would intersect this probe.
probe=Part.makeBox(L-2*t-4,W-2*t-4,2,V(t+2,t+2,H-1));assert asm.common(probe).Volume<1e-6
# End plates touch and fully cover the U section, with no 0.2mm setback.
rep['end_cover']={}
for n,x in [('END_L',t),('END_R',L-t)]:
 uf=max([f for f in U.Faces if isinstance(f.Surface,Part.Plane) and abs(f.CenterOfMass.x-x)<1e-6 and abs(abs(f.normalAt(0,0).x)-1)<1e-6],key=lambda f:f.Area)
 ef=max([f for f in P[n].Faces if isinstance(f.Surface,Part.Plane) and abs(f.CenterOfMass.x-x)<1e-6 and abs(abs(f.normalAt(0,0).x)-1)<1e-6],key=lambda f:f.Area)
 uncovered=uf.cut(Part.Face(ef.OuterWire)).Area;assert uncovered<1e-6
 rep['end_cover'][n]={'uncovered_U_profile_area_mm2':uncovered,'axial_gap_mm':P[n].distToShape(U)[0]}
 assert P[n].distToShape(U)[0]<1e-6
# Only the U bends; ends are genuine rigid exterior-face transforms, determinant +1.
doc=F.newDocument('OpenBox');ob=doc.addObject('Part::Feature','U');ob.Shape=P['U'];root=max([i for i,f in enumerate(P['U'].Faces) if isinstance(f.Surface,Part.Plane) and f.normalAt(0,0).z<-.999 and abs(f.CenterOfMass.z)<1e-6],key=lambda i:P['U'].Faces[i].Area)
with track_bends(NU):(_,flat,lines,normal,bends),tm=get_unfold(NU.BendAllowanceCalculator.from_single_value(K,'ansi'),ob,'Face'+str(root+1),t)
assert len(bends)==2
rot=F.Placement(V(),F.Rotation(normal,V(0,0,1))).toMatrix();flat=flat.transformed(rot);lines=lines.transformed(rot);bb=flat.BoundBox;d=V(-bb.XMin,-bb.YMin,-bb.ZMax);flat.translate(d);lines.translate(d);matrix=F.Placement(d,F.Rotation()).toMatrix().multiply(rot)
bl=[[[q.x,q.y] for q in edge.discretize(Number=2)] for edge in lines.Edges];recs=records(bends,matrix,root+1,normal,bl)
rig={'END_L':F.Matrix(0,-1,0,W,0,0,1,0,-1,0,0,0,0,0,0,1),'END_R':F.Matrix(0,1,0,0,0,0,1,0,1,0,0,-L,0,0,0,1)}
flats={};mesh={};proj={};audit=[]
for n,s in P.items():
 fl=flat if n=='U' else s.transformed(rig[n]);rr=recs if n=='U' else [];th=tm if n=='U' else {'method':'rigid exterior-face +1 determinant transform','measured_t_mm':t}
 if n!='U':assert abs(rig[n].determinant()-1)<1e-8 and abs(fl.Volume-s.Volume)<1e-6
 pf=max([f for f in fl.Faces if isinstance(f.Surface,Part.Plane) and abs(f.CenterOfMass.z)<1e-6 and abs(abs(f.normalAt(0,0).z)-1)<1e-6],key=lambda f:f.Area)
 assert len(pf.Wires)==1 and abs(fl.Volume/pf.Area-t)<1e-5 and abs(fl.BoundBox.ZLength-t)<1e-6
 fl=export(fl,out/(n+'_UNFOLD.step'),1)
 try:entities,idx,diff=write_dxf(out/(n+'_CUT_raw.dxf'),pf)
 except ValueError:
  # Same documented tangent-endpoint merge used by the existing golden build.py.
  import dxf_topology as DT
  old=DT.intersections
  def merged(e,f):
   pts=old(e,f);res=[]
   for q in pts:
    if not any(math.dist(q,v)<1e-6 for v in res):res.append(q)
   ends=[a for a in DT.ends(e) for b in DT.ends(f) if DT.dist(a,b)<1e-6]
   return [ends[0] if ends and min(math.dist(q,v) for v in ends)<1e-6 else q for q in res]
  DT.intersections=merged
  try:entities,idx,diff=write_dxf(out/(n+'_CUT_raw.dxf'),pf)
  finally:DT.intersections=old
 assert not any(q['type']=='CIRCLE' for q in entities) and len(idx)==1 and diff<1e-5
 size=[pf.BoundBox.XLength,pf.BoundBox.YLength]
 if n=='U':assert abs(size[0]-(L-2*t))<1e-5 and abs(size[1]-(W+2*H-2*rep['params']['BD']))<1e-5
 else:assert abs(size[0]-W)<1e-5 and abs(size[1]-H)<1e-5
 rep['parts'][n]={'bbox':bbox(s),'size':[s.BoundBox.XLength,s.BoundBox.YLength,s.BoundBox.ZLength],'volume_mm3':s.Volume,'flat_size':size,'flat_area':pf.Area,'flat_volume_mm3':fl.Volume,'formed_flat_volume_ratio':fl.Volume/s.Volume,'thickness':th,'bend_records':rr,'flat_circles':[],'bend_lines':bl if n=='U' else [],'dxf_native_area_diff':diff}
 assert .95<fl.Volume/s.Volume<1.05
 flats[n]={'wires':[[[v.x,v.y] for v in wire.discretize(Deflection=.03)] for wire in pf.Wires]}
 verts,tris=s.tessellate(.2);mesh[n]={'v':[list(v) for v in verts],'f':[list(q) for q in tris]}
 for f in s.Faces:
  if isinstance(f.Surface,Part.Plane):assert len(f.Wires)==1,'Unexpected hole in formed sheet'
 audit.append({'part':n,'native_bends':len(rr),'inner_wires':0,'flat_Z_thickness':fl.BoundBox.ZLength,'native_CUT_area_difference_mm2':diff,'valid':True})
F.closeDocument(doc.Name)
for n,s in {**P,'ASSEMBLY':asm}.items():
 proj[n]={}
 for label,dvec in [('front',V(0,-1,0)),('right',V(1,0,0)),('left',V(-1,0,0)),('top',V(0,0,1))]:
  arr=TechDraw.projectEx(s,dvec);pol=[]
  for group in arr[:5]:
   for edge in group.Edges:pol.append([[v.x,v.y] for v in edge.discretize(Deflection=.05)])
  proj[n][label]={'vis':pol,'hid':[]}
rep['weld_candidate']={'method':'end plates externally cover U; weld contacts, beads/process unmodelled pending first article','contact_planes_X':[t,L-t],'outer_seam_length_each_mm':2*(H-ro)+(W-2*ro)+math.pi*ro}
seam=[]
for edge in P['U'].Edges:
 if not all(abs(v.Point.x-t)<1e-6 for v in edge.Vertexes):continue
 c=edge.Curve
 is_outer=(isinstance(c,Part.Circle) and abs(c.Radius-ro)<1e-6) or (isinstance(c,Part.Line) and (all(abs(v.Point.y)<1e-6 for v in edge.Vertexes) or all(abs(v.Point.y-W)<1e-6 for v in edge.Vertexes) or all(abs(v.Point.z)<1e-6 for v in edge.Vertexes)))
 if is_outer:seam.append(edge)
assert len(seam)==5 and abs(sum(e.Length for e in seam)-rep['weld_candidate']['outer_seam_length_each_mm'])<1e-5
rep['weld_candidate']['paths_YZ']=[[[v.y,v.z] for v in e.discretize(Deflection=.03)] for e in seam]
for name,data in [('report.json',rep),('flats.json',flats),('projections.json',proj),('mesh.json',{'parts':mesh,'shifts':shifts})]:(out/name).write_text(json.dumps(data,ensure_ascii=False,indent=2))
a={'pass':True,'release':J['release'],'lid_required':False,'holes':0,'main_parts':3,'actual_outer_mm':[b.XLength,b.YLength,b.ZLength],'top_opening_probe_intersection_mm3':0,'body_height_not_reduced':True,'parts':audit,'intersections_mm3':rep['intersections_mm3'],'end_cover':rep['end_cover'],'physical_first_article_verified':False,'production_release':False};(out/'actual_geometry_audit.json').write_text(json.dumps(a,ensure_ascii=False,indent=2));print('PASS no-lid/no-hole native body:',[L,W,H],'3parts;U2bends;ends0')
