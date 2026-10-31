import json,copy,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
def fixture():return json.loads((ROOT/'assets/examples/synthetic-handle85-check.json').read_text())
def write_dxf(path,wide=85.0,narrow=59.0,row=27.0,D=5.2):
 pts=[(85-wide/2,30),(85+wide/2,30),(85-narrow/2,30+row),(85+narrow/2,30+row)]
 pairs=[(0,'SECTION'),(2,'HEADER'),(9,'$INSUNITS'),(70,4),(0,'ENDSEC'),(0,'SECTION'),(2,'ENTITIES')]
 border=[(0,0),(170,0),(170,90),(0,90)]
 for a,b in zip(border,border[1:]+border[:1]):pairs.extend([(0,'LINE'),(8,'CUT'),(10,a[0]),(20,a[1]),(11,b[0]),(21,b[1])])
 for x,y in pts:pairs.extend([(0,'CIRCLE'),(8,'CUT'),(10,x),(20,y),(40,D/2)])
 pairs.extend([(0,'ENDSEC'),(0,'EOF')]);path.write_text('\n'.join(str(v) for pair in pairs for v in pair)+'\n')
