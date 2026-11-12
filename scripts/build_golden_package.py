#!/usr/bin/env python3
"""MCP/API 确认稿入口。几何按尺寸选U围+L或U+端板，PDF只走同一金样引擎。

通用入口 build_general_package 的 11 页灰图不从这里出。
usage: golden_entry.py BRIEF.json --output OUT [--naming NAMING.json]
"""
import csv, hashlib, json, math, os, shutil, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SK = HERE.parent
PIPE = SK / "pipelines" / "u_endplates"
GOLD = SK / "assets" / "bend-pdf-golden-001-visual" / "engine_u_endplates.py"
FONT = os.environ.get("SM_CJK_FONT", "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc")
FC = os.environ.get("SM_FC") or os.environ.get("FREECAD_PYTHON") or sys.executable


def fail(msg):
    print(json.dumps({"ok": False, "error": msg, "production_release": False},
                     ensure_ascii=False), file=sys.stderr)
    raise SystemExit(2)


def pipe_brief(brief, code):
    """通用 brief -> 共用几何 worker brief。缺外形或孔位就拒绝，不补坐标。"""
    dims = brief.get("dimensions") or {}
    try:
        L, W, H = (float(dims["length"]), float(dims["width"]), float(dims["height"]))
        t = float(brief["thickness"])
    except (KeyError, TypeError, ValueError):
        fail("brief needs dimensions.length/width/height and thickness")
    if not all(math.isfinite(v) and v > 0 for v in (L, W, H, t)):
        fail("dimensions and thickness must be finite positive numbers")
    if str(brief.get('material', '201')) != '201':
        fail('this adapter supports 201 stainless only')
    basis = brief.get('dim_basis', 'finished_outer')
    if basis not in ('finished_outer', 'body_outer'):
        fail('dim_basis must be finished_outer or body_outer')
    ri, g = float(brief.get('Ri', .8)), float(brief.get('g', .5))
    if not all(math.isfinite(v) and v >= 0 for v in (ri, g)) or ri == 0:
        fail('Ri must be positive and g nonnegative')
    structure = brief.get('structure') or ('u_endplates' if max(L, W) >= H else 'u_l_t7u')
    if structure not in ('u_endplates', 'u_l_t7u'):
        fail('unsupported structure')
    offset = g + t
    finished = [L, W, H] if basis == 'finished_outer' else [L + 2*offset, W + 2*offset, H]
    if basis == 'finished_outer':
        L, W = L - 2*offset, W - 2*offset
    if min(L, W, H) <= 2*(ri+t):
        fail('box is too small for the selected thickness/radius')
    bd = 4.24 if t == 2 else 1.7*t
    k = float(brief.get('K', ((2*(ri+t)-bd)/(math.pi/2)-ri)/t))
    if not math.isfinite(k) or not 0 <= k <= 1:
        fail('K must be between 0 and 1')
    fixings = {}
    for key, limit, default in (("long_x", L, [20, L / 2, L - 20]),
                                ("short_y", W, [20, W / 2, W - 20])):
        values = brief.get(key, default)
        if (not isinstance(values, list) or
                any(type(v) not in (int, float) or not math.isfinite(v) or not 0 < v < limit for v in values) or
                len(set(values)) != len(values)):
            fail(key + " must contain unique coordinates inside the body")
        fixings[key] = values
    quantity = brief.get("quantity", 1)
    if type(quantity) is not int or quantity < 1:
        fail("quantity must be a positive integer")
    handles = brief.get("handles") or {}
    if handles:
        if (not isinstance(handles, dict) or
                set(handles) - {"profile", "cx", "cy"} or
                handles.get("profile") != "handle-85-62-30-v1"):
            fail("handles needs the supported handle-85-62-30-v1 lid profile")
        handles = dict(handles)
        centers = handles.get("cx")
        if basis == 'finished_outer' and isinstance(centers, list):
            centers = [x-offset for x in centers]
            handles['cx'] = centers
            if handles.get('cy') is not None:
                handles['cy'] -= offset
        cy = W / 2 if handles.get("cy") is None else handles["cy"]
        if (not isinstance(centers, list) or not centers or
                any(type(x) not in (int, float) or not math.isfinite(x) or
                    not 18.3 < x < L - 18.3 for x in centers) or
                len(set(centers)) != len(centers) or
                type(cy) not in (int, float) or not math.isfinite(cy) or
                not 45.8 < cy < W - 45.8):
            fail("handle mounting holes must fit inside the lid")
    panels = [h for h in brief.get('holes', []) if h.get('part_id') != 'LID']
    rects = brief.get('rect_cutouts') or []
    if (panels or rects) and basis != 'body_outer':
        fail('panel features require explicit body_outer coordinates')
    panel_ids = set()
    def panel_bounds(h, point, halfsize):
        part, axis = h.get('part_id'), h.get('axis')
        if structure == 'u_l_t7u' and part == 'U' and axis in ([1, 0, 0], [-1, 0, 0]):
            normal, face, tangents, limits = 0, (0, L), (1, 2), (W, H-t-(brief.get('q') or .2))
        elif part == 'U' and axis in ([0, 1, 0], [0, -1, 0]):
            normal, face, tangents, limits = 1, (0,), (0, 2), (L, H-t-(brief.get('q') or .2))
        elif part in ('END_L', 'END_R') and axis in ([1, 0, 0], [-1, 0, 0]):
            normal, face, tangents, limits = 0, ((0,) if part == 'END_L' else (L,)), (1, 2), (W, H-t-(brief.get('q') or .2))
        else:
            fail('unsupported panel part/axis')
        if (not isinstance(point, list) or len(point) != 3 or
                any(type(v) not in (int, float) or not math.isfinite(v) for v in point) or
                not any(abs(point[normal]-v) < 1e-6 for v in face)):
            fail('panel feature must lie on its declared outer face')
        if any(min(point[i], limit-point[i])-radius < ri+t
               for i, limit, radius in zip(tangents, limits, halfsize)):
            fail('panel feature crosses an edge/bend zone')
        if not h.get('id') or h['id'] in panel_ids:
            fail('panel feature IDs must be present and unique')
        panel_ids.add(h['id'])
    for h in panels:
        d = h.get('diameter')
        if type(d) not in (int, float) or not math.isfinite(d) or d <= 0:
            fail('panel diameter must be finite and positive')
        panel_bounds(h, h.get('point'), [d/2, d/2])
    for part in {h['part_id'] for h in panels if h.get('purpose') == 'handle'}:
        group = [h for h in panels if h['part_id']==part and h.get('purpose')=='handle']
        pts = sorted((h['point'][2], h['point'][1]) for h in group)
        if (part not in ('END_L', 'END_R') or len(pts)!=4 or
                any(abs(h['diameter']-6.6)>1e-6 for h in group) or
                abs(pts[0][0]-pts[1][0])>1e-6 or abs(pts[2][0]-pts[3][0])>1e-6 or
                any(abs(p-w)>1e-6 for p,w in zip(sorted((pts[1][1]-pts[0][1], pts[3][1]-pts[2][1])), (62,85))) or
                abs(pts[2][0]-pts[0][0]-30)>1e-6 or
                any(abs((a+b)/2-W/2)>1e-6 for a,b in ((pts[0][1],pts[1][1]),(pts[2][1],pts[3][1]))) or
                abs(sum(p[0] for p in pts)/4-(H-t-brief.get('q', .2))/2)>1e-6):
            fail('panel handle must be centered 85/62/30, wide row up or down, 4x6.6')
    for h in rects:
        if h.get('part_id') != 'U':
            fail('rectangular openings currently require the U front face')
        size, radius = h.get('size_xy'), h.get('corner_radius', 0)
        if (not isinstance(size, list) or len(size) != 2 or
                any(type(v) not in (int, float) or not math.isfinite(v) or v <= 0 for v in size) or
                type(radius) not in (int, float) or not math.isfinite(radius) or
                not 0 <= radius < min(size)/2):
            fail('invalid rectangular panel opening')
        panel_bounds(h, h.get('center'), [v/2 for v in size])
    holes = []
    for h in brief.get("holes") or []:
        if h.get("part_id") != "LID":
            continue
        pt = h.get("point") or []
        if h.get("diameter") is None or len(pt) < 2:
            fail("each lid hole needs diameter and point")
        item = {"d": float(h["diameter"]), "x": float(pt[0]), "y": float(pt[1])}
        if basis == 'finished_outer':
            item['x'] -= offset
            item['y'] -= offset
        if not all(math.isfinite(v) for v in item.values()) or item['d'] <= 0:
            fail('hole diameter and coordinates must be finite; diameter must be positive')
        if h.get('axis', [0, 0, 1]) not in ([0, 0, 1], [0, 0, -1]):
            fail('LID hole axis must be vertical')
        if len(pt) > 2 and abs(float(pt[2])-H) > .001:
            fail('LID hole Z must equal the closed height')
        if h.get("d_bolt") and h.get("pitch"):
            item["d_bolt"] = float(h["d_bolt"])
            item["pitch"] = float(h["pitch"])
        circles = [(item['x'], item['y'], item['d'])]
        if item.get('d_bolt'):
            if not all(math.isfinite(item[key]) and item[key] > 0 for key in ('d_bolt', 'pitch')):
                fail('bolt diameter and pitch must be finite positive numbers')
            circles += [(item['x']+sx*item['pitch']/2, item['y']+sy*item['pitch']/2, item['d_bolt'])
                        for sx in (-1, 1) for sy in (-1, 1)]
        if any(min(x+offset, y+offset, L+offset-x, W+offset-y) < d/2+ri+t
               for x, y, d in circles):
            fail('functional hole crosses the lid bend zone')
        holes.append(item)
    if not holes and not panels and not rects and not handles:
        fail("brief needs at least one functional hole")
    if structure == 'u_l_t7u' and any(h['part_id'] != 'U' or h.get('axis') not in ([1, 0, 0], [-1, 0, 0]) for h in panels + rects):
        fail('U+L panel features currently support the two X-normal U walls only')
    return {
        "structure": structure,
        "release": code,
        "material_cn": "201不锈钢",
        "dim_basis": "body_outer",
        "dimension_source": basis,
        "finished_outer_mm": finished,
        "height_basis": "total_incl_lid",
        "L": L, "W": W, "H": H, "t": t,
        "Ri": ri,
        "K": k,
        "kr_source": 'user' if 'K' in brief else ('t2_machine_BD4.24' if t == 2 else 'candidate_BD1.7t'),
        "g": g,
        "q": brief.get("q"),
        "skirt": float(brief.get("skirt", 15)),
        "corner_gap": float(brief.get("corner_gap", 0.2)),
        "corner_gap_source": "candidate",
        **fixings,
        "quantity": quantity,
        "confirm": brief.get("confirm") or {},
        "handles": handles,
        "lid_ports": holes,
        "panel_holes": panels,
        "rect_cutouts": rects,
        "production_release": False,
    }


