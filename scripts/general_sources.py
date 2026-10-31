"""Deterministic source/stage dossier, bound to original general brief and current policy."""
import csv,json,re
from pathlib import Path
LABEL={'user':'用户指定','experience_default':'经验默认候选','calculated':'本款计算','pending':'待核'}
STAGE={'confirmation_draft':'确认稿：候选参数，禁止据此直接生产','evidence_based_trial':'有来源试折包：须实折/刀模/首件核实','factory_signed_production_record':'首件装配验证记录：工厂签署负责，软件不代签放行'}
def value_text(v):
 s=json.dumps(v,ensure_ascii=False,separators=(',',':')) if isinstance(v,(dict,list)) else str(v)
 return s if len(s)<=170 else s[:170]+'…（完整值见同版来源表）'
def pdf_lines(meta):
 lines=['GENERAL_CONTRACT='+meta['contract']+' | DELIVERY_GRADE='+meta['effective_stage'],STAGE[meta['effective_stage']]]
 for row in meta['parameter_sources']:lines.append(row['parameter']+' = '+value_text(row['value'])+' '+str(row['unit'] or '')+' | '+LABEL[row['origin']]+' | '+str(row['source'])+' | '+row['note'])
 lines.append('待核：'+', '.join(meta['pending'])+'；刀模/BG/实折未知不得当机床程序。')
 return lines
def write(root,meta,stamp):
 root=Path(root);p=root/f'GENERAL_PROCESS_{stamp}.json';p.write_text(json.dumps(meta,ensure_ascii=False,indent=2));c=root/f'PARAMETER_SOURCES_{stamp}.csv'
 with c.open('w',newline='',encoding='utf-8-sig') as f:
  w=csv.DictWriter(f,fieldnames=list(meta['parameter_sources'][0]));w.writeheader();w.writerows(meta['parameter_sources'])
 report=root/f'GENERAL_PARAMETER_REPORT_{stamp}.md';report.write_text("# 工程参数与来源核验（非师傅作业册）\n\n"+"\n\n".join(pdf_lines(meta)))
 return p,c,report
def check(root,manifest,job):
 from general_process import validate_compiled_job
 meta=validate_compiled_job(job)['job']['general_process'];root=Path(root)
 def one(kind):
  items=[a for a in manifest['artifacts'] if a['kind']==kind]
  if len(items)!=1:raise ValueError('GENERAL_REQUIRED_ARTIFACT: '+kind)
  return root/items[0]['path']
 if json.loads(one('general_source_brief').read_text())!=meta['brief']:raise ValueError('GENERAL_ORIGINAL_BRIEF_REQUIRED_OR_DRIFT')
 if json.loads(one('general_parameter_sources').read_text())!=meta:raise ValueError('GENERAL_PARAMETER_SOURCE_OR_STAGE_DRIFT')
 with one('general_parameter_csv').open(encoding='utf-8-sig',newline='') as f:rows=list(csv.DictReader(f))
 if rows!=[{k:'' if v is None else str(v) for k,v in row.items()} for row in meta['parameter_sources']]:raise ValueError('GENERAL_PARAMETER_CSV_DRIFT')
 if manifest.get('general_process_contract')!=meta['contract'] or manifest.get('general_effective_stage')!=meta['effective_stage']:raise ValueError('GENERAL_CONTRACT_REQUIRED')
 if manifest.get('workshop_pdf_contract')=='cn-workshop-dimensioned-v1':
  report=one('general_parameter_report').read_text()
  if any(line not in report for line in pdf_lines(meta)):raise ValueError('GENERAL_ENGINEERING_REPORT_SOURCE_OR_STAGE_MISSING')
  return {'ok':True,'effective_stage':meta['effective_stage'],'parameter_rows':len(rows),'pending':meta['pending'],'full_provenance_in_separate_report':True,'manufacturing_delivery_complete':meta['effective_stage'] in ['evidence_based_trial','factory_signed_production_record'],'production_release':False}
 from pypdf import PdfReader
 norm=lambda s:re.sub(r'\s+','',s);alltext=''.join(norm(p.extract_text()) for p in PdfReader(one('pdf')).pages)
 for line in pdf_lines(meta):
  if norm(line) not in alltext:raise ValueError('GENERAL_PDF_SOURCE_OR_STAGE_MISSING: '+line[:80])
 return {'ok':True,'effective_stage':meta['effective_stage'],'parameter_rows':len(rows),'pending':meta['pending'],'manufacturing_delivery_complete':meta['effective_stage'] in ['evidence_based_trial','factory_signed_production_record'],'production_release':False}
