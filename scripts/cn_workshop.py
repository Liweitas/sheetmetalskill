"""Chinese shop booklet from actual projections/unfolds; audit detail stays outside the booklet."""
import math,re,json
from pathlib import Path
CONTRACT='cn-workshop-dimensioned-v1'
ORDER=['U','L','END_L','END_R','LID']
NAMES={'U':'U形主体','L':'底侧L件','END_L':'左外端板','END_R':'右外端板','LID':'盒盖','ASSEMBLY':'装配','EXPLODED':'爆炸分件'}
DIR={'UP':'上折','DOWN':'下折'}
def fmt(x):return format(float(x),'.6f').rstrip('0').rstrip('.') or '0'
def point(p):return '('+','.join(fmt(v) for v in p)+')'
def no(owner,owners):return f'{[x for x in ORDER if x in owners].index(owner)+1:02d}'
def name(owner,owners):return ('件'+no(owner,owners)+' '+NAMES[owner]) if owner in owners else NAMES[owner]
def material(text):
 from material_code import normalize,ROOT
 policy=json.loads((ROOT/'assets/process/material-code-aliases-v1.json').read_text())
 for code,aliases in policy['aliases'].items():
  if isinstance(text,str) and normalize(text) in [normalize(a) for a in aliases]:return code+('碳钢' if code=='Q235' else '不锈钢')
 if isinstance(text,str) and re.fullmatch(r'[A-Za-z0-9_./-]+',text):return text
 return '牌号待核，原描述见参数报告'
def source_label(meta,key):
 row=next((x for x in (meta or {}).get('parameter_sources',[]) if x['parameter']==key),None)
 if not row:return '输入值，工厂复核'
 return {'user':'本款输入','experience_default':'默认','calculated':'计算候选','pending':'待核'}[row['origin']]
def header(project,r,report):
 t,ri,k=[r[x] for x in ['t','Ri','K_ANSI']];ba=math.pi/2*(ri+k*t);bd=2*(ri+t)-ba;meta=r.get('general_process');s=r['delivery']['sets']
 rows=[f'材料：{material(project["requirements"]["material"]["value"])}　板厚：{fmt(t)} mm　数量：{s}套',f'箱体外长×宽：{fmt(r["L"])}×{fmt(r["W"])} mm　'+('闭盖金属总高：' if r['lid_required'] else '裸盒总高：')+fmt(r['H'])+' mm',f'内圆角R{fmt(ri)}（{source_label(meta,"Ri")}）　中性层系数K={fmt(k)}（{source_label(meta,"K_ANSI")}；未标定值不得套机台）',f'90°弯曲补偿：{fmt(ba)} mm　折弯扣除：{fmt(bd)} mm（按本页R/K计算，不重复扣除）']
 if r['lid_required']:
  rows.append(f'盖裙：{fmt(r["skirt"])} mm（{source_label(meta,"lid.skirt_height")}）　单边间隙：{fmt(r["g"])} mm　顶隙：{fmt(r["q"])} mm（{source_label(meta,"lid.roof_gap")}）　03角缝：{fmt(r["corner_gap"])} mm（{source_label(meta,"lid.corner_gap")}）')
  rows.append(f'配合口径：盖内直壁比箱体外直壁长宽各大 {fmt(2*r["g"])} mm；不是盖外形差。')
  rows.append(f'按本款闭盖高计算箱体金属高：{fmt(r["H"]-t-r["q"])} mm；顶隙与板厚已计入。')
 rows.append('本款未建把手实体；有安装孔时只核孔型，配件活动包络未验。')
 if meta and 'CORNER_RELIEF_CANDIDATE_REQUIRES_CONFIRMATION' in meta['pending']:
  base=next(x['value'] for x in meta['parameter_sources'] if x['parameter']=='lid.corner_gap.original');rows.append('角部间隙为独立派生候选；原值'+fmt(base)+' mm保留，未经确认不得生产。')
 if r.get('site_fit_acceptance'):
  volume=report.get('root_interference_measurement',{}).get('authoritative_volume_mm3',0);rows.append('本款已授权现场修配；保留交叠'+fmt(volume)+' mm³，未消除，须试装。')
 rows.append('折序与靠边仅为几何候选；刀模、后挡料、回弹及首件须现场核实。')
 return rows

