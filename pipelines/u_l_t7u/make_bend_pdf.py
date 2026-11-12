#!/usr/bin/env python3
"""S-201-0.8-20261030-004 bend PDF — skill 2.8.16 rule18:
三视+斜视；双向折弯尺寸；ERP关键栏醒目；去冗余。
Geometry from work_main only (no CAD rebuild). VER from release_config.
"""
import json, math, datetime, os, sys
from pathlib import Path
from zoneinfo import ZoneInfo
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.utils import ImageReader

ORDER = Path(os.environ['SM_ORDER'])
FONT = ORDER / 'logs' / 'cjk-sub.ttf'
if not FONT.exists():
    FONT = ORDER / 'work' / 'font' / 'NotoSansCJKsc_subset.ttf'
os.environ['V005_FONT'] = str(FONT)
sys.path.insert(0, str(ORDER / 'addendum-tools'))
import cfg
# force fresh font registration (pdf_common registers at import)
from reportlab.pdfbase import pdfmetrics as _pm
if 'NotoCJK' in _pm.getRegisteredFontNames():
    try:
        _pm._fonts.pop('NotoCJK', None)
        if hasattr(_pm, 'getFont'):
            pass
    except Exception:
        pass
import pdf_common as PC
from bidir import bidir, table_rows, f3

VER = cfg.VER
# always re-register from our subset
pdfmetrics.registerFont(TTFont('NotoCJK', str(FONT)))
PC.F = 'NotoCJK'
PC.FONT_TTF = str(FONT)
PC.VER = VER

PW, PH = PC.PW, PC.PH
NAVY, RED, DIMC, GRN, GREY = PC.NAVY, PC.RED, PC.DIMC, PC.GRN, PC.GREY
FILL_U = (0.92, 0.82, 0.65)
FILL_L = (0.90, 0.88, 0.70)
FILL_LID = (0.75, 0.92, 0.78)
FILL_H = (0.95, 0.90, 0.75)
BRN = (0.55, 0.42, 0.28)

rep = json.loads((ORDER / 'work_main' / 'E_main_report.json').read_text())
VW = json.loads((ORDER / 'work_main' / 'views_E.json').read_text())
P = rep['params']
L, W, H, t, Ri, g, q, skirt, K = P['L'], P['W'], P['H'], P['t'], P['Ri'], P['g'], P['q'], P['skirt'], P['K_ANSI']
ha = rep.get('handle_assembly') or {}
HH = ha.get('hole_coords_xy') or rep['lid']['handle_holes']
CABLE = rep['lid']['roof_holes_16']
HC = ha.get('centre_xy') or [L / 2, W / 2]
TOTAL_H = ha.get('total_height_with_handle', 341.2)
STACK = ha.get('stack_mm', 16.2)

NOW = datetime.datetime.now(ZoneInfo('Asia/Shanghai'))
STAMP = NOW.strftime('%Y-%m-%d %H:%M') + ' Asia/Shanghai'
OUTDIR = ORDER / 'named_release' / VER
OUTDIR.mkdir(parents=True, exist_ok=True)
PDF_PATH = OUTDIR / f'{VER}_BEND_PDF_A3_CN.pdf'

# ERP-critical red bar (rule18): t / L×W×H / VER / date / material — one glance
MAT = cfg.MATERIAL_CN
HEAD = (f'材料 {MAT}｜板厚 t={t:g} mm｜外形 {f3(L)}×{f3(W)}×{f3(H)}｜'
        f'编号 {VER}｜出图 {STAMP}｜确认稿 production_release=false')

BU = bidir(rep, 'U')
BL = bidir(rep, 'L')
BLID = bidir(rep, 'LID')
BD = {'U': BU, 'L': BL, 'LID': BLID}

ISO_PNG = {
    'ASSEMBLY': ORDER / 'post_out' / 'ASSEMBLY_iso.png',
    'U': None,  # drawn from HLR
    'L': None,
    'LID': ORDER / 'post_out' / 'LID_iso.png',
}


