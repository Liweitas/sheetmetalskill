from pathlib import Path
import math
def parse_dxf(path):
 lines=path.read_text(encoding='ascii').splitlines()
 if len(lines)%2:raise ValueError('odd DXF group-code lines')
 pairs=[(int(lines[i]),lines[i+1]) for i in range(0,len(lines),2)];inside=False;ents=[];cur=None
 if not any(pairs[i]==(9,'$INSUNITS') and pairs[i+1]==(70,'4') for i in range(len(pairs)-1)):raise ValueError('explicit mm INSUNITS=4 missing')
 for k,v in pairs:
  if k==2 and v=='ENTITIES':inside=True;continue
  if not inside:continue
  if k==0:
   if cur:ents.append(cur)
   if v=='ENDSEC':break
   if v not in ['LINE','ARC','CIRCLE']:raise ValueError('unsupported CUT entity '+v)
   cur={'type':v}
  elif cur is not None:cur[k]=v
 if (0,'EOF') not in pairs or not any(k==0 and v=='ENDSEC' for k,v in pairs[pairs.index((2,'ENTITIES'))+1:]):raise ValueError('incomplete DXF ENTITIES/EOF')
 if not ents:raise ValueError('empty CUT entities')
 signatures=[]
 for e in ents:
  if e.get(8)!='CUT':raise ValueError('only CUT layer permitted')
  if any(abs(float(e.get(k,0)))>1e-9 for k in [30,31]):raise ValueError('nonzero Z')
  normal=[float(e.get(k,default)) for k,default in [(210,0),(220,0),(230,1)]]
  if any(not math.isfinite(v) for v in normal) or any(abs(a-b)>1e-9 for a,b in zip(normal,[0,0,1])):raise ValueError('non-default/invalid extrusion direction; OCS conversion needs CAD adapter')
  thickness=float(e.get(39,0))
  if not math.isfinite(thickness) or abs(thickness)>1e-9:raise ValueError('nonzero/invalid entity thickness; planar CUT required')
  for k in [10,20]:float(e[k])
  if any(not math.isfinite(float(e[k])) for k in [10,20,11,21,30,31,40,50,51] if k in e):raise ValueError('nonfinite coordinate/size')
  if e['type']=='LINE':
   for k in [11,21]:float(e[k])
   pts=sorted([(round(float(e[k]),7),round(float(e[k+10]),7)) for k in [10,11]])
   if pts[0]==pts[1]:raise ValueError('zero-length line')
   sig=('LINE',tuple(pts))
  else:
   rad=float(e[40])
   if not math.isfinite(rad) or rad<=0:raise ValueError('invalid radius')
   sig=(e['type'],round(float(e[10]),7),round(float(e[20]),7),round(rad,7),round(float(e.get(50,0)),7),round(float(e.get(51,0)),7))
  if sig in signatures:raise ValueError('duplicate CUT entity')
  signatures.append(sig)
 return ents
