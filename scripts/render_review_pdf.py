#!/usr/bin/env python3
"""Parameter/actual-DXF review pages, not an automatic production three-view drawing engine."""
import argparse,json,math,hashlib,io,re
from pathlib import Path
from create_intake import apply_lid_defaults

def summary(doc):
 d=apply_lid_defaults(doc);lid=d['lid'];yes=d['requirements']['lid_required']['value'];v=lambda f:f['value'];fmt=lambda n:format(n,'.6g')
 if yes is False:fit='本项目无盖：单边g不适用；长向总差不适用；宽向总差不适用。'
 elif yes is not True:fit='盖范围待确认；条件默认（有盖新项目）：单边g=0.5mm；长向总差=1mm；宽向总差=1mm。'
 elif v(lid['gap']) is None or v(lid['gap_basis']) is None:fit='现有项目间隙口径待确认；不得用升级规则静默改值。'
 else:
  g=v(lid['gap'])/(2 if v(lid['gap_basis'])=='total' else 1);status='默认' if lid['gap']['status']=='default' else '试折候选' if lid['gap']['status']=='assumed' else '明确需求/原有值'
  fit='四周直壁：单边g='+fmt(g)+'mm；长向总差='+fmt(2*g)+'mm；宽向总差='+fmt(2*g)+'mm。来源：'+status+'。'
 q='不适用' if yes is False else '待确认（独立参数，无默认）' if v(lid['roof_gap']) is None else fmt(v(lid['roof_gap']))+'mm（独立参数）'
 h=d['handles'];enabled=v(h['enabled']);layout=v(h['layout'])
 if enabled is False:handle='本项目无把手：宽排孔心距不适用。'
 elif enabled is not True or layout!='four_hole_trapezoid':handle='把手范围/布局未定或非四孔梯形：不激活宽排85默认。'
 else:
  pitch=v(h['wide_row_pitch']);label='默认' if h['wide_row_pitch']['status']=='default' else '试折候选' if h['wide_row_pitch']['status']=='assumed' else '明确需求/原有值'
  handle='四孔梯形把手：宽排两安装孔圆心距='+('待确认' if pitch is None else format(pitch,'.2f')+'mm')+'；来源：'+label+'。'
  handle+=' 窄排='+('待确认' if v(h['narrow_row_pitch']) is None else fmt(v(h['narrow_row_pitch']))+'mm')+'；排距='+('待确认' if v(h['row_spacing']) is None else fmt(v(h['row_spacing']))+'mm')+'；孔径独立来源，不由85推定。'
 root='Ri圆弧根部与顶部落座q单独核验；g不证明零干涉。正交叠、未试折/试装仍HOLD。';acceptance=None
 if yes is True and d.get('input_mode')=='new_design':
  from site_fit import acceptance_from_project
  acceptance=acceptance_from_project(d)
  if acceptance:
   if d['project']['revision']['value'] in ['v2.6.1-R06','v2.7.0-R07','v2.7.1-R08','v2.7.2-R09','v2.7.3-R10','v2.8.0-R11','v2.8.1-R12']:
    from interference_volume import display_volume
    root='现场修配：本项目已获用户授权，盖根干涉保留；待现场师傅修配、试装确认。未消除干涉，未确认试装。权威BODY/LID布尔体积='+display_volume(v(lid['root_overlap_volume']))+'mm^3（显示6位；CAD数值计算，不代表实测精度）；详见本图授权页。'
   else:root='现场修配：本项目已获用户授权，盖根干涉保留；待现场师傅修配、试装确认。未消除干涉，未确认试装。实测逐件交叠合计='+str(v(lid['root_overlap_volume']))+'mm^3；详见本图授权页。'
 return {'handle':handle,'fit':fit,'q':q,'corner':'不适用' if yes is False else str(v(lid['corner_scheme']) or '待确认'),'corner_gap':'不适用' if yes is False else '待确认，无默认' if v(lid['corner_gap']) is None else fmt(v(lid['corner_gap']))+'mm；仅当前值','default_policy':'有盖新项目条件默认g=0.5mm单边、长宽总差各1.0mm，corner_scheme=03；客户明确值优先，旧项目不静默改写。','root':root,'site_fit_acceptance':acceptance}

