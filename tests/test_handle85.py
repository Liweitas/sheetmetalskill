import unittest,json,copy,sys,tempfile,subprocess,hashlib
from pathlib import Path
import handle85_fixture as fx
ROOT=fx.ROOT;sys.path.insert(0,str(ROOT/'scripts'))
from create_intake import build,apply_project_defaults
from migrate_project import migrate
from validate_project import validate,parameter_hash
from handle_readback import contracts,check_dxf,measure_pattern,mapped
from validate_manifest import check

def change(f,v,status='confirmed',source='user'):f.update(value=v,status=status,source=[source],note='Fictional independent project input')
def unknown(f):f.update(value=None,status='unknown',source=[],note=None)
MAP={'handle-A':[1,0,0,0,0,1,0,0]}
class HandlePolicies(unittest.TestCase):
 def test_scope_unknown_policy85_but_actual_pitch_unknown(self):
  _,d=build();self.assertEqual(d['policies']['handle_trapezoid_wide_pitch']['value'],85);self.assertIsNone(d['handles']['wide_row_pitch']['value']);self.assertIsNone(d['handles']['quantity']['value'])
 def test_explicit_four_hole_layout_only_defaults_wide85(self):
  _,d=build(handle_layout='four_hole_trapezoid');h=d['handles'];self.assertEqual(h['wide_row_pitch']['value'],85);self.assertEqual(h['wide_row_pitch']['status'],'default');self.assertEqual(h['holes_per_handle']['value'],4)
  for k in ['quantity','narrow_row_pitch','row_spacing']:self.assertIsNone(h[k]['value'])
  self.assertEqual(d['hole_groups'],[])
 def test_other_layout_no_pitch_default(self):
  _,d=build(handle_layout='other');self.assertIsNone(d['handles']['wide_row_pitch']['value'])
 def test_does_not_infer_layout_from_holes_count(self):
  _,d=build();change(d['handles']['enabled'],True,source='policy-timezone');change(d['handles']['holes_per_handle'],4,source='policy-timezone');self.assertIsNone(apply_project_defaults(d)['handles']['wide_row_pitch']['value'])
 def test_existing_unknown_not_auto_rewritten(self):
  d=fx.fixture();unknown(d['handles']['wide_row_pitch']);change(d['project']['record_kind'],'existing',source='policy-timezone');self.assertIsNone(apply_project_defaults(d)['handles']['wide_row_pitch']['value'])
 def test_explicit_old84_preserved_by_migration_not_default(self):
  d=fx.fixture();change(d['handles']['wide_row_pitch'],84);d['schema_version']='2.1.0';before=copy.deepcopy(d);x=migrate(d);self.assertEqual(d,before);self.assertEqual(x['handles']['wide_row_pitch'],d['handles']['wide_row_pitch']);self.assertEqual(x['project']['record_kind']['value'],'existing')
 def test_other_explicit_pitches_sources_remain_unchanged(self):
  d=fx.fixture()
  for k,x in [('narrow_row_pitch',59),('row_spacing',27)]:change(d['handles'][k],x)
  before=copy.deepcopy(d);after=apply_project_defaults(d);self.assertEqual(d,before)
  for k in ['narrow_row_pitch','row_spacing']:self.assertEqual(after['handles'][k],before['handles'][k])
  self.assertEqual(after['hole_groups'][0]['laser_size'],before['hole_groups'][0]['laser_size'])
 def test_no_handle_is_not_applicable_no_auto_add(self):
  _,d=build();change(d['handles']['enabled'],False,source='policy-timezone');x=apply_project_defaults(d)
  for k in ['layout','wide_row_pitch','narrow_row_pitch','row_spacing']:self.assertEqual(x['handles'][k]['status'],'not_applicable')
  self.assertEqual(x['handles']['patterns'],[])
 def test_default84_cannot_masquerade_as85(self):
  d=fx.fixture();d['handles']['wide_row_pitch']['value']=84;r=validate(d,'model');self.assertIn('DEFAULT_HANDLE_PITCH',{q['code'] for q in r['errors']})
 def test_model85_passes_other_unknowns_hold(self):
  r=validate(fx.fixture(),'cut');self.assertTrue(r['ok'],r['errors']);self.assertEqual(r['computed']['handle_patterns'][0]['wide_row_pitch_mm'],85);self.assertIn('HANDLE_OTHER_DIMENSION_UNKNOWN',{q['code'] for q in r['holds']})
 def test_planned84_cannot_pass_current_default85(self):
  d=fx.fixture();d['hole_groups'][0]['positions'][0]['center']['value'][0]+=.5;d['hole_groups'][0]['positions'][1]['center']['value'][0]-=.5;self.assertIn('HANDLE_PATTERN',{q['code'] for q in validate(d,'cut')['errors']})
 def test_nonreused_four_hole_membership_required(self):
  d=fx.fixture();d['handles']['patterns'][0]['narrow_hole_ids'][0]='HW1';self.assertRaises(ValueError,contracts,d)
 def test_wide_narrow_pair_swap_rejected(self):
  d=fx.fixture();p=d['handles']['patterns'][0];p['wide_hole_ids'],p['narrow_hole_ids']=p['narrow_hole_ids'],p['wide_hole_ids'];self.assertRaises(ValueError,contracts,d)
 def test_handle_quantity_not_derived(self):
  d=fx.fixture();unknown(d['handles']['quantity']);self.assertIn('MISSING',{q['code'] for q in validate(d,'model')['errors']});self.assertIsNone(d['handles']['quantity']['value'])
 def test_incomplete_instance_mapping_blocks(self):
  d=fx.fixture();d['handles']['patterns']=[];self.assertRaises(ValueError,contracts,d)
