"""R07 complete delivery contract. A complete digital trial package is never production approval."""
import collections,copy,csv,hashlib,json,math,re,zipfile
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
from cut_dxf import parse_dxf
VERSION='2.8.1-R12'
CONTRACT_REVISIONS={'2.7.0-R07':'v2.7.0-R07','2.7.1-R08':'v2.7.1-R08','2.7.2-R09':'v2.7.2-R09','2.7.3-R10':'v2.7.3-R10','2.8.0-R11':'v2.8.0-R11',VERSION:'v2.8.1-R12'}
WORKSHOP_CONTRACT='cn-workshop-dimensioned-v1'
def current_workshop_requirements(project,manifest,spec,source_result,envelope=None):
 """A new publisher never upgrades the manufacturing/PDF generation vintage."""
 from validate_project import value
 versions=[manifest.get('delivery_contract'),value(project['project']['revision']).removeprefix('v'),source_result.get('package_version')]
 current=VERSION in versions
 if current and versions!=[VERSION]*3:raise ValueError('WORKSHOP_SOURCE_MANUFACTURING_VERSION_BINDING')
 protocols=[manifest.get('workshop_pdf_contract'),spec.get('process_pdf',{}).get('contract')]
 if current and protocols!=[WORKSHOP_CONTRACT]*2:raise ValueError('CURRENT_WORKSHOP_PROTOCOL_REQUIRED: manifest and actual process PDF receipt')
 complete=current and protocols==[WORKSHOP_CONTRACT]*2
 if envelope is not None:
  required=current or envelope.get('publisher_release')==VERSION
  if required or 'current_workshop_requirements_complete' in envelope:
   if type(envelope.get('current_workshop_requirements_complete')) is not bool or envelope['current_workshop_requirements_complete']!=complete:raise ValueError('CURRENT_WORKSHOP_ENVELOPE_SOURCE_STATE')
 return complete
SCHEMA={'type':'object','additionalProperties':False,'properties':{
 'namespace':{'enum':['customer','requirement']},'entity_id':{'type':'string','pattern':'^[A-Za-z0-9_-]+$'},'revision':{'type':'string','pattern':'^[A-Za-z0-9_-]+$'},
 'sets':{'type':'integer','minimum':1,'maximum':100},
 'stock':{'type':'object','additionalProperties':False,'required':['length_mm','width_mm','edge_margin_mm','part_gap_mm','status','source'],'properties':{'length_mm':{'type':'number','exclusiveMinimum':0},'width_mm':{'type':'number','exclusiveMinimum':0},'edge_margin_mm':{'type':'number','minimum':0},'part_gap_mm':{'type':'number','exclusiveMinimum':0},'available_sheets':{'type':'integer','minimum':1},'status':{'enum':['requested','confirmed','assumed']},'source':{'type':'string','minLength':1}}}},'allOf':[{'if':{'required':['namespace'],'properties':{'namespace':{'const':'customer'}}},'then':{'required':['entity_id']}}]}
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def resolved_delivery(job):
 from jsonschema import Draft202012Validator
 raw=job.get('delivery',{});errors=list(Draft202012Validator(SCHEMA).iter_errors(raw))
 if errors:raise ValueError('DELIVERY_INPUT: '+'; '.join(e.message for e in errors))
 stock=raw.get('stock',{'length_mm':2440.,'width_mm':1220.,'edge_margin_mm':10.,'part_gap_mm':10.,'status':'assumed','source':'R07 explicit trial stock candidate; inventory, grain, kerf, CAM and machine unconfirmed'})
 if any(not math.isfinite(v) for v in stock.values() if isinstance(v,(int,float))):raise ValueError('Nonfinite stock value')
 if 2*stock['edge_margin_mm']>=min(stock['length_mm'],stock['width_mm']):raise ValueError('Stock margin leaves no usable area')
 return {'contract':VERSION,'namespace':raw.get('namespace','requirement'),'entity_id':raw.get('entity_id',job['id']),'revision':raw.get('revision'), 'sets':raw.get('sets',1),'sets_source':'explicit delivery.sets' if 'sets' in raw else 'assumed one trial set, not order quantity','stock':stock,'identity_source':'explicit delivery namespace/entity_id' if 'entity_id' in raw else 'job.id used as requirement ID, no customer number inferred'}
def revision_root(base,job):
 d=resolved_delivery(job);now=datetime.now(ZoneInfo('Asia/Shanghai')).strftime('%Y%m%d_%H%M%S')
 d['revision']=d['revision'] or now+'_'+hashlib.sha256(json.dumps(job,sort_keys=True).encode()).hexdigest()[:8]
 root=Path(base).resolve()/(d['namespace']+'_'+d['entity_id'])/'revisions'/d['revision']
 if root.exists():raise ValueError('REVISION_EXISTS: immutable revision, choose a new revision; historical files never overwritten')
 return root,d
