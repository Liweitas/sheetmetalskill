"""Chinese confirmation sheets; use existing CAD evidence without manufacturing claims."""
import math
import re
from cn_workshop import Sheet, fmt, material, name, ORDER

ORIGINS = {'user': '用户指定', 'experience_default': '经验默认',
           'calculated': '计算候选', 'pending': '待确认'}
MISSING = {'units': '尺寸单位', 'dimension_basis': '内外尺寸口径',
           'height_basis': '含盖或裸盒高度口径', 'lid_required': '是否有盖',
           'thickness': '板厚', 'material': '材质牌号', 'dimensions': '长宽高',
           'dimensions.length': '长度', 'dimensions.width': '宽度',
           'dimensions.height': '高度'}
ISSUES = {
 'MATERIAL_UNSPECIFIED': '材质牌号待确认。',
 'K_AND_TOOLING_CALIBRATION_NOT_PROVIDED': '中性层系数、实际刀模、回弹及实折尚未标定。',
 'HANDLE_BODY_ENVELOPE_AND_LOAD_UNVERIFIED': '把手实体、活动包络与承载尚未验证。',
 'ROOF_PORT_INTERFACE_REFERENCE_UNCONFIRMED': '盖顶开孔的接口规格尚未确认。',
 'FACTORY_FIRST_ARTICLE_ASSEMBLY_AND_SIGNED_RELEASE_RECORD_REQUIRED': '须完成首件试折、装配与工厂放行记录。',
 'EXPLICIT_LID_ROOT_ENVELOPE_CONFLICT': '盖根存在几何配合冲突；当前尺寸保留，未自动加顶隙或接受修配。',
 'DEFAULT_SKIRT_GEOMETRY_CONFLICT': '盖裙与当前圆角或结构冲突；默认15 mm保留，调整须确认。',
 'SKIRT_FIXING_STRAIGHT_WALL_CONFLICT': '盖裙直壁与固定孔位置冲突；不得自动加高盖裙或移孔。',
 'CORNER_RELIEF_CANDIDATE_OUTSIDE_ADAPTER': '角部避让超出当前适配范围；须确认角部方案。',
 'DEFAULT_CORNER_RELIEF_OUTSIDE_ADAPTER': '当前默认角部避让无法适配；须确认独立调整候选。',
 'CORNER_RELIEF_CANDIDATE_REQUIRES_CONFIRMATION': '角缝为独立计算候选；原默认值保留，未经确认不得生产。',
}


def source(compiled, key):
    row = next((r for r in compiled.get('parameter_sources', [])
                if r.get('parameter') == key), None)
    if not row:
        return '来源待核'
    label = ORIGINS.get(row.get('origin'), '来源待核')
    if row.get('needs_confirmation') and label != '待确认':
        label += '，待确认'
    return label


def scalar(compiled, key, fallback=None):
    row = next((r for r in compiled.get('parameter_sources', [])
                if r.get('parameter') == key), None)
    return row.get('value') if row else fallback


