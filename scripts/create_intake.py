#!/usr/bin/env python3
"""Build a blank intake and its strict JSON Schema; never inserts design dimensions."""
import argparse,json,copy
from pathlib import Path
STATUS=['unknown','requested','confirmed','measured','assumed','not_applicable','default']
def obj(props):return {'type':'object','properties':props,'required':list(props),'additionalProperties':False}
def nullable(t,**kw):return {'anyOf':[{'type':t,**kw},{'type':'null'}]}
def leaf(v,unit='1'):
 return obj({'value':v,'unit':{'const':unit},'source':{'type':'array','items':{'type':'string'},'uniqueItems':True},'status':{'enum':STATUS},'note':nullable('string')})
def text():return leaf(nullable('string'))
def enum(v):return leaf({'enum':[None,*v]})
def number(unit='mm',minimum=0):return leaf(nullable('number',minimum=minimum),unit)
def count(unit='count'):return leaf(nullable('integer',minimum=0),unit)
def boolean():return leaf(nullable('boolean'))
def vector(unit='mm'):return leaf({'anyOf':[{'type':'array','items':{'type':'number'},'minItems':3,'maxItems':3},{'type':'null'}]},unit)
def size():return obj({'magnitude':number(),'representation':enum(['diameter','radius'])})
def dims():return obj({a:number() for a in ['X','Y','Z']})
def array(item):return {'type':'array','items':item}
def seat():
 return obj({'enabled':boolean(),'side':enum(['outer','inner']),'flush_required':boolean(),'flush_tolerance':number(),'screw_ref':text(),'included_angle':number('deg'),'mouth_size':size(),'segments':array(obj({'kind':{'enum':['cylinder','cone','straight_land']},'start_depth':number(),'depth':number(),'entry_size':size(),'exit_size':size()})),'minimum_remaining_accepted':number(),'first_article_passed':boolean()})
def hole_group():
 return obj({'id':{'type':'string','minLength':1},'purpose':enum(['mounting','lid_body_fixing','handle','connector','other']),'type':enum(['clearance','tap_drill','clinch_install','countersunk_clearance','other']),'count':count(),'thread':text(),'laser_size':size(),'hardware_ref':text(),'position_datum':text(),'positions':array(obj({'id':{'type':'string','minLength':1},'part_id':{'type':'string','minLength':1},'center':vector(),'axis':vector('1')})),'edge':obj({'distance':number(),'basis':enum(['center_to_edge','net_ligament']),'feature_size':size()}),'seat':seat()})
def hardware():
 return obj({'id':{'type':'string','minLength':1},'role':enum(['screw','clinch_nut','nut','handle','connector']),'model':text(),'drawing_ref':text(),'thread':text(),'length':number(),'material':text(),'head_type':text(),'head_angle':number('deg'),'head_size':size(),'head_tolerance':text(),'install_size':size(),'install_tolerance':text(),'minimum_sheet_t':number(),'max_sheet_hardness_HRB':number('HRB'),'minimum_center_edge':number(),'applicable_sheet_material':text(),'physical_fit_verified':boolean()})
