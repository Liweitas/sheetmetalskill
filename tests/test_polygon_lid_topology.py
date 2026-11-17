import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from dxf_topology import largest_closed_loop_indices,validate_planar

def rectangle(x,y,w,h):
 points=[(x,y),(x+w,y),(x+w,y+h),(x,y+h)]
 return [{'type':'LINE',10:a[0],20:a[1],11:b[0],21:b[1]} for a,b in zip(points,points[1:]+points[:1])]
class PolygonLidTopology(unittest.TestCase):
 def test_inner_rectangle_is_not_mistaken_for_an_outer_boundary(self):
  entities=rectangle(10,10,20,30)+rectangle(0,0,100,100)+[{'type':'CIRCLE',10:70,20:70,40:3}]
  indices=largest_closed_loop_indices(entities)
  self.assertEqual(set(indices),set(range(4,8)))
  result=validate_planar(entities,indices)
  self.assertEqual(result['inner_polygonal_openings'],1)
  self.assertEqual(result['circle_holes'],1)
 def test_polygon_crossing_exterior_is_rejected(self):
  entities=rectangle(90,90,20,20)+rectangle(0,0,100,100)
  with self.assertRaises(ValueError):validate_planar(entities,largest_closed_loop_indices(entities))
 def test_circle_crossing_rectangle_is_rejected(self):
  entities=rectangle(10,10,20,30)+rectangle(0,0,100,100)+[{'type':'CIRCLE',10:30,20:20,40:3}]
  with self.assertRaises(ValueError):validate_planar(entities,largest_closed_loop_indices(entities))