def summary_rows(compiled, report=None):
    """Keep source precision and render only essential, translated scalar facts."""
    job = compiled.get('job') or {}
    rows = ['本稿仅用于尺寸与方案确认；尚未完成制造展开、套料和折弯工艺验收，禁止据此投产。']
    mat = job.get('material', scalar(compiled, 'material'))
    thick = job.get('thickness', scalar(compiled, 'thickness'))
    qty = job.get('delivery', {}).get('sets')
    rows.append('材料：' + material(mat) + '（' + source(compiled, 'material') + '）'
                + ('　板厚：' + fmt(thick) + ' mm（' + source(compiled, 'thickness') + '）' if thick is not None else '　板厚：待提供')
                + ('　数量：' + str(qty) + '套' if qty is not None else '　数量：待确认'))
    dims = job.get('dimensions') or {}
    if all(k in dims for k in ('length', 'width', 'height')):
        rows.append('输入箱体外长×宽：' + fmt(dims['length']) + '×' + fmt(dims['width'])
                    + ' mm；' + ('闭盖金属总高：' if job.get('lid_required') else '裸盒总高：')
                    + fmt(dims['height']) + ' mm。实际成形尺寸以各图标注为准。')
    ri = job.get('Ri', scalar(compiled, 'Ri'))
    if ri is not None:
        rows.append('内圆角：R' + fmt(ri) + ' mm（' + source(compiled, 'Ri') + '）；补偿与刀模须实折确认。')
    lid = job.get('lid') or {}
    skirt = lid.get('skirt_height', scalar(compiled, 'lid.skirt_height'))
    if skirt is not None:
        line = '盖裙外高：' + fmt(skirt) + ' mm（' + source(compiled, 'lid.skirt_height') + '）'
        for key, label in [('g', '单边间隙'), ('roof_gap', '顶隙'), ('corner_gap', '03角缝')]:
            val = lid.get(key, scalar(compiled, 'lid.' + key))
            if val is not None:
                line += '　' + label + '：' + fmt(val) + ' mm'
        rows.append(line + '。03为盖裙角部方案，未作制造展开验收。')
    method = {'u_external_ends': '侧底侧U＋两外端板＋盖',
              'u_wrap_bottom_l': '三面U围＋底侧L件＋盖'}.get(job.get('method'))
    if method:
        rows.append('拆件结构：' + method + '。外封板轮廓退让不等于轴向接合缝。')
    if report:
        owners = list(report['parts'])
        for inter in report.get('intersections', []):
            rows.append('实测交叠：' + '与'.join(name(o, owners) for o in inter['parts'])
                        + '，' + fmt(inter['volume_mm3']) + ' 立方毫米；数值保留，未据此自动接受现场修配。')
    for item in compiled.get('adjustment_candidates', []):
        if 'candidate_q_mm' in item:
            rows.append('顶隙调整建议：当前' + fmt(item['current_q_mm']) + ' mm → 候选'
                        + fmt(item['candidate_q_mm']) + ' mm；待确认，本稿未采用。')
        if 'default_skirt_mm' in item:
            rows.append('盖裙默认' + fmt(item['default_skirt_mm']) + ' mm保持不变；相关孔位、圆角或拆件方案须另行确认。')
    original = scalar(compiled, 'lid.corner_gap.original')
    if original is not None:
        rows.append('原角缝' + fmt(original) + ' mm保留；当前派生候选不等于用户已确认值。')
    known = set()
    for issue in compiled.get('pending', []):
        if issue in ISSUES and issue not in known:
            rows.append(ISSUES[issue]);known.add(issue)
    if any(issue not in ISSUES for issue in compiled.get('pending', [])):
        rows.append('其余接口、来源与工艺待核项见独立参数报告；本稿不替代确认记录。')
    return rows


def bbox_dimensions(box):
    if len(box) != 6 or not all(math.isfinite(float(x)) for x in box):
        raise ValueError('CONFIRMATION_INVALID_ACTUAL_BBOX')
    result = [float(box[i+3])-float(box[i]) for i in range(3)]
    if any(x <= 0 for x in result):
        raise ValueError('CONFIRMATION_INVALID_ACTUAL_BBOX')
    return result