def check_first_page(path,project):
 from pypdf import PdfReader
 from validate_project import value
 from site_fit import acceptance_from_project
 norm=lambda s:re.sub(r'\s+','',s);text=norm(PdfReader(path).pages[0].extract_text())
 needles=['装配总图与工艺要点','本款未建把手实体；有安装孔时只核孔型，配件活动包络未验。']
 if value(project['requirements']['lid_required']):
  g=value(project['lid']['gap'])/(2 if value(project['lid']['gap_basis'])=='total' else 1);q=value(project['lid']['roof_gap'])
  needles += ['单边间隙：'+fmt(g)+' mm','顶隙：'+fmt(q)+' mm',f'配合口径：盖内直壁比箱体外直壁长宽各大 {fmt(2*g)} mm；不是盖外形差。']
 if acceptance_from_project(project):needles.append('本款已授权现场修配；保留交叠'+fmt(value(project['lid']['root_overlap_volume']))+' mm³，未消除，须试装。')
 if any(norm(s) not in text for s in needles):raise ValueError('CN_FIRST_PAGE_FIT_OR_AUTHORIZED_SITE_FIT_MISSING')
 return {'ok':True,'source_fit_summary_checked':True,'Chinese':True}

class Sheet:
 def __init__(self,path,revision):
  from reportlab.pdfgen.canvas import Canvas
  from reportlab.lib.pagesizes import A3,landscape
  from reportlab.pdfbase import pdfmetrics
  from reportlab.pdfbase.cidfonts import UnicodeCIDFont
  pdfmetrics.registerFont(UnicodeCIDFont('STSong-Light'));self.cv=Canvas(str(path),pagesize=landscape(A3));self.w,self.h=landscape(A3);self.page=0;self.revision=revision
 def text(self,x,y,s,size=10,color=(0,0,0)):
  self.cv.setFillColorRGB(*color);self.cv.setFont('STSong-Light',size);self.cv.drawString(x,y,str(s));self.cv.setFillColorRGB(0,0,0)
 def para(self,x,y,s,width,size=10):
  from reportlab.platypus import Paragraph
  from reportlab.lib.styles import ParagraphStyle
  from xml.sax.saxutils import escape
  p=Paragraph(escape(str(s)),ParagraphStyle('cn',fontName='STSong-Light',fontSize=size,leading=size+4,wordWrap='CJK'));_,h=p.wrap(width,self.h);p.drawOn(self.cv,x,y-h);return y-h-7
 def start(self,title):
  self.text(30,self.h-35,title,21);self.text(30,self.h-55,'图纸修订：'+self.revision+'　单位：mm　状态：确认/试折候选',10);self.cv.setStrokeColorRGB(.15,.3,.55);self.cv.line(30,self.h-64,self.w-30,self.h-64);self.cv.setStrokeColorRGB(0,0,0)
 def end(self):
  self.text(30,19,'尺寸数值优先，不按纸测量；刀模与后挡料未确认，不是机床程序。',9);self.text(self.w-85,19,'第'+str(self.page+1)+'页',9);self.cv.showPage();self.page+=1
 def label(self,owner,axis,value,x,y,kind,labels):
  self.text(x,y,fmt(value)+' mm',9);labels.append({'owner':owner,'axis':axis,'kind':kind,'page_index':self.page,'anchor':[x,y]})
 def segment(self,a,b,offset,label,owner,axis,kind,labels):
  cv=self.cv;dx=b[0]-a[0];dy=b[1]-a[1];ln=math.hypot(dx,dy)
  if ln<1e-8:return
  n=[-dy/ln,dx/ln];p=[a[i]+n[i]*offset for i in range(2)];q=[b[i]+n[i]*offset for i in range(2)];cv.setLineWidth(.3);cv.setStrokeColorRGB(.2,.25,.4)
  cv.line(*a,*p);cv.line(*b,*q);cv.line(*p,*q)
  for v in [p,q]:cv.line(v[0]-2,v[1]-2,v[0]+2,v[1]+2)
  x=(p[0]+q[0])/2+3;y=(p[1]+q[1])/2+3;self.label(owner,axis,label,x,y,kind,labels);cv.setStrokeColorRGB(0,0,0)
 def plot(self,lines,rect,title):
  cv=self.cv;x,y,w,h=rect;pts=[p for line in lines for p in line];x0=min(p[0] for p in pts);x1=max(p[0] for p in pts);y0=min(p[1] for p in pts);y1=max(p[1] for p in pts);sc=min((w-120)/max(x1-x0,1e-9),(h-95)/max(y1-y0,1e-9));ox=x+60-sc*x0+(w-120-sc*(x1-x0))/2;oy=y+42-sc*y0+(h-95-sc*(y1-y0))/2
  cv.setLineWidth(.5)
  for line in lines:
   for a,b in zip(line,line[1:]):cv.line(ox+sc*a[0],oy+sc*a[1],ox+sc*b[0],oy+sc*b[1])
  self.text(x+8,y+h-18,title,12);return [sc,0,0,sc,ox,oy],[ox+sc*x0,oy+sc*y0,ox+sc*x1,oy+sc*y1]
 def ortho(self,lines,rect,title,owner,axes,dims,labels):
  m,box=self.plot(lines,rect,title);l,b,r,t=box;cv=self.cv;cv.setLineWidth(.3);cv.line(l,b-12,r,b-12);cv.line(l-12,b,l-12,t)
  for x in [l,r]:cv.line(x,b-3,x,b-17)
  for y in [b,t]:cv.line(l-3,y,l-17,y)
  self.label(owner,axes[0],dims['XYZ'.index(axes[0])],(l+r)/2-22,b-27,'formed',labels);self.label(owner,axes[1],dims['XYZ'.index(axes[1])],l-57,(b+t)/2,'formed',labels);return m
 def iso(self,lines,rect,title,owner,bbox,labels):
  from formed_isometric import iso_point
  m,box=self.plot(lines,rect,title);x0,y0,z0,x1,y1,z1=bbox
  def tr(p):p=iso_point(p);return [m[0]*p[0]+m[4],m[3]*p[1]+m[5]]
  for axis,a,b,off in [('X',[x0,y0,z0],[x1,y0,z0],-19),('Y',[x0,y0,z0],[x0,y1,z0],19),('Z',[x1,y1,z0],[x1,y1,z1],-23)]:self.segment(tr(a),tr(b),off,math.dist(a,b),owner,axis,'formed',labels)
  return m

