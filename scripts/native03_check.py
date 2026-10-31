#!/usr/bin/env python3
"""Actual read-only FreeCAD/SheetMetal re-unfold + STEP/DXF comparison. CAD modules supplied by host.
Run inside a configured FreeCAD Python environment; missing/incompatible modules BLOCK, never pass.
This creates an in-memory document only and never saves or edits the supplied CAD files.
"""
import json,math,hashlib,argparse,sys
from pathlib import Path
from corner03 import spec,check_dxf
from create_intake import apply_lid_defaults

def require(condition,message):
 if not condition:raise ValueError(message)

def verify(doc,formed_path,unfold_path,dxf_path,body_path=None,execution_state=None):
 if not body_path:raise ValueError('body STEP is required: 03 validation includes root interference and roof seating')
 import FreeCAD as F,Part,SheetMetalNewUnfolder as NU
 if execution_state is not None:execution_state.update(CAD_executed=False,stage='parameters')
 s=spec(doc);V=F.Vector;tol=1e-5;area_tol=1e-5
 formed=Part.read(str(formed_path));
 if execution_state is not None:execution_state.update(CAD_executed=True,stage='formed_STEP_BOP')
 provided=Part.read(str(unfold_path));require(formed.isValid() and len(formed.Solids)==1,'formed STEP must be one valid solid');require(provided.isValid(),'true-unfold STEP invalid')
 formed.check(True);axis='XYZ'.index(doc['requirements']['height_axis']['value']);dim='XYZ'[axis];height=max(getattr(f.CenterOfGravity,dim.lower()) for f in formed.Faces if f.Surface.TypeId=='Part::GeomPlane' and abs(list(f.normalAt(0,0))[axis])>.999)
 candidates=[i for i,f in enumerate(formed.Faces) if f.Surface.TypeId=='Part::GeomPlane' and abs(list(f.CenterOfGravity)[axis]-height)<tol and abs(list(f.normalAt(0,0))[axis])>.999];root=max(candidates,key=lambda i:formed.Faces[i].Area)
 work=F.newDocument('Skill03Readback')
 try:
  ob=work.addObject('Part::Feature','ReadOnlyCopy');ob.Shape=formed
  from measured_unfold import get_unfold
  (_,flat,bl,normal,bends),thickness_measurement=get_unfold(NU.BendAllowanceCalculator.from_single_value(s['K_ANSI'],'ansi'),ob,'Face'+str(root+1),s['t']);require(len(bends)==4,'03 four-bend adapter requires actual4 bends')
  mat=F.Placement(V(),F.Rotation(normal,V(0,0,1))).toMatrix();flat=flat.transformed(mat)
  def planar(shape):
   return max([f for f in shape.Faces if f.Surface.TypeId=='Part::GeomPlane' and abs(abs(f.normalAt(0,0).z)-1)<1e-6],key=lambda f:f.Area)
  def orientations(shape):
   for angle in [0,90,180,270]:
    sh=shape.copy();sh.rotate(V(),V(0,0,1),angle);face=planar(sh).copy();bb=face.BoundBox;face.translate(V(-bb.XMin,-bb.YMin,-bb.ZMin));yield face
  # Count/check03 on freshly unfolded native outer edge geometry, not a claimed label.
  actual=None
  from corner03 import expected_segments,same_segment
  expect=expected_segments(s)
  for face in orientations(flat):
   bb=face.BoundBox
   if abs(bb.XLength-s['flat_size'][0])>tol or abs(bb.YLength-s['flat_size'][1])>tol:continue
   lines=[]
   for edge in face.OuterWire.Edges:
    if edge.Curve.TypeId=='Part::GeomLine':lines.append(([edge.Vertexes[0].Point.x,edge.Vertexes[0].Point.y],[edge.Vertexes[-1].Point.x,edge.Vertexes[-1].Point.y]))
   diag=[(a,b) for a,b in lines if abs(a[0]-b[0])>tol and abs(a[1]-b[1])>tol]
   if len(diag)==8 and all(any(same_segment(a,b,u,v,tol) for u,v in diag) for a,b in expect):actual=face;break
  require(actual is not None,'fresh native unfold is not the computed03 sloped profile (20straight0sloped is rejected)')
  delta=min(actual.cut(f).Area+f.cut(actual).Area for f in orientations(provided));require(delta<=area_tol,'provided true-unfold STEP differs from fresh native unfold')
  read=check_dxf(dxf_path,s,tol);ents=read['entities'];edges=[];holes=[]
  for e in ents:
   if e['type']=='LINE':edges.append(Part.makeLine(V(float(e[10]),float(e[20]),0),V(float(e[11]),float(e[21]),0)))
   elif e['type']=='ARC':
    center=V(float(e[10]),float(e[20]),0);rad=float(e[40]);a=math.radians(float(e[50]));sweep=(math.radians(float(e[51]))-a)%(2*math.pi);pt=lambda q:center+V(rad*math.cos(a+q*sweep),rad*math.sin(a+q*sweep),0);edges.append(Part.Arc(pt(0),pt(.5),pt(1)).toShape())
   else:holes.append(Part.Face(Part.Wire([Part.makeCircle(float(e[40]),V(float(e[10]),float(e[20]),0))])))
  wire=Part.Wire(Part.__sortEdges__(edges));require(wire.isClosed(),'actual DXF outer not closed');cut=Part.Face(wire)
  for hole in holes:cut=cut.cut(hole)
  dxf_delta=actual.cut(cut).Area+cut.cut(actual).Area;require(dxf_delta<=area_tol,'DXF area/holes differ from actual native unfolded face')
  root_volume=None;measured_q=None;holds=[]
  if body_path:
   body=Part.read(str(body_path));require(body.isValid(),'body STEP invalid');root_volume=abs(body.common(formed).Volume);fresh_root_volume=root_volume;measured_q=getattr(formed.BoundBox,dim+'Max')-s['t']-getattr(body.BoundBox,dim+'Max')
   if doc['project']['revision']['value'] in ['v2.6.1-R06','v2.7.0-R07','v2.7.1-R08','v2.7.2-R09','v2.7.3-R10','v2.8.0-R11','v2.8.1-R12']:
    from interference_volume import require_same_measurement
    authority=doc['lid']['root_overlap_volume']['value'];require_same_measurement(authority,root_volume);root_volume=authority
   if s['q'] is None:holds.append('q requirement not specified; actual CAD seating measurement is not an automatic approval')
   elif abs(measured_q-s['q'])>tol:raise ValueError('actual roof q differs from specified q')
   from site_fit import acceptance_from_project,check_actual_overlap,VOLUME_TOL_MM3
   acceptance=acceptance_from_project(doc)
   intersection=body.common(formed)
   disposition=check_actual_overlap(root_volume,acceptance,getattr(intersection.BoundBox,dim+'Min') if root_volume>VOLUME_TOL_MM3 else 0,height-s['t']-s['Ri'])
   if root_volume>VOLUME_TOL_MM3:holds.append('AUTHORIZED_SITE_FIT_TRIAL_REQUIRED: positive interference retained; no geometric elimination or trial confirmation')
  else:holds.append('body STEP absent: root/body interference and seating not checked')
  sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
  result={'ok':True,'CAD_executed':True,'method':'actual FreeCAD SheetMetal fresh unfold and geometric area difference','FreeCAD_version':F.Version()[:3],'parameter_hash':hashlib.sha256(json.dumps(apply_lid_defaults(doc),ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest(),'input_sha256':{'formed_step':sha(formed_path),'unfold_step':sha(unfold_path),'dxf':sha(dxf_path)},'actual_bends':4,'native_sloped_edges':8,'DXF_sloped_edges':8,'fresh_vs_provided_unfold_area_mm2':delta,'native_vs_DXF_area_mm2':dxf_delta,'root_overlap_volume_mm3':root_volume,'actual_roof_q_mm':measured_q,'numeric_tolerance_mm':tol,'numeric_area_tolerance_mm2':area_tol,'holds':holds,'production_release':False}
  result['thickness_measurement']=thickness_measurement
  if doc['project']['revision']['value'] in ['v2.6.1-R06','v2.7.0-R07','v2.7.1-R08','v2.7.2-R09','v2.7.3-R10','v2.8.0-R11','v2.8.1-R12']:
   from interference_volume import measurement
   result.update(root_interference_measurement=measurement(root_volume),fresh_body_lid_common_volume_mm3=fresh_root_volume)
  result.update(assembly_interference_free=root_volume<=VOLUME_TOL_MM3,fit_disposition=disposition,site_fit_acceptance=acceptance,geometry_interference_eliminated=False,trial_assembly_confirmed=False)
  if body_path:result['input_sha256']['body_step']=sha(body_path)
  return result
 finally:F.closeDocument(work.Name)

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('project');p.add_argument('--formed',required=True);p.add_argument('--unfold',required=True);p.add_argument('--dxf',required=True);p.add_argument('--body',required=True);p.add_argument('--output');p.add_argument('--module-path',action='append',default=[]);a=p.parse_args();sys.path.extend(a.module_path)
 from safe_io import guard_outputs
 try:guard_outputs([a.project,a.formed,a.unfold,a.dxf,a.body],[a.output])
 except ValueError as ex:p.error(str(ex))
 execution_state={'CAD_executed':False,'stage':'dependency_or_input'}
 try:result=verify(json.loads(Path(a.project).read_text()),a.formed,a.unfold,a.dxf,a.body,execution_state)
 except Exception as ex:result={'ok':False,**execution_state,'CAD_completed':False,'error_type':type(ex).__name__,'error':str(ex),'production_release':False}
 text=json.dumps(result,ensure_ascii=False,indent=2);print(text)
 if a.output:Path(a.output).write_text(text+'\n')
 raise SystemExit(0 if result['ok'] else 2)
