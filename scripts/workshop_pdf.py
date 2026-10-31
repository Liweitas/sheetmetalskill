"""Workshop-facing summary and actual native bend/datum records; never guessed machine programs."""
import io,json,math,re
from pathlib import Path
def header_lines(project,resolved):
 from validate_project import value
 d=resolved['delivery'];r=project['requirements'];b=project['bending'];v=value(project['project']['version']);t=value(r['nominal_t']);ri=value(b['Ri']);k=value(b['K_value']);ba=math.pi/2*(ri+k*t);bd=2*(ri+t)-ba
 parts=', '.join(p['id']+' x'+str(d['sets']) for p in project['fabrication']['parts'])
 lines=[f'ID={d["namespace"]}_{d["entity_id"]} | REV={d["revision"]} | VERSION={v}',f'MATERIAL={value(r["material"])} | t={t}mm | STATUS=REVIEW_TRIAL_HOLD | production_release=false',f'尺寸口径：体外长宽 {resolved["L"]} x {resolved["W"]} mm；总高 {resolved["H"]} mm；'+('含盖金属总高，不含未建模把手' if resolved['lid_required'] else '无盖裸盒高'), '钣金件与数量：'+parts+'；未列五金实体不代表无需采购。',f'Ri={ri}mm / ANSI K={k}；BA90={ba:.6f}mm / BD90={bd:.6f}mm（理论补偿，不重复扣除）',f'Ri来源状态={b["Ri"]["status"]}；K来源状态={b["K_value"]["status"]}；材料来源状态={r["material"]["status"]}；详见同版参数provenance。',f'板材候选 {d["stock"]["length_mm"]} x {d["stock"]["width_mm"]}mm；状态 {d["stock"]["status"]}；{d["sets"]}套，实际需板数见集中套料预览。','试折：核实际材质/板厚、刀模、V槽、Ri、回弹、BG与折序/退刀；未知参数不编成可直接执行机床程序。']
 if resolved.get('general_process'):
  from general_sources import STAGE
  meta=resolved['general_process'];lines=['GENERAL_CONTRACT='+meta['contract']+' | DELIVERY_GRADE='+meta['effective_stage'],STAGE[meta['effective_stage']]]+lines
 return lines

def datum_for(part,bend):
 a,b=bend['flat_line_mm'];dx=b[0]-a[0];dy=b[1]-a[1];ln=math.hypot(dx,dy)
 if ln<1e-8:raise ValueError('Bend baseline has zero length')
 candidates=[];center=[(a[i]+b[i])/2 for i in [0,1]]
 for i in part['outer_boundary_entity_indices']:
  e=part['records'][i]
  if e['type']!='LINE':continue
  p,q=e['p'],e['q'];ux=q[0]-p[0];uy=q[1]-p[1];le=math.hypot(ux,uy)
  if le<1e-6 or abs(ux*dy-uy*dx)>1e-6*le*ln:continue
  # A tiny corner-relief edge is real geometry but cannot be advertised as the flange's gauging edge.
  project=lambda pt:((pt[0]-a[0])*dx+(pt[1]-a[1])*dy)/ln
  lo,hi=sorted([project(p),project(q)])
  if le<.5*ln or min(ln,hi)-max(0.,lo)<.5*ln:continue
  distance=abs((center[0]-p[0])*dy-(center[1]-p[1])*dx)/ln
  if distance>1e-5:candidates.append((distance,i,p,q))
 if not candidates:return {'kind':'flat_coordinate_datum_only','note':'X0/Y0 are geometric datums, physical gauging edge requires tooling confirmation'}
 distance,i,p,q=min(candidates)
 return {'kind':'actual_outer_straight_edge_candidate','DXF_entity_index':i,'edge_mm':[p,q],'distance_to_bend_center_mm':distance,'note':'closest parallel actual CUT free edge spanning at least half the actual bend length; short corner reliefs excluded; geometric reference only, NOT machine BG; verify tool access'}
def process_data(project,resolved,report):
 return {'header':header_lines(project,resolved),'parts':{name:{'actual_bends':p['actual_bends'],'suggested_sequence_status':'NATIVE_ID_ORDER_CANDIDATE_NOT_TOOL_VALIDATED','bend_rows':[{'sequence_candidate':i+1,'id':b['id'],'direction':b['direction'],'angle_signed_deg':b['angle_signed_deg'],'flat_line_mm':b['flat_line_mm'],'formed_point_mm':b['source_formed_point_mm'],'root_face':b['root_face'],'datum':datum_for(p,b)} for i,b in enumerate(p.get('bend_records',[]))]} for name,p in report['parts'].items()},'zero_bend_isometric':{},'production_release':False}
