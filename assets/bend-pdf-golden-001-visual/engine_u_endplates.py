import sys, json, math, datetime, hashlib, numpy as np, matplotlib, os
from pathlib import Path
# Order tools (cfg) + golden bidir
ORDER = Path(os.environ.get('SM_ORDER') or Path(sys.argv[1]).resolve().parent if len(sys.argv) > 1 else '.')
# When called as make_bend_pdf WORK STAGE, WORK's parent is order root
if len(sys.argv) >= 3:
    ORDER = Path(sys.argv[1]).resolve().parent
sys.path.insert(0, str(ORDER / 'tools'))
sys.path.insert(0, str(Path(__file__).resolve().parent))  # golden bidir/views
from cfg import *
from bidir import bidir, table_rows, EDGE_CN
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from matplotlib import font_manager as fm
from matplotlib.patches import Rectangle, Circle, FancyBboxPatch, FancyArrowPatch
from matplotlib.collections import PolyCollection
from matplotlib.text import Text
matplotlib.rcParams['pdf.fonttype'] = 42
FPATH = os.environ.get('SM_CJK_FONT', '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc')
if not os.path.isfile(FPATH):
    for _alt in ('/System/Library/Fonts/STHeiti Medium.ttc',
                 '/usr/share/fonts/truetype/wqy/wqy-microhei.ttc'):
        if os.path.isfile(_alt):
            FPATH = _alt
            break
fm.fontManager.addfont(FPATH)
FP = fm.FontProperties(fname=FPATH)
matplotlib.rcParams['font.family'] = FP.get_name()
matplotlib.rcParams['axes.unicode_minus'] = False

W_ = Path(sys.argv[1]); R = Path(sys.argv[2])
rep = json.load(open(W_ / 'report.json'))
proj = json.load(open(W_ / 'projections.json'))
mesh = json.load(open(W_ / 'mesh.json'))
flats = json.load(open(W_ / 'flats.json'))
sec = json.load(open(W_ / 'section_mid.json'))
dchk = json.load(open(W_ / 'dxf_checks.json'))
P = rep['parts']; G = rep['gap_check']
EF = (JOB or {}).get('end_features') or rep.get('end_features') or {}
_END_CIRCLES = list(EF.get('circles') or rep.get('end_holes') or [])
_END_RECTS = list(EF.get('rects') or rep.get('end_rects') or [])
EF_PART = EF.get('part') or 'END_R'
# Dynamic captions from JOB (fix v1 engine; avoid frozen 009-order hardcodes)
_END_HOLES = [dict(c) for c in _END_CIRCLES]
_END_HOLE_TXT = ('/'.join(f"{h.get('id','')}Ø{float(h['d']):g}@(Y{float(h['y']):g},Z{float(h['z']):g})" for h in _END_HOLES) if _END_HOLES else '端板无功能孔')
_centers = [h for h in _END_HOLES if float(h.get('d',0)) >= 10]
_sats = [h for h in _END_HOLES if float(h.get('d',0)) < 10]
_LID_HOLE_TXT = ('/'.join(f"{h['id']}Ø{h['d']:g}@({h['x']:g},{h['y']:g})" for h in LID_HOLES) if LID_HOLES else '盖顶无功能孔')
_FEAT_TOP = (('盖顶孔 '+_LID_HOLE_TXT) if LID_HOLES else '盖顶无功能孔')
_HDL_LINE = (('两端板把手握把朝上' if HANDLE_MOUNT == 'END_L+END_R' else ('END_R把手握把朝上' if HANDLE_MOUNT == 'END_R' else ('END_L把手握把朝上' if HANDLE_MOUNT == 'END_L' else (f'盖顶把手×{len(HANDLE_CX)}' if HANDLE_CX else '不要把手/无把手孔')))))
_PANEL = JOB.get('panel_holes') or []
_RECTS = JOB.get('rect_cutouts') or []

def panel_handle_row_note(holes):
    rows = []
    for z in sorted({h['point'][2] for h in holes}):
        ys = [h['point'][1] for h in holes if h['point'][2] == z]
        rows.append((max(ys)-min(ys), z))
    (narrow, nz), (wide, wz) = sorted(rows)
    return f'宽排{wide:g} Z{wz:g}{"在上" if wz>nz else "在下"}；窄排{narrow:g} Z{nz:g}{"在下" if wz>nz else "在上"}'

_PANEL_HANDLES = [h for h in _PANEL if h.get('purpose') == 'handle']
if _PANEL_HANDLES:
    _HDL_LINE = '两端板居中；85/62/30；朝向见端板图'
# flange summary for this dual Φ16.5+4×Φ4.5 pattern (or generic)
if _centers and _sats and abs(float(_centers[0]['d'])-16.5)<0.1 and abs(float(_sats[0]['d'])-4.5)<0.1:
    _ys = sorted({float(c['y']) for c in _centers})
    _zc = float(_centers[0]['z'])
    _END_SUMMARY = f"END_R：{len(_centers)}×(Φ16.5+4×Φ4.5@20×20) Y={'/'.join(f'{y:g}' for y in _ys)} Zc={_zc:g}；END_L仅M4"
else:
    _END_SUMMARY = (('END功能孔：'+_END_HOLE_TXT) if _END_HOLES else 'END_L/END_R：无功能孔') + '；对端仅M4'
# skirt clearance from group top (center+mount envelope)
_skirt_z = H - skirt
_group_top = max((float(h['z']) + float(h['d'])/2 for h in _END_HOLES), default=_skirt_z)
_skirt_clear = _skirt_z - _group_top
_SKIRT_NOTE = (f'孔组裙净空{_skirt_clear:.1f} WARN（<10）' if 0 <= _skirt_clear < 10 else (f'孔组裙净空{_skirt_clear:.1f} PASS' if _skirt_clear >= 10 else f'孔组裙净空{_skirt_clear:.1f} ERROR遮挡'))
if not _END_HOLES:
    _SKIRT_NOTE = '端板无功能孔，无盖裙遮挡项'
if _PANEL:
    _END_SUMMARY = f'侧壁功能圆孔{sum(h["part_id"]=="U" for h in _PANEL)}；端板把手孔{len(_PANEL_HANDLES)}；详见附页'
    _tops = [h['point'][2]+h['diameter']/2 for h in _PANEL]
    _tops += [h['center'][2]+h['size_xy'][1]/2 for h in _RECTS]
    _SKIRT_NOTE = f'功能孔至盖裙净空 {H-skirt-max(_tops):g} mm'
_SIDE_TITLE = (f'侧视图 {EF_PART}（端板功能孔；ASSEMBLY 沿X投影）' if _END_HOLES else f'侧视图（外封端板侧）')
_TOP_CAPTION = f'盖顶功能孔 {len(LID_HOLES)} 个，坐标/孔径见第4页孔表'
_TOP_EXTRA = '孔位见第4页；盖-体固定 M4'

Hb = H - t - q
PW, PH = 420, 297  # A3 mm landscape via figsize
NAVY = (0.10, 0.22, 0.45); REDC = (0.82, 0.10, 0.10); DIMC = (0.0, 0.20, 0.65)
GRN = (0.20, 0.55, 0.30); TAN = (0.55, 0.40, 0.20)
RED = '#c00000'; BLU = '#0040a0'

# --- Harry t59u/t60u visual language (ref S-201-1-20261031-001-v1) ---
# reportlab gold uses MINPT=9.4 (~3.3 mm on A3). Matplotlib path must match.
# Crowding OK; do NOT shrink text to force 4 pages — split pages instead (rule6 / t124u).
MINPT = 9.4
FS_DIM = 9.5
FS_NOTE = 9.4
FS_TITLE = 10.5
FS_BOX = 9.4
FS_HEADER_TITLE = 13.0
FS_HEADER_META = 9.4
FS_FOOT = 9.4
NPAGES = 5  # ASSEMBLY / U / END / LID / Checks  (may grow; never hard-cap at 4)
if _PANEL:
    NPAGES += 2

def _fs(x):
    try:
        return max(float(x), MINPT)
    except Exception:
        return MINPT

# --- dim text bbox avoid (matplotlib data-space; v2.8.27) ---
_OV = {'attempted': 0, 'resolved_by_nudge': 0, 'resolved_by_flip': 0, 'remaining': 0, 'events': []}
_BB = []  # (ax_id, xmin, ymin, xmax, ymax)

def _ax_id(ax):
    return id(ax)

def _tb(ax, x, y, txt, fs, rot=0, ha='center', va='bottom'):
    # approximate data-space text box using ax.s (page-mm per data-mm) when present
    s = getattr(ax, 's', 1.0) or 1.0
    # char width ~0.55*fs pt; 1 pt ≈ 0.3528 mm page; data = page_mm / s
    w_mm = max(len(str(txt)), 1) * fs * 0.55 * 0.3528
    h_mm = fs * 1.2 * 0.3528
    w = w_mm / s; h = h_mm / s
    if abs(rot) == 90:
        w, h = h, w
    if ha == 'center':
        x0, x1 = x - w/2, x + w/2
    elif ha == 'right':
        x0, x1 = x - w, x
    else:
        x0, x1 = x, x + w
    if va in ('bottom', 'baseline'):
        y0, y1 = y, y + h
    elif va == 'top':
        y0, y1 = y - h, y
    else:
        y0, y1 = y - h/2, y + h/2
    pad = 0.8 / s
    return (x0 - pad, y0 - pad, x1 + pad, y1 + pad)

def _hit(ax, bb):
    aid = _ax_id(ax)
    for o in _BB:
        if o[0] != aid: continue
        if not (bb[2] <= o[1] or o[3] <= bb[0] or bb[3] <= o[2] or o[4] <= bb[1]):
            return True
    return False