def write_pdf(doc,path,dxf=None,native_report=None,title='钣金参数与展开审核 / HOLD',workshop_resolved=None):
 from reportlab.pdfgen import canvas
 from reportlab.pdfbase import pdfmetrics
 from reportlab.pdfbase.cidfonts import UnicodeCIDFont
 from reportlab.platypus import Paragraph
 from reportlab.lib.styles import ParagraphStyle
 from pypdf import PdfReader,PdfWriter
 from cut_dxf import parse_dxf
 pdfmetrics.registerFont(UnicodeCIDFont('STSong-Light'));buf=io.BytesIO();cv=canvas.Canvas(buf,pagesize=(595,842));cv.setTitle(title);s=summary(doc);style=ParagraphStyle('body',fontName='STSong-Light',fontSize=11,leading=18,wordWrap='CJK')
 def text(text,y,size=11):
  st=ParagraphStyle('t',parent=style,fontSize=size,leading=size+7);p=Paragraph(text,st);w,h=p.wrap(495,700);p.drawOn(cv,50,y-h);return y-h-15
 cv.setFont('STSong-Light',20);cv.drawString(50,786,title);y=750
 items=[s['fit'],'配合口径：盖内直壁相对盒外直壁的长/宽总差；不是盖外尺寸减盒外尺寸。','顶部落座间距 q：'+s['q'],'盖角方案：'+s['corner']+'；角缝：'+s['corner_gap'],'当前名义 t='+str(doc['requirements']['nominal_t']['value'])+'mm；Ri='+str(doc['bending']['Ri']['value'])+'mm；K='+str(doc['bending']['K_value']['value'])+' '+str(doc['bending']['K_definition']['value'])+'；未实机标定。','补偿K来源状态：'+str(doc['bending']['K_value']['status'])+'；拼缝来源状态：'+str(doc['fabrication']['seam_gap']['status'])+'；角缝来源状态：'+str(doc['lid']['corner_gap']['status'])+'。候选不等于客户已确认或实测机床值。',s['root'],s['default_policy'],s['handle'],'数字检查、首件实测和生产放行分别确认。本页不替代完整三视尺寸、折弯工艺及现场验收。']
 if workshop_resolved:
  from workshop_pdf import header_lines
  items=header_lines(doc,workshop_resolved)+[s['fit'],'顶部落座间距 q：'+s['q'],s['handle'],s['root'],'盖角方案：'+s['corner']+'；角缝：'+s['corner_gap'],'数字齐套、现场试折与生产放行分别确认；本版保留HOLD。']
 for line in items:y=text(line,y,9 if workshop_resolved else 11)
 if y<45:raise ValueError('WORKSHOP_FIRST_PAGE_OVERFLOW')
 cv.setFont('STSong-Light',9);cv.drawString(50,35,'v2.8.1 R12 | 审核HOLD | 实际加工需首件验证');result={'first_page_summary':s,'pages':1}
 if s['site_fit_acceptance']:
  from xml.sax.saxutils import escape
  a=s['site_fit_acceptance'];cv.showPage();cv.setFont('STSong-Light',18);cv.drawString(50,786,'本项目现场修配授权及限制 / HOLD');y=745
  for line in ['仅适用于当前项目 '+a['job_id']+'；本页不授权其它客户或变更后的参数。','授权来源：'+a['authorization_source'],'用户原文：'+a['authorization_quote'],'原始设计 SHA256：'+a['job_design_sha256'],s['root'],'保持本次 Ri/g/q、闭盖总高和物理孔位；未自动增顶隙、侧隙或删除交叠。','现场修配与试装尚未执行。几何干涉检测数值仍然有效；03/板厚/孔轴/DXF等其它门禁不得跳过。','材料、机床工装、首件和生产放行仍按各自证据确认；本授权不是生产放行。']:
   y=text(escape(line),y,10)
   if y<50:raise ValueError('SITE_FIT_PDF: authorization text exceeds one page; shorten reference without dropping evidence')
  cv.setFont('STSong-Light',9);cv.drawString(50,35,'v2.8.1 R12 | '+doc['project']['version']['value']+' | 本项目专项授权，不是生产放行')
  result['pages']+=1
 if dxf:
  cv.showPage();cv.setFont('STSong-Light',17);cv.drawString(50,790,'已写DXF实际回读 / 展开几何核对')
  ents=parse_dxf(Path(dxf));lines=[([float(e[10]),float(e[20])],[float(e[11]),float(e[21])]) for e in ents if e['type']=='LINE'];xs=[p[0] for e in lines for p in e];ys=[p[1] for e in lines for p in e];xmin,xmax=min(xs),max(xs);ymin,ymax=min(ys),max(ys);scale=min(470/(xmax-xmin),530/(ymax-ymin));ox=60-scale*xmin;oy=180-scale*ymin
  cv.setLineWidth(.6)
  for a,b in lines:cv.line(ox+scale*a[0],oy+scale*a[1],ox+scale*b[0],oy+scale*b[1])
  for e in ents:
   if e['type']=='CIRCLE':cv.circle(ox+scale*float(e[10]),oy+scale*float(e[20]),scale*float(e[40]),stroke=1,fill=0)
   elif e['type']=='ARC':raise ValueError('this PDF vector adapter supports line outline and circle holes; use a CAD drawing adapter for arcs')
  claim='仅DXF平面回读；尚未证明真实展开。'
  if native_report:
   n=json.loads(Path(native_report).read_text());h=hashlib.sha256(Path(dxf).read_bytes()).hexdigest()
   if n.get('ok') is not True or n.get('CAD_executed') is not True or n['input_sha256']['dxf']!=h or n.get('parameter_hash')!=__import__('handle_readback').parameter_hash(doc):raise ValueError('native report does not bind this actual DXF')
   claim='实际STEP/DXF把手孔心回读报告已绑定；仅孔轴/孔距，不证明真实展开或生产放行。' if 'STEP' in n and 'DXF' in n else '实际CAD原生重展开报告已绑定该DXF；仍需逐页目视、根部干涉与首件验证。'
  text(claim,130,10);cv.setFont('STSong-Light',9);cv.drawString(50,35,'v2.8.1 R12 | 文件几何核对不构成生产放行');result.update(pdf_flat_page_index=result['pages'],pdf_flat_map=[scale,0,0,scale,ox,oy]);result['pages']+=1
 cv.save();reader=PdfReader(io.BytesIO(buf.getvalue()));writer=PdfWriter();writer.append_pages_from_reader(reader);writer.add_metadata({'/Title':title,'/Author':'STEP sheetmetal workflow','/Producer':'ReportLab and pypdf'});writer.write(path);return result

