#!/usr/bin/env python3
"""v2.8.2 release DXF writer + gate (ezdxf; run with /workspace/addendum-venv/bin/python or any python with ezdxf).

Why (audit 2026-10-26, items #1/#2): the skill-native nest had no SHEET border, and order-side post.py once copied
BEND lines into the NEST (seen by the user as "dashed lines"; t32u had to strip them from 11 releases).
This module is the ONE place that writes release CUT / BEND / NEST DXFs and the ONE gate every release DXF must pass,
whatever tool produced it.

Rules enforced (role = cut | nest | bend):
  * $INSUNITS=4 (mm), 1:1 (optional expected flat size check), ezdxf audit 0 errors, no zero-length entities
  * cut/nest: only layers CUT (+SHEET for nest); only LINE/ARC/CIRCLE/closed LWPOLYLINE; every effective linetype
    CONTINUOUS (BYLAYER/BYBLOCK resolved); NO layer whose name contains BEND, no BEND entities, no TEXT/DIM/INSERT
  * closed contours: every LINE/ARC endpoint meets exactly one other endpoint (tol 1e-6 mm)
  * no duplicate entities, no collinear overlapping lines, no overlapping concentric arcs
  * nest: exactly one closed SHEET rectangle (0,0)-(sheet), every CUT entity inside sheet-margin, part bboxes >= gap apart
  * nest publish default (user t62u 2026-10-28): kit/1BOX — one complete box kit (qty=1 of each part) in a single
    `{ver}_NEST_{W}x{H}_1BOX.dxf`; order qty stays in README/BOM; do not replicate kits or emit SHEETnn for qty.
    Legacy nest_mode='sheets' (SHEETnn) retained for internal/evidence only.
  * bend: OUTLINE (or CUT) contour closed + continuous, >=1 BEND line when the part has bends
  * ALL roles (user t16u 2026-10-26 "所有DXF中不能有虚线，影响切割"): every entity's effective linetype AND every layer in the
    layer table must be CONTINUOUS (DASHED/HIDDEN/CENTER/DOT/... = FAIL). Bend lines in the BEND DXF are continuous solid lines
    on their own red BEND layer with TEXT labels; write_bend/post_release refuse any other linetype.
CLI:
  release_dxf.py check --role cut|nest|bend FILE... [--sheet 2440x1220 --margin 10 --gap 10]   -> JSON, exit 1 on FAIL
  release_dxf.py nodash FILE_OR_DIR...      -> any DXF, exit 1 if any non-continuous (dashed) linetype (user t16u)
  release_dxf.py post --work WORK --report report.json --out RELEASE_DIR --ver VER --parts U,END_L,... [--order ...]
"""
import sys, json, math, argparse, itertools
from pathlib import Path
import ezdxf

TOL = 1e-6
CUT_TYPES = {'LINE', 'ARC', 'CIRCLE', 'LWPOLYLINE'}
CONTINUOUS_OK = {'CONTINUOUS', 'BYLAYER', 'BYBLOCK', ''}


def _is_continuous(lt):
    return (lt or '').upper() in CONTINUOUS_OK


def noncontinuous(doc):
    """user t16u: no dashed lines in ANY release DXF. Returns (entity offenders, layer-table offenders)."""
    ents = [(e.dxftype(), e.dxf.get('layer', '0'), eff_linetype(doc, e)) for e in doc.modelspace() if not _is_continuous(eff_linetype(doc, e))]
    lays = [(l.dxf.name, l.dxf.linetype) for l in doc.layers if not _is_continuous(l.dxf.get('linetype', 'CONTINUOUS'))]
    return ents, lays


def eff_linetype(doc, e):
    lt = e.dxf.get('linetype', 'BYLAYER')
    if lt.upper() == 'BYLAYER':
        lay = e.dxf.get('layer', '0')
        lt = doc.layers.get(lay).dxf.linetype if lay in doc.layers else 'CONTINUOUS'
    if lt.upper() == 'BYBLOCK':
        lt = 'CONTINUOUS'
    return lt


