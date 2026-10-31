#!/usr/bin/env python3
"""Validate the intake contract and phase gates. Does not run CAD or certify manufacture."""
import argparse,json,math,hashlib,re,sys
from pathlib import Path
from datetime import datetime,timedelta
from create_intake import apply_lid_defaults
try:from jsonschema import Draft202012Validator
except ImportError:raise SystemExit('Missing jsonschema dependency; see references/validation.md. No validation performed.')
ROOT=Path(__file__).resolve().parents[1]
def value(x):return x.get('value') if isinstance(x,dict) else None
def walk(x,path=''):
 if isinstance(x,dict):
  if set(x)=={'value','unit','source','status','note'}:yield path,x
  else:
   for k,v in x.items():yield from walk(v,path+'/'+k)
 elif isinstance(x,list):
  for i,v in enumerate(x):yield from walk(v,path+'/'+str(i))
def diameter(size):
 n=value(size['magnitude']);rep=value(size['representation'])
 if n is None or rep is None:return None
 return n*2 if rep=='radius' else n
def normalized_center_edge(edge):
 n=value(edge['distance']);basis=value(edge['basis']);D=diameter(edge['feature_size'])
 if n is None or basis is None:return None
 return n if basis=='center_to_edge' else None if D is None else n+D/2
def bend_numbers(b,t):
 ri=value(b['Ri']);mode=value(b['compensation_mode'])
 if ri is None or t is None or mode is None:return None
 if mode=='K_factor':
  k=value(b['K_value']);definition=value(b['K_definition'])
  if k is None or definition is None:return None
  k=k/2 if definition=='DIN' else k;ba=math.pi/2*(ri+k*t);return {'BA90':ba,'BD90':2*(ri+t)-ba,'scope':'circular90deg outer-dimension model only; not backgauge'}
 bd=value(b['BD90'])
 return None if bd is None else {'BA90':2*(ri+t)-bd,'BD90':bd,'scope':'provided90deg outer-dimension deduction only; not backgauge'}
