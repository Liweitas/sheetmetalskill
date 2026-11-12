#!/usr/bin/env python3
"""Read-only STEP dimensions. Does not use drawing projections, process receipts or writer bbox reports."""
import argparse,hashlib,json,sys
from pathlib import Path
def inspect(root,request):
 import FreeCAD as F,Part,time as _t
 _marks=[]; _marks.append(('start',_t.time()))
 root=Path(root).resolve();parts={};body=[];loaded={}
 def box(shape):
  b=shape.BoundBox;return [b.XMin,b.YMin,b.ZMin,b.XMax,b.YMax,b.ZMax]
 for item in request['shapes']:
  path=(root/item['path']).resolve()
  if not path.is_relative_to(root) or not path.is_file():raise ValueError('ACTUAL_STEP_DIMENSIONS: invalid input path')
  shape=Part.read(str(path))
  if shape.isNull() or not shape.isValid():raise ValueError('ACTUAL_STEP_DIMENSIONS: invalid shape '+item['id'])
  parts[item['id']]={'bbox_mm':box(shape),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'source':'fresh Part.read, no PDF or JSON bbox used'}
  if request.get('dimensioned_CN_views'):
   from formed_isometric import actual_lines
   import TechDraw
   parts[item['id']]['isometric_lines_mm']=actual_lines(shape);parts[item['id']]['vertices_mm']=[list(v.Point) for v in shape.Vertexes]
   projections={}
   for label,direction in [('front',F.Vector(0,-1,0)),('right',F.Vector(1,0,0)),('top',F.Vector(0,0,1))]:
    pol=[]
    for group in TechDraw.projectEx(shape,direction)[:5]:
     for edge in group.Edges:
      pol.append([[p.x,p.y] if label=='top' else [-p.y,p.x] if label=='right' else [p.y,-p.x] for p in edge.discretize(Deflection=.05)])
    projections[label]=pol
   parts[item['id']]['orthographic_lines_mm']=projections
  loaded[item['id']]=shape
  if item.get('body_part'):body.append(shape)
 _marks.append(('after_shapes',_t.time()))
 if not body:raise ValueError('ACTUAL_STEP_DIMENSIONS: no body sheets')
 identity=None
 if request.get('translation_only_parts'):
  owners=request['translation_only_parts'];identity={}
  for label in ['ASSEMBLY','EXPLODED']:
   solids=list(loaded[label].Solids);used=set();rows=[]
   if len(solids)!=len(owners):raise ValueError('ASSEMBLY_TRANSLATION_PART_COUNT: '+label)
   for owner,delta in owners.items():
    original=loaded[owner];target=original.copy()
    if label=='EXPLODED':target.translate(F.Vector(*delta))
    possible=[]
    def _same_shape(a,b,tol):
     # 包围盒+体积+面积已筛过；用双向顶点最大偏差确认是同一实体（重合时为 0）。
     # 等价于对称布尔差，但布尔 cut 对重合复杂实体极慢（单件约 13s），顶点偏差约 0.02s。
     cb=Part.makeCompound(b.Vertexes); ca=Part.makeCompound(a.Vertexes)
     return max(max(cb.distToShape(Part.Vertex(v.Point))[0] for v in a.Vertexes), max(ca.distToShape(Part.Vertex(v.Point))[0] for v in b.Vertexes))<=tol
    for i,s in enumerate(solids):
     if i in used or max(abs(a-b) for a,b in zip(box(s),box(target)))>1e-5:continue
     tolerance=max(1e-5,abs(target.Volume)*1e-8)
     if abs(s.Volume-target.Volume)>tolerance or abs(s.Area-target.Area)>max(1e-5,target.Area*1e-8):continue
     if _same_shape(s,target,1e-5):possible.append((i,0.0))
    if len(possible)!=1:raise ValueError('ASSEMBLY_NOT_SAME_TRANSLATED_PART: '+label+'/'+owner)
    i,difference=possible[0];used.add(i);rows.append({'part_id':owner,'translation_mm':delta if label=='EXPLODED' else [0,0,0],'symmetric_volume_difference_mm3':difference})
   identity[label]=rows
 return {'ok':True,'CAD_executed':True,'actual_STEP_read':True,'shapes':parts,'body_bbox_mm':box(Part.makeCompound(body)),'translation_only_identity':identity,'production_release':False}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--request',required=True);p.add_argument('--output',required=True);p.add_argument('--module-path',action='append',default=[]);a=p.parse_args()
 for path in a.module_path:sys.path.insert(0,path)
 try:r=inspect(a.root,json.loads(Path(a.request).read_text()))
 except Exception as ex:r={'ok':False,'CAD_executed':'FreeCAD' in sys.modules,'errors':[str(ex)],'production_release':False}
 Path(a.output).write_text(json.dumps(r,indent=2));raise SystemExit(0 if r['ok'] else 2)
