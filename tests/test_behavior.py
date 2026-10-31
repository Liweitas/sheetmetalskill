import unittest,json,copy,sys,math,tempfile,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from validate_project import validate,diameter,normalized_center_edge,bend_numbers,parameter_hash
from validate_manifest import check
from compare_change import verify_revision,invalidations
from create_intake import build
def example(name):return json.loads((ROOT/'assets/examples'/name).read_text())
def setv(f,v,status=None,source=None):
 f['value']=v
 if status:f['status']=status
 if source:f['source']=[source]
 if status=='assumed':f['note']='test-specified reversible candidate'
def inactive(f):f.update(value=None,status='not_applicable',source=[],note='inactive selected method')
def codes(r):return {e['code'] for e in r['errors']}
class InputBehavior(unittest.TestCase):
 def setUp(self):self.demo_a=example('demo-a.body-only.json');self.demo_b=example('demo-b.lid-clinch.json')
 def test_demo_a_body_only_ten_and_hold(self):
  r=validate(self.demo_a,'cut');self.assertTrue(r['ok']);self.assertEqual(r['status'],'PASS_WITH_HOLD');self.assertFalse(r['certifies_manufacture']);self.assertEqual(sum(g['count']['value'] for g in self.demo_a['hole_groups']),10);self.assertFalse(self.demo_a['requirements']['lid_required']['value']);self.assertFalse(self.demo_a['requirements']['nuts_required']['value'])
 def test_demo_b_lid_clinch_and_handles_are_explicit(self):
  r=validate(self.demo_b,'model');self.assertTrue(r['ok']);self.assertFalse(validate(self.demo_b,'cut')['ok']);self.assertEqual(sum(g['count']['value'] for g in self.demo_b['hole_groups']),18);self.assertEqual(self.demo_b['hole_groups'][2]['laser_size']['magnitude']['value'],5.6);self.assertEqual(self.demo_b['handles']['quantity']['value'],2);self.assertEqual(self.demo_b['requirements']['material']['value'],'304 stainless - synthetic scenario')
 def test_no_lid_plan_expansion(self):
  self.demo_a['fabrication']['parts'].append(copy.deepcopy(self.demo_b['fabrication']['parts'][-1]));r=validate(self.demo_a,'model');self.assertIn('UNREQUESTED_LID',codes(r))
 def test_no_inferred_clinch(self):
  setv(self.demo_a['hole_groups'][0]['type'],'clinch_install');r=validate(self.demo_a,'model');self.assertIn('NUT_SCOPE',codes(r))
 def test_scope_contradiction(self):
  setv(self.demo_a['requirements']['lid_required'],True);self.assertIn('SCOPE_CONFLICT',codes(validate(self.demo_a,'audit')))
 def test_step_lid_does_not_override_body_only_request(self):
  setv(self.demo_a['step_facts']['source_lid_present'],True);r=validate(self.demo_a,'cut');self.assertTrue(r['ok']);self.assertFalse(self.demo_a['requirements']['lid_required']['value'])
 def test_blank_stays_unknown_and_blocks_dependent_model(self):
  schema,b=build();self.assertIsNone(b['requirements']['nominal_t']['value']);self.assertIsNone(b['requirements']['lid_required']['value']);self.assertIsNone(b['bending']['Ri']['value']);self.assertIsNone(b['handles']['quantity']['value']);self.assertFalse(validate(b,'model')['ok'])
 def test_nominal_thread_does_not_supply_pilot(self):
  g=self.demo_a['hole_groups'][0];g['laser_size']['magnitude'].update(value=None,status='unknown',source=[],note=None);self.assertIn('HOLE_SIZE',codes(validate(self.demo_a,'cut')))
 def test_radius_representation_changes_calculation(self):
  g=self.demo_a['hole_groups'][0];setv(g['laser_size']['magnitude'],1.7);setv(g['laser_size']['representation'],'radius');self.assertAlmostEqual(diameter(g['laser_size']),3.4);self.assertTrue(validate(self.demo_a,'cut')['ok'])
 def test_unconverted_radius_detects_wrong_seat_pilot(self):
  setv(self.demo_a['hole_groups'][0]['laser_size']['representation'],'radius');self.assertIn('LASER_PILOT',codes(validate(self.demo_a,'cut')))
 def test_net_ligament_to_center_distance(self):
  e=self.demo_b['hole_groups'][0]['edge'];setv(e['basis'],'net_ligament');setv(e['distance'],6.1);self.assertAlmostEqual(normalized_center_edge(e),8.2);self.assertTrue(validate(self.demo_b,'model')['ok']);setv(e['distance'],6.0);self.assertIn('CLINCH_EDGE',codes(validate(self.demo_b,'cut')))
 def test_source_requirement_layers_not_copied(self):
  self.demo_a['step_facts']['source_material']=copy.deepcopy(self.demo_a['requirements']['material']);self.assertIn('STEP_FACT_STATUS',codes(validate(self.demo_a,'model')))
 def test_missing_core_thickness_blocks(self):
  f=self.demo_a['requirements']['nominal_t'];f.update(value=None,status='unknown',source=[],note=None);self.assertIn('MISSING',codes(validate(self.demo_a,'cut')))
 def test_cone_depth_geometry(self):
  setv(self.demo_a['hole_groups'][0]['seat']['segments'][1]['depth'],1.0);self.assertIn('CONE_GEOMETRY',codes(validate(self.demo_a,'cut')))
 def test_inner_outer_side_cannot_be_omitted(self):
  f=self.demo_a['hole_groups'][0]['seat']['side'];f.update(value=None,status='unknown',source=[],note=None);self.assertIn('MISSING',codes(validate(self.demo_a,'model')))
 def test_counterseat_mouth_not_pilot(self):
  setv(self.demo_a['hole_groups'][0]['laser_size']['magnitude'],5.2);self.assertIn('LASER_PILOT',codes(validate(self.demo_a,'cut')))
 def test_no_universal_remaining_wall_acceptance(self):
  r=validate(self.demo_a,'release');self.assertFalse(r['ok']);self.assertTrue(any(h['code']=='REMAINING_ACCEPTANCE' for h in r['holds']))
 def test_project_remaining_criterion_enforced(self):
  setv(self.demo_a['hole_groups'][0]['seat']['minimum_remaining_accepted'],.6,'confirmed','user');self.assertIn('REMAINING_TOO_THIN',codes(validate(self.demo_a,'model')))
 def test_smaller_remaining_accepted_by_explicit_project_criterion(self):
  b=self.demo_a;b['provenance'].append({'id':'factory','kind':'factory_measurement','ref':'SYNTHETIC calibration inputs only','message_at':None,'recorded_at':None});setv(b['requirements']['measured_t'],1.4,'measured','factory')
  for g in b['hole_groups']:
   seg=g['seat']['segments'];setv(seg[0]['depth'],.1);setv(seg[1]['start_depth'],.1);setv(seg[2]['start_depth'],1.0);setv(seg[2]['depth'],.4);setv(g['seat']['minimum_remaining_accepted'],.3,'confirmed','factory')
  r=validate(b,'model');self.assertTrue(r['ok'],r['errors']);self.assertAlmostEqual(r['computed']['demo-a-seats_remaining_mm'],.4)
 def test_k_and_bd_modes_not_double_applied(self):
  b=self.demo_a['bending'];n=bend_numbers(b,1.6);setv(b['BD90'],n['BD90'],'assumed','trial');self.assertIn('COMPENSATION_CONFLICT',codes(validate(self.demo_a,'cut')));setv(b['compensation_mode'],'bend_deduction');inactive(b['K_value']);inactive(b['K_definition']);r=validate(self.demo_a,'cut');self.assertTrue(r['ok']);self.assertAlmostEqual(r['computed']['bend90']['BA90'],n['BA90'])
 def test_din_and_ansi_are_not_interchangeable_numbers(self):
  b=self.demo_a['bending'];a=bend_numbers(b,1.6);setv(b['K_definition'],'DIN');setv(b['K_value'],.84);self.assertAlmostEqual(bend_numbers(b,1.6)['BA90'],a['BA90'])
 def test_geometric_ba_is_not_backgauge(self):
  setv(self.demo_a['bending']['machine_backgauge'],3.1,'assumed','trial');self.assertIn('BACKGAUGE_SOURCE',codes(validate(self.demo_a,'cut')))
 def test_material_change_invalidates_hardware(self):
  setv(self.demo_b['requirements']['material'],'SYNTHETIC ALTERNATE MATERIAL');self.assertIn('CLINCH_MATERIAL_STALE',codes(validate(self.demo_b,'cut')))
 def test_material_and_t_change_cannot_inherit_calibration(self):
  b=self.demo_a;b['provenance'].append({'id':'factory','kind':'factory_measurement','ref':'synthetic calibration input','message_at':None,'recorded_at':None});setv(b['bending']['calibrated'],True,'measured','factory');setv(b['bending']['calibration_material'],'304 stainless - synthetic scenario','measured','factory');setv(b['bending']['calibration_t'],1.6,'measured','factory');self.assertIn('CALIBRATION_STALE',codes(validate(b,'cut')))
 def test_dependency_plan_reinvalidates_actual_material_change(self):
  a=copy.deepcopy(self.demo_a);setv(a['requirements']['material'],'SYNTHETIC CHANGED MATERIAL');plan=invalidations(self.demo_a,a);self.assertIn('hardware_qualification',plan['invalidate']);self.assertIn('first_article',plan['invalidate'])
 def test_wrong_timezone_and_second_precision(self):
  setv(self.demo_a['project']['version_timezone'],'UTC');self.assertFalse(validate(self.demo_a,'audit')['ok']);self.demo_a=example('demo-a.body-only.json');setv(self.demo_a['project']['version'],'20400102_101500');self.assertIn('VERSION_FORMAT',codes(validate(self.demo_a,'audit')))
 def test_beijing_minute_must_match_timestamp(self):
  setv(self.demo_a['project']['version'],'20400102_1016');self.assertIn('VERSION_TIME_MISMATCH',codes(validate(self.demo_a,'audit')))
 def test_no_unknown_zero_substitution(self):
  self.demo_a['requirements']['measured_t']['value']=0;self.assertIn('UNKNOWN_HAS_VALUE',codes(validate(self.demo_a,'model')))
 def test_nonfinite_input_blocked_not_crashed(self):
  setv(self.demo_a['requirements']['nominal_t'],float('nan'));self.assertIn('NONFINITE',codes(validate(self.demo_a,'model')))
 def test_history_alone_cannot_confirm(self):
  self.demo_a['provenance'].append({'id':'history','kind':'history_reference','ref':'oldjob','message_at':None,'recorded_at':None});setv(self.demo_a['requirements']['material'],'SYNTHETIC ALTERNATE MATERIAL','confirmed','history');self.assertIn('CONFIRMATION_SOURCE',codes(validate(self.demo_a,'model')))
 def test_actual_screw_angle_conflict(self):
  setv(self.demo_a['hardware'][0]['head_angle'],120);self.assertIn('SCREW_SEAT_ANGLE',codes(validate(self.demo_a,'cut')))
 def test_clinch_batch_hardness_above_limit(self):
  b=self.demo_b;b['provenance'].append({'id':'factory','kind':'factory_measurement','ref':'synthetic hardness test','message_at':None,'recorded_at':None});setv(b['requirements']['measured_hardness_HRB'],95,'measured','factory');setv(b['hardware'][1]['max_sheet_hardness_HRB'],90,'confirmed','drawing');self.assertIn('CLINCH_HARDNESS',codes(validate(b,'cut')))
 def test_authorized_interference_scope_retained(self):
  self.assertTrue(validate(self.demo_b,'model')['ok']);setv(self.demo_b['exceptions'][0]['retained'],False);self.assertIn('EXCEPTION_GEOMETRY',codes(validate(self.demo_b,'model')))
 def test_mm_inch_conversion_not_assumed(self):
  setv(self.demo_a['step_facts']['declared_unit'],'inch');self.assertIn('UNIT_SCALE',codes(validate(self.demo_a,'model')));setv(self.demo_a['step_facts']['scale_to_mm'],25.4);self.assertTrue(validate(self.demo_a,'model')['ok'])
 def test_missing_handle_quantity_is_not_inferred(self):
  self.demo_b['handles']['quantity'].update(value=None,status='unknown',source=[],note=None);r=validate(self.demo_b,'cut');self.assertIn('MISSING',codes(r));self.assertIsNone(self.demo_b['handles']['quantity']['value'])
