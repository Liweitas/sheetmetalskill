#!/usr/bin/env python3
"""v2.8.2 release packager + gate (stdlib + poppler pdfinfo/pdftotext/pdffonts; DXF gate via release_dxf with ezdxf python).
Audit items #1 #2 #3 #6 #7. One complete ASCII zip per release, the release name used EXACTLY as given.

  package  STAGE VER [--zip OUT.zip] [--orders /workspace/orders] [--pdf-pages 4] [--dxf-python PY]
           STAGE is the assembled release folder (STEP/ DXF_CUT/ DXF_BEND/ NEST/ PDF or *.pdf/ DOC/ EVIDENCE/ PREVIEW/ ...).
           Gate (all must pass, else no zip):
             name   VER non-empty, ASCII [A-Za-z0-9._-] only; never rewritten. Anything else -> FAIL, ask the user.
             files  every file name starts with VER; ASCII names; no dotfiles/__MACOSX/nested zip/FCStd backups
             ver    VER inside every STEP header, DXF ($RELEASE custom var or text), every PDF page, every text doc;
                    no OTHER release-like name inside STEP/DXF/PDF (stale version); docs only WARN
             pdf    A3 (420x297 +-1 mm) pages, expected page count, all fonts embedded, Chinese text present
             dxf    release_dxf check: cut/bend/nest roles (closed, no dup/overlap, CUT-only nests, SHEET border, 1:1 mm)
             clash  same VER already used by another folder under --orders -> WARN (name collision, e.g. 001-v1 x2)
           Writes EVIDENCE/{VER}_release_gate.json + {VER}_geometry_sha256.json, then the zip with an explicit arcname map
           (all entries under {VER}/), testzip + byte-for-byte round trip + ASCII names, and a .sha256 next to it.
  geomhash STAGE VER   -> geometry-only hashes (STEP DATA section without header, DXF ENTITIES section); used by rename
  rename   OLD_STAGE OLD_VER NEW_VER NEW_STAGE   (干画图3 rename_release.py practice)
           copies the stage with the VER swapped in names, text docs, STEP header (not DATA) and DXF ($RELEASE, TEXT labels);
           PDFs are NOT text-patched (re-render with the new VER) -> exit 2 listing them. Geometry hashes must be identical.
"""
import argparse, hashlib, json, os, re, shutil, subprocess, sys, zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
VER_OK = re.compile(r'^[A-Za-z0-9._-]+$')
REL_LIKE = re.compile(r'\b[SXR]-[A-Za-z0-9]+(?:-[A-Za-z0-9]+){1,5}-v\d+\b')
TEXT_EXT = {'.md', '.txt', '.csv', '.json', '.py', '.step', '.stp', '.dxf'}
SKIP = re.compile(r'(^|/)(\.|__MACOSX|__pycache__)|\.(zip|FCStd\d+|bak|tmp)$')


def files(stage):
    return sorted(p for p in Path(stage).rglob('*') if p.is_file())


def step_geom(b):
    s = b.decode('latin-1'); i = s.find('DATA;'); return (s[i:] if i >= 0 else s).encode('latin-1')


def dxf_geom(b, ver):
    """ENTITIES section with the release name replaced by a placeholder (BEND DXF TEXT labels carry the name)."""
    s = b.decode('utf-8', 'replace'); i = s.find('ENTITIES'); j = s.find('ENDSEC', i); return s[i:j].replace(ver, '{VER}').encode()


def geomhash(stage, ver):
    """geometry-only hashes keyed by file name with VER -> {VER}: STEP DATA section, DXF ENTITIES section."""
    out = {}
    for p in files(stage):
        e = p.suffix.lower(); rel = str(p.relative_to(stage)).replace(ver, '{VER}')
        if e in ('.step', '.stp'): out[rel] = hashlib.sha256(step_geom(p.read_bytes())).hexdigest()
        elif e == '.dxf': out[rel] = hashlib.sha256(dxf_geom(p.read_bytes(), ver)).hexdigest()
    return out


def sh(cmd, err=False):
    r = subprocess.run(cmd, capture_output=True, text=True); return r.returncode, (r.stdout + r.stderr) if err else r.stdout