def write(project,r,report,projections,path,*unused):
 from formed_isometric import iso_point,check_pdf
 from workshop_pdf import process_data
 from pypdf import PdfReader
 parts=report['parts'];owners=list(parts);book=Sheet(path,project['project']['version']['value']);data=process_data(project,r,report);data.update(contract=CONTRACT,header=header(project,r,report),dimension_labels=[],part_pages={},flat_pages={},iso_views={},orthographic_views={},corner_detail=None);labels=data['dimension_labels'];iso_views={};flat_pages={}
 dims=lambda box:[box[i+3]-box[i] for i in range(3)]
 assembly=report.get('assembly_bbox')
 if assembly is None:
  boxes=[p['bbox'] for p in parts.values()];assembly=[min(b[i] for b in boxes) for i in range(3)]+[max(b[i] for b in boxes) for i in range(3,6)]
 book.start('装配总图与工艺要点');data['assembly_page']=book.page
 data['orthographic_views']['ASSEMBLY']={}
 for key,rect,axes,title in [('front',(30,430,550,325),'XZ','装配正视'),('right',(610,430,550,325),'YZ','装配右视'),('top',(30,60,550,325),'XY','装配俯视')]:
  om=book.ortho(projections['ASSEMBLY'][key],rect,title,'ASSEMBLY',axes,dims(assembly),labels);data['orthographic_views']['ASSEMBLY'][key]={'page_index':book.page,'map':om}
 y=385
 for i,line in enumerate(data['header']):y=book.para(620,y,line,520,14 if i==0 else 11)
 book.end();book.start('爆炸分件图：尺寸按真实成形件');data['exploded_page']=book.page;m,_=book.plot(projections['EXPLODED']['isometric'],(30,80,800,650),'分件位置');data['exploded_map']=m
 y=740
 for owner,p in parts.items():
  delta=report['exploded_translations_mm'][owner];bb=p['bbox'];mid=[(bb[i]+bb[i+3])/2+delta[i] for i in range(3)];pt=iso_point(mid);pt=[m[0]*pt[0]+m[4],m[3]*pt[1]+m[5]];book.cv.line(*pt,850,y-7);book.text(855,y,name(owner,owners)+'　数量'+str(r['delivery']['sets']),13)
  for i,axis in enumerate('XYZ'):book.text(855,y-25-i*18,axis+'向成形：',10);book.label(owner,axis,dims(bb)[i],940,y-25-i*18,'formed',labels)
  y-=125
 book.text(50,60,'爆炸移位仅用于区分零件；产品总外形见装配页。',11);book.end()
 for owner,p in parts.items():
  bb=p['bbox'];dd=dims(bb);book.start(name(owner,owners)+'：成形三视与斜视');data['part_pages'][owner]=book.page;data['orthographic_views'][owner]={};book.text(40,765,'材料 '+material(project['requirements']['material']['value'])+'　板厚 '+fmt(r['t'])+' mm　R'+fmt(r['Ri'])+'　数量 '+str(r['delivery']['sets']),12)
  for key,rect,axes,title in [('front',(30,430,550,325),'XZ','正视'),('right',(610,430,550,325),'YZ','右视'),('top',(30,60,550,325),'XY','俯视')]:
   om=book.ortho(projections[owner][key],rect,title,owner,axes,dd,labels);data['orthographic_views'][owner][key]={'page_index':book.page,'map':om}
  im=book.iso(projections[owner]['isometric'],(610,60,550,325),'斜视：标注成形尺寸',owner,bb,labels);data['iso_views'][owner]={'page_index':book.page,'map':im};bends=p.get('bend_records',[])
  if bends:
   iso_views[owner]={'language':'zh','display_name':name(owner,owners),'page_index':book.page,'pdf_map':im,'formed_sha256':p['formed_sha256'],'bend_labels':bends}
   for b in bends:
    v=iso_point(b['source_formed_point_mm']);x=im[0]*v[0]+im[4];y=im[3]*v[1]+im[5];book.cv.circle(x,y,2,stroke=1,fill=0);book.text(x+6,y+7,b['id'],9,(.1,.25,.65))
   book.text(625,48,'　'.join(b['id']+' '+DIR[b['direction']] for b in bends),9)
  else:data['zero_bend_isometric'][owner]={'page_index':book.page,'map':im}
  book.end();book.start(name(owner,owners)+'：展开与折弯作业');fw,fh=p['flat_size_mm'];sc=min(650/fw,475/fh);ox=65;oy=230;fm=[sc,0,0,sc,ox,oy];cv=book.cv
  for e in p['records']:
   if e['type']=='LINE':cv.line(ox+sc*e['p'][0],oy+sc*e['p'][1],ox+sc*e['q'][0],oy+sc*e['q'][1])
   elif e['type']=='CIRCLE':cv.circle(ox+sc*e['center'][0],oy+sc*e['center'][1],sc*e['radius'],stroke=1,fill=0)
   else:
    x,y=e['center'];rad=e['radius'];cv.arc(ox+sc*(x-rad),oy+sc*(y-rad),ox+sc*(x+rad),oy+sc*(y+rad),startAng=e['start'],extent=(e['end']-e['start'])%360)
  cv.setDash(4,3);cv.setStrokeColorRGB(.1,.3,.7)
  for line in p['bend_lines']:cv.line(ox+sc*line[0][0],oy+sc*line[0][1],ox+sc*line[1][0],oy+sc*line[1][1])
  cv.setDash();cv.setStrokeColorRGB(0,0,0);book.text(ox,oy-18,'展开原点（0,0）',10)
  book.segment([ox,oy],[ox+sc*fw,oy],-34,fw,owner,'X','flat',labels);book.segment([ox,oy],[ox,oy+sc*fh],42,fh,owner,'Y','flat',labels)
  for b in bends:
   mid=[sum(v[i] for v in b['flat_line_mm'])/2 for i in [0,1]];book.text(ox+sc*mid[0]+5,oy+sc*mid[1]+5,b['id']+' '+DIR[b['direction']],9,(.1,.25,.65))
  flat_pages[owner]={'page_index':book.page,'flat_map':fm};data['flat_pages'][owner]=flat_pages[owner]
  ba=math.pi/2*(r['Ri']+r['K_ANSI']*r['t'])
  if owner in iso_views:iso_views[owner].update(flat_page_index=book.page,flat_map=fm,BA_mm=ba)
  y=755;book.text(765,y,'板厚 '+fmt(r['t'])+' mm　R'+fmt(r['Ri'])+'　数量'+str(r['delivery']['sets']),15);y-=30
  if owner=='LID':y=book.para(765,y,'盖裙外高 '+fmt(r['skirt'])+' mm（'+source_label(r.get('general_process'),'lid.skirt_height')+'）；03角缝 '+fmt(r['corner_gap'])+' mm。',385,12)
  y=book.para(765,y,'位置以展开左下角为基准。方向按原生基准皮层；翻面与折序须首件确认。',385,10)
  if not bends:y=book.para(765,y,'本件不折弯；禁止增加折弯工序。',385,13)
  for row in data['parts'][owner]['bend_rows']:
   b=next(b for b in bends if b['id']==row['id']);line=b['flat_line_mm'];axis='X' if abs(line[0][0]-line[1][0])<1e-5 else 'Y';ix=0 if axis=='X' else 1;center=sum(v[ix] for v in line)/2
   y=book.para(765,y,f'折序候选{row["sequence_candidate"]}　{b["id"]} {DIR[b["direction"]]} {fmt(abs(b["angle_signed_deg"]))}°　R{fmt(r["Ri"])}',385,13)
   y=book.para(765,y,b['id']+': '+axis+'='+format(center,'.9f')+'；折线端点 '+point(line[0])+' → '+point(line[1]),385,10)
   datum=row['datum']
   if datum['kind']=='actual_outer_straight_edge_candidate':
    edge=datum['edge_mm'];y=book.para(765,y,'靠边候选：边'+str(datum['DXF_entity_index'])+'，距折线 '+fmt(datum['distance_to_bend_center_mm'])+' mm；不是机床后挡料。',385,10);cv.setStrokeColorRGB(.1,.5,.25);cv.setLineWidth(1.5);cv.line(ox+sc*edge[0][0],oy+sc*edge[0][1],ox+sc*edge[1][0],oy+sc*edge[1][1]);cv.setLineWidth(.5);cv.setStrokeColorRGB(0,0,0)
   else:y=book.para(765,y,'靠边未确认；只给展开坐标，不填写机床后挡料。',385,10)
  y=book.para(765,y,'机台______　上模______　下模______\n后挡料______　回弹补偿______　首件确认______',385,11)
  circles=[e for e in p['records'] if e['type']=='CIRCLE']
  if circles:book.text(555,205,'孔径及展开坐标见后页',10)
  if owner=='LID':
   from corner03 import profile
   cp=profile(r['t'],r['Ri'],r['skirt'],r['corner_gap'],ba);lo=cp['A']-2*cp['Ro'];hi=cp['B']+cp['Ro'];zoom=125/(hi-lo);tx=75-zoom*lo;ty=50-zoom*lo;cv.saveState();clip=cv.beginPath();clip.rect(65,45,150,135);cv.clipPath(clip,stroke=0,fill=0)
   for e in p['records']:
    if e['type']=='LINE':cv.line(tx+zoom*e['p'][0],ty+zoom*e['p'][1],tx+zoom*e['q'][0],ty+zoom*e['q'][1])
   cv.restoreState();book.text(235,166,'03角局部：坐标按展开原点',11);pts=[]
   vertices=[q for e in p['records'] if e['type']=='LINE' for q in [e['p'],e['q']]]
   for i,key in enumerate(['P1','P2','P3'],1):
    v=min(vertices,key=lambda v:math.dist(v,cp[key]));
    if math.dist(v,cp[key])>1e-5:raise ValueError('CN_CORNER_POINT_NOT_ACTUAL_DXF')
    pts.append(v);book.text(tx+zoom*v[0]+3,ty+zoom*v[1]+3,str(i),9);book.text(235,145-20*(i-1),'点'+str(i)+'：'+point(v)+' mm',10)
   data['corner_detail']={'page_index':book.page,'points':pts,'text_anchors':[[235,145-20*i] for i in range(3)]}
  book.end()
  for start in range(0,len(circles),22):
   book.start(name(owner,owners)+'：展开孔位表');book.text(40,740,'展开原点为左下角；孔径与坐标均为mm。攻丝/沉座不得混作激光孔径。',12)
   for j,e in enumerate(circles[start:start+22]):book.text(45,705-j*27,'孔'+str(start+j+1)+'　直径'+fmt(2*e['radius'])+'　X='+fmt(e['center'][0])+'　Y='+fmt(e['center'][1]),12)
   book.end()
 book.cv.save();data['total_pages']=len(PdfReader(path).pages)
 evidence=Path(path).parents[1]/'evidence'/('PROCESS_PDF_'+project['project']['version']['value']+'.json');evidence.write_text(json.dumps(data,ensure_ascii=False,indent=2));checked=check_pdf(path,parts,iso_views,projections)
 result={'total_pages':data['total_pages'],'part_flat_pages':flat_pages,'formed_isometric_views':iso_views,'isometric_vector_checks':checked,'workshop_pdf_contract':CONTRACT}
 if 'LID' in flat_pages:result.update(pdf_flat_page_index=flat_pages['LID']['page_index'],pdf_flat_map=flat_pages['LID']['flat_map'])
 return result