def contract():
 return obj({'schema_version':{'const':'2.2.0'},'policies':obj({'lid_gap_single_side':leaf({'const':0.5},'mm'),'lid_corner_scheme':leaf({'const':'03'}),'handle_trapezoid_wide_pitch':leaf({'const':85.0},'mm')}),'project':obj({'record_kind':enum(['new','existing']),'customer_id':text(),'project_id':text(),'revision':text(),'version':text(),'version_timezone':enum(['Asia/Shanghai']),'recorded_at':leaf(nullable('string'),'ISO8601'),'quantity_sets':count('set')}),
 'attachment':obj({'reference':text(),'filename':text(),'sha256':text(),'bytes':count('byte'),'preserve_original':boolean()}),
 'step_facts':obj({'declared_unit':enum(['mm','inch','m']),'scale_to_mm':number('1'),'audit_passed':boolean(),'solid_count':count(),'source_material':text(),'source_thickness':number(),'outer_dimensions':dims(),'source_lid_present':boolean(),'physical_hole_count':count(),'inner_radius':number()}),
 'requirements':obj({'scope':enum(['body_only','body_and_lid','other']),'body_only':boolean(),'lid_required':boolean(),'nuts_required':boolean(),'material':text(),'nominal_t':number(),'measured_t':number(),'measured_hardness_HRB':number('HRB'),'dimension_basis':enum(['outer','inner']),'height_basis':enum(['bare_body','including_lid']),'dimensions':dims(),'length_axis':enum(['X','Y','Z']),'width_axis':enum(['X','Y','Z']),'height_axis':enum(['X','Y','Z']),'origin_and_datums':text(),'preserve_outer_dimensions':boolean(),'preserve_hole_axes':boolean()}),
 'lid':obj({'style':enum(['external','flush','flat','other']),'gap':number(),'gap_basis':enum(['single_side','total']),'gap_datum':text(),'skirt_height':number(),'roof_gap':number(),'seating_datum':text(),'whole_height':number(),'corner_reference':text(),'corner_scheme':text(),'corner_gap':number(),'root_check_passed':boolean(),'root_overlap_volume':number('mm^3'),'root_check_ref':text(),'geometry_evidence_ref':text()}),
 'fabrication':obj({'method':enum(['keep_source','u_external_ends','u_wrap_bottom_l','other']),'external_end_count':count(),'seam_gap':number(),'end_inset':number(),'weld_requirement':text(),'geometry_difference_ref':text(),'parts':array(obj({'id':{'type':'string','minLength':1},'role':enum(['body','u_body','endplate','bottom_l','lid','nut','other']),'name':text(),'bends':count(),'dimensions':dims()}))}),
 'handles':obj({'layout':enum(['four_hole_trapezoid','other']),'wide_row_pitch':number(),'narrow_row_pitch':number(),'row_spacing':number(),'patterns':array(obj({'id':{'type':'string','minLength':1},'part_id':{'type':'string','minLength':1},'wide_hole_ids':{'type':'array','items':{'type':'string'},'minItems':2,'maxItems':2},'narrow_hole_ids':{'type':'array','items':{'type':'string'},'minItems':2,'maxItems':2}})),'enabled':boolean(),'quantity':count(),'hardware_ref':text(),'holes_per_handle':count(),'hole_group_ids':array({'type':'string'}),'position_and_orientation':text()}),
 'connectors':array(obj({'id':{'type':'string'},'hardware_ref':text(),'hole_group_ids':array({'type':'string'}),'position_datum':text(),'datum_kind':enum(['hole_center','hole_edge','other'])})),
 'hardware':array(hardware()),'hole_groups':array(hole_group()),
 'bending':obj({'Ri':number(),'compensation_mode':enum(['K_factor','bend_deduction']),'K_value':number('1'),'K_definition':enum(['ANSI','DIN']),'BD90':number(),'calibrated':boolean(),'calibration_material':text(),'calibration_t':number(),'calibration_ref':text(),'machine_backgauge':number(),'backgauge_machine_and_datum':text(),'tool_clearance_verified':boolean()}),
 'delivery':obj({'formats':leaf({'anyOf':[{'type':'array','items':{'enum':['dxf','pdf','step_parts','step_assembly','step_exploded','confirmation_png','fcstd']},'uniqueItems':True},{'type':'null'}]}),'units':enum(['mm']),'acceptance_criteria':text()}),
 'review':obj({'digital_checks_passed':boolean(),'first_article_passed':boolean(),'production_release':boolean(),'approver':text(),'approval_scope':text(),'approval_at':leaf(nullable('string'),'ISO8601')}),
 'exceptions':array(obj({'id':{'type':'string'},'authorization_source':{'type':'string'},'scope':{'type':'string'},'retained':boolean(),'observed_overlap_volume':number('mm^3'),'evidence_ref':{'type':'string'}})),
 'provenance':array(obj({'id':{'type':'string'},'kind':{'enum':['user','step_measurement','factory_measurement','manufacturer_drawing','engineering_assumption','history_reference','policy','default_policy']},'ref':{'type':'string'},'message_at':nullable('string'),'recorded_at':nullable('string')})),'notes':{'type':'string'}})
_contract_base=contract
def contract():
 s=_contract_base()
 s['properties']['schema_version']={'enum':['2.2.0','2.4.0','2.4.1']}
 s['properties']['input_mode']={'enum':[None,'step','new_design']}
 s['properties']['fabrication']['properties']['end_top_flush']=boolean()
 s['properties']['fabrication']['properties']['fixing_pairs']=array(obj({'id':{'type':'string'},'body_hole_id':{'type':'string'},'lid_hole_id':{'type':'string'},'side':{'type':'string'}}))
 return s
