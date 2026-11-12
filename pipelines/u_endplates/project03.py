# Build the skill intake-format project doc (create_intake.build) for corner03.py / native03_check.py.
# v2.8.3 pipeline u_endplates (vendored from order box-400x220x150 t46u). Values from the brief (env SM_JOB) via cfg.py.
# corner_gap: brief value (source user) or candidate 0.2 (status assumed, listed as pending). usage: python3 project03.py OUT.json
import sys,json
from pathlib import Path
SK=str(Path(__file__).resolve().parents[2]/'scripts');sys.path.insert(0,SK);sys.path.insert(0,str(Path(__file__).parent))   # v2.8.3 pipeline: skill-relative
from create_intake import build
from cfg import *
_,d=build(True)
d['provenance']+= [{'id':'user-brief','kind':'user','ref':f'{VER}: {L:g}x{W:g} body outer, {H:g} incl. lid, {MATERIAL_CN} t{t:g}, g{g:g}, skirt{skirt:g} (brief)','message_at':None,'recorded_at':None},
 {'id':'corner-gap','kind':'user' if CORNER_GAP_SOURCE=='user' else 'engineering_assumption','ref':f'lid corners = skill 03 scheme, corner_gap={CORNER_GAP:g} ({CORNER_GAP_SOURCE})','message_at':None,'recorded_at':None},
 {'id':'empirical','kind':'engineering_assumption','ref':'Ri0.8/K0.4 ANSI empirical candidates, not calibrated','message_at':None,'recorded_at':None}]
def put(f,v,src,st='confirmed',note=None):f.update(value=v,status=st,source=[src],note=note)
P=d['project'];put(P['project_id'],VER,'user-brief');put(P['revision'],'v2.8.3-u_endplates','user-brief',note='pipeline revision label; not a legacy R06-R12 record');put(P['version'],VER,'user-brief');put(P['customer_id'],'UNASSIGNED_CUSTOMER','user-brief');put(P['quantity_sets'],1,'user-brief','assumed')
R=d['requirements']
for k,v in {'nominal_t':t,'dimension_basis':'outer','height_basis':'including_lid','length_axis':'X','width_axis':'Y','height_axis':'Z','material':JOB.get('material_en','201 stainless')}.items():put(R[k],v,'user-brief')
for k,v in zip('XYZ',[L,W,H]):put(R['dimensions'][k],v,'user-brief')
Ld=d['lid']
for k,v in {'style':'external','gap':g,'gap_basis':'single_side','gap_datum':'Lid inner straight walls to body outer straight walls','skirt_height':skirt,'roof_gap':q,'seating_datum':'roof inner face versus body top','whole_height':H}.items():put(Ld[k],v,'user-brief')
put(Ld['corner_scheme'],'03','corner-gap');put(Ld['corner_gap'],CORNER_GAP,'corner-gap','confirmed' if CORNER_GAP_SOURCE=='user' else 'assumed',note=f'corner_gap source: {CORNER_GAP_SOURCE}')
B=d['bending']
for k,v in {'Ri':ri,'compensation_mode':'K_factor','K_value':K,'K_definition':'ANSI'}.items():put(B[k],v,'empirical','assumed')
put(B['calibrated'],False,'empirical');put(B['tool_clearance_verified'],False,'empirical')
F=d['fabrication'];put(F['method'],'u_wrap_bottom_l' if STRUCTURE == 'u_l_t7u' else 'u_external_ends','user-brief');put(F['seam_gap'],SEAM,'user-brief');put(F['end_inset'],END_INSET,'user-brief');put(F['end_top_flush'],END_TOP_FLUSH,'user-brief')
for k in ['digital_checks_passed','first_article_passed','production_release']:put(d['review'][k],False,'user-brief')
Path(sys.argv[1]).write_text(json.dumps(d,ensure_ascii=False,indent=1))
print('written',sys.argv[1])