def _small_text(p, k, min_mm=3.3):
    """user t16u: A3 legibility screen - words whose bbox height (pdftotext -bbox) < ~min_mm. Heuristic -> WARN only."""
    rc, x = sh(['pdftotext', '-bbox', '-f', str(k), '-l', str(k), str(p), '-'])
    hs = [(float(m.group(4)) - float(m.group(2))) * 25.4 / 72 for m in re.finditer(r'<word xMin="([\d.]+)" yMin="([\d.]+)" xMax="([\d.]+)" yMax="([\d.]+)"', x)]
    return sum(1 for h in hs if h < min_mm * 0.95), len(hs)


def pdf_check(p, ver, pages_expected=None, pages_max=None, min_text_mm=3.3):
    fails = []; warns = []; rc, info = sh(['pdfinfo', str(p)])
    n = int(re.search(r'Pages:\s+(\d+)', info).group(1)) if 'Pages:' in info else 0
    for k in range(1, n + 1):
        rc, pi = sh(['pdfinfo', '-f', str(k), '-l', str(k), str(p)])
        m = re.search(r'Page\s+%d size:\s+([\d.]+) x ([\d.]+)' % k, pi)
        w, h = (float(m.group(1)) * 25.4 / 72, float(m.group(2)) * 25.4 / 72) if m else (0, 0)
        if not (abs(max(w, h) - 420) < 1.5 and abs(min(w, h) - 297) < 1.5): fails.append(f'page {k} not A3 ({w:.1f}x{h:.1f} mm)')
        rc, tx = sh(['pdftotext', '-f', str(k), '-l', str(k), '-layout', str(p), '-'])
        if ver not in tx: fails.append(f'page {k} lacks release name')
        if not re.search(r'[\u4e00-\u9fff]', tx): fails.append(f'page {k} has no Chinese text')
        other = sorted(set(REL_LIKE.findall(tx)) - {ver})
        if other: warns.append(f'page {k} mentions other release names {other} (must be cited sources only, never this part\'s name)')
    if pages_expected and n != pages_expected: fails.append(f'{n} pages, expected {pages_expected}')
    if pages_max and n > pages_max: fails.append(f'{n} pages > max {pages_max} (user t16u: PDF页数尽可能压缩，总装1页+每零件1页)')
    for k in range(1, n + 1):
        try:
            sm, tot = _small_text(p, k, min_text_mm)
            if sm: warns.append(f'page {k}: {sm}/{tot} words smaller than ~{min_text_mm:g} mm at A3 - check legibility; every hole/bend/notch must still be dimensioned')
        except Exception as e:  # noqa - heuristic only
            warns.append(f'page {k}: text-size screen failed {e!r}')
    rc, fo = sh(['pdffonts', str(p)]); rows = [l for l in fo.splitlines()[2:] if l.strip()]
    notemb = [l for l in rows if len(l.split()) >= 5 and l.split()[-5] != 'yes']
    if notemb: fails.append(f'fonts not embedded: {[l.split()[0] for l in notemb]}')
    rc, fe = sh(['pdffonts', str(p)], err=True)
    if 'Mismatch between font type' in fe:   # matplotlib type42 + CFF-based Noto CJK OTF; 干画图3 converts to TTF (Cu2QuPen)
        warns.append('poppler: font type / embedded font file mismatch (CFF CJK in Type42 path) - opens fine in poppler, check on a factory viewer or use the TTF-converted font (references/v2.8.2-delivery-rules.md L44)')
    return {'file': p.name, 'pages': n, 'fonts': len(rows), 'fails': fails, 'warnings': warns, 'pass': not fails}