def _segments(e):
    """yield primitive LINE/ARC/CIRCLE-like dicts (LWPOLYLINE exploded)."""
    t = e.dxftype()
    if t == 'LWPOLYLINE':
        for v in e.virtual_entities():
            yield from _segments(v)
        return
    if t == 'LINE':
        yield {'t': 'L', 'a': tuple(e.dxf.start)[:2], 'b': tuple(e.dxf.end)[:2]}
    elif t == 'ARC':
        yield {'t': 'A', 'c': tuple(e.dxf.center)[:2], 'r': e.dxf.radius, 's': e.dxf.start_angle % 360, 'e': e.dxf.end_angle % 360,
               'a': tuple(e.start_point)[:2], 'b': tuple(e.end_point)[:2]}
    elif t == 'CIRCLE':
        yield {'t': 'C', 'c': tuple(e.dxf.center)[:2], 'r': e.dxf.radius}


def _seg_bbox(s):
    if s['t'] == 'L':
        xs, ys = (s['a'][0], s['b'][0]), (s['a'][1], s['b'][1])
        return min(xs), min(ys), max(xs), max(ys)
    (cx, cy), r = s['c'], s['r']
    if s['t'] == 'C':
        return cx - r, cy - r, cx + r, cy + r
    pts = [s['a'], s['b']]
    span = (s['e'] - s['s']) % 360
    for q in (0, 90, 180, 270):
        if (q - s['s']) % 360 <= span + 1e-9:
            pts.append((cx + r * math.cos(math.radians(q)), cy + r * math.sin(math.radians(q))))
    return min(p[0] for p in pts), min(p[1] for p in pts), max(p[0] for p in pts), max(p[1] for p in pts)


def _components(segs):
    """group segments into connected contours (by shared endpoints); circles are own contours."""
    n = len(segs); parent = list(range(n))
    def f(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]; i = parent[i]
        return i
    ends = [(i, p) for i, s in enumerate(segs) if s['t'] != 'C' for p in (s['a'], s['b'])]
    grid = {}
    for i, p in ends:
        grid.setdefault((round(p[0], 4), round(p[1], 4)), []).append(i)
    for v in grid.values():
        for j in v[1:]:
            parent[f(j)] = f(v[0])
    comp = {}
    for i in range(n):
        comp.setdefault(f(i), []).append(i)
    return list(comp.values())