def translate(e,dx,dy):
 r=copy.deepcopy(e)
 for a,b in [(10,20),(11,21)]:
  if a in r:r[a]=float(r[a])+dx;r[b]=float(r[b])+dy
 return r
def signature(e):
 t=e['type'];r=[t]
 if t=='LINE':r+=sorted([(round(float(e[10]),6),round(float(e[20]),6)),(round(float(e[11]),6),round(float(e[21]),6))])
 else:
  r += [round(float(e[k]),6) for k in [10,20,40]]
  if t=='ARC':r += [round(float(e[k])%360,6) for k in [50,51]]
 return tuple(r)
def bbox(es):
 xs=[];ys=[]
 for e in es:
  x=float(e[10]);y=float(e[20]);xs.append(x);ys.append(y)
  if e['type']=='LINE':xs.append(float(e[11]));ys.append(float(e[21]))
  else:
   r=float(e[40]);angles=[0,90,180,270] if e['type']=='CIRCLE' else [float(e[50]),float(e[51])]+[v for v in [0,90,180,270] if (v-float(e[50]))%360 <= (float(e[51])-float(e[50]))%360+1e-10]
   xs.pop();ys.pop()
   for a in angles:xs.append(x+r*math.cos(math.radians(a)));ys.append(y+r*math.sin(math.radians(a)))
 return [min(xs),min(ys),max(xs),max(ys)]
def write_entities(path,entities):
 pairs=[(0,'SECTION'),(2,'HEADER'),(9,'$INSUNITS'),(70,4),(0,'ENDSEC'),(0,'SECTION'),(2,'ENTITIES')]
 for e in entities:
  pairs.extend([(0,e['type']),(8,'CUT')]);keys=[10,20,11,21] if e['type']=='LINE' else [10,20,40]+([50,51] if e['type']=='ARC' else [])
  pairs.extend((k,format(float(e[k]),'.12f')) for k in keys)
 pairs += [(0,'ENDSEC'),(0,'EOF')];Path(path).write_text('\n'.join(str(v) for pair in pairs for v in pair)+'\n',encoding='ascii');parse_dxf(Path(path))
def layout_parts(dxfs,d):
 stock=d['stock'];m=stock['edge_margin_mm'];gap=stock['part_gap_mm'];L=stock['length_mm'];W=stock['width_mm'];placements=[];sheet=1;x=y=m;rowh=0
 data={k:parse_dxf(v) for k,v in dxfs.items()}
 for owner in sorted(data,key=lambda k:-(bbox(data[k])[3]-bbox(data[k])[1])):
  bb=bbox(data[owner]);w=bb[2]-bb[0];h=bb[3]-bb[1]
  if w>L-2*m+1e-7 or h>W-2*m+1e-7:raise ValueError('NEST_OVERSIZE: '+owner+' no rotation/shape alteration allowed; select adequate stock')
  for instance in range(1,d['sets']+1):
   if x+w>L-m+1e-7:x=m;y+=rowh+gap;rowh=0
   if y+h>W-m+1e-7:sheet+=1;x=y=m;rowh=0
   placements.append({'part_id':owner,'instance':instance,'sheet':sheet,'translation_mm':[x-bb[0],y-bb[1]],'rotation_deg':0,'bbox_mm':[x,y,x+w,y+h]});x+=w+gap;rowh=max(rowh,h)
 if 'available_sheets' in stock and sheet>stock['available_sheets']:raise ValueError('NEST_STOCK_QUANTITY_INSUFFICIENT: required '+str(sheet))
 return {'stock':stock,'sets':d['sets'],'required_sheets':sheet,'placements':placements,'rotation_policy':'0deg only; no grain/material direction qualification','method':'conservative rectangle shelf packing, no batch optimization','kerf_compensated':False,'units':'mm','scale':1,'production_release':False}
