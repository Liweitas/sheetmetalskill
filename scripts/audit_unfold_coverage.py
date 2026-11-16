#!/usr/bin/env python3
"""Independent STEP readback of a candidate native unfold against its source main solid.

Run with FreeCAD's Python. This gate detects partial but valid native unfold results;
it does not certify exterior-face handedness, bend allowance, or manufacturing release.
"""
import argparse
import json
from pathlib import Path
import FreeCAD  # Initialize FreeCAD's C++ runtime before importing Part.
import Part


def inspect(source, unfold, min_ratio, max_ratio):
    original = Part.Shape(); original.read(str(source))
    flat = Part.Shape(); flat.read(str(unfold))
    if not original.isValid() or not original.Solids:
        raise ValueError('source STEP is invalid or contains no solid')
    main = max(original.Solids, key=lambda shape: shape.Volume)
    ratio = flat.Volume / main.Volume if main.Volume else 0
    checks = {
        'source_valid': original.isValid(),
        'source_solids': len(original.Solids),
        'unfold_valid': flat.isValid(),
        'unfold_one_solid': len(flat.Solids) == 1,
        'volume_coverage': min_ratio <= ratio <= max_ratio,
    }
    return {
        'source': str(source), 'unfold': str(unfold),
        'main_source_volume_mm3': main.Volume,
        'unfold_volume_mm3': flat.Volume,
        'volume_ratio': ratio,
        'accepted_ratio': [min_ratio, max_ratio],
        'checks': checks,
        'pass': all(checks.values()),
        'limit': 'Catches partial unfold. Exterior face, bend IDs, holes, and DXF still need separate checks.',
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('source_step', type=Path)
    parser.add_argument('unfold_step', type=Path)
    parser.add_argument('--min-ratio', type=float, default=.95)
    parser.add_argument('--max-ratio', type=float, default=1.05)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if not 0 < args.min_ratio <= 1 <= args.max_ratio:
        parser.error('ratio limits must enclose 1')
    result = inspect(args.source_step, args.unfold_step, args.min_ratio, args.max_ratio)
    output = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output + '\n')
    print(output)
    raise SystemExit(0 if result['pass'] else 2)


if __name__ == '__main__':
    main()