def check_dxf(path, role, sheet=(2440.0, 1220.0), margin=10.0, gap=10.0, expect_size=None, expect_bends=None):
    path = Path(path); doc = ezdxf.readfile(path)
    noncont, noncont_layers = noncontinuous(doc)   # user t16u: all roles, entities + layer table; BEFORE audit (audit resets undefined linetypes)
    aud = doc.audit(); msp = doc.modelspace()
    ents = list(msp); fails = []
    units = doc.header.get('$INSUNITS')
    if units != 4: fails.append(f'INSUNITS={units} (need 4 = mm)')
    if aud.has_errors: fails.append(f'audit errors {len(aud.errors)}')
    layers_used = sorted({e.dxf.get('layer', '0') for e in ents})
    layer_table = sorted(l.dxf.name for l in doc.layers)
    allowed = {'cut': {'CUT'}, 'nest': {'CUT', 'SHEET'}, 'bend': {'OUTLINE', 'CUT', 'BEND', 'TEXT'}}[role]
    if not set(layers_used) <= allowed: fails.append(f'layers {layers_used} not subset of {sorted(allowed)}')
    contour_layers = {'cut': {'CUT'}, 'nest': {'CUT'}, 'bend': {'OUTLINE', 'CUT'}}[role]
    if role in ('cut', 'nest'):
        if any('BEND' in n.upper() for n in layer_table): fails.append('BEND layer present in layer table')
        bad_types = sorted({e.dxftype() for e in ents} - CUT_TYPES)
        if bad_types: fails.append(f'forbidden entity types {bad_types}')
    else:
        nb = sum(1 for e in ents if e.dxf.layer == 'BEND')
        if expect_bends is not None and nb != expect_bends: fails.append(f'BEND lines {nb} != expected {expect_bends}')
    if noncont: fails.append(f'{len(noncont)} non-continuous (dashed) entities e.g. {noncont[:3]} - no dashed lines allowed in any DXF (user t16u)')
    if noncont_layers: fails.append(f'non-continuous layer linetypes {noncont_layers} - no dashed lines allowed in any DXF (user t16u)')
    cents = [e for e in ents if e.dxf.layer in contour_layers]
    for e in cents:
        if e.dxftype() == 'LWPOLYLINE' and not e.closed: pass  # exploded below; open polylines are checked by endpoint pairing
    segs = [s for e in cents for s in _segments(e)]
    # zero length
    zl = sum(1 for s in segs if (s['t'] == 'L' and math.dist(s['a'], s['b']) < TOL) or (s['t'] != 'L' and s['r'] < TOL))
    if zl: fails.append(f'{zl} zero-length/zero-radius entities')
    # closed contours
    pts = [p for s in segs if s['t'] != 'C' for p in (s['a'], s['b'])]
    grid = {}
    for p in pts: grid.setdefault((round(p[0], 4), round(p[1], 4)), []).append(p)
    open_pts = 0
    for i, p in enumerate(pts):
        k = (round(p[0], 4), round(p[1], 4)); m = sum(1 for q in grid[k] if math.dist(p, q) < TOL) - 1
        if m != 1: open_pts += 1
    if open_pts: fails.append(f'{open_pts} open/branching endpoints')
    # duplicates
    def key(s):
        if s['t'] == 'L': return ('L',) + tuple(sorted([tuple(round(v, 5) for v in s['a']), tuple(round(v, 5) for v in s['b'])]))
        if s['t'] == 'C': return ('C', round(s['c'][0], 5), round(s['c'][1], 5), round(s['r'], 5))
        return ('A', round(s['c'][0], 5), round(s['c'][1], 5), round(s['r'], 5), round(s['s'], 4), round(s['e'], 4))
    keys = [key(s) for s in segs]; dup = len(keys) - len(set(keys))
    if dup: fails.append(f'{dup} duplicate entities')
    # collinear overlaps (lines) + overlapping concentric arcs/circles
    lines = [s for s in segs if s['t'] == 'L']; overl = 0
    buckets = {}
    for s in lines:
        ux, uy = s['b'][0] - s['a'][0], s['b'][1] - s['a'][1]; Ln = math.hypot(ux, uy)
        ang = round(math.degrees(math.atan2(uy, ux)) % 180, 3) % 180
        buckets.setdefault(ang, []).append(s)
    for grp in buckets.values():
        for s1, s2 in itertools.combinations(grp, 2):
            a, b = s1['a'], s1['b']; ux, uy = b[0] - a[0], b[1] - a[1]; Ln = math.hypot(ux, uy); ux /= Ln; uy /= Ln
            if all(abs((p[0] - a[0]) * uy - (p[1] - a[1]) * ux) < TOL for p in (s2['a'], s2['b'])):
                tc = [(p[0] - a[0]) * ux + (p[1] - a[1]) * uy for p in (s2['a'], s2['b'])]
                if min(max(tc), Ln) - max(min(tc), 0) > TOL: overl += 1
    arcs = [s for s in segs if s['t'] in ('A', 'C')]
    for s1, s2 in itertools.combinations(arcs, 2):
        if math.dist(s1['c'], s2['c']) < TOL and abs(s1['r'] - s2['r']) < TOL:
            if 'C' in (s1['t'], s2['t']): overl += 1; continue
            def arcset(s):
                span = (s['e'] - s['s']) % 360 or 360
                return {round((s['s'] + k * 0.5) % 360, 1) for k in range(1, int(span / 0.5))}
            if arcset(s1) & arcset(s2): overl += 1
    if overl: fails.append(f'{overl} overlapping collinear lines/concentric arcs')
    res = {'file': path.name, 'role': role, 'dxfversion': doc.dxfversion, 'units': units, 'audit_errors': len(aud.errors), 'entities': len(ents),
           'types': {t: sum(1 for e in ents if e.dxftype() == t) for t in sorted({e.dxftype() for e in ents})},
           'layers_used': layers_used, 'layer_table': layer_table,
           'layer_linetypes': {l.dxf.name: l.dxf.linetype for l in doc.layers},
           'non_continuous_entities': len(noncont), 'non_continuous_layers': noncont_layers, 'bend_entities': sum(1 for e in ents if 'BEND' in e.dxf.get('layer', '').upper()),
           'open_endpoints': open_pts, 'duplicates': dup, 'overlaps': overl, 'zero_length': zl,
           'circles': sum(1 for s in segs if s['t'] == 'C')}
    cb = [_seg_bbox(s) for s in segs]
    if cb:
        bb = [min(b[0] for b in cb), min(b[1] for b in cb), max(b[2] for b in cb), max(b[3] for b in cb)]
        res['contour_bbox'] = [round(v, 6) for v in bb]; res['contour_size'] = [round(bb[2] - bb[0], 6), round(bb[3] - bb[1], 6)]
        if expect_size and role != 'nest' and any(abs(a - b) > 1e-3 for a, b in zip(res['contour_size'], expect_size)):
            fails.append(f'size {res["contour_size"]} != expected flat {expect_size} (not 1:1?)')
    if role == 'nest':
        sh = [e for e in ents if e.dxf.layer == 'SHEET']
        ok = len(sh) == 1 and sh[0].dxftype() == 'LWPOLYLINE' and sh[0].closed
        if ok:
            p = sorted((round(x, 6), round(y, 6)) for x, y in sh[0].get_points('xy'))
            ok = p == sorted([(0, 0), (sheet[0], 0), (sheet[0], sheet[1]), (0, sheet[1])])
        if not ok: fails.append(f'SHEET border missing / not a closed {sheet[0]:g}x{sheet[1]:g} rectangle at origin')
        if cb and (bb[0] < margin - TOL or bb[1] < margin - TOL or bb[2] > sheet[0] - margin + TOL or bb[3] > sheet[1] - margin + TOL):
            fails.append(f'CUT bbox {res["contour_bbox"]} outside sheet minus margin {margin}')
        comps = _components(segs); pb = []
        for c in comps:
            bbs = [cb[i] for i in c]; pb.append([min(b[0] for b in bbs), min(b[1] for b in bbs), max(b[2] for b in bbs), max(b[3] for b in bbs)])
        # outer contours = bboxes not contained in another
        outer = [b for b in pb if not any(o is not b and o[0] <= b[0] + TOL and o[1] <= b[1] + TOL and o[2] >= b[2] - TOL and o[3] >= b[3] - TOL and o != b for o in pb)]
        mind = None
        for a, b in itertools.combinations(outer, 2):
            dx = max(b[0] - a[2], a[0] - b[2]); dy = max(b[1] - a[3], a[1] - b[3]); d = max(dx, dy)
            mind = d if mind is None else min(mind, d)
        res['parts_in_nest'] = len(outer); res['min_part_bbox_gap'] = mind
        if mind is not None and mind < gap - 1e-6: fails.append(f'part gap {mind:.3f} < {gap}')
    res['fails'] = fails; res['pass'] = not fails
    return res


