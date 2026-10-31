import copy,json,tempfile,unittest,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from delivery_contract import *
class DeliveryContractTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
  self.job={'id':'TEST','delivery':{'namespace':'customer','entity_id':'C_TEST','revision':'R01','sets':2,'stock':{'length_mm':500,'width_mm':300,'edge_margin_mm':10,'part_gap_mm':8,'status':'assumed','source':'synthetic unit test'}}};self.d=resolved_delivery(self.job)
  self.dxfs={}
  for name,(w,h) in {'U':(120,80),'END':(70,65)}.items():
   es=[{'type':'LINE',10:a[0],20:a[1],11:b[0],21:b[1]} for a,b in zip([(0,0),(w,0),(w,h),(0,h)],[(w,0),(w,h),(0,h),(0,0)])];es.append({'type':'CIRCLE',10:20,20:20,40:3});p=self.root/(name+'.dxf');write_entities(p,es);self.dxfs[name]=p
  self.layout=layout_parts(self.dxfs,self.d);self.nests=self.write(self.layout)
 def tearDown(self):self.tmp.cleanup()
 def write(self,layout):
  paths={}
  for s in range(1,layout['required_sheets']+1):
   p=self.root/f'board{s}.dxf';es=[translate(e,*x['translation_mm']) for x in layout['placements'] if x['sheet']==s for e in parse_dxf(self.dxfs[x['part_id']])];write_entities(p,es);paths[s]=p
  return paths
 def test_exact_entities_quantities_and_spacing(self):self.assertTrue(check_nest(self.layout,self.dxfs,self.nests)['ok'])
 def test_missing_instance(self):
  l=copy.deepcopy(self.layout);l['placements'].pop()
  with self.assertRaisesRegex(ValueError,'QUANTITY'):check_nest(l,self.dxfs,self.write(l))
 def test_overlap_with_rebound_layout(self):
  l=copy.deepcopy(self.layout);a,b=l['placements'][:2];b['translation_mm']=[v+3 for v in a['translation_mm']];b['bbox_mm']=[v+3 for v in a['bbox_mm']];b['sheet']=a['sheet']
  with self.assertRaisesRegex(ValueError,'OVERLAP'):check_nest(l,self.dxfs,self.write(l))
 def test_double_scale_dxf(self):
  for p in self.nests.values():
   es=parse_dxf(p)
   for e in es:
    for k in [10,20,11,21,40]:
     if k in e:e[k]=float(e[k])*2
   write_entities(p,es)
  with self.assertRaisesRegex(ValueError,'GEOMETRY_SCALE'):check_nest(self.layout,self.dxfs,self.nests)
 def test_duplicate_line_blocked(self):
  es=parse_dxf(next(iter(self.nests.values())));es.append(copy.deepcopy(es[0]))
  with self.assertRaisesRegex(ValueError,'duplicate'):write_entities(self.root/'duplicate.dxf',es)
 def test_cut_layer_and_units(self):
  p=next(iter(self.nests.values()));p.write_text(p.read_text().replace('CUT','BEND'))
  with self.assertRaisesRegex(ValueError,'CUT layer'):check_nest(self.layout,self.dxfs,self.nests)
 def test_wrong_stock_margin(self):
  l=copy.deepcopy(self.layout);l['stock']['edge_margin_mm']=20
  with self.assertRaisesRegex(ValueError,'MARGIN'):check_nest(l,self.dxfs,self.nests)
 def test_revision_immutable(self):
  root,d=revision_root(self.root,self.job);root.mkdir(parents=True)
  with self.assertRaisesRegex(ValueError,'REVISION_EXISTS'):revision_root(self.root,self.job)
 def test_missing_customer_is_requirement_namespace(self):
  d=resolved_delivery({'id':'REQ003'});self.assertEqual(d['namespace'],'requirement');self.assertEqual(d['entity_id'],'REQ003')
 def test_unknown_stock_is_candidate(self):self.assertEqual(resolved_delivery({'id':'X'})['stock']['status'],'assumed')
 def test_stock_requires_source_and_status(self):
  j=copy.deepcopy(self.job);j['delivery']['stock'].pop('source')
  with self.assertRaisesRegex(ValueError,'DELIVERY_INPUT'):resolved_delivery(j)
 def test_stock_quantity_insufficient(self):
  d=copy.deepcopy(self.d);d['stock'].update(length_mm=160,width_mm=110,available_sheets=1)
  with self.assertRaisesRegex(ValueError,'QUANTITY_INSUFFICIENT'):layout_parts(self.dxfs,d)
 def test_oversize_no_silent_scaling(self):
  d=copy.deepcopy(self.d);d['stock']['length_mm']=60
  with self.assertRaisesRegex(ValueError,'OVERSIZE'):layout_parts(self.dxfs,d)
 def test_corner_stub_is_not_flange_gauging_edge(self):
  from workshop_pdf import datum_for
  part={'outer_boundary_entity_indices':[0,1],'records':[{'type':'LINE','p':[14,0],'q':[14,14]},{'type':'LINE','p':[0,0],'q':[0,260]}]}
  bend={'flat_line_mm':[[15,15],[15,245]]};d=datum_for(part,bend)
  self.assertEqual(d['DXF_entity_index'],1);self.assertAlmostEqual(d['distance_to_bend_center_mm'],15)
if __name__=='__main__':unittest.main()