def _place(ax, x, y, txt, fs, rot=0, ha='center', va='bottom', lane=(0, 1), step=None):
    _OV['attempted'] += 1
    s = getattr(ax, 's', 1.0) or 1.0
    step = step if step is not None else (3.5 / s)
    bb0 = _tb(ax, x, y, txt, fs, rot, ha, va)
    if not _hit(ax, bb0):
        _BB.append((_ax_id(ax), *bb0)); return x, y, False
    dx, dy = lane
    for i in range(1, 7):
        xx, yy = x + dx * step * i, y + dy * step * i
        bb = _tb(ax, xx, yy, txt, fs, rot, ha, va)
        if not _hit(ax, bb):
            _OV['resolved_by_nudge'] += 1
            _OV['events'].append({'text': str(txt), 'how': 'nudge', 'steps': i})
            _BB.append((_ax_id(ax), *bb)); return xx, yy, False
    for i in range(1, 7):
        xx, yy = x - dx * step * i, y - dy * step * i
        bb = _tb(ax, xx, yy, txt, fs, rot, ha, va)
        if not _hit(ax, bb):
            _OV['resolved_by_flip'] += 1
            _OV['events'].append({'text': str(txt), 'how': 'flip', 'steps': i})
            _BB.append((_ax_id(ax), *bb)); return xx, yy, True
    _OV['remaining'] += 1
    _OV['events'].append({'text': str(txt), 'how': 'remain'})
    _BB.append((_ax_id(ax), *bb0)); return x, y, False


_PDF_STAMP = datetime.datetime.now().strftime('%Y-%m-%d %H:%M') + ' Asia/Shanghai'

def header(ax, n):
    stamp = _PDF_STAMP
    _pr = bool((JOB or {}).get('production_release', False))
    ax.add_patch(Rectangle((0, PH - 18), PW, 18, fc=NAVY, ec='none'))
    ax.text(8, PH - 12, f'{VER}  钣金折弯工艺' + ('生产图纸（投产包）' if _pr else '确认稿（非生产放行）'), color='w', fontsize=_fs(FS_HEADER_TITLE), weight='bold', va='center')
    ax.text(PW - 70, PH - 12, f'出图 {stamp}', color='w', fontsize=_fs(FS_HEADER_META), ha='right', va='center')
    ax.text(PW - 8, PH - 12, f'{n}/{NPAGES}', color='w', fontsize=_fs(12), ha='right', va='center')
    # taller ERP red bar: material / t / LWH / VER / date (rule18)
    ax.add_patch(Rectangle((0, PH - 34), PW, 16, fc=REDC, ec='none'))
    ax.text(8, PH - 22, f'材料 {MATERIAL_CN}｜板厚 t={t:g} mm｜外形 {OUTER_L:g}×{OUTER_W:g}×{H:g}（含盖不含把手）｜内R{ri:g} K={K:.4f} BD={BD:.3f}(候选)｜每套{len(P)}件｜production_release={str(_pr).lower()}',
            color='w', fontsize=_fs(FS_HEADER_META), va='center')
    ax.text(8, PH - 31, f'工厂编号 {VER}｜出图 {stamp}｜用户外形口径｜公差 +0/−2｜金样引擎 engine_u_endplates 2.8.45｜视觉参考001-v1｜可>4页',
            color='w', fontsize=_fs(FS_HEADER_META), va='center')
    ax.set_xlim(0, PW); ax.set_ylim(0, PH); ax.axis('off')

def foot(ax):
    ax.plot([8, PW - 8], [12, 12], color=NAVY, lw=0.8)
    ax.text(8, 5, '单位 mm；尺寸取自本版 STEP/DXF/孔表。投产包：实物试折试装未进行；首件须确认。', fontsize=_fs(FS_FOOT))
    ax.text(PW - 8, 5, VER, fontsize=_fs(FS_FOOT), ha='right')

def vax(fig, x, y, xlim, ylim, s, title, tfs=None, axis_off=True):
    # x,y in mm on page; s = page-mm per data-mm → axes width
    w = (xlim[1] - xlim[0]) * s; h = (ylim[1] - ylim[0]) * s
    ax = fig.add_axes([x / PW, y / PH, w / PW, h / PH])
    ax.set_xlim(*xlim); ax.set_ylim(*ylim); ax.set_aspect('equal'); ax.s = s
    if tfs is None:
        tfs = FS_TITLE
    tfs = _fs(tfs)
    if axis_off:
        ax.axis('off')
    else:
        ax.tick_params(labelsize=_fs(7))
    ax.set_title('\n'.join(wrap_text(ax, title, tfs, xlim[1] - xlim[0])), fontsize=tfs, loc='left')
    return ax

def dimh(ax, x1, x2, y, ya, yb, txt, fs=None, c=DIMC):
    # ya/yb = extension-line roots; label uses lane avoid (v2.8.27)
    fs = _fs(FS_DIM if fs is None else fs)
    if getattr(ax, 's', None):
        o = 1.0 / ax.s
        tx0 = (x1 + x2) / 2
        ty0 = y + 0.5 / ax.s
        sg = 1 if y >= max(ya, yb) else -1
        tx, ty, flipped = _place(ax, tx0, ty0, txt, fs, rot=0, ha='center', va='bottom', lane=(0, sg))
        if flipped:
            # mirror dim line to opposite side of roots
            mid = (ya + yb) / 2 if False else (min(ya, yb) + max(ya, yb)) / 2
            y = mid - (y - mid)
            ty = y - 0.5 / ax.s
            sg = -sg
        elif abs(ty - ty0) > 1e-9:
            y = ty - 0.5 / ax.s
        for x, yr in ((x1, ya), (x2, yb)):
            ax.plot([x, x], [yr, y + (o if y > yr else -o)], color=c, lw=0.35, clip_on=False)
        ax.annotate('', xy=(x1, y), xytext=(x2, y),
                    annotation_clip=False, arrowprops=dict(arrowstyle='<|-|>', lw=0.55, color=c, mutation_scale=7, shrinkA=0, shrinkB=0))
        ax.text(tx, ty, txt, fontsize=fs, ha='center', va='bottom', color=c)
    else:
        ax.annotate('', xy=(x1, ya), xytext=(x2, yb), arrowprops=dict(arrowstyle='<->', color=c, lw=0.6))
        ax.text((x1 + x2) / 2, y, txt, fontsize=fs, ha='center', color=c)

def dimv(ax, y1, y2, x, xa, xb, txt, fs=None, c=DIMC):
    fs = _fs(FS_DIM if fs is None else fs)
    if getattr(ax, 's', None):
        o = 1.0 / ax.s
        tx0 = x - 0.5 / ax.s
        ty0 = (y1 + y2) / 2
        sg = 1 if x >= max(xa, xb) else -1
        tx, ty, flipped = _place(ax, tx0, ty0, txt, fs, rot=90, ha='right', va='center', lane=(sg, 0))
        if flipped:
            mid = (min(xa, xb) + max(xa, xb)) / 2
            x = mid - (x - mid)
            tx = x + 0.5 / ax.s
            sg = -sg
        elif abs(tx - tx0) > 1e-9:
            x = tx + 0.5 / ax.s
        for y, xr in ((y1, xa), (y2, xb)):
            ax.plot([xr, x + (o if x > xr else -o)], [y, y], color=c, lw=0.35, clip_on=False)
        ax.annotate('', xy=(x, y1), xytext=(x, y2),
                    annotation_clip=False, arrowprops=dict(arrowstyle='<|-|>', lw=0.55, color=c, mutation_scale=7, shrinkA=0, shrinkB=0))
        ax.text(tx, ty, txt, fontsize=fs, ha='right', va='center', rotation=90, color=c)
    else:
        ax.annotate('', xy=(xa, y1), xytext=(xb, y2), arrowprops=dict(arrowstyle='<->', color=c, lw=0.6))
        ax.text(x, (y1 + y2) / 2, txt, fontsize=fs, va='center', color=c)

def bilateral_dims(ax, dimensions):
    fx, fy = dimensions['flat']
    for i, bend in enumerate(dimensions['X']):
        dimh(ax, 0, bend['pos'], -(12+12*i)/ax.s, 0, 0, f'{bend["a"]:.2f}')
        dimh(ax, bend['pos'], fx, -(18+12*i)/ax.s, 0, 0, f'{bend["b"]:.2f}')
    for i, bend in enumerate(dimensions['Y']):
        dimv(ax, 0, bend['pos'], -(12+7*i)/ax.s, 0, 0, f'{bend["a"]:.2f}')
        dimv(ax, bend['pos'], fy, fx+(12+7*i)/ax.s, fx, fx, f'{bend["b"]:.2f}')


def _pl_proj(ax, poly, fn, **k):
    a = np.array([fn(p[0], p[1]) for p in poly])
    ax.plot(a[:, 0], a[:, 1], **k)

def view(ax, name, v, fn, lw=0.7, hidden=True):
    for poly in proj[name][v]['vis']:
        _pl_proj(ax, poly, fn, color='k', lw=lw)
    if hidden:
        for poly in proj[name][v]['hid']:
            _pl_proj(ax, poly, fn, color='0.55', lw=0.3, ls=(0, (3, 2)))

def wrap_text(ax, text, fs, width):
    renderer = ax.figure.canvas.get_renderer()
    px = ax.transData.transform((width, 0))[0] - ax.transData.transform((0, 0))[0]
    probe = ax.text(0, 0, '', fontsize=fs, parse_math=False)
    rows = []
    for paragraph in str(text).split('\n'):
        row = ''
        for ch in paragraph:
            probe.set_text(row + ch)
            if row and probe.get_window_extent(renderer).width > px:
                rows.append(row); row = ''
            row += ch
        rows.append(row)
    probe.remove()
    return rows