def parse_dxf(path):
    text = Path(path).read_text(encoding='latin-1', errors='replace').splitlines()
    ents = []; i = 0
    while i < len(text) - 1:
        if text[i].strip() == '0' and text[i + 1].strip() in ('LINE', 'ARC', 'CIRCLE'):
            typ = text[i + 1].strip(); d = {}; j = i + 2
            while j < len(text) - 1 and text[j].strip() != '0':
                try:
                    d[int(text[j])] = text[j + 1].strip()
                except Exception:
                    pass
                j += 2
            if typ == 'LINE':
                ents.append(('L', float(d[10]), float(d[20]), float(d[11]), float(d[21])))
            elif typ == 'CIRCLE':
                ents.append(('C', float(d[10]), float(d[20]), float(d[40])))
            elif typ == 'ARC':
                ents.append(('A', float(d[10]), float(d[20]), float(d[40]), float(d[50]), float(d[51])))
            i = j; continue
        i += 1
    return ents


def chain(pg, pts, vals, off, src, vertical=False, size=9.5, step=14, labels=None):
    sg = 1 if off > 0 else -1
    lens = [abs((b[1] - a[1]) if vertical else (b[0] - a[0])) for a, b in zip(pts, pts[1:])]
    txt = [(labels[i] if labels else f3(v)) for i, v in enumerate(vals)]
    tight = any(PC.sw(t_, size) + 6 > l for t_, l in zip(txt, lens))
    for i, (a, b) in enumerate(zip(pts, pts[1:])):
        o = off + (sg * step if (tight and i % 2) else 0)
        pg.dim(a, b, o, vals[i], src, vertical=vertical, size=size, label=txt[i])


def draw_flat(pg, ents, ox, oy, sc, stroke=(0.1, 0.1, 0.1)):
    xs, ys = [], []
    for e in ents:
        if e[0] == 'L':
            xs += [e[1], e[3]]; ys += [e[2], e[4]]
        elif e[0] in ('C', 'A'):
            xs += [e[1] - e[3], e[1] + e[3]]; ys += [e[2] - e[3], e[2] + e[3]]
    if not xs:
        return None
    xmin, ymin = min(xs), min(ys)

    def m(x, y):
        return (ox + (x - xmin) * sc, oy + (y - ymin) * sc)

    for e in ents:
        if e[0] == 'L':
            pg.line(m(e[1], e[2]), m(e[3], e[4]), 0.7, stroke)
        elif e[0] == 'C':
            cx, cy = m(e[1], e[2]); pg.circ((cx, cy), e[3] * sc, 0.7, stroke)
        elif e[0] == 'A':
            a0, a1 = math.radians(e[4]), math.radians(e[5])
            if a1 < a0:
                a1 += 2 * math.pi
            n = max(8, int((a1 - a0) / 0.15))
            pts = []
            for i in range(n + 1):
                a = a0 + (a1 - a0) * i / n
                pts.append(m(e[1] + e[3] * math.cos(a), e[2] + e[3] * math.sin(a)))
            for a, b in zip(pts, pts[1:]):
                pg.line(a, b, 0.7, stroke)
    return {'xmin': xmin, 'ymin': ymin, 'm': m,
            'w': (max(xs) - xmin) * sc, 'h': (max(ys) - ymin) * sc}


def ext(pols):
    xs = [q[0] for p in pols for q in p]
    ys = [q[1] for p in pols for q in p]
    return min(xs), min(ys), max(xs), max(ys)


def mapper(ox, oy, sc, u0, v0):
    return lambda p: (ox + sc * (p[0] - u0), oy + sc * (p[1] - v0))