def check_nest(layout,dxfs,nests):
 data={k:parse_dxf(v) for k,v in dxfs.items()};stock=layout['stock'];m=stock['edge_margin_mm'];gap=stock['part_gap_mm'];ps=layout['placements']
 want=collections.Counter({(k,i):1 for k in data for i in range(1,layout['sets']+1)})
 if collections.Counter((p['part_id'],p['instance']) for p in ps)!=want:raise ValueError('NEST_PART_QUANTITY_COVERAGE')
 if set(nests)!=set(range(1,layout['required_sheets']+1)) or {p['sheet'] for p in ps}!=set(nests):raise ValueError('NEST_SHEET_COVERAGE')
 for p in ps:
  if p['rotation_deg']!=0:raise ValueError('NEST_UNSUPPORTED_ROTATION')
  actual=bbox([translate(e,*p['translation_mm']) for e in data[p['part_id']]])
  if any(abs(a-b)>1e-5 for a,b in zip(actual,p['bbox_mm'])):raise ValueError('NEST_BBOX_NOT_ACTUAL_DXF')
  x0,y0,x1,y1=actual
  if min(x0,y0)<m-1e-6 or x1>stock['length_mm']-m+1e-6 or y1>stock['width_mm']-m+1e-6:raise ValueError('NEST_STOCK_MARGIN')
 for i,p in enumerate(ps):
  for q in ps[i+1:]:
   if p['sheet']!=q['sheet']:continue
   a,b=p['bbox_mm'],q['bbox_mm'];dx=max(0,a[0]-b[2],b[0]-a[2]);dy=max(0,a[1]-b[3],b[1]-a[3])
   if math.hypot(dx,dy)<gap-1e-6:raise ValueError('NEST_OVERLAP_OR_PART_GAP')
 for sheet,path in nests.items():
  expected=collections.Counter(signature(translate(e,*p['translation_mm'])) for p in ps if p['sheet']==sheet for e in data[p['part_id']])
  actual=collections.Counter(signature(e) for e in parse_dxf(path))
  if actual!=expected:raise ValueError('NEST_GEOMETRY_SCALE_OR_QUANTITY_DIFFERS_FROM_PART_DXFS')
 return {'ok':True,'units':'mm','scale':1,'stock_margin_mm':m,'part_gap_mm':gap,'coverage':'every sheet part exactly sets times, actual entity multiset readback','overlap_proof':'actual-part bounding rectangles have declared positive separation; conservative','production_release':False}
def draw_nests(layout,nests,path,project,version):
 from reportlab.pdfgen.canvas import Canvas
 from reportlab.lib.pagesizes import A3,landscape
 from reportlab.pdfbase import pdfmetrics
 from reportlab.pdfbase.cidfonts import UnicodeCIDFont
 from cn_workshop import material,fmt
 pdfmetrics.registerFont(UnicodeCIDFont('STSong-Light'));cv=Canvas(str(path),pagesize=landscape(A3));pw,ph=landscape(A3);maps={}
 for sheet in sorted(nests):
  s=layout['stock'];scale=min((pw-300)/s['length_mm'],(ph-220)/s['width_mm']);ox=50;oy=90;maps[str(sheet)]={'page_index':sheet-1,'map':[scale,0,0,scale,ox,oy]}
  cv.setFont('STSong-Light',17);cv.drawString(40,ph-40,'集中套料预览 / 第'+str(sheet)+'张 / 待核试折')
  cv.setFont('STSong-Light',10)
  status={'requested':'本款要求，库存待核','confirmed':'板幅已确认，库存复核','assumed':'候选板幅，待确认'}[s['status']]
  lines=[f'版本 {version} | 材料 {material(project["requirements"]["material"]["value"])} | 板厚 {fmt(project["requirements"]["nominal_t"]["value"])} mm | {layout["sets"]}套 | 所需板数 {layout["required_sheets"]}',f'板幅 {fmt(s["length_mm"])}×{fmt(s["width_mm"])} mm | {status} | 边距 {fmt(s["edge_margin_mm"])} / 件距 {fmt(s["part_gap_mm"])} mm','下料文件为毫米原大纯切割轮廓；本页缩放预览，不按纸测量。边框、尺寸和标签仅用于本图。','割缝、桥接、纹向及机床程序待核；分件与集中套料文件二选一，避免重复下料。']
  for j,line in enumerate(lines):cv.drawString(40,ph-62-j*17,line[:170])
  cv.setStrokeColorRGB(.6,.6,.6);cv.rect(ox,oy,scale*s['length_mm'],scale*s['width_mm']);cv.setStrokeColorRGB(0,0,0);cv.setLineWidth(.4)
  draw_pdf_entities(cv,parse_dxf(nests[sheet]),[scale,0,0,scale,ox,oy])
  cv.setFont('STSong-Light',9)
  owners=sorted({p['part_id'] for p in layout['placements'] if p['sheet']==sheet})
  if len(owners)>22:raise ValueError('NEST_PREVIEW_TOO_MANY_PARTS_REQUIRES_DETAIL')
  cv.drawString(ox,oy-24,'板幅长 '+fmt(s['length_mm'])+' mm');cv.drawString(ox+scale*s['length_mm']+5,oy+scale*s['width_mm']/2,'宽 '+fmt(s['width_mm'])+' mm')
  tx=pw-220;ty=ph-175;cv.drawString(tx,ty,'本张实际展开外包尺寸 / mm')
  for index,owner in enumerate(owners):
   placed=[p for p in layout['placements'] if p['sheet']==sheet and p['part_id']==owner];bb=placed[0]['bbox_mm'];cv.drawString(tx,ty-24*(index+1),owner+'：'+fmt(bb[2]-bb[0])+'×'+fmt(bb[3]-bb[1])+'，'+str(len(placed))+'件')
  for p in layout['placements']:
   if p['sheet']==sheet:cv.drawString(ox+scale*p['bbox_mm'][0]+2,oy+scale*p['bbox_mm'][1]+3,p['part_id']+' / '+str(p['instance']))
  cv.showPage()
 cv.save();return maps
