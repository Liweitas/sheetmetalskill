#!/usr/bin/env python3
"""Four 90-degree skirt03 arithmetic and actual planar/vector readback. No hidden design constants."""
import math,json,argparse,hashlib
from pathlib import Path

def profile(t,ri,skirt,seam,ba):
 values=[t,ri,skirt,seam,ba]
 if any(not isinstance(x,(int,float)) or isinstance(x,bool) or not math.isfinite(x) for x in values):raise ValueError('finite t,Ri,skirt,corner seam and BA required')
 if t<=0 or ri<=0 or skirt<=ri+t or not 0<=seam<ri or ba<=0:raise ValueError('unsupported03 range: positive t,Ri,BA; skirt>Ro; 0<=seam<Ri; use separate CAD design outside this adapter')
 ro=ri+t;A=skirt-ro;B=A+ba
 return {'Ro':ro,'A':A,'B':B,'short_skirt_retreat':t+seam,'P1':[B-ro,A],'P2':[B,B],'P3':[A,B-(ri-seam)]}

def spec(doc):
 from create_intake import apply_lid_defaults
 d=apply_lid_defaults(doc);v=lambda f:f['value'];lid=d['lid'];req=d['requirements'];b=d['bending']
 if v(req['lid_required']) is not True or v(lid['corner_scheme'])!='03':raise ValueError('applicable lid with scheme03 required')
 t=v(req['measured_t']) if v(req['measured_t']) is not None else v(req['nominal_t']);ri=v(b['Ri']);skirt=v(lid['skirt_height']);seam=v(lid['corner_gap']);g=v(lid['gap']);basis=v(lid['gap_basis'])
 if None in [t,ri,skirt,seam,g,basis]:raise ValueError('03 missing actual/candidate t,Ri,skirt,corner seam or clearance; no seam/Ri/q defaults')
 g=g/2 if basis=='total' else g
 if v(b['compensation_mode'])=='K_factor':
  k=v(b['K_value']);definition=v(b['K_definition'])
  if k is None or definition not in ['ANSI','DIN']:raise ValueError('K value/definition required')
  k=k/2 if definition=='DIN' else k;ba=math.pi/2*(ri+k*t)
 elif v(b['compensation_mode'])=='bend_deduction':
  bd=v(b['BD90'])
  if bd is None:raise ValueError('explicit90deg BD required')
  ba=2*(ri+t)-bd;k=(ba/(math.pi/2)-ri)/t
 else:raise ValueError('one compensation mode required')
 if not 0<=k<=1:raise ValueError('equivalent ANSI K outside supported range')
 if v(req['dimension_basis'])!='outer':raise ValueError('this adapter needs explicit body OUTER dimensions')
 L=v(req['dimensions'][v(req['length_axis'])]);W=v(req['dimensions'][v(req['width_axis'])]);H=v(req['dimensions'][v(req['height_axis'])])
 if any(x is None or x<=0 for x in [L,W,H]):raise ValueError('body outer dimensions and axes required')
 p=profile(t,ri,skirt,seam,ba);bd=2*(ri+t)-ba;flat=[L+2*(g+t)+2*skirt-2*bd,W+2*(g+t)+2*skirt-2*bd]
 if min(flat)<=2*p['B']:raise ValueError('corners overlap; unsupported dimensions')
 return dict(p,t=t,Ri=ri,skirt=skirt,corner_gap=seam,g_single=g,q=v(lid['roof_gap']),BA=ba,BD=bd,K_ANSI=k,body_outer=[L,W,H],flat_size=flat)

def expected_segments(s):
 out=[]
 for mx,my in [(False,False),(False,True),(True,False),(True,True)]:
  def tr(p):return [s['flat_size'][0]-p[0] if mx else p[0],s['flat_size'][1]-p[1] if my else p[1]]
  a,b,c=[tr(s[k]) for k in ['P1','P2','P3']];out.extend([(a,b),(b,c)])
 return out

def same_segment(a,b,c,d,tol):return min(max(math.dist(a,c),math.dist(b,d)),max(math.dist(a,d),math.dist(b,c)))<=tol