# ---------------------------------------------------------------- writers
def new_doc(ver, production_release=False):
    d = ezdxf.new('R2010', setup=True); d.units = 4; d.header['$INSUNITS'] = 4; d.header['$MEASUREMENT'] = 1
    d.header.custom_vars.append('RELEASE', ver); d.header.custom_vars.append('PRODUCTION_RELEASE', str(bool(production_release)).lower())
    return d


def raw_entities(path):
    """LINE/ARC/CIRCLE from a skill cad_dxf.write_dxf raw CUT DXF (any layer)."""
    return [e for e in ezdxf.readfile(path).modelspace() if e.dxftype() in ('LINE', 'ARC', 'CIRCLE')]


def _copy(msp, e, layer, dx=0.0, dy=0.0):
    c = e.copy(); c.dxf.layer = layer; c.dxf.linetype = 'BYLAYER'
    if dx or dy: c.translate(dx, dy, 0)
    msp.add_entity(c)


def write_cut(raw, out, ver):
    d = new_doc(ver); d.layers.add('CUT', color=7, linetype='CONTINUOUS'); msp = d.modelspace()
    for e in raw_entities(raw): _copy(msp, e, 'CUT')
    d.saveas(out); return out


def _require_continuous(lt):
    if (lt or '').upper() != 'CONTINUOUS':
        raise ValueError(f'bend_linetype={lt!r}: all DXF lines must be CONTINUOUS (user t16u: 所有DXF中不能有虚线，影响切割)')