def draw_pdf_entities(cv,entities,m):
 scale=m[0];ox=m[4];oy=m[5]
 for e in entities:
  x=float(e[10]);y=float(e[20])
  if e['type']=='LINE':cv.line(ox+scale*x,oy+scale*y,ox+scale*float(e[11]),oy+scale*float(e[21]))
  elif e['type']=='CIRCLE':cv.circle(ox+scale*x,oy+scale*y,scale*float(e[40]),stroke=1,fill=0)
  else:
   r=float(e[40]);cv.arc(ox+scale*(x-r),oy+scale*(y-r),ox+scale*(x+r),oy+scale*(y+r),startAng=float(e[50]),extent=(float(e[51])-float(e[50]))%360)
def pdf_nest_check(path,layout,nests,maps,project=None,require_workshop=False):
 from pypdf import PdfReader
 from corner03 import check_pdf_geometry
 reader=PdfReader(path)
 if len(reader.pages)!=layout['required_sheets']:raise ValueError('NEST_PREVIEW_PAGE_COVERAGE')
 for sheet,path2 in nests.items():
  # Actual LINE vectors must occur at the declared map; ARC/CIRCLE are separately entity-bound DXF.
  lines=[([float(e[10]),float(e[20])],[float(e[11]),float(e[21])]) for e in parse_dxf(path2) if e['type']=='LINE']
  mm=maps[str(sheet)];check_pdf_geometry(path,mm['page_index'],lines,mm['map'])
  from pypdf.generic import ContentStream
  entities=parse_dxf(path2);curve_count=sum(4 if e['type']=='CIRCLE' else max(1,math.ceil(((float(e[51])-float(e[50]))%360)/90)) if e['type']=='ARC' else 0 for e in entities)
  actual_curves=sum(op==b'c' for args,op in ContentStream(reader.pages[mm['page_index']].get_contents(),reader).operations)
  if actual_curves!=curve_count:raise ValueError('NEST_PREVIEW_ARC_CIRCLE_COVERAGE')
  if require_workshop:
   from cn_workshop import material,fmt
   if project is None:raise ValueError('NEST_WORKSHOP_PROJECT_AUTHORITY_REQUIRED')
   text=reader.pages[mm['page_index']].extract_text();norm=lambda x:re.sub(r'\s+','',x);actual=norm(text);s=layout['stock'];status={'requested':'本款要求，库存待核','confirmed':'板幅已确认，库存复核','assumed':'候选板幅，待确认'}[s['status']]
   expected=['集中套料预览',material(project['requirements']['material']['value']),'板厚 '+fmt(project['requirements']['nominal_t']['value'])+' mm',str(layout['sets'])+'套','所需板数 '+str(layout['required_sheets']),fmt(s['length_mm'])+'×'+fmt(s['width_mm'])+' mm',status,'边距 '+fmt(s['edge_margin_mm'])+' / 件距 '+fmt(s['part_gap_mm'])+' mm','板幅长 '+fmt(s['length_mm'])+' mm','宽 '+fmt(s['width_mm'])+' mm']
   for owner in {p['part_id'] for p in layout['placements'] if p['sheet']==sheet}:
    placed=[p for p in layout['placements'] if p['sheet']==sheet and p['part_id']==owner];bb=placed[0]['bbox_mm'];expected.append(owner+'：'+fmt(bb[2]-bb[0])+'×'+fmt(bb[3]-bb[1])+'，'+str(len(placed))+'件')
   if any(norm(fragment) not in actual for fragment in expected):raise ValueError('NEST_WORKSHOP_CHINESE_METADATA_OR_ACTUAL_DIMENSIONS')
   if re.search(r'\b[A-Za-z]{3,}[ \t]+[A-Za-z]{3,}\b',text) or any(term in text for term in ['HOLD','stainless steel','CAM确认']):raise ValueError('NEST_WORKSHOP_ENGLISH_AUDIT_TEXT')
 return True
def expected_bom(project,report,d):
 from validate_project import value
 return [{'part_id':p['id'],'role':value(p['role']),'quantity':d['sets'],'material':value(project['requirements']['material']),'thickness_mm':value(project['requirements']['nominal_t']),'actual_unfold_t_mm':report['parts'][p['id']]['unfold_t_mm'],'actual_bends':report['parts'][p['id']]['actual_bends'],'actual_holes':report['parts'][p['id']]['actual_holes'],'production_release':False} for p in project['fabrication']['parts']]