def box(ax, x, y, w, h, lines, title=None, fs=None, ec=NAVY):
    fs = _fs(FS_BOX if fs is None else fs)
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle='round,pad=1', fc='#f7f9fc', ec=ec, lw=0.8))
    yy = y + h - 4
    if title:
        ax.text(x + 3, yy, title, fontsize=fs + 0.5, weight='bold', color=ec, va='top'); yy -= 9
    for ln in lines:
        txt, color = ln if isinstance(ln, tuple) else (ln, 'black')
        for row in wrap_text(ax, txt, fs, w - 6):
            if yy - fs * 0.3528 * 1.3 < y + 2:
                raise ValueError(f'PDF_LAYOUT: text exceeds box {title!r}; split page')
            ax.text(x + 3, yy, row, fontsize=fs, color=color, va='top', parse_math=False)
            yy -= fs * 0.3528 * 1.3 + 1.7


def customer_requirement_pages(ax, job):
    sections = [('客户原始需求（原文）', job.get('customer_requirement_text') or
                 '未提供客户原始需求；本次为历史数据重绘，需补录客户原文。')]
    sections += [(f'后续确认 / 修改原文 {i}', text)
                 for i, text in enumerate(job.get('customer_requirement_updates') or [], 1)]
    rows = [('以下保留客户原话及原单位；实际采用参数、待确认项见本版图纸。', NAVY)]
    for title, text in sections:
        rows.append((title, REDC))
        printable = text.replace('\r\n', '\n').replace('\r', '\n').expandtabs(4)
        rows += [(line, 'black') for line in wrap_text(ax, printable, FS_NOTE, 390)]
    return [rows[i:i+30] for i in range(0, len(rows), 30)]


def draw_customer_requirements(pdf):
    for i, rows in enumerate(_REQ_PAGES):
        fig = plt.figure(figsize=(PW/25.4, PH/25.4), dpi=120)
        ax = fig.add_axes([0, 0, 1, 1])
        header(ax, NPAGES-len(_REQ_PAGES)+1+i); foot(ax)
        box(ax, 12, 26, 396, 222, rows,
            title=f'客户原始需求 / 后续确认（{i+1}/{len(_REQ_PAGES)}）', fs=FS_NOTE)
        save_page(pdf, fig)


def hole_labels(ax, holes):
    # Satellite coordinates remain in the hole table; label each connector group once.
    holes = [h for h in holes if '+' not in h['id'] and '-' not in h['id']]
    if not holes:
        return
    xmin, xmax = ax.get_xlim(); ymin, ymax = ax.get_ylim()
    rows = sorted(holes, key=lambda h: h['y'])
    gap = 5 / ax.s
    ys = []
    for h in rows:
        ys.append(max(h['y'], ys[-1] + gap if ys else ymin + gap))
    shift = max(0, ys[-1] - (ymax - gap))
    for h, yy in zip(rows, ys):
        left = h['x'] > (xmin + xmax) / 2
        xx = h['x'] + (-12 if left else 12) / ax.s
        ax.annotate(h['id'], (h['x'], h['y']), (xx, yy - shift),
                    fontsize=FS_NOTE, color=REDC, ha='right' if left else 'left', va='center',
                    arrowprops=dict(arrowstyle='-', color=REDC, lw=.4))


def layout_issues(fig):
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    texts = list(fig.texts)
    for ax in fig.axes:
        texts += list(ax.texts) + [ax.title, ax._left_title, ax._right_title]
    boxes = []; issues = []
    for text in texts:
        if not text.get_visible() or not text.get_text().strip():
            continue
        # Annotation extent includes its leader; only test the actual glyphs.
        bb = Text.get_window_extent(text, renderer).frozen()
        label = text.get_text()
        if bb.x0 < 0 or bb.y0 < 0 or bb.x1 > fig.bbox.width or bb.y1 > fig.bbox.height:
            issues.append(dict(kind='outside_page', text=label))
        for old, other in boxes:
            if min(bb.x1, old.x1) - max(bb.x0, old.x0) > .5 and min(bb.y1, old.y1) - max(bb.y0, old.y0) > .5:
                issues.append(dict(kind='overlap', text=label, other=other))
        boxes.append((bb, label))
    return issues


def save_page(pdf, fig):
    issues = layout_issues(fig)
    _PAGE_LAYOUT.append(dict(page=len(_PAGE_LAYOUT) + 1, issues=issues))
    pdf.savefig(fig); plt.close(fig)

def _subdiv_tris(T, maxe=18.0):
    """Subdivide large tris (ref S-201-1-20261028-001 post.py) so shaded iso looks solid."""
    out = []; stack = [T]
    while stack:
        X = stack.pop()
        if len(X) == 0:
            continue
        e = np.stack([
            np.linalg.norm(X[:, 1] - X[:, 0], axis=1),
            np.linalg.norm(X[:, 2] - X[:, 1], axis=1),
            np.linalg.norm(X[:, 0] - X[:, 2], axis=1),
        ], 1)
        big = e.max(1) > maxe
        out.append(X[~big]); Y = X[big]
        if len(Y) == 0:
            continue
        k = e[big].argmax(1)
        Y = np.stack([np.roll(Y[i], -k[i], axis=0) for i in range(len(Y))])
        m = (Y[:, 0] + Y[:, 1]) / 2
        stack.append(np.stack([Y[:, 0], m, Y[:, 2]], 1))
        stack.append(np.stack([m, Y[:, 1], Y[:, 2]], 1))
    return np.concatenate(out) if out else np.zeros((0, 3, 3))


def render_assy_iso_png(path, names, elev=22, azim=-58, dpi=140, exploded=False):
    """Clean ASSEMBLY iso PNG matching S-201-1-20261028-001 page-1 clarity (t109u).

    Uses 2D isometric projection + solid per-triangle shade with matching edgecolors
    (same idea as addendum iso_png / 001 PREVIEW) — no mplot3d spiderweb.
    Outer L/W/H drawn as blue dim lines with arrows on the iso (ref 620/555/265 style).
    Assembly ignores mesh exploded shifts unless exploded=True.
    """
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    shifts = mesh.get('shifts', {}) if exploded else {}
    cols = {'U': np.array(TAN), 'END_L': np.array((0.80, 0.68, 0.45)),
            'END_R': np.array((0.80, 0.68, 0.45)), 'LID': np.array(GRN),
            'HANDLE_REF_L': np.array((0.50, 0.50, 0.58)),
            'HANDLE_REF_R': np.array((0.50, 0.50, 0.58))}
    # isometric: u=(x+y)/√2, v=(-x+y+2z)/√6  (iso_png / formed convention)
    S2, S6 = math.sqrt(2.0), math.sqrt(6.0)
    DV = np.array([1.0, -1.0, 1.0]) / math.sqrt(3.0)  # painter sort
    Lt = np.array([0.35, -0.55, 0.75]); Lt /= np.linalg.norm(Lt)

    tris_all = []; cols_all = []
    for n in names:
        if n not in mesh['parts']:
            continue
        v = np.array(mesh['parts'][n]['v'], dtype=float)
        f = np.array(mesh['parts'][n]['f'])
        sh = np.array(shifts.get(n, [0.0, 0.0, 0.0]), dtype=float)
        T = _subdiv_tris(v[f] + sh, maxe=16.0)
        if len(T) == 0:
            continue
        nn = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0])
        nn /= (np.linalg.norm(nn, axis=1)[:, None] + 1e-12)
        # backface soft-cull against view dir for cleaner solid
        vis = (nn @ DV) < 0.08  # keep near-silhouette + front
        T = T[vis]; nn = nn[vis]
        if len(T) == 0:
            continue
        shade = 0.42 + 0.55 * np.clip(np.abs(nn @ Lt), 0, 1)
        base = cols.get(n, np.array((0.65, 0.65, 0.65)))
        C = np.clip(base[None, :] * shade[:, None], 0, 1)
        tris_all.append(T); cols_all.append(C)
    if not tris_all:
        # empty fallback
        fig = plt.figure(figsize=(6, 5), dpi=dpi); ax = fig.add_subplot(111)
        ax.text(0.5, 0.5, '(无轴测网格)', ha='center'); ax.axis('off')
        fig.savefig(path, bbox_inches='tight', facecolor='white'); plt.close(fig)
        return path

    T = np.concatenate(tris_all); C = np.concatenate(cols_all)
    # painter's algorithm
    order = np.argsort(T.mean(1) @ DV)
    T, C = T[order], C[order]
    U = (T[:, :, 0] + T[:, :, 1]) / S2
    V = (-T[:, :, 0] + T[:, :, 1] + 2 * T[:, :, 2]) / S6
    polys = np.stack([U, V], axis=2)

    # outer bbox in 3D → projected corners for dim lines (cfg L/W/H labels)
    # Use mesh extents for geometry; labels from confirmed cfg L,W,H
    allv = T.reshape(-1, 3)
    x0, y0, z0 = allv.min(0); x1, y1, z1 = allv.max(0)
    # Prefer confirmed outer sizes for labels
    lab_L, lab_W, lab_H = (P[names[0]]['size'] if len(names)==1 else (float(OUTER_L),float(OUTER_W),float(H)))
    def iso_pt(X, Y, Z):
        return ((X + Y) / S2, (-X + Y + 2 * Z) / S6)

    # corners used for outer dims (assembled box)
    # L along X at front-bottom: (x0,y0,z0)-(x1,y0,z0)
    # W along Y at left-bottom:  (x0,y0,z0)-(x0,y1,z0)
    # H along Z at left-front:   (x0,y0,z0)-(x0,y0,z1)  — use full H to lid top
    # For lid-inclusive height use z1
    pL0, pL1 = iso_pt(x0, y0, z0), iso_pt(x1, y0, z0)
    pW0, pW1 = iso_pt(x0, y0, z0), iso_pt(x0, y1, z0)
    pH0, pH1 = iso_pt(x0, y0, z0), iso_pt(x0, y0, z1)

    pad = 18.0
    umin, umax = float(U.min()) - pad, float(U.max()) + pad
    vmin, vmax = float(V.min()) - pad, float(V.max()) + pad

    fig_w = 7.0; fig_h = 5.8
    fig = plt.figure(figsize=(fig_w, fig_h), dpi=dpi)
    ax = fig.add_axes([0.06, 0.10, 0.88, 0.82])
    ax.set_xlim(umin, umax); ax.set_ylim(vmin, vmax)
    ax.set_aspect('equal'); ax.axis('off')
    ax.add_collection(PolyCollection(
        polys, facecolors=C, edgecolors=C, linewidths=0.22, antialiased=True))

    # --- outer dim lines (ref isoview style: extension + arrow + value) ---
    def _dim(p0, p1, nxy, val, off=22.0):
        # nxy = outward normal in 2D for offset
        a = np.array(p0, dtype=float); b = np.array(p1, dtype=float)
        n = np.array(nxy, dtype=float); n = n / (np.linalg.norm(n) + 1e-12)
        pa = a + n * off; pb = b + n * off
        # extension ticks
        ax.plot([a[0], pa[0]], [a[1], pa[1]], color=DIMC, lw=0.45)
        ax.plot([b[0], pb[0]], [b[1], pb[1]], color=DIMC, lw=0.45)
        ax.annotate('', xy=pa, xytext=pb,
                    arrowprops=dict(arrowstyle='<|-|>', color=DIMC, lw=0.7, mutation_scale=9))
        mid = (pa + pb) / 2 + n * 6
        ax.text(mid[0], mid[1], f'{val:g}', color=DIMC, fontsize=_fs(11.0), weight='bold',
                ha='center', va='center',
                bbox=dict(boxstyle='round,pad=0.15', fc='white', ec=DIMC, lw=0.6, alpha=0.92))

    # normals chosen to sit outside the silhouette (similar to pdflib isoview)
    if not exploded: _dim(pL0, pL1, (0.2, -1.0), lab_L, off=28)   # L along bottom
    if not exploded: _dim(pW0, pW1, (-1.0, -0.35), lab_W, off=26) # W
    if not exploded: _dim(pH0, pH1, (-1.0, 0.15), lab_H, off=24)  # H

    title = ('零件轴测' if len(names)==1 else ('爆炸轴测（只平移）' if exploded else '装配轴测')) + f'  {lab_L:g}×{lab_W:g}×{lab_H:g}'
    fig.suptitle(title, fontproperties=FP, fontsize=_fs(13.0), y=0.98)
    fig.text(0.5, 0.015, f'L={lab_L:g}　W={lab_W:g}　H={lab_H:g}　｜　绿盖 / 褐箱　｜　确认稿' + ('；尺寸为装配尺寸，非爆炸间隔' if exploded else ''),
             ha='center', fontsize=_fs(9.4), color=DIMC)
    fig.savefig(path, facecolor='white', dpi=dpi)
    plt.close(fig)
    return path



