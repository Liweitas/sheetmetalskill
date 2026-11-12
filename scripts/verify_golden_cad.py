"""Read exported STEP and CUT DXF, including the closed assembly's true bounds."""
import json
import sys
from pathlib import Path
import FreeCAD
import Part
import ezdxf

root, source = map(Path, sys.argv[1:3])
job = json.loads(source.read_text())
work = root / 'work'
stage = root / 'stage' / job['release']
rep = json.loads((work / 'report.json').read_text())


def circles(shape, roof=None):
    result = set()
    for edge in shape.Edges:
        curve = edge.Curve
        if isinstance(curve, Part.Circle) and edge.isClosed() and abs(curve.Axis.z) > .999999:
            if roof is None or abs(curve.Center.z-roof) < 1e-5:
                result.add(tuple(round(v, 5) for v in (curve.Center.x, curve.Center.y, 2*curve.Radius)))
    return result


assembly = Part.read(str(work / 'ASSEMBLY.step'))
size = [assembly.BoundBox.XLength, assembly.BoundBox.YLength, assembly.BoundBox.ZLength]
assert assembly.isValid() and len(assembly.Solids) == len(rep['parts'])
assert all(abs(a-b) < 1e-5 for a, b in zip(size, job['finished_outer_mm'])), size
expected = set()
for hole in job['lid_ports']:
    x, y, d = hole['x'], hole['y'], hole['d']
    expected.add((x, y, d))
    if hole.get('d_bolt'):
        expected.update((x+sx*hole['pitch']/2, y+sy*hole['pitch']/2, hole['d_bolt'])
                        for sx in (-1, 1) for sy in (-1, 1))
expected.update((h['x'], h['y'], h['d']) for h in rep['handle_holes'])
expected = {tuple(round(v, 5) for v in row) for row in expected}
lid = Part.read(str(work / 'LID.step'))
assert circles(lid, job['H']) == expected
panel_readback = []
for hole in job.get('panel_holes', []):
    shape = Part.read(str(work / (hole['part_id']+'.step')))
    point, axis, diameter = FreeCAD.Vector(*hole['point']), FreeCAD.Vector(*hole['axis']), hole['diameter']
    matches = [e.Curve for e in shape.Edges if isinstance(e.Curve, Part.Circle) and e.isClosed()
               and abs(2*e.Curve.Radius-diameter) < 1e-5
               and e.Curve.Axis.cross(axis).Length < 1e-5
               and (e.Curve.Center-point).cross(axis).Length < 1e-5]
    assert len(matches) == 2, (hole['id'], len(matches))
    panel_readback.append(hole)
for opening in job.get('rect_cutouts', []):
    shape = Part.read(str(work / (opening['part_id']+'.step')))
    from rect_cutout_tool import rounded_rect_prism
    cutter = rounded_rect_prism(opening['center'], opening['size_xy'], opening.get('corner_radius', 0), opening['axis'], length=2*job['t']+4)
    assert shape.common(cutter).Volume < 1e-4, opening['id']
    expected_width, expected_height = opening['size_xy']
    cy, cz = opening['center'][1:]
    candidates = []
    for face in shape.Faces:
        if isinstance(face.Surface, Part.Plane) and abs(abs(face.normalAt(0,0).x)-1)<1e-6:
            for wire in face.Wires:
                b = wire.BoundBox
                if abs(b.YLength-expected_width)<1e-5 and abs(b.ZLength-expected_height)<1e-5:
                    candidates.append((b.YMin,b.YMax,b.ZMin,b.ZMax))
    if job['structure'] == 'u_l_t7u':
        assert len(candidates) == 2, candidates
        assert all(abs((a+b)/2-cy)<1e-5 and abs((c+d)/2-cz)<1e-5 for a,b,c,d in candidates)
for part in rep['parts']:
    formed = Part.read(str(work / (part+'.step')))
    assert formed.isValid() and len(formed.Solids) == 1
    flat = Part.read(str(work / (part+'_UNFOLD.step')))
    actual = {tuple(round(v, 5) for v in (e.dxf.center.x, e.dxf.center.y, 2*e.dxf.radius))
              for e in ezdxf.readfile(stage / 'DXF_CUT' / (job['release']+'_CUT_'+part+'.dxf')).modelspace().query('CIRCLE')}
    assert actual == circles(flat), part
    if part == 'LID':
        offset = (rep['parts']['LID']['flat_size'][0]-job['L'])/2
        assert {tuple(round(v, 5) for v in (x+offset, y+offset, d))
                for x, y, d in expected}.issubset(actual)
assert max(rep['intersections_mm3'].values()) < 1e-3
assert len(rep['hole_coaxial']) == len(rep['holes'])
assert all(c['axis_line_material_lid_mm'] < 1e-5 and c['axis_line_material_body_mm'] < 1e-5
           for c in rep['hole_coaxial'])
result = {'pass': True, 'release': job['release'], 'finished_outer_from_STEP_mm': size,
          'roof_holes_from_STEP': sorted(expected),
          'panel_holes_from_STEP': panel_readback,
          'rect_cutouts_open_in_STEP': job.get('rect_cutouts', []),
          'main_hole_center_to_lid_edges_mm': [
              [h['x']-lid.BoundBox.XMin, min(h['y']-lid.BoundBox.YMin, lid.BoundBox.YMax-h['y'])]
              for h in job['lid_ports']],
          'cut_circles_match_unfold_STEP': True, 'production_release': False}
(work / 'cad_verification.json').write_text(json.dumps(result, indent=2))
print(json.dumps(result))