def write_bend(raw, out, ver, bend_records, labels=(), bend_linetype='CONTINUOUS'):
    """separate per-part BEND DXF: OUTLINE (continuous) + BEND layer (red, CONTINUOUS solid bend lines) + TEXT labels.
    Never used for laser cutting. user t16u: no dashed lines in any DXF -> any other linetype raises ValueError."""
    _require_continuous(bend_linetype); bend_linetype = 'CONTINUOUS'
    d = new_doc(ver); d.layers.add('OUTLINE', color=7, linetype='CONTINUOUS'); d.layers.add('BEND', color=1, linetype=bend_linetype)
    d.layers.add('TEXT', color=3, linetype='CONTINUOUS'); msp = d.modelspace()
    for e in raw_entities(raw): _copy(msp, e, 'OUTLINE')
    for b in bend_records:
        a, bb = b['flat_line_mm']; msp.add_line(a, bb, dxfattribs={'layer': 'BEND'})
        if b.get('label'):
            msp.add_text(b['label'], height=3.5, dxfattribs={'layer': 'TEXT'}).set_placement(((a[0] + bb[0]) / 2 + 2, (a[1] + bb[1]) / 2 + 2))
    for i, s in enumerate(labels):
        msp.add_text(s, height=4, dxfattribs={'layer': 'TEXT'}).set_placement((0, -10 - 8 * i))
    d.saveas(out); return out


def shelf_layout(parts, sheet=(2440.0, 1220.0), margin=10.0, gap=10.0):
    """parts: list of (name, raw_path, (w,h), qty) in placement order. Left->right rows, new row / new sheet when full.
    No rotation (the user prefers grain/orientation as drawn); oversize -> ValueError."""
    pl = []; sh = 1; x = y = margin; rowh = 0.0
    for name, raw, (w, h), qty in parts:
        if w > sheet[0] - 2 * margin + 1e-7 or h > sheet[1] - 2 * margin + 1e-7: raise ValueError(f'NEST_OVERSIZE {name} {w}x{h}')
        for k in range(1, qty + 1):
            if x + w > sheet[0] - margin + 1e-7: x = margin; y += rowh + gap; rowh = 0.0
            if y + h > sheet[1] - margin + 1e-7: sh += 1; x = y = margin; rowh = 0.0
            pl.append({'part': name, 'instance': k, 'sheet': sh, 'origin': [x, y], 'size': [w, h], 'raw': str(raw)}); x += w + gap; rowh = max(rowh, h)
    return pl


