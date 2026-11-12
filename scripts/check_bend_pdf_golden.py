#!/usr/bin/env python3
"""Bend PDF golden hash gate (skill 2.8.45 / rule 26+32).

Checks order addendum-tools copies of:
  make_bend_pdf.py, pdf_common.py, bidir.py, views.py, engine_u_endplates.py
against assets/bend-pdf-golden-001-visual/ (symlink resolved).

Visual reference: S-201-1-20261031-001-v1 (Harry t59u/t60u).
Legacy assets/bend-pdf-golden-004-v2/ is historical only.

Also flags gray-box tools/pdf.py as outbound-forbidden when present without
a matching golden make_bend_pdf entrypoint.

Usage:
  check_bend_pdf_golden.py ORDER_DIR [--overlap logs/bend_pdf_overlap.json]
  exit 0 PASS | 2 BLOCK | 1 WARN (overlap remaining>0 when --strict-overlap)
"""
from __future__ import annotations
import argparse, hashlib, json, sys
from pathlib import Path

SK = Path(__file__).resolve().parents[1]
GOLDEN = SK / 'assets' / 'bend-pdf-golden-001-visual'
FILES = ('make_bend_pdf.py', 'pdf_common.py', 'bidir.py', 'views.py', 'engine_u_endplates.py')


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('order')
    ap.add_argument('--overlap', default=None, help='path to bend_pdf_overlap.json')
    ap.add_argument('--strict-overlap', action='store_true',
                    help='BLOCK when overlap remaining>0 (default: WARN)')
    ap.add_argument('--json-out', default=None)
    args = ap.parse_args()
    order = Path(args.order).resolve()
    add = order / 'addendum-tools'
    tools_pdf = order / 'tools' / 'pdf.py'
    report = {
        'order': str(order),
        'golden': str(GOLDEN),
        'visual_ref': 'S-201-1-20261031-001-v1',
        'skill': '2.8.45',
        'files': {},
        'gate': 'PASS',
        'blocks': [],
        'warns': [],
        'overlap': None,
    }
    if not GOLDEN.is_dir():
        report['gate'] = 'BLOCK'
        report['blocks'].append(f'golden missing: {GOLDEN}')
    else:
        for name in FILES:
            g = GOLDEN / name
            a = add / name
            entry = {'golden_sha256': sha256(g) if g.exists() else None}
            if not a.exists():
                report['blocks'].append(f'missing addendum-tools/{name} (must symlink or cp from golden)')
                entry['status'] = 'MISSING'
            else:
                real = a.resolve()
                entry['path'] = str(a)
                entry['resolved'] = str(real)
                entry['symlink'] = a.is_symlink()
                entry['order_sha256'] = sha256(real)
                if entry['order_sha256'] == entry['golden_sha256']:
                    entry['status'] = 'MATCH'
                else:
                    entry['status'] = 'MISMATCH'
                    report['blocks'].append(
                        f'HASH MISMATCH addendum-tools/{name}: order={entry["order_sha256"][:12]}… '
                        f'golden={entry["golden_sha256"][:12]}… — BLOCK (cp/symlink from golden only; do not fork)')
            report['files'][name] = entry

    if tools_pdf.exists():
        mb = add / 'make_bend_pdf.py'
        if mb.exists():
            txt = mb.read_text(encoding='utf-8', errors='replace')
            if 'tools/pdf.py' in txt and 'engine_u_endplates' not in txt and 'GOLDEN' not in txt.upper():
                if report['files'].get('make_bend_pdf.py', {}).get('status') != 'MATCH':
                    report['blocks'].append(
                        'gray-box tools/pdf.py used via divergent addendum make_bend_pdf — '
                        'use golden make_bend_pdf (dispatches engine_u_endplates) instead')
        report['warns'].append('tools/pdf.py present — must NOT be outbound confirmation appearance; use addendum make_bend_pdf')

    ov_path = Path(args.overlap) if args.overlap else (order / 'logs' / 'bend_pdf_overlap.json')
    if ov_path.exists():
        ov = json.loads(ov_path.read_text())
        report['overlap'] = ov
        rem = int(ov.get('remaining') or 0)
        if rem > 0:
            msg = f'dim overlap remaining={rem} (attempted={ov.get("attempted")}, nudged={ov.get("resolved_by_nudge")}, flipped={ov.get("resolved_by_flip")})'
            if args.strict_overlap:
                report['blocks'].append('PDF layout FAIL: ' + msg)
            else:
                report['warns'].append('PDF layout WARN: ' + msg)
        else:
            report['warns'].append(f'PDF layout PASS: overlap remaining=0 (attempted={ov.get("attempted")})')
    else:
        report['warns'].append(f'no overlap report at {ov_path} (run make_bend_pdf first)')

    if report['blocks']:
        report['gate'] = 'BLOCK'
    elif any('WARN' in w or 'warn' in w.lower() for w in report['warns'] if 'PASS' not in w):
        report['gate'] = 'PASS'

    if args.json_out:
        Path(args.json_out).write_text(json.dumps(report, indent=2, ensure_ascii=False))
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if report['gate'] == 'BLOCK':
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main())
