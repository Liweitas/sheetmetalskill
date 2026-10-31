#!/usr/bin/env python3
"""Check a scoped hole-only revision with bound external CAD witness; never generates that witness."""
import json,argparse,hashlib,math
from pathlib import Path
def changed_values(a,b,path=''):
 if isinstance(a,dict) and isinstance(b,dict):
  if 'value'in a and 'value'in b:return [] if a['value']==b['value'] else [path]
  return [q for k in sorted(set(a)|set(b)) for q in changed_values(a.get(k),b.get(k),path+'/'+k)]
 if isinstance(a,list) and isinstance(b,list) and len(a)==len(b):return [q for i,(x,y) in enumerate(zip(a,b)) for q in changed_values(x,y,path+'/'+str(i))]
 return [] if a==b else [path]
def invalidations(before,after):
 paths=changed_values(before,after)
 if any(p.startswith('/requirements/material') or p.startswith('/requirements/nominal_t') or p.startswith('/requirements/measured_t') for p in paths):return {'changed':paths,'invalidate':['formed_geometry_if_t_changed','unfold','CUT','Ri_and_compensation_calibration','hardware_qualification','first_article','assembly_checks','PDF','manifest'],'reuse':'only geometrically unchanged data with current evidence; old material calibration not valid'}
 return {'changed':paths,'invalidate':['changed feature/part and its dependent unfold,CUT,axes,views,PDF,manifest'],'reuse':'unaffected parts may be byte-identical; scoped CAD witness still required'}