def write_nests(parts, out_pattern, ver, sheet=(2440.0, 1220.0), margin=10.0, gap=10.0, nest_mode='kit'):
    """cut-only nests: SHEET border + translated CUT contours. NO bend lines, NO text, all CONTINUOUS.
    nest_mode='kit' (default, user t62u 2026-10-28): one kit / one box on one DXF named *_1BOX.dxf;
    parts list should already be qty=1 per kit member. If the kit needs >1 physical sheet -> ValueError.
    nest_mode='sheets': legacy multi-sheet SHEETnn (internal/evidence only; not the release default).
    out_pattern e.g. kit '.../{ver}_NEST_2440x1220_1BOX.dxf' or sheets '.../{ver}_NEST_2440x1220_SHEET{n:02d}.dxf'.
    Raw part DXFs must have bbox origin at (0,0)."""
    pl = shelf_layout(parts, sheet, margin, gap)
    nsheets = len({p['sheet'] for p in pl})
    if nest_mode == 'kit' and nsheets > 1:
        raise ValueError(f'NEST_KIT_NEEDS_{nsheets}_SHEETS: one-box kit must fit on a single {sheet[0]:g}x{sheet[1]:g} sheet (user t62u 1BOX)')
    files = []
    for s in sorted({p['sheet'] for p in pl}):
        d = new_doc(ver); d.layers.add('CUT', color=7, linetype='CONTINUOUS'); d.layers.add('SHEET', color=8, linetype='CONTINUOUS'); msp = d.modelspace()
        msp.add_lwpolyline([(0, 0), (sheet[0], 0), (sheet[0], sheet[1]), (0, sheet[1])], close=True, dxfattribs={'layer': 'SHEET'})
        for p in pl:
            if p['sheet'] != s: continue
            ents = raw_entities(p['raw'])
            for e in ents: _copy(msp, e, 'CUT', *p['origin'])
        f = Path(str(out_pattern).format(ver=ver, n=s)); d.saveas(f); files.append(f)
    return pl, files