def iso(ax, names, elev=25, azim=-60, mark_outer=True):
    """Legacy in-axes 3D iso (kept for any caller). Prefer render_assy_iso_png + embed for page-1."""
    shifts = mesh.get('shifts', {})
    cols = {'U': TAN, 'END_L': (0.78, 0.62, 0.40), 'END_R': (0.78, 0.62, 0.40), 'LID': GRN,
            'HANDLE_REF_L': (0.45, 0.45, 0.55), 'HANDLE_REF_R': (0.45, 0.45, 0.55)}
    lt = np.array([0.40, -0.50, 0.80], dtype=float); lt /= np.linalg.norm(lt)
    TT, CC = [], []
    for n in names:
        if n not in mesh['parts']: continue
        v = np.array(mesh['parts'][n]['v']); f = np.array(mesh['parts'][n]['f'])
        sh = np.array(shifts.get(n, [0, 0, 0]))
        tris = _subdiv_tris(v[f] + sh)
        nn = np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0])
        nn /= (np.linalg.norm(nn, axis=1)[:, None] + 1e-12)
        shade = 0.38 + 0.58 * np.abs(nn @ lt)
        base = np.array(cols.get(n, (0.6, 0.6, 0.6)), dtype=float)
        TT.append(tris); CC += [tuple(np.clip(base * s, 0, 1)) for s in shade]
    if TT:
        ax.add_collection3d(Poly3DCollection(np.concatenate(TT), facecolors=CC, edgecolors=CC, linewidths=0.15))
    ax.view_init(elev=elev, azim=azim)
    allv = np.concatenate([t.reshape(-1, 3) for t in TT]) if TT else np.zeros((1, 3))
    c = (allv.max(0) + allv.min(0)) / 2; r = (allv.max(0) - allv.min(0)).max() / 2 * 1.15
    ax.set_xlim(c[0] - r, c[0] + r); ax.set_ylim(c[1] - r, c[1] + r); ax.set_zlim(c[2] - r, c[2] + r)
    ax.set_axis_off()
    if mark_outer:
        ax.text2D(0.02, 0.02, f'L={L:g}', transform=ax.transAxes, fontsize=_fs(9.4), color=DIMC, weight='bold')
        ax.text2D(0.38, 0.02, f'W={W:g}', transform=ax.transAxes, fontsize=_fs(9.4), color=DIMC, weight='bold')
        ax.text2D(0.70, 0.02, f'H={H:g}', transform=ax.transAxes, fontsize=_fs(9.4), color=DIMC, weight='bold')


def pl(ax, pts, color='k', lw=0.7, ls='-'):
    if not pts: return
    xs=[p[0] for p in pts]; ys=[p[1] for p in pts]
    ax.plot(xs, ys, color=color, lw=lw, ls=ls)
def flatdraw(ax, name, show_holes=True):
    for w in flats[name]['wires']:
        pl(ax, w + [w[0]], color='k', lw=0.7)
    for b in P[name].get('bend_lines', []):
        pl(ax, b, color=REDC, lw=0.9, ls=(0, (6, 2)))
    for bend in P[name].get('bend_records', []):
        (x1, y1), (x2, y2) = bend['flat_line_mm']
        fx, fy = P[name]['flat_size']
        mx, my = (x1+x2)/2, (y1+y2)/2
        dx = (3 if mx < fx/2 else -6)/ax.s if abs(x1-x2) < 1e-4 else 0
        dy = (3 if my < fy/2 else -6)/ax.s if abs(y1-y2) < 1e-4 else 0
        ax.text(mx+dx, my+dy, bend['id'], fontsize=FS_DIM, color=REDC)
    if show_holes:
        for c in P[name].get('flat_circles', []):
            # [x,y,d] or [x,y,r]?
            if len(c) >= 3:
                d = c[2] if c[2] > 2 else c[2] * 2
                # report uses diameter in flat_circles typically
                ax.add_patch(Circle((c[0], c[1]), (c[2] / 2 if c[2] > 2 else c[2]), fill=False, ec=REDC, lw=0.45))

