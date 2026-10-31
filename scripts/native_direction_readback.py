#!/usr/bin/env python3
"""Read-side native direction proof from actual STEP/selected root, never writer JSON consensus.
Does not import formed_isometric.track_bends/records. No CAD file is saved or edited.
"""
import argparse,json,math,sys
from pathlib import Path

def segments_equal(a,b,tol=1e-5):
 return min(max(math.dist(a[0],b[0]),math.dist(a[1],b[1])),max(math.dist(a[0],b[1]),math.dist(a[1],b[0])))<=tol

def compare_claims(actual,claims,root_face,root_normal):
 if len(actual)!=len(claims):raise ValueError('NATIVE_DIRECTION: native bend/claim count differs')
 used=set()
 for c in claims:
  matches=[i for i,a in enumerate(actual) if math.dist(a['formed_point_mm'],c['source_formed_point_mm'])<=1e-5]
  if len(matches)!=1 or matches[0] in used:raise ValueError('NATIVE_DIRECTION: bend has no unique actual cylindrical source point')
  i=matches[0];used.add(i);a=actual[i];angle=c.get('angle_signed_deg')
  if isinstance(angle,bool) or not isinstance(angle,(int,float)) or not math.isfinite(angle) or abs(angle-a['native_signed_angle_deg'])>1e-7 or c.get('direction')!=a['native_direction']:raise ValueError('NATIVE_DIRECTION: '+str(c.get('id'))+' actual '+a['native_direction']+'/'+str(a['native_signed_angle_deg'])+' deg differs from claimed '+str(c.get('direction'))+'/'+str(angle))
  if c.get('root_face')!=root_face or math.dist(c.get('root_skin_normal',[]),root_normal)>1e-6:raise ValueError('NATIVE_DIRECTION: selected actual root/normal differs')
  axis=c['source_formed_axis'];other=a['axis'];cross=[axis[1]*other[2]-axis[2]*other[1],axis[2]*other[0]-axis[0]*other[2],axis[0]*other[1]-axis[1]*other[0]]
  if abs(math.sqrt(sum(v*v for v in axis))-1)>1e-6 or math.sqrt(sum(v*v for v in cross))>1e-6:raise ValueError('NATIVE_DIRECTION: actual cylinder axis differs')
  claimed=c['flat_segments_mm'];fresh=a['segments']
  if len(claimed)!=len(fresh) or any(sum(segments_equal(s,t) for t in claimed)!=1 for s in fresh):raise ValueError('NATIVE_DIRECTION: signed angle not linked to actual trimmed native bend segments')
 return True