def check_process(path,project,report,d,version,spec,resolved):
 from pypdf import PdfReader
 from workshop_pdf import process_data
 if spec.get('contract')!=CONTRACT:raise ValueError('CN_WORKSHOP_CONTRACT_REQUIRED')
 texts=[p.extract_text() for p in PdfReader(path).pages];norm=lambda x:re.sub(r'\s+','',x);alltext=''.join(norm(t) for t in texts)
 expected=header(project,{**resolved,'delivery':d},report)
 if spec['header']!=expected or any(norm(line) not in norm(texts[0]) for line in expected):raise ValueError('CN_WORKSHOP_SOURCE_HEADER_MISMATCH')
 if any(norm('图纸修订：'+version) not in norm(t) for t in texts):raise ValueError('CN_WORKSHOP_REVISION_MISMATCH')
 allowed={'STEP','DXF','PDF'}
 for t in texts:
  words=set(re.findall(r'\b[A-Za-z]{3,}\b',t))
  if words-allowed:raise ValueError('CN_WORKSHOP_ENGLISH_EXPLANATION: '+','.join(sorted(words-allowed)))
 expected_parts=process_data(project,{**resolved,'delivery':d},report)['parts']
 if spec['parts']!=expected_parts:raise ValueError('CN_WORKSHOP_NATIVE_PROCESS_ROWS')
 for owner,data in expected_parts.items():
  for row in data['bend_rows']:
   signed=row['angle_signed_deg'];direction=DIR[row['direction']];needle=f'折序候选{row["sequence_candidate"]}　{row["id"]} {direction} {fmt(abs(signed))}°　R{fmt(resolved["Ri"])}'
   if norm(needle) not in alltext:raise ValueError('CN_WORKSHOP_BEND_DIRECTION_ANGLE_SEQUENCE_MISSING')
   b=next(b for b in report['parts'][owner]['bend_records'] if b['id']==row['id']);axis='X' if abs(b['flat_line_mm'][0][0]-b['flat_line_mm'][1][0])<1e-5 else 'Y';idx=0 if axis=='X' else 1;center=sum(p[idx] for p in b['flat_line_mm'])/2;needle=b['id']+': '+axis+'='+format(center,'.9f')
   if norm(needle) not in alltext:raise ValueError('CN_WORKSHOP_BEND_COORDINATE_MISSING')
 if set(spec['part_pages'])!=set(expected_parts) or set(spec['flat_pages'])!=set(expected_parts) or set(spec['iso_views'])!=set(expected_parts):raise ValueError('CN_WORKSHOP_ALL_PART_VIEWS_REQUIRED')
 return {'ok':True,'Chinese_explanations':True,'source_header_and_native_bend_tables':True,'production_release':False}