# ---- page builders ----
_probe_fig = plt.figure(figsize=(PW/25.4, PH/25.4), dpi=120)
_probe_ax = _probe_fig.add_axes([0, 0, 1, 1])
_probe_ax.set(xlim=(0, PW), ylim=(0, PH))
_REQ_PAGES = customer_requirement_pages(_probe_ax, JOB)
plt.close(_probe_fig)
NPAGES += len(_REQ_PAGES)
out_pdf = R / f'{VER}_BEND_PDF_A3_CN.pdf'
_PAGE_LAYOUT = []
_candidate = R / f'.{VER}.layout-check.pdf'
# U-wrap and L use the same primitives, colours, dimensions and layout gate as the end-plate variant.
if STRUCTURE == 'u_l_t7u':
    NPAGES = 7 + len(_REQ_PAGES)
    with PdfPages(_candidate) as pdf:
        fig = plt.figure(figsize=(PW/25.4, PH/25.4), dpi=120)
        ax = fig.add_axes([0,0,1,1]); header(ax,1); foot(ax)
        preview = R / 'PREVIEW'; preview.mkdir(exist_ok=True)
        for exploded, x, title in ((False,10,'装配轴测'),(True,210,'爆炸图（只平移原件）')):
            path = render_assy_iso_png(preview / f'{VER}_{"EXPLODED" if exploded else "ASSEMBLY"}_iso.png', list(P), exploded=exploded)
            a = fig.add_axes([x/PW,105/PH,195/PW,143/PH])
            a.imshow(plt.imread(path)); a.axis('off'); a.set_title(title,fontsize=FS_TITLE,loc='left')
        box(ax,12,22,396,72,[
            f'结构：U围＋L形底侧板＋03盖；L盖U，拼缝0、退让0；一套3件。合盖外形 {OUTER_L:g}×{OUTER_W:g}×{H:g}。',
            f'体外 {L:g}×{W:g}×{Hb:g}；高含盖、不含把手；盖顶中心一个85/62/30把手，4×Ø6.6 M6过孔，仅安装参考。',
            *[f'方孔 {h["size_xy"][0]:g}×{h["size_xy"][1]:g}，右侧X={h["center"][0]:g}面；中心Y={h["center"][1]:g}、Z={h["center"][2]:g}；距相邻竖边{W-h["center"][1]:g}、孔下沿距底{h["center"][2]-h["size_xy"][1]/2:g}。' for h in _RECTS],
            *((JOB.get('confirm') or {}).get('pending_cn') or [])[:1],
            'Ri/K/扣除为试折候选；1mm板直接攻M4约1扣，易滑牙；未实物试折试装，production_release=false。',
        ],title='本版参数及确认事项')
        save_page(pdf,fig)
        for index,name in enumerate(('U','L','LID')):
            page = 2+index*2
            piece = P[name]; fx,fy = piece['flat_size']; B = bidir(rep,name)
            fig = plt.figure(figsize=(PW/25.4,PH/25.4),dpi=120)
            ax = fig.add_axes([0,0,1,1]); header(ax,page); foot(ax)
            s = min(195/(fx+130),145/(fy+130))
            a = vax(fig,18,90,(-65,fx+65),(-65,fy+65),s,f'{name} 实际展开 {fx:.2f}×{fy:.2f}；外表面朝读者')
            flatdraw(a,name)
            for sg in B['X_seg']:
                dimh(a,sg[0],sg[1],fy+7/s,fy,fy,f'{sg[2]:.2f}')
            for sg in B['Y_seg']:
                dimv(a,sg[0],sg[1],-7/s,0,0,f'{sg[2]:.2f}')
            bilateral_dims(a,B)
            dimh(a,0,fx,-42/s,0,0,f'总长 {fx:.2f}')
            dimv(a,0,fy,fx+32/s,fx,fx,f'总宽 {fy:.2f}')
            rows = ['孔号 / 展开X / 展开Y / 直径（mm）；原点为CUT左下角']
            rows += [f'C{i+1:02d} / {x:.2f} / {y:.2f} / Ø{d:g}' for i,(x,y,d) in enumerate(piece.get('flat_circles',[]))]
            rows += [f'方孔{i+1}：X {r[0]:.2f}～{r[2]:.2f}；Y {r[1]:.2f}～{r[3]:.2f}' for i,r in enumerate(piece.get('flat_rectangles',[]))]
            box(ax,242,130,166,125,rows,title=f'{name} 实际CUT孔表')
            bends = [f'{r["id"]} {r["axis"]}：距A {r["a"]} / 距B {r["b"]}；{r["seg_prev"]}；{r["seg_next"]}；{r["dir"]} {r["ang"]:g}°' for r in table_rows(B,name)]
            if name == 'LID':
                c3 = rep['corner03']
                bends += [f'03四角同形；各点由展开外角向内量；角缝{c3["corner_gap"]:g}候选。']
                bends += [f'{key}：X={c3[key][0]:.3f} / Y={c3[key][1]:.3f} mm' for key in ('P1','P2','P3')]
            box(ax,242,35,166,88,bends+[f'内R{ri:g}；K={K:.5f}；BD90={BD:.3f}，候选。',
                 '折序按B号供试折；刀具、靠边及回弹须工厂确认。'],title='逐弯双向基准 / 折序候选')
            box(ax,12,20,220,35,[f'{MATERIAL_CN} t{t:g}，每套{name}×1；CUT不含折弯线。',
                'BEND红色连续线；NEST一盒一份；成形位置见下页。',
                'M4底孔Ø3.3，盖Ø4.5；薄板螺纹易滑牙。'],title='加工提示')
            save_page(pdf,fig)
            fig = plt.figure(figsize=(PW/25.4,PH/25.4),dpi=120)
            ax = fig.add_axes([0,0,1,1]); header(ax,page+1); foot(ax)
            for label,x,title in (('front',8,'主视'),('right',142,'右视'),('top',276,'俯视')):
                polys = proj[name][label]['vis']
                transform = {'front':lambda u,v:(v,-u),'right':lambda u,v:(-v,u),'top':lambda u,v:(u,v)}[label]
                pts = np.array([transform(*p) for poly in polys for p in poly])
                lo,hi = pts.min(axis=0),pts.max(axis=0)
                expected_size = {'front':(piece['size'][0],piece['size'][2]),'right':(piece['size'][1],piece['size'][2]),'top':(piece['size'][0],piece['size'][1])}[label]
                assert np.max(np.abs(hi-lo-expected_size)) < 1e-4, (name,label,hi-lo,expected_size)
                s = min(112/(hi[0]-lo[0]+65),125/(hi[1]-lo[1]+65))
                a = vax(fig,x,107,(lo[0]-30,hi[0]+35),(lo[1]-30,hi[1]+35),s,f'{name} {title}（实际STEP）')
                view(a,name,label,transform)
                dimh(a,lo[0],hi[0],lo[1]-15/s,lo[1],lo[1],f'{hi[0]-lo[0]:.2f}')
                dimv(a,lo[1],hi[1],hi[0]+15/s,hi[0],hi[0],f'{hi[1]-lo[1]:.2f}')
                if name == 'U' and label == 'right':
                    for opening in _RECTS:
                        cy,cz = opening['center'][1:]
                        dimv(a,0,cz,lo[0]-16/s,cy,cy,f'中心距底 {cz:g}')
                        dimh(a,cy,W,cz+opening['size_xy'][1]/2+12/s,cz,cz,f'距边 {W-cy:g}')
            path = render_assy_iso_png(preview / f'{VER}_{name}_iso.png',[name])
            a = fig.add_axes([12/PW,20/PH,110/PW,70/PH]); a.imshow(plt.imread(path)); a.axis('off')
            # Isometric labels above use product dimensions only for assemblies; piece extents follow below.
            lines = [f'成形外包络 {piece["size"][0]:.2f}×{piece["size"][1]:.2f}×{piece["size"][2]:.2f}；厚{t:g}；弯数{len(piece["bend_records"])}。',
                     '本页三视及轴测由同一STEP读取；展开孔坐标见前页，不按示意比例量孔。']
            if name == 'U':
                lines += [*[f'方孔 {h["size_xy"][0]:g}×{h["size_xy"][1]:g}：中心Y{h["center"][1]:g}/Z{h["center"][2]:g}；下沿Z{h["center"][2]-h["size_xy"][1]/2:g}；距后竖边{W-h["center"][1]:g}；所在面X={h["center"][0]:g}。' for h in _RECTS],
                          'U为三面围板；L盖住前开口及底边；0缝0退让；展开两弯。']
            elif name == 'LID':
                lines += [f'把手中心 X{L/2:g}/Y{W/2:g}；宽排85、窄排62、排距30；4×Ø6.6 M6过孔。',
                          '把手实体、承载及活动包络未核；03四折盖角及原生展开核验见EVIDENCE。']
            else:
                lines += ['L形底侧板：底＋前侧一折；外露边与U外面齐平；M4固定孔按本版表。']
            box(ax,137,22,271,68,lines,title='成形位置与配合')
            save_page(pdf,fig)
        draw_customer_requirements(pdf)
