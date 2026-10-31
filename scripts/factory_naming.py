"""Factory identity is independent of internal revisions and of geometric authorization."""
import datetime,decimal,re

FIELDS=['channel','material','thickness','date','number','factory_version']
def thickness(value):
 try:d=decimal.Decimal(str(value))
 except decimal.InvalidOperation:raise ValueError('NAMING_THICKNESS')
 if not d.is_finite() or d<=0:raise ValueError('NAMING_THICKNESS')
 s=format(d,'f').rstrip('0').rstrip('.') if '.' in format(d,'f') else format(d,'f')
 return s if '.' in s else s+'.0'
def resolve(request,job,delivery):
 request={} if request is None else request
 if not isinstance(request,dict) or set(request)-set(FIELDS+['previous_code','source','material_code','material_mapping']):raise ValueError('NAMING_FIELDS')
 request={k:v for k,v in request.items() if v is not None and v!=''}
 from pathlib import Path
 import json
 from jsonschema import Draft202012Validator
 errors=list(Draft202012Validator(json.loads((Path(__file__).resolve().parents[1]/'references/naming.schema.json').read_text())).iter_errors(request))
 if errors:raise ValueError('NAMING_SCHEMA: '+'; '.join(e.message for e in errors))
 if 'channel' in request and request['channel'] not in ['S','X']:raise ValueError('NAMING_CHANNEL_S_OR_X')
 if 'material' in request and (not isinstance(request['material'],str) or not re.fullmatch(r'[A-Za-z0-9_\u4e00-\u9fff]+',request['material'])):raise ValueError('NAMING_MATERIAL_SAFE_SEGMENT')
 from material_code import resolve as resolve_material
 material,material_identity,material_missing=resolve_material(request,job.get('material'))
 if material is not None:request={**request,'material':material}
 scale={'mm':1,'cm':10,'m':1000,'inch':25.4}[job.get('units','mm')]
 if 'thickness' in request and thickness(request['thickness'])!=thickness(job['thickness']*scale):raise ValueError('NAMING_THICKNESS_DIFFERS_SOURCE')
 normalized={k:request[k] for k in FIELDS if k in request}
 if 'thickness' in request:normalized['thickness']=thickness(request['thickness'])
 if 'date' in request:
  value=str(request['date']);value=value.replace('/','').replace('-','')
  if not re.fullmatch(r'\d{8}',value):raise ValueError('NAMING_DATE_YYYYMMDD')
  try:datetime.datetime.strptime(value,'%Y%m%d')
  except ValueError:raise ValueError('NAMING_DATE_INVALID')
  normalized['date']=value
 if 'number' in request:
  value=request['number']
  if isinstance(value,bool) or not re.fullmatch(r'\d{1,4}',str(value)) or not 1<=int(value)<=9999:raise ValueError('NAMING_NUMBER_1_TO_9999')
  normalized['number']=f'{int(value):04d}'
 if 'factory_version' in request:
  value=request['factory_version']
  if type(value) is not int or value<1:raise ValueError('NAMING_FACTORY_VERSION_POSITIVE_INTEGER')
 missing=[k for k in FIELDS if k not in request or request[k] is None or request[k]=='']+material_missing
 extra={'material_identity':material_identity} if material_identity is not None else {}
 if missing:
  if request.get('previous_code'):raise ValueError('NAMING_VERSION_UPGRADE_REQUIRES_ALL_FIELDS')
  return {**extra,'status':'UNNAMED_PENDING_CONFIRMATION','code':None,'prefix':'未命名待确认_'+delivery['namespace']+'_'+delivery['entity_id']+'_'+delivery['revision'],'missing_fields':missing,'normalized':normalized,'number_allocation':'factory manages uniqueness/reset; no auto assignment','source':request.get('source','not supplied')}
 code='-'.join(str(normalized[k]) for k in FIELDS[:-1])+'-v'+str(normalized['factory_version'])
 previous=request.get('previous_code')
 if previous:
  match=re.fullmatch(r'(.+)-v([1-9]\d*)',previous)
  if not match or code.rsplit('-v',1)[0]!=match[1] or normalized['factory_version']<=int(match[2]):raise ValueError('NAMING_UPGRADE_KEEP_FIRST_FIVE_SEGMENTS: changed identity needs explicit new identity, never silent version upgrade')
 return {**extra,'status':'FORMALLY_NAMED','code':code,'prefix':code,'missing_fields':[],'normalized':normalized,'number_allocation':'factory manages uniqueness/reset; duplicate output blocked, no auto renumber','source':request.get('source','provided naming input; sender verifies factory assignment')}

LABELS={'general_parameter_report':'工程参数核验报告','confirmation_pdf':'确认PDF','step_assembly':'装配STEP','step_exploded':'爆炸STEP','step_part':'成形STEP','unfold_step':'真实展开STEP','dxf':'激光CUT','bend_dxf':'折弯BEND','nest_dxf':'套料CUT','nest_preview_pdf':'套料预览PDF','pdf':'完整折弯工艺PDF','bom_json':'BOM','bom_csv':'BOM','parameters':'参数','source_job':'原始需求','hole_table':'孔表','cad_report':'CAD核验','delivery_spec':'交付参数','acceptance_report':'验收','run_result':'工程结果','confirmation_png':'确认图','formed_isometric_report':'成形斜视核验','cad_projections':'实际投影'}
def filename_map(files,manifest,prefix,previous_prefix=None):
 from pathlib import PurePosixPath
 kinds={a['path']:a['kind'] for a in manifest['artifacts']};mapping={}
 for name in files:
  p=PurePosixPath(name);label=LABELS.get(kinds.get(name),'核验资料' if p.suffix.lower() in ['.json','.log'] else '资料')
  basename=p.name
  if previous_prefix and basename.startswith(previous_prefix+'_'):
   basename=basename[len(previous_prefix)+1:]
   if basename.startswith(label+'_'):basename=basename[len(label)+1:]
  if manifest.get('general_effective_stage')=='confirmation_draft' and not basename.startswith('确认稿候选_'):basename='确认稿候选_'+basename
  mapping[name]=str(p.parent/(prefix+'_'+label+'_'+basename))
 if len(set(mapping.values()))!=len(mapping):raise ValueError('NAMING_COLLISION')
 return mapping

def published_root(archive):
 """Find a single final revision for test/helper callers; never choose a stage or guess among revisions."""
 from pathlib import Path
 import json
 candidates=[]
 for p in Path(archive).rglob('*DELIVERY_ENVELOPE_*.json'):
  if '.R09-unpublished-engineering' in p.parts:continue
  if json.loads(p.read_text()).get('publication_stage'):continue
  candidates.append(p.parent)
 if len(candidates)!=1:raise ValueError('NAMING_EXPLICIT_PUBLISHED_REVISION_REQUIRED: '+str(len(candidates)))
 return candidates[0]