def draw_hlr(pg, name, view, ox, oy, sc, u0, v0, lw=0.7, c=(0.1, 0.1, 0.1), hidden=False):
    V = VW[name][view]
    m = mapper(ox, oy, sc, u0, v0)
    for pol in V['visible']:
        if len(pol) < 2:
            continue
        for a, b in zip(pol, pol[1:]):
            pg.line(m(a), m(b), lw, c)
    if hidden and V.get('hidden'):
        for pol in V['hidden']:
            if len(pol) < 2:
                continue
            for a, b in zip(pol, pol[1:]):
                pg.line(m(a), m(b), 0.35, GREY, dash=(2, 2))
    return m


def threeview(pg, name, x, y, w, h, gap=36, labels=True):
    """GB first-angle: 主视(front) top-left, 左视(left) right, 俯视(top) below front."""
    V = VW[name]
    fr = ext(V['front']['visible']); le = ext(V['left']['visible']); tp = ext(V['top']['visible'])
    fw, fh = fr[2] - fr[0], fr[3] - fr[1]
    lw_, th = le[2] - le[0], tp[3] - tp[1]
    sc = min((w - 2 * gap - 20) / max(fw + lw_, 1), (h - 2 * gap - 30) / max(fh + th, 1))
    X0 = x + gap; Yt = y + h - gap - 16 - sc * fh
    mf = draw_hlr(pg, name, 'front', X0, Yt, sc, fr[0], fr[1])
    ml = draw_hlr(pg, name, 'left', X0 + sc * fw + gap * 0.7, Yt, sc, le[0], le[1])
    mt = draw_hlr(pg, name, 'top', X0, Yt - gap * 0.7 - sc * th, sc, tp[0], tp[1])
    if labels:
        pg.t(X0, Yt + sc * fh + 4, '主视（前）', 10, NAVY)
        pg.t(X0 + sc * fw + gap * 0.7, Yt + sc * fh + 4, '左视', 10, NAVY)
        pg.t(X0, Yt - gap * 0.7 - sc * th - 14, '俯视', 10, NAVY)
    return {'front': (mf, fr), 'left': (ml, le), 'top': (mt, tp), 'sc': sc,
            'X0': X0, 'Yt': Yt, 'fw': fw, 'fh': fh, 'lw': lw_, 'th': th}


def draw_iso_png(pg, path, x, y, w, h, title='斜视'):
    pg.frame(x, y, w, h, title)
    if not path or not Path(path).exists():
        pg.t(x + 10, y + h / 2, '(无斜视图)', 10, RED)
        return
    img = ImageReader(str(path))
    # fit inside frame with margin
    from PIL import Image
    im = Image.open(path); iw, ih = im.size
    top = 16; margin = 10
    sc = min((w - 2 * margin) / iw, (h - top - 2 * margin) / ih)
    dw, dh = iw * sc, ih * sc
    ox = x + (w - dw) / 2; oy = y + (h - top - dh) / 2
    pg.cv.drawImage(img, ox, oy, dw, dh, mask='auto')


def draw_iso_hlr(pg, name, x, y, w, h, title='斜视（成形）'):
    pg.frame(x, y, w, h, title)
    V = VW[name]['iso']['visible']
    e = ext(V)
    margin = 18; top = 16
    sc = min((w - 2 * margin) / max(e[2] - e[0], 1), (h - top - 2 * margin) / max(e[3] - e[1], 1))
    ox = x + margin + (w - 2 * margin - sc * (e[2] - e[0])) / 2
    oy = y + margin + (h - top - 2 * margin - sc * (e[3] - e[1])) / 2
    m = mapper(ox, oy, sc, e[0], e[1])
    for pol in V:
        if len(pol) < 2:
            continue
        for a, b in zip(pol, pol[1:]):
            pg.line(m(a), m(b), 0.55, (0.15, 0.15, 0.15))
    return m


