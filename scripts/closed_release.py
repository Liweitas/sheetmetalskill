#!/usr/bin/env python3
"""Closed drawing entry. One call writes geometry, DXF and PDF together.

Missing hole slots or a failed caller-supplied gate refuse the run. Those
outputs are never labeled 确认稿. This does not replace the CAD pipeline:
callers pass already-generated artifact bytes, and this entry binds them into
one run directory with hashes. Stdlib only.
"""
import hashlib, json, sys
from pathlib import Path

REQUIRED_SLOTS = ('roof_ports', 'handles', 'fixings')
ARTIFACTS = {'geometry': 'geometry.step', 'dxf': 'cut.dxf', 'pdf': 'bend.pdf'}


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def missing_slots(brief):
    missing = []
    for name in REQUIRED_SLOTS:
        slot = brief.get(name)
        if not isinstance(slot, dict) or not slot.get('mode'):
            missing.append(name)
    return missing


def emit(brief, geometry, dxf, pdf, gate_pass, outdir):
    """Write all three artifacts or none. Returns a receipt."""
    out = Path(outdir)
    missing = missing_slots(brief)
    blobs = {'geometry': geometry, 'dxf': dxf, 'pdf': pdf}
    reasons = []
    if missing:
        reasons.append('missing_slots:' + ','.join(missing))
    if not gate_pass:
        reasons.append('gate_failed')
    if any(not blob for blob in blobs.values()):
        reasons.append('empty_artifact')
    confirmed = not reasons
    receipt = {
        'entry': 'closed_release',
        'artifacts': list(ARTIFACTS),
        'same_run': False,
        'hashes': {},
        'gate_pass': bool(gate_pass),
        'missing_slots': missing,
        'confirmation': confirmed,
        'label': '确认稿' if confirmed else '拒绝',
        'reasons': reasons,
    }
    if not confirmed:
        return receipt
    out.mkdir(parents=True, exist_ok=True)
    for name, filename in ARTIFACTS.items():
        target = out / filename
        target.write_bytes(blobs[name])
        receipt['hashes'][name] = sha256(target.read_bytes())
    receipt['same_run'] = True
    (out / 'receipt.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n')
    return receipt


def main(argv):
    spec = json.loads(Path(argv[1]).read_text())
    base = Path(argv[1]).resolve().parent
    def load(name):
        value = spec[name]
        path = Path(value)
        if not path.is_absolute():
            path = base / path
        return path.read_bytes() if path.is_file() else str(value).encode()
    outdir = spec.get('outdir') or str(base / 'closed-out')
    out = emit(spec['brief'], load('geometry'), load('dxf'), load('pdf'), spec.get('gate_pass', False), outdir)
    text = json.dumps(out, ensure_ascii=False, indent=2)
    print(text)
    return 0 if out['confirmation'] else 2


if __name__ == '__main__':
    sys.exit(main(sys.argv))
