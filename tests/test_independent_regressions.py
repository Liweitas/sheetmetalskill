"""Regression inputs from independent adversarial review, synthetic files only."""
import copy,math,unittest
from test_behavior import InputBehavior,ArtifactBehavior,NarrowChangeBehavior,setv,codes
from validate_project import validate
from validate_manifest import check
from compare_change import verify_revision
class IntakeRegressions(InputBehavior):
 def test_unknown_bends_cannot_bypass_cut_compensation(self):
  for p in self.demo_a['fabrication']['parts']:p['bends'].update(value=None,status='unknown',source=[],note=None)
  for f in self.demo_a['bending'].values():f.update(value=None,status='unknown',source=[],note=None)
  self.assertFalse(validate(self.demo_a,'cut')['ok'])
 def test_U_cannot_claim_zero_bends(self):
  setv(self.demo_a['fabrication']['parts'][0]['bends'],0);self.assertIn('U_BENDS',codes(validate(self.demo_a,'cut')))
 def test_zero_target_dimension_rejected(self):
  setv(self.demo_a['requirements']['dimensions']['X'],0);self.assertIn('DIMENSION_POSITIVE',codes(validate(self.demo_a,'cut')))
 def test_clinch_role_must_be_nut(self):
  setv(self.demo_b['hardware'][1]['role'],'screw');self.assertIn('CLINCH_ROLE',codes(validate(self.demo_b,'cut')))
class SnapshotRegressions(NarrowChangeBehavior):
 def test_empty_snapshot_rejected(self):
  self.assertFalse(verify_revision({'parts':{}},{'parts':{}},self.w,self.root,['lid:H1'])['ok'])
 def test_bad_bboxes_rejected_without_crash(self):
  for box in [[float('nan')]*6,['x',0,0,100,100,1.6],[0,0,0,0,100,1.6],[0,0,0]]:
   with self.subTest(box=box):
    a=copy.deepcopy(self.a);a['parts']['lid']['bbox_mm']=box;self.assertFalse(verify_revision(self.b,a,self.w,self.root,['lid:H1'])['ok'])
 def test_bad_hole_inputs_rejected_without_crash(self):
  for key,v in [('diameter_mm',float('nan')),('diameter_mm',-3.6),('diameter_mm','3.6'),('center','wrong type'),('axis',[0,0,2]),('local_t_mm',0)]:
   with self.subTest(key=key,value=v):
    a=copy.deepcopy(self.a);a['parts']['lid']['holes']['H1'][key]=v;self.assertFalse(verify_revision(self.b,a,self.w,self.root,['lid:H1'])['ok'])
 def test_nan_diameter_cannot_hide_volume_loss(self):
  self.a['parts']['lid']['holes']['H1']['diameter_mm']=float('nan');self.a['parts']['lid']['volume_mm3']=1;self.assertFalse(self.runcheck()['ok'])
class PlanarRegressions(ArtifactBehavior):
 def test_bowtie_closed_but_self_intersecting_rejected(self):
  p=self.dxf();s=p.read_text()
  # Use explicit segments for unambiguous self-crossing polygon.
  lines=s.splitlines();pairs=list(zip(lines[::2],lines[1::2]));start=next(i for i,x in enumerate(pairs) if x==('2','ENTITIES'))+1;end=next(i for i in range(start,len(pairs)) if pairs[i]==('0','CIRCLE'));pts=[(0,0),(190.0,240.0),(0,240.0),(190.0,0)];new=[]
  for a,b in zip(pts,pts[1:]+pts[:1]):new +=[(0,'LINE'),(8,'CUT'),(10,a[0]),(20,a[1]),(11,b[0]),(21,b[1])]
  pairs=pairs[:start]+new+pairs[end:];p.write_text('\n'.join(str(v) for pair in pairs for v in pair)+'\n');self.assertFalse(check(self.p,self.manifest(p),self.root)['ok'])
 def test_all_pilots_outside_outline_rejected(self):
  p=self.dxf();s=p.read_text()
  for x in [30.0,90.0,160.0]:s=s.replace('10\n'+str(x)+'\n','10\n'+str(x+10000)+'\n')
  p.write_text(s);self.assertFalse(check(self.p,self.manifest(p),self.root)['ok'])
 def test_missing_EOF_rejected(self):
  p=self.dxf();p.write_text(p.read_text().replace('0\nEOF\n',''));self.assertFalse(check(self.p,self.manifest(p),self.root)['ok'])
# Inherit fixture helpers, not their test methods: collect only new independent regressions.
for cls,base in [(IntakeRegressions,InputBehavior),(SnapshotRegressions,NarrowChangeBehavior),(PlanarRegressions,ArtifactBehavior)]:
 for name in dir(base):
  if name.startswith('test_') and name not in cls.__dict__:setattr(cls,name,None)
del InputBehavior,ArtifactBehavior,NarrowChangeBehavior,cls,base
if __name__=='__main__':unittest.main()