class ArtifactBehavior(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory();self.root=Path(self.t.name);self.p=example('demo-a.body-only.json');self.version=self.p['project']['version']['value']
  # This fixture intentionally tests one supplied sheet, not a complete three-sheet box.
  self.p['fabrication']['method']['value']='keep_source';self.p['fabrication']['parts']=self.p['fabrication']['parts'][:1];self.p['delivery']['formats']['value']=['dxf']
  for g in self.p['hole_groups']:
   g['positions']=[x for x in g['positions'] if x['part_id']=='01'];g['count']['value']=len(g['positions'])
 def tearDown(self):self.t.cleanup()
 def dxf(self,radius=1.7,empty=False,open_outline=False):
  pairs=[(0,'SECTION'),(2,'HEADER'),(9,'$INSUNITS'),(70,4),(0,'ENDSEC'),(0,'SECTION'),(2,'ENTITIES')]
  if not empty:
   points=[(0,0),(190.0,0),(190.0,240.0),(0,240.0)]
   for i in range(3 if open_outline else 4):
    a=points[i];b=points[(i+1)%4];pairs +=[(0,'LINE'),(8,'CUT'),(10,a[0]),(20,a[1]),(30,0),(11,b[0]),(21,b[1]),(31,0)]
   for x in [30.0,90.0,160.0]:
    for y in [20.0,220.0]:pairs +=[(0,'CIRCLE'),(8,'CUT'),(10,x),(20,y),(30,0),(40,radius)]
  pairs +=[(0,'ENDSEC'),(0,'EOF')];path=self.root/('U_'+self.version+'.dxf');path.write_text('\n'.join(str(v) for pair in pairs for v in pair)+'\n');return path
 def manifest(self,path):
  h=parameter_hash(self.p);return {'version':self.version,'timezone':'Asia/Shanghai','parameter_hash':h,'artifacts':[{'path':path.name,'kind':'dxf','stage':'laser','part_ids':['01'],'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'parameter_version':self.version,'parameter_hash':h}]}
 def test_actual_dxf_closed_with_only_pilot_circles(self):
  p=self.dxf();r=check(self.p,self.manifest(p),self.root);self.assertTrue(r['ok'],r['errors']);self.assertFalse(r['certifies_manufacture'])
 def test_actual_mouth_circle_cannot_enter_CUT(self):
  p=self.dxf(radius=2.6);r=check(self.p,self.manifest(p),self.root);self.assertFalse(r['ok']);self.assertTrue(any('pilot' in e for e in r['errors']))
 def test_empty_and_open_dxf_rejected(self):
  for args in [{'empty':True},{'open_outline':True}]:
   p=self.dxf(**args);self.assertFalse(check(self.p,self.manifest(p),self.root)['ok'])
 def test_actual_modified_file_hash_invalidates_pass(self):
  p=self.dxf();m=self.manifest(p);p.write_text(p.read_text()+'\n');self.assertFalse(check(self.p,m,self.root)['ok'])
 def test_cross_version_or_parameter_hash_rejected(self):
  p=self.dxf();m=self.manifest(p);m['artifacts'][0]['parameter_version']='20400101_0910';self.assertFalse(check(self.p,m,self.root)['ok']);m=self.manifest(p);setv(self.p['requirements']['material'],'SYNTHETIC CHANGED MATERIAL');self.assertFalse(check(self.p,m,self.root)['ok'])
 def test_nondefault_extrusion_direction_rejected(self):
  p=self.dxf();p.write_text(p.read_text().replace('40\n1.7\n','40\n1.7\n210\n0\n220\n1\n230\n0\n',1));self.assertFalse(check(self.p,self.manifest(p),self.root)['ok'])
 def test_explicit_default_normal_stays_supported(self):
  p=self.dxf();p.write_text(p.read_text().replace('40\n1.7\n','40\n1.7\n210\n0\n220\n0\n230\n1\n',1));self.assertTrue(check(self.p,self.manifest(p),self.root)['ok'])
 def test_nonzero_entity_thickness_rejected(self):
  p=self.dxf();p.write_text(p.read_text().replace('40\n1.7\n','40\n1.7\n39\n0.5\n',1));self.assertFalse(check(self.p,self.manifest(p),self.root)['ok'])
class NarrowChangeBehavior(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory();self.root=Path(self.t.name)
  def artifact(name,data):p=self.root/name;p.write_bytes(data);return {'file':name,'sha256':hashlib.sha256(data).hexdigest()}
  before=artifact('before.step',b'SYNTHETIC CONTRACT FIXTURE ONLY - no CAD');after=artifact('after.step',b'SYNTHETIC CHANGED HOLE CONTRACT FIXTURE - no CAD');body=artifact('body.step',b'UNCHANGED SYNTHETIC BODY - no CAD')
  h={'center':[10,10,0],'axis':[0,0,1],'diameter_mm':3,'kind':'through_circle','local_t_mm':1.6};p={**before,'bbox_mm':[0,0,0,80,60,1.6],'volume_mm3':1000,'holes':{'H1':h,'H2':{**h,'center':[40,10,0]}}};q=copy.deepcopy(p);q.update(after);q['holes']['H1']['diameter_mm']=3.6;q['volume_mm3']=1000-math.pi/4*(3.6**2-3**2)*1.6
  body.update(bbox_mm=[0,0,0,80,60,1.6],volume_mm3=2000,holes={});self.b={'parts':{'lid':p,'body':body}};self.a={'parts':{'lid':q,'body':copy.deepcopy(body)}};self.w={'method':'CAD_symmetric_difference_outside_edit_regions','evidence_ref':'SYNTHETIC witness fixture, not actual CAD evidence','allowed_holes':['lid:H1'],'baseline_parts_sha256':{k:v['sha256'] for k,v in self.b['parts'].items()},'candidate_parts_sha256':{k:v['sha256'] for k,v in self.a['parts'].items()},'outside_edit_regions_symmetric_difference_mm3':{'lid':0}}
 def tearDown(self):self.t.cleanup()
 def runcheck(self):return verify_revision(self.b,self.a,self.w,self.root,['lid:H1'])
 def test_authorized_handle_diameter_contract(self):
  r=self.runcheck();self.assertTrue(r['ok'],r['errors']);self.assertFalse(r['CAD_computed_by_this_script'])
 def test_other_hole_move_is_detected(self):
  self.a['parts']['lid']['holes']['H2']['center'][0]+=1;self.assertFalse(self.runcheck()['ok'])
 def test_edit_outside_authorized_region_detected(self):
  self.w['outside_edit_regions_symmetric_difference_mm3']['lid']=.01;self.assertFalse(self.runcheck()['ok'])
 def test_missing_or_stale_actual_CAD_witness(self):
  self.w['baseline_parts_sha256']['lid']='0'*64;self.assertFalse(self.runcheck()['ok']);self.w={};self.assertFalse(self.runcheck()['ok'])
 def test_unaffected_part_byte_change_detected(self):
  p=self.root/'different_body.step';p.write_bytes(b'DIFFERENT SYNTHETIC BODY');self.a['parts']['body'].update(file=p.name,sha256=hashlib.sha256(p.read_bytes()).hexdigest());self.w['candidate_parts_sha256']['body']=self.a['parts']['body']['sha256'];self.assertFalse(self.runcheck()['ok'])
 def test_unexplained_volume_change_detected(self):
  self.a['parts']['lid']['volume_mm3']+=.1;self.assertFalse(self.runcheck()['ok'])
 def test_missing_volume_is_not_silently_zero(self):
  del self.a['parts']['lid']['volume_mm3'];self.assertFalse(self.runcheck()['ok'])
if __name__=='__main__':unittest.main()
