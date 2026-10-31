#!/usr/bin/env python3
"""Four-hole trapezoid: actual STEP inner-circle axes and DXF centers. Read-only CAD.
Numeric tolerance is a computational comparison tolerance, never a factory acceptance tolerance.
Only circular holes on a planar handle mounting face are supported; other geometry BLOCKS.
"""
import argparse,json,math,hashlib,sys
from pathlib import Path
from create_intake import apply_project_defaults
from cut_dxf import parse_dxf
NUMERIC_TOL=1e-5
def value(f):return f.get('value') if isinstance(f,dict) else None
def sub(a,b):return [x-y for x,y in zip(a,b)]
def dot(a,b):return sum(x*y for x,y in zip(a,b))
def norm(a):return math.sqrt(dot(a,a))
def unit(a):
 n=norm(a)
 if n<=1e-12:raise ValueError('zero axis/row vector')
 return [x/n for x in a]
def cross(a,b):return [a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]]
def finite(a,n):return isinstance(a,list) and len(a)==n and all(isinstance(x,(int,float)) and not isinstance(x,bool) and math.isfinite(x) for x in a)
def parameter_hash(doc):return hashlib.sha256(json.dumps(apply_project_defaults(doc),ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def diameter(group):
 s=group['laser_size'];n=value(s['magnitude']);rep=value(s['representation'])
 if n is None or rep not in ['diameter','radius'] or n<=0:raise ValueError('handle laser hole diameter unresolved;85 does not supply diameter')
 return n*2 if rep=='radius' else n

def contracts(doc,part_ids=None,require_positions=True):
 d=apply_project_defaults(doc);h=d['handles'];tol=NUMERIC_TOL
 if value(h['enabled']) is not True or value(h['layout'])!='four_hole_trapezoid':raise ValueError('explicit active four-hole trapezoid scope required')
 target=value(h['wide_row_pitch'])
 if target is None or target<=0:raise ValueError('wide-row pitch unresolved')
 if h['wide_row_pitch']['status']=='default' and abs(target-85.0)>tol:raise ValueError('default wide-row pitch is85.00mm, never84')
 if value(h['holes_per_handle']) not in [None,4]:raise ValueError('four-hole layout conflicts with holes_per_handle')
 groups={g['id']:g for g in d['hole_groups']};lookup={};expected=set()
 for gid in h['hole_group_ids']:
  if gid not in groups:raise ValueError('unknown handle hole group')
  g=groups[gid]
  if value(g['purpose'])!='handle':raise ValueError('handle pattern must reference handle-purpose groups')
  for pos in g['positions']:
   if pos['id'] in lookup:raise ValueError('duplicate handle hole ID')
   lookup[pos['id']]=(pos,g);expected.add(pos['id'])
 pats=h['patterns'];seen=set();names=set();records=[]
 if not pats:raise ValueError('each handle needs explicit wide/narrow hole ID pairs; no guessing from global extrema')
 for pat in pats:
  if pat['id'] in names:raise ValueError('duplicate handle pattern ID')
  names.add(pat['id']);ids=pat['wide_hole_ids']+pat['narrow_hole_ids']
  if len(ids)!=4 or len(set(ids))!=4 or any(k in seen for k in ids):raise ValueError('each instance must own four distinct non-reused hole IDs')
  seen.update(ids)
  if any(k not in lookup for k in ids):raise ValueError('pattern references unknown handle hole')
  if any(lookup[k][0]['part_id']!=pat['part_id'] for k in ids):raise ValueError('pattern holes cross part boundaries')
  if part_ids is not None and pat['part_id'] not in part_ids:continue
  rec={'id':pat['id'],'part_id':pat['part_id'],'hole_ids':ids,'wide_target_mm':target,'narrow_target_mm':value(h['narrow_row_pitch']),'spacing_target_mm':value(h['row_spacing'])}
  if require_positions:
   pts=[value(lookup[k][0]['center']) for k in ids];axes=[value(lookup[k][0]['axis']) for k in ids]
   if any(not finite(q,3) for q in pts+axes):raise ValueError('handle center/axis unresolved')
   axes=[unit(a) for a in axes]
   if any(norm(cross(a,axes[0]))>tol for a in axes):raise ValueError('handle axes must be parallel in this planar adapter')
   rec.update(points=pts,axes=axes,diameters=[diameter(lookup[k][1]) for k in ids]);measure_pattern(rec,pts)
  records.append(rec)
 if seen!=expected:raise ValueError('every physical handle hole must belong to exactly one declared instance')
 qty=value(h['quantity'])
 if qty is not None and len(pats)!=qty:raise ValueError('pattern count differs from explicit handle quantity')
 if not records:raise ValueError('no applicable handle pattern for selected part')
 return records

def measure_pattern(rec,points):
 a,b,c,d=points;u=sub(b,a);v=sub(d,c);wide=norm(u);narrow=norm(v);tol=NUMERIC_TOL
 if wide<=tol or narrow<=tol or norm(cross(unit(u),unit(v)))>tol:raise ValueError('handle row pairs must be nonzero and parallel')
 if narrow>=wide-tol:raise ValueError('declared wide row must be wider than narrow row')
 offset=sub(c,a);row_normal=sub(offset,[dot(offset,unit(u))*q for q in unit(u)]);spacing=norm(row_normal)
 if spacing<=tol:raise ValueError('handle rows must be distinct')
 if len(a)==3:
  normal=unit(cross(u,offset))
  if abs(dot(sub(d,a),normal))>tol:raise ValueError('four handle centers not coplanar')
  if any(norm(cross(normal,axis))>tol for axis in rec.get('axes',[])):raise ValueError('hole axes not normal to mounting plane')
 for actual,target,label in [(wide,rec['wide_target_mm'],'wide'),(narrow,rec.get('narrow_target_mm'),'narrow'),(spacing,rec.get('spacing_target_mm'),'row spacing')]:
  if target is not None and abs(actual-target)>tol:raise ValueError(label+' actual center distance '+str(actual)+' differs from specified '+str(target))
 return {'wide_row_pitch_mm':wide,'narrow_row_pitch_mm':narrow,'row_spacing_mm':spacing}

def mapped(point,m,axis):
 if not finite(m,8):raise ValueError('explicit8-value CAD flat map required')
 u=m[:3];v=m[4:7]
 if abs(norm(u)-1)>NUMERIC_TOL or abs(norm(v)-1)>NUMERIC_TOL or abs(dot(u,v))>NUMERIC_TOL:raise ValueError('flat map must be an isometry; scaling/shear cannot disguise84 as85')
 if norm(cross(unit(cross(u,v)),axis))>NUMERIC_TOL:raise ValueError('flat map plane not normal to handle hole axes')
 return [dot(u,point)+m[3],dot(v,point)+m[7],0]

def check_dxf(doc,path,flat_maps,part_ids=None):
 records=contracts(doc,part_ids);ents=parse_dxf(Path(path));circles=[e for e in ents if e['type']=='CIRCLE'];used=set();result=[]
 for rec in records:
  m=flat_maps.get(rec['id']);actual=[];matches=[]
  for pt,axis,D,hid in zip(rec['points'],rec['axes'],rec['diameters'],rec['hole_ids']):
   desired=mapped(pt,m,axis);candidates=[]
   for i,e in enumerate(circles):
    center=[float(e[10]),float(e[20]),0]
    if math.dist(center,desired)<=NUMERIC_TOL and abs(2*float(e[40])-D)<=NUMERIC_TOL:candidates.append((i,center))
   if len(candidates)!=1 or candidates[0][0] in used:raise ValueError('DXF actual unique circle center/diameter mismatch for '+hid)
   i,center=candidates[0];used.add(i);actual.append(center);matches.append({'hole_id':hid,'actual_center_mm':center,'diameter_mm':D})
  # These are actual DXF circle centers, not dimensions read from text labels.
  measured=measure_pattern({**rec,'axes':[[0,0,1]]*4},actual)
  result.append({'pattern_id':rec['id'],'part_id':rec['part_id'],**measured,'holes':matches})
 return {'patterns':result,'numeric_tolerance_mm':NUMERIC_TOL,'manufacturing_tolerance_inferred':False}

def step_circles(path):
 import FreeCAD,Part
 shape=Part.read(str(path))
 if not shape.isValid() or len(shape.Solids)!=1:raise ValueError('handle STEP adapter requires one valid actual part solid; assembly ownership needs a separate adapter')
 candidates=[]
 for face in shape.Faces:
  if face.Surface.TypeId!='Part::GeomPlane':continue
  for wire in face.Wires:
   if wire.isSame(face.OuterWire):continue
   edges=wire.Edges
   if not edges or any(e.Curve.TypeId!='Part::GeomCircle' for e in edges):continue
   first=edges[0].Curve;center=list(first.Center);axis=unit(list(first.Axis));rad=first.Radius
   if abs(sum(e.Length for e in edges)-2*math.pi*rad)>NUMERIC_TOL:continue
   if any(math.dist(list(e.Curve.Center),center)>NUMERIC_TOL or abs(e.Curve.Radius-rad)>NUMERIC_TOL for e in edges):continue
   candidates.append({'center':center,'axis':axis,'diameter':2*rad})
 if not candidates:raise ValueError('no actual circular inner wires on STEP planar faces; unsupported holes BLOCK')
 return candidates

def check_step(doc,path,part_ids=None):
 records=contracts(doc,part_ids)
 if len({rec['part_id'] for rec in records})!=1:raise ValueError('one part per STEP handle check; do not pool assembly holes')
 candidates=step_circles(path);result=[]
 for rec in records:
  actual=[];holes=[]
  for pt,axis,D,hid in zip(rec['points'],rec['axes'],rec['diameters'],rec['hole_ids']):
   matches=[]
   for q in candidates:
    if abs(q['diameter']-D)>NUMERIC_TOL or norm(cross(q['axis'],axis))>NUMERIC_TOL:continue
    delta=sub(q['center'],pt);off=sub(delta,[dot(delta,axis)*x for x in axis])
    if norm(off)<=NUMERIC_TOL:matches.append(q)
   if not matches:raise ValueError('STEP actual inner-circle axis/diameter mismatch for '+hid)
   # Top/bottom circular wires of the SAME axis are one physical hole; project onto declared datum plane.
   q=matches[0];delta=sub(q['center'],pt);center=sub(q['center'],[dot(delta,axis)*x for x in axis]);actual.append(center);holes.append({'hole_id':hid,'axis_point_mm':q['center'],'datum_center_mm':center,'axis':q['axis'],'diameter_mm':q['diameter']})
  measured=measure_pattern(rec,actual);result.append({'pattern_id':rec['id'],'part_id':rec['part_id'],**measured,'holes':holes})
 return {'patterns':result,'numeric_tolerance_mm':NUMERIC_TOL,'manufacturing_tolerance_inferred':False}

def verify(doc,step_path,dxf_path,flat_maps,part_ids=None):
 step=check_step(doc,step_path,part_ids);dxf=check_dxf(doc,dxf_path,flat_maps,part_ids)
 for a,b in zip(step['patterns'],dxf['patterns']):
  if a['pattern_id']!=b['pattern_id'] or abs(a['wide_row_pitch_mm']-b['wide_row_pitch_mm'])>NUMERIC_TOL:raise ValueError('actual STEP/DXF pattern mismatch')
 sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
 return {'ok':True,'CAD_executed':True,'method':'actual STEP planar-face inner-circle axes and actual DXF circle-center readback','parameter_hash':parameter_hash(doc),'input_sha256':{'formed_step':sha(step_path),'dxf':sha(dxf_path)},'flat_maps':flat_maps,'part_ids':part_ids,'STEP':step,'DXF':dxf,'production_release':False,'scope':'planar four-hole handle center/axis and laser diameter checks; no entire-project CAD or factory acceptance certification'}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('project');p.add_argument('--step',required=True);p.add_argument('--dxf',required=True);p.add_argument('--flat-maps',required=True);p.add_argument('--part',action='append');p.add_argument('--module-path',action='append',default=[]);p.add_argument('--output');a=p.parse_args()
 from safe_io import guard_outputs
 try:guard_outputs([a.project,a.step,a.dxf,a.flat_maps],[a.output])
 except ValueError as ex:p.error(str(ex))
 sys.path.extend(a.module_path)
 try:result=verify(json.loads(Path(a.project).read_text()),a.step,a.dxf,json.loads(Path(a.flat_maps).read_text()),a.part)
 except Exception as ex:result={'ok':False,'CAD_executed':False,'error_type':type(ex).__name__,'error':str(ex),'production_release':False}
 text=json.dumps(result,ensure_ascii=False,indent=2);print(text)
 if a.output:Path(a.output).write_text(text+'\n')
 raise SystemExit(0 if result['ok'] else 2)
