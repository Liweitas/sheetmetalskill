"""Raster confirmation views from actual exported CAD triangulation; no imagined hardware."""
import json,math
from pathlib import Path
def previews(resolved,report,mesh,out,version):
 from PIL import Image,ImageDraw,ImageFont
 import numpy as np
 font=ImageFont.load_default(size=22);small=ImageFont.load_default(size=18)
 n=[1,-1,1];length=math.sqrt(3);n=[v/length for v in n];u=[1/math.sqrt(2),1/math.sqrt(2),0];v=[-1/math.sqrt(6),1/math.sqrt(6),2/math.sqrt(6)]
 dot=lambda a,b:sum(x*y for x,y in zip(a,b))
 colors={'U':(183,197,210),'L':(156,178,193),'END_L':(161,177,192),'END_R':(161,177,192),'LID':(188,212,226)}
 paths=[]
 for exploded in [False,True]:
  polygons=[];points=[]
  for name,p in mesh['parts'].items():
   delta=mesh['exploded_translations_mm'][name] if exploded else [0,0,0]
   xyz=[[x+dx for x,dx in zip(point,delta)] for point in p['vertices']]
   xy=[[dot(point,u),-dot(point,v)] for point in xyz];points.extend(xy)
   for triangle in p['triangles']:
    a,b,c=[xyz[i] for i in triangle];ab=[b[i]-a[i] for i in range(3)];ac=[c[i]-a[i] for i in range(3)];normal=[ab[1]*ac[2]-ab[2]*ac[1],ab[2]*ac[0]-ab[0]*ac[2],ab[0]*ac[1]-ab[1]*ac[0]];ln=math.sqrt(dot(normal,normal))
    shade=.4+.6*abs(dot(normal,[-.35,-.45,.82]))/ln if ln>1e-12 else .6
    color=tuple(round(q*shade) for q in colors.get(name,(170,190,205)));depth=sum(dot(xyz[i],n) for i in triangle)/3
    polygons.append(([dot(xyz[i],n) for i in triangle],[xy[i] for i in triangle],color))
  xmin=min(p[0] for p in points);xmax=max(p[0] for p in points);ymin=min(p[1] for p in points);ymax=max(p[1] for p in points)
  scale=min(1480/(xmax-xmin),760/(ymax-ymin));ox=120+(1480-scale*(xmax-xmin))/2-scale*xmin;oy=170+(760-scale*(ymax-ymin))/2-scale*ymin
  pixels=np.empty((1100,1800,3),dtype=np.uint8);pixels[:]=[246,247,248];zbuffer=np.full((1100,1800),-np.inf)
  for depths,poly,color in polygons:
   (x1,y1),(x2,y2),(x3,y3)=[(ox+scale*x,oy+scale*y) for x,y in poly]
   denom=(y2-y3)*(x1-x3)+(x3-x2)*(y1-y3)
   if abs(denom)<1e-10:continue
   left=max(0,math.floor(min(x1,x2,x3)));right=min(1799,math.ceil(max(x1,x2,x3)));top=max(0,math.floor(min(y1,y2,y3)));bottom=min(1099,math.ceil(max(y1,y2,y3)))
   if right<left or bottom<top:continue
   xx=np.arange(left,right+1)[None,:]+.5;yy=np.arange(top,bottom+1)[:,None]+.5
   a=((y2-y3)*(xx-x3)+(x3-x2)*(yy-y3))/denom;b=((y3-y1)*(xx-x3)+(x1-x3)*(yy-y3))/denom;c=1-a-b
   depth=a*depths[0]+b*depths[1]+c*depths[2];current=zbuffer[top:bottom+1,left:right+1]
   mask=(a>=-1e-9)&(b>=-1e-9)&(c>=-1e-9)&(depth>current+1e-8)
   current[mask]=depth[mask];pixels[top:bottom+1,left:right+1][mask]=color
  im=Image.fromarray(pixels);draw=ImageDraw.Draw(im)
  label='EXPLODED' if exploded else 'ASSEMBLED'
  draw.text((60,35),resolved['id']+' - '+label+' / GEOMETRY REVIEW - HOLD',font=font,fill='#162330')
  draw.text((60,78),('Actual imported STEP | source XYZ extents ' if report.get('source_review') else 'Actual STEP geometry | L/W/H ')+str([resolved[k] for k in ['L','W','H']])+' mm | t '+str(resolved['t'])+' mm | '+str(len(report['parts']))+' sheet parts',font=small,fill='#263745')
  draw.text((60,995),(resolved.get('review_notes',[None])[0] if resolved.get('review_notes') else 'Source parts preserved; explosion uses rigid translations only. Invalid BOP, unavailable flats and unknown process data remain HOLD.' if report.get('source_review') else 'No handle body invented; only declared mounting holes. Root interference, shop fit, tooling and first article remain HOLD.'),font=small,fill='#263745')
  draw.text((60,1035),(resolved['review_notes'][1] if len(resolved.get('review_notes',[]))>1 else 'Candidate review only; no production release. See actual STEP, per-part DXF and dimensioned PDF.'),font=small,fill='#263745')
  path=Path(out)/(resolved['id']+'_'+label+'_CONFIRMATION_'+version+'.png');im.save(path);paths.append(path)
 return paths
