#!/usr/bin/env python3
"""Independent read-side verification. Does not import CAD/DXF writers or trust stored area differences."""
import argparse,json,math,hashlib,sys,itertools
from pathlib import Path

def inspect(root,manifest):
 import FreeCAD as F,Part,SheetMetalNewUnfolder as NU
 from measured_unfold import get_unfold
 V=F.Vector;tol=1e-5;root=Path(root).resolve();errors=[];checks=[]
 def path(name):
  p=(root/name).resolve()
  if not p.is_relative_to(root):raise ValueError('Readback path escapes audit root')
  return p
 def bop(shape):
  try:shape.check(True);return True
  except Exception:return False
 def extent(shape):return [getattr(shape.BoundBox,k) for k in ['XMin','YMin','ZMin','XMax','YMax','ZMax']]
 def skin_t(shape):
  candidates=[];planes=[f for f in shape.Faces if isinstance(f.Surface,Part.Plane)]
  for a,b in itertools.combinations(planes,2):
   n=a.normalAt(0,0)
   if n.dot(b.normalAt(0,0))>-.999999:continue
   distance=(a.Surface.Position-b.Surface.Position).dot(n)
   if abs(distance)<1e-7:continue
   shifted=b.copy();shifted.translate(n*distance)
   if a.common(shifted).Area>=.9*max(a.Area,b.Area):candidates.append(abs(distance))
  if not candidates:raise ValueError('No independent opposing-skin thickness evidence')
  return min(candidates)
 def flatten(shape,normal):
  rotated=shape.transformed(F.Placement(V(),F.Rotation(normal,V(0,0,1))).toMatrix());bb=rotated.BoundBox;rotated.translate(V(-bb.XMin,-bb.YMin,-bb.ZMax));return rotated
 def surface(shape):
  faces=[f for f in shape.Faces if isinstance(f.Surface,Part.Plane) and f.normalAt(0,0).z>.999999]
  f=max(faces,key=lambda x:x.Area).copy();f.translate(V(0,0,-f.CenterOfMass.z));return f
 def difference(a,b):return abs(a.cut(b).Area)+abs(b.cut(a).Area)
 def physical_holes(shape,t):
  groups={}
  for f in shape.Faces:
   if not isinstance(f.Surface,Part.Cylinder) or f.Orientation!='Reversed':continue
   s=f.Surface;u0,u1,v0,v1=f.ParameterRange
   if abs(abs(v1-v0)-t)>tol:continue
   axis=s.Axis
   if next((v for v in axis if abs(v)>1e-7),1)<0:axis=-axis
   middle=s.Center+s.Axis*((v0+v1)/2);key=tuple(round(v,6) for v in [s.Radius,*axis,*middle]);g=groups.setdefault(key,{'D':2*s.Radius,'center':list(middle),'axis':list(axis),'angle':0});g['angle']+=abs(u1-u0)
  return [g for g in groups.values() if abs(g['angle']-2*math.pi)<tol]
 def dxf_face(filename):
  # Separate ASCII reader and wire grouping from cad_dxf/cut_dxf. No reported loop indices used.
  lines=path(filename).read_text(encoding='ascii').splitlines()
  if len(lines)%2:raise ValueError('Independent DXF reader: odd group-code lines')
  pairs=[(int(lines[i].strip()),lines[i+1].strip()) for i in range(0,len(lines),2)]
  if not any(pairs[i]==(9,'$INSUNITS') and pairs[i+1]==(70,'4') for i in range(len(pairs)-1)):raise ValueError('Independent DXF reader: mm units missing')
  section=None;entities=[];current=None
  for k,v in pairs:
   if k==2 and v=='ENTITIES':section='ENTITIES';continue
   if section!='ENTITIES':continue
   if k==0:
    if current:entities.append(current)
    current=None
    if v=='ENDSEC':break
    if v not in ['LINE','ARC','CIRCLE']:raise ValueError('Independent DXF unsupported entity '+v)
    current={'kind':v}
   elif current is not None:current[k]=v
  edges=[]
  for e in entities:
   if e.get(8)!='CUT':raise ValueError('Independent DXF reader: layer is not CUT')
   for k,default in [(30,0),(31,0),(39,0),(210,0),(220,0),(230,1)]:
    value=float(e.get(k,default))
    if not math.isfinite(value) or abs(value-default)>1e-9:raise ValueError('Independent DXF not planar default-OCS geometry')
   numbers={k:float(e[k]) for k in [10,20,11,21,40,50,51] if k in e}
   if any(not math.isfinite(v) for v in numbers.values()):raise ValueError('Nonfinite DXF geometry')
   a=V(numbers[10],numbers[20],0)
   if e['kind']=='LINE':edge=Part.makeLine(a,V(numbers[11],numbers[21],0))
   else:
    radius=numbers[40]
    if radius<=0:raise ValueError('Invalid independent DXF radius')
    if e['kind']=='CIRCLE':edge=Part.makeCircle(radius,a)
    else:
     start=math.radians(numbers[50]);sweep=math.radians((numbers[51]-numbers[50])%360)
     if sweep<1e-9:raise ValueError('Zero DXF arc sweep')
     point=lambda fraction:a+V(radius*math.cos(start+sweep*fraction),radius*math.sin(start+sweep*fraction),0)
     edge=Part.Arc(point(0),point(.5),point(1)).toShape()
   edges.append(edge)
  faces=[]
  for group in Part.sortEdges(edges):
   wire=Part.Wire(group)
   if not wire.isClosed():raise ValueError('Independent DXF wire open')
   face=Part.Face(wire);face.check(True);faces.append(face)
  if not faces:raise ValueError('Independent DXF empty')
  faces.sort(key=lambda f:f.Area,reverse=True);outer=faces[0];cut=outer
  for face in faces[1:]:
   if face.cut(outer).Area>tol or any(face.common(other).Area>tol for other in faces[1:faces.index(face)]):raise ValueError('DXF holes outside/overlapping')
   cut=cut.cut(face)
  cut.check(True)
  return cut,len(faces)-1
 report=json.loads(path(manifest['source_report']).read_text());source=Part.read(str(path(manifest['source_copy'])));cfg=report['config']
 if len(source.Solids)!=len(report['parts']):raise ValueError('Actual source solid count differs from scope')
 doc=F.newDocument('IndependentSourceArtifactReadback')
 try:
  for index,(original,p) in enumerate(zip(source.Solids,report['parts']),1):
   name='SOLID_%02d'%index
   try:
    if p['id']!=name:raise ValueError('Actual source part identity/order changed')
    valid=original.isValid();strict=bop(original)
    if p['isValid'] is not valid or p['BOP']['ok'] is not strict:raise ValueError('Source validity/BOP declaration differs from actual STEP')
    formed=Part.read(str(path('cad/'+p['formed_step'])))
    if len(formed.Solids)!=1 or formed.isValid()!=valid or bop(formed)!=strict:raise ValueError('Formed STEP validity differs from source')
    volume_difference=abs(original.Volume-formed.Volume);symmetric_volume=abs(original.cut(formed).Volume)+abs(formed.cut(original).Volume)
    if volume_difference>tol or symmetric_volume>tol or max(abs(a-b) for a,b in zip(extent(original),extent(formed)))>tol:raise ValueError('Actual formed STEP differs from original source solid')
    t=skin_t(original)
    if abs(t-p['measured_planar_t_mm'])>tol:raise ValueError('Reported thickness differs from actual source skins')
    holes=physical_holes(original,t)
    if len(holes)!=len(p['holes']):raise ValueError('Source physical hole coverage differs')
    for h in holes:
     matching=[r for r in p['holes'] if abs(r['D_mm']-h['D'])<=tol and (V(*r['center_mm'])-V(*h['center'])).Length<=tol and V(*r['axis']).cross(V(*h['axis'])).Length<=1e-6]
     if len(matching)!=1:raise ValueError('Reported source hole differs from actual source STEP')
    roots=sorted([i for i,f in enumerate(original.Faces) if isinstance(f.Surface,Part.Plane)],key=lambda i:original.Faces[i].Area,reverse=True)
    rigid=flatten(original,original.Faces[roots[0]].normalAt(0,0));is_planar=abs(rigid.BoundBox.ZLength-t)<=tol and abs(rigid.Volume/surface(rigid).Area-t)<=tol
    ob=doc.addObject('Part::Feature',name);ob.Shape=original;u=p['unfold'];selected=u.get('selected_attempt');K=cfg.get('K_ANSI') if cfg.get('K_ANSI') is not None else cfg.get('diagnostic_K_ANSI')
    def fresh(root_face):
     if is_planar:return rigid,0,None
     if K is None:raise ValueError('No compensation input for actual source re-unfold')
     if not 1<=root_face<=len(original.Faces) or not isinstance(original.Faces[root_face-1].Surface,Part.Plane):raise ValueError('Invalid actual root face')
     from native_direction_readback import unfold_readback
     expected_records=None
     if selected is not None and report.get('version') in ['2.6.0-R05','2.6.1-R06']:
      expected_records=u['attempts'][selected].get('bend_records')
      if expected_records is None:raise ValueError('NATIVE_DIRECTION: native direction claims absent')
     (_,flat,folds,normal,bends),measurement,direction_proof=unfold_readback(NU,ob,root_face,t,K,expected_records)
     return flatten(flat,normal),len(bends),direction_proof
    if selected is None:
     if is_planar and strict:raise ValueError('Supported planar source has no accepted artifact')
     if K is not None and (strict or cfg.get('diagnose_invalid')):
      if not u.get('attempts'):raise ValueError('Opted-in unfold has no actual attempted-root evidence')
      failed=[]
      for a in u['attempts']:
       try:flat,n,_=fresh(a['root_face']);flat.check(True)
       except Exception as ex:failed.append(str(ex));continue
       raise ValueError('Source freshly unfolds but accepted flat artifacts are absent')
      checks.append({'part':name,'source_BOP':strict,'actual_t_mm':t,'hole_count':len(holes),'fresh_native_failed_roots':len(failed),'status':'BLOCKED verified from actual attempts'})
     else:checks.append({'part':name,'source_BOP':strict,'actual_t_mm':t,'hole_count':len(holes),'status':'BLOCKED: actual invalid source or missing compensation'})
     continue
    if type(selected) is not int or selected<0 or selected>=len(u['attempts']):raise ValueError('Invalid selected actual-flat attempt index')
    a=u['attempts'][selected]
    if not strict and not cfg.get('diagnose_invalid'):raise ValueError('Invalid source flat was not opted into diagnostic scope')
    if not is_planar and K is None:raise ValueError('Bent flat lacks compensation evidence')
    fresh_shape,native_bends,direction_proof=fresh(a['root_face']);fresh_shape.check(True)
    if not fresh_shape.isValid() or len(fresh_shape.Solids)!=1 or abs(fresh_shape.BoundBox.ZLength-t)>tol:raise ValueError('Fresh native flat invalid or wrong thickness')
    if native_bends!=len(p['bends']) or native_bends!=a['actual_bends']:raise ValueError('Measured fresh bend count differs from report')
    flat=Part.read(str(path('cad/'+a['flat_step'])));flat.check(True)
    if len(flat.Solids)!=1 or not flat.isValid() or abs(flat.BoundBox.ZLength-t)>tol:raise ValueError('Actual unfold STEP invalid or wrong thickness')
    actual=surface(flat);native=surface(fresh_shape);dxf,flat_holes=dxf_face('cad/'+a['dxf']);flat_delta=difference(actual,native);dxf_delta=difference(actual,dxf);source_delta=difference(native,dxf)
    if max(flat_delta,dxf_delta,source_delta)>tol:raise ValueError('Actual source/unfold STEP/DXF geometric difference mm2: '+str({'source_vs_STEP':flat_delta,'STEP_vs_DXF':dxf_delta,'source_vs_DXF':source_delta}))
    if flat_holes!=len(holes) or a['flat_hole_count']!=len(holes):raise ValueError('Actual flat/source hole coverage differs')
    if abs(a['flat_thickness_mm']-flat.BoundBox.ZLength)>tol or max(abs(a['flat_size_mm'][k]-v) for k,v in enumerate([actual.BoundBox.XLength,actual.BoundBox.YLength]))>tol:raise ValueError('Flat numerical dimensions differ from actual STEP')
    diagnostic=(not strict) or (not is_planar and cfg.get('K_ANSI') is None)
    expected='DIAGNOSTIC_ONLY' if diagnostic else 'GEOMETRY_CHECKED_WITH_HOLD'
    if u['status']!=expected or u['diagnostic_only'] is not diagnostic:raise ValueError('Artifact status disagrees with actual source and compensation scope')
    checks.append({'part':name,'source_BOP':strict,'actual_t_mm':t,'hole_count':len(holes),'fresh_native_bends':native_bends,'actual_native_direction_readback':direction_proof,'actual_source_vs_unfold_STEP_area_mm2':flat_delta,'actual_unfold_STEP_vs_DXF_area_mm2':dxf_delta,'actual_source_vs_DXF_area_mm2':source_delta,'reported_area_values_not_used':True,'status':expected})
   except Exception as ex:errors.append(name+': '+str(ex))
 finally:F.closeDocument(doc.Name)
 return {'ok':not errors,'errors':errors,'CAD_executed':True,'actual_source_read':True,'source_sha256':hashlib.sha256(path(manifest['source_copy']).read_bytes()).hexdigest(),'checks':checks,'numeric_tolerance_mm':tol,'numeric_area_tolerance_mm2':tol,'production_release':False}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--manifest',required=True);p.add_argument('--output',required=True);p.add_argument('--module-path',action='append',default=[]);a=p.parse_args()
 for name in a.module_path:sys.path.insert(0,name)
 try:r=inspect(a.root,json.loads(Path(a.manifest).read_text()))
 except Exception as ex:r={'ok':False,'errors':[str(ex)],'CAD_executed':False,'production_release':False}
 Path(a.output).write_text(json.dumps(r,indent=2));raise SystemExit(0 if r['ok'] else 2)