def gate(stage, ver, orders=None, pdf_pages=None, dxf_python=None, pdf_max_pages=None):
    stage = Path(stage); res = {'release': ver, 'checks': [], 'warnings': []}
    F = lambda name, ok, detail=None: res['checks'].append({'check': name, 'pass': bool(ok), 'detail': detail})
    F('name_ascii_exact', bool(ver) and VER_OK.fullmatch(ver) is not None and ver == ver.strip(),
      'release name must be used exactly as given; non [A-Za-z0-9._-] -> ask the user, never normalize')
    fl = [p for p in files(stage) if not p.name.endswith(('_release_gate.json', '_geometry_sha256.json'))]
    bad_prefix = [str(p.relative_to(stage)) for p in fl if not p.name.startswith(ver)]
    bad_ascii = [str(p.relative_to(stage)) for p in fl if not str(p.relative_to(stage)).isascii()]
    junk = [str(p.relative_to(stage)) for p in fl if SKIP.search(str(p.relative_to(stage)))]
    F('every_file_prefixed_with_release', not bad_prefix, bad_prefix); F('ascii_file_names', not bad_ascii, bad_ascii); F('no_junk_files', not junk, junk)
    vmiss, vother, dmiss = [], [], []
    for p in fl:
        e = p.suffix.lower()
        if e not in TEXT_EXT: continue
        s = p.read_bytes().decode('utf-8', 'replace')
        if e in ('.step', '.stp'):
            hdr = s[:s.find('DATA;')]
            if ver not in hdr: vmiss.append(p.name)
            o = sorted(set(REL_LIKE.findall(hdr)) - {ver})
            if o: vother.append((p.name, o))
        elif e == '.dxf':
            if ver not in s: vmiss.append(p.name)
            o = sorted(set(REL_LIKE.findall(s)) - {ver})
            if o: vother.append((p.name, o))
        elif e in ('.md', '.txt', '.csv') and ver not in s: dmiss.append(p.name)
        if e in ('.md', '.txt', '.csv'):
            o = sorted(set(REL_LIKE.findall(s)) - {ver})
            if o: res['warnings'].append(f'{p.name} mentions other release names {o} (ok only for cited references)')
    F('release_name_inside_step_dxf', not vmiss, vmiss); F('no_stale_release_in_step_dxf', not vother, vother)
    if dmiss: res['warnings'].append(f'docs without release name: {dmiss}')
    pdfs = [p for p in fl if p.suffix.lower() == '.pdf']; F('pdf_present', bool(pdfs), [p.name for p in pdfs])
    for p in pdfs:
        r = pdf_check(p, ver, pdf_pages, pdf_max_pages); F('pdf:' + p.name, r['pass'], r); res['warnings'] += [p.name + ': ' + w for w in r['warnings']]
    py = dxf_python or os.environ.get('SM_DXF_PYTHON', '/workspace/addendum-venv/bin/python')
    for role, sub in (('cut', 'DXF_CUT'), ('bend', 'DXF_BEND'), ('nest', 'NEST')):
        ds = sorted((stage / sub).glob('*.dxf')) if (stage / sub).exists() else []
        if not ds:  # v2.8.2: flat zip layout (u_l_t7u OPEN_ME.zip) -> role from the file name <VER>_CUT_/_BEND_/_NEST_
            ds = sorted(p for p in fl if p.suffix.lower() == '.dxf' and p.name.startswith(f'{ver}_{role.upper()}_'))
        if not ds: F(f'dxf_{role}_present', False, f'no {sub}/*.dxf'); continue
        rc, out = sh([py, str(HERE / 'release_dxf.py'), 'check', '--role', role, *map(str, ds)])
        try: det = [{'file': r['file'], 'pass': r['pass'], 'fails': r['fails']} for r in json.loads(out[out.find('['):])]
        except Exception: det = out[-2000:]
        F(f'dxf_{role}', rc == 0, det)
    if orders:
        hits = [str(p) for p in Path(orders).glob(f'*/**/{ver}') if p.is_dir() and stage.resolve() not in (p.resolve(), *p.resolve().parents) and p.resolve() not in stage.resolve().parents]
        if hits: res['warnings'].append(f'NAME COLLISION: {ver} already used by {hits} - make sure the user means this geometry')
        res['name_collisions'] = hits
    res['pass'] = all(c['pass'] for c in res['checks'])
    return res


