#!/usr/bin/env python3
"""Recommend structure only; never mutate a project or certify bending feasibility."""
import argparse
import json
from decimal import Decimal, InvalidOperation

SCALE = {'mm': Decimal(1), 'cm': Decimal(10), 'm': Decimal(1000), 'inch': Decimal('25.4')}
METHODS = {'u_external_ends': (3, 4), 'u_wrap_bottom_l': (2, 3)}

def select_structure(length, width, height, unit='mm', *, record_kind='new', explicit_method=None, lid_required=True):
    if unit not in SCALE:
        raise ValueError('Unsupported unit; normalize mm/cm/m/inch explicitly')
    if record_kind not in ('new', 'existing'):
        raise ValueError('record_kind must be new or existing')
    values = []
    for v in (length, width, height):
        if isinstance(v, bool):
            raise ValueError('Dimensions must be positive finite numbers')
        try:
            n = Decimal(str(v)) * SCALE[unit]
        except (InvalidOperation, ValueError):
            raise ValueError('Dimensions must be positive finite numbers') from None
        if not n.is_finite() or n <= 0:
            raise ValueError('Dimensions must be positive finite numbers')
        values.append(n)
    if not isinstance(lid_required, bool):
        raise ValueError('lid_required must be boolean; the selector does not add a lid')
    L, W, H = values
    comparable = max(L, W)
    recommendation = 'u_external_ends' if comparable >= H else 'u_wrap_bottom_l'
    if explicit_method is not None:
        if explicit_method not in (*METHODS, 'keep_source', 'other'):
            raise ValueError('Unknown explicit method')
        method, source = explicit_method, 'explicit_project_choice'
    elif record_kind == 'existing':
        method, source = None, 'existing_project_preserved'
    else:
        method, source = recommendation, 'workflow_structure_2.4.0'
    counts = METHODS.get(method)
    return {
        'dimensions_mm': [float(x) for x in values],
        'comparison': '>=' if comparable >= H else '<',
        'default_recommendation': recommendation,
        'selected_method': method, 'source': source,
        'body_sheet_parts': counts[0] if counts else None,
        'sheet_parts_with_requested_lid': counts[1 if lid_required else 0] if counts else None,
        'lid_required': lid_required,
        'manufacturability': 'not_evaluated', 'production_released': False,
        'note': 'Equality belongs to U floor + two external ends. Existing projects and explicit choices are preserved. Counts exclude handles/hardware. U direction, seams, radii, holes and tooling require project design.'
    }

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--length', required=True); p.add_argument('--width', required=True); p.add_argument('--height', required=True)
    p.add_argument('--unit', choices=SCALE, default='mm')
    p.add_argument('--record-kind', choices=['new', 'existing'], default='new')
    p.add_argument('--explicit-method', choices=[*METHODS, 'keep_source', 'other'])
    p.add_argument('--lid', choices=['yes', 'no'], required=True)
    a = p.parse_args()
    try:
        result = select_structure(a.length, a.width, a.height, a.unit, record_kind=a.record_kind, explicit_method=a.explicit_method, lid_required=a.lid == 'yes')
    except ValueError as e:
        p.error(str(e))
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
