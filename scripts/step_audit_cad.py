#!/usr/bin/env python3
"""Read-only imported STEP audit and bounded native unfolding; never redesigns source parts."""
import argparse,collections,hashlib,itertools,json,math,sys,traceback
from pathlib import Path

def main():
 ap=argparse.ArgumentParser();ap.add_argument('source');ap.add_argument('--config',required=True);ap.add_argument('--output',required=True);ap.add_argument('--module-path',action='append',default=[]);a=ap.parse_args()
 for path in a.module_path:sys.path.insert(0,path)
 import FreeCAD as F,Part,TechDraw,SheetMetalNewUnfolder as NU
 from measured_unfold import get_unfold
 from cad_dxf import write_dxf
 V=F.Vector;tol=1e-5;src=Path(a.source);out=Path(a.output);cfg=json.loads(Path(a.config).read_text());out.mkdir(parents=True,exist_ok=False)
 sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
 vec=lambda v:[v.x,v.y,v.z]
 bbox=lambda s:[getattr(s.BoundBox,k) for k in ['XMin','YMin','ZMin','XMax','YMax','ZMax']]
 def bop(s):
  try:s.check(True);return {'ok':True,'error':None}
  except Exception as ex:return {'ok':False,'error':str(ex),'subshape_indices':'not supplied by this API; no localization asserted'}
 def describe(shape):
  x={'isValid':shape.isValid(),'BOP':bop(shape),'solids':len(shape.Solids),'faces':len(shape.Faces),'edges':len(shape.Edges),'vertices':len(shape.Vertexes),'bbox_mm':bbox(shape),'volume_mm3':shape.Volume,'area_mm2':shape.Area,'max_topology_tolerance_mm':shape.getTolerance(1)}
  x['faces_detail']=[];x['planar_skin_pairs']=[];planes=[];cyl=[]
  for i,f in enumerate(shape.Faces,1):
   sf=f.Surface;d={'face':i,'surface_type':sf.TypeId,'area_mm2':f.Area,'center_mm':vec(f.CenterOfMass),'orientation':f.Orientation,'wire_count':len(f.Wires)}
   if isinstance(sf,Part.Plane):d.update(normal=vec(f.normalAt(0,0)),plane_position_mm=vec(sf.Position));planes.append((i,f))
   if isinstance(sf,Part.Cylinder):
    u0,u1,v0,v1=f.ParameterRange;axis=sf.Axis;center=sf.Center;canonical=axis if next((v for v in axis if abs(v)>1e-7),1)>0 else -axis;perp=center-canonical*center.dot(canonical);ends=sorted([(center+axis*v0).dot(canonical),(center+axis*v1).dot(canonical)])
    d.update(radius_mm=sf.Radius,axis=vec(canonical),axis_perpendicular_origin_mm=vec(perp),axial_interval_mm=ends,angle_rad=abs(u1-u0));cyl.append(d)
   x['faces_detail'].append(d)
  for (ia,fa),(ib,fb) in itertools.combinations(planes,2):
   n=fa.normalAt(0,0)
   if n.dot(fb.normalAt(0,0))>-.999999:continue
   signed=(fa.Surface.Position-fb.Surface.Position).dot(n)
   if abs(signed)<1e-7:continue
   moved=fb.copy();moved.translate(n*signed);overlap=fa.common(moved).Area;fraction=overlap/max(fa.Area,fb.Area)
   if fraction>=.9:x['planar_skin_pairs'].append({'faces':[ia,ib],'distance_mm':abs(signed),'overlap_max_fraction':fraction})
  x['planar_skin_pairs'].sort(key=lambda p:p['distance_mm']);t=x['planar_skin_pairs'][0]['distance_mm'] if x['planar_skin_pairs'] else None
  x['measured_planar_t_mm']=t;x['thickness_scope']='candidate opposing skins; bends require independent cylinder agreement, local BSplines are not certified equal thickness'
  bends=[]
  for ca,cb in itertools.combinations(cyl,2):
   if ca['angle_rad']>=2*math.pi-tol or cb['angle_rad']>=2*math.pi-tol:continue
   if (V(*ca['axis']).cross(V(*cb['axis']))).Length>1e-6:continue
   if (V(*ca['axis_perpendicular_origin_mm'])-V(*cb['axis_perpendicular_origin_mm'])).Length>tol:continue
   if max(abs(u-v) for u,v in zip(ca['axial_interval_mm'],cb['axial_interval_mm']))>tol:continue
   if t is None or abs(abs(ca['radius_mm']-cb['radius_mm'])-t)>tol:continue
   angle=min(ca['angle_rad'],cb['angle_rad'])
   if abs(ca['angle_rad']-cb['angle_rad'])>tol or ca['axial_interval_mm'][1]-ca['axial_interval_mm'][0]<=t+tol:continue
   bends.append({'faces':[ca['face'],cb['face']],'Ri_mm':min(ca['radius_mm'],cb['radius_mm']),'Ro_mm':max(ca['radius_mm'],cb['radius_mm']),'angle_deg':math.degrees(angle),'axis':ca['axis'],'axis_perpendicular_origin_mm':ca['axis_perpendicular_origin_mm'],'axial_interval_mm':ca['axial_interval_mm']})
  x['bends']=bends
  groups={}
  for d in cyl:
   if d['orientation']!='Reversed':continue
   if t is None or abs(d['axial_interval_mm'][1]-d['axial_interval_mm'][0]-t)>tol:continue
   key=tuple(round(v,6) for v in [d['radius_mm'],*d['axis'],*d['axis_perpendicular_origin_mm'],*d['axial_interval_mm']]);g=groups.setdefault(key,{'radius_mm':d['radius_mm'],'axis':d['axis'],'axis_perpendicular_origin_mm':d['axis_perpendicular_origin_mm'],'axial_interval_mm':d['axial_interval_mm'],'faces':[],'angle_sum':0});g['faces'].append(d['face']);g['angle_sum']+=d['angle_rad']
  holes=[]
  for g in groups.values():
   if abs(g['angle_sum']-2*math.pi)>tol:continue
   middle=sum(g['axial_interval_mm'])/2;center=V(*g['axis_perpendicular_origin_mm'])+V(*g['axis'])*middle
   holes.append({'id':'H%02d'%(len(holes)+1),'D_mm':2*g['radius_mm'],'center_mm':vec(center),'axis':g['axis'],'source_faces':g['faces'],'angular_sum_rad':g['angle_sum'],'physical_hole_from_split_cylinders':True})
  x['holes']=holes
  # Outer skins exclude the thin sheet edge faces and inner-facing cylinders.
  skin=[i for i,f in enumerate(shape.Faces,1) if (isinstance(f.Surface,Part.Plane) and t is not None and f.Area>10*t*t) or (isinstance(f.Surface,Part.Cylinder) and f.Orientation=='Forward' and any(i in b['faces'] for b in bends))]
  edges=[]
  for ia,ib in itertools.combinations(skin,2):
   if any(ea.isSame(eb) for ea in shape.Faces[ia-1].Edges for eb in shape.Faces[ib-1].Edges):edges.append([ia,ib])
  # A topology graph cycle is evidence, not proof that any CAD kernel cannot unfold it.
  graph={i:set() for i in skin}
  for ia,ib in edges:graph[ia].add(ib);graph[ib].add(ia)
  seen=set();components=[]
  for i in skin:
   if i in seen:continue
   todo=[i];component=set()
   while todo:
    k=todo.pop()
    if k in component:continue
    component.add(k);todo.extend(graph[k]-component)
   seen|=component;rank=sum(len(graph[k]) for k in component)//2-len(component)+1
   components.append({'faces':sorted(component),'cycle_rank':rank})
  x['skin_adjacency']={'edges':edges,'components':components,'has_cycle':any(c['cycle_rank']>0 for c in components)}
  return x
 def write_report():
  report['source_sha256_after']=sha(src);report['source_unchanged']=report['source_sha256']==report['source_sha256_after'];(out/'source_audit.json').write_text(json.dumps(report,indent=2))
 source=Part.read(str(src));report={'version':'2.6.1-R06','CAD_executed':True,'FreeCAD':F.Version()[:3],'OCCT':Part.OCC_VERSION,'source_sha256':sha(src),'source_filename':src.name,'shape_type':source.ShapeType,'solid_count':len(source.Solids),'assembly_metadata':'solid identities only; imported solid count is not assembly-component metadata','parts':[],'intersections':[],'config':cfg,'production_release':False};write_report()
 if not source.Solids:raise ValueError('No solids in imported STEP; surface-only import needs another audited adapter')
 parts={};projections={};mesh={};doc=F.newDocument('IsolatedExistingStepAudit')
 def projected(name,shape):
  projections[name]={}
  from formed_isometric import actual_lines
  projections[name]['isometric']=actual_lines(shape)
  for label,direction in [('XY',V(0,0,1)),('XZ',V(0,-1,0)),('YZ',V(1,0,0))]:
   groups=TechDraw.projectEx(shape,direction);projections[name][label]=[[[p.x,p.y] for p in edge.discretize(Deflection=.05)] for group in groups[:5] for edge in group.Edges]
 def normalized(shape,normal,lines=None,return_matrix=False):
  matrix=F.Placement(V(),F.Rotation(normal,V(0,0,1))).toMatrix();flat=shape.transformed(matrix);bb=flat.BoundBox;delta=V(-bb.XMin,-bb.YMin,-bb.ZMax);flat.translate(delta)
  if lines is not None and not lines.isNull():lines=lines.transformed(matrix);lines.translate(delta)
  combined=F.Placement(delta,F.Rotation()).toMatrix().multiply(matrix)
  return (flat,lines,combined) if return_matrix else (flat,lines)
 def flat_face(shape):return max([f for f in shape.Faces if isinstance(f.Surface,Part.Plane) and abs(f.normalAt(0,0).z-1)<1e-6],key=lambda f:f.Area)
 try:
  for i,shape in enumerate(source.Solids,1):
   name='SOLID_%02d'%i;parts[name]=shape;x={'id':name,'role':cfg.get('part_roles',{}).get(name,'unclassified_source'),**describe(shape),'unfold':{'status':'NOT_ATTEMPTED'},'repairs':[]};report['parts'].append(x);x['formed_step']=name+'.step';shape.exportStep(str(out/x['formed_step']));back=Part.read(str(out/x['formed_step']));x['STEP_readback']={'sha256':sha(out/x['formed_step']),'BOP':bop(back),'volume_difference_mm3':abs(back.Volume-shape.Volume),'max_topology_tolerance_mm':back.getTolerance(1),'bbox_difference_mm':max(abs(u-v) for u,v in zip(bbox(shape),bbox(back)))}
   verts,tris=shape.tessellate(.2);mesh[name]={'vertices':[vec(v) for v in verts],'triangles':tris};projected(name,shape);write_report()
   if cfg.get('try_non_design_repair') and not x['BOP']['ok']:
    for method in ['rebuildShell']:
     trial={'method':method,'tolerance_increase_allowed':False,'selected_for_output':False}
     try:
      candidate=Part.makeSolid(Part.makeShell(shape.Faces))
      details=describe(candidate);delta=shape.cut(candidate).Volume+candidate.cut(shape).Volume
      trial.update(after=details,volume_change_mm3=candidate.Volume-shape.Volume,bbox_change_mm=max(abs(u-v) for u,v in zip(bbox(shape),bbox(candidate))),symmetric_volume_difference_mm3=delta,hausdorff_vertex_max_mm=max([candidate.distToShape(Part.Vertex(v.Point))[0] for v in shape.Vertexes]+[shape.distToShape(Part.Vertex(v.Point))[0] for v in candidate.Vertexes]),before_max_tolerance_mm=x['max_topology_tolerance_mm'])
      # Trial results never silently replace the source, even when equivalent.
      trial['equivalent_candidate']=bool(details['BOP']['ok'] and abs(trial['volume_change_mm3'])<=tol and trial['bbox_change_mm']<=tol and delta<=tol and details['max_topology_tolerance_mm']<=x['max_topology_tolerance_mm']+1e-12 and details['holes']==x['holes'] and details['measured_planar_t_mm']==x['measured_planar_t_mm'])
      candidate.exportStep(str(out/(name+'_REPAIR_TRIAL_'+method+'.step')))
     except Exception as ex:trial.update(error=str(ex),traceback=traceback.format_exc())
     x['repairs'].append(trial);write_report()
   t=x['measured_planar_t_mm'];roots=sorted([k for k,f in enumerate(shape.Faces) if isinstance(f.Surface,Part.Plane)],key=lambda k:shape.Faces[k].Area,reverse=True)[:cfg.get('max_root_attempts',3)]
   if t is None:x['unfold']={'status':'BLOCKED','reason':'NO_SUPPORTED_THICKNESS_MEASUREMENT'};write_report();continue
   bends=x['bends'];is_planar=not bends and all(isinstance(f.Surface,Part.Plane) or isinstance(f.Surface,Part.Cylinder) for f in shape.Faces) and abs(shape.Volume/max(shape.Faces[k].Area for k in roots)-t)<=tol
   kvalue=cfg.get('K_ANSI') if cfg.get('K_ANSI') is not None else cfg.get('diagnostic_K_ANSI');diagnostic=bool(not x['BOP']['ok'] or (bends and cfg.get('K_ANSI') is None))
   if not is_planar and (kvalue is None or (not x['BOP']['ok'] and not cfg.get('diagnose_invalid'))):x['unfold']={'status':'BLOCKED','reason':'SOURCE_BOP_FAILED' if not x['BOP']['ok'] else 'COMPENSATION_UNKNOWN','diagnostic_only':False};write_report();continue
   attempts=[];x['unfold']={'status':'BLOCKED','attempts':attempts,'diagnostic_only':diagnostic,'K_ANSI_used':kvalue if bends else None,'K_status':'diagnostic' if diagnostic and bends else cfg.get('K_status','unknown')};ob=doc.addObject('Part::Feature',name);ob.Shape=shape
   for root in roots if not is_planar else roots[:1]:
    attempt={'root_face':root+1,'CAD_executed':True,'K_ANSI_used':kvalue if bends else None,'K_scope':'diagnostic' if diagnostic else cfg.get('K_status','unknown')};attempts.append(attempt)
    try:
     if is_planar:flat,lines=normalized(shape,shape.Faces[root].normalAt(0,0),Part.Shape());native_bends=[];measurement={'measured_t_mm':t,'method':'rigid planar sheet; no bend allowance needed'}
     else:
      from formed_isometric import track_bends,records as bend_records
      with track_bends(NU):(_,fl,ln,normal,native_bends),measurement=get_unfold(NU.BendAllowanceCalculator.from_single_value(kvalue,'ansi'),ob,'Face'+str(root+1),t)
      flat,lines,flat_matrix=normalized(fl,normal,ln,return_matrix=True);attempt['bend_records']=bend_records(native_bends,flat_matrix,root+1,normal,[[[p.x,p.y] for p in edge.discretize(Number=2)] for edge in lines.Edges])
      if len(native_bends)!=len(bends):raise ValueError('Native fold count differs from measured cylinder pairs')
     flat.check(True)
     if not flat.isValid() or len(flat.Solids)!=1 or abs(flat.BoundBox.ZLength-t)>tol:raise ValueError('Native flat validity/thickness failed')
     face=flat_face(flat).copy();face.translate(V(0,0,-face.CenterOfMass.z))
     if abs(flat.Volume/face.Area-t)>tol:raise ValueError('Flat volume/area thickness failed')
     label='DIAGNOSTIC_' if diagnostic else 'CHECKED_';stepname=label+name+'_UNFOLD.step';dxfname=label+name+'.dxf';flat.exportStep(str(out/stepname));rback=Part.read(str(out/stepname));rback.check(True);rface=flat_face(rback).copy();rface.translate(V(0,0,-rface.CenterOfMass.z));difference=face.cut(rface).Area+rface.cut(face).Area
     if difference>tol:raise ValueError('Exported unfold STEP area differs')
     # Keep native exporter bytes for lineage; normalize from the identical actual flat face.
     import Import
     native_name=label+name+'_NATIVE_RAW.dxf';flatobj=doc.addObject('Part::Feature',name+'FlatFace');flatobj.Shape=face;Import.writeDXFObject([flatobj],str(out/native_name),12,False)
     records,indices,dxfdelta=write_dxf(out/dxfname,face)
     if len([r for r in records if r['type']=='CIRCLE'])-(1 if len(face.OuterWire.Edges)==1 and isinstance(face.OuterWire.Edges[0].Curve,Part.Circle) else 0)!=len(x['holes']):raise ValueError('Flat circle-hole coverage differs from measured physical source holes')
     bend_lines=[[[p.x,p.y] for p in edge.discretize(Number=2)] for edge in lines.Edges]
     attempt.update(status='CHECKED',native_raw_dxf=native_name,native_raw_dxf_sha256=sha(out/native_name),normalization_method='shared actual-flat-face writer: explicit mm INSUNITS4 and CUT; no coordinate scaling',flat_step=stepname,dxf=dxfname,flat_BOP=bop(rback),measured_t=measurement,flat_thickness_mm=flat.BoundBox.ZLength,actual_bends=len(native_bends),flat_size_mm=[face.BoundBox.XLength,face.BoundBox.YLength],native_vs_exported_STEP_area_mm2=difference,native_vs_DXF_area_mm2=dxfdelta,records=records,outer_boundary_entity_indices=indices[0],bend_lines=bend_lines,flat_hole_count=len(x['holes']),sloped_outer_edges=sum(r['type']=='LINE' and abs(r['p'][0]-r['q'][0])>tol and abs(r['p'][1]-r['q'][1])>tol for r in records[:len(indices[0])]),corner03_status='NOT_CLASSIFIED_SOURCE_PRESERVED',flat_step_sha256=sha(out/stepname),dxf_sha256=sha(out/dxfname))
     x['unfold'].update(status='DIAGNOSTIC_ONLY' if diagnostic else 'GEOMETRY_CHECKED_WITH_HOLD',selected_attempt=len(attempts)-1,manufacturing_accepted=False,K_ANSI_used=kvalue if bends else None,K_status='diagnostic' if diagnostic and bends else cfg.get('K_status','unknown'));break
    except Exception as ex:attempt.update(status='FAILED',error=str(ex),error_type=type(ex).__name__,traceback=traceback.format_exc())
    write_report()
   write_report()
  for (na,sa),(nb,sb) in itertools.combinations(parts.items(),2):
   common=sa.common(sb);report['intersections'].append({'parts':[na,nb],'volume_mm3':common.Volume,'distance_mm':sa.distToShape(sb)[0],'intersection_BOP':bop(common),'diagnostic_on_invalid_source':not all(x['BOP']['ok'] for x in report['parts'] if x['id'] in [na,nb])})
  report['same_side_hole_pairs']=[]
  for (na,sa),(nb,sb) in itertools.combinations([(x['id'],x) for x in report['parts']],2):
   for ha,hb in itertools.product(sa['holes'],sb['holes']):
    axis=V(*ha['axis']);delta=V(*hb['center_mm'])-V(*ha['center_mm']);offset=delta.cross(axis).Length;axial=abs(delta.dot(axis));limit=(sa['measured_planar_t_mm'] or 0)+(sb['measured_planar_t_mm'] or 0)+cfg.get('adjacent_hole_gap_limit_mm',2)
    if V(*hb['axis']).cross(axis).Length<1e-6 and offset<tol and axial<=limit:report['same_side_hole_pairs'].append({'parts':[na,nb],'hole_ids':[ha['id'],hb['id']],'axis_offset_mm':offset,'axial_midplane_distance_mm':axial,'proximity_filter_mm':limit,'connection_intent':'unknown; geometric adjacent pairs only'})
  interface=cfg.get('interface')
  if interface:
   axis='XYZ'.index(interface['up_axis']);sign=interface.get('up_sign',1);lid=next(x for x in report['parts'] if x['id']==interface['lid_id']);body=[x for x in report['parts'] if x['id'] in interface['body_ids']];lplanes=[f for f in lid['faces_detail'] if 'normal' in f];bodyplanes=[{**f,'part_id':x['id']} for x in body for f in x['faces_detail'] if 'normal' in f];roof=max([f for f in lplanes if f['normal'][axis]*sign<-.999],key=lambda f:f['area_mm2']);body_top=max(f['center_mm'][axis]*sign for f in bodyplanes if f['normal'][axis]*sign>.999);g=[]
   for lateral in [k for k in range(3) if k!=axis]:
    for direction in [-1,1]:
     wall=max([f for f in bodyplanes if f['normal'][lateral]*direction>.999],key=lambda f:(round(f['center_mm'][lateral]*direction,7),f['area_mm2']));candidate=min([f for f in lplanes if f['normal'][lateral]*direction<-.999],key=lambda f:abs(f['center_mm'][lateral]-wall['center_mm'][lateral]));g.append({'axis':'XYZ'[lateral],'side':direction,'body_part':wall['part_id'],'body_face':wall['face'],'lid_face':candidate['face'],'single_side_gap_mm':direction*(candidate['center_mm'][lateral]-wall['center_mm'][lateral])})
   report['interface_measurement']={'source':'explicit part mapping and axis; actual planar faces','q_mm':roof['center_mm'][axis]*sign-body_top,'g_walls':g,'corner_clearance_certified':False}
  assembly=Part.makeCompound(list(parts.values()));assembly.exportStep(str(out/'SOURCE_ASSEMBLY.step'));shifts={};moved=[];extent=max(source.BoundBox.XLength,source.BoundBox.YLength,source.BoundBox.ZLength)
  for i,(name,shape) in enumerate(parts.items()):
   delta=V(0,0,(i-(len(parts)-1)/2)*extent*.6);shifts[name]=vec(delta);copy=shape.copy();copy.translate(delta);moved.append(copy)
  exploded=Part.makeCompound(moved);exploded.exportStep(str(out/'SOURCE_EXPLODED.step'));report['rigid_exports']={}
  for label,shape in [('SOURCE_ASSEMBLY',assembly),('SOURCE_EXPLODED',exploded)]:
   back=Part.read(str(out/(label+'.step')));restored=[]
   if len(back.Solids)!=len(parts):raise ValueError('Rigid assembly STEP lost solids')
   for (name,original),read in zip(parts.items(),back.Solids):
    read=read.copy()
    if label=='SOURCE_EXPLODED':read.translate(-V(*shifts[name]))
    restored.append({'part':name,'volume_difference_mm3':abs(original.Volume-read.Volume),'symmetric_volume_difference_mm3':original.cut(read).Volume+read.cut(original).Volume,'BOP':bop(read)})
   report['rigid_exports'][label]={'path':label+'.step','sha256':sha(out/(label+'.step')),'restoration':restored};projected(label,shape)
  report['exploded_translations_mm']=shifts;report['CAD_audit_complete']=True;write_report();(out/'source_projections.json').write_text(json.dumps(projections));(out/'source_mesh.json').write_text(json.dumps({'parts':mesh,'exploded_translations_mm':shifts}))
 finally:F.closeDocument(doc.Name);write_report()
 if not report['source_unchanged']:raise RuntimeError('Source changed during audit')
if __name__=='__main__':main()