class ActualHandleDXF(unittest.TestCase):
 def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.p=fx.fixture();self.p['delivery']['formats']['value']=['dxf'];self.path=self.root/'cut.dxf'
 def tearDown(self):self.tmp.cleanup()
 def test_actual85_circle_centers_pass(self):
  fx.write_dxf(self.path);r=check_dxf(self.p,self.path,MAP,['01']);self.assertEqual(r['patterns'][0]['wide_row_pitch_mm'],85);self.assertFalse(r['manufacturing_tolerance_inferred'])
 def test_same_count_diameter_but84_centers_block(self):
  fx.write_dxf(self.path,wide=84);self.assertRaises(ValueError,check_dxf,self.p,self.path,MAP,['01'])
 def test_label85_does_not_override_actual84_geometry(self):
  fx.write_dxf(self.path,wide=84);self.path.write_text('999\n85.00mm\n'+self.path.read_text());self.assertRaises(ValueError,check_dxf,self.p,self.path,MAP,['01'])
 def test_wide85_does_not_supply_diameter(self):
  fx.write_dxf(self.path);unknown(self.p['hole_groups'][0]['laser_size']['magnitude']);self.assertRaises(ValueError,check_dxf,self.p,self.path,MAP,['01'])
 def test_wrong_diameter_blocks_even_with_correct85(self):
  fx.write_dxf(self.path,D=5.4);self.assertRaises(ValueError,check_dxf,self.p,self.path,MAP,['01'])
 def test_missing_flat_map_blocks(self):
  fx.write_dxf(self.path);self.assertRaises(ValueError,check_dxf,self.p,self.path,{},['01'])
 def test_scaling_map_cannot_disguise84(self):
  fx.write_dxf(self.path,wide=84);self.assertRaises(ValueError,check_dxf,self.p,self.path,{'handle-A':[84/85,0,0,1,0,1,0,0]},['01'])
 def test_axis_in_plane_blocks(self):
  self.p['hole_groups'][0]['positions'][0]['axis']['value']=[1,0,0];self.assertRaises(ValueError,contracts,self.p)
 def test_rotated_translated_flat_dxf_supported(self):
  fx.write_dxf(self.path);lines=self.path.read_text().splitlines();pairs=[(int(lines[i]),lines[i+1]) for i in range(0,len(lines),2)];out=[];i=0
  while i<len(pairs):
   if pairs[i][0] in [10,11] and pairs[i+1][0] in [20,21]:
    k,x=pairs[i];ky,y=pairs[i+1];out.extend([(k,200-float(y)),(ky,20+float(x))]);i+=2
   else:out.append(pairs[i]);i+=1
  self.path.write_text('\n'.join(str(v) for q in out for v in q)+'\n');r=check_dxf(self.p,self.path,{'handle-A':[0,-1,0,200,1,0,0,20]},['01']);self.assertEqual(r['patterns'][0]['wide_row_pitch_mm'],85)
 def test_manifest_requires_actual_STEP_evidence(self):
  version=self.p['project']['version']['value'];self.path=self.root/('cut_'+version+'.dxf');fx.write_dxf(self.path);h=parameter_hash(self.p);m={'version':version,'timezone':'Asia/Shanghai','parameter_hash':h,'artifacts':[{'path':self.path.name,'kind':'dxf','stage':'laser','part_ids':['01'],'parameter_hash':h,'parameter_version':version,'sha256':hashlib.sha256(self.path.read_bytes()).hexdigest()}]};r=check(self.p,m,self.root);self.assertFalse(r['ok']);self.assertTrue(any('handle_geometry_report' in x for x in r['errors']))
 def test_manifest_circle_counts_stay_numeric_after_handle_readback(self):
  version=self.p['project']['version']['value'];self.path=self.root/('cut_'+version+'.dxf');fx.write_dxf(self.path);h=parameter_hash(self.p);step=self.root/'synthetic-evidence-contract.step';step.write_bytes(b'SOFTWARE BINDING FIXTURE ONLY; NOT CAD')
  report={'ok':True,'CAD_executed':True,'parameter_hash':h,'input_sha256':{'formed_step':hashlib.sha256(step.read_bytes()).hexdigest(),'dxf':hashlib.sha256(self.path.read_bytes()).hexdigest()},'flat_maps':MAP,'STEP':{'patterns':[{'pattern_id':'handle-A'}]},'note':'SIMULATED report for evidence-binding test only, not actual CAD execution'}
  (self.root/'report.json').write_text(json.dumps(report));m={'version':version,'timezone':'Asia/Shanghai','parameter_hash':h,'artifacts':[{'path':self.path.name,'kind':'dxf','stage':'laser','part_ids':['01'],'parameter_hash':h,'parameter_version':version,'sha256':hashlib.sha256(self.path.read_bytes()).hexdigest(),'formed_step':step.name,'handle_geometry_report':'report.json'}]};result=check(self.p,m,self.root);self.assertTrue(result['ok'],result['errors']);self.assertEqual(result['checks'][0]['circle_diameter_counts'],{5.2:4})
 def test_report_output_cannot_overwrite_actual_source(self):
  fx.write_dxf(self.path);b=self.path.read_bytes();p=self.root/'project.json';p.write_text(json.dumps(self.p));maps=self.root/'maps.json';maps.write_text(json.dumps(MAP));run=subprocess.run([sys.executable,str(ROOT/'scripts/handle_readback.py'),str(p),'--step',str(self.path),'--dxf',str(self.path),'--flat-maps',str(maps),'--output',str(self.path)],capture_output=True);self.assertNotEqual(run.returncode,0);self.assertEqual(self.path.read_bytes(),b)
if __name__=='__main__':unittest.main()