def blank(schema):
 if schema.get('type')=='object':
  if set(schema['properties'])=={'value','unit','source','status','note'}:return {'value':None,'unit':schema['properties']['unit']['const'],'source':[],'status':'unknown','note':None}
  return {k:blank(v) for k,v in schema['properties'].items()}
 if schema.get('type')=='array':return []
 if 'const'in schema:return schema['const']
 return ''
DEFAULT_SOURCE='workflow-defaults-2.1'
def initialize_policy(b,lid_required=None):
 b['provenance'].append({'id':DEFAULT_SOURCE,'kind':'default_policy','ref':'User-approved workflow policy: four straight walls g0.5mm per side; default corner scheme03; no q/Ri/corner-gap default','message_at':None,'recorded_at':None})
 for key,v in [('lid_gap_single_side',.5),('lid_corner_scheme','03')]:b['policies'][key].update(value=v,status='default',source=[DEFAULT_SOURCE],note='Conditional on an applicable new lid project; explicit customer values override')
 b['project']['record_kind'].update(value='new',status='confirmed',source=['policy-timezone'],note='New intake, not migration of an existing order')
 b['lid']['gap']['note']='Conditional new-project default g0.5 per side, total delta1.0 each plan axis; inactive until lid_required=true'
 b['lid']['corner_scheme']['note']='Conditional new-project default03; no fixed t,Ri or corner seam'
 if lid_required is not None:
  b['provenance'].append({'id':'intake-scope','kind':'user','ref':'Caller explicitly selected lid scope while creating a new intake','message_at':None,'recorded_at':None})
  for k,v in [('lid_required',lid_required),('body_only',not lid_required),('scope','body_and_lid' if lid_required else 'body_only')]:b['requirements'][k].update(value=v,status='confirmed',source=['intake-scope'],note='Explicit intake scope selection')
def apply_lid_defaults(doc):
 """Pure copy. Defaults fill missing NEW-project fields; never overwrite explicit/legacy values or q."""
 d=copy.deepcopy(doc);lid=d.get('lid',{});has=d.get('requirements',{}).get('lid_required',{}).get('value')
 if has is False:
  for f in lid.values():
   if isinstance(f,dict) and 'status'in f and (f.get('value') is None or f.get('status')=='default'):f.update(value=None,status='not_applicable',source=[],note='No lid: this fit/corner field is not applicable')
  return d
 if has is not True or d.get('project',{}).get('record_kind',{}).get('value')!='new':return d
 def missing(f):return f.get('value') is None and f.get('status')=='unknown'
 def default(f,v,note):f.update(value=v,status='default',source=[DEFAULT_SOURCE],note=note)
 if missing(lid['gap']):
  basis=lid['gap_basis'].get('value')
  if basis in [None,'single_side','total']:
   default(lid['gap'],1.0 if basis=='total' else .5,'Default four-wall clearance: g0.5 per side; delta length/width1.0; q and root radius separate')
   if basis is None:default(lid['gap_basis'],'single_side','Default g is per side, never a total0.5')
 if lid['gap'].get('status')=='default' and missing(lid['gap_datum']):default(lid['gap_datum'],'lid inner straight wall to body outer straight wall, four sides','Straight walls only; not roof seating or bend-root clearance')
 if missing(lid['corner_scheme']):default(lid['corner_scheme'],'03','03 sloped bend-root closure; recalculate actual t,Ri,seam; no fixed seam/Ri')
 return d
HANDLE_SOURCE='workflow-handle85-2.2'
def apply_handle_defaults(doc):
 d=copy.deepcopy(doc);h=d.get('handles',{})
 # Never add handles or select a layout. The policy is active only after explicit scope/layout.
 if h.get('enabled',{}).get('value') is False:
  for k in ['layout','wide_row_pitch','narrow_row_pitch','row_spacing']:
   f=h.get(k,{})
   if f.get('value') is None or f.get('status')=='default':f.update(value=None,status='not_applicable',source=[],note='No handle: layout and pitches not applicable')
  return d
 if h.get('enabled',{}).get('value') is True and h.get('layout',{}).get('value')=='four_hole_trapezoid' and d.get('project',{}).get('record_kind',{}).get('value')=='new':
  f=h['wide_row_pitch']
  if f.get('value') is None and f.get('status')=='unknown':f.update(value=85.0,status='default',source=[HANDLE_SOURCE],note='Four-hole trapezoid: wider row two actual hole centers85.00mm; not84; no other pitch/row spacing/diameter default')
 return d
