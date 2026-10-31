"""Orthographic isometric wireframe from actual formed BRep, plus native bend provenance.
No CAD imports until called in the CAD worker. UP/DOWN is the SheetMetal native
signed angle relative to its chosen root skin; it is not a machine/sequence instruction.
"""
import math
from contextlib import contextmanager

def iso_point(p):return [(p[0]+p[1])/math.sqrt(2),(-p[0]+p[1]+2*p[2])/math.sqrt(6)]

def actual_lines(shape):
 return [[iso_point(list(v)) for v in edge.discretize(Deflection=.05)] for edge in shape.Edges]

@contextmanager
def track_bends(module):
 original=module.unroll_cylinder;original_move=module.SketchExtraction.move_to_origin;captured=[]
 def tracked(face,*args,**kwargs):
  edges,info=original(face,*args,**kwargs);u0,u1,v0,v1=face.ParameterRange
  info.source_formed_point_mm=list(face.valueAt((u0+u1)/2,(v0+v1)/2));info.source_formed_axis=list(face.Surface.Axis)
  captured.append(info)
  return edges,info
 def move(*args,**kwargs):
  matrix=original_move(*args,**kwargs)
  for info in captured:info.native_sketch_inverse=matrix.inverse()
  return matrix
 module.unroll_cylinder=tracked
 module.SketchExtraction.move_to_origin=staticmethod(move)
 try:yield
 finally:
  module.unroll_cylinder=original;module.SketchExtraction.move_to_origin=staticmethod(original_move)

def records(bends,flat_matrix,root_face,root_normal,native_lines):
 out=[]
 for bend in bends:
  if not hasattr(bend,'source_formed_point_mm'):raise ValueError('ISOMETRIC: native bend provenance unavailable; unsupported SheetMetal API')
  if not hasattr(bend,'native_sketch_inverse'):raise ValueError('BEND_FLAT_LINK: native sketch frame missing')
  edge=bend.line.transformed(bend.native_sketch_inverse).transformed(flat_matrix);p,q=[list(v.Point)[:2] for v in edge.Vertexes];dx=q[0]-p[0];dy=q[1]-p[1];length=math.hypot(dx,dy)
  if length<1e-7:raise ValueError('BEND_FLAT_LINK: degenerate native identifier line')
  def on_line(v):return abs((v[0]-p[0])*dy-(v[1]-p[1])*dx)/length<1e-5 and -1e-5<=((v[0]-p[0])*dx+(v[1]-p[1])*dy)/length<=length+1e-5
  fragments=[line for line in native_lines if all(on_line(v) for v in line)]
  if not fragments:raise ValueError('BEND_FLAT_LINK: identifier has no matching actual trimmed native fold line')
  out.append({'flat_line_mm':max(fragments,key=lambda line:math.dist(*line)),'flat_segments_mm':fragments,'source_formed_point_mm':bend.source_formed_point_mm,'source_formed_axis':bend.source_formed_axis,'angle_signed_deg':bend.angle,'direction':'UP' if bend.angle>0 else 'DOWN','radius_on_selected_skin_mm':bend.radius,'root_face':root_face,'root_skin_normal':list(root_normal),'direction_basis':'Native SheetMetal signed angle relative to selected root skin; not machine tooling or sequence approval'})
 out.sort(key=lambda b:(sum(p[0] for p in b['flat_line_mm'])/2,sum(p[1] for p in b['flat_line_mm'])/2,b['source_formed_point_mm']))
 for i,b in enumerate(out,1):b['id']='B'+str(i)
 validate_flat_link(native_lines,out)
 return out

def validate_flat_link(lines,labels):
 from corner03 import same_segment
 fragments=[line for b in labels for line in b.get('flat_segments_mm',[])]
 if len(fragments)!=len(lines) or any(sum(same_segment(*line,*candidate,1e-5) for candidate in fragments)!=1 for line in lines):raise ValueError('BEND_FLAT_LINK: identifiers do not uniquely cover all actual native fold segments')
 return True

def bend_note(label,ba):
 line=label['flat_line_mm'];axis='X' if abs(line[0][0]-line[1][0])<1e-5 else 'Y';idx=0 if axis=='X' else 1;center=sum(p[idx] for p in line)/2
 return label['id']+': '+axis+'='+format(center,'.9f')+'  zone +/-'+format(ba/2,'.9f')

def require_coverage(parts,views):
 expected={name for name,p in parts.items() if p['actual_bends']>0}
 if set(views)!=expected:raise ValueError('ISOMETRIC: every bent sheet needs its own actual formed view')
 for name in expected:
  p=parts[name];v=views[name];labels=v.get('bend_labels',[])
  if v.get('formed_sha256')!=p['formed_sha256'] or len(labels)!=p['actual_bends'] or {b.get('id') for b in labels}!={'B'+str(i) for i in range(1,p['actual_bends']+1)} or any(b.get('direction') not in ['UP','DOWN'] or not b.get('source_formed_point_mm') for b in labels):raise ValueError('ISOMETRIC: missing or stale formed binding/bend number/direction: '+name)
  validate_flat_link(p.get('native_fold_segments_mm',p.get('bend_lines',[])),labels)

def check_pdf(path,parts,views,projections):
 from corner03 import check_pdf_geometry
 from pypdf import PdfReader
 require_coverage(parts,views);reader=PdfReader(path);results={}
 for name,v in views.items():
  polylines=projections[name]['isometric'];segments=[(p,q) for poly in polylines for p,q in zip(poly,poly[1:])]
  result=check_pdf_geometry(path,v['page_index'],segments,v['pdf_map']);text=reader.pages[v['page_index']].extract_text()
  zh=v.get('language')=='zh'
  if ('斜视' not in text or v.get('display_name','') not in text) if zh else ('ISOMETRIC' not in text or name not in text):raise ValueError('ISOMETRIC: per-part view page missing')
  for b in v['bend_labels']:
   if b['id']+' '+({'UP':'上折','DOWN':'下折'}[b['direction']] if zh else b['direction']) not in text:raise ValueError('ISOMETRIC: bend number/direction not printed')
  # Read actual PDF text anchors so IDs cannot be present only in an unrelated table.
  anchors=[]
  def visit(text,cm,tm,font,size):
   anchors.append((text.strip(),[cm[0]*tm[4]+cm[2]*tm[5]+cm[4],cm[1]*tm[4]+cm[3]*tm[5]+cm[5]]))
  reader.pages[v['flat_page_index']].extract_text(visitor_text=visit)
  flattext=reader.pages[v['flat_page_index']].extract_text()
  for label in v['bend_labels']:
   expected=bend_note(label,v['BA_mm']).split('  zone')[0]
   if expected not in flattext:raise ValueError('BEND_FLAT_LINK: coordinate table uses different B numbering/axis')
  a,b,c,d,e,f=v['flat_map']
  for label in v['bend_labels']:
   mid=[sum(p[i] for p in label['flat_line_mm'])/2 for i in [0,1]];expected=[a*mid[0]+c*mid[1]+e+5,b*mid[0]+d*mid[1]+f+5]
   if not any(t==label['id']+' '+({'UP':'上折','DOWN':'下折'}[label['direction']] if zh else label['direction']) and math.dist(pos,expected)<=.05 for t,pos in anchors):raise ValueError('BEND_FLAT_LINK: actual PDF label is absent/moved from its native fold center')
  results[name]=result
 return results