def check_dxf(path,s,tol=1e-5):
 from cut_dxf import parse_dxf
 from dxf_topology import validate_planar
 ents=parse_dxf(Path(path));indices=[i for i,e in enumerate(ents) if e['type']!='CIRCLE'];validate_planar(ents,indices)
 lines=[([float(e[10]),float(e[20])],[float(e[11]),float(e[21])]) for e in ents if e['type']=='LINE'];diags=[(a,b) for a,b in lines if abs(a[0]-b[0])>tol and abs(a[1]-b[1])>tol]
 expected=expected_segments(s)
 if len(diags)!=8:raise ValueError('claimed03 must have8 actual outer sloped segments; right-angle/20straight0sloped is not03')
 if any(not any(same_segment(a,b,c,d,tol) for c,d in diags) for a,b in expected):raise ValueError('03 slopes differ from current t,Ri,seam,BA calculation or unnormalized flat frame')
 xs=[x for a,b in lines for x in [a[0],b[0]]];ys=[y for a,b in lines for y in [a[1],b[1]]]
 if abs(min(xs))>tol or abs(min(ys))>tol or abs(max(xs)-s['flat_size'][0])>tol or abs(max(ys)-s['flat_size'][1])>tol:raise ValueError('DXF outer size/frame differs from computed flat extent')
 return {'actual_sloped_edges':8,'outer_lines':lines,'entities':ents,'numeric_tolerance_mm':tol}

def pdf_lines(path,page):
 from pypdf import PdfReader
 from pypdf.generic import ContentStream
 r=PdfReader(path);p=r.pages[page];M=[1,0,0,1,0,0];stack=[];pending=[];out=[];point=None;start=None
 def apply(a,b):return [M[0]*a+M[2]*b+M[4],M[1]*a+M[3]*b+M[5]]
 for operands,op in ContentStream(p.get_contents(),r).operations:
  n=[float(x) for x in operands] if op in [b'cm',b'm',b'l',b're'] else []
  if op==b'q':stack.append(M[:])
  elif op==b'Q':M=stack.pop()
  elif op==b'cm':
   a,b,c,d,e,f=n;A,B,C,D,E,F=M;M=[A*a+C*b,B*a+D*b,A*c+C*d,B*c+D*d,A*e+C*f+E,B*e+D*f+F]
  elif op==b'm':point=apply(*n);start=point
  elif op==b'l':
   new=apply(*n)
   if point is not None:pending.append((point,new))
   point=new
  elif op==b're':
   x,y,w,h=n;ps=[apply(x,y),apply(x+w,y),apply(x+w,y+h),apply(x,y+h)];pending.extend(zip(ps,ps[1:]+ps[:1]));point=ps[0];start=point
  elif op in [b'h',b's',b'b',b'b*']:
   if point is not None and start is not None:pending.append((point,start));point=start
  if op in [b'S',b's',b'B',b'B*',b'b',b'b*']:out.extend(pending);pending=[];point=None;start=None
  elif op in [b'n',b'f',b'f*']:pending=[];point=None;start=None
 return out

def check_pdf_geometry(path,page,lines,mapping,tol_points=.05):
 if len(mapping)!=6 or any(not math.isfinite(x) for x in mapping):raise ValueError('finite PDF flat mapping required')
 a,b,c,d,e,f=mapping;scale=math.hypot(a,b)
 if scale<=0 or abs(math.hypot(c,d)-scale)>1e-8 or abs(a*c+b*d)>1e-8:raise ValueError('PDF map must be a uniform similarity, not distorted geometry')
 transform=lambda p:[a*p[0]+c*p[1]+e,b*p[0]+d*p[1]+f];actual=pdf_lines(path,page)
 if any(not any(same_segment(transform(p),transform(q),u,v,tol_points) for u,v in actual) for p,q in lines):raise ValueError('PDF vector outline does not match actual unfolded DXF; raster/Form drawings require a separate verified CAD/PDF adapter and visual review')
 return {'matched_outline_segments':len(lines),'page_index':page,'numeric_tolerance_points':tol_points,'visual_review_still_required':True}

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('project');p.add_argument('--dxf');a=p.parse_args()
 try:
  s=spec(json.loads(Path(a.project).read_text()));result={'ok':True,'spec':s,'CAD_executed':False,'manufacturing_release':False}
  if a.dxf:result['DXF']=check_dxf(a.dxf,s);result['DXF'].pop('entities');result['DXF'].pop('outer_lines')
 except (ValueError,KeyError,TypeError,OSError) as ex:result={'ok':False,'error':str(ex),'CAD_executed':False,'manufacturing_release':False}
 print(json.dumps(result,ensure_ascii=False,indent=2));raise SystemExit(0 if result['ok'] else 2)
