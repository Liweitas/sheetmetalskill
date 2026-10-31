#!/usr/bin/env python3
"""CAD-Python author test on an actual lid STEP: thickness rejection and callback restoration."""
import argparse,json,sys
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--formed',required=True);p.add_argument('--nominal',required=True,type=float);p.add_argument('--K',type=float,default=.5);p.add_argument('--module-path',action='append',default=[]);p.add_argument('--output',required=True);a=p.parse_args()
for path in a.module_path:sys.path.insert(0,path)
import FreeCAD as F,Part,SheetMetalNewUnfolder as NU
from measured_unfold import measured_thickness,get_unfold
shape=Part.read(a.formed);root=max([i for i,face in enumerate(shape.Faces) if isinstance(face.Surface,Part.Plane) and face.normalAt(0,0).z>.999999],key=lambda i:shape.Faces[i].Area)
measurement=measured_thickness(shape,root,a.nominal)
try:measured_thickness(shape,root,a.nominal+.01)
except ValueError as ex:wrong={'rejected':True,'error':str(ex)}
else:raise RuntimeError('Wrong nominal thickness unexpectedly accepted')
doc=F.newDocument('IsolatedThicknessSelftest');ob=doc.addObject('Part::Feature','Lid');ob.Shape=shape;bac=NU.BendAllowanceCalculator.from_single_value(a.K,'ansi');original=NU.EstimateThickness.__dict__['using_best_method'];native=NU.getUnfold
try:
 def injected(*args):raise RuntimeError('INTENTIONAL_CALLBACK_RESTORE_TEST')
 NU.getUnfold=injected
 try:get_unfold(bac,ob,'Face'+str(root+1),a.nominal)
 except RuntimeError as ex:
  if str(ex)!='INTENTIONAL_CALLBACK_RESTORE_TEST':raise
 finally:NU.getUnfold=native
 if NU.EstimateThickness.__dict__['using_best_method'] is not original:raise RuntimeError('Thickness callback not restored after failure')
 (_,flat,lines,normal,bends),measured=get_unfold(bac,ob,'Face'+str(root+1),a.nominal)
 if NU.EstimateThickness.__dict__['using_best_method'] is not original:raise RuntimeError('Thickness callback not restored after success')
 flat=flat.transformed(F.Placement(F.Vector(),F.Rotation(normal,F.Vector(0,0,1))).toMatrix())
 if not flat.isValid() or len(flat.Solids)!=1 or abs(flat.BoundBox.ZLength-a.nominal)>1e-5:raise RuntimeError('Actual flat thickness failed')
 result={'author_selftest_only':True,'actual_measurement':measurement,'wrong_nominal':wrong,'callback_restored_after_failure_and_success':True,'native_flat_thickness_mm':flat.BoundBox.ZLength,'actual_bends':len(bends),'tolerance_mm':1e-5,'production_release':False}
 Path(a.output).write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
finally:F.closeDocument(doc.Name)