def write_zip(stage, ver, zpath):
    stage = Path(stage); zpath = Path(zpath)
    amap = [(p, f'{ver}/{p.relative_to(stage).as_posix()}') for p in files(stage)]
    assert all(a.isascii() for _, a in amap), [a for _, a in amap if not a.isascii()]
    tmp = zpath.with_suffix('.zip.part')
    with zipfile.ZipFile(tmp, 'w', zipfile.ZIP_DEFLATED) as z:   # always rebuilt from scratch, never appended
        for src, arc in amap: z.write(src, arc)
    with zipfile.ZipFile(tmp) as z:
        assert z.testzip() is None
        names = z.namelist(); assert len(names) == len(set(names)) == len(amap)
        for src, arc in amap: assert z.read(arc) == src.read_bytes(), arc
    tmp.replace(zpath)
    h = hashlib.sha256(zpath.read_bytes()).hexdigest(); Path(str(zpath) + '.sha256').write_text(f'{h}  {zpath.name}\n')
    return {'zip': str(zpath), 'entries': len(amap), 'sha256': h, 'ascii': True, 'roundtrip': True}


def rename(old, old_ver, new_ver, new):
    """copy OLD stage as NEW_VER: names + STEP header + DXF (header var, TEXT labels) + text docs. Geometry hashes must be equal.
    PDFs are never text-patched: they are listed for re-rendering with the new name (every page must show it)."""
    old, new = Path(old), Path(new); assert VER_OK.fullmatch(new_ver), 'new name must be ASCII [A-Za-z0-9._-]; ask the user'
    assert not new.exists(), new
    O, N = old_ver.encode(), new_ver.encode(); todo_pdf = []
    for p in files(old):
        if p.suffix.lower() == '.zip' or p.name.endswith('.zip.sha256'): continue
        q = new / Path(*[x.replace(old_ver, new_ver) for x in p.relative_to(old).parts]); q.parent.mkdir(parents=True, exist_ok=True)
        e = p.suffix.lower(); b = p.read_bytes()
        if e == '.pdf': todo_pdf.append(str(q)); continue
        if e in ('.step', '.stp'): i = b.find(b'DATA;'); q.write_bytes(b[:i].replace(O, N) + b[i:])   # header only
        elif e in TEXT_EXT: q.write_bytes(b.replace(O, N))
        else: shutil.copy2(p, q)
    g0, g1 = geomhash(old, old_ver), geomhash(new, new_ver)
    return {'geometry_unchanged': g0 == g1, 'files_compared': len(g0), 'pdf_to_regenerate': todo_pdf}


def main():
    ap = argparse.ArgumentParser(); sp = ap.add_subparsers(dest='cmd', required=True)
    a = sp.add_parser('package'); a.add_argument('stage'); a.add_argument('ver'); a.add_argument('--zip'); a.add_argument('--orders')
    a.add_argument('--pdf-pages', type=int); a.add_argument('--pdf-max-pages', type=int, help='user t16u: fail if the PDF has more pages'); a.add_argument('--dxf-python')
    b = sp.add_parser('geomhash'); b.add_argument('stage'); b.add_argument('ver')
    c = sp.add_parser('rename'); c.add_argument('old'); c.add_argument('old_ver'); c.add_argument('new_ver'); c.add_argument('new')
    x = ap.parse_args()
    if x.cmd == 'geomhash': print(json.dumps(geomhash(x.stage, x.ver), indent=1)); return
    if x.cmd == 'rename':
        r = rename(x.old, x.old_ver, x.new_ver, x.new); print(json.dumps(r, indent=1, ensure_ascii=False))
        sys.exit(0 if r['geometry_unchanged'] and not r['pdf_to_regenerate'] else 2)
    st = Path(x.stage); ev = st / 'EVIDENCE'; ev.mkdir(exist_ok=True)
    g = gate(st, x.ver, x.orders, x.pdf_pages, x.dxf_python, x.pdf_max_pages)
    (ev / f'{x.ver}_geometry_sha256.json').write_text(json.dumps(geomhash(st, x.ver), indent=1))
    (ev / f'{x.ver}_release_gate.json').write_text(json.dumps(g, indent=1, ensure_ascii=False))
    for c_ in g['checks']: print(('PASS ' if c_['pass'] else 'FAIL ') + c_['check'])
    for w in g['warnings']: print('WARN ' + w)
    if not g['pass']: sys.exit('gate failed - no zip written')
    z = write_zip(st, x.ver, x.zip or st.parent / f'{x.ver}_CONFIRM_DRAFT.zip'); print(json.dumps(z, indent=1))


if __name__ == '__main__':
    main()