def parameter_hash(doc):return hashlib.sha256(json.dumps(apply_lid_defaults(doc),ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def validate(doc,stage='audit'):
 doc=apply_lid_defaults(doc)
 errors=[];holds=[];computed={};levels={'audit':0,'model':1,'cut':2,'release':3};level=levels[stage]
 def err(code,path,message):errors.append({'code':code,'path':path,'message':message})
 def hold(code,path,message):holds.append({'code':code,'path':path,'message':message})
 schema=json.loads((ROOT/'references/project.schema.json').read_text())
 for e in Draft202012Validator(schema).iter_errors(doc):err('SCHEMA','/'+('/'.join(map(str,e.absolute_path))),e.message)
 if errors:return {'ok':False,'status':'BLOCKED','stage':stage,'errors':errors,'holds':holds,'computed':computed,'certifies_manufacture':False}
 def nonfinite(v):
  if isinstance(v,(int,float)) and not isinstance(v,bool):
   try:return not math.isfinite(v)
   except OverflowError:return True
  return any(nonfinite(q) for q in v) if isinstance(v,list) else False
 for path,f in walk(doc):
  if nonfinite(f['value']):err('NONFINITE',path,'finite numeric values required')
 if errors:return {'ok':False,'status':'BLOCKED','stage':stage,'errors':errors,'holds':holds,'computed':computed,'certifies_manufacture':False}
 sources={p['id']:p for p in doc['provenance']}
 if len(sources)!=len(doc['provenance']):err('DUPLICATE_SOURCE','/provenance','source IDs must be unique')
 for path,f in walk(doc):
  v=f['value'];s=f['status'];refs=f['source'];kinds={sources[r]['kind'] for r in refs if r in sources}
  if any(r not in sources for r in refs):err('UNKNOWN_SOURCE',path,'unresolved provenance ID')
  if s in ['unknown','not_applicable'] and v is not None:err('UNKNOWN_HAS_VALUE',path,'unknown/not_applicable must keep value null')
  if s not in ['unknown','not_applicable'] and (v is None or not refs):err('VALUE_SOURCE_REQUIRED',path,'known/requested/assumed values need value and source')
  if s=='not_applicable' and not f['note']:err('NA_REASON',path,'explain why not applicable')
  if s=='assumed' and ('engineering_assumption' not in kinds or not f['note']):err('ASSUMPTION_SOURCE',path,'candidate needs explicit assumption source and note')
  if s=='default' and ('default_policy' not in kinds or not f['note']):err('DEFAULT_SOURCE',path,'workflow defaults need a named policy source and explanation')
  if s=='assumed':hold('CANDIDATE',path,'review assumption, not factory measurement or release')
  if s=='confirmed' and not(kinds & {'user','factory_measurement','manufacturer_drawing'} or (path.startswith('/project/') and 'policy' in kinds)):err('CONFIRMATION_SOURCE',path,'history/assumptions alone cannot become confirmation')
  if s=='measured' and not kinds & {'step_measurement','factory_measurement'}:err('MEASUREMENT_SOURCE',path,'measurement needs actual STEP/factory evidence')
  if path.startswith('/step_facts/') and v is not None and s!='measured':err('STEP_FACT_STATUS',path,'STEP facts must be measured, not silently copied requirements')
 def need(f,path,minlevel=1):
  if level>=minlevel and (value(f) is None or value(f)==''):err('MISSING',path,'required for this phase; continue only independent work')
 for k in ['customer_id','project_id','version']:need(doc['project'][k],'/project/'+k,0)
 ver=value(doc['project']['version']);tz=value(doc['project']['version_timezone']);at=value(doc['project']['recorded_at'])
 if ver is not None and not re.fullmatch(r'\d{8}_\d{4}',ver):err('VERSION_FORMAT','/project/version','use minute precision YYYYMMDD_HHmm')
 elif ver:
  try:datetime.strptime(ver,'%Y%m%d_%H%M')
  except ValueError:err('VERSION_DATE','/project/version','invalid calendar date/minute')
 if tz!='Asia/Shanghai':err('TIMEZONE','/project/version_timezone','explicit Asia/Shanghai required')
 if at:
  try:
   dt=datetime.fromisoformat(at)
   if dt.utcoffset()!=timedelta(hours=8):err('TIME_OFFSET','/project/recorded_at','record timestamp must explicitly use +08:00')
   elif ver and dt.strftime('%Y%m%d_%H%M')!=ver:err('VERSION_TIME_MISMATCH','/project/version','version must equal recorded_at minute in Beijing time')
  except ValueError:err('TIME_PARSE','/project/recorded_at','invalid ISO8601 timestamp')
 else:err('MISSING','/project/recorded_at','explicit version creation time required')
 need(doc['attachment']['reference'],'/attachment/reference',0)
 need(doc['attachment']['filename'],'/attachment/filename',0)
 if value(doc['attachment']['preserve_original']) is not True:err('SOURCE_PRESERVATION','/attachment/preserve_original','must explicitly preserve original')
 h=value(doc['attachment']['sha256'])
 if h is not None and not re.fullmatch('[0-9a-f]{64}',h):err('SOURCE_HASH','/attachment/sha256','expected lowercase SHA256')
 new_design=doc.get('input_mode')=='new_design'
 if level>=1 and not new_design:
  need(doc['attachment']['sha256'],'/attachment/sha256')
  if value(doc['step_facts']['audit_passed']) is not True:err('SOURCE_AUDIT','/step_facts/audit_passed','actual attachment audit must precede modeling')
 sf=doc['step_facts'];unit=value(sf['declared_unit']);scale=value(sf['scale_to_mm']);expected={'mm':1,'inch':25.4,'m':1000}
 if unit in expected and scale is not None and abs(scale-expected[unit])>1e-9:err('UNIT_SCALE','/step_facts/scale_to_mm','declared unit conversion inconsistent')
 if level>=1 and not new_design:need(sf['declared_unit'],'/step_facts/declared_unit');need(sf['scale_to_mm'],'/step_facts/scale_to_mm')
 req=doc['requirements'];scope=value(req['scope']);body=value(req['body_only']);lid=value(req['lid_required']);nuts=value(req['nuts_required'])
 if (scope=='body_only' and (body is not True or lid is not False)) or (scope=='body_and_lid' and (body is not False or lid is not True)):err('SCOPE_CONFLICT','/requirements','scope/body_only/lid_required contradict or incomplete')
 for k in ['scope','body_only','lid_required','nuts_required','material','nominal_t','dimension_basis','height_basis','length_axis','width_axis','height_axis','origin_and_datums']:need(req[k],'/requirements/'+k)
 t=value(req['measured_t']) if value(req['measured_t']) is not None else value(req['nominal_t'])
 if t is not None and t<=0:err('THICKNESS','/requirements','thickness must be positive')
 if value(req['measured_t']) is None:hold('ACTUAL_T','/requirements/measured_t','actual batch thickness unknown; thin land not physically verified')
 for axis,f in req['dimensions'].items():
  need(f,'/requirements/dimensions/'+axis)
  if value(f) is not None and value(f)<=0:err('DIMENSION_POSITIVE','/requirements/dimensions/'+axis,'target dimensions must be positive')
 axes=[value(req[k]) for k in ['length_axis','width_axis','height_axis']]
 if all(axes) and len(set(axes))!=3:err('AXIS_CONFLICT','/requirements','length/width/height axes must be distinct')
 qty=value(doc['project']['quantity_sets'])
 if qty is None:hold('QUANTITY','/project/quantity_sets','single-part geometry may continue; order quantity not specified')
 elif qty<=0:err('QUANTITY','/project/quantity_sets','sets must be positive')
 if lid is False:
  if value(req['height_basis'])=='including_lid':err('HEIGHT_SCOPE','/requirements/height_basis','no lid, so including-lid height is contradictory')
  for path,f in walk(doc['lid'],'/lid'):
   if value(f) is not None:err('UNREQUESTED_LID',path,'remove inactive lid design values; keep source lid fact separately')
 if lid is True:
  for k in ['style','gap','gap_basis','gap_datum','skirt_height','seating_datum','whole_height']:need(doc['lid'][k],'/lid/'+k)
  gap=value(doc['lid']['gap']);basis=value(doc['lid']['gap_basis'])
  if gap is not None and basis not in ['single_side','total']:err('GAP_BASIS','/lid/gap_basis','single-side or total must be explicit')
  if gap is not None and basis:computed['lid_gap_each_side_mm']=gap if basis=='single_side' else gap/2
  if gap is not None and basis:
   g=gap if basis=='single_side' else gap/2;computed['lid_gap_total_length_mm']=2*g;computed['lid_gap_total_width_mm']=2*g
   computed['lid_gap_source_status']=doc['lid']['gap']['status']
   if doc['lid']['gap']['status']=='default' and abs(g-.5)>1e-9:err('DEFAULT_GAP_VALUE','/lid/gap','default is g0.5 per side, total1.0 each plan axis')
  scheme=value(doc['lid']['corner_scheme']);computed['lid_corner_scheme']=scheme
  if doc['lid']['corner_scheme']['status']=='default' and scheme!='03':err('DEFAULT_CORNER_VALUE','/lid/corner_scheme','policy default is03; explicit overrides need their own source/status')
  if scheme is None:hold('LID_CORNER_UNRESOLVED','/lid/corner_scheme','existing/unspecified corner needs explicit review; migration does not redesign it')
  if scheme=='03' and value(doc['lid']['corner_gap']) is None:hold('CORNER_SEAM_UNKNOWN','/lid/corner_gap','03 scheme has no default seam; actual t,Ri,seam must drive geometry')
  if value(doc['lid']['roof_gap']) is None:hold('ROOF_Q_UNKNOWN','/lid/roof_gap','q is independent of g and has no default')
  if new_design:
   from site_fit import acceptance_from_project,assess
   try:
    accepted=acceptance_from_project(doc)
    args=[value(doc['bending']['Ri']),computed.get('lid_gap_each_side_mm'),value(doc['lid']['roof_gap']),value(doc['lid']['whole_height']),t]
    if all(x is not None for x in args):
     fit=assess(*args);computed['root_fit']=fit
     if not fit['analytic_feasible'] and not accepted:
      if level>=2:err('LID_ROOT_FIT_REVIEW_REQUIRED','/lid','Known circular-root conflict requires this-job user site-fitting acceptance or approved design change; dimensions unchanged')
      else:hold('LID_ROOT_FIT_REVIEW_REQUIRED','/lid','Review candidate only; complete delivery blocked pending scoped disposition')
    if accepted:hold('AUTHORIZED_SITE_FIT_TRIAL_REQUIRED','/exceptions','User accepted retaining this-job lid-root interference; site fitting and trial assembly remain required, not geometric elimination')
   except (ValueError,KeyError,TypeError) as ex:err('SITE_FIT_SCOPE','/exceptions',str(ex))
  if value(doc['lid']['root_check_passed']) is not True or value(doc['lid']['root_overlap_volume']) is None or value(doc['lid']['root_check_ref']) is None:hold('LID_ROOT_REVIEW','/lid','actual Ri root/roof interference must be checked independently; g does not prove zero overlap')
  elif value(doc['lid']['root_overlap_volume'])>0:hold('LID_ROOT_INTERFERENCE','/lid/root_overlap_volume','positive overlap remains HOLD even when g0.5; retain scoped authorized exceptions')
  if value(doc['lid']['geometry_evidence_ref']) is None:hold('LID_GEOMETRY_EVIDENCE','/lid/geometry_evidence_ref','formed STEP, true unfolded DXF and PDF geometry must match the same parameters')
  if level>=2:
   for k in ['corner_scheme','geometry_evidence_ref','root_check_passed','root_overlap_volume','root_check_ref']:need(doc['lid'][k],'/lid/'+k,2)
   if scheme=='03':need(doc['lid']['corner_gap'],'/lid/corner_gap',2)

 fab=doc['fabrication'];parts={p['id']:p for p in fab['parts']};roles=[value(p['role']) for p in fab['parts']]
 if len(parts)!=len(fab['parts']):err('DUPLICATE_PART','/fabrication/parts','part IDs not unique')
 if lid is False and 'lid' in roles:err('UNREQUESTED_LID','/fabrication/parts','planned lid forbidden by explicit scope')
 if nuts is False and 'nut' in roles:err('UNREQUESTED_NUT','/fabrication/parts','planned nuts forbidden by explicit scope')
 if level>=1 and not parts:err('MISSING','/fabrication/parts','explicit planned parts required; do not auto-add lid/nuts')
 for i,part in enumerate(fab['parts']):
  need(part['bends'],'/fabrication/parts/'+str(i)+'/bends',2)
  for axis,f in part['dimensions'].items():
   if value(f) is not None and value(f)<=0:err('DIMENSION_POSITIVE','/fabrication/parts/'+str(i)+'/dimensions/'+axis,'part dimensions must be positive')
  if value(fab['method'])=='u_external_ends' and value(part['role'])=='u_body' and value(part['bends']) is not None and value(part['bends'])<2:err('U_BENDS','/fabrication/parts/'+str(i)+'/bends','selected U body requires at least two bends')
 if value(fab['method'])=='u_external_ends':
  need(fab['external_end_count'],'/fabrication/external_end_count');need(fab['seam_gap'],'/fabrication/seam_gap');need(fab['end_inset'],'/fabrication/end_inset');need(fab['geometry_difference_ref'],'/fabrication/geometry_difference_ref')
  if roles.count('u_body')!=1 or (value(fab['external_end_count']) is not None and roles.count('endplate')!=value(fab['external_end_count'])):err('U_PARTS','/fabrication/parts','U/ends must match explicit chosen plan; not a universal conversion')
 method=value(fab['method'])
 if method=='u_wrap_bottom_l':
  if roles.count('u_body')!=1 or roles.count('bottom_l')!=1 or roles.count('endplate') or roles.count('body'):err('UL_PARTS','/fabrication/parts','U wrap requires exactly one U and one bottom-side L')
  for i,part in enumerate(fab['parts']):
   expected_bends={'u_body':2,'bottom_l':1}.get(value(part['role']))
   if expected_bends is not None and value(part['bends'])!=expected_bends:err('UL_BENDS','/fabrication/parts/'+str(i),'U wrap has two bends and L one bend')
 if lid is True and roles.count('lid')!=1:err('LID_PARTS','/fabrication/parts','lid_required needs exactly one planned lid sheet')
 if value(doc['project']['record_kind'])=='new' and (lid is True or new_design):
  need(fab['method'],'/fabrication/method')
  if method not in ['u_external_ends','u_wrap_bottom_l']:err('NEW_STRUCTURE_ADAPTER','/fabrication/method','New design needs a supported structural route; explicit other forms require a separate verified CAD adapter')
  if method=='u_external_ends' and (roles.count('u_body')!=1 or roles.count('endplate')!=2 or roles.count('bottom_l') or roles.count('body')):err('NEW_U_END_PARTS','/fabrication/parts','New U plus ends route requires one U and two end sheets')
  if fab['method']['status']=='default':
   try:
    from select_structure import select_structure
    dims=[value(req['dimensions'][value(req[k])]) for k in ['length_axis','width_axis','height_axis']]
    if method!=select_structure(*dims,lid_required=lid)['selected_method']:err('STRUCTURE_DEFAULT_STALE','/fabrication/method','Default route disagrees with current dimensions')
   except (KeyError,ValueError,TypeError):err('STRUCTURE_DIMENSIONS','/fabrication/method','Resolve dimensions/axes before selecting structure')
 hardware={h['id']:h for h in doc['hardware']}
 if len(hardware)!=len(doc['hardware']):err('DUPLICATE_HARDWARE','/hardware','IDs not unique')
 allpos=[];groupids=[]
 for i,g in enumerate(doc['hole_groups']):
  path='/hole_groups/'+str(i);groupids.append(g['id']);typ=value(g['type']);count=value(g['count']);pilot=diameter(g['laser_size']);positions=g['positions'];allpos.extend(p['id'] for p in positions)
  need(g['type'],path+'/type');need(g['purpose'],path+'/purpose');need(g['count'],path+'/count');need(g['position_datum'],path+'/position_datum')
  if level>=1 and (pilot is None or pilot<=0):err('HOLE_SIZE',path+'/laser_size','explicit diameter or radius required; thread M4 does not define cut diameter')
  if level>=1 and count!=len(positions):err('HOLE_COUNT',path+'/positions','physical hole count must equal explicit owner/position records')
  for j,p in enumerate(positions):
   if p['part_id'] not in parts:err('HOLE_OWNER',path+'/positions/'+str(j),'unknown owning part')
   need(p['center'],path+'/positions/'+str(j)+'/center');need(p['axis'],path+'/positions/'+str(j)+'/axis')
   ax=value(p['axis'])
   if ax is not None and abs(math.sqrt(sum(v*v for v in ax))-1)>1e-6:err('HOLE_AXIS',path+'/positions/'+str(j)+'/axis','unit axis required')
  hr=value(g['hardware_ref']);hw=hardware.get(hr)
  if hr and hw is None:err('HARDWARE_REF',path+'/hardware_ref','unknown hardware record')
  edge=normalized_center_edge(g['edge']);computed[g['id']+'_center_edge_mm']=edge
  if value(g['edge']['distance']) is not None and edge is None:err('EDGE_BASIS',path+'/edge','net distance needs explicit feature diameter/radius')
  if typ=='tap_drill':need(g['thread'],path+'/thread');hold('TAP_PROCESS',path,'thread and drill tolerance/process require actual design specification')
  if typ=='clinch_install':
   if nuts is not True:err('NUT_SCOPE',path,'clinch installation cannot be inferred from M4 or countersink')
   if hw is None:err('CLINCH_MODEL',path,'specific clinch model/drawing required; no inherited install size')
   else:
    if value(hw['role'])!='clinch_nut':err('CLINCH_ROLE',path+'/hardware/role','clinch installation requires a clinch_nut record')
    need(hw['model'],path+'/hardware/model');need(hw['drawing_ref'],path+'/hardware/drawing_ref')
    size=diameter(hw['install_size']);minedge=value(hw['minimum_center_edge']);maxhard=value(hw['max_sheet_hardness_HRB']);hard=value(req['measured_hardness_HRB']);mint=value(hw['minimum_sheet_t'])
    if size is None:err('CLINCH_INSTALL_SIZE',path,'manufacturer install diameter required')
    elif pilot is not None and abs(size-pilot)>1e-8:err('CLINCH_INSTALL_SIZE',path,'laser hole differs from selected manufacturer install size')
    if edge is None or minedge is None:hold('CLINCH_EDGE_UNKNOWN',path,'manufacturer center-to-edge and actual datum unresolved')
    elif edge+1e-8<minedge:err('CLINCH_EDGE',path,'insufficient center-to-edge for selected hardware')
    if mint is not None and t is not None and t<mint:err('CLINCH_THICKNESS',path,'sheet thinner than selected shank minimum')
    if hard is None or maxhard is None:hold('CLINCH_HARDNESS',path,'actual batch hardness and supplier limit required')
    elif hard>maxhard:err('CLINCH_HARDNESS',path,'actual sheet exceeds selected hardware hardness limit')
    scoped_material=value(hw['applicable_sheet_material'])
    if scoped_material is None:hold('CLINCH_MATERIAL_UNKNOWN',path,'qualification scope for selected sheet material missing')
    elif scoped_material!=value(req['material']):err('CLINCH_MATERIAL_STALE',path,'material changed; selected installation qualification must be revalidated')
    if value(hw['install_tolerance']) is None:hold('CLINCH_TOLERANCE',path,'do not copy tolerance from another material/model')
    if value(hw['physical_fit_verified']) is not True:hold('CLINCH_TRIAL',path,'installation/torque-out/pushout and tooling not verified')
  seat=g['seat'];enabled=value(seat['enabled'])
  if typ=='countersunk_clearance' and enabled is not True:err('SEAT_REQUIRED',path+'/seat','counterseat segments must be explicitly enabled')
  if enabled is True:
   if typ!='countersunk_clearance':err('SEAT_TYPE',path,'seat enabled but hole purpose/type differs')
   for k in ['side','flush_required','screw_ref','included_angle']:need(seat[k],path+'/seat/'+k)
   angle=value(seat['included_angle']);mouth=diameter(seat['mouth_size']);sr=value(seat['screw_ref']);screw=hardware.get(sr)
   if sr and (screw is None or value(screw['role'])!='screw'):err('SCREW_REF',path,'seat needs a specific screw record, not a nut')
   if angle is not None and not 0<angle<180:err('SEAT_ANGLE',path,'included angle must be between0 and180')
   if screw:
    ah=value(screw['head_angle']);hd=diameter(screw['head_size'])
    if ah is not None and angle is not None and abs(ah-angle)>1e-8:err('SCREW_SEAT_ANGLE',path,'screw/seat nominal included angles conflict')
    if hd is not None and mouth is not None and abs(hd-mouth)>1e-8:hold('HEAD_FIT',path,'head diameter and seat mouth need declared tolerance/fit check')
    if value(screw['drawing_ref']) is None or value(screw['head_tolerance']) is None or value(screw['physical_fit_verified']) is not True:hold('SCREW_PHYSICAL_PROFILE',path,'actual head profile/angle/tolerance and physical fit are not proved by nominalM4')
   segments=seat['segments'];cursor=0;prior=None;seatdepth=0;land=None
   if not segments:err('SEAT_SEGMENTS',path,'explicit axial segments required')
   for j,seg in enumerate(segments):
    start=value(seg['start_depth']);depth=value(seg['depth']);de=diameter(seg['entry_size']);dx=diameter(seg['exit_size']);kind=seg['kind']
    if None in [start,depth,de,dx]:err('SEAT_SEGMENT_MISSING',path+'/seat/segments/'+str(j),'all axial dimensions and size representations required');continue
    if abs(start-cursor)>1e-8:err('SEAT_CONTINUITY',path,'axial segments have gap/overlap')
    if prior is not None and abs(prior-de)>1e-8:err('SEAT_RADIAL_CONTINUITY',path,'adjacent segment diameters disagree')
    if kind in ['cylinder','straight_land'] and abs(de-dx)>1e-8:err('CYLINDER_SIZE',path,'cylindrical segment must have equal entry/exit sizes')
    if kind=='cone' and angle is not None and 0<angle<180 and abs(depth-(de-dx)/(2*math.tan(math.radians(angle/2))))>1e-8:err('CONE_GEOMETRY',path,'diameters/angle/depth inconsistent')
    if j==0 and mouth is not None and abs(mouth-de)>1e-8:err('MOUTH_SIZE',path,'mouth and first segment disagree')
    if kind=='straight_land':land=depth
    else:seatdepth+=depth
    cursor=start+depth;prior=dx
   if t is not None and segments and abs(cursor-t)>1e-8:err('SEAT_THICKNESS',path,'segments must explicitly span current actual/nominal thickness')
   if pilot is not None and prior is not None and abs(pilot-prior)>1e-8:err('LASER_PILOT',path,'CUT must use pilot hole, never countersink mouth')
   remaining=None if t is None else t-seatdepth;computed[g['id']+'_remaining_mm']=remaining
   if remaining is not None and remaining< -1e-8:err('SEAT_BREAKTHROUGH',path,'machining exceeds sheet thickness')
   accepted=value(seat['minimum_remaining_accepted'])
   if accepted is None:hold('REMAINING_ACCEPTANCE',path,'no universal remaining-wall minimum; approved remaining-wall criterion and first article required')
   elif remaining is not None and remaining+1e-8<accepted:err('REMAINING_TOO_THIN',path,'remaining wall below this project accepted criterion')
   if value(seat['flush_tolerance']) is None:hold('FLUSH_TOLERANCE',path,'flush tolerance not specified; no inferred zero tolerance')
   if value(seat['first_article_passed']) is not True:hold('SEAT_FIRST_ARTICLE',path,'thin wall/flush/indentation needs physical verification')
 if len(groupids)!=len(set(groupids)) or len(allpos)!=len(set(allpos)):err('DUPLICATE_HOLE_ID','/hole_groups','group and physical hole IDs must be unique')
 handles=doc['handles']
 if value(handles['enabled']) is True:
  for k in ['quantity','hardware_ref','holes_per_handle','position_and_orientation']:need(handles[k],'/handles/'+k)
  if any(g not in groupids for g in handles['hole_group_ids']):err('HANDLE_GROUP','/handles','unknown hole group')
  qty=value(handles['quantity']);per=value(handles['holes_per_handle']);n=sum(value(g['count']) or 0 for g in doc['hole_groups'] if g['id'] in handles['hole_group_ids'])
  if qty is not None and per is not None and qty*per!=n:err('HANDLE_COUNT','/handles','quantity×holes per handle does not match physical holes; no default double handle')
 if value(handles['enabled']) is False:
  for key in ['layout','wide_row_pitch','narrow_row_pitch','row_spacing']:
   if value(handles[key]) is not None:err('UNREQUESTED_HANDLE','/handles/'+key,'no handle scope: active layout/pitches cannot remain')
  if handles['patterns']:err('UNREQUESTED_HANDLE','/handles/patterns','no handle scope: active instances cannot remain')
 if value(handles['enabled']) is True:
  layout=value(handles['layout'])
  if layout is None:hold('HANDLE_LAYOUT_UNRESOLVED','/handles/layout','legacy/unspecified layout is not automatically four-hole trapezoid; no historical redesign')
  if handles['wide_row_pitch']['status']=='default' and (layout!='four_hole_trapezoid' or value(handles['wide_row_pitch'])!=85.0):err('DEFAULT_HANDLE_PITCH','/handles/wide_row_pitch','applicable four-hole trapezoid default85.00mm;84 cannot be labeled default')
  if layout=='four_hole_trapezoid':
   need(handles['wide_row_pitch'],'/handles/wide_row_pitch')
   if level>=1:
    try:
     from handle_readback import contracts,measure_pattern
     records=contracts(doc);computed['handle_patterns']=[{'pattern_id':rec['id'],**measure_pattern(rec,rec['points'])} for rec in records]
    except (ValueError,KeyError,TypeError) as ex:err('HANDLE_PATTERN','/handles',str(ex))
   for key in ['narrow_row_pitch','row_spacing']:
    if value(handles[key]) is None:hold('HANDLE_OTHER_DIMENSION_UNKNOWN','/handles/'+key,'85 supplies only wide-row pitch; this independent requirement/source remains unknown')
 for connector in doc['connectors']:
  need(connector['datum_kind'],'/connectors/datum_kind');need(connector['position_datum'],'/connectors/position_datum')
  if any(g not in groupids for g in connector['hole_group_ids']):err('CONNECTOR_GROUP','/connectors','unknown hole group')
 b=doc['bending'];mode=value(b['compensation_mode']);k=value(b['K_value']);definition=value(b['K_definition']);bd=value(b['BD90']);hasbends=any((value(p['bends']) or 0)>0 for p in fab['parts'])
 if hasbends:
  need(b['Ri'],'/bending/Ri',2);need(b['compensation_mode'],'/bending/compensation_mode',2)
  if mode=='K_factor':
   need(b['K_value'],'/bending/K_value',2);need(b['K_definition'],'/bending/K_definition',2)
   if bd is not None:err('COMPENSATION_CONFLICT','/bending','select K or direct BD; do not apply both')
   if k is not None and definition is not None and k>(2 if definition=='DIN' else 1):err('K_RANGE','/bending/K_value','out of declared K-definition range')
  if mode=='bend_deduction':
   need(b['BD90'],'/bending/BD90',2)
   if k is not None:err('COMPENSATION_CONFLICT','/bending','K must be inactive when direct BD is selected')
  n=bend_numbers(b,t);computed['bend90']=n
  if n and n['BA90']<=0:err('BEND_GEOMETRY','/bending','nonpositive bend allowance from supplied model')
  if value(b['calibrated']) is not True:hold('BEND_CALIBRATION','/bending','material/t/Ri/angle specific trial calibration missing')
  elif value(b['calibration_material'])!=value(req['material']) or value(b['calibration_t'])!=t:err('CALIBRATION_STALE','/bending','material or thickness changed; prior calibration invalid')
  elif not any(sources.get(s,{}).get('kind')=='factory_measurement' for s in b['calibrated']['source']):err('CALIBRATION_SOURCE','/bending','calibration needs actual factory evidence')
  if value(b['tool_clearance_verified']) is not True:hold('TOOLING','/bending','bend sequence/clamp/retraction not physically verified')
 if value(b['machine_backgauge']) is not None and not any(sources.get(s,{}).get('kind')=='factory_measurement' for s in b['machine_backgauge']['source']):err('BACKGAUGE_SOURCE','/bending/machine_backgauge','BA/BD/bendline cannot be substituted for measured machine backgauge')
 for exc in doc['exceptions']:
  src=sources.get(exc['authorization_source'])
  if not src or src['kind']!='user' or not exc['scope'].strip():err('EXCEPTION_AUTH','/exceptions','retain scoped human authorization; another agent assumption is not approval')
  if value(exc['observed_overlap_volume']) and value(exc['retained']) is not True:err('EXCEPTION_GEOMETRY','/exceptions','authorized retained collision cannot be deleted then claimed absent')
 if level>=2 and value(doc['delivery']['units'])!='mm':err('OUTPUT_UNITS','/delivery/units','explicit normalized output units required')
 production=value(doc['review']['production_release'])
 if level==3 or production is True:
  if value(doc['review']['digital_checks_passed']) is not True or value(doc['review']['first_article_passed']) is not True:err('RELEASE_EVIDENCE','/review','digital and physical first-article evidence both required')
  for k in ['approver','approval_scope','approval_at']:need(doc['review'][k],'/review/'+k,0)
  if holds:err('RELEASE_HOLD','/review','unresolved candidates/unknown acceptance cannot become production release')
 return {'ok':not errors,'status':'BLOCKED' if errors else 'PASS_WITH_HOLD' if holds else 'PARAMETER_CHECKS_PASSED','stage':stage,'errors':errors,'holds':holds,'computed':computed,'parameter_hash':parameter_hash(doc),'certifies_manufacture':False,'independent_work':['source audit','read-only geometry measurement','unaffected draft work'],'limitation':'JSON/schema checks do not establish actual CAD geometry, tool access or production quality'}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('project');p.add_argument('--stage',choices=['audit','model','cut','release'],default='audit');p.add_argument('--schema-only',action='store_true');p.add_argument('--output');p.add_argument('--resolved-output');a=p.parse_args()
 from safe_io import guard_outputs
 try:guard_outputs([a.project],[a.output,a.resolved_output])
 except ValueError as ex:p.error(str(ex))
 doc=json.loads(Path(a.project).read_text())
 if a.schema_only:
  schema=json.loads((ROOT/'references/project.schema.json').read_text());errs=[e.message for e in Draft202012Validator(schema).iter_errors(doc)];result={'ok':not errs,'structural_errors':errs,'certifies_manufacture':False}
 else:result=validate(doc,a.stage)
 text=json.dumps(result,ensure_ascii=False,indent=2);print(text)
 if a.output:Path(a.output).write_text(text+'\n')
 if a.resolved_output:
  if Path(a.resolved_output).resolve()==Path(a.project).resolve():p.error('resolved output must not overwrite original project')
  Path(a.resolved_output).write_text(json.dumps(apply_lid_defaults(doc),ensure_ascii=False,indent=2)+'\n')
 raise SystemExit(0 if result['ok'] else 2)