else:

    with PdfPages(_candidate) as pdf:
        # PAGE 1 — overview WITH orthographic outer dims (fix: bare iso had no L/W/H labels)
        fig = plt.figure(figsize=(PW / 25.4, PH / 25.4), dpi=120)
        ax = fig.add_axes([0, 0, 1, 1]); header(ax, 1); foot(ax)
        LOL = L + 2 * (g + t); LOW = W + 2 * (g + t); OH = g + t
        # --- layout under red ERP bar (ends at PH-34); keep view tops ≤ PH-36 (t108u) ---
        _hdr_clear = PH - 36  # 261 mm
        # --- 主视图 front (Y=0): length × height ---
        sF = min(0.32, 185 / (L + 110), 77 / (H + 90))
        _fh = (H + 55 - (-35)) * sF  # axes height in page-mm
        if 170 + _fh > _hdr_clear:  # prefer y≈170; shrink scale if still tall
            sF = max(0.22, (_hdr_clear - 170) / (H + 90))
            _fh = (H + 90) * sF
        yF = min(170.0, _hdr_clear - _fh)
        a = vax(fig, 8, yF, (-55, L + 55), (-35, H + 55), sF,
                f'主视图（从前侧 Y=0 看）约 1:{1/sF:.1f}  — 外尺寸已标注', tfs=7.5, axis_off=True)
        view(a, 'ASSEMBLY', 'front', lambda u, v: (v, -u))
        dimv(a, 0, H, -40, -OH, -OH, f'{H:g} 含盖总高（已确认）', fs=_fs(9.4))
        dimv(a, 0, Hb, L + 42, L, L, f'{Hb:g} 箱体高', fs=_fs(9.4))
        dimv(a, H - skirt, H, L + 28, L + OH, L + OH, f'{skirt:g}', fs=_fs(9.4))
        dimh(a, -OH, L + OH, H + 38, H, H, f'{LOL:g} 盖外长', fs=_fs(9.4))
        dimh(a, 0, L, -22, 0, 0, f'{L:g} 箱体外长（已确认）', fs=_fs(9.4))
        for x in LONG_X:
            a.plot([x], [ZH], '+', color=BLU, ms=5, mew=0.8)
        a.text(L * 0.12, Hb*.4 if _PANEL else ZH - 28, f'长边每侧 M4×{len(LONG_X)}  Z={ZH:g}（Ø3.3攻 / 盖Ø4.5）', fontsize=_fs(9.4), color=BLU)
        a.text(L * 0.12, 35, f'盖裙下沿 Z={H - skirt:g}；箱体顶 Z={Hb:g}；顶隙 q={q:g}', fontsize=_fs(9.4))
        # --- 左/端板侧视图 right: width × height (same y/scale as front; clear header) ---
        sR = min(sF, 110 / (W + 105))
        a2 = vax(fig, 210, yF, (-50, W + 55), (-35, H + 55), sR,
                 f'{_SIDE_TITLE}约 1:{1/sR:.1f}', tfs=7.0, axis_off=True)
        # t126u: cable holes remain END_R; handle moved to LID_TOP center. Side view shows END_R holes only.
        view(a2, 'ASSEMBLY', 'right', lambda u, v: (-v, u))
        dimh(a2, -OH, W + OH, H + 38, H, H, f'{LOW:g} 盖外宽', fs=_fs(9.4))
        dimh(a2, 0, W, -22, 0, 0, f'{W:g} 箱体外宽（已确认）', fs=_fs(9.4))
        dimv(a2, 0, H, -38, -OH, -OH, f'{H:g}', fs=_fs(9.4))
        for y in SHORT_Y:
            a2.plot([y], [ZH], '+', color=BLU, ms=5, mew=0.8)
        a2.text(15, 35, f'每侧 M4×{len(SHORT_Y)}；端板 {W:g}×{Hb:g}', fontsize=_fs(9.4), color=BLU)
        # END_R functional holes (formed YZ)
        a2.hlines(H - skirt, 0, W, color=REDC, ls=':', lw=0.6)
        a2.text(W*0.55, H - skirt + 2, f'盖裙下沿 Z={H-skirt:g}', fontsize=_fs(9.4), color=REDC)
        for c in _END_CIRCLES:
            if (c.get('part') or EF_PART) != 'END_R' and EF_PART != 'END_R':
                continue
            yy, zz, dd = float(c['y']), float(c['z']), float(c['d'])
            a2.add_patch(Circle((yy, zz), dd/2, fill=False, ec=REDC, lw=0.7))
            a2.text(yy + 4, zz + dd/2 + 2, f"{c.get('id','')}Ø{dd:g}", fontsize=_fs(9.4), color=REDC)
        for r in _END_RECTS:
            if (r.get('part') or EF_PART) != 'END_R' and EF_PART != 'END_R':
                continue
            cy, cz, ww, hh = float(r['cy']), float(r['cz']), float(r['w']), float(r['h'])
            a2.add_patch(Rectangle((cy-ww/2, cz-hh/2), ww, hh, fill=False, ec=REDC, lw=0.8))
            a2.text(cy, cz-hh/2-6, f"品字{ww:g}×{hh:g}", fontsize=_fs(9.4), ha='center', color=REDC)
        a2.text(8, 65, '端板把手坐标见附页' if _PANEL_HANDLES else ('端板功能孔见第3页' if _END_HOLES else '端板无功能孔'), fontsize=_fs(9.4), color=REDC)
        # --- 俯视图 top: length × width ---
        sT = min(0.32, 190 / (L + 110), 118 / (W + 120))
        _top_extra = _TOP_EXTRA
        a3 = vax(fig, 8, 28, (-55, L + 55), (-50, W + 70), sT,
                 f'俯视图（从上看）约 1:{1/sT:.1f}  {_top_extra}', tfs=7.5, axis_off=True)
        view(a3, 'ASSEMBLY', 'top', lambda u, v: (u, v), hidden=False)
        dimh(a3, -OH, L + OH, -32, -OH, -OH, f'{LOL:g} 盖外长', fs=_fs(9.4))
        dimv(a3, -OH, W + OH, -40, -OH, -OH, f'{LOW:g} 盖外宽', fs=_fs(9.4))
        dimh(a3, 0, L, W + 48, W, W, f'{L:g} 箱体外长（已确认）', fs=_fs(9.4))
        dimv(a3, 0, W, L + 38, W, W, f'{W:g} 箱体外宽（已确认）', fs=_fs(9.4))
        for cx in (HANDLE_CX if HANDLE_MOUNT not in ('END_L+END_R','END_R','END_L') else []):
            a3.add_patch(Rectangle((cx - HREF_BX / 2, HANDLE_CY - HREF_BY / 2), HREF_BX, HREF_BY,
                                   fill=False, ec='0.4', ls=':', lw=0.5))
            a3.plot(cx, HANDLE_CY, 'k+', ms=4)
            a3.text(cx, HANDLE_CY + 55, f'把手\n({cx:g},{HANDLE_CY:g})', fontsize=_fs(9.4), ha='center', color=BLU)
        for h in LID_HOLES:
            a3.add_patch(Circle((h['x'], h['y']), h['d'] / 2, fill=False, ec=REDC, lw=0.6))
        hole_labels(a3, LID_HOLES)
        # --- 装配轴测：2D iso solid + outer dim arrows (ref 001 isoview L/W/H) t107u/t109u ---
        if HAS_HANDLES and HANDLE_MOUNT in ('END_L+END_R','END_R','END_L'):
            _iso_parts = ['U', 'END_L', 'END_R', 'LID'] + [f'HANDLE_REF_{p[-1]}' for p in HANDLE_PARTS]
        elif HAS_HANDLES and HANDLE_CX:
            # LID_TOP: build.py names HANDLE_REF_L if cx<L/2 else HANDLE_REF_R (center → R)
            _iso_parts = ['U', 'END_L', 'END_R', 'LID'] + [f'HANDLE_REF_{"L" if cx < L/2 else "R"}' for cx in HANDLE_CX]
        else:
            _iso_parts = ['U', 'END_L', 'END_R', 'LID']
        _iso_dir = ORDER / 'logs' / 'iso'; _iso_dir.mkdir(parents=True, exist_ok=True)
        _iso_png = render_assy_iso_png(_iso_dir / f'{VER}_ASSEMBLY_iso.png', _iso_parts, exploded=False)
        _exp_png = render_assy_iso_png(_iso_dir / f'{VER}_EXPLODED_iso.png', _iso_parts, exploded=True)
        try:
            _prev = R / 'PREVIEW'; _prev.mkdir(parents=True, exist_ok=True)
            (_prev / f'{VER}_ASSEMBLY_iso.png').write_bytes(_iso_png.read_bytes())
            (_prev / f'{VER}_EXPLODED_iso.png').write_bytes(_exp_png.read_bytes())
        except Exception:
            pass
        # embed assembly iso (primary); small exploded below if space
        a3d = fig.add_axes([0.51, 0.23, 0.25, 0.28])
        a3d.imshow(plt.imread(str(_iso_png))); a3d.set_axis_off()
        a3d.set_title(f'装配轴测  {OUTER_L:g}×{OUTER_W:g}×{H:g}', fontsize=_fs(9.4), loc='left')
        a3e = fig.add_axes([0.51, 0.06, 0.25, 0.15])
        a3e.imshow(plt.imread(str(_exp_png))); a3e.set_axis_off()
        a3e.set_title('爆炸轴测（示意）', fontsize=_fs(9.4), loc='left')
        # --- 关键参数 ---
        rh = '/'.join(f"{h['id']}Ø{h['d']:g}" for h in LID_HOLES)
        box(ax, 330, 95, 82, 155, [
            ('尺寸口径 盒体尺寸/body_outer', REDC),
            f'· 合盖外尺寸 {OUTER_L:g}×{OUTER_W:g}×{H:g}',
            f'· {H:g}=含盖总高(不含把手)',
            f'· 箱体高 Hb={Hb:g}',
            f'· 盖外 {LOL:g}×{LOW:g}×{skirt:g}（盖外形，非ERP）',
            ('结构', NAVY),
            '· 件1 U：底+两长侧壁',
            '· 件2/3 外封端板零折',
            '  拼缝0/不退让/齐口',
            f'· 件4 盖裙{skirt:g} 03角缝候选0.2',
            f'· 把手：{_HDL_LINE}',
            f'· 盖顶功能孔 {len(LID_HOLES)} 个；详见第4页',
            '· 功能孔及把手坐标见附页' if _PANEL else '· 端板功能孔见第3页',
            '· 仍开盖-体M4（规则4/23）',
            f'· {_SKIRT_NOTE}',
            ('待确认', REDC),
            '· 端板接合/RiK/角缝',
            '· 薄板攻M4替代',
            '· 法兰用途/卫星是否改攻丝',
        ], title='关键参数', fs=_fs(9.4))
        box(ax, 330, 25, 82, 55, [
            f'长X={"/".join(f"{x:g}" for x in LONG_X)}',
            f'短Y={"/".join(f"{y:g}" for y in SHORT_Y)}',
            f'Z={ZH:g}；箱Ø3.3/盖Ø4.5'
        ], title='M4 布局', fs=_fs(9.4))
        # t108u: removed cream banner at PH-48 — it overlapped navy/red header & front-view top.
        # Outer L×W×H already on red ERP bar + three orthographic views + iso title/callouts.
        save_page(pdf, fig)

        # PAGE 2 — U flat alone (t59u/t124u: do not pack with ends; keep dim text ≥MINPT)
        fig = plt.figure(figsize=(PW / 25.4, PH / 25.4), dpi=120)
        ax = fig.add_axes([0, 0, 1, 1]); header(ax, 2); foot(ax)
        ufx, ufy = P['U']['flat_size']
        # prefer larger view scale like 001 fsc≈0.55 when it fits; else fit
        sU = min(0.55, 240 / max(ufx + 80, 1), 200 / max(ufy + 60, 1))
        a = vax(fig, 20, 40, (-40, ufx + 40), (-30, ufy + 30), sU,
                f'件1 U 展开 {ufx:.2f}×{ufy:.2f}（外表面朝读者；规则9双向）·视觉字号≥{MINPT}pt')
        flatdraw(a, 'U')
        BU = bidir(rep, 'U')
        for i, sg in enumerate(BU.get('X_seg', [])):
            dimh(a, sg[0], sg[1], ufy + 10 + (i % 2) * 10, ufy + 2, ufy + 2, f'{sg[2]:.2f}', fs=FS_DIM)
        for i, sg in enumerate(BU.get('Y_seg', [])):
            dimv(a, sg[0], sg[1], -12 - (i % 2) * 12, -2, -2, f'{sg[2]:.2f}', fs=FS_DIM)
        dimh(a, 0, ufx, -22, 0, 0, f'{ufx:.2f}'); dimv(a, 0, ufy, ufx + 18, ufx, ufx, f'{ufy:.2f}')
        bilateral_dims(a, BU)
        box(ax, 270, 40, 140, 200, [
            f'U：弯线沿长{L-2*t:g}；第2道侧壁高{Hb:g}、内宽{W-2*t:g} — 深U折弯避让 WARN',
            f'拼缝0、inset0、上边齐口；接合=内侧角焊或外侧激光焊（待确认）',
            f'BD={BD:.4f}；U展开宽公式 {W:g}+2×{Hb:g}−2×BD = {W+2*Hb-2*BD:.2f}',
            f'视觉：参考 S-201-1-20261031-001-v1；字号≥{MINPT}pt；拥挤则加页不缩字',
            '处理面朝外（规则31）；展开外表面朝读者',
        ], title='U 说明（右栏）', fs=FS_BOX)
        save_page(pdf, fig)

        # PAGE 3 — END_R (+ END_L note) alone
        fig = plt.figure(figsize=(PW / 25.4, PH / 25.4), dpi=120)
        ax = fig.add_axes([0, 0, 1, 1]); header(ax, 3); foot(ax)
        efx, efy = P['END_R']['flat_size']
        sE = min(0.9, 220 / max(efx + 50, 1), 180 / max(efy + 50, 1))
        a2 = vax(fig, 20, 50, (-20, efx + 30), (-20, efy + 30), sE,
                 f'件3 END_R 展开（零折；外表面/处理面朝读者）{efx:.2f}×{efy:.2f}')
        flatdraw(a2, 'END_R')
        for y in SHORT_Y:
            a2.plot(y, ZH, 'b+', ms=5, mew=0.8)
        a2.axhline(H - skirt, color=REDC, ls=':', lw=0.5)
        a2.text(efx * 0.4, H - skirt - 18, f'盖裙下沿 Z={H-skirt:g}', fontsize=_fs(FS_NOTE), color=REDC)
        def _er_flat(y, z):
            return (float(y), float(z))
        for c in _END_CIRCLES:
            if (c.get('part') or EF_PART) != 'END_R':
                continue
            fx, fy = _er_flat(c['y'], c['z']); dd = float(c['d'])
            a2.text(fx + 3, fy + dd/2 + 1.5, f"{c.get('id','')}Ø{dd:g}\n成形Y{float(c['y']):g} Z{float(c['z']):g}", fontsize=_fs(FS_NOTE), color=REDC)
        for r in _END_RECTS:
            if (r.get('part') or EF_PART) != 'END_R':
                continue
            cy, cz, ww, hh = float(r['cy']), float(r['cz']), float(r['w']), float(r['h'])
            fx, fy = _er_flat(cy, cz)
            a2.add_patch(Rectangle((fx-ww/2, fy-hh/2), ww, hh, fill=False, ec=REDC, lw=0.9))
            a2.text(fx, fy, f"品字{ww:g}×{hh:g}\n成形Y{cy:g} Z{cz:g}", fontsize=_fs(FS_NOTE), ha='center', va='center', color=REDC)
        a2.text(efx * 0.5, 28, 'END_R展开 X′=Y（外表面朝读者/处理面朝上）；孔标注=成形Y/Z；与CUT DXF同手性', fontsize=_fs(FS_NOTE), ha='center', color=BLU)
        dimh(a2, 0, efx, -14, 0, 0, f'{efx:.2f}'); dimv(a2, 0, efy, efx + 14, efx, efx, f'{efy:.2f}')
        # END_L small
        efxL, efyL = P['END_L']['flat_size']
        aL = vax(fig, 250, 155, (-15, efxL + 20), (-15, efyL + 20), min(0.55, 140/max(efxL+40,1), 85/max(efyL+35,1)),
                 f'件2 END_L 展开（零折）{efxL:.2f}×{efyL:.2f}')
        flatdraw(aL, 'END_L')
        dimh(aL, 0, efxL, -12, 0, 0, f'{efxL:.2f}'); dimv(aL, 0, efyL, efxL + 12, efxL, efxL, f'{efyL:.2f}')
        box(ax, 250, 40, 155, 100, [
            f'端板：零折平板，外轮廓={W:g}×{Hb:g}，底角R{ro:g}与U外圆同心',
            '两端板把手居中；坐标及孔表见附页' if _PANEL_HANDLES else 'END_R：功能孔见左图；END_L：通常仅M4（以本单为准）',
            '仍开盖-体 M4（规则23）：端板短边 Y 上攻丝 Ø3.3',
            '规则31：处理面朝外；DXF与PDF同手性',
            'NEST：端板可旋转90°塞进单张2440×1220；单件CUT未旋转',
        ], title='端板说明（右栏）', fs=FS_BOX)
        save_page(pdf, fig)

        # PAGE 4 — LID flat + roof holes + handles
        fig = plt.figure(figsize=(PW / 25.4, PH / 25.4), dpi=120)
        ax = fig.add_axes([0, 0, 1, 1]); header(ax, 4); foot(ax)
        lfx, lfy = P['LID']['flat_size']
        a = vax(fig, 15, 35, (-50, lfx + 40), (-40, lfy + 35), min(.48, 245/(lfx+90), 190/(lfy+75)), f'件4 上盖展开 {lfx:.2f}×{lfy:.2f}（外表面朝读者；双向尺寸）')
        flatdraw(a, 'LID')
        BL = bidir(rep, 'LID')
        for i, sg in enumerate(BL.get('X_seg', [])):
            dimh(a, sg[0], sg[1], lfy + 6 + (i % 2) * 5, lfy + 1, lfy + 1, f'{sg[2]:.2f}', fs=_fs(9.4))
        for i, sg in enumerate(BL.get('Y_seg', [])):
            dimv(a, sg[0], sg[1], -6 - (i % 2) * 7, -1, -1, f'{sg[2]:.2f}', fs=_fs(9.4))
        dimh(a, 0, lfx, -22, 0, 0, f'{lfx:.2f}'); dimv(a, 0, lfy, lfx + 12, lfx, lfx, f'{lfy:.2f}')
        bilateral_dims(a, BL)
        # formed lid top sketch
        a2 = vax(fig, 280, 180, (-20, L + 20), (-20, W + 20), min(.25, 120/(L+40), 65/(W+40)), '盖顶俯视（成形坐标，孔位待确认）')
        a2.add_patch(Rectangle((-g, -g), L + 2 * g, W + 2 * g, fill=False, ec=GRN, lw=0.9))
        a2.add_patch(Rectangle((0, 0), L, W, fill=False, ec='0.5', lw=0.4, ls='--'))
        for cx in (HANDLE_CX if HANDLE_MOUNT not in ('END_L+END_R','END_R','END_L') else []):
            a2.add_patch(Rectangle((cx - HREF_BX / 2, HANDLE_CY - HREF_BY / 2), HREF_BX, HREF_BY, fill=False, ec='0.4', ls=':', lw=0.6))
            a2.plot(cx, HANDLE_CY, 'k+', ms=5)
            a2.text(cx, HANDLE_CY + 55, f'把手\n({cx:g},{HANDLE_CY:g})', fontsize=_fs(9.4), ha='center', color=BLU)
        for h in LID_HOLES:
            a2.add_patch(Circle((h['x'], h['y']), h['d'] / 2, fill=False, ec=REDC, lw=0.7))
        hole_labels(a2, LID_HOLES)
        box(ax, 280, 25, 125, 145, [
            '孔号 / 直径 / 成形X / 成形Y（mm）',
        ] + [f"{h['id']} / Ø{h['d']:g} / {h['x']:g} / {h['y']:g}" for h in LID_HOLES] + [
            f'把手：{_HDL_LINE}',
            _END_SUMMARY,
            f'{_SKIRT_NOTE}',
            f'薄板 t={t:g} 攻M4 WARN（约1扣；压铆/拉铆/点焊待确认）',
            f'盖角03 corner_gap={CORNER_GAP:g} 候选（切除版展开）',
        ], title='盖顶 / 端板孔 / 把手', fs=_fs(9.4), ec=REDC)
        save_page(pdf, fig)

        # PAGE 5 — checks / pending
        fig = plt.figure(figsize=(PW / 25.4, PH / 25.4), dpi=120)
        ax = fig.add_axes([0, 0, 1, 1]); header(ax, 5); foot(ax)
        coax = all(c.get('axis_line_material_lid_mm', 1) < 0.1 and c.get('axis_line_material_body_mm', 1) < 0.1 for c in rep.get('hole_coaxial', []))
        hok = rep.get('handle_mirror_ok', False)
        _cs = dchk.get('dxf_checks', dchk if isinstance(dchk, list) else [])
        allpass = all(c.get('pass') for c in _cs) if _cs else False
        n3 = {}
        n3p = W_ / 'native03.json'
        if n3p.exists():
            n3 = json.load(open(n3p))
        confs = json.load(open(W_ / 'conflicts.json')) if (W_ / 'conflicts.json').exists() else []
        warn_cn = [c['msg_cn'] for c in confs if c.get('level') == 'WARN'][:6]
        box(ax, 12, 150, 250, 110, [
            ('【计算检查】CAD，非实物；native03结果见本次报告', REDC),
            f'· 模型：箱体{L:g}×{W:g}×{Hb:g}；盖约{L+2*(g+t):g}×{W+2*(g+t):g}×{skirt:g}；总高{H:g}',
            f'· M4孔盖↔箱体 {len(rep["holes"])}/{len(rep["holes"])} 同轴 {"通过" if coax else "见报告"}',
            (f'· 端板把手孔{len(_PANEL_HANDLES)}；STEP/DXF回读见cad_verification' if _PANEL_HANDLES else (f'· 把手孔 {len(rep.get("handle_holes") or [])} 通透核验、85/62/30、镜像 {"通过" if hok else "见报告"}' if HAS_HANDLES else '· 不要把手，无把手孔')),
            f'· {_END_SUMMARY}；{_SKIRT_NOTE}',
            f'· DXF CUT/BEND/NEST 门禁：{"通过" if allpass else "见 dxf_checks"}',
            f'· corner03.py：ok；native03：{n3.get("error", n3.get("ok", "?"))}',
            f'· NEST 1BOX：排布及旋转以本版套料报告为准',
        ] + [(f'· WARN: {w[:60]}', REDC) for w in warn_cn[:3]], title='检查摘要', fs=_fs(9.4))
        _pend_path = ORDER / f'{VER}.brief.json'
        pending = (JOB.get('confirm') or {}).get('pending_cn') or (json.load(open(_pend_path))['confirm']['pending_cn'] if _pend_path.exists() else [
            f'K={K:.4f} / Ri={ri:g} 为候选值，须试折',
            '孔边距与孔距以本图为准，客户未给孔距',
            '1.0 板攻 M4 约 1 扣，压铆或拉铆未定',
            '确认稿，production_release=false，非生产放行',
        ])
        box(ax, 270, 40, 140, 220, [f'{i+1}. {p}' for i, p in enumerate(pending)], title='待确认清单', fs=_fs(9.4), ec=REDC)
        box(ax, 12, 40, 250, 100, [
            f'BA=π/2×(Ri+K·t)={BA:.4f}；OSSB={OSSB:.1f}；BD={BD:.4f}',
            f'U展开宽={W:g}+2×{Hb:g}−2BD={W+2*Hb-2*BD:.2f}（CAD {P["U"]["flat_size"][1]:.2f}）',
            f'盖展开 CAD {P["LID"]["flat_size"][0]:.2f}×{P["LID"]["flat_size"][1]:.2f}；端板零折 {P["END_L"]["flat_size"][0]:.2f}×{P["END_L"]["flat_size"][1]:.2f}',
            f'K={K:.4f} / Ri{ri:g}：候选，须试折；孔坐标：箱体外角 X0/Y0/Z0',
            f'把手：{_HDL_LINE}；{_END_SUMMARY}',
            f'订单{JOB.get("quantity", 1)}套；套料1盒；production_release={str(bool((JOB or {}).get("production_release", False))).lower()}；版本 {VER}',
        ] + [f'{part}/{row["id"]} {row["axis"]} 距A {row["a"]} / 距B {row["b"]} / '
             f'段长 {row["seg_prev"]}；{row["seg_next"]} / {row["dir"]} {row["ang"]:g}°'
             for part in ('U', 'LID') for row in table_rows(bidir(rep, part), part)],
            title='K值 / 折弯扣除 / 折弯表（原生编号，非机台工序）', fs=_fs(9.4))
        save_page(pdf, fig)

        if _PANEL:
            def circle_table(canvas, name, x, y, width, step=6.5):
                rows = sorted(P[name]['flat_circles'], key=lambda row: (row[1], row[0], row[2]))
                canvas.text(x, y, f'{name} CUT孔表：展开左下角为原点，全部圆孔', fontsize=FS_TITLE, color=NAVY)
                ys = y-10
                columns = [x, x+20, x+width*.43, x+width*.72]
                for xx, label in zip(columns, ['孔号', 'Ø', '展开X', '展开Y']):
                    canvas.text(xx, ys, label, fontsize=FS_NOTE, color=NAVY)
                for i, (cx, cy, diameter) in enumerate(rows, 1):
                    yy = ys-step*i
                    for xx, value in zip(columns, [f'F{i:02}', f'{diameter:g}', f'{cx:.3f}', f'{cy:.3f}']):
                        canvas.text(xx, yy, value, fontsize=FS_NOTE)
                return rows

            fig = plt.figure(figsize=(PW/25.4, PH/25.4), dpi=120)
            ax = fig.add_axes([0, 0, 1, 1]); header(ax, 6); foot(ax)
            a = vax(fig, 12, 135, (-40, L+40), (-30, Hb+65), min(230/(L+80), 115/(Hb+95)),
                    'U前侧 Y=0；坐标X从左端、Z从箱底；后侧无功能孔')
            a.add_patch(Rectangle((0, 0), L, Hb, fill=False, ec=TAN))
            for hole in [h for h in _PANEL if h['part_id']=='U']:
                x, _, z = hole['point']; d = hole['diameter']
                a.add_patch(Circle((x,z), d/2, fill=False, ec=REDC))
                if d >= 10:
                    a.text(x, z+22, hole['id'].replace('-MAIN',''), fontsize=FS_NOTE, ha='center', color=REDC)
            for rect in _RECTS:
                x, _, z = rect['center']; w, h = rect['size_xy']
                a.add_patch(FancyBboxPatch((x-w/2,z-h/2),w,h,boxstyle=f'round,pad=0,rounding_size={rect.get("corner_radius",0)}',fill=False,ec=REDC))
            dimh(a,0,L,-15,0,0,f'{L:g}')
            _front = [h for h in _PANEL if h['part_id']=='U']
            _large = [h for h in _front if h['diameter']>=10]
            _notes = []
            for h in _large:
                xx,_,zz=h['point']
                _notes.append(f"{h['id']}：Ø{h['diameter']:g}，中心X{xx:g}/Z{zz:g}，距近端边{min(xx,L-xx):g}。")
                group=[v for v in _front if v['id'].startswith(h['id'].split('-')[0]+'-S')]
                if len(group)==4:
                    pitchx=max(v['point'][0] for v in group)-min(v['point'][0] for v in group)
                    pitchz=max(v['point'][2] for v in group)-min(v['point'][2] for v in group)
                    _notes.append(f"安装孔4×Ø{group[0]['diameter']:g}；圆心距{pitchx:g}×{pitchz:g}；通孔。")
            _notes += [f"{r['id']}：中心X{r['center'][0]:g}/Z{r['center'][2]:g}；{r['size_xy'][0]:g}×{r['size_xy'][1]:g}；R{r.get('corner_radius',0):g}" for r in _RECTS]
            _notes += ['全部圆孔坐标见右侧实际CUT孔表；矩形开口尺寸见本栏。',
                       '展开原点为CUT外轮廓左下角；U前侧外表面朝读者。']
            box(ax,12,25,235,100,_notes,title='侧壁开孔尺寸（STEP/DXF同源）',fs=FS_NOTE)
            circle_table(ax,'U',265,250,145)
            save_page(pdf,fig)

            fig = plt.figure(figsize=(PW/25.4, PH/25.4), dpi=120)
            ax = fig.add_axes([0,0,1,1]); header(ax,7); foot(ax)
            for name, x in [('END_L',15),('END_R',220)]:
                fw,fh=P[name]['flat_size']
                a=vax(fig,x,150,(-25,fw+25),(-25,fh+30),min(175/(fw+50),95/(fh+55)),f'{name} 把手居中；外表面朝读者')
                flatdraw(a,name)
                dimh(a,0,fw,-12,0,0,f'{fw:g}')
                dimv(a,0,fh,fw+12,fw,fw,f'{fh:g}')
                circle_table(ax,name,x,133,180,step=7)
            box(ax,15,20,390,35,[
                f'{part}：中心Y={W/2:g}/Z={Hb/2:g}；{panel_handle_row_note([h for h in _PANEL_HANDLES if h["part_id"]==part])}。'
                for part in sorted({h['part_id'] for h in _PANEL_HANDLES})
            ]+[
                '每侧4×Ø6.6（M6过孔），排距30；END_L展开X′=W−Y，END_R展开X′=Y，两者Y′=Z；把手实体/承载待供应商及实物核对。',
            ],title='端板把手安装要求',fs=FS_NOTE)
            save_page(pdf,fig)
        draw_customer_requirements(pdf)