def check_dimensions(path,project,manifest,root,actual):
 from pypdf import PdfReader
 from collections import Counter
 from corner03 import check_pdf_geometry,profile
 root=Path(root);spec_path=next(a['path'] for a in manifest['artifacts'] if a['kind']=='delivery_spec');spec=json.loads((root/spec_path).read_text())['process_pdf'];reader=PdfReader(path);anchors=[]
 for page in reader.pages:
  items=[]
  def visit(text,cm,tm,font,size):items.append((text.strip(),[cm[0]*tm[4]+cm[2]*tm[5]+cm[4],cm[1]*tm[4]+cm[3]*tm[5]+cm[5]],size))
  page.extract_text(visitor_text=visit);anchors.append(items)
 owners={p['id'] for p in project['fabrication']['parts']};want=Counter()
 for owner in owners:
  for axis in 'XYZ':want[(owner,'formed',spec['part_pages'][owner],axis)]=3;want[(owner,'formed',spec['exploded_page'],axis)]=1
  for axis in 'XY':want[(owner,'flat',spec['flat_pages'][owner]['page_index'],axis)]=1
 for axis in 'XYZ':want[('ASSEMBLY','formed',spec['assembly_page'],axis)]=2
 got=Counter((x['owner'],x['kind'],x['page_index'],x['axis']) for x in spec['dimension_labels'])
 if got!=want:raise ValueError('CN_DIMENSION_ALL_VIEWS_COVERAGE_OR_EXPLODED_DIMENSION_BASIS')
 def present(page,text,at):return any(t==text and math.dist(pos,at)<=.08 and size>=8 for t,pos,size in anchors[page])
 for x in spec['dimension_labels']:
  key=x['owner'] if x['kind']=='formed' else 'FLAT:'+x['owner'];box=actual['shapes'][key]['bbox_mm'];i='XYZ'.index(x['axis']);value=box[i+3]-box[i]
  if not present(x['page_index'],fmt(value)+' mm',x['anchor']):raise ValueError('CN_ACTUAL_STEP_DIMENSION_LABEL_MISMATCH: '+key+'/'+x['axis'])
 checked={}
 for owner,views in spec['orthographic_views'].items():
  for label,v in views.items():
   lines=actual['shapes'][owner]['orthographic_lines_mm'][label];segments=[(a,b) for line in lines for a,b in zip(line,line[1:])];check_pdf_geometry(path,v['page_index'],segments,v['map'])
 for owner,v in spec['iso_views'].items():
  lines=actual['shapes'][owner]['isometric_lines_mm'];segments=[(a,b) for line in lines for a,b in zip(line,line[1:])];checked[owner]=check_pdf_geometry(path,v['page_index'],segments,v['map'])
 lines=actual['shapes']['EXPLODED']['isometric_lines_mm'];check_pdf_geometry(path,spec['exploded_page'],[(a,b) for line in lines for a,b in zip(line,line[1:])],spec['exploded_map'])
 t=project['requirements']['nominal_t']['value']
 for owner in owners:
  b=actual['shapes']['FLAT:'+owner]['bbox_mm']
  if abs(b[5]-b[2]-t)>1e-5:raise ValueError('CN_ACTUAL_FLAT_THICKNESS')
 if spec.get('corner_detail'):
  from design_job import resolve_job
  job=json.loads((root/next(a['path'] for a in manifest['artifacts'] if a['kind']=='source_job')).read_text());r=resolve_job(job);ba=math.pi/2*(r['Ri']+r['K_ANSI']*r['t']);cp=profile(r['t'],r['Ri'],r['skirt'],r['corner_gap'],ba);v=spec['corner_detail'];vertices=actual['shapes']['FLAT:LID']['vertices_mm']
  for i,key in enumerate(['P1','P2','P3']):
   vertex=min(vertices,key=lambda p:math.dist(p[:2],cp[key]))
   if math.dist(vertex[:2],cp[key])>1e-5 or math.dist(v['points'][i],vertex[:2])>1e-5 or not present(v['page_index'],'点'+str(i+1)+'：'+point(v['points'][i])+' mm',v['text_anchors'][i]):raise ValueError('CN_CORNER_ACTUAL_DIMENSION_MISMATCH')
 return {'ok':True,'dimension_label_count':len(spec['dimension_labels']),'orthographic_isometric_exploded_vectors_from_fresh_STEP':True,'exploded_displacement_in_product_dimensions':False,'scope':'actual formed/flat STEP extents and true part dimensions, not receipt dimensions','isometric_checks':checked}