def verify_revision(before,after,witness,root,allowed_holes):
 errors=[];root=Path(root).resolve();allowed=set(allowed_holes);bp=before.get('parts',{});ap=after.get('parts',{});bound_before={};bound_after={}
 def finite(n):return isinstance(n,(int,float)) and not isinstance(n,bool) and math.isfinite(n)
 def vec(v,n):return isinstance(v,list) and len(v)==n and all(finite(q) for q in v)
 def valid_parts(parts,label):
  if not isinstance(parts,dict) or not parts:errors.append('EMPTY_OR_INVALID_PARTS:'+label);return
  for pid,part in parts.items():
   if not isinstance(part,dict):errors.append('INVALID_PART:'+label+':'+str(pid));continue
   box=part.get('bbox_mm')
   if not vec(box,6) or any(box[i]>=box[i+3] for i in range(3)):errors.append('INVALID_BBOX:'+label+':'+pid)
   if not finite(part.get('volume_mm3')) or part['volume_mm3']<=0:errors.append('MISSING_VALID_VOLUME:'+label+':'+pid)
   holes=part.get('holes')
   if not isinstance(holes,dict):errors.append('MISSING_HOLE_RECORDS:'+label+':'+pid);continue
   for hid,h in holes.items():
    if not isinstance(h,dict) or not vec(h.get('center'),3) or not vec(h.get('axis'),3) or abs(sum(q*q for q in h['axis'])-1)>1e-6 or not finite(h.get('diameter_mm')) or h['diameter_mm']<=0 or not finite(h.get('local_t_mm')) or h['local_t_mm']<=0 or h.get('kind')!='through_circle':errors.append('INVALID_HOLE_RECORD:'+label+':'+pid+':'+str(hid))
 valid_parts(bp,'baseline');valid_parts(ap,'candidate')
 if errors:return {'ok':False,'errors':errors,'CAD_computed_by_this_script':False,'certifies_manufacture':False}
 existing={pid+':'+hid for pid,p in bp.items() for hid in p['holes']}
 if not allowed<=existing:errors.append('UNKNOWN_ALLOWED_HOLE')
 if set(bp)!=set(ap):errors.append('PART_SET_CHANGED')
 if not allowed or witness.get('method')!='CAD_symmetric_difference_outside_edit_regions' or not witness.get('evidence_ref'):errors.append('MISSING_CAD_WITNESS_OR_SCOPE')
 if set(witness.get('allowed_holes',[]))!=allowed:errors.append('WITNESS_SCOPE_MISMATCH')
 for pid in sorted(set(bp)&set(ap)):
  x=bp[pid];y=ap[pid]
  for side,part in [('baseline',x),('candidate',y)]:
   if not isinstance(part.get('volume_mm3'),(int,float)) or isinstance(part.get('volume_mm3'),bool) or not math.isfinite(part.get('volume_mm3',float('nan'))) or part['volume_mm3']<=0:errors.append('MISSING_VALID_VOLUME:'+side+':'+pid)
   if not isinstance(part.get('holes'),dict):errors.append('MISSING_HOLE_RECORDS:'+side+':'+pid)
   for hid,h in part.get('holes',{}).items():
    if any(k not in h for k in ['center','axis','diameter_mm','kind','local_t_mm']):errors.append('MISSING_HOLE_FIELDS:'+pid+':'+hid)
  if any('MISSING' in e for e in errors):continue
  for side,part,bound in [('baseline',x,bound_before),('candidate',y,bound_after)]:
   try:
    p=(root/part['file']).resolve()
    if not p.is_relative_to(root):raise ValueError('path escapes root')
    h=hashlib.sha256(p.read_bytes()).hexdigest();bound[pid]=h
    if h!=part['sha256']:errors.append(side+':STALE_PART_HASH:'+pid)
   except (KeyError,OSError,ValueError) as ex:errors.append(side+':FILE:'+pid+':'+str(ex))
  hx=x.get('holes',{});hy=y.get('holes',{})
  if set(hx)!=set(hy):errors.append('HOLE_SET_CHANGED:'+pid)
  changed=[]
  for hid in set(hx)&set(hy):
   if hx[hid]!=hy[hid]:
    key=pid+':'+hid
    if key not in allowed:errors.append('UNAUTHORIZED_HOLE_CHANGE:'+key)
    changed.append(hid)
  if any(abs(a-b)>1e-7 for a,b in zip(x.get('bbox_mm',[]),y.get('bbox_mm',[]))) or len(x.get('bbox_mm',[]))!=6 or len(y.get('bbox_mm',[]))!=6:errors.append('OUTER_DIMENSION_CHANGED:'+pid)
  if not changed:
   if x.get('sha256')!=y.get('sha256'):errors.append('UNAFFECTED_PART_BYTES_CHANGED:'+pid)
  else:
   residual=witness.get('outside_edit_regions_symmetric_difference_mm3',{}).get(pid)
   if not isinstance(residual,(int,float)) or isinstance(residual,bool) or not math.isfinite(residual) or residual<0 or residual>1e-6:errors.append('OUTSIDE_GEOMETRY_CHANGED_OR_UNPROVED:'+pid)
   expected=0;canpredict=True
   for hid in changed:
    h0=hx[hid];h1=hy[hid]
    if h0.get('kind')!='through_circle' or h1.get('kind')!='through_circle' or h0.get('local_t_mm')!=h1.get('local_t_mm') or h0.get('axis')!=h1.get('axis'):canpredict=False;errors.append('UNSUPPORTED_NARROW_FEATURE:'+pid+':'+hid);continue
    expected-=math.pi/4*(h1['diameter_mm']**2-h0['diameter_mm']**2)*h0['local_t_mm']
   if canpredict and abs((y.get('volume_mm3',0)-x.get('volume_mm3',0))-expected)>1e-6:errors.append('UNEXPLAINED_VOLUME_CHANGE:'+pid)
 if witness.get('baseline_parts_sha256')!=bound_before or witness.get('candidate_parts_sha256')!=bound_after:errors.append('CAD_WITNESS_INPUT_HASH_MISMATCH')
 return {'ok':not errors,'errors':errors,'scope':'file hashes + unchanged hole/dimension records + external CAD-witness input binding + simple through-hole volume change','CAD_computed_by_this_script':False,'certifies_manufacture':False,'witness_required':'actual CAD outside-edit-region comparison must be performed separately; a claimed report is not independently recomputed here'}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('before');p.add_argument('after');p.add_argument('--witness');p.add_argument('--root');p.add_argument('--allow-hole',action='append',default=[]);p.add_argument('--plan',action='store_true');a=p.parse_args();b=json.loads(Path(a.before).read_text());c=json.loads(Path(a.after).read_text())
 if a.plan:out=invalidations(b,c)
 else:
  if not a.witness or not a.root:p.error('--witness and --root required for revision verification')
  out=verify_revision(b,c,json.loads(Path(a.witness).read_text()),a.root,a.allow_hole)
 print(json.dumps(out,ensure_ascii=False,indent=2));raise SystemExit(0 if out.get('ok',True) else 2)
