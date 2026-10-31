"""Input and result rules for existing STEP; separate from new-dimensional-box contracts."""
import copy,json,math
from pathlib import Path
from jsonschema import Draft202012Validator
CONFIG_SCHEMA={'$schema':'https://json-schema.org/draft/2020-12/schema','title':'Existing STEP audit configuration2.5.0','type':'object','additionalProperties':False,'properties':{
 'material':{'type':['string','null'],'minLength':1},'material_source':{'type':['string','null'],'minLength':1},'K_ANSI':{'type':['number','null'],'minimum':0,'maximum':1},'K_source':{'type':['string','null'],'minLength':1},'K_status':{'enum':['unknown','requested','assumed','measured']},'diagnostic_K_ANSI':{'type':['number','null'],'minimum':0,'maximum':1},'diagnose_invalid':{'type':'boolean'},'try_non_design_repair':{'type':'boolean'},'max_root_attempts':{'type':'integer','minimum':1,'maximum':6},'part_roles':{'type':'object','patternProperties':{'^SOLID_[0-9]+$':{'type':'string','minLength':1}},'additionalProperties':False},'adjacent_hole_gap_limit_mm':{'type':'number','minimum':0,'maximum':20},'interface':{'type':'object','additionalProperties':False,'required':['body_ids','lid_id','up_axis'],'properties':{'body_ids':{'type':'array','minItems':1,'uniqueItems':True,'items':{'type':'string','pattern':'^SOLID_[0-9]+$'}},'lid_id':{'type':'string','pattern':'^SOLID_[0-9]+$'},'up_axis':{'enum':['X','Y','Z']},'up_sign':{'enum':[-1,1]}}}}}
def config_for(config):
 errors=list(Draft202012Validator(CONFIG_SCHEMA).iter_errors(config))
 if errors:raise ValueError('SOURCE_CONFIG: '+'; '.join(e.message for e in errors))
 def finite(o):
  if isinstance(o,float) and not math.isfinite(o):raise ValueError('Nonfinite source configuration')
  if isinstance(o,dict):
   for x in o.values():finite(x)
  if isinstance(o,list):
   for x in o:finite(x)
 finite(config);c=copy.deepcopy(config)
 if c.get('K_ANSI') is not None:
  if not c.get('K_source') or c.get('K_status') not in ['requested','assumed','measured']:raise ValueError('Manufacturing candidate K requires explicit source and status; no confirmation inferred')
 elif c.get('K_status','unknown')!='unknown':raise ValueError('Unknown K cannot carry requested/assumed/measured status')
 if c.get('material') is not None and not c.get('material_source'):raise ValueError('Material requires its own source; STEP colour/name is not a material certificate')
 c.setdefault('max_root_attempts',3);c.setdefault('diagnose_invalid',False);c.setdefault('try_non_design_repair',False);c.setdefault('material',None);c.setdefault('K_ANSI',None);c.setdefault('K_status','unknown');c.setdefault('part_roles',{})
 return c

def delivery_state(report):
 problems=[];diagnostic=[];checked=[]
 for p in report.get('parts',[]):
  u=p['unfold'];status=u['status']
  if not p['BOP']['ok']:problems.append({'part':p['id'],'code':'SOURCE_BOP_FAILED'})
  if status=='GEOMETRY_CHECKED_WITH_HOLD':checked.append(p['id'])
  elif status=='DIAGNOSTIC_ONLY':diagnostic.append(p['id']);problems.append({'part':p['id'],'code':'DIAGNOSTIC_NOT_MANUFACTURING'})
  else:
   reason=u.get('reason')
   if report.get('version') in ['2.5.1-R04','2.6.0-R05','2.6.1-R06'] and not reason:reason='; '.join('Face'+str(a.get('root_face'))+': '+a.get('error','unknown native failure') for a in u.get('attempts',[])) or 'No accepted source flat'
   problems.append({'part':p['id'],'code':'UNFOLD_BLOCKED','reason':reason})
 geometry_complete=bool(report.get('CAD_audit_complete') and len(checked)==report.get('solid_count') and not problems)
 if not report['config'].get('material'):problems.append({'code':'MATERIAL_UNKNOWN'})
 if any(p['bends'] for p in report.get('parts',[])) and report['config'].get('K_ANSI') is None:problems.append({'code':'MANUFACTURING_K_UNKNOWN'})
 if any(abs(pair['volume_mm3'])>1e-6 for pair in report.get('intersections',[])):problems.append({'code':'POSITIVE_SOURCE_INTERFERENCE_HOLD'})
 return {'status':'AUDIT_COMPLETE_WITH_HOLD' if geometry_complete else 'PARTIAL_HOLD','geometry_delivery_complete':geometry_complete,'manufacturing_delivery_complete':False,'production_release':False,'checked_parts':checked,'diagnostic_parts':diagnostic,'holds':problems,'audit_completed':bool(report.get('CAD_audit_complete'))}