def unfold_readback(module,obj,root_face,t,K,claims=None):
 import FreeCAD as F
 from measured_unfold import get_unfold
 V=F.Vector;captured=[];transforms=[];unroll=module.unroll_cylinder;move=module.SketchExtraction.move_to_origin
 def observe_cylinder(face,*args,**kw):
  edges,info=unroll(face,*args,**kw);u0,u1,v0,v1=face.ParameterRange
  captured.append((info,list(face.valueAt((u0+u1)/2,(v0+v1)/2)),list(face.Surface.Axis)));return edges,info
 def observe_sketch(*args,**kw):
  m=move(*args,**kw);transforms.append(m);return m
 module.unroll_cylinder=observe_cylinder;module.SketchExtraction.move_to_origin=staticmethod(observe_sketch)
 try:result,thickness=get_unfold(module.BendAllowanceCalculator.from_single_value(K,'ansi'),obj,'Face'+str(root_face),t)
 finally:module.unroll_cylinder=unroll;module.SketchExtraction.move_to_origin=staticmethod(move)
 _,flat,folds,normal,bends=result
 if not transforms:raise ValueError('NATIVE_DIRECTION: actual native sketch transform unavailable')
 rot=F.Placement(V(),F.Rotation(normal,V(0,0,1))).toMatrix();s=flat.transformed(rot);bb=s.BoundBox;delta=V(-bb.XMin,-bb.YMin,-bb.ZMax);s.translate(delta);matrix=F.Placement(delta,F.Rotation()).toMatrix().multiply(rot);folds=folds.transformed(matrix)
 actual_segments=[[[p.x,p.y] for p in e.discretize(Number=2)] for e in folds.Edges];actual=[]
 for b in bends:
  observed=[(pt,axis) for bi,pt,axis in captured if bi is b]
  if len(observed)!=1:raise ValueError('NATIVE_DIRECTION: bend metadata not from actual native invocation')
  point,axis=observed[0];line=b.line.transformed(transforms[-1].inverse()).transformed(matrix);p,q=[list(v.Point)[:2] for v in line.Vertexes];dx=q[0]-p[0];dy=q[1]-p[1];length=math.hypot(dx,dy)
  if length<1e-7:raise ValueError('NATIVE_DIRECTION: degenerate native fold reference')
  def belongs(v):return abs((v[0]-p[0])*dy-(v[1]-p[1])*dx)/length<=1e-5 and -1e-5<=((v[0]-p[0])*dx+(v[1]-p[1])*dy)/length<=length+1e-5
  fragments=[seg for seg in actual_segments if all(belongs(v) for v in seg)]
  if not fragments:raise ValueError('NATIVE_DIRECTION: no actual trimmed segment for cylindrical bend')
  actual.append({'native_signed_angle_deg':b.angle,'native_direction':'UP' if b.angle>0 else 'DOWN','formed_point_mm':point,'axis':axis,'segments':fragments})
 if claims is not None:compare_claims(actual,claims,root_face,list(normal))
 return result,thickness,{'root_face':root_face,'actual_root_normal':list(normal),'native_bends':actual,'claims_compared_to_actual_CAD':claims is not None,'CAD_executed':True}

def inspect(root,request):
 import FreeCAD as F,Part,SheetMetalNewUnfolder as NU
 root=Path(root).resolve();proof=[]
 def path(name):
  p=(root/name).resolve()
  if not p.is_relative_to(root):raise ValueError('NATIVE_DIRECTION: path escapes output root')
  return p
 doc=F.newDocument('NativeDirectionReadOnlyProof')
 try:
  for part in request['parts']:
   shape=Part.read(str(path(part['formed_step'])));shape.check(True)
   planes=[i for i,f in enumerate(shape.Faces) if isinstance(f.Surface,Part.Plane)]
   if part['role']=='lid':
    top=shape.BoundBox.ZMax;planes=[i for i in planes if abs(shape.Faces[i].CenterOfMass.z-top)<=1e-5 and shape.Faces[i].normalAt(0,0).z>.999]
   root_face=max(planes,key=lambda i:shape.Faces[i].Area)+1;ob=doc.addObject('Part::Feature',part['id']);ob.Shape=shape
   _,_,r=unfold_readback(NU,ob,root_face,part['t'],part['K_ANSI'],part['claims']);proof.append({'part_id':part['id'],**r})
  result={'ok':True,'CAD_executed':True,'actual_STEP_read':True,'checks':proof,'production_release':False}
  if request.get('interference'):
   from interference_volume import require_same_measurement,measurement
   record=request['interference'];body=Part.read(str(path(record['body_step'])));lid=Part.read(str(path(record['lid_step'])));volume=abs(body.common(lid).Volume)
   require_same_measurement(record['claimed_authority_mm3'],volume);result['actual_interference_readback']=measurement(volume)
  return result
 finally:F.closeDocument(doc.Name)

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--root',required=True);ap.add_argument('--request',required=True);ap.add_argument('--output',required=True);ap.add_argument('--module-path',action='append',default=[]);a=ap.parse_args()
 for p in a.module_path:sys.path.insert(0,p)
 try:r=inspect(a.root,json.loads(Path(a.request).read_text()))
 except Exception as ex:r={'ok':False,'CAD_executed':'FreeCAD' in sys.modules,'errors':[str(ex)],'production_release':False}
 Path(a.output).write_text(json.dumps(r,indent=2));raise SystemExit(0 if r['ok'] else 2)
if __name__=='__main__':main()