class Book:
    def __init__(self, path, n_total=4):
        self.pg = PC.Pg(path, HEAD)
        self.pg.N = n_total
        self.path = path

    def head(self, title, part=None):
        """Navy + red ERP bar: t / size / VER / stamp / material all visible (rule18)."""
        p = self.pg
        cv = p.cv
        cv.setFillColorRGB(*NAVY); cv.rect(0, PH - 46, PW, 46, fill=1, stroke=0)
        p.t(24, PH - 30, title, 15, (1, 1, 1))
        p.t(PW - 24, PH - 18, f'出图 {STAMP}', 11, (1, 1, 1), 'r')
        p.t(PW - 24, PH - 34, VER, 12, (1, 1, 1), 'r')
        # taller red bar for ERP five fields
        cv.setFillColorRGB(*RED); cv.rect(0, PH - 86, PW, 40, fill=1, stroke=0)
        erp1 = f'材料 {MAT}　｜　板厚 t={t:g} mm　｜　外形 {f3(L)}×{f3(W)}×{f3(H)} mm'
        erp2 = f'工厂编号 {VER}　｜　出图 {STAMP}　｜　确认稿 production_release=false'
        if part:
            erp2 += f'　｜　本页 {part}'
        p.t(24, PH - 62, erp1, 12, (1, 1, 1))
        p.t(24, PH - 78, erp2, 11, (1, 1, 1))

    def foot(self):
        p = self.pg
        cv = p.cv
        cv.setStrokeColorRGB(*NAVY); cv.setLineWidth(0.8); cv.line(24, 30, PW - 24, 30)
        p.t(24, 14, '单位 mm；尺寸取自本版 STEP/DXF；按数值加工。确认稿：实物试折试装未进行；production_release=false。规则9双向+规则18三视斜视。', 9.4)
        p.t(PW - 24, 13, f'{VER}   {p.n + 1}/{p.N}', 11, anchor='r')
        cv.showPage(); p.n += 1

    def save(self):
        self.pg.cv.save()


