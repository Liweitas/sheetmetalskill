#!/usr/bin/env python3
"""Real PDF+receipt+SHA+ZIP synchronized counterexamples; isolated copies, CAD unchanged."""
import argparse,copy,hashlib,json,shutil,zipfile,re
from pathlib import Path
from pypdf import PdfReader,PdfWriter
from pypdf.generic import ContentStream,TextStringObject,ByteStringObject
from delivery_contract import check_envelope,sha
def patch_pdf(pdf,old,new):
 w=PdfWriter(clone_from=PdfReader(pdf));count=0
 for page in w.pages:
  stream=ContentStream(page.get_contents(),w)
  for operands,op in stream.operations:
   if op!=b'Tj':continue
   x=operands[0]
   if isinstance(x,str) and old in str(x):operands[0]=TextStringObject(str(x).replace(old,new));count+=1;continue
   try:raw=x.original_bytes if hasattr(x,'original_bytes') else bytes(x);s=raw.decode('utf-16be')
   except (UnicodeError,TypeError,AttributeError):continue
   if old in s:operands[0]=ByteStringObject(s.replace(old,new).encode('utf-16be'));count+=1
  page.replace_contents(stream)
 w.write(pdf)
 if count<1:raise ValueError('Counterexample did not actually change PDF text')
 return count
def repack(root):
 mp=next(root.glob('*manifest_*.json'));m=json.loads(mp.read_text());ep=next(root.glob('*DELIVERY_ENVELOPE_*.json'));e=json.loads(ep.read_text());pdf=root/next(a['path'] for a in m['artifacts'] if a['kind']=='pdf');iso=root/m['formed_isometric_report'];d=json.loads(iso.read_text());d['pdf_sha256']=sha(pdf);iso.write_text(json.dumps(d,indent=2))
 for a in m['artifacts']:a['sha256']=sha(root/a['path'])
 mp.write_text(json.dumps(m,indent=2));inv=root/e['inventory'];zp=root/e['zip'];excludes={inv.name,zp.name,ep.name};files=[p for p in root.rglob('*') if p.is_file() and str(p.relative_to(root)) not in excludes];inv.write_text(json.dumps({'contract':e['contract'],'files':[{'path':str(p.relative_to(root)),'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(files)]},indent=2))
 prefix=root.name if e.get('naming') else '/'.join(root.parts[-3:])
 with zipfile.ZipFile(zp,'w',zipfile.ZIP_DEFLATED) as z:
  for p in sorted(files+[inv]):z.write(p,prefix+'/'+str(p.relative_to(root)))
 e['zip_sha256']=sha(zp);e['revision_root']=str(root)
 if 'final_message_plan' in e:
  e['final_message_plan']['archive_sha256']=e['zip_sha256']
  for message in e['final_message_plan']['messages']:
   for attachment in message['attachments']:
    if attachment['path']==e['zip']:attachment['sha256']=e['zip_sha256']
 ep.write_text(json.dumps(e,indent=2))
def main():
 p=argparse.ArgumentParser();p.add_argument('revision_root');p.add_argument('--output',required=True);a=p.parse_args();source=Path(a.revision_root).resolve();out=Path(a.output).resolve()
 if out.exists():p.error('output must not exist')
 out.mkdir(parents=True);m=json.loads(next(source.glob('*manifest_*.json')).read_text());job=json.loads((source/next(x['path'] for x in m['artifacts'] if x['kind']=='source_job')).read_text());proj=json.loads((source/next(x['path'] for x in m['artifacts'] if x['kind']=='parameters')).read_text());L=proj['requirements']['dimensions']['X']['value'];W=proj['requirements']['dimensions']['Y']['value'];immutable={str(p.relative_to(source)):sha(p) for p in source.rglob('*') if p.is_file()};results=[]
 for name in ['legal_repacked','synchronized_PDF_dimensions','wrong_three_view_dimension_labels','false_envelope_sets','false_envelope_board_count']:
  root=out/name/Path(*source.parts[-3:]);shutil.copytree(source,root);mp=next(root.glob('*manifest_*.json'));m2=json.loads(mp.read_text());pdf=root/next(x['path'] for x in m2['artifacts'] if x['kind']=='pdf');ep=next(root.glob('*DELIVERY_ENVELOPE_*.json'));e=json.loads(ep.read_text());mutations=0
  if name=='synchronized_PDF_dimensions':
   old=str(float(L))+' x '+str(float(W));new='999.0 x 888.0';mutations=patch_pdf(pdf,old,new)
   for path in [next(root.glob('*DELIVERY_SPEC_*.json')),next((root/'evidence').glob('*PROCESS_PDF_*.json'))]:
    d=json.loads(path.read_text());holder=d['process_pdf'] if 'process_pdf' in d else d;holder['header']=[s.replace(old,new) for s in holder['header']];path.write_text(json.dumps(d,ensure_ascii=False,indent=2))
  elif name=='wrong_three_view_dimension_labels':
   page=next(p for p in PdfReader(pdf).pages if 'ASSEMBLY - ACTUAL EXPORTED STEP THREE VIEWS' in p.extract_text());old=next(s.strip() for s in page.extract_text().splitlines() if re.fullmatch(r'\d+\.\d{6} mm',s.strip()));mutations=patch_pdf(pdf,old,'999.000000 mm')
  elif name=='false_envelope_sets':e['sets']=999;ep.write_text(json.dumps(e,indent=2))
  elif name=='false_envelope_board_count':e['required_stock_sheets']=999;ep.write_text(json.dumps(e,indent=2))
  repack(root)
  unchanged=[x for x in m['artifacts'] if x['kind'] in ['source_job','parameters','step_part','step_assembly','step_exploded','dxf','unfold_step']]
  assert all(sha(source/x['path'])==sha(root/x['path']) for x in unchanged)
  try:result=check_envelope(root);ok=result['ok'];error=None
  except Exception as ex:result=None;ok=False;error=str(ex)
  expected=name=='legal_repacked'
  if ok!=expected:raise RuntimeError('Receipt authority test failed '+name+': '+str(error))
  results.append({'test':name,'expected_accepted':expected,'ok':ok,'error':error,'result':result,'fixture':str(root),'PDF_text_replacements':mutations,'authoritative_input_and_CAD_unchanged':True})
 assert immutable=={str(p.relative_to(source)):sha(p) for p in source.rglob('*') if p.is_file()}
 (out/'RECEIPT_AUTHORITY_RESULTS.json').write_text(json.dumps({'author_test_only':True,'validator':'2.7.3-R10','source_unchanged':True,'cases':results},ensure_ascii=False,indent=2));print(json.dumps({'positive':1,'semantic_negatives':4,'status':'PASS_AUTHOR_ONLY'},indent=2))
if __name__=='__main__':main()