def check_first_page(path,doc):
 if doc.get('project',{}).get('revision',{}).get('value')=='v2.8.1-R12':
  from cn_workshop import check_first_page as check_cn
  return check_cn(path,doc)
 from pypdf import PdfReader
 text=re.sub(r'\s+','',PdfReader(path).pages[0].extract_text());s=summary(doc)
 # Extracted text must contain the actual fit statement on PAGE ONE, not a later note.
 for fragment in [s['fit'],'顶部落座间距 q：'+s['q'],s['handle']]:
  if re.sub(r'\s+','',fragment) not in text:raise ValueError('PDF first-page g/total difference/q summary missing or stale')
 if s['site_fit_acceptance']:
  if re.sub(r'\s+','',s['root']) not in text:raise ValueError('SITE_FIT_PDF: first-page retained interference/onsite disposition absent or stale')
  pages=PdfReader(path).pages
  if len(pages)<2:raise ValueError('SITE_FIT_PDF: missing authorization page')
  auth=re.sub(r'\s+','',pages[1].extract_text())
  for key in ['authorization_source','authorization_quote','job_design_sha256']:
   if re.sub(r'\s+','',s['site_fit_acceptance'][key]) not in auth:raise ValueError('SITE_FIT_PDF: authorization source/quote/design hash absent or stale')
 return {'first_page_gap_q_checked':True}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('project');p.add_argument('--output',required=True);p.add_argument('--dxf');p.add_argument('--native-report');p.add_argument('--mapping-output');a=p.parse_args()
 from safe_io import guard_outputs
 try:guard_outputs([a.project,a.dxf,a.native_report],[a.output,a.mapping_output])
 except ValueError as ex:p.error(str(ex))
 d=json.loads(Path(a.project).read_text());result=write_pdf(d,a.output,a.dxf,a.native_report);check_first_page(a.output,d)
 if a.mapping_output:Path(a.mapping_output).write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps(result,ensure_ascii=False,indent=2))