def page_assembly(bk):
    pg = bk.pg
    bk.head(f'{VER} 总装：三视图 + 斜视图（绿盖褐箱）')
    # content below taller header (PH-86)
    top_y = PH - 100

    # --- three views frame (left) ---
    fx, fy, fw, fh = 24, 210, 620, top_y - 210
    pg.frame(fx, fy, fw, fh, '总装三视图（第一角；实测 ASSEMBLY.step）')
    tv = threeview(pg, 'ASSEMBLY', fx, fy, fw, fh - 8, gap=40)
    mf, fr = tv['front']; ml, le = tv['left']; mt, tp = tv['top']
    # overall dims on front/left
    pg.dim(mf((fr[0], fr[1])), mf((fr[2], fr[1])), -18, L, 'ASSEMBLY bbox X', label=f'{f3(L)}')
    pg.dim(mf((fr[2], fr[1])), mf((fr[2], fr[3])), 14, H, 'ASSEMBLY bbox Z', vertical=True, label=f'{f3(H)}含盖')
    pg.dim(ml((le[0], le[1])), ml((le[2], le[1])), -18, W, 'ASSEMBLY bbox Y', label=f'{f3(W)}')

    # --- iso (right top) green lid / brown box PNG ---
    ix, iy, iw, ih = 660, 430, 500, top_y - 430
    draw_iso_png(pg, ISO_PNG['ASSEMBLY'], ix, iy, iw, ih, title='总装斜视（绿盖+褐箱；实测 STEP）')
    pg.t(ix + 8, iy + 8, f'外形 {f3(L)}×{f3(W)}×{f3(H)}｜加提手≈{f3(TOTAL_H)}', 9.5, DIMC)

    # --- short HOLD/WARN (right mid, compressed) ---
    pg.t(660, 410, 'HOLD / WARN（短）', 12, NAVY)
    holds = [
        ('HOLD', '双线孔 Φ16×2 候选坐标/孔径待确认'),
        ('HOLD', '把手型号/承重（用户STEP仅装配参考）'),
        ('HOLD', '盖外缘用户约184×164 vs skill flush'),
        ('WARN', f'M4攻丝 t={t:g} 薄板约1扣，易滑牙'),
        ('WARN', f'Ri={Ri:g}/K={K:g} 经验未标定'),
        ('INFO', '实物试折试装未进行｜不投产'),
    ]
    y = 390
    for tag, s in holds:
        col = RED if tag in ('HOLD', 'WARN') else (0.2, 0.2, 0.2)
        pg.t(668, y, f'{tag} {s}', 9.5, col); y -= 15

    # --- parts table bottom ---
    pg.t(24, 190, '零件表（1套）', 12, NAVY)
    cols = [('零件', 70), ('说明', 200), ('成形约', 150), ('展开约', 150), ('数量', 40)]
    rows = [
        ['U', '围板（侧-底-侧）', f'{f3(L)}×{f3(W)}×{f3(H - t - q)}', f'{f3(BU["flat"][0])}×{f3(BU["flat"][1])}', '1'],
        ['L', 'L型底板（盖U齐平）', f'{f3(L)}×{f3(W)}×{f3(H - t - q)}', f'{f3(BL["flat"][0])}×{f3(BL["flat"][1])}', '1'],
        ['LID', '盖+把手孔+线孔候选', f'{f3(L + 2 * (g + t))}×{f3(W + 2 * (g + t))}×裙{f3(skirt)}', f'{f3(BLID["flat"][0])}×{f3(BLID["flat"][1])}', '1'],
        ['HANDLE', '用户STEP装配参考', f'堆叠≈{f3(STACK)}', '—', '1'],
    ]
    yy = 170
    pg.box(24, yy - 16, 610, 16, fill=(0.88, 0.92, 1))
    x = 24
    for h, ww in cols:
        pg.t(x + 3, yy - 12, h, 9.4); x += ww
    for r in rows:
        yy -= 16; pg.box(24, yy - 16, 610, 16, fill=(1, 1, 1), lw=0.3)
        x = 24
        for (h, ww), v in zip(cols, r):
            pg.t(x + 3, yy - 12, v, 9.4); x += ww

    pg.t(650, 170, f'结构 u_wrap_bottom_l｜裙{f3(skirt)} g={f3(g)} q={f3(q)}', 9.5, NAVY)
    pg.t(650, 154, f'把手居中({f3(HC[0])},{f3(HC[1])}) 4×Φ6.6｜NEST一盒一文件', 9.5)
    pg.t(650, 138, 'DXF：CUT无折弯线；BEND红实线+双向尺寸', 9.5)
    bk.foot()