def add_artifact(m,root,path,kind,**extra):
 from validate_project import parameter_hash
 m['artifacts'].append({'path':str(Path(path).relative_to(root)),'kind':kind,'parameter_version':m['version'],'parameter_hash':m['parameter_hash'],'sha256':sha(path),**extra})
def manifest_contract_check(project,m,root):
 """Called by the normal manifest validator; derives required kinds rather than trusting a list."""
 from validate_project import value
 root=Path(root);arts=m['artifacts'];ver=m['version']
 if m.get('delivery_contract') not in CONTRACT_REVISIONS or m.get('workflow_contract')!='2.6.1-R06' or value(project['project']['revision'])!=CONTRACT_REVISIONS[m['delivery_contract']]:raise ValueError('DELIVERY_CORE_CONTRACT_OR_REVISION_DOWNGRADE')
 def one(kind):
  found=[a for a in arts if a['kind']==kind]
  if len(found)!=1:raise ValueError('DELIVERY_MISSING_OR_DUPLICATE: '+kind)
  a=found[0];path=(root/a['path']).resolve()
  if not path.is_relative_to(root.resolve()) or not path.is_file():raise ValueError('DELIVERY_REQUIRED_FILE_ABSENT: '+kind)
  if a.get('parameter_version')!=ver or sha(path)!=a['sha256']:raise ValueError('DELIVERY_ARTIFACT_VERSION_OR_SHA: '+kind)
  return path
 spec=json.loads(one('delivery_spec').read_text());d=spec['delivery'];job=json.loads(one('source_job').read_text());report=json.loads(one('cad_report').read_text())
 workshop_complete=current_workshop_requirements(project,m,spec,json.loads(one('run_result').read_text()))
 if job.get('general_process') or m.get('general_process_contract') or any(a['kind'].startswith('general_') for a in arts):
  if not job.get('general_process'):raise ValueError('GENERAL_SOURCE_CONTRACT_REQUIRED')
  from general_sources import check as check_general
  check_general(root,m,job)
 one('step_assembly');one('step_exploded');one('formed_isometric_report');one('cad_projections')
 planned={p['id'] for p in project['fabrication']['parts']}
 for kind in ['step_part','unfold_step','dxf']:
  owners=collections.Counter(owner for a in arts if a['kind']==kind for owner in a.get('part_ids',[]))
  if owners!=collections.Counter({owner:1 for owner in planned}):raise ValueError('DELIVERY_REQUIRED_PART_FORMAT: '+kind)
 if len({a['path'] for a in arts if a['kind']=='confirmation_png'})<2:raise ValueError('DELIVERY_CONFIRMATION_ASSEMBLY_EXPLODED_MISSING')
 expected=resolved_delivery(job);expected['revision']=d['revision'];expected['contract']=m['delivery_contract']
 if d!=expected or spec['job_sha256']!=sha(one('source_job')) or spec['contract']!=m['delivery_contract']:raise ValueError('DELIVERY_INPUT_BINDING')
 named_envs=list(root.glob('*DELIVERY_ENVELOPE_*.json'))
 named_envelope=json.loads(named_envs[0].read_text()) if len(named_envs)==1 else {}
 if named_envelope.get('naming'):
  from publish_named_delivery import check_named
  check_named(root,named_envelope,m,d,job)
 else:
  suffix=(d['namespace']+'_'+d['entity_id'],'revisions',d['revision'])
  if tuple(root.parts[-3:])!=suffix:raise ValueError('CUSTOMER_REQUIREMENT_REVISION_ROOT_NOT_ENFORCED')
 if spec['version']!=ver:raise ValueError('DELIVERY_VERSION')
 if value(project['requirements']['material'])!=job['material'] or value(project['requirements']['nominal_t'])!=job['thickness']*{'mm':1,'cm':10,'m':1000,'inch':25.4}[job.get('units','mm')]:raise ValueError('DELIVERY_MATERIAL_OR_THICKNESS_DIFFERS_SOURCE')
 scale={'mm':1,'cm':10,'m':1000,'inch':25.4}[job.get('units','mm')]
 for axis,key in zip('XYZ',['length','width','height']):
  if abs(value(project['requirements']['dimensions'][axis])-job['dimensions'][key]*scale)>1e-8:raise ValueError('DELIVERY_DIMENSION_BASIS_DIFFERS_SOURCE')
 for name,p in report['parts'].items():
  if abs(p['unfold_t_mm']-value(project['requirements']['nominal_t']))>1e-5:raise ValueError('DELIVERY_ACTUAL_SHEET_THICKNESS')
 bom=json.loads(one('bom_json').read_text())
 if bom!=expected_bom(project,report,d):raise ValueError('BOM_MATERIAL_THICKNESS_QUANTITY_OR_PARTS')
 with one('bom_csv').open(newline='') as f:csvrows=list(csv.DictReader(f))
 if csvrows!=[{k:str(v) for k,v in r.items()} for r in bom]:raise ValueError('BOM_CSV_JSON_INCONSISTENT')
 one('parameters');one('hole_table');one('acceptance_report')
 layout=json.loads(one('nest_layout').read_text());dxfs={a['part_ids'][0]:root/a['path'] for a in arts if a['kind']=='dxf'};nests={a['sheet']:root/a['path'] for a in arts if a['kind']=='nest_dxf'}
 if len(nests)!=len([a for a in arts if a['kind']=='nest_dxf']):raise ValueError('DUPLICATE_NEST_SHEET')
 if layout['stock']!=d['stock'] or layout['sets']!=d['sets']:raise ValueError('NEST_STOCK_QUANTITY_INPUT_MISMATCH')
 checked=check_nest(layout,dxfs,nests);pdf_nest_check(one('nest_preview_pdf'),layout,nests,spec['nest_pdf_maps'],project,workshop_complete)
 from workshop_pdf import check_process_pdf
 from design_job import resolve_job
 authority=resolve_job(job)
 if value(project['project']['project_id'])!=authority['id'] or value(project['project']['quantity_sets'])!=d['sets']:raise ValueError('DELIVERY_PROJECT_INPUT_ID_OR_QUANTITY')
 check_process_pdf(one('pdf'),project,report,d,ver,spec['process_pdf'],resolved_authority=authority)
 from corner03 import check_pdf_geometry
 projections=json.loads((root/m['cad_projections']).read_text())
 for name,view in spec['process_pdf']['zero_bend_isometric'].items():
  lines=[(a,b) for line in projections[name]['isometric'] for a,b in zip(line,line[1:])]
  check_pdf_geometry(one('pdf'),view['page_index'],lines,view['map'])
 return {'ok':True,'nest_readback':checked,'digital_deliverables_complete':True,'current_workshop_requirements_complete':workshop_complete,'production_release':False}