# overlap report (layout PASS iff remaining==0)
ov = dict(_OV)
ov['dimension_remaining'] = ov.get('remaining', 0)
ov['page_checks'] = _PAGE_LAYOUT
ov['remaining'] += sum(len(p['issues']) for p in _PAGE_LAYOUT)
ov['pass'] = ov['remaining'] == 0
ov['bbox_count'] = len(_BB)
ov['stamp'] = _PDF_STAMP
ov['ver'] = VER
ov['pdf'] = str(out_pdf)
ov['pages'] = NPAGES
logs = ORDER / 'logs'; logs.mkdir(exist_ok=True)
(logs / 'bend_pdf_overlap.json').write_text(json.dumps(ov, indent=2, ensure_ascii=False))
(logs / 'bend_pdf_meta.json').write_text(json.dumps({
    'ver': VER, 'pdf': str(out_pdf), 'pages': NPAGES, 'stamp': _PDF_STAMP,
    'production_release': bool((JOB or {}).get('production_release', False)), 'rev': 'u_endplates_visual_001_2.8.45_t59u',
    'customer_requirement_pages': len(_REQ_PAGES),
    'customer_requirement_text_sha256': hashlib.sha256(JOB.get('customer_requirement_text', '').encode('utf-8')).hexdigest(),
    'dim_overlap': ov, 'pdf_layout_pass': ov['pass'],
}, indent=2, ensure_ascii=False))
if not ov['pass']:
    _candidate.unlink(missing_ok=True)
    raise SystemExit('PDF_LAYOUT: overlap/clipping detected; see logs/bend_pdf_overlap.json')
