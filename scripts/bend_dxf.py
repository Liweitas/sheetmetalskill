"""BEND-only native fold fragments. Never mix these into the laser CUT layer."""
import math
from pathlib import Path
def write(path,segments):
 pairs=[(0,'SECTION'),(2,'HEADER'),(9,'$INSUNITS'),(70,4),(0,'ENDSEC'),(0,'SECTION'),(2,'ENTITIES')]
 for a,b in segments:pairs += [(0,'LINE'),(8,'BEND'),(10,format(a[0],'.12f')),(20,format(a[1],'.12f')),(11,format(b[0],'.12f')),(21,format(b[1],'.12f'))]
 pairs += [(0,'ENDSEC'),(0,'EOF')];Path(path).write_text('\n'.join(str(x) for pair in pairs for x in pair)+'\n',encoding='ascii');read(path)
def read(path):
 lines=Path(path).read_text(encoding='ascii').splitlines()
 if len(lines)%2:raise ValueError('BEND_DXF_INVALID_PAIR')
 pairs=[(int(lines[i].strip()),lines[i+1].strip()) for i in range(0,len(lines),2)]
 if not any(k==9 and v=='$INSUNITS' and pairs[i+1]==(70,'4') for i,(k,v) in enumerate(pairs[:-1])):raise ValueError('BEND_DXF_MM_UNITS_REQUIRED')
 inside=False;records=[];record=None
 for i,(code,value) in enumerate(pairs):
  if code==0 and value=='SECTION':inside=i+1<len(pairs) and pairs[i+1]==(2,'ENTITIES')
  if code==0 and inside:
   if record:records.append(record);record=None
   if value=='ENDSEC':inside=False
   elif value!='SECTION':
    if value!='LINE':raise ValueError('BEND_DXF_LINE_ONLY')
    record={}
  elif inside and record is not None:record[code]=value
 result=[]
 for r in records:
  if r.get(8)!='BEND' or any(float(r.get(k,0))!=0 for k in [30,31]):raise ValueError('BEND_DXF_CLEAN_LAYER_Z')
  a=[float(r[k]) for k in [10,20]];b=[float(r[k]) for k in [11,21]]
  if not all(math.isfinite(x) for x in a+b) or math.dist(a,b)<1e-7:raise ValueError('BEND_DXF_BAD_SEGMENT')
  result.append([a,b])
 if not result:raise ValueError('BEND_DXF_EMPTY_FOR_BENT_PART')
 return result
def compare(path,expected):
 from native_direction_readback import segments_equal
 actual=read(path)
 if len(actual)!=len(expected) or any(sum(segments_equal(a,b) for a in actual)!=1 for b in expected):raise ValueError('BEND_DXF_ACTUAL_NATIVE_FRAGMENT_MISMATCH')
 return {'ok':True,'actual_native_segments':len(expected),'units':'mm','layer':'BEND','laser_CUT_contains_no_fold_lines':True}
def check_manifest(root,manifest,native):
 root=Path(root);found={a['part_ids'][0]:a for a in manifest['artifacts'] if a['kind']=='bend_dxf'};checks={}
 for part in native['checks']:
  owner=part['part_id']
  if owner not in found:raise ValueError('BEND_DXF_MISSING_PART: '+owner)
  expected=[s for b in part['native_bends'] for s in b['segments']];checks[owner]=compare(root/found[owner]['path'],expected)
 if set(found)!=set(checks):raise ValueError('BEND_DXF_FALSE_ZERO_BEND_PART_OR_DUPLICATE')
 if len([a for a in manifest['artifacts'] if a['kind']=='bend_dxf'])!=len(found):raise ValueError('BEND_DXF_DUPLICATE_PART')
 return checks