def post_release(work, report, out, ver, parts, order=None, qty=None, sheet=(2440.0, 1220.0), margin=10.0, gap=10.0,
                 material_cn='', bend_text=None, extra_labels=None, bend_linetype='CONTINUOUS', nest_mode='kit'):
    """generic replacement for the order-side dxf_post.py/post.py. report: skill-style report.json with
    parts[n].flat_size and parts[n].bend_records[i].{id,flat_line_mm}. Writes DXF_CUT/DXF_BEND/NEST and returns checks.
    nest_mode='kit' (default, user t62u 2026-10-28): NEST = one DXF with exactly 1 kit (qty forced to 1 per part);
    order qty belongs in README/BOM only — never duplicate kits into NEST / never split SHEETnn for qty.
    nest_mode='sheets': legacy qty-aware multi SHEETnn (optional internal/evidence)."""
    _require_continuous(bend_linetype)   # user t16u: no dashed lines in any DXF
    work, out = Path(work), Path(out); rep = json.load(open(report)); P = rep['parts']
    for d in ('DXF_CUT', 'DXF_BEND', 'NEST'): (out / d).mkdir(parents=True, exist_ok=True)
    checks = []
    for n in parts:
        raw = work / f'{n}_CUT_raw.dxf'; fs = P[n]['flat_size']
        c = write_cut(raw, out / 'DXF_CUT' / f'{ver}_CUT_{n}.dxf', ver)
        checks.append(check_dxf(c, 'cut', expect_size=fs))
        recs = [{**b, 'label': (bend_text or (lambda n_, b_: ' '.join(str(v) for v in (b_['id'], b_.get('direction_cn') or b_.get('direction') or '', f"{b_.get('angle_deg', 90):g}°") if v)))(n, b)} for b in P[n]['bend_records']]
        labels = (extra_labels or {}).get(n, [])
        b = write_bend(raw, out / 'DXF_BEND' / f'{ver}_BEND_{n}.dxf', ver, recs, labels, bend_linetype)
        checks.append(check_dxf(b, 'bend', expect_size=fs, expect_bends=len(recs)))
    order = order or list(parts); qty = qty or {}
    if nest_mode == 'kit':
        # user t62u: one box / one NEST DXF; ignore order qty here (qty lives in README/BOM)
        plist = [(n, work / f'{n}_CUT_raw.dxf', tuple(P[n]['flat_size']), 1) for n in order]
        pat = out / 'NEST' / ('{ver}_NEST_%dx%d_1BOX.dxf' % (sheet[0], sheet[1]))
    else:
        plist = [(n, work / f'{n}_CUT_raw.dxf', tuple(P[n]['flat_size']), qty.get(n, 1)) for n in order]
        pat = out / 'NEST' / ('{ver}_NEST_%dx%d_SHEET{n:02d}.dxf' % (sheet[0], sheet[1]))
    pl, files = write_nests(plist, pat, ver, sheet, margin, gap, nest_mode=nest_mode)
    for f in files: checks.append(check_dxf(f, 'nest', sheet, margin, gap))
    area = sum(P[p['part']]['flat_area'] for p in pl if 'flat_area' in P[p['part']])
    nest = {'sheet': list(sheet), 'margin': margin, 'gap': gap, 'placements': pl, 'sheets': len(files), 'parts_area_mm2': area,
            'nest_mode': nest_mode, 'kit_boxes_in_nest': 1 if nest_mode == 'kit' else None,
            'order_qty_note': 'order qty is documented in README/BOM only; NEST holds 1 kit (user t62u 2026-10-28)' if nest_mode == 'kit' else 'legacy sheets mode may expand qty across SHEETnn',
            'utilization_per_sheet_avg': area / (sheet[0] * sheet[1] * len(files)) if files else 0,
            'rule': 'NEST = CUT + SHEET layers only, all CONTINUOUS, no bend lines (bend lines only in DXF_BEND, also CONTINUOUS; no dashed lines in any DXF - user t16u). Default kit/1BOX: one complete box kit per NEST DXF (user t62u 2026-10-28); shop adjusts nesting on site; do not split SHEETnn for order qty. Use either DXF_CUT or NEST in CAM, not both.'}
    return checks, nest


def main():
    ap = argparse.ArgumentParser(); sp = ap.add_subparsers(dest='cmd', required=True)
    c = sp.add_parser('check'); c.add_argument('--role', required=True, choices=['cut', 'nest', 'bend']); c.add_argument('files', nargs='+')
    c.add_argument('--sheet', default='2440x1220'); c.add_argument('--margin', type=float, default=10); c.add_argument('--gap', type=float, default=10)
    n = sp.add_parser('nodash', help='role-agnostic: FAIL if any DXF (files or dirs, recursive) has a non-continuous linetype'); n.add_argument('paths', nargs='+')
    a = ap.parse_args()
    if a.cmd == 'nodash':
        fs = [q for p in map(Path, a.paths) for q in (sorted(p.rglob('*.dxf')) + sorted(p.rglob('*.DXF')) if p.is_dir() else [p])]
        res = []
        for f in fs:
            e, l = noncontinuous(ezdxf.readfile(f)); res.append({'file': str(f), 'non_continuous_entities': e[:10], 'n_entities': len(e), 'non_continuous_layers': l, 'pass': not e and not l})
        print(json.dumps(res, indent=1, ensure_ascii=False)); sys.exit(0 if res and all(r['pass'] for r in res) else 1)
    if a.cmd == 'check':
        sh = tuple(float(v) for v in a.sheet.lower().split('x'))
        res = [check_dxf(f, a.role, sh, a.margin, a.gap) for f in a.files]
        print(json.dumps(res, indent=1, ensure_ascii=False)); sys.exit(0 if all(r['pass'] for r in res) else 1)


if __name__ == '__main__':
    main()