def page_part(bk, name, title_cn, fill):
    pg = bk.pg
    bk.head(f'{VER} {title_cn}（{name}）— 展开双向尺寸 + 成形斜视', part=name)
    part = rep['parts'][name]
    flat = part.get('flat_size') or [0, 0]
    fw, fh = flat[0], flat[1]
    B = BD[name]
    ents = parse_dxf(ORDER / 'work_main' / f'{name}.dxf')

    # left: unfold with bidir dims
    sc = min(420 / max(fw, 1), 280 / max(fh, 1), 1.1)
    ox, oy = 80, 280
    info = draw_flat(pg, ents, ox, oy, sc, stroke=(0.15, 0.15, 0.15))
    pg.t(40, PH - 105, f'{name} 展开（规则9双向）｜外形 {f3(fw)}×{f3(fh)}｜t={f3(t)} Ri={f3(Ri)} K={f3(K)}', 11, NAVY)

    if info:
        m = info['m']; xmin, ymin = info['xmin'], info['ymin']
        pg.dim(m(xmin, ymin), m(xmin + fw, ymin), -28, fw, f'{name}.dxf', label=f'总长 {f3(fw)}')
        pg.dim(m(xmin, ymin), m(xmin, ymin + fh), -28, fh, f'{name}.dxf', vertical=True, label=f'总宽 {f3(fh)}')

        xs = [0.0] + [d['pos'] for d in B['X']] + [fw]
        if len(xs) > 2:
            pts = [m(xmin + x, ymin) for x in xs]
            vals = [xs[i + 1] - xs[i] for i in range(len(xs) - 1)]
            chain(pg, pts, vals, -14, f'{name} X segs', vertical=False, size=9.4)
        ys = [0.0] + [d['pos'] for d in B['Y']] + [fh]
        if len(ys) > 2:
            pts = [m(xmin, ymin + y) for y in ys]
            vals = [ys[i + 1] - ys[i] for i in range(len(ys) - 1)]
            chain(pg, pts, vals, -14, f'{name} Y segs', vertical=True, size=9.4)

        for d in B['X']:
            x = d['pos']; sp0, sp1 = d.get('span', (0, fh))
            a = m(xmin + x, ymin + sp0); b = m(xmin + x, ymin + sp1)
            pg.line(a, b, 1.3, RED)
            pg.t((a[0] + b[0]) / 2 + 5, (a[1] + b[1]) / 2, d['id'], 9, RED)
            pg.dim(m(xmin, ymin + fh), m(xmin + x, ymin + fh), 12, d['a'], f'{name} {d["id"]} dA',
                   size=8.5, label=f"{d['id']} 距A={f3(d['a'])}")
            pg.dim(m(xmin + x, ymin + fh), m(xmin + fw, ymin + fh), 26, d['b'], f'{name} {d["id"]} dB',
                   size=8.5, label=f"距B={f3(d['b'])}")

        for d in B['Y']:
            y = d['pos']; sp0, sp1 = d.get('span', (0, fw))
            a = m(xmin + sp0, ymin + y); b = m(xmin + sp1, ymin + y)
            pg.line(a, b, 1.3, RED)
            pg.t((a[0] + b[0]) / 2, (a[1] + b[1]) / 2 + 6, d['id'], 9, RED)
            pg.dim(m(xmin + fw, ymin), m(xmin + fw, ymin + y), 16, d['a'], f'{name} {d["id"]} dA',
                   vertical=True, size=8.5, label=f"{d['id']} 距A={f3(d['a'])}")
            pg.dim(m(xmin + fw, ymin + y), m(xmin + fw, ymin + fh), 32, d['b'], f'{name} {d["id"]} dB',
                   vertical=True, size=8.5, label=f"距B={f3(d['b'])}")

    # right: formed iso (small) + hole table + bend table
    iso_path = ISO_PNG.get(name)
    if iso_path and Path(iso_path).exists():
        draw_iso_png(pg, iso_path, 640, 520, 320, 200, title=f'{name} 成形斜视')
    else:
        draw_iso_hlr(pg, name, 640, 520, 320, 200, title=f'{name} 成形斜视（HLR）')

    circles = [(e[1], e[2], 2 * e[3]) for e in ents if e[0] == 'C']
    pg.t(640, 500, f'{name} 孔表', 11, NAVY)
    yy = 478
    pg.box(640, yy, 310, 16, fill=(0.88, 0.92, 1))
    pg.t(643, yy + 3, '序', 9); pg.t(670, yy + 3, 'Φ', 9)
    pg.t(710, yy + 3, '中心X', 9); pg.t(770, yy + 3, '中心Y', 9); pg.t(830, yy + 3, '说明', 9)
    for i, (cx, cy, d) in enumerate(sorted(circles, key=lambda q: (round(q[2], 2), q[0], q[1])), 1):
        yy -= 14
        note = ''
        if abs(d - 6.6) < 0.05:
            note = '把手M6过孔'
        elif abs(d - 16) < 0.05:
            note = '线孔HOLD'
        elif abs(d - 4.5) < 0.05:
            note = '裙M4过孔'
        elif abs(d - 3.3) < 0.05:
            note = '体M4底孔'
        pg.box(640, yy, 310, 14, fill=(1, 1, 1), lw=0.3)
        pg.t(643, yy + 2, str(i), 9); pg.t(670, yy + 2, f3(d), 9)
        pg.t(710, yy + 2, f3(cx), 9); pg.t(770, yy + 2, f3(cy), 9)
        pg.t(830, yy + 2, note, 8.5, RED if 'HOLD' in note else (0, 0, 0))
        if yy < 300:
            break

    pg.t(640, min(yy - 16, 280), f'{name} 折弯表（距A/距B/段长）', 11, NAVY)
    bcols = [('弯号', 40), ('轴', 28), ('距A边', 55), ('距B边', 55), ('段(前)', 100), ('段(后)', 100)]
    brows = []
    for r in table_rows(B, name):
        brows.append([r['id'], r['axis'], r['a'], r['b'], r['seg_prev'], r['seg_next']])
    if not brows:
        brows = [['—', '—', '—', '—', '无折弯', '—']]
    ty = min(yy - 34, 260)
    pg.table(640, ty, bcols, brows, size=8.5, rh=13, title=None)

    dir_notes = []
    for d in B['X'] + B['Y']:
        ang = abs(float(d.get('ang') or 90))
        direc = '上折' if (d.get('dir') or '').upper() == 'UP' else '下折'
        dir_notes.append(f"{d['id']} {direc} {f3(ang)}° R{f3(d.get('R') or Ri)}")
    ynotes = ty - 16 - 13 * len(brows)
    for s in dir_notes:
        pg.t(640, ynotes, s, 9, RED); ynotes -= 12

    pg.t(40, 70, '规则9：边→折/折→折/折→边 + 每折距A/距B；折弯表同值。师傅免心算。', 9.5, DIMC)
    if name == 'LID':
        pg.t(40, 54, f'把手4×Φ6.6 {HH}｜线孔2×Φ16候选 HOLD｜盖外缘≈{f3(L + 2 * (g + t))}×{f3(W + 2 * (g + t))}', 9.5, RED)
    bk.foot()