_apply_lid_defaults=apply_lid_defaults
def apply_lid_defaults(doc):
 # Compatibility name: normalize both conditional project policies on a pure copy.
 return apply_handle_defaults(_apply_lid_defaults(doc))
_apply_legacy_defaults=apply_lid_defaults
STRUCTURE_SOURCE='workflow-structure-2.4'
def apply_structure_defaults(doc):
 d=copy.deepcopy(doc)
 if d.get('project',{}).get('record_kind',{}).get('value')!='new':return d
 req=d.get('requirements',{});fab=d.get('fabrication',{})
 if req.get('lid_required',{}).get('value') not in (True,False):return d
 try:
  dims=[req['dimensions'][req[k]['value']]['value'] for k in ['length_axis','width_axis','height_axis']]
  if any(x is None for x in dims):return d
  from select_structure import select_structure
  chosen=select_structure(*dims,lid_required=req['lid_required']['value'])
 except (KeyError,ValueError,TypeError):return d
 f=fab.get('method',{})
 if f.get('value') is None and f.get('status')=='unknown':
  if not any(x['id']==STRUCTURE_SOURCE for x in d['provenance']):d['provenance'].append({'id':STRUCTURE_SOURCE,'kind':'default_policy','ref':'2.4 structure policy: max(L,W)>=H selects U plus two ends; otherwise U wrap plus bottom L; explicit customer choices preserved','message_at':None,'recorded_at':None})
  f.update(value=chosen['selected_method'],status='default',source=[STRUCTURE_SOURCE],note='Resolved from normalized dimensions; not a manufacturability certificate')
 return d
def apply_lid_defaults(doc):
 return apply_structure_defaults(_apply_legacy_defaults(doc))
apply_project_defaults=apply_lid_defaults

def build(lid_required=None,handle_layout=None):
 s=contract();s.update({'$schema':'https://json-schema.org/draft/2020-12/schema','title':'STEP Sheetmetal intake2.4.1; legacy2.2/2.4 compatible; unknown quantities null'})
 b=blank(s);b['schema_version']='2.4.1';b['input_mode']=None;b['project']['version_timezone']={'value':'Asia/Shanghai','unit':'1','source':['policy-timezone'],'status':'confirmed','note':'Explicit project numbering rule, not a design default'};b['provenance']=[{'id':'policy-timezone','kind':'policy','ref':'project versioning uses Asia/Shanghai per workflow','message_at':None,'recorded_at':None}];initialize_policy(b,lid_required)
 b['provenance'].append({'id':HANDLE_SOURCE,'kind':'default_policy','ref':'User-approved workflow policy: applicable four-hole trapezoid handle wider row center distance85.00mm; not84; no other hole layout dimensions supplied','message_at':None,'recorded_at':None})
 b['policies']['handle_trapezoid_wide_pitch'].update(value=85.0,status='default',source=[HANDLE_SOURCE],note='Only applicable new four-hole trapezoid handles; explicit project overrides retain provenance; old orders not redesigned')
 if handle_layout is not None:
  b['provenance'].append({'id':'intake-handle-layout','kind':'user','ref':'Caller explicitly selected handle layout in new intake','message_at':None,'recorded_at':None})
  for key,value in [('enabled',True),('layout',handle_layout)]:b['handles'][key].update(value=value,status='confirmed',source=['intake-handle-layout'],note='Explicit intake handle layout selection; quantity not inferred')
  if handle_layout=='four_hole_trapezoid':b['handles']['holes_per_handle'].update(value=4,status='confirmed',source=['intake-handle-layout'],note='Explicit four-hole layout definition, not inferred handle quantity')
 return s,apply_lid_defaults(b)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',required=True);p.add_argument('--schema-output');p.add_argument('--lid',choices=['yes','no','unknown'],default='unknown');p.add_argument('--handle-layout',choices=['four_hole_trapezoid','other']);a=p.parse_args();s,b=build(None if a.lid=='unknown' else a.lid=='yes',a.handle_layout);Path(a.output).write_text(json.dumps(b,ensure_ascii=False,indent=2)+'\n')
 if a.schema_output:Path(a.schema_output).write_text(json.dumps(s,ensure_ascii=False,indent=2)+'\n')
