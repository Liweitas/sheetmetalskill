import unittest,json,copy,sys,tempfile,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/"scripts"))
from design_job import resolve_job,project_for
from validate_project import validate,parameter_hash
from validate_manifest import check
from create_intake import apply_project_defaults
class BoxWorkflow(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.job=json.loads((ROOT/"assets/examples/box-wrap-l.job.json").read_text())
 def tearDown(self):self.tmp.cleanup()
 def project(self,j=None):
  j=j or self.job;p=self.root/"job.json";p.write_text(json.dumps(j));return project_for(j,resolve_job(j),p,"20261021_1200","2026-10-21T12:00:00+08:00")
 def codes(self,p):return {x["code"] for x in validate(p,"model")["errors"]}
 def test_ul_selector_result_is_valid_canonical_schema(self):
  p=self.project();self.assertEqual(p["fabrication"]["method"]["value"],"u_wrap_bottom_l");self.assertTrue(validate(p,"model")["ok"])
 def test_default_roles_have_real_u_l_lid(self):
  p=self.project();self.assertEqual([x["role"]["value"] for x in p["fabrication"]["parts"]],["u_body","bottom_l","lid"])
 def test_external_route_has_exactly_two_ends(self):
  j=json.loads((ROOT/"assets/examples/box-external.job.json").read_text());p=self.project(j);self.assertTrue(validate(p,"model")["ok"]);self.assertEqual([x["id"] for x in p["fabrication"]["parts"]],["U","END_L","END_R","LID"])
 def test_no_l_cannot_pass(self):
  p=self.project();p["fabrication"]["parts"]=[x for x in p["fabrication"]["parts"] if x["id"]!="L"];self.assertIn("UL_PARTS",self.codes(p))
 def test_missing_lid_cannot_pass(self):
  p=self.project();p["fabrication"]["parts"]=[x for x in p["fabrication"]["parts"] if x["id"]!="LID"];self.assertIn("LID_PARTS",self.codes(p))
 def test_wrong_l_bends_cannot_pass(self):
  p=self.project();p["fabrication"]["parts"][1]["bends"]["value"]=0;self.assertIn("UL_BENDS",self.codes(p))
 def test_cut_requires_real_geometry_evidence(self):
  self.assertFalse(validate(self.project(),"cut")["ok"])
 def test_explicit_structural_override_is_preserved(self):
  self.job["dimensions"]={"length":240,"width":150,"height":100};self.job["method"]="u_wrap_bottom_l";p=self.project();self.assertTrue(validate(p,"model")["ok"]);self.assertEqual(p["fabrication"]["method"]["value"],"u_wrap_bottom_l")
 def test_existing_without_explicit_rebuild_is_blocked(self):
  self.job["record_kind"]="existing"
  with self.assertRaisesRegex(ValueError,"EXISTING_PROTECTED"):resolve_job(self.job)
 def test_existing_explicit_rebuild_does_not_apply_dimension_default(self):
  self.job.update(record_kind="existing",rebuild_existing_authorized=True,method="u_external_ends");self.job['lid'].update(g=.7,corner_scheme='03');self.assertEqual(resolve_job(self.job)["method"],"u_external_ends");self.assertEqual(resolve_job(self.job)['g'],.7)
 def test_existing_lid_cannot_acquire_new_g_or_corner_defaults(self):
  self.job.update(record_kind='existing',rebuild_existing_authorized=True,method='u_external_ends')
  with self.assertRaisesRegex(ValueError,'EXISTING_PROTECTED'):resolve_job(self.job)
 def test_no_lid_does_not_create_lid(self):
  self.job["lid_required"]=False;self.job.pop("lid");p=self.project();self.assertNotIn("lid",[x["role"]["value"] for x in p["fabrication"]["parts"]]);self.assertIsNone(p["lid"]["corner_scheme"]["value"]);self.assertTrue(validate(p,"model")["ok"])
 def test_no_lid_forbids_active_lid_input(self):
  self.job["lid_required"]=False
  with self.assertRaisesRegex(ValueError,"No-lid"):resolve_job(self.job)
 def test_default_is_rechecked_after_dimensions_change(self):
  p=self.project();p["requirements"]["dimensions"]["X"]["value"]=400;self.assertIn("STRUCTURE_DEFAULT_STALE",self.codes(p))
 def test_missing_radius_blocks_before_cad(self):
  self.job.pop("Ri")
  with self.assertRaisesRegex(ValueError,"JOB_SCHEMA"):resolve_job(self.job)
 def test_missing_k_blocks_before_cad(self):
  self.job.pop("K_ANSI")
  with self.assertRaisesRegex(ValueError,"JOB_SCHEMA"):resolve_job(self.job)
 def test_missing_q_does_not_get_silently_defaulted(self):
  self.job["lid"].pop("roof_gap")
  with self.assertRaisesRegex(ValueError,"JOB_SCHEMA"):resolve_job(self.job)
 def test_corner_override_is_blocked_without_supported_adapter(self):
  self.job["lid"]["corner_scheme"]="clover"
  with self.assertRaisesRegex(ValueError,"UNSUPPORTED_CORNER_ADAPTER"):resolve_job(self.job)
 def test_wrong_hole_owner_blocks_before_cad(self):
  self.job["holes"]=[{"id":"h","part_id":"END_L","diameter":4,"point":[0,10,10],"axis":[1,0,0]}]
  with self.assertRaisesRegex(ValueError,"Hole owner"):resolve_job(self.job)
 def test_units_and_default_g_are_mm_consistent(self):
  self.job["units"]="cm";self.job["dimensions"]={"length":12,"width":10,"height":20};self.job["thickness"]=.12;self.job["Ri"]=.08;self.job["seam_gap"]=.01;self.job["lid"]={"skirt_height":1.6,"corner_gap":.02,"roof_gap":0};r=resolve_job(self.job);self.assertAlmostEqual(r["g"],.5);self.assertAlmostEqual(r["t"],1.2);self.assertEqual(r["method"],"u_wrap_bottom_l")
 def test_empty_dxf_coverage_cannot_pass_even_if_manifest_has_pdf(self):
  p=self.project();m={"version":p["project"]["version"]["value"],"timezone":"Asia/Shanghai","parameter_hash":parameter_hash(p),"artifacts":[]};r=check(p,m,self.root);self.assertFalse(r["ok"]);self.assertTrue(any("DXF_PART_COVERAGE" in e for e in r["errors"]))
 def test_duplicate_sheet_dxf_coverage_cannot_pass(self):
  p=self.project();v=p["project"]["version"]["value"];h=parameter_hash(p);a={"path":"missing_"+v+".dxf","kind":"dxf","part_ids":["U","L","LID"],"parameter_version":v,"parameter_hash":h,"sha256":"0"*64};r=check(p,{"version":v,"timezone":"Asia/Shanghai","parameter_hash":h,"artifacts":[a,a]},self.root);self.assertTrue(any("DXF_PART_COVERAGE" in e for e in r["errors"]))
 def test_first_article_cannot_be_inferred_from_cad(self):
  p=self.project();self.assertFalse(validate(p,"release")["ok"]);self.assertFalse(p["review"]["production_release"]["value"])
 def test_nonfinite_and_unknown_features_block(self):
  self.job["Ri"]=float("nan")
  with self.assertRaises(ValueError):resolve_job(self.job)
  self.job["Ri"]=.8;self.job["inward_rim_width"]=20
  with self.assertRaisesRegex(ValueError,"JOB_SCHEMA"):resolve_job(self.job)
 def test_native03_missing_body_blocks_before_CAD_import(self):
  from native03_check import verify
  with self.assertRaisesRegex(ValueError,'body STEP is required'):verify({},None,None,None)
 def test_native03_guards_survive_python_optimization(self):
  code='import sys;sys.path.insert(0,'+repr(str(ROOT/'scripts'))+');from native03_check import require;require(False,"guard remains active")'
  result=subprocess.run([sys.executable,'-B','-O','-c',code],capture_output=True,text=True)
  self.assertNotEqual(result.returncode,0);self.assertIn('guard remains active',result.stderr)
if __name__=="__main__":unittest.main()