def main():
    PC.LOG.clear()
    tmp = ORDER / 'logs' / f'{VER}_bend_pdf_build.pdf'
    bk = Book(tmp, 4)
    page_assembly(bk)
    page_part(bk, 'U', 'U型围板', FILL_U)
    page_part(bk, 'L', 'L型底板', FILL_L)
    page_part(bk, 'LID', '盖板（含把手孔/线孔）', FILL_LID)
    bk.save()
    PDF_PATH.write_bytes(tmp.read_bytes())
    alias = OUTDIR / f'{VER}_完整折弯工艺PDF_折弯师傅作业图_4页.pdf'
    alias.write_bytes(tmp.read_bytes())
    sources = {
        'ver': VER, 'stamp': STAMP, 'production_release': False,
        'rule': '2.8.16-rule18',
        'bidir': {k: {'flat': list(v['flat']),
                      'X': [{kk: vv for kk, vv in d.items() if kk != 'span'} for d in v['X']],
                      'Y': [{kk: vv for kk, vv in d.items() if kk != 'span'} for d in v['Y']],
                      'X_seg': v['X_seg'], 'Y_seg': v['Y_seg']} for k, v in BD.items()},
        'pdf_log': PC.LOG,
        'handle_holes': HH, 'cable_candidates': CABLE,
    }
    (ORDER / 'logs' / 'bend_pdf_dimension_sources.json').write_text(json.dumps(sources, indent=2, ensure_ascii=False))
    meta = {
        'ver': VER, 'pdf': str(PDF_PATH), 'pages': 4, 'stamp': STAMP,
        'production_release': False, 'handle_holes': HH, 'cable_candidates': CABLE,
        'total_height_with_handle': TOTAL_H,
        'rev': 'v2_rule18',
        'dims_logged': len(PC.LOG),
    }
    (ORDER / 'logs' / 'bend_pdf_meta.json').write_text(json.dumps(meta, indent=2, ensure_ascii=False))
    print(json.dumps(meta, ensure_ascii=False))


if __name__ == '__main__':
    main()