_candidate.replace(out_pdf)
print('PDF', out_pdf, 'pages', NPAGES, 'overlap', json.dumps(ov, ensure_ascii=False))

# The same golden engine also renders the one-box nest preview.
import ezdxf
from ezdxf.addons.drawing import RenderContext, Frontend
from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
from ezdxf.addons.drawing.config import Configuration, BackgroundPolicy, ColorPolicy
_nest = next((R / 'NEST').glob('*_1BOX.dxf'))
_doc = ezdxf.readfile(_nest)
_fig = plt.figure(figsize=(PW / 25.4, PH / 25.4), dpi=120)
_canvas = _fig.add_axes([0, 0, 1, 1])
_saved_pages, NPAGES = NPAGES, 1
header(_canvas, 1); foot(_canvas)
NPAGES = _saved_pages
_axes = _fig.add_axes([.03, .12, .94, .72])
Frontend(RenderContext(_doc), MatplotlibBackend(_axes), config=Configuration(background_policy=BackgroundPolicy.WHITE, color_policy=ColorPolicy.BLACK)).draw_layout(_doc.modelspace(), finalize=True)
_fig.set_size_inches(PW / 25.4, PH / 25.4)
_axes.set_position([.03, .12, .94, .72])
_axes.set_aspect('equal'); _axes.axis('off')
_fig.savefig(R / 'NEST' / f'{VER}_NEST_PREVIEW.pdf')
_fig.savefig(R / 'PREVIEW' / f'{VER}_NEST_PREVIEW.png')
plt.close(_fig)