def write(path, compiled, report=None, projections=None):
    """No geometry generation or sidecar edits; callers retain integrity contracts."""
    job = compiled.get('job')
    revision = (job or {}).get('delivery', {}).get('revision', '确认稿')
    if not isinstance(revision, str) or not re.fullmatch(r'(?:R\d+|v\d+|确认稿)', revision):
        revision = '确认稿'
    book = Sheet(path, revision)
    labels = []
    book.start('尺寸与方案确认单')
    y = 748
    for row in summary_rows(compiled, report):
        if y < 105:
            book.end();book.start('尺寸与方案确认单：续页');y = 748
        y = book.para(40, y, row, 1100, 13)
    if not job:
        status = compiled.get('status')
        if status == 'UNSUPPORTED_SHAPE_REQUIRES_ADAPTER':
            lines = ['异形需提供完整尺寸图或原始实体模型，并确认制造拆件；当前未生成成形模型或展开。']
        elif status == 'NEEDS_PROCESS_DECISION':
            lines = ['当前工艺组合存在冲突；尚未生成成形模型或展开。请确认角部、孔位或结构调整方案；默认盖裙15 mm不自动改变。']
        else:
            lines = ['请补充：' + '、'.join(dict.fromkeys(MISSING.get(x, '尺寸图与工艺输入（详见参数报告）') for x in compiled.get('missing', []))) + '。',
                     '关键输入未齐；当前未生成成形模型、展开、套料或机床程序。']
        for line in lines:
            if y < 105:
                book.end();book.start('需确认事项');y = 748
            y = book.para(40, y-12, line, 1100, 15)
    elif not report or not projections:
        book.para(40, y-12, '实际成形报告或投影未就绪；本稿不展示推测图形，须先完成实体核查。', 1100, 15)
    book.end()
    if not job or not report or not projections:
        book.cv.save();return
    parts = report['parts'];owners = list(parts)
    boxes = [p['bbox'] for p in parts.values()]
    for bb in boxes:
        bbox_dimensions(bb)
    assembly = [min(b[i] for b in boxes) for i in range(3)] + [max(b[i] for b in boxes) for i in range(3, 6)]
    for owner in ['ASSEMBLY'] + [o for o in ORDER if o in parts]:
        views = projections.get(owner, {})
        bb = assembly if owner == 'ASSEMBLY' else parts[owner]['bbox']
        dd = bbox_dimensions(bb)
        book.start(name(owner, owners) + '：实际成形尺寸')
        book.text(40, 765, '尺寸由同版实体回读；本页仅为成形确认，未给出展开折弯定位。', 11)
        for key, rect, axes, title in [('front', (30,430,550,325), 'XZ', '正视'), ('right', (610,430,550,325), 'YZ', '右视'), ('top', (30,60,550,325), 'XY', '俯视')]:
            if any(views.get(key, [])):
                book.ortho(views[key], rect, title, owner, axes, dd, labels)
            else:
                book.text(rect[0]+20, rect[1]+rect[3]/2, title+'投影缺失，待补充', 13)
        if any(views.get('isometric', [])):
            book.iso(views['isometric'], (610,60,550,325), '斜视：真实成形尺寸', owner, bb, labels)
        else:
            book.text(630,220,'斜视投影缺失，待补充',13)
        book.end()
    lines = projections.get('EXPLODED', {}).get('isometric', [])
    shifts = report.get('exploded_translations_mm') or {}
    if any(lines) and all(o in shifts for o in owners):
        from formed_isometric import iso_point
        book.start('爆炸分件图：标注原零件成形尺寸')
        m, _ = book.plot(lines, (30,80,800,650), '装配关系')
        for index, owner in enumerate(o for o in ORDER if o in parts):
            bb = parts[owner]['bbox'];dd = bbox_dimensions(bb);delta = shifts[owner]
            pt = iso_point([(bb[i]+bb[i+3])/2+delta[i] for i in range(3)])
            y = 740-index*125
            book.cv.line(m[0]*pt[0]+m[4], m[3]*pt[1]+m[5], 850, y-7)
            book.text(855,y,name(owner,owners),13)
            for i, axis in enumerate('XYZ'):
                book.text(855,y-25-i*18,axis+'向成形：',10)
                book.label(owner,axis,dd[i],940,y-25-i*18,'formed',labels)
        book.text(45,55,'爆炸移位仅区分零件；未计入产品或零件尺寸，产品总外形见装配页。',11)
        book.end()
    else:
        book.start('爆炸图待补充')
        book.para(40,740,'缺少实际爆炸投影或逐件平移记录；不绘制推测分件图。成形尺寸见前页。',1100,15)
        book.end()
    book.cv.save()
