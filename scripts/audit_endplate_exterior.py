#!/usr/bin/env python3
"""Check exterior-side hole coordinates for U + two external end plates.

This is a release gate, not a geometric repair. The CAD builder must also
verify its 3D flattening rotation has determinant +1 and puts exterior up.
"""
import argparse
import json
from pathlib import Path

import ezdxf


EXPECTED_MAPS = {
    'END_R': "X'=Y,Y'=Z,Z'=X-L",
    'END_L': "X'=W-Y,Y'=Z,Z'=-X",
}


def circles(path):
    result = []
    for entity in ezdxf.readfile(path).modelspace():
        if entity.dxftype() == 'CIRCLE':
            result.append((float(entity.dxf.center.x), float(entity.dxf.center.y),
                           2 * float(entity.dxf.radius)))
    return result


def audit(cad_dir, tolerance):
    report = json.loads((cad_dir / 'report.json').read_text())
    width = float(report['formed_outer_body_mm'][1])
    declared = report.get('flat_exterior_maps', {})
    findings = []
    for part in ('END_L', 'END_R'):
        actual = circles(cad_dir / (part + '.dxf'))
        features = [f for f in report['features']
                    if f.get('part') == part and 'diameter_mm' in f]
        mapping_ok = declared.get(part) == EXPECTED_MAPS[part]
        matches = []
        for feature in features:
            _, y, z = feature['center_mm']
            expected = ((width - y) if part == 'END_L' else y,
                        z, feature['diameter_mm'])
            found = any(max(abs(a - b) for a, b in zip(expected, item)) <= tolerance
                        for item in actual)
            matches.append({'kind': feature['kind'], 'expected_xy_d_mm': expected,
                            'matched': found})
        bbox = report['parts'][part]['flat_size_mm']
        bbox_ok = abs(bbox[0] - width) <= tolerance
        # Neither a matching hole pattern nor matching PDF is proof that the
        # exterior face was flattened; require the builder's explicit map.
        status = 'PASS' if mapping_ok and bbox_ok and matches and all(m['matched'] for m in matches) else 'FAIL'
        findings.append({'part': part, 'status': status, 'declared_map': declared.get(part),
                         'expected_map': EXPECTED_MAPS[part], 'bbox_mm': bbox,
                         'bbox_ok': bbox_ok, 'features': matches})
    return {'status': 'PASS' if all(f['status'] == 'PASS' for f in findings) else 'FAIL',
            'cad_dir': str(cad_dir), 'tolerance_mm': tolerance, 'parts': findings}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('cad_dir', type=Path)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--tolerance-mm', type=float, default=0.05)
    args = parser.parse_args()
    result = audit(args.cad_dir, args.tolerance_mm)
    payload = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload)
    print(payload)
    if result['status'] != 'PASS':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