def main(argv):
    if len(argv) < 4 or argv[2] != "--output":
        fail("usage: golden_entry.py BRIEF.json --output OUT [--naming NAMING.json]")
    src = json.loads(Path(argv[1]).read_text())
    out = Path(argv[3]).resolve()
    naming = None
    if "--naming" in argv:
        naming = json.loads(Path(argv[argv.index("--naming") + 1]).read_text())
    code = (naming or {}).get("channel") and "-".join([
        naming["channel"], naming["material"], str(naming["thickness"]),
        naming["date"], str(naming["number"]), "v" + str(naming["factory_version"]),
    ])
    if not code:
        fail("naming file required; refusing to invent a drawing code")
    if out.exists():
        fail("fresh output dir required")
    job = pipe_brief(src, code)
    work_root = out.parent / "pipe"
    work_root.mkdir(parents=True)
    brief_path = work_root / "pipe.json"
    brief_path.write_text(json.dumps(job, ensure_ascii=False, indent=2))
    env = {**os.environ, "SM_JOB": str(brief_path), "SM_CJK_FONT": FONT}
    from execution_log import run_stage
    logs = work_root / 'logs'
    env['PYTHONPATH'] = str(PIPE)
    env['PYTHONUNBUFFERED'] = '1'
    def run(name, *cmd):
        return run_stage(logs, name, cmd, env=env)
    run('geometry', FC, '-B', PIPE / 'run.py', brief_path, work_root, '--geometry-only')
    run('cad_verify', FC, '-B', HERE / 'verify_golden_cad.py', work_root, brief_path)
    rep = json.loads((work_root / 'work/report.json').read_text())
    from conflict_checks import run as conflicts
    checks = conflicts({
        **rep['params'], 'K': job['K'], 'm4_count': len(rep['holes']),
        'deep_u': [{'part': 'U', 'wall_h': rep['params']['Hb'], 'inner_w': job['W']-2*job['t']}],
        'requested': {'handles': bool(job['handles']), 'roof_ports': bool(job['lid_ports'])},
        'features': {'handles': len(rep['handle_holes']), 'roof_ports': len(job['lid_ports'])},
    }, rep)
    (work_root / 'work/conflicts.json').write_text(json.dumps(checks, ensure_ascii=False, indent=2))
    if any(c['level'] == 'ERROR' for c in checks):
        fail('conflict check failed; see conflicts.json')
    stage = out / code
    shutil.copytree(work_root / 'stage' / code, stage)
    add = work_root / 'addendum-tools'
    add.mkdir()
    gold_dir = GOLD.parent
    for name in ('make_bend_pdf.py', 'pdf_common.py', 'bidir.py', 'views.py', 'engine_u_endplates.py'):
        (add / name).symlink_to(gold_dir / name)
    for line in (gold_dir / 'GOLDEN_SCRIPTS.sha256').read_text().splitlines():
        digest, name = line.split()
        if hashlib.sha256((gold_dir / name).read_bytes()).hexdigest() != digest:
            fail('golden manifest hash mismatch: '+name)
    run('golden_precheck', FC, '-B', HERE / 'check_bend_pdf_golden.py', work_root)
    # Use the installed TrueType CJK font; subset the actual sources and this order.
    from fontTools.ttLib import TTFont
    from fontTools.subset import Subsetter, Options
    font = TTFont(FONT, fontNumber=0)
    text = ''.join(p.read_text(errors='replace') for p in list(gold_dir.glob('*.py'))+[brief_path])
    subset = Subsetter(options=Options())
    subset.populate(text=text+''.join(chr(c) for c in range(32, 127)))
    subset.subset(font)
    logs.mkdir(exist_ok=True)
    subset_path = logs / 'cjk-sub.ttf'
    font.save(subset_path)
    env['SM_CJK_FONT'] = str(subset_path)
    run('golden_pdf', FC, '-B', add / 'make_bend_pdf.py', work_root / 'work', stage)
    run('golden_postcheck', FC, '-B', HERE / 'check_bend_pdf_golden.py', work_root,
        '--strict-overlap', '--json-out', logs / 'golden_gate.json')
    pdfs = list(stage.glob('*_BEND_PDF_A3_CN.pdf'))
    if len(pdfs) != 1:
        fail('golden pdf missing')
    run('render', 'pdftoppm', '-png', '-r', '90', pdfs[0], work_root / 'page')
    doc, evidence = stage / 'DOC', stage / 'EVIDENCE'
    doc.mkdir(); evidence.mkdir()
    rep = json.loads((work_root / 'work/report.json').read_text())
    from conflict_checks import m4_thin_sheet_warning_cn
    warning = m4_thin_sheet_warning_cn(job['t'], job['material_cn'])
    with (doc / f'{code}_BOM.csv').open('w') as stream:
        writer = csv.writer(stream)
        writer.writerow(['release', 'part', 'per_box', 'order_boxes', 'material', 'thickness_mm', 'flat_L_mm', 'flat_W_mm'])
        for name, part in rep['parts'].items():
            writer.writerow([code, name, 1, job['quantity'], job['material_cn'], job['t'], *part['flat_size']])
    with (doc / f'{code}_LID_HOLES.csv').open('w') as stream:
        writer = csv.writer(stream)
        writer.writerow(['release', 'formed_x_body_mm', 'formed_y_body_mm', 'diameter_mm'])
        check = json.loads((work_root / 'work/cad_verification.json').read_text())
        writer.writerows([code, *row] for row in check['roof_holes_from_STEP'])
    if job['panel_holes']:
        with (doc / f'{code}_PANEL_HOLES.csv').open('w') as stream:
            writer = csv.writer(stream)
            writer.writerow(['release', 'part', 'id', 'diameter_mm', 'formed_X', 'formed_Y', 'formed_Z'])
            writer.writerows([code, h['part_id'], h['id'], h['diameter'], *h['point']]
                             for h in check['panel_holes_from_STEP'])
    readme = (f'{code} 客户确认稿；production_release=false\n'
              f'合盖外尺寸 {job["finished_outer_mm"]} mm；{job["material_cn"]}；t={job["t"]}mm。\n'
              f'结构：{"U围＋L（L盖U，0缝0退让）＋03盖" if job["structure"] == "u_l_t7u" else "U＋两外封端板＋03盖"}；盖顶把手安装组{len(job["handles"].get("cx", []))}；端板把手孔{sum(h.get("purpose")=="handle" for h in job["panel_holes"])}个。\n'
              f'Ri={job["Ri"]}；K={job["K"]}；来源{job["kr_source"]}；工厂试折未标定。\n'
              '孔坐标详见源需求、解析参数、STEP回读报告及PDF孔表；接口小孔按本单明确孔径制作。\n'
              '盖-体：箱体Ø3.3攻M4、盖裙Ø4.5；'+warning+'。\n'
              'NEST仅一套；单件CUT与NEST择一加工，勿重复切割。\n'
              '图纸PDF仅由skill金样五文件生成；完整日志及各阶段资源记录见EVIDENCE。\n'
              '实物试折试装未进行，非生产放行。\n')
    (doc / f'{code}_README.txt').write_text(readme)
    (doc / f'{code}_PARAMS.json').write_text(json.dumps(job, ensure_ascii=False, indent=2))
    for folder in (work_root / 'work', logs):
        for p in sorted(folder.iterdir()):
            if p.is_file() and p.suffix in ('.json', '.jsonl', '.log'):
                shutil.copy2(p, evidence / (code+'_'+p.name))
    for name, p in [('source_brief.json', Path(argv[1])), ('resolved_brief.json', brief_path)]:
        shutil.copy2(p, evidence / (code+'_'+name))
    sources = list(PIPE.glob('*.py'))+list(gold_dir.glob('*.py'))+[
        Path(__file__), HERE / 'execution_log.py', HERE / 'verify_golden_cad.py',
        HERE / 'check_bend_pdf_golden.py', HERE / 'native03_check.py', HERE / 'corner03.py',
        HERE / 'rect_cutout_tool.py', HERE / 'dxf_topology.py']
    (evidence / f'{code}_SCRIPT_SHA256.json').write_text(json.dumps(
        {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}, indent=2))
    preview = stage / 'PREVIEW'; preview.mkdir(exist_ok=True)
    for p in work_root.glob('page-*.png'):
        shutil.copy2(p, preview / (code+'_'+p.name))
    run('package', FC, '-B', HERE / 'release_package.py', 'package', stage, code,
        '--zip', out / f'{code}_CONFIRM_DRAFT.zip', '--dxf-python', FC)
    print(json.dumps({"ok": True, "pdf": str(pdfs[0]), "drawing_code": code,
                      "pipeline": "bend-pdf-golden-001-visual",
                      "production_release": False}, ensure_ascii=False))


if __name__ == "__main__":
    main(sys.argv)
