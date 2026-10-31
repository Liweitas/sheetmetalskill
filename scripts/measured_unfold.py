"""Native unfolding with thickness independently measured on the actual formed STEP.
The SheetMetal normal-edge mode may select shortened03 corner boundary edges.
No tolerance relaxation; planar skin distance and concentric bend radii must agree.
Only the current process's estimator callback is scoped/restored; plugin files never change.
"""
import math
def measured_thickness(shape,root_index,expected,tol=1e-5):
 import FreeCAD as F,Part,SheetMetalNewUnfolder as NU
 root=shape.Faces[root_index]
 if not isinstance(root.Surface,Part.Plane):raise ValueError("Thickness root must be an actual planar skin")
 normal=root.normalAt(0,0);origin=root.Surface.Position;candidates=[]
 for i,face in enumerate(shape.Faces):
  if i==root_index or not isinstance(face.Surface,Part.Plane) or normal.dot(face.normalAt(0,0))>-.999999:continue
  distance=(origin-face.Surface.Position).dot(normal)
  if distance<=1e-7:continue
  moved=face.copy();moved.translate(normal*distance)
  overlap=root.common(moved).Area
  fraction=overlap/max(root.Area,1e-12)
  if fraction>=.9:candidates.append((distance,-fraction,i))
 if not candidates:raise ValueError("No supported opposing planar skin for independent thickness measurement")
 distance,negfraction,opposite=min(candidates)
 cylinder=NU.EstimateThickness.from_cylinders(shape);edge=NU.EstimateThickness.from_normal_edges(shape,root_index)
 if not math.isfinite(distance) or abs(distance-expected)>tol:raise ValueError("Actual planar sheet thickness differs from specification: "+str(distance))
 if not cylinder or abs(cylinder-distance)>tol:raise ValueError("Concentric bend radii disagree with planar skin thickness")
 return {"measured_t_mm":distance,"opposite_skin_face":opposite+1,"projected_skin_overlap_fraction":-negfraction,"concentric_bend_t_mm":cylinder,"legacy_normal_edge_estimate_mm":edge,"legacy_estimator_disagrees":abs(edge-distance)>tol,"method":"actual opposing planar skin distance corroborated by actual concentric bend radii","tolerance_mm":tol}
def get_unfold(bac,ob,facename,expected):
 import SheetMetalNewUnfolder as NU
 root=int(facename[4:])-1;measurement=measured_thickness(ob.Shape,root,expected)
 original=NU.EstimateThickness.__dict__["using_best_method"]
 def exact_from_geometry(shape,selected_face):
  return measured_thickness(shape,selected_face,expected)["measured_t_mm"]
 NU.EstimateThickness.using_best_method=staticmethod(exact_from_geometry)
 try:result=NU.getUnfold(bac,ob,facename)
 finally:NU.EstimateThickness.using_best_method=original
 return result,measurement