def finalize(root,d,result,runtime):
 from validate_manifest import check
 root=Path(root);ver=result['manifest'].removeprefix('manifest_').removesuffix('.json');mp=root/result['manifest'];project=json.loads((root/result['project']).read_text());m=json.loads(mp.read_text());report=json.loads(next((root/'evidence').glob('cad_report_*.json')).read_text());jobpath=next(root.glob('source_job_*.json'));resolved=json.loads(next((root/'evidence').glob('resolved_job_*.json')).read_text())
 d=copy.deepcopy(d);nd=root/'NEST';nd.mkdir();layout=layout_parts({a['part_ids'][0]:root/a['path'] for a in m['artifacts'] if a['kind']=='dxf'},d)
 nests={}
 dxfs={a['part_ids'][0]:root/a['path'] for a in m['artifacts'] if a['kind']=='dxf'}
 for sheet in range(1,layout['required_sheets']+1):
  path=nd/f'NEST_SHEET{sheet:02d}_{ver}.dxf';es=[translate(e,*p['translation_mm']) for p in layout['placements'] if p['sheet']==sheet for e in parse_dxf(dxfs[p['part_id']])];write_entities(path,es);nests[sheet]=path;add_artifact(m,root,path,'nest_dxf',sheet=sheet)
 layoutpath=nd/f'NEST_LAYOUT_{ver}.json';layoutpath.write_text(json.dumps(layout,indent=2));add_artifact(m,root,layoutpath,'nest_layout')
 preview=root/'PDF'/f'NEST_PREVIEW_{ver}.pdf';maps=draw_nests(layout,nests,preview,project,ver);add_artifact(m,root,preview,'nest_preview_pdf')
 bom=expected_bom(project,report,d);bp=root/f'BOM_{ver}.json';bp.write_text(json.dumps(bom,ensure_ascii=False,indent=2));add_artifact(m,root,bp,'bom_json')
 bc=root/f'BOM_{ver}.csv'
 with bc.open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(bom[0]));w.writeheader();w.writerows(bom)
 add_artifact(m,root,bc,'bom_csv');add_artifact(m,root,root/result['project'],'parameters');add_artifact(m,root,jobpath,'source_job');add_artifact(m,root,next(root.glob('holes_*.csv')),'hole_table');add_artifact(m,root,next((root/'evidence').glob('cad_report_*.json')),'cad_report')
 process=json.loads((root/'evidence'/f'PROCESS_PDF_{ver}.json').read_text());sp=root/f'DELIVERY_SPEC_{ver}.json';sp.write_text(json.dumps({'contract':VERSION,'version':ver,'job_sha256':sha(jobpath),'delivery':d,'nest_pdf_maps':maps,'process_pdf':process,'production_release':False},ensure_ascii=False,indent=2));add_artifact(m,root,sp,'delivery_spec')
 ap=root/f'ACCEPTANCE_{ver}.json';ap.write_text(json.dumps({'status':'PENDING_COMPLETE_GATE','production_release':False}));add_artifact(m,root,ap,'acceptance_report')
 m['delivery_contract']=VERSION;mp.write_text(json.dumps(m,indent=2))
 gate=check(project,m,root,runtime=runtime)
 if not gate['ok']:raise ValueError('COMPLETE_DELIVERY_GATE: '+str(gate['errors']))
 ap.write_text(json.dumps({'status':'DIGITAL_CONTRACT_CHECKED_WITH_HOLD','production_release':False,'independent_review':'PENDING','PDF_visual_review_required':True,'checks':gate},indent=2))
 for a in m['artifacts']:
  if a['kind']=='acceptance_report':a['sha256']=sha(ap)
 mp.write_text(json.dumps(m,indent=2))
 inventory=root/f'FILE_SHA256_{ver}.json';files=[{'path':str(p.relative_to(root)),'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(root.rglob('*')) if p.is_file()];inventory.write_text(json.dumps({'contract':VERSION,'files':files},indent=2))
 zp=root/f'{d["namespace"]}_{d["entity_id"]}_{d["revision"]}_DELIVERY_{ver}.zip'
 archive_prefix='/'.join(root.parts[-3:])
 with zipfile.ZipFile(zp,'x',zipfile.ZIP_DEFLATED) as z:
  for p in sorted(root.rglob('*')):
   if p.is_file() and p!=zp:z.write(p,archive_prefix+'/'+str(p.relative_to(root)))
 envelope={'contract':VERSION,'revision_root':str(root),'manifest':mp.name,'inventory':inventory.name,'zip':zp.name,'zip_sha256':sha(zp),'digital_deliverables_complete':True,'current_workshop_requirements_complete':current_workshop_requirements(project,m,{'process_pdf':process},result),'production_release':False,'engineering_status':result['status'],'stock_status':d['stock']['status'],'required_stock_sheets':layout['required_sheets'],'sets':d['sets'],'PDF_visual_review_required':True,'independent_review':'PENDING'}
 from delivery_dispatch import CONTRACT as DISPATCH_CONTRACT,make_plan
 envelope['message_dispatch_contract']=DISPATCH_CONTRACT;envelope['final_message_plan']=make_plan(root,envelope,d,m)
 if 'general_process_contract' in m:
  meta=json.loads(jobpath.read_text())['general_process'];envelope['general_design_stage']=meta['effective_stage'];envelope['manufacturing_delivery_complete']=meta['effective_stage'] in ['evidence_based_trial','factory_signed_production_record']
 envelope['publication_stage']='ENGINEERING_STAGE_NOT_NAMED_FINAL'
 ep=root/f'DELIVERY_ENVELOPE_{ver}.json';ep.write_text(json.dumps(envelope,indent=2));check_envelope(root,envelope,check_cad=False,allow_unpublished=True)
 return envelope
def envelope_authority(envelope,project,spec,layout,final,bom):
 from validate_project import value
 d=spec['delivery'];sets=d['sets']
 if value(project['project']['quantity_sets'])!=sets or layout['sets']!=sets or any(row['quantity']!=sets for row in bom):raise ValueError('ENVELOPE_SOURCE_QUANTITY_INPUTS_DISAGREE')
 expected_fields={'sets':sets,'required_stock_sheets':layout['required_sheets'],'stock_status':d['stock']['status'],'engineering_status':final['status'],'PDF_visual_review_required':True,'independent_review':'PENDING'}
 for key,expected in expected_fields.items():
  if type(envelope.get(key)) is not type(expected) or envelope[key]!=expected:raise ValueError('ENVELOPE_SOURCE_QUANTITY_OR_STATE_MISMATCH: '+key+' receipt='+str(envelope.get(key))+' source='+str(expected))
 return {'input_sets':sets,'canonical_sets':value(project['project']['quantity_sets']),'BOM_quantities':{row['part_id']:row['quantity'] for row in bom},'nest_sets':layout['sets'],'required_stock_sheets':layout['required_sheets'],'receipt_sets':envelope['sets']}
def check_envelope(root,envelope=None,check_cad=True,runtime=None,allow_unpublished=False,allow_legacy_publication=False):
 root=Path(root).resolve()
 if list(root.glob('*GENERAL_REVIEW_STATUS.json')):raise ValueError('GENERAL_CONFIRMATION_ONLY_HOLD: missing essential input or unresolved fit; not complete manufacturing delivery')
 if list(root.glob('SOURCE_DELIVERY_STATUS_*.json')):raise ValueError('SOURCE_AUDIT_ONLY_PARTIAL_HOLD: no complete manufacturing delivery supported by this source-audit mode')
 envelope=envelope or json.loads(next(root.glob('*DELIVERY_ENVELOPE_*.json')).read_text());m=json.loads((root/envelope['manifest']).read_text())
 if envelope.get('contract') not in CONTRACT_REVISIONS or envelope.get('contract')!=m.get('delivery_contract') or envelope.get('production_release') is not False or envelope.get('digital_deliverables_complete') is not True:raise ValueError('DELIVERY_ENVELOPE_FALSE_STATE')
 from publication_contract import check as check_publication
 dispatch,publication=check_publication(root,envelope,m,allow_unpublished,allow_legacy_publication)
 project=json.loads(next(root.glob('*project_*.json')).read_text());workshop_check=manifest_contract_check(project,m,root)
 if m.get('general_process_contract'):
  source=json.loads((root/next(a['path'] for a in m['artifacts'] if a['kind']=='source_job')).read_text());stage=source['general_process']['effective_stage']
  if envelope.get('general_design_stage')!=stage or envelope.get('manufacturing_delivery_complete')!=(stage in ['evidence_based_trial','factory_signed_production_record']):raise ValueError('GENERAL_ENVELOPE_STAGE_OR_MANUFACTURING_CLAIM')
 def only(kind):
  selected=[a for a in m['artifacts'] if a['kind']==kind]
  if len(selected)!=1:raise ValueError('ENVELOPE_AUTHORITY_REQUIRED: '+kind)
  return json.loads((root/selected[0]['path']).read_text())
 spec=only('delivery_spec');d=spec['delivery'];layout=only('nest_layout');final=only('run_result');quantities=envelope_authority(envelope,project,spec,layout,final,only('bom_json'));gate=None
 workshop_complete=current_workshop_requirements(project,m,spec,final,envelope)
 if tuple(Path(envelope['revision_root']).parts[-3:])!=tuple(root.parts[-3:]):raise ValueError('ENVELOPE_IDENTITY_REVISION_MISMATCH')
 if check_cad:
  from validate_manifest import check
  gate=check(project,m,root,runtime=runtime)
  if not gate['ok']:raise ValueError('DELIVERY_CORE_GATE: '+str(gate['errors']))
 inv=root/envelope['inventory'];items=json.loads(inv.read_text())['files'];expected={x['path']:x for x in items};excluded={inv.name,envelope['zip'],next(root.glob('*DELIVERY_ENVELOPE_*.json')).name}
 actual={str(p.relative_to(root)) for p in root.rglob('*') if p.is_file()}-excluded
 if actual!=set(expected):raise ValueError('DELIVERY_INVENTORY_COVERAGE')
 for name,r in expected.items():
  p=root/name
  if sha(p)!=r['sha256'] or p.stat().st_size!=r['bytes']:raise ValueError('DELIVERY_INVENTORY_SHA: '+name)
 zp=root/envelope['zip']
 if sha(zp)!=envelope['zip_sha256']:raise ValueError('DELIVERY_ZIP_SHA')
 with zipfile.ZipFile(zp) as z:
  if z.testzip():raise ValueError('DELIVERY_ZIP_CRC')
  wanted=actual|{inv.name}
  prefix=root.name if envelope.get('naming') else '/'.join(root.parts[-3:])
  if set(z.namelist())!={prefix+'/'+s for s in wanted}:raise ValueError('DELIVERY_ZIP_COVERAGE')
  for name in wanted:
   if hashlib.sha256(z.read(prefix+'/'+name)).hexdigest()!=sha(root/name):raise ValueError('DELIVERY_ZIP_MEMBER_SHA')
 return {'ok':True,'publication':publication,'general_design_stage':envelope.get('general_design_stage'),'manufacturing_delivery_complete':envelope.get('manufacturing_delivery_complete'),'current_workshop_requirements_complete':workshop_complete,'message_dispatch':dispatch,'contract':m['delivery_contract'],'validator_version':VERSION,'digital_deliverables_complete':bool(check_cad),'fresh_CAD_checks_executed':bool(check_cad),'actual_STEP_dimension_readback':gate.get('actual_STEP_dimension_readback') if gate else None,'quantity_authority':quantities,'production_release':False,'checks':['required kinds','source material/thickness/dimensions/quantity','native CAD checks' if check_cad else 'transport/source checks only; final CAD gate not rerun','nest actual entity/qty/spacing','source-derived process PDF','source-derived envelope counts','revision directory','inventory','ZIP CRC/members']}