def shop_bend_lines(row):
 point=lambda p:'('+', '.join(format(v,'.6f') for v in p)+')'
 label=('下折 DOWN' if row['direction']=='DOWN' else '上折 UP')
 a,b=row['flat_line_mm'];d=row['datum']
 lines=[f'候选顺序 {row["sequence_candidate"]}：{row["id"]}，{label}；折弯角 {abs(row["angle_signed_deg"]):.6g} 度，带符号角 {row["angle_signed_deg"]:.6g} 度。',f'展开弯中心线(mm)：{point(a)} → {point(b)}；同版成形参考点(mm)：{point(row["formed_point_mm"])}。']
 if d['kind']=='actual_outer_straight_edge_candidate':
  a,b=d['edge_mm'];lines.append(f'靠边候选 E{d["DXF_entity_index"]}：实际外轮廓直边 {point(a)} → {point(b)}；至本弯中心线 {d["distance_to_bend_center_mm"]:.6f}mm。几何距离不是机床BG，靠边/刀模须现场确认。')
 else:lines.append('靠边未确认：只给展开X0/Y0几何基准；需现场选择实际挡料边，不填写未知机床BG。')
 return lines
def append_process_pages(path,project,resolved,report,projections):
 from reportlab.pdfgen.canvas import Canvas
 from reportlab.lib.pagesizes import A3,landscape
 from reportlab.pdfbase import pdfmetrics
 from reportlab.pdfbase.cidfonts import UnicodeCIDFont
 from reportlab.platypus import Paragraph
 from reportlab.lib.styles import ParagraphStyle
 from xml.sax.saxutils import escape
 from pypdf import PdfReader,PdfWriter
 pdfmetrics.registerFont(UnicodeCIDFont('STSong-Light'));buf=io.BytesIO();cv=Canvas(buf,pagesize=landscape(A3));pw,ph=landscape(A3);data=process_data(project,resolved,report);base_pages=len(PdfReader(path).pages);pages=0;y=0
 style=ParagraphStyle('shop',fontName='STSong-Light',fontSize=11,leading=16,wordWrap='CJK')
 def start(title):
  nonlocal y
  cv.setFont('STSong-Light',18);cv.drawString(35,ph-35,title);cv.setFont('Helvetica',9);cv.drawString(35,ph-54,'v2.8.1 R12 | '+project['project']['version']['value']+' | mm | REVIEW / TRIAL HOLD');y=ph-86
 def para(s):
  nonlocal y
  p=Paragraph(escape(s),style);_,h=p.wrap(pw-85,ph)
  if y-h<50:raise ValueError('PROCESS_PDF_OVERFLOW: process table requires another page')
  p.drawOn(cv,40,y-h);y-=h+10
 def end():
  nonlocal pages
  cv.setFont('STSong-Light',9);cv.drawString(35,25,'数字图册齐套不等于生产放行；现场记录未填，刀模/定位/回弹与首件须核实。');cv.showPage();pages+=1
 start('工艺交接总览 / 版本、材料与数量')
 for line in data['header']:para(line)
 para('数值尺寸优先；各件实际三视、成形斜视与展开见前页。折弯UP/DOWN相对原生展开所选根面法向；不等于机器操作侧。')
 para('现场记录：材质批次______ 实测t______ 机台______ 上模/刀尖R______ 下模V______ 实测Ri______ 回弹______ 首件号/日期______')
 end()
 for name,p in report['parts'].items():
  start(name+' / 逐弯位置、方向与靠边候选')
  para('件号 '+name+'；数量 '+str(resolved['delivery']['sets'])+'；实际弯数 '+str(p['actual_bends'])+'；展开X0/Y0为同版原生DXF坐标。原生弯号顺序仅为候选，未验证机台折序/末折退刀。')
  if name=='LID':
   ba=math.pi/2*(resolved['Ri']+resolved['K_ANSI']*resolved['t']);straight=resolved['skirt']-resolved['Ri']-resolved['t']
   para(f'盖裙外高 {resolved["skirt"]}mm；自由直边至弯带 {straight:.6f} .. {straight+ba:.6f}mm；至弯中心 {straight+ba/2:.6f}mm。03角缝 {resolved["corner_gap"]}mm；不是0.3缝，不是机床BG。')
  for row in data['parts'][name]['bend_rows']:
   for line in shop_bend_lines(row):para(line)
  if not p['actual_bends']:para('本件0折，禁止凭空添加折弯工序；尺寸与孔位按前页实际三视及展开。')
  para('逐弯现场记录：刀模/靠边______ 实际BG______ 角度补偿______ 实测角______ 成形尺寸______ 干涉/退刀检查______ 操作人______')
  end()
  if not p['actual_bends']:
   start(name+' / 实际成形轴测斜视（0折板）');lines=projections[name]['isometric'];pts=[v for line in lines for v in line];x0=min(v[0] for v in pts);x1=max(v[0] for v in pts);y0=min(v[1] for v in pts);y1=max(v[1] for v in pts);sc=min((pw-160)/max(x1-x0,1e-8),(ph-200)/max(y1-y0,1e-8));ox=80-sc*x0;oy=80-sc*y0
   for line in lines:
    for a,b in zip(line,line[1:]):cv.line(ox+sc*a[0],oy+sc*a[1],ox+sc*b[0],oy+sc*b[1])
   data['zero_bend_isometric'][name]={'page_index':base_pages+pages,'map':[sc,0,0,sc,ox,oy]};end()
 if resolved.get('general_process'):
  from general_sources import pdf_lines
  start('通用工艺 / 参数来源与交付等级')
  for line in pdf_lines(resolved['general_process']):
   test=Paragraph(escape(line),style);_,height=test.wrap(pw-85,ph)
   if y-height<50:end();start('通用工艺 / 参数来源续页')
   para(line)
  end()
 cv.save();writer=PdfWriter();writer.append(PdfReader(path));writer.append(PdfReader(io.BytesIO(buf.getvalue())));writer.write(path);data['appended_pages']=pages;return data
def check_process_pdf(path,project,report,d,version,spec,resolved_authority=None):
 if spec.get("contract")=="cn-workshop-dimensioned-v1":
  from cn_workshop import check_process
  return check_process(path,project,report,d,version,spec,resolved_authority)
 from pypdf import PdfReader
 from corner03 import check_pdf_geometry
 norm=lambda s:re.sub(r'\s+','',s)
 reader=PdfReader(path);first=norm(reader.pages[0].extract_text());texts=[norm(p.extract_text()) for p in reader.pages];alltext=''.join(texts)
 expected_label=project['project']['revision']['value'].replace('-','')
 if any(expected_label not in text for text in texts):raise ValueError('PROCESS_PDF_WRONG_SKILL_VERSION')
 if resolved_authority is None:raise ValueError('PROCESS_PDF_SOURCE_AUTHORITY_REQUIRED')
 authoritative_header=header_lines(project,{**resolved_authority,'delivery':d})
 if spec['header']!=authoritative_header:raise ValueError('PROCESS_PDF_HEADER_AUTHORITY_MISMATCH: source job/canonical dimensions, material, quantity and compensation are authoritative, not the process receipt')
 for fragment in [f'MATERIAL={project["requirements"]["material"]["value"]}',f't={project["requirements"]["nominal_t"]["value"]}mm',f'VERSION={version}',f'REV={d["revision"]}','STATUS=REVIEW_TRIAL_HOLD','production_release=false']:
  if norm(fragment) not in first:raise ValueError('PROCESS_PDF_FIRST_PAGE_METADATA: '+fragment)
 for line in authoritative_header:
  if norm(line) not in first:raise ValueError('PROCESS_PDF_FIRST_PAGE_SPEC_MISMATCH')
 overview=[text for text in texts if norm('工艺交接总览 / 版本、材料与数量') in text]
 if len(overview)!=1 or any(norm(line) not in overview[0] for line in authoritative_header):raise ValueError('PROCESS_PDF_OVERVIEW_SOURCE_MISMATCH')
 if set(spec['parts'])!=set(report['parts']):raise ValueError('PROCESS_PDF_PART_COVERAGE')
 for name,p in report['parts'].items():
  rows=spec['parts'][name]['bend_rows']
  expected=[{'sequence_candidate':i+1,'id':b['id'],'direction':b['direction'],'angle_signed_deg':b['angle_signed_deg'],'flat_line_mm':b['flat_line_mm'],'formed_point_mm':b['source_formed_point_mm'],'root_face':b['root_face'],'datum':datum_for(p,b)} for i,b in enumerate(p.get('bend_records',[]))]
  if rows!=expected:raise ValueError('PROCESS_PDF_NATIVE_BEND_RECORD_MISMATCH')
  for row in rows:
   fragments=shop_bend_lines(row)
   if any(norm(t) not in alltext for t in fragments):raise ValueError('PROCESS_PDF_BEND_TABLE_MISSING_OR_STALE')
 zero={name for name,p in report['parts'].items() if not p['actual_bends']}
 if set(spec['zero_bend_isometric'])!=zero:raise ValueError('PROCESS_PDF_ZERO_BEND_ISOMETRIC_COVERAGE')
 return {'ok':True,'materials_quantity_header':True,'bend_table_native_links':True,'production_release':False}
