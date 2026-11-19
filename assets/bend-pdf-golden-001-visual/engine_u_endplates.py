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
from PIL import Image
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
matplotlib.rcParams['font.family'] = [FP.get_name(), 'DejaVu Sans']
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
_TOP4 = rep.get('top_fixings') or []
_BATTERY_SIDE=bool(JOB.get('battery_side_connection_review'))
if _BATTERY_SIDE and (not JOB.get('battery_lid_region_review') or _TOP4 or len(rep.get('holes') or [])!=2*(len(LONG_X)+len(SHORT_Y))):
    raise ValueError('battery side connection adapter requires zero roof corner holes and actual side connections matching the planned rows')
_TOP_SUPPORTS = bool(_TOP4) and all('TAB'+str(i+1) in P for i in range(len(_TOP4)))

def fixing_edge_coordinates(fixings, offset):
    return (sorted({round(h['formed'][0]+offset,8) for h in fixings}),
            sorted({round(h['formed'][1]+offset,8) for h in fixings}))

_FIX_X,_FIX_Y=fixing_edge_coordinates(_TOP4,g+t)

def panel_handle_row_note(holes):
    rows = []
    for z in sorted({h['point'][2] for h in holes}):
        ys = [h['point'][1] for h in holes if h['point'][2] == z]
        rows.append((max(ys)-min(ys), z))
    (narrow, nz), (wide, wz) = sorted(rows)
    return f'宽排{wide:g} Z{wz:g}{"在上" if wz>nz else "在下"}；窄排{narrow:g} Z{nz:g}{"在下" if wz>nz else "在上"}'

_PANEL_HANDLES = [h for h in _PANEL if h.get('purpose') == 'handle']
if JOB.get('compact_panel_review') and (_RECTS or _PANEL_HANDLES or any(h['part_id']!='U' for h in _PANEL)):
    raise ValueError('compact_panel_review only supports U front circular holes without panel handles or rectangles')
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
if STRUCTURE == 'u_l_t7u':
    _SIDE_TITLE='右视图（U围侧壁）'
    _SKIRT_NOTE='箱体无功能孔；功能开口在盖上'

if _TOP4:
    _END_SUMMARY = (('U围＋L，箱体无孔；盖顶承接结构未定' if STRUCTURE=='u_l_t7u' else 'END_L/END_R均无孔；仅盖顶4孔，螺钉承接结构未定') if not _TOP_SUPPORTS else '盖顶M4固定在角部支承片')
    _TOP_EXTRA = '盖顶四角M4；孔位直接标注'


if JOB.get('lid_pair_end_review'):
    _ep=lid_pair_end_side() if 'lid_pair_end_side' in globals() else _PANEL[0]['part_id']
    _END_SUMMARY=f'{_ep}：2×Ø{_PANEL[0]["diameter"]:g}，孔心高{_PANEL[0]["point"][2]:g}；对端无孔'
    _SKIRT_NOTE=f'侧孔上缘至盖裙下沿 {H-skirt-max(h["point"][2]+h["diameter"]/2 for h in _PANEL):g} mm'

if JOB.get('lid_two_circle_review'):
    if (STRUCTURE!='u_endplates' or len(JOB.get('lid_ports') or [])!=2 or len(HANDLE_CX)!=1 or
            _PANEL or _RECTS or len(_TOP4)!=4 or _TOP_SUPPORTS):
        raise ValueError('lid_two_circle_review requires two lid circles, one lid handle, four lid-only fixing holes')
    _END_SUMMARY=f'箱体无功能孔；盖顶{len(JOB["lid_ports"])}功能孔/{len(rep["handle_holes"])}把手孔/{len(_TOP4)}固定孔'

if JOB.get('dual_end_interfaces_review'):
    _END_SUMMARY='左端6圆孔；右端4圆孔＋2方口；无盖裙固定孔'
    _SKIRT_NOTE=f'右方口上缘至盖裙 {H-skirt-max(h["center"][2]+h["size_xy"][1]/2 for h in _RECTS):g} mm；首件待核'

if (JOB.get('battery_lid_edge_review') or JOB.get('battery_lid_region_review')):
    _END_SUMMARY='正常箱体，盖顶7圆孔＋2方口，无把手'
    _SKIRT_NOTE=('孔心距可开孔区；实际外边距另核' if JOB.get('battery_lid_region_review') else '孔心距实际盖外边，不以箱体投影边代替')

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
if _PANEL and not JOB.get('dual_end_interfaces_review') and not JOB.get('compact_panel_review') and not JOB.get('lid_pair_end_review'):
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
    ax.text(8, PH - 22, f'材料 {MATERIAL_CN}｜板厚 t={t:g} mm｜箱体 {L:g}×{W:g}×含盖高{H:g}｜盖外{OUTER_L:g}×{OUTER_W:g}｜内R{ri:g} K={K:.4f} BD={BD:.3f}(候选)｜每套{len(P)}件｜production_release={str(_pr).lower()}',
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
        rows += [(line, 'black') for line in wrap_text(ax, printable, FS_NOTE, 188 if (job.get('ordinary_side_fixings_review') or job.get('battery_lid_region_review')) else 390)]
    capacity=60 if (job.get('ordinary_side_fixings_review') or job.get('battery_lid_region_review')) else 30
    return [rows[i:i+capacity] for i in range(0, len(rows), capacity)]


def draw_customer_requirements(pdf):
    for i, rows in enumerate(_REQ_PAGES):
        fig = plt.figure(figsize=(PW/25.4, PH/25.4), dpi=120)
        ax = fig.add_axes([0, 0, 1, 1])
        header(ax, NPAGES-len(_REQ_PAGES)+1+i); foot(ax)
        if JOB.get('ordinary_side_fixings_review') or JOB.get('battery_lid_region_review'):
            box(ax,12,26,194,222,rows[:30],title=f'客户原文（{i+1}/{len(_REQ_PAGES)}）左栏→右栏',fs=FS_NOTE)
            box(ax,212,26,194,222,rows[30:],title='客户原文（续）',fs=FS_NOTE)
        else:
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
    if JOB.get('ordinary_local_dimensions_review'):
        fig.canvas.draw();renderer=fig.canvas.get_renderer()
        for local_ax in fig.axes:
            if not hasattr(local_ax,'_ld_panel'):continue
            x,y,w,h=local_ax._ld_panel;outside=[]
            for text in local_ax.texts:
                if not text.get_text().strip():continue
                bb=Text.get_window_extent(text,renderer);lo,hi=local_ax.transData.inverted().transform([[bb.x0,bb.y0],[bb.x1,bb.y1]])
                if lo[0]<-3 or lo[1]<-3 or hi[0]>w+3 or hi[1]>h+3:outside.append(text.get_text())
            for line in local_ax.lines:
                if line.get_clip_on():continue
                xs,ys=line.get_xdata(),line.get_ydata()
                if len(xs) and (min(xs)<-3 or max(xs)>w+3 or min(ys)<-3 or max(ys)>h+3):outside.append('dimension extension outside its view panel')
            _LD_RECORDS.append(dict(kind='panel_boundary_check',panel=[x,y,w,h],outside=outside))
            if outside:raise ValueError(('LOCAL_PANEL_OVERFLOW',outside))
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
        label=(bend['id']+f' 背向读者90° Ri{ri:g}') if (_TOP4 or _BATTERY_SIDE) else bend['id']
        ax.text(mx+dx, my+dy, label, fontsize=FS_DIM, color=REDC, rotation=90 if (_TOP4 or _BATTERY_SIDE) and abs(x1-x2)<1e-4 else 0, ha='center' if (_TOP4 or _BATTERY_SIDE) else 'left', va='center' if (_TOP4 or _BATTERY_SIDE) else 'baseline')
    if show_holes:
        for c in P[name].get('flat_circles', []):
            # [x,y,d] or [x,y,r]?
            if len(c) >= 3:
                d = c[2] if c[2] > 2 else c[2] * 2
                # report uses diameter in flat_circles typically
                ax.add_patch(Circle((c[0], c[1]), (c[2] / 2 if c[2] > 2 else c[2]), fill=False, ec=REDC, lw=0.45))

LOL=L+2*(g+t); LOW=W+2*(g+t); OH=g+t

def lid_pair_end_side():
    parts={h['part_id'] for h in _PANEL}
    corners=(len(_FIX_X)==len(_FIX_Y)==2 and
             all(abs(a-b)<1e-6 for a,b in zip(_FIX_X,[4.5,LOL-4.5])) and
             all(abs(a-b)<1e-6 for a,b in zip(_FIX_Y,[4.5,LOW-4.5])))
    if (STRUCTURE!='u_endplates' or len(parts)!=1 or not parts.issubset({'END_L','END_R'}) or
            len(_PANEL)!=2 or _RECTS or JOB.get('lid_ports') or len(HANDLE_CX)!=2 or
            (JOB.get('handles') or {}).get('rotations')!=[90,270] or len(_TOP4)!=4 or _TOP_SUPPORTS or
            not corners or any(abs(h.get('lid_clearance',4.5)-4.5)>1e-6 for h in _TOP4)):
        raise ValueError('lid_pair_end_review requires two end circles, two opposing lid handles and four 4.5-inset lid holes')
    return next(iter(parts))


def draw_lid_pair_end_overview():
    part=lid_pair_end_side();left=part=='END_L';side='左' if left else '右'
    fig=plt.figure(figsize=(PW/25.4,PH/25.4),dpi=120)
    ax=fig.add_axes([0,0,1,1]);header(ax,1);foot(ax)
    box(ax,12,210,115,46,[f'订单 {JOB.get("order_id","")} / 序号{VER.split("-")[-2]}',f'{MATERIAL_CN} t={t:g}；数量{JOB.get("quantity",1)}',f'箱体{L:g}×{W:g}；含盖高{H:g}',f'{side}端2×Ø{_PANEL[0]["diameter"]:g}；盖顶双把手'],title='本单审核信息')
    im=fig.add_axes([12/PW,119/PH,115/PW,84/PH]);im.imshow(np.asarray(Image.open(JOB['customer_image'])),interpolation='none',resample=False);im.axis('off');im.set_title('客户原图（原样）',fontsize=FS_TITLE,loc='left')
    box(ax,12,91,115,27,[JOB.get('customer_image_note',''), '孔面和把手坐标采用本单文字。'],title='来源采用依据',fs=FS_NOTE)
    scale=min(.26,260/(L+130),100/(W+180))
    a=vax(fig,141,132,(-60,L+70),(-75,W+105),scale,'盖顶俯视：从上看；位置尺寸从实际盖边量')
    view(a,'ASSEMBLY','top',lambda u,v:(u,v),hidden=False)
    centers=sorted(HANDLE_CX)
    for cx in centers:a.plot(cx,HANDLE_CY,'+',color=BLU,ms=5)
    dimh(a,-OH,L+OH,W+78,W+OH,W+OH,f'{LOL:g} 盖外长')
    dimv(a,-OH,W+OH,-38,-OH,-OH,f'{LOW:g} 盖外宽')
    dimh(a,-OH,centers[0],-22,-OH,HANDLE_CY,f'{centers[0]+OH:g}')
    dimh(a,centers[-1],L+OH,-22,HANDLE_CY,-OH,f'{L+OH-centers[-1]:g}')
    dimh(a,centers[0],centers[-1],-56,HANDLE_CY,HANDLE_CY,f'把手心距{centers[-1]-centers[0]:g}')
    dimv(a,-OH,HANDLE_CY,L+37,centers[-1],centers[-1],f'{HANDLE_CY+OH:g}')
    for i,cx in enumerate(centers):
        a.annotate(f'把手{i+1} 各4×Ø6.6',(cx,HANDLE_CY),(cx+(90 if i==0 else -90),W+28),fontsize=FS_NOTE,color=BLU,ha='left' if i==0 else 'right',arrowprops=dict(arrowstyle='-',lw=.4,color=BLU))
    hh=[h for h in rep['handle_holes'] if h['x']<L/2]
    for rx in sorted({h['x'] for h in hh}):
        ys=sorted(h['y'] for h in hh if abs(h['x']-rx)<1e-6)
        dimv(a,ys[0],ys[-1],rx+(-24 if rx<centers[0] else 24),rx,rx,f'{ys[-1]-ys[0]:g}')
    rows=sorted({h['x'] for h in hh});dimh(a,rows[0],rows[-1],HANDLE_CY-65,HANDLE_CY-31,HANDLE_CY-42.5,f'{rows[-1]-rows[0]:g}')
    # Enlarged real corner: local translation only, no invented inset.
    inset=_FIX_X[0];ca=vax(fig,147,88,(-7,25),(-7,25),.65,'四角相同：4×Ø4.5')
    ca.plot([0,0,18],[18,0,0],color='k',lw=.7);ca.add_patch(Circle((inset,inset),2.25,fill=False,ec=REDC))
    dimh(ca,0,inset,14,0,inset,f'{inset:g}');dimv(ca,0,inset,14,inset,0,f'{inset:g}')
    ax.text(143,255,'双把手85/62/30，90°/270°相向；四角4×Ø4.5，孔心距盖边4.5。',fontsize=FS_NOTE,color=BLU)
    ax.text(143,249,'角孔边距2.25 / 折弯切线净距约0.45；承接结构及长盖刚度首件HOLD。',fontsize=FS_NOTE,color=REDC)
    # Front view preserves the actual long body and lid extents.
    sf=min(.205,195/(L+100),61/(H+75))
    fa=vax(fig,12,24,(-45,L+55),(-35,H+50),sf,'正视图：箱体长不含盖；高度含盖')
    view(fa,'ASSEMBLY','front',lambda u,v:(v,-u))
    dimh(fa,0,L,-22,0,0,f'{L:g} 箱体外长')
    dimv(fa,0,H,-30,0,0,f'{H:g} 含盖高')
    dimv(fa,0,Hb,L+30,L,L,f'{Hb:g} 箱体高')
    # Explicit exterior end view. Left is viewed along +X, never reuse right projection.
    se=min(.42,145/(W+100),112/(H+75))
    ea=vax(fig,224,14,(-45,W+55),(-40,H+35),se,f'{side}视图：从{side}端外侧向内看，孔在{part}')
    label='left' if left else 'right'; transform=(lambda u,v:(W+v,-u)) if left else (lambda u,v:(-v,u))
    view(ea,'ASSEMBLY',label,transform,hidden=False)
    centers_side=sorted((W-h['point'][1] if left else h['point'][1],h['point'][2],h['diameter']) for h in _PANEL)
    for i,(x,z,d) in enumerate(centers_side):
        ea.add_patch(Circle((x,z),d/2,fill=False,ec=REDC,lw=.8))
        dimh(ea,x,W,35-22*i,z,0,f'距右{W-x:g}')
    x1,z,d=centers_side[0];x2=centers_side[-1][0]
    dimh(ea,x1,x2,H+16,z,z,f'孔心距{x2-x1:g}')
    dimv(ea,0,z,-29,x1,x1,f'孔心高{z:g}')
    dimv(ea,z,H,W+31,x2,x2,f'距顶{H-z:g}')
    dimh(ea,0,W,-23,0,0,f'{W:g} 箱体外宽')
    ea.annotate(f'2×Ø{d:g}',(x1,z),(W*.35,H*.48),fontsize=FS_NOTE,color=REDC,arrowprops=dict(arrowstyle='-',lw=.5,color=REDC))
    path=render_assy_iso_png(R/'PREVIEW'/f'{VER}_ASSEMBLY_iso.png',list(P),exploded=False)
    render_assy_iso_png(R/'PREVIEW'/f'{VER}_EXPLODED_iso.png',list(P),exploded=True)
    ia=fig.add_axes([370/PW,30/PH,40/PW,65/PH]);ia.imshow(plt.imread(path));ia.axis('off');ia.set_title('实际装配',fontsize=FS_NOTE)
    return fig


def draw_lid_pair_end_parts(pdf):
    part=lid_pair_end_side()
    fig=plt.figure(figsize=(PW/25.4,PH/25.4),dpi=120);ax=fig.add_axes([0,0,1,1]);header(ax,3);foot(ax)
    for name,px in [('END_L',12),('END_R',217)]:
        fx,fy=P[name]['flat_size'];a=vax(fig,px,96,(-35,fx+40),(-35,fy+45),min(.57,185/(fx+75),138/(fy+80)),f'{name} 外侧展开，零折；{fx:g}×{fy:g}')
        flatdraw(a,name);dimh(a,0,fx,-21,0,0,f'{fx:g}');dimv(a,0,fy,fx+25,fx,fx,f'{fy:g}')
        cc=sorted(P[name]['flat_circles'])
        for i,(xx,yy,dd) in enumerate(cc):
            a.annotate(f'P{i+1} Ø{dd:g}',(xx,yy),(xx+(22 if xx<fx/2 else -22),yy-45),fontsize=FS_NOTE,color=REDC,ha='left' if xx<fx/2 else 'right',arrowprops=dict(arrowstyle='-',lw=.4,color=REDC))
            dimh(a,xx,fx,35-20*i,yy,0,f'距右{fx-xx:g}');dimv(a,0,yy,fx/2,xx,xx,f'{yy:g}') if i==0 else None
        if cc:
            dimh(a,cc[0][0],cc[-1][0],fy+21,cc[0][1],cc[-1][1],f'孔心距{cc[-1][0]-cc[0][0]:g}')
            dimv(a,cc[0][1],fy,-22,cc[0][0],0,f'{fy-cc[0][1]:g}')
        else:a.text(fx/2,fy/2,'无孔',fontsize=FS_TITLE,ha='center',color=BLU)
        path=render_assy_iso_png(R/'PREVIEW'/f'{VER}_{name}_iso.png',[name])
        ia=fig.add_axes([(px+128)/PW,21/PH,64/PW,63/PH]);ia.imshow(plt.imread(path));ia.axis('off')
        box(ax,px,22,125,66,[
            f'{name} 外表面朝读者；厚{t:g}，数量1。',
            ("X′=W−Y；Y′=Z；Z′=−X" if name=='END_L' else "X′=Y；Y′=Z；Z′=X−L"),
            '平坯孔心：距左/右，距下/上；mm',
        ]+[f'P{i+1} Ø{dd:g}: {xx:g}/{fx-xx:g}, {yy:g}/{fy-yy:g}' for i,(xx,yy,dd) in enumerate(cc)]+[
            '零折；底角随U外圆；焊接拼缝0。',
        ],title=name+' 尺寸与处理面',fs=FS_NOTE)
    save_page(pdf,fig)


def check_dual_end_interfaces():
    cc_left=[h for h in _PANEL if h['part_id']=='END_L']
    cc_right=[h for h in _PANEL if h['part_id']=='END_R']
    zl=sorted({h['point'][2] for h in cc_left})
    if (STRUCTURE!='u_endplates' or len(_RECTS)!=2 or any(r['part_id']!='END_R' or r['size_xy']!=[26.5,18] for r in _RECTS) or
            len(cc_right)!=4 or any(abs(h['diameter']-4.2)>1e-6 for h in cc_right) or len(cc_left)!=6 or
            len({h['point'][1] for h in cc_left})!=2 or len(zl)!=3 or
            len({h['point'][2] for h in cc_right}|{r['center'][2] for r in _RECTS})!=1 or
            len(HANDLE_CX)!=1 or (JOB.get('handles') or {}).get('rotations')!=[270] or
            len(_TOP4)!=4 or _TOP_SUPPORTS or JOB.get('lid_ports')):
        raise ValueError('dual_end_interfaces_review requires right two26.5x18/four4.2, left two columns/three rows, one270 lid handle and four top fixings')
    expected=[[4.5,4.5],[12.5,12.5],[4.2,4.5]]
    if any(sorted(h['diameter'] for h in cc_left if h['point'][2]==z)!=ds for z,ds in zip(zl,expected)):
        raise ValueError('dual_end_interfaces_review left diameter rows do not match the verified pattern')


def dual_end_features(part):
    local=lambda yy:W-yy if part=='END_L' else yy
    cc=sorted((local(h['point'][1]),h['point'][2],h['diameter']) for h in _PANEL if h['part_id']==part)
    rr=sorted((local(h['center'][1]),h['center'][2],*h['size_xy']) for h in _RECTS if h['part_id']==part)
    return cc,rr


def draw_dual_end_overview():
    check_dual_end_interfaces()
    fig=plt.figure(figsize=(PW/25.4,PH/25.4),dpi=120);ax=fig.add_axes([0,0,1,1]);header(ax,1);foot(ax)
    ax.text(12,257,f'订单{JOB.get("order_id","")} / {VER.split("-")[-2]} / {MATERIAL_CN} t{t:g} / {JOB.get("quantity",1)}套',fontsize=FS_NOTE,color=NAVY)
    ia=fig.add_axes([12/PW,161/PH,104/PW,84/PH]);ia.imshow(np.asarray(Image.open(JOB['customer_image'])),interpolation='none',resample=False);ia.axis('off');ia.set_title('客户原图（原样）',fontsize=FS_TITLE,loc='left')
    fa=vax(fig,12,87,(-45,L+55),(-40,H+50),.25,'正视图：长宽不含盖，高度含盖')
    view(fa,'ASSEMBLY','front',lambda u,v:(v,-u),hidden=False)
    dimh(fa,0,L,-22,0,0,f'{L:g} 箱体外长');dimv(fa,0,H,-29,0,0,f'{H:g} 含盖高')
    dimv(fa,0,Hb,L+27,L,L,f'{Hb:g} 箱体高')
    a=vax(fig,12,17,(-40,L+60),(-35,W+50),.20,'盖顶俯视：以实际盖左下为尺寸基准')
    view(a,'LID','top',lambda u,v:(u,v),hidden=False)
    dimh(a,-OH,L+OH,-22,-OH,-OH,f'{LOL:g} 盖外长');dimv(a,-OH,W+OH,-24,-OH,-OH,f'{LOW:g} 盖外宽')
    cx=HANDLE_CX[0];cy=HANDLE_CY;a.plot(cx,cy,'+',color=BLU,ms=5)
    dimh(a,-OH,cx,51,-OH,cy,f'{cx+OH:g}');dimv(a,-OH,cy,cx+72,cx,cx,f'{cy+OH:g}')
    ax.text(12,79,f'方口至盖裙{H-skirt-max(h["center"][2]+h["size_xy"][1]/2 for h in _RECTS):g}mm；箱体螺钉承接未定HOLD',fontsize=FS_NOTE,color=REDC)
    ha=vax(fig,145,18,(-25,65),(-65,65),.44,'把手270°：4×Ø6.6')
    hh=rep['handle_holes'];x0=min(h['x'] for h in hh)
    for h in hh:ha.add_patch(Circle((h['x']-x0,h['y']-cy),h['d']/2,fill=False,ec=BLU))
    dimv(ha,-42.5,42.5,-15,0,0,'85');dimv(ha,-31,31,45,30,30,'62');dimh(ha,0,30,-52,-42.5,-31,'30')
    inset=_FIX_X[0];cd=_TOP4[0]['lid_clearance']
    ca=vax(fig,167,101,(-4,31),(-4,31),1.0,f'盖顶四角同形：4×Ø{cd:g}')
    ca.plot([0,0,27],[27,0,0],color='k',lw=.7);ca.add_patch(Circle((inset,inset),cd/2,fill=False,ec=REDC))
    dimh(ca,0,inset,25,0,inset,f'{inset:g}');dimv(ca,0,inset,25,inset,0,f'{inset:g}')
    for part,py in [('END_R',140),('END_L',17)]:
        right=part=='END_R';ea=vax(fig,220,py,(-45,W+70),(-40,H+45),.44,('右端外视：2个26.5×18，4个Ø4.2' if right else '左端外视：全部6孔，按实际孔径'))
        if right:view(ea,part,'right',lambda u,v:(-v,u),hidden=False)
        else:view(ea,part,'left',lambda u,v:(W+v,-u),hidden=False)
        cc,rr=dual_end_features(part)
        dimh(ea,0,W,-25,0,0,f'{W:g} 箱体外宽')
        ea.axhline(H-skirt,color=REDC,ls=':',lw=.45)
        if right:
            z=cc[0][1]
            for i,(xx,zz,dd) in enumerate(cc):dimh(ea,0,xx,65-17*i,0,zz,f'{xx:g}')
            for i,(xx,zz,ww,hh) in enumerate(rr):
                dimh(ea,0,xx,110-18*i,0,zz,f'心{xx:g}')
                dimh(ea,xx-ww/2,xx+ww/2,178,zz+hh/2,zz+hh/2,f'{ww:g}')
            xx,zz,ww,hh=rr[-1];dimv(ea,zz-hh/2,zz+hh/2,xx+ww/2+21,xx+ww/2,xx+ww/2,f'{hh:g}')
            dimv(ea,0,z,-28,0,0,f'孔心高{z:g}')
            ea.annotate(f'{len(cc)}×Ø{cc[0][2]:g}',(cc[-1][0],z),(W+18,105),fontsize=FS_NOTE,color=REDC,arrowprops=dict(arrowstyle='-',color=REDC,lw=.4))
        else:
            xs=sorted({h[0] for h in cc});zs=sorted({h[1] for h in cc})
            for i,xx in enumerate(xs):dimh(ea,0,xx,50-22*i,0,zs[0],f'{xx:g}')
            for i,zz in enumerate(zs):dimv(ea,0,zz,W+20+18*i,0,0,f'{zz:g}')
            for i,(z0,z1) in enumerate(zip(zs,zs[1:])):dimv(ea,z0,z1,W/2+(-11 if i==0 else 11),xs[0],xs[-1],f'{z1-z0:g}')
            large=[q for q in cc if abs(q[2]-12.5)<1e-6]
            for k,(xx,zz,dd) in enumerate(large):
                ea.annotate('2×Ø12.5' if k==0 else '',(xx,zz),(W/2,98),fontsize=FS_NOTE,color=REDC,ha='center',arrowprops=dict(arrowstyle='-',color=REDC,lw=.4))
            low=[q for q in cc if q[1]==zs[0]]
            for k,(xx,zz,dd) in enumerate(low):ea.annotate('2×Ø4.5 下排' if k==0 else '',(xx,zz),(W/2,75),fontsize=FS_NOTE,color=REDC,ha='center',arrowprops=dict(arrowstyle='-',color=REDC,lw=.4))
            for xx,zz,dd in [q for q in cc if q[1]==zs[-1]]:
                ea.annotate(f'Ø{dd:g}',(xx,zz),(xx+(-20 if xx<W/2 else -4),184),fontsize=FS_NOTE,color=REDC,arrowprops=dict(arrowstyle='-',color=REDC,lw=.4))
    render_assy_iso_png(R/'PREVIEW'/f'{VER}_ASSEMBLY_iso.png',list(P));render_assy_iso_png(R/'PREVIEW'/f'{VER}_EXPLODED_iso.png',list(P),exploded=True)
    return fig


def draw_dual_end_parts(pdf):
    check_dual_end_interfaces()
    fig=plt.figure(figsize=(PW/25.4,PH/25.4),dpi=120);ax=fig.add_axes([0,0,1,1]);header(ax,3);foot(ax)
    for part,px in [('END_L',12),('END_R',217)]:
        fx,fy=P[part]['flat_size'];ea=vax(fig,px,125,(-40,fx+45),(-35,fy+45),.48,f'{part} 实际CUT外视展开；零折')
        flatdraw(ea,part);dimh(ea,0,fx,-20,0,0,f'{fx:g}');dimv(ea,0,fy,fx+22,fx,fx,f'{fy:g}')
        cc=sorted(P[part]['flat_circles']);rr=sorted(P[part].get('flat_rectangles') or [])
        for i,(xx,yy,dd) in enumerate(cc,1):
            dx=-17 if xx<fx/2 else 17;middle=sorted({q[1] for q in cc})[len({q[1] for q in cc})//2];dy=15 if part=='END_R' else (-15 if yy<middle else (15 if yy>middle else 0))
            ea.annotate(f'F{i:02}',(xx,yy),(xx+dx,yy+dy),fontsize=FS_NOTE,color=BLU,ha='right' if dx<0 else 'left',arrowprops=dict(arrowstyle='-',color=BLU,lw=.35))
        for i,(x0,y0,x1,y1) in enumerate(rr,1):
            ea.text((x0+x1)/2,y0-18,f'R{i}',fontsize=FS_NOTE,color=REDC,ha='center')
        lines=['X距左/右，Y距下/上；孔心mm。']+[f'F{i:02} Ø{dd:g} X{xx:g}/{fx-xx:g} Y{yy:g}/{fy-yy:g}' for i,(xx,yy,dd) in enumerate(cc,1)]
        for i,(x0,y0,x1,y1) in enumerate(rr,1):
            cx=(x0+x1)/2;cy=(y0+y1)/2
            lines += [f'R{i} {x1-x0:g}×{y1-y0:g} 心X{cx:g}/{fx-cx:g} Y{cy:g}/{fy-cy:g}',f'R{i} 边界X{x0:g}～{x1:g}；Y{y0:g}～{y1:g}']
        lines += [("外侧映射X′=W−Y，Y′=Z" if part=='END_L' else "外侧映射X′=Y，Y′=Z"),'孔径按输入保留；端板无新增盖裙固定孔。']
        box(ax,px,18,188,103,lines,title=part+' 全部圆孔/方口双向尺寸',fs=FS_NOTE)
        path=render_assy_iso_png(R/'PREVIEW'/f'{VER}_{part}_iso.png',[part]);ia=fig.add_axes([(px+126)/PW,237/PH,60/PW,23/PH]);ia.imshow(plt.imread(path));ia.axis('off')
    save_page(pdf,fig)



def battery_lid_edge_items():
    if (STRUCTURE!='u_endplates' or HANDLE_CX or _PANEL or _RECTS or len(JOB.get('lid_ports') or [])!=7 or
            len(JOB.get('lid_rectangles') or [])!=2 or len(_TOP4)!=(0 if _BATTERY_SIDE else 4) or _TOP_SUPPORTS):
        raise ValueError('battery_lid_edge_review requires seven roof circles, two roof rectangles, no handle, verified side or top fixing coordinates')
    datum=rep['lid_opening_region_origin'] if JOB.get('battery_lid_region_review') else rep['lid_edge_datum'];items=[]
    for i,h in enumerate(JOB['lid_ports'],1):items.append(dict(id='C'+str(i),type='circle',x=h['x']-datum[0],y=h['y']-datum[1],d=h['d']))
    for h in JOB['lid_rectangles']:items.append(dict(id=h['id'],type='rect',x=h['center'][0]-datum[0],y=h['center'][1]-datum[1],w=h['size'][0],h=h['size'][1]))
    if sorted(h['d'] for h in items if h['type']=='circle')!=[11,11,16,20,20,20,22]:
        raise ValueError('battery_lid_edge_review circle families do not match the verified layout')
    return datum,items



def draw_battery_lid_edge_overview():
    datum,items=battery_lid_edge_items();cl=L+2*OH;cw=W+2*OH
    region=bool(JOB.get('battery_lid_region_review'));ex=rep['lid_edge_datum'][0]-datum[0];ey=rep['lid_edge_datum'][1]-datum[1]
    fig=plt.figure(figsize=(PW/25.4,PH/25.4),dpi=120);ax=fig.add_axes([0,0,1,1]);header(ax,1);foot(ax)
    ax.text(12,257,f'订单{JOB.get("order_id","")} / {VER.split("-")[-2]} / 201不锈钢 t{t:g} / {JOB.get("quantity",1)}套',fontsize=FS_NOTE,color=NAVY)
    ia=fig.add_axes([12/PW,138/PH,155/PW,107/PH]);ia.imshow(np.asarray(Image.open(JOB['customer_image'])),interpolation='none',resample=False);ia.axis('off');ia.set_title('客户原图（原样）',fontsize=FS_TITLE,loc='left')
    ax.text(12,129,f'箱体{L:g}×{W:g}×含盖高{H:g}；201/t{t:g}；无把手',fontsize=FS_NOTE,color=BLU)
    if region:ax.text(12,29,f'源JSON盒高不含盖；本单制造含盖高{H:g}沿用约定',fontsize=FS_NOTE,color=BLU)
    ax.text(12,22,(f'盖裙侧面{len(rep["holes"])}处连接；1mm板攻M4及Ri/K待首件' if _BATTERY_SIDE else 'HOLD：四角螺钉承接结构未设计；Ri/K待首件'),fontsize=FS_NOTE,color=REDC)
    for name,px,xx,title,fn in [('front',12,L,'正视：长不含盖',lambda u,v:(v,-u)),('right',112,W,'右视：宽不含盖',lambda u,v:(-v,u))]:
        ea=vax(fig,px,37,(-40,xx+40),(-40,H+45),.22,title)
        view(ea,'ASSEMBLY',name,fn,hidden=False);dimh(ea,0,xx,-23,0,0,f'{xx:g} 箱体');dimv(ea,0,H,-25,0,0,f'{H:g} 含盖')
        if _BATTERY_SIDE and name=='front':
            for lane,x in enumerate(LONG_X):dimh(ea,0,x,100-25*lane,0,ZH,f'{x:g}')

            for x0,x1 in zip(LONG_X,LONG_X[1:]):dimh(ea,x0,x1,25,ZH,ZH,f'{x1-x0:g}')
            dimv(ea,0,ZH,-45,LONG_X[0],LONG_X[0],f'{ZH:g} 孔高')
            ea.text(L/2,175,f'盖Ø4.5 / 体Ø3.3攻M4\n前后各{len(LONG_X)}处同轴连接',fontsize=FS_NOTE,color=REDC,ha='center')
    ax.text(195,252,(f'孔心X/Y从可开孔区O量；O世界坐标{datum[0]:g}/{datum[1]:g}' if region else '孔心X/Y＝距实际盖左/下；不再加3mm或盖外伸'),fontsize=FS_NOTE,color=REDC)
    ax.text(195,245,(f'实际盖边距＝图示X/Y＋{-ex:g}；盖外{cl:g}×{cw:g}' if region else f'盖外{cl:g}×{cw:g}另列；箱体{L:g}×{W:g}不含盖'),fontsize=FS_NOTE,color=BLU)
    a=vax(fig,195,45,(-85,cl+75),(-100,cw+110),.42,('盖顶俯视：O为可开孔区左下；绿色框为源可开孔区' if region else '盖顶俯视：尺寸原点O为盖板实际左下外边'))
    view(a,'LID','top',lambda u,v:(u-datum[0],v-datum[1]),hidden=False)
    if region:
        a.add_patch(Rectangle((0,0),*rep['lid_opening_region_size'],fill=False,ec=GRN,lw=.6,ls=':'))
    a.plot(0,0,'+',color=BLU,ms=5);a.text(-5,-8,'O',fontsize=FS_NOTE,color=BLU)
    dimh(a,ex,ex+cl,-90,ey,ey,f'{cl:g} 盖外长');dimv(a,ey,ey+cw,cl+65,ex+cl,ex+cl,f'{cw:g} 盖外宽')
    upper=sorted([h for h in items if h.get('d')==20],key=lambda q:q['x'])
    for i,h in enumerate(upper):dimh(a,0,h['x'],cw+27+25*i,0,h['y'],f'{h["x"]:g}')
    ytop=upper[0]['y'];dimv(a,0,ytop,cl+20,upper[-1]['x'],upper[-1]['x'],f'{ytop:g}')
    for i,h in enumerate(upper):a.annotate('3×Ø20' if i==0 else '',(h['x'],h['y']),(128,cw-19),fontsize=FS_NOTE,color=REDC,arrowprops=dict(arrowstyle='-',color=REDC,lw=.4))
    middle=sorted([h for h in items if h.get('d')==11],key=lambda q:q['x'])
    for i,h in enumerate(middle):
        dimh(a,0,h['x'],-15-25*i,0,h['y'],f'{h["x"]:g}')
        a.annotate('2×Ø11' if i==0 else '',(h['x'],h['y']),(143,112),fontsize=FS_NOTE,color=REDC,arrowprops=dict(arrowstyle='-',color=REDC,lw=.4))
    dimv(a,0,middle[0]['y'],cl+42,middle[-1]['x'],middle[-1]['x'],f'{middle[0]["y"]:g}')
    lower=sorted([h for h in items if h['y']<min(q['y'] for q in middle)],key=lambda q:q['x'])
    xs=[0]+[h['x'] for h in lower]+[rep['lid_opening_region_size'][0] if region else cl]
    for x0,x1 in zip(xs,xs[1:]):dimh(a,x0,x1,-65,0,0,f'{x1-x0:g}')
    for i,yy in enumerate(sorted({h['y'] for h in lower})):dimv(a,0,yy,-60+20*i,0,0,f'{yy:g}')
    rr=0
    for h in lower:
        if h['type']=='rect':
            ww,hh=h['w'],h['h'];xx,yy=h['x'],h['y'];x0=xx-ww/2;x1=xx+ww/2;y0=yy-hh/2;y1=yy+hh/2
            dimh(a,x0,x1,y1+10,y1,y1,f'{ww:g}');dimv(a,y0,y1,x1+10,x1,x1,f'{hh:g}')
            a.annotate(f'{ww:g}×{hh:g}\nX{xx:g} Y{yy:g}',(xx,yy),(76 if rr==0 else 166,5),fontsize=FS_NOTE,color=REDC,arrowprops=dict(arrowstyle='-',color=REDC,lw=.4));rr+=1
        else:
            xx,yy=h['x'],h['y'];target=(6,80) if h['d']==22 else (237,78)
            a.annotate(f'Ø{h["d"]:g}\nX{xx:g} Y{yy:g}',(xx,yy),target,fontsize=FS_NOTE,color=REDC,arrowprops=dict(arrowstyle='-',color=REDC,lw=.4))
    if region:
        oa=vax(fig,270,228,(-5,25),(-5,25),.7,'基准O放大')
        oa.plot([0,0,20],[20,0,0],color='k',lw=.7);oa.plot(-ex,-ey,'+',color=GRN,ms=5)
        dimh(oa,0,-ex,20,0,-ey,f'{-ex:g}');dimv(oa,0,-ey,20,-ex,0,f'{-ey:g}')
        oa.text(-ex+2,-ey+2,'O',fontsize=FS_NOTE,color=GRN)
    if not _BATTERY_SIDE:
        inset=_FIX_X[0];ca=vax(fig,350,232,(-4,28),(-4,28),.60,'角孔')
        ca.plot([0,0,25],[25,0,0],color='k',lw=.7);ca.add_patch(Circle((inset,inset),2.25,fill=False,ec=REDC));dimh(ca,0,inset,24,0,inset,f'{inset:g}');dimv(ca,0,inset,24,inset,0,f'{inset:g}')
        ax.text(295,229,f'4×Ø4.5（加工候选），盖边距{inset:g}',fontsize=FS_NOTE,color=BLU)
    path=render_assy_iso_png(R/'PREVIEW'/f'{VER}_ASSEMBLY_iso.png',list(P));render_assy_iso_png(R/'PREVIEW'/f'{VER}_EXPLODED_iso.png',list(P),exploded=True)
    return fig




def ordinary_new_page(page):
    fig=plt.figure(figsize=(PW/25.4,PH/25.4),dpi=120);ax=fig.add_axes([0,0,1,1]);header(ax,page);foot(ax);return fig,ax

def ordinary_number(x):
    return f'{x:.2f}'.rstrip('0').rstrip('.')

def ordinary_iso(fig,name,x,y,w,h):
    path=render_assy_iso_png(R/'PREVIEW'/f'{VER}_{name}_ordinary_iso.png',list(P) if name=='ASSEMBLY' else [name])
    a=fig.add_axes([x/PW,y/PH,w/PW,h/PH]);a.imshow(plt.imread(path));a.axis('off');a.set_title('实际装配轴测' if name=='ASSEMBLY' else name+' 实际成形轴测',fontsize=FS_NOTE,loc='left')

def ordinary_feature_rows():
    rows=[f'订单{JOB.get("order_id","")}；每套{len(P)}件；{MATERIAL_CN} t{t:g}',f'箱体外{L:g}×{W:g}；含盖总高{H:g}',f'盖外{L+2*OH:g}×{W+2*OH:g}；四边裙高{skirt:g}',f'四边{len(rep["holes"])}对M4，箱Ø3.3攻丝、盖裙Ø4.5',f'长侧X：'+ '/'.join(ordinary_number(v) for v in LONG_X),f'短侧Y：'+ '/'.join(ordinary_number(v) for v in SHORT_Y),f'各固定孔心距箱底Z{ZH:g}；盖顶角孔取消']
    for i,h in enumerate(JOB.get('panel_holes') or [],1):
        x,y,z=h['point'];face='左端外视' if h['part_id']=='END_L' else '右端外视' if h['part_id']=='END_R' else '前板外视';s=W-y if h['part_id']=='END_L' else y if h['part_id']=='END_R' else x
        rows.append(f'{face} Ø{h["diameter"]:g}：距左{ordinary_number(s)}，距底{ordinary_number(z)}')
    for i,h in enumerate(JOB.get('lid_ports') or [],1):rows.append(f'盖P{i} Ø{h["d"]:g}：实际左{ordinary_number(h["x"]+OH)}、下{ordinary_number(h["y"]+OH)}')
    for i,h in enumerate(JOB.get('lid_rectangles') or [],1):rows.append(f'盖R{i} {h["size"][0]:g}×{h["size"][1]:g}：中心左{ordinary_number(h["center"][0]+OH)}、下{ordinary_number(h["center"][1]+OH)}')
    for h in JOB.get('rect_cutouts') or []:
        x,y,z=h['center'];s=W-y if h['part_id']=='END_L' else y if h['part_id']=='END_R' else x
        rows.append(f'{h["part_id"]}方口{h["size_xy"][0]:g}×{h["size_xy"][1]:g}：外视左{ordinary_number(s)}、底{ordinary_number(z)}')
    for i,cx in enumerate(HANDLE_CX):rows.append(f'把手{i+1}：实际盖左{ordinary_number(cx+OH)}、下{ordinary_number(HANDLE_CYS[i]+OH)}；{(JOB.get("handles") or {}).get("rotations",[])[i] if (JOB.get("handles") or {}).get("rotations") else "按原版"}°')
    if HANDLE_CX:rows.append('每把手4×Ø6.6，宽85/窄62/排距30；原位置不改')
    if rep.get('lid_opening_region_origin'):
        oo=rep['lid_opening_region_origin'];rows.append(f'原图可开孔区O世界{oo[0]:g}/{oo[1]:g}；本页另列实际盖边')
    rows += ['功能孔/把手/主体外形沿用原版，仅修正盖体固定','无承接的顶角孔已取消；没有新增焊片','Ri/K/刀模/薄板攻丝及承载须首件确认']
    return rows

def ordinary_overview(pdf):
    fig,ax=ordinary_new_page(1)
    ip=Path(JOB['customer_image']);ia=fig.add_axes([12/PW,191/PH,112/PW,62/PH]);ia.imshow(np.asarray(Image.open(ip)));ia.axis('off');ia.set_title('客户原图（原样）',fontsize=FS_NOTE,loc='left')
    ordinary_iso(fig,'ASSEMBLY',132,191,105,62)
    for label,px,py,ww,hh,title,fn in [('front',12,99,L,H,'正视：箱体长/含盖高',lambda u,v:(v,-u)),('right',129,99,W,H,'右端外视：宽/高',lambda u,v:(-v,u)),('left',12,20,W,H,'左端外视：宽/高',lambda u,v:(W+v,-u)),('top',129,20,L,W,'俯视：箱体长宽不含盖',lambda u,v:(u,v))]:
        a=vax(fig,px,py,(-40,ww+45),(-40,hh+45),min(100/(ww+85),62/(hh+85)),title)
        view(a,'ASSEMBLY',label,fn,hidden=False);dimh(a,0,ww,-22,0,0,f'{ww:g}');dimv(a,0,hh,ww+20,ww,ww,f'{hh:g}')
    box(ax,246,22,162,234,ordinary_feature_rows(),title='本版连接及功能孔位置；单位mm',fs=FS_NOTE)
    save_page(pdf,fig)

def ordinary_circle_table(ax,name,x,y,w):
    fx,fy=P[name]['flat_size'];circles=sorted(P[name]['flat_circles']);cols=2 if len(circles)>8 else 1;per=math.ceil(len(circles)/cols) if circles else 0
    ax.text(x,y,'孔心：X距左/右；Y距下/上（CUT坐标）',fontsize=FS_NOTE,color=BLU)
    for i,(xx,yy,dd) in enumerate(circles):
        column=i//per if per else 0;row=i%per if per else 0
        txt=f'F{i+1:02} Ø{dd:g} X{ordinary_number(xx)}/{ordinary_number(fx-xx)} Y{ordinary_number(yy)}/{ordinary_number(fy-yy)}'
        ax.text(x+column*w/cols,y-8-row*6,txt,fontsize=FS_NOTE,color='k')
    yy=y-10-per*6
    for i,(x0,y0,x1,y1) in enumerate(sorted(P[name].get('flat_rectangles') or []),1):
        ax.text(x,yy,f'R{i} {ordinary_number(x1-x0)}×{ordinary_number(y1-y0)}：孔边X{ordinary_number(x0)}/{ordinary_number(fx-x1)}',fontsize=FS_NOTE,color=REDC);yy-=6
        ax.text(x,yy,f'孔边Y{ordinary_number(y0)}/{ordinary_number(fy-y1)}；中心X{ordinary_number((x0+x1)/2)} Y{ordinary_number((y0+y1)/2)}',fontsize=FS_NOTE,color=REDC);yy-=7
    return yy

def ordinary_flat_labels(a,name):
    fx,fy=P[name]['flat_size'];cs=sorted(P[name]['flat_circles']);groups=[[(i,q) for i,q in enumerate(cs,1) if q[0]<fx/2],[(i,q) for i,q in enumerate(cs,1) if q[0]>=fx/2]]
    for side,group in enumerate(groups):
        group.sort(key=lambda q:q[1][1])
        for rank,(i,(xx,yy,dd)) in enumerate(group):
            tx=-6/a.s if side==0 else fx+5/a.s;ty=fy/2+(rank-(len(group)-1)/2)*6/a.s
            a.annotate(f'F{i:02}',(xx,yy),(tx,ty),fontsize=FS_NOTE,color=BLU,ha='right' if side==0 else 'left',arrowprops=dict(arrowstyle='-',lw=.3,color=BLU))
    for i,(x0,y0,x1,y1) in enumerate(sorted(P[name].get('flat_rectangles') or []),1):a.text((x0+x1)/2,(y0+y1)/2,f'R{i}',fontsize=FS_NOTE,color=REDC,ha='center')

def ordinary_piece_page(pdf,name,page):
    fig,ax=ordinary_new_page(page);fx,fy=P[name]['flat_size'];ax.text(12,252,f'{name} 真实展开 {fx:.2f}×{fy:.2f}；外表面朝读者',fontsize=FS_TITLE,color=NAVY)
    a=vax(fig,12,47,(-45,fx+90),(-45,fy+45),min(218/(fx+135),170/(fy+90)),'')
    flatdraw(a,name);ordinary_flat_labels(a,name);dimh(a,0,fx,-25/a.s,0,0,f'{fx:.2f}');dimv(a,0,fy,fx+22/a.s,fx,fx,f'{fy:.2f}')
    ordinary_iso(fig,name,145,232,82,22)
    yy=ordinary_circle_table(ax,name,248,245,160)-7
    BB=bidir(rep,name)
    ax.text(248,yy,'折弯中心双向定位；90°；按本单原生方向',fontsize=FS_NOTE,color=BLU);yy-=8
    rows=table_rows(BB,name)
    for row in sorted(rows,key=lambda r:-next(math.dist(*b['flat_line_mm']) for b in P[name]['bend_records'] if b['id']==r['id'])):
        ax.text(248,yy,f'{row["id"]} {row["axis"]} A{row["a"]}/B{row["b"]} {row["dir"]} 90°',fontsize=FS_NOTE,color=BLU);yy-=6
        for text in wrap_text(ax,f'{row["seg_prev"]}；{row["seg_next"]}',FS_NOTE,160):ax.text(248,yy,text,fontsize=FS_NOTE);yy-=6
    for text in [f'Ri{ri:g}，K{K:.5f}，BD{BD:.3f}（候选）','盖裙向内折；先长后短，先外后内。','表为几何中心距，机床挡料须按实际靠面校准。','CUT仅切割；BEND含折线；不能重复下料。']:
        for line in wrap_text(ax,text,FS_NOTE,160):ax.text(248,yy,line,fontsize=FS_NOTE,color=REDC if '机床' in text else 'k');yy-=6
    ax.text(12,18,f'{MATERIAL_CN} t{t:g}；每套{name}×1；固定孔：箱体Ø3.3攻M4／盖裙Ø4.5。',fontsize=FS_NOTE,color=BLU)
    save_page(pdf,fig)

def ordinary_end_page(pdf):
    fig,ax=ordinary_new_page(3)
    for name,x in [('END_L',12),('END_R',220)]:
        fx,fy=P[name]['flat_size'];a=vax(fig,x,151,(-25,fx+35),(-25,fy+30),min(165/(fx+60),75/(fy+55)),name+' 零折；外表面朝读者')
        flatdraw(a,name);ordinary_flat_labels(a,name);dimh(a,0,fx,-16/a.s,0,0,f'{fx:g}');dimv(a,0,fy,fx+19/a.s,fx,fx,f'{fy:g}')
        ordinary_iso(fig,name,x+130,234,54,20)
        ordinary_circle_table(ax,name,x,123,188)
    ax.text(12,28,'左端外视展开X′=W−Y，右端X′=Y；两侧Y′=Z，不镜像套用。',fontsize=FS_NOTE,color=BLU)
    ax.text(12,19,f'固定孔高Z{ZH:g}；Ø3.3攻M4，盖裙对应Ø4.5；功能孔按原版实际几何保留。',fontsize=FS_NOTE,color=REDC)
    save_page(pdf,fig)

def ordinary_process_page(pdf):
    fig,ax=ordinary_new_page(5)
    rows=[f'四边共{len(rep["holes"])}对；一一同轴；外形和功能孔不改',f'箱体Ø3.3攻M4；盖裙Ø4.5；Z{ZH:g}',f'长边最大心距{max(np.diff(LONG_X)) if len(LONG_X)>1 else 0:g}',f'短边最大心距{max(np.diff(SHORT_Y)) if len(SHORT_Y)>1 else 0:g}']
    for h in rep['holes']:rows.append(f'{h["id"]} {h["body_part"]} X{ordinary_number(h["point"][0])} Y{ordinary_number(h["point"][1])} Z{ordinary_number(h["point"][2])}')
    rows += ['表中为箱体外表面孔心，盖裙孔同轴。','薄板攻丝有效牙数少，反复拆装和承重须首件核验。','需要压铆/拉铆螺母时另定工艺，不擅自放大孔。']
    rows += list((JOB.get('confirm') or {}).get('pending_cn') or [])
    box(ax,12,27,193,229,rows,title='盖裙—箱体固定孔；单位mm',fs=FS_NOTE)
    ordinary_iso(fig,'ASSEMBLY',220,151,188,95)
    box(ax,219,27,189,105,[f'本版共有{len(P)}块主板件，实际CAD和原生展开一一对应。','盖为一体折弯件，四边裙高15；不保留无承接的顶角孔。','功能孔和把手不移位，不因连接修正重新换算图片坐标。','实际逐对孔轴、区域外几何、原生03、CUT/BEND/NEST分别核验。','工装、Ri/K/回弹、薄板螺纹及把手承重尚未实物验证。','首件试折试装确认后再批量；production_release=false。'],title='本版边界及首件确认',fs=FS_NOTE)
    save_page(pdf,fig)

def ordinary_side_fixing_pages(pdf):
    if _TOP4 or len(rep.get('holes') or [])<8 or len({h['side'] for h in rep['holes']})!=4:
        raise ValueError('ordinary side-fixing review requires actual paired holes on four walls and no roof corner holes')
    if JOB.get('image_dimension_priority_review'):image_dimension_priority_overview(pdf)
    elif JOB.get('source_side_region'):source_side_region_overview(pdf)
    elif JOB.get('full_first_page_dimensions'):full_first_page_overview(pdf)
    else:ordinary_overview(pdf)
    ordinary_piece_page(pdf,'U',2)
    if STRUCTURE=='u_l_t7u':ordinary_piece_page(pdf,'L',3)
    else:ordinary_end_page(pdf)
    ordinary_piece_page(pdf,'LID',4);ordinary_process_page(pdf);draw_customer_requirements(pdf)

od_old_piece=ordinary_piece_page
od_old_end=ordinary_end_page
od_old_overview=ordinary_overview
od_old_process=ordinary_process_page

# Direct, geometry-derived dimensions for the audited ordinary-box layout.
def od_n(x):
    return ordinary_number(0.0 if abs(float(x))<0.005 else float(x))

def od_note(ax,a,point,xy,text,color=BLU,ha='left'):
    # Arrow and number share one annotation; no separate F-only lookup.
    ax.annotate('',xy=point,xycoords=a.transData,xytext=xy,textcoords=ax.transData,
                annotation_clip=False,zorder=1,arrowprops=dict(arrowstyle='-',lw=.32,color=color,
                connectionstyle='angle,angleA=0,angleB=90,rad=0'))
    ax.text(*xy,text,fontsize=FS_NOTE,color=color,ha=ha,va='center',linespacing=1.12,
            zorder=5,bbox=dict(facecolor='white',edgecolor='none',pad=.5))

def od_items(name):
    fx,fy=P[name]['flat_size'];out=[]
    for i,(x,y,d) in enumerate(sorted(P[name]['flat_circles']),1):
        out.append((x,y,f'F{i:02} Ø{od_n(d)}\n左{od_n(x)} / 右{od_n(fx-x)}\n下{od_n(y)} / 上{od_n(fy-y)}',3))
    for i,(x0,y0,x1,y1) in enumerate(sorted(P[name].get('flat_rectangles') or []),1):
        x=(x0+x1)/2;y=(y0+y1)/2
        out.append((x,y,f'R{i} {od_n(x1-x0)}×{od_n(y1-y0)}\n心左{od_n(x)} / 右{od_n(fx-x)}\n心下{od_n(y)} / 上{od_n(fy-y)}\n边左{od_n(x0)} / 右{od_n(fx-x1)}\n边下{od_n(y0)} / 上{od_n(fy-y1)}',5))
    return out

def od_fan(ax,a,items,columns,low,high):
    for group,(tx,ha) in zip(columns,[(12,'left'),(334,'left')]):
        group=sorted(group,key=lambda q:q[1]);heights=[q[3]*3.7+1.0 for q in group]
        if sum(heights)>high-low:raise ValueError('direct dimension callout column exceeds page height')
        # order-preserving, independent physical-mm lanes.
        start=(low+high-sum(heights))/2
        for q,h in zip(group,heights):
            x,y,txt,_=q;od_note(ax,a,(x,y),(tx,start+h/2),txt);start+=h

def od_hole_chains(a,name,include_fixings=False):
    # Direct centre-distance chains within real aligned functional rows/columns.
    pts=[(x,y) for x,y,d in P[name]['flat_circles'] if include_fixings or d>=8]
    pts += [((x0+x1)/2,(y0+y1)/2) for x0,y0,x1,y1 in P[name].get('flat_rectangles',[])]
    fx,fy=P[name]['flat_size']
    for axis in (0,1):
        groups={}
        for pt in pts:groups.setdefault(round(pt[1-axis],4),[]).append(pt[axis])
        for fixed,vals in groups.items():
            vals=sorted(set(round(v,4) for v in vals))
            if len(vals)<2:continue
            if include_fixings:vals=[0]+vals+[fx if axis==0 else fy]
            lane=(fy*.30 if axis==0 else fx*.50) if include_fixings else fixed+(10/a.s if fixed<(fy if axis==0 else fx)/2 else -10/a.s)
            for u,v in zip(vals,vals[1:]):
                if abs(v-u)<.001:continue
                if axis==0:dimh(a,u,v,lane,fixed,fixed,od_n(v-u))
                else:dimv(a,u,v,lane,fixed,fixed,od_n(v-u))

def od_bend_dims(ax,a,name):
    fx,fy=P[name]['flat_size'];BB=bidir(rep,name)
    for axis in ('X','Y'):
        vals=BB[axis]
        for i,b in enumerate(vals):
            pos=b['pos'];s=a.s
            if axis=='X':
                dimh(a,0,pos,-(14+7*i)/s,0,0,f'{b["id"]} 左{od_n(pos)}')
                dimh(a,pos,fx,fy+(14+7*i)/s,fy,fy,f'{b["id"]} 右{od_n(fx-pos)}')
            else:
                dimv(a,0,pos,-(12+7*i)/s,0,0,f'{b["id"]} 下{od_n(pos)}')
                dimv(a,pos,fy,fx+(14+7*i)/s,fx,fx,f'{b["id"]} 上{od_n(fy-pos)}')
        # All same-axis combinations, not only adjacent pairs.
        k=0
        for i,b in enumerate(vals):
            for c in vals[i+1:]:
                if abs(c['pos']-b['pos'])<1e-6:continue
                txt=f'{b["id"]}–{c["id"]} {od_n(abs(c["pos"]-b["pos"]))}'
                if axis=='X':dimh(a,b['pos'],c['pos'],fy+(30+7*k)/a.s,fy,fy,txt)
                else:dimv(a,b['pos'],c['pos'],fx+(30+7*k)/a.s,fx,fx,txt)
                k+=1
    records=sorted(P[name]['bend_records'],key=lambda b:-math.dist(*b['flat_line_mm']))
    for i,b in enumerate(records):
        p,q=b['flat_line_mm'];pt=((p[0]+q[0])/2,(p[1]+q[1])/2)
        dx=abs(p[0]-q[0]);axis='Y' if dx>1e-4 else 'X';v=next(x for x in BB[axis] if x['id']==b['id'])
        line=f'{i+1}. {b["id"]} {b["direction"]} 90°；线长{od_n(math.dist(p,q))}\n'+(('左 / 右 ' if axis=='X' else '下 / 上 ')+f'{od_n(v["a"])} / {od_n(v["b"])}')
        od_note(ax,a,pt,(12+i*100,33),line)
    ax.text(12,19,f'Ri{od_n(ri)} / Ro{od_n(ri+t)}；K{K:.5f}；BD{BD:.3f}。图为展开中心尺寸；实际机床靠面/挡料须首件校准。',fontsize=FS_NOTE,color=REDC)

def ordinary_piece_page(pdf,name,page):
    if not JOB.get('ordinary_dimensioned_review'):return od_old_piece(pdf,name,page)
    fig,ax=ordinary_new_page(page);fx,fy=P[name]['flat_size'];ax.text(12,252,f'{name} 真实展开；全部尺寸直接引到本件；单位mm',fontsize=FS_TITLE,color=NAVY)
    ax.text(12,242,'孔心距展开外包四边；方孔另给孔边距。外表面朝读者，UP朝读者／DOWN背向读者。',fontsize=FS_NOTE,color=BLU)
    s=min(178/fx,100/fy);px=210-fx*s/2;py=130-fy*s/2
    a=vax(fig,px,py,(0,fx),(0,fy),s,'');flatdraw(a,name);od_hole_chains(a,name)
    dimh(a,0,fx,-7/s,0,0,f'展开长 {od_n(fx)}');dimv(a,0,fy,fx+7/s,fx,fx,f'展开宽 {od_n(fy)}')
    items=od_items(name);seq=sorted(items,key=lambda q:q[0]);cut=min(range(len(seq)+1),key=lambda k:abs(sum(q[3]*3.7+1 for q in seq[:k])-sum(q[3]*3.7+1 for q in seq)/2));groups=[seq[:cut],seq[cut:]]
    od_fan(ax,a,items,groups,56,233);od_bend_dims(ax,a,name)
    for label in a.texts:label.set_bbox(dict(facecolor='white',edgecolor='none',pad=.4))
    ip=render_assy_iso_png(R/'PREVIEW'/f'{VER}_{name}_dimension_iso.png',[name]);ia=fig.add_axes([180/PW,216/PH,60/PW,18/PH]);ia.imshow(plt.imread(ip));ia.axis('off')
    ax.text(180,235,'实际成形；'+('四边裙高均15' if name=='LID' else f't{od_n(t)}'),fontsize=FS_NOTE,color=REDC)
    save_page(pdf,fig)

def ordinary_end_page(pdf):
    if not JOB.get('ordinary_dimensioned_review'):return od_old_end(pdf)
    fig,ax=ordinary_new_page(3);ax.text(12,252,'两端板真实展开；每个孔完整双向尺寸直接引出',fontsize=FS_TITLE,color=NAVY)
    for name,ox in [('END_L',12),('END_R',222)]:
        fx,fy=P[name]['flat_size'];s=min(138/fx,79/fy);px=ox+90-fx*s/2;py=185-fy*s/2
        a=vax(fig,px,py,(0,fx),(0,fy),s,'');flatdraw(a,name);od_hole_chains(a,name)
        dimh(a,0,fx,-9/s,0,0,f'{od_n(fx)}');dimv(a,0,fy,fx+9/s,fx,fx,f'{od_n(fy)}')
        ax.text(ox,236,f'{name}；零折；外表面朝读者',fontsize=FS_NOTE,color=NAVY)
        items=od_items(name)
        for i,(x,y,txt,n) in enumerate(items):
            col=i%3;row=i//3;od_note(ax,a,(x,y),(ox+col*63,128-row*27),txt)
        ordinary_iso(fig,name,ox+133,224,53,19)
    ax.text(12,27,'END_L 外视X′=W−Y；END_R 外视X′=Y；Y′=Z。四边尺寸以本件真实展开外包为准。',fontsize=FS_NOTE,color=BLU)
    ax.text(12,18,f'Ø3.3为攻M4底孔；功能孔按本版原尺寸；t{t:g}；底角内R{ri:g}、外R{ri+t:g}。',fontsize=FS_NOTE,color=REDC)
    save_page(pdf,fig)

def ordinary_overview(pdf):
    if not JOB.get('ordinary_dimensioned_review'):return od_old_overview(pdf)
    fig,ax=ordinary_new_page(1)
    ia=fig.add_axes([12/PW,191/PH,111/PW,62/PH]);ia.imshow(np.asarray(Image.open(JOB['customer_image'])));ia.axis('off');ia.set_title('客户原图（原样）',fontsize=FS_NOTE,loc='left')
    ordinary_iso(fig,'ASSEMBLY',130,191,104,62)
    views={}
    for label,px,py,ww,hh,title,fn in [('front',24,109,L,H,'正视 长×含盖高',lambda u,v:(v,-u)),('right',136,109,W,H,'右端外视',lambda u,v:(-v,u)),('left',24,32,W,H,'左端外视',lambda u,v:(W+v,-u)),('top',136,32,L+2*OH,W+2*OH,'俯视（实际盖边）',lambda u,v:(u+OH,v+OH))]:
        s=min(85/ww,53/hh);a=vax(fig,px,py,(0,ww),(0,hh),s,'');view(a,'ASSEMBLY',label,fn,hidden=False)
        ax.text(px,py+hh*s+12,title,fontsize=FS_NOTE,color=NAVY)
        dimh(a,0,ww,-9/s,0,0,od_n(ww));dimv(a,0,hh,ww+9/s,ww,ww,od_n(hh));views[label]=a
    notes=[]
    for i,h in enumerate(JOB.get('panel_holes') or [],1):
        x,y,z=h['point'];face='left' if h['part_id']=='END_L' else 'right' if h['part_id']=='END_R' else 'front';u=W-y if face=='left' else y if face=='right' else x;ww=W if face in ('left','right') else L
        notes.append((face,(u,z),f'孔{i} Ø{od_n(h["diameter"])}\n左{od_n(u)} / 右{od_n(ww-u)}\n底{od_n(z)} / 顶{od_n(rep["params"]["Hb"]-z)}'))
    for i,h in enumerate(JOB.get('rect_cutouts') or [],1):
        x,y,z=h['center'];face='left' if h['part_id']=='END_L' else 'right' if h['part_id']=='END_R' else 'front';u=W-y if face=='left' else y if face=='right' else x;ww=W if face in ('left','right') else L
        notes.append((face,(u,z),f'方{i} {od_n(h["size_xy"][0])}×{od_n(h["size_xy"][1])}\n心左{od_n(u)} / 右{od_n(ww-u)}\n底{od_n(z)} / 顶{od_n(rep["params"]["Hb"]-z)}'))
    for i,h in enumerate(JOB.get('lid_ports') or [],1):
        x=h['x']+OH;y=h['y']+OH;notes.append(('top',(x,y),f'盖P{i} Ø{od_n(h["d"])}\n左{od_n(x)} / 右{od_n(LOL-x)}\n下{od_n(y)} / 上{od_n(LOW-y)}'))
    for i,h in enumerate(JOB.get('lid_rectangles') or [],1):
        x=h['center'][0]+OH;y=h['center'][1]+OH;notes.append(('top',(x,y),f'盖R{i} {od_n(h["size"][0])}×{od_n(h["size"][1])}\n心左{od_n(x)} / 右{od_n(LOL-x)}\n下{od_n(y)} / 上{od_n(LOW-y)}'))
    for i,cx in enumerate(HANDLE_CX):
        x=cx+OH;y=HANDLE_CYS[i]+OH;notes.append(('top',(x,y),f'把手{i+1} 4×Ø6.6\n心左{od_n(x)} / 右{od_n(LOL-x)}\n下{od_n(y)} / 上{od_n(LOW-y)}\n孔距85/62/30；朝向见p5'))
    notes += [('front',(LONG_X[0],ZH),f'前后各{len(LONG_X)}对M4\n箱Ø3.3 / 裙Ø4.5\nX：'+ '/'.join(od_n(x) for x in LONG_X)+'\n孔心高'+od_n(ZH)),('right',(SHORT_Y[0],ZH),f'左右各{len(SHORT_Y)}对M4\n箱Ø3.3 / 裙Ø4.5\nY：'+ '/'.join(od_n(x) for x in SHORT_Y)+'\n孔心高'+od_n(ZH))]
    ax.text(248,252,f'全部功能位置；实际外边基准；t{t:g}',fontsize=FS_NOTE,color=NAVY)
    # In this audited family at most 13 individual feature groups + two fixing rows.
    for j,txt in enumerate([f'订单{JOB.get("order_id","")}；数量{JOB.get("quantity",1)}',f'箱体外{L:g}×{W:g}×高{od_n(rep["params"]["Hb"])}',f'含盖总高{H:g}；罩盖外{LOL:g}×{LOW:g}',f'一体四边裙15；共{len(rep["holes"])}对实际侧面连接',f'Ri{ri:g}、K{K:.5f}及薄板攻丝须首件确认']):
        ax.text(248,240-j*6,txt,fontsize=FS_NOTE,color=NAVY)
    per=math.ceil(len(notes)/2)
    for i,(face,pt,txt) in enumerate(notes):
        col=i//per;row=i%per;od_note(ax,views[face],pt,(248+col*81,184-row*22),txt)
    ax.text(12,18,f'箱体高{od_n(rep["params"]["Hb"])}；盖高15；含盖{H:g}。四边{len(rep["holes"])}对；原图坐标与实际盖边区别保留。',fontsize=FS_NOTE,color=REDC)
    save_page(pdf,fig)

def ordinary_process_page(pdf):
    if not JOB.get('ordinary_dimensioned_review'):return od_old_process(pdf)
    fig,ax=ordinary_new_page(5);ax.text(12,252,'四边固定链尺寸、把手安装孔与03盖角放大；单位mm',fontsize=FS_TITLE,color=NAVY)
    for ox,span,coords,label in [(20,L,LONG_X,'前/后长壁，每面'),(228,W,SHORT_Y,'左/右短壁，每面')]:
        s=min(166/span,.65);a=vax(fig,ox,191,(0,span),(0,30),s,'')
        a.plot([0,span,span,0,0],[0,0,30,30,0],color='k',lw=.6)
        for u in coords:a.add_patch(Circle((u,15),2.25,fill=False,ec=REDC))
        pts=[0]+list(coords)+[span]
        for u,v in zip(pts,pts[1:]):dimh(a,u,v,-9/s,0,0,od_n(v-u))
        dimh(a,0,span,-18/s,0,0,od_n(span))
        ax.text(ox,233,f'{label}{len(coords)}对，孔排示意链',fontsize=FS_NOTE,color=NAVY)
        od_note(ax,a,(coords[0],15),(ox,220),f'箱Ø3.3攻M4／盖裙Ø4.5；Z{od_n(ZH)}\n箱上边{od_n(rep["params"]["Hb"]-ZH)}；裙下边7.5')
    # Native cut edge shape: enlarge exact lower-left 03 corner, no guessed redrawing.
    a=vax(fig,22,84,(0,23),(0,23),2.1,'');
    for wire in flats['LID']['wires']:pl(a,wire+[wire[0]],lw=.8)
    for b in P['LID']['bend_records']:pl(a,b['flat_line_mm'],color=REDC,lw=.6)
    pts=[]
    for x,y in flats['LID']['wires'][0]:
        if -.001<=x<=23 and -.001<=y<=23 and not any(math.dist((x,y),q)<.001 for q in pts):pts.append((x,y))
    if len(pts)>12:raise ValueError('corner requires separate arc treatment')
    ax.text(12,151,'03角：本版真实CUT局部 ×2.1',fontsize=FS_NOTE,color=NAVY)
    for i,pt in enumerate(sorted(pts),1):
        col=(i-1)%2;row=(i-1)//2;od_note(ax,a,pt,(12+col*51,69-row*10),f'C{i} X{od_n(pt[0])}\nY{od_n(pt[1])}')
    # Exact, pre-existing native STEP section, cropped at the front top corner.
    ax.text(112,151,'盖—体实际STEP剖面局部',fontsize=FS_NOTE,color=NAVY)
    s=3.1;a=vax(fig,127,85,(-4,17),(-1,20),s,'')
    for part,paths in sec.items():
        for path in paths:pl(a,[(y,z-(H-20)) for y,z in path],color='k',lw=.8)
    bodytop=20-(t+rep['params']['q'])
    dimv(a,5,20,10,-g-t,-g-t,'裙15')
    od_note(ax,a,(t/2,bodytop/2),(112,64),f'板厚t{od_n(t)}；内R{od_n(ri)}／外R{od_n(ri+t)}\n侧净隙g{od_n(g)}；顶净隙q{od_n(rep["params"]["q"])}\n孔轴Z{od_n(ZH)}；裙下边高Z{od_n(H-15)}')
    # All four handle holes, actual orientation, dimensioned from physical arrangement.
    for i,cx in enumerate(HANDLE_CX):
        cy=HANDLE_CYS[i];hh=[(h['x'],h['y']) for h in rep.get('handle_holes',[]) if abs(h['x']-cx)<60 and abs(h['y']-cy)<60]
        pts=[(x-cx,y-cy) for x,y in hh];ox=240+i*90
        if len(pts)!=4:raise ValueError('actual handle group must have exactly four points')
        xs=[p[0] for p in pts];ys=[p[1] for p in pts];sc=.62
        a=vax(fig,ox,89,(min(xs)-8,max(xs)+8),(min(ys)-8,max(ys)+8),sc,'')
        for x,y in pts:a.add_patch(Circle((x,y),3.3,fill=False,ec=REDC))
        if len(set(round(x,5) for x in xs))==2:
            xx=sorted(set(round(x,5) for x in xs))
            for j,x in enumerate(xx):
                yy=sorted(y for px,y in pts if abs(px-x)<1e-4);dimv(a,yy[0],yy[-1],x+(-8 if j==0 else 8)/sc,x,x,od_n(yy[-1]-yy[0]))
            dimh(a,xx[0],xx[-1],min(ys)-9/sc,min(ys),min(ys),'30')
        else:
            yy=sorted(set(round(y,5) for y in ys))
            for j,y in enumerate(yy):
                xx=sorted(x for x,py in pts if abs(py-y)<1e-4);dimh(a,xx[0],xx[-1],y+(-8 if j==0 else 8)/sc,y,y,od_n(xx[-1]-xx[0]))
            dimv(a,yy[0],yy[-1],max(xs)+9/sc,max(xs),max(xs),'30')
        ax.text(ox-6,151,f'把手{i+1} 实际方向\n4×Ø6.6；孔距85/62/30',fontsize=FS_NOTE,color=NAVY)
        od_note(ax,a,(0,0),(ox-6,57),f'中心实际盖左{od_n(cx+OH)}\n下{od_n(cy+OH)}；原孔不移')
    ax.text(112,33,'先长后短、先外后内为建议；逐道顺序与UP/DOWN在对应展开页。',fontsize=FS_NOTE,color=BLU)
    ax.text(112,25,'薄板攻M4牙数少；刀模、回弹、03角与合盖/承重须首件确认。',fontsize=FS_NOTE,color=REDC)
    ax.text(112,17,('本版含尺寸/连接修正；实际CAD、展开、CUT/BEND/NEST同步。' if JOB.get('batch_geometry_changed') else '本版仅补图上尺寸；CAD / CUT / BEND / NEST的实际几何保持。'),fontsize=FS_NOTE,color=REDC)
    save_page(pdf,fig)

def review_face_features(face):
    features=[]
    if face=='top':
        for i,h in enumerate(LID_HOLES,1):
            features.append(dict(x=h['x']+OH,y=h['y']+OH,label=f'Ø{h["d"]:g}'+(' M6过孔' if abs(h['d']-6.6)<1e-6 else '')+f'\nX{h["x"]+OH:g} Y{h["y"]+OH:g}'))
        for i,h in enumerate(JOB.get('lid_rectangles') or [],1):
            x,y=h['center'];w,hg=h['size'];features.append(dict(x=x+OH,y=y+OH,label=f'{w:g}×{hg:g}'+(f' R{h["corner_radius"]:g}' if h.get('corner_radius') else '')+f'\nX{x+OH:g} Y{y+OH:g}'))
        centers=[(x,y) for x,y in zip(HANDLE_CX,HANDLE_CYS)]
        centers += [tuple(h['center']) for h in JOB.get('roof_handle_groups') or []]
        for i,(x,y) in enumerate(centers,1):features.append(dict(x=x+OH,y=y+OH,label=f'把手{i}中心\nX{x+OH:g} Y{y+OH:g}',center_mark=True))
        return features
    for h in JOB.get('panel_holes') or []:
        x,y,z=h['point'];axis=h['axis'];ok=(face=='front' and abs(axis[1])>.9 and abs(y)<1e-6) or (face=='right' and abs(axis[0])>.9 and abs(x-L)<1e-6) or (face=='left' and abs(axis[0])>.9 and abs(x)<1e-6)
        if ok:
            u=x if face=='front' else y if face=='right' else W-y
            features.append(dict(x=u,y=z,label=f'Ø{h["diameter"]:g}\nX{u:g} Z{z:g}'))
    for h in JOB.get('rect_cutouts') or []:
        x,y,z=h['center'];axis=h['axis'];ok=(face=='front' and abs(axis[1])>.9 and abs(y)<1e-6) or (face=='right' and abs(axis[0])>.9 and abs(x-L)<1e-6) or (face=='left' and abs(axis[0])>.9 and abs(x)<1e-6)
        if ok:
            u=x if face=='front' else y if face=='right' else W-y;ww,hh=h['size_xy'];features.append(dict(x=u,y=z,label=f'{ww:g}×{hh:g}'+(f' R{h["corner_radius"]:g}' if h.get('corner_radius') else '')+f'\nX{u:g} Z{z:g}'))
    for h in rep.get('holes') or []:
        x,y,z=h['point'];axis=h['axis'];ok=(face=='front' and abs(axis[1])>.9 and abs(y)<1e-6) or (face=='right' and abs(axis[0])>.9 and abs(x-L)<1e-6) or (face=='left' and abs(axis[0])>.9 and abs(x)<1e-6)
        if ok:
            u=x if face=='front' else y if face=='right' else W-y
            features.append(dict(x=u,y=z,label=f'M4：体Ø3.3/盖Ø4.5\nX{u:g} Z{z:g}'))
    return features


def review_dimensioned_face(fig,face,px,py,pw,ph):
    ww=(L+2*OH if face=='top' else L if face=='front' else W);hh=W+2*OH if face=='top' else H
    a=fig.add_axes([px/PW,py/PH,pw/PW,ph/PH]);a.set(xlim=(0,pw),ylim=(0,ph));a.axis('off');a.s=1
    title={'front':'正视｜孔心距箱体左/底','right':'右外视｜孔心距面左/底','left':'左外视｜孔心距面左/底','top':'盖顶俯视｜孔心距实际盖左/下'}[face]
    a.text(pw/2,ph-2,title,ha='center',va='top',fontsize=FS_NOTE,color=NAVY)
    scale=min((pw-76)/ww,(ph-30)/hh);gx=(pw-ww*scale)/2;gy=(ph-hh*scale)/2-1
    mappings={'front':lambda u,v:(v,-u),'right':lambda u,v:(-v,u),'left':lambda u,v:(W+v,-u),'top':lambda u,v:(u+OH,v+OH)}
    def mapping(u,v):
        x,y=mappings[face](u,v);return (gx+x*scale,gy+y*scale)
    view(a,'LID' if face=='top' else 'ASSEMBLY',face,mapping,hidden=False)
    dimh(a,gx,gx+ww*scale,gy-5,gy,gy,f'{ww:g}'+(' 盖' if face=='top' else ' 箱体'))
    dimv(a,gy,gy+hh*scale,gx+ww*scale+5,gx+ww*scale,gx+ww*scale,f'{hh:g}')
    ff=review_face_features(face)
    for f in ff:
        first=f['label'].split('\n')[0];f['category']='mount' if first.startswith('M4') else 'rect' if '×' in first else 'circle'
    for f in ff:
        if f.get('center_mark'):
            a.plot(gx+f['x']*scale,gy+f['y']*scale,'+',color=GRN,ms=4)
            continue
        if face=='top' and f['label'].startswith('Ø6.6'):continue
        right=sorted([q['x']-f['x'] for q in ff if not q.get('center_mark') and q['category']==f['category'] and not (face=='top' and q['label'].startswith('Ø6.6')) and abs(q['y']-f['y'])<1e-6 and q['x']>f['x']+1e-6])
        lower=sorted([f['y']-q['y'] for q in ff if not q.get('center_mark') and q['category']==f['category'] and not (face=='top' and q['label'].startswith('Ø6.6')) and abs(q['x']-f['x'])<1e-6 and q['y']<f['y']-1e-6])
        relation=[]
        if right:relation.append(f'右邻{right[0]:g}')
        if lower:relation.append(f'下邻{lower[0]:g}')
        if relation:f['label']+='\n'+' '.join(relation)
    ordered=sorted(ff,key=lambda h:(h['x'],h['y']));weights=[len(h['label'].split('\n')) for h in ordered]
    split=min(range(len(ordered)+1),key=lambda k:abs(sum(weights[:k])-sum(weights)/2))
    groups=[ordered[:split],ordered[split:]]
    for side,group in enumerate(groups):
        group.sort(key=lambda h:(-h['y'],h['x']))
        if not group:continue
        heights=[]
        for h in group:
            probe=a.text(0,0,h['label'],fontsize=FS_NOTE,va='center',parse_math=False);fig.canvas.draw();heights.append(probe.get_window_extent(fig.canvas.get_renderer()).height/fig.dpi*25.4+1.6);probe.remove()
        if sum(heights)>ph-20:raise ValueError(str((face,side,sum(heights),[(h['label'],height) for h,height in zip(group,heights)])))
        top=(ph+sum(heights))/2
        for h,height in zip(group,heights):
            ty=top-height/2;top-=height;tx=1 if side==0 else pw-1
            a.annotate(h['label'],(gx+h['x']*scale,gy+h['y']*scale),(tx,ty),fontsize=FS_NOTE,color=GRN if h.get('center_mark') else BLU,va='center',ha='left' if side==0 else 'right',arrowprops=dict(arrowstyle='-',lw=.35,color=BLU),parse_math=False)
    if face=='top' and (HANDLE_CX or JOB.get('roof_handle_groups')):
        a.text(pw/2,ph-10,'每组把手：宽排85 / 窄排62 / 排距30，4×Ø6.6 M6过孔',ha='center',fontsize=FS_NOTE,color=BLU)
    if not ff:a.text(pw/2,ph/2,'本面无功能孔',ha='center',fontsize=FS_NOTE,color='0.35')
    if face=='top' and rep.get('lid_opening_region_origin'):
        ox,oy=rep['lid_opening_region_origin'];a.plot(gx+(ox+OH)*scale,gy+(oy+OH)*scale,'+',color=GRN,ms=5)
        a.text(pw/2,1,f'源可开孔区O距实际盖边{ox+OH:g}/{oy+OH:g}；上图另用实际盖边',ha='center',fontsize=FS_NOTE,color=GRN)


def full_first_page_overview(pdf):
    fig,ax=ordinary_new_page(1)
    image=fig.add_axes([12/PW,182/PH,95/PW,64/PH]);image.imshow(np.asarray(Image.open(JOB['customer_image'])),interpolation='none',resample=False);image.axis('off');image.set_title('客户原图（原样）',fontsize=FS_NOTE,loc='left')
    ax.text(12,256,f'订单{JOB.get("order_id","")}｜{MATERIAL_CN} t{t:g}',fontsize=FS_NOTE,color=NAVY)
    ax.text(12,176,f'箱体{L:g}×{W:g}｜含盖高{H:g}',fontsize=FS_NOTE,color=BLU)
    ax.text(12,169,f'盖外{L+2*OH:g}×{W+2*OH:g}｜盖裙{skirt:g}',fontsize=FS_NOTE,color=BLU)
    notes=JOB.get('customer_image_note') or ''
    lines=wrap_text(ax,notes,FS_NOTE,95)
    if len(lines)>4:raise ValueError('source-datum note requires more room on first review page')
    for i,line in enumerate(lines):ax.text(12,162-i*5,line,fontsize=FS_NOTE,color=REDC)
    review_dimensioned_face(fig,'top',120,150,288,110)
    review_dimensioned_face(fig,'front',12,22,126,124)
    review_dimensioned_face(fig,'right',147,22,126,124)
    review_dimensioned_face(fig,'left',282,22,126,124)
    xx=max(np.diff(sorted(LONG_X))) if len(LONG_X)>1 else 0;yy=max(np.diff(sorted(SHORT_Y))) if len(SHORT_Y)>1 else 0
    ax.text(12,15,f'盖体连接{len(rep.get("holes") or [])}对；长边最大心距{xx:g}、短边{yy:g}；体Ø3.3攻M4/盖裙Ø4.5；{t:g}mm薄板与Ri/K须首件核验。',fontsize=FS_NOTE,color=REDC)
    save_page(pdf,fig)

# Scoped revision: dimensions remain in each view's own physical panel.
_ld_old_overview=ordinary_overview
_ld_old_piece=ordinary_piece_page
_ld_old_end=ordinary_end_page
_LD_RECORDS=[]

def ld_axes(fig,x,y,w,h):
    a=fig.add_axes([x/PW,y/PH,w/PW,h/PH]);a.set(xlim=(0,w),ylim=(0,h));a.axis('off');a.s=1
    return a

def ld_chain(a,values,origin,scale,fixed,axis,offset):
    vv=sorted({round(float(v),5) for v in values});last=-100
    for i,(u,v) in enumerate(zip(vv,vv[1:])):
        if v-u<1e-4:continue
        # Very short intervals use a second nearby lane, rather than overlapping figures.
        lane=offset+(6 if (v-u)*scale<8 and i%2 else 0)
        if axis=='X':dimh(a,origin+u*scale,origin+v*scale,fixed-lane,fixed,fixed,od_n(v-u))
        else:dimv(a,origin+u*scale,origin+v*scale,fixed+lane,fixed,fixed,od_n(v-u))

def ld_label(a,point,text,bounds):
    # Glyph-aware local placement; every leader stays within one panel.
    a.figure.canvas.draw();renderer=a.figure.canvas.get_renderer()
    occupied=[q.get_window_extent(renderer) for q in a.texts if q.get_text()]
    best=None
    for dx,dy,ha in [(5,5,'left'),(-5,5,'right'),(5,-7,'left'),(-5,-7,'right'),(0,10,'center'),(0,-12,'center'),(9,12,'left'),(-9,12,'right'),(9,-14,'left'),(-9,-14,'right')]:
        tx,ty=point[0]+dx,point[1]+dy
        probe=a.text(tx,ty,text,fontsize=FS_NOTE,ha=ha,va='center',linespacing=1.1);a.figure.canvas.draw();bb=probe.get_window_extent(renderer);probe.remove()
        inv=a.transData.inverted();lo,hi=inv.transform([[bb.x0,bb.y0],[bb.x1,bb.y1]])
        outside=max(0,bounds[0]-lo[0])+max(0,hi[0]-bounds[1])+max(0,bounds[2]-lo[1])+max(0,hi[1]-bounds[3])
        collisions=sum(bb.overlaps(b) for b in occupied);score=outside*100+collisions*1000+math.hypot(dx,dy)
        if best is None or score<best[0]:best=(score,tx,ty,ha)
        if outside==0 and collisions==0:break
    _,tx,ty,ha=best
    a.annotate('',point,(tx,ty),zorder=1,arrowprops=dict(arrowstyle='-',lw=.35,color=BLU))
    a.text(tx,ty,text,fontsize=FS_NOTE,color=BLU,ha=ha,va='center',linespacing=1.1,zorder=5,bbox=dict(facecolor='white',edgecolor='none',pad=.6))
    _LD_RECORDS.append(dict(kind='local_label',text=text,leader_mm=math.hypot(tx-point[0],ty-point[1]),local_panel=True))

def ld_face_data(face):
    out=[]
    for f in review_face_features(face):
        # Handle centres define the complete repeated mounting pattern on page5.
        if face=='top' and f['label'].startswith('Ø6.6'):continue
        first=f['label'].split('\n')[0]
        kind='handle' if f.get('center_mark') else 'fix' if first.startswith('M4') else 'feature'
        out.append(dict(x=f['x'],y=f['y'],text=first,kind=kind))
    return out

def ld_face_panel(fig,face,ox,oy,cw,ch):
    a=ld_axes(fig,ox,oy,cw,ch);ww=LOL if face=='top' else L if face=='front' else W;hh=LOW if face=='top' else H;fs=ld_face_data(face)
    functional=[f for f in fs if f['kind']=='feature'];ym=0
    if face in ('left','right') and len(functional)>4 and min(f['y'] for f in functional)>hh*.5:
        ym=max(0,min(f['y'] for f in functional)-18)
    ymax=hh;scale=min((cw-58)/ww,(ch-39)/(ymax-ym));gx=(cw-ww*scale)/2;gy=24
    title={'front':'正视','right':'右端外视','left':'左端外视','top':'盖顶俯视'}[face]
    a.text(cw/2,ch-2,title+('｜上部放大，Z仍自箱底' if ym else ''),fontsize=FS_NOTE,ha='center',va='top',color=NAVY)
    fn={'front':lambda u,v:(v,-u),'right':lambda u,v:(-v,u),'left':lambda u,v:(W+v,-u),'top':lambda u,v:(u+OH,v+OH)}[face]
    # Clip projection to the local diagram, not to unrelated dimensions.
    va=fig.add_axes([(ox+gx)/PW,(oy+gy)/PH,ww*scale/PW,(ymax-ym)*scale/PH]);va.set(xlim=(0,ww),ylim=(ym,ymax));va.axis('off');va.s=scale
    view(va,'LID' if face=='top' else 'ASSEMBLY',face,fn,hidden=False)
    coordsx=[0,ww]+[f['x'] for f in fs];coordsy=[ym,ymax]+[f['y'] for f in fs if f['y']>=ym]
    ld_chain(a,coordsx,gx,scale,gy,'X',6)
    ld_chain(a,coordsy,gy-ym*scale,scale,gx+ww*scale,'Y',7)
    dimh(a,gx,gx+ww*scale,gy-19,gy,gy,f'{od_n(ww)}'+(' 盖外' if face=='top' else ' 箱体'))
    if JOB.get('show_review_overall_dimensions') and not ym:
        dimv(a,gy,gy+hh*scale,gx+ww*scale+20,gx+ww*scale,gx+ww*scale,
             f'{od_n(hh)}'+(' 盖宽' if face=='top' else ' 含盖高'))
    # Unique diameter/shape group, not a separate four-line leader for every identical hole.
    groups={}
    for f in fs:
        if f['kind']=='fix':continue
        groups.setdefault(f['text'],[]).append(f)
    for text,group in groups.items():
        f=min(group,key=lambda q:abs(q['x']-ww/2));pt=(gx+f['x']*scale,gy+(f['y']-ym)*scale)
        label=(f'{len(group)}×' if len(group)>1 else '')+text
        if f['kind']=='handle':label+='\n4×Ø6.6；85/62/30'
        ld_label(a,pt,label,(0,cw,21,ch-7))
    mounts=[f for f in fs if f['kind']=='fix']
    if mounts:a.text(2,ch-10,f'本面{len(mounts)}对M4；体Ø3.3／裙Ø4.5',fontsize=FS_NOTE,color=BLU)
    if ym:
        for z in sorted({f['y'] for f in functional}):
            zz=gy+(z-ym)*scale;a.plot([gx-2,gx],[zz,zz],color=BLU,lw=.4);a.text(gx-3,zz,'Z'+od_n(z),fontsize=FS_NOTE,color=BLU,ha='right',va='center')
        a.plot([gx-2,gx,gx+2],[gy-1,gy+1,gy-1],color='k',lw=.6);a.text(2,16,f'下截面Z{od_n(ym)}，非零点',fontsize=FS_NOTE,color=BLU)
    _LD_RECORDS.append(dict(kind='face',face=face,chain_x=sorted(set(coordsx)),chain_y=sorted(set(coordsy)),panel=[ox,oy,cw,ch],crop_y=ym))
    for txt in a.texts:txt.set_bbox(dict(facecolor='white',edgecolor='none',pad=.4))

def ordinary_overview(pdf):
    if not JOB.get('ordinary_local_dimensions_review'):return _ld_old_overview(pdf)
    fig,ax=ordinary_new_page(1)
    ia=fig.add_axes([12/PW,211/PH,92/PW,43/PH]);ia.imshow(np.asarray(Image.open(JOB['customer_image'])));ia.axis('off');ia.set_title('客户原图',fontsize=FS_NOTE,loc='left')
    ordinary_iso(fig,'ASSEMBLY',112,211,82,43)
    for i,txt in enumerate([f'订单{JOB.get("order_id","")}；数量{JOB.get("quantity",1)}',f'箱体外{L:g}×{W:g}；体高{od_n(rep["params"]["Hb"])}；含盖{H:g}',f'盖外{LOL:g}×{LOW:g}；四边裙15；材质201 t{t:g}',f'四边{len(rep["holes"])}对M4；孔距按各面尺寸链', '孔心定位；盖从实际外边量；mm。把手孔型见第5页。']):ax.text(210,250-i*7,txt,fontsize=FS_NOTE,color=NAVY)
    for f,x,y in [('front',12,114),('right',218,114),('left',12,22),('top',218,22)]:ld_face_panel(fig,f,x,y,190,87)
    save_page(pdf,fig)

def ld_native_features(name):
    p=P[name];allc=sorted(p['flat_circles']);features=[];handle_points=[]
    for i,(x,y,d) in enumerate(allc,1):
        if name=='LID' and abs(d-6.6)<1e-5:handle_points.append((x,y,d));continue
        features.append(dict(x=x,y=y,text=f'Ø{od_n(d)}',id=f'F{i:02}',kind='fix' if abs(d-(4.5 if name=='LID' else 3.3))<1e-5 else 'feature'))
    # Preserve independent rotations; centre average is the actual four-hole pattern centre.
    remaining=handle_points[:]
    while remaining:
        seed=remaining[0];group=sorted(remaining,key=lambda q:math.dist(q[:2],seed[:2]))[:4]
        if len(group)!=4:raise ValueError('handle group incomplete')
        for q in group:remaining.remove(q)
        cx=sum(q[0] for q in group)/4;cy=sum(q[1] for q in group)/4
        features.append(dict(x=cx,y=cy,text=f'把手 {len([f for f in features if f["kind"]=="handle"])+1}',kind='handle',holes=group))
    for i,(x0,y0,x1,y1) in enumerate(sorted(p.get('flat_rectangles') or []),1):features.append(dict(x=(x0+x1)/2,y=(y0+y1)/2,text=f'R{i} {od_n(x1-x0)}×{od_n(y1-y0)}',kind='feature'))
    return features

def ld_native_panel(fig,name,ox,oy,cw,ch,with_bends=True):
    a=ld_axes(fig,ox,oy,cw,ch);fx,fy=P[name]['flat_size'];scale=min((cw-80)/fx,(ch-69)/fy);gx=(cw-fx*scale)/2;gy=34
    for wire in flats[name]['wires']:pl(a,[(gx+x*scale,gy+y*scale) for x,y in wire+[wire[0]]],lw=.7)
    features=ld_native_features(name)
    xs=[0,fx]+[f['x'] for f in features];ys=[0,fy]+[f['y'] for f in features]
    ld_chain(a,xs,gx,scale,gy,'X',6);ld_chain(a,ys,gy,scale,gx+fx*scale,'Y',7)
    dimh(a,gx,gx+fx*scale,gy-21,gy,gy,f'展开长{od_n(fx)}');dimv(a,gy,gy+fy*scale,gx-8,gx,gx,f'展开宽{od_n(fy)}')
    if with_bends:
        BB=bidir(rep,name)
        for axis in ('X','Y'):
            vals=BB[axis]
            # Only a few native fold lines: each gets both edge offsets at the local side.
            for i,b in enumerate(vals):
                pos=b['pos']
                if axis=='X':
                    dimh(a,gx,gx+pos*scale,gy+fy*scale+8+i*7,gy+fy*scale,gy+fy*scale,f'{b["id"]}左{od_n(pos)}')
                    dimh(a,gx+pos*scale,gx+fx*scale,gy-28-i*7,gy,gy,f'右{od_n(fx-pos)}')
                else:
                    dimv(a,gy,gy+pos*scale,gx-17-i*7,gx,gx,f'{b["id"]}下{od_n(pos)}')
                    dimv(a,gy+pos*scale,gy+fy*scale,gx+fx*scale+20+i*7,gx+fx*scale,gx+fx*scale,f'上{od_n(fy-pos)}')
            if len(vals)==2:
                u,v=vals
                if axis=='X':dimh(a,gx+u['pos']*scale,gx+v['pos']*scale,gy+fy*scale+24,gy+fy*scale,gy+fy*scale,f'{u["id"]}–{v["id"]} {od_n(v["pos"]-u["pos"])}')
                else:dimv(a,gy+u['pos']*scale,gy+v['pos']*scale,gx+fx*scale+35,gx+fx*scale,gx+fx*scale,f'{u["id"]}–{v["id"]} {od_n(v["pos"]-u["pos"])}')
        for b in P[name]['bend_records']:
            p,q=b['flat_line_mm'];sp=[(gx+x*scale,gy+y*scale) for x,y in (p,q)];pl(a,sp,color=REDC,lw=.8)
            pt=((sp[0][0]+sp[1][0])/2,(sp[0][1]+sp[1][1])/2)
            # B number printed directly beside its own line; no long sequence-card leader.
            a.text(pt[0]+2,pt[1]+2,b['id'],fontsize=FS_NOTE,color=REDC)
    groups={}
    for f in features:groups.setdefault(f['text'],[]).append(f)
    for text,group in groups.items():
        # Each diameter or repeated pattern labelled next to an actual feature, no page-wide fans.
        f=min(group,key=lambda q:abs(q['x']-fx/2)+abs(q['y']-fy/2));label=(f'{len(group)}×' if len(group)>1 else '')+text
        if f['kind']=='handle':label+='\n4×Ø6.6，孔型见第5页'
        ld_label(a,(gx+f['x']*scale,gy+f['y']*scale),label,(1,cw-1,gy-1,ch-6))
    for txt in a.texts:txt.set_bbox(dict(facecolor='white',edgecolor='none',pad=.4))
    _LD_RECORDS.append(dict(kind='native',part=name,circle_count=len(P[name]['flat_circles']),rect_count=len(P[name].get('flat_rectangles',[])),chain_x=sorted(set(xs)),chain_y=sorted(set(ys)),handle_groups=[f for f in features if f['kind']=='handle'],panel=[ox,oy,cw,ch]))

def ordinary_piece_page(pdf,name,page):
    if not JOB.get('ordinary_local_dimensions_review'):return _ld_old_piece(pdf,name,page)
    fig,ax=ordinary_new_page(page);ax.text(12,252,f'{name} 真实展开｜尺寸按位置围绕本图排列｜外表面朝读者',fontsize=FS_TITLE,color=NAVY)
    ax.text(12,241,'孔心链尺寸含两端板边；相同孔径共用数量标注。把手按中心定位＋第5页完整孔型。单位mm。',fontsize=FS_NOTE,color=BLU)
    ip=render_assy_iso_png(R/'PREVIEW'/f'{VER}_{name}_local_iso.png',[name]);ia=fig.add_axes([344/PW,240/PH,60/PW,16/PH]);ia.imshow(plt.imread(ip));ia.axis('off')
    ld_native_panel(fig,name,12,49,396,184)
    rows=sorted(P[name]['bend_records'],key=lambda b:-math.dist(*b['flat_line_mm']))
    for i,b in enumerate(rows):
        ax.text(12+i*99,34,f'{i+1}. {b["id"]} {b["direction"]} 90°\n折线长{od_n(math.dist(*b["flat_line_mm"]))}',fontsize=FS_NOTE,color=BLU)
    ax.text(12,18,f'Ri{ri:g} / Ro{ri+t:g}；K{K:.5f}；先长后短。UP朝读者，DOWN背向读者；机床靠面/挡料须首件校准。',fontsize=FS_NOTE,color=REDC)
    save_page(pdf,fig)

def ordinary_end_page(pdf):
    if not JOB.get('ordinary_local_dimensions_review'):return _ld_old_end(pdf)
    fig,ax=ordinary_new_page(3);ax.text(12,252,'两端板真实展开｜各件独立尺寸链，不跨图拉线',fontsize=FS_TITLE,color=NAVY)
    for name,x in [('END_L',12),('END_R',218)]:
        ax.text(x,240,name+' 外视｜零折；Y′=Z',fontsize=FS_NOTE,color=NAVY)
        ip=render_assy_iso_png(R/'PREVIEW'/f'{VER}_{name}_local_iso.png',[name]);ia=fig.add_axes([(x+157)/PW,235/PH,30/PW,14/PH]);ia.imshow(plt.imread(ip));ia.axis('off')
        ld_native_panel(fig,name,x,40,190,187,with_bends=False)
    ax.text(12,24,'左端X′=W−Y；右端X′=Y；相同孔径按数量共用标注。底角内R'+od_n(ri)+'／外R'+od_n(ri+t)+'。',fontsize=FS_NOTE,color=BLU)
    ax.text(12,16,'Ø3.3为攻M4底孔；盖裙Ø4.5。完整圆孔/方口四向坐标CSV仍随完整包保留。',fontsize=FS_NOTE,color=REDC)
    save_page(pdf,fig)

# Scoped revision: dimensions remain in each view's own physical panel.
_ld_old_overview=ordinary_overview
_ld_old_piece=ordinary_piece_page
_ld_old_end=ordinary_end_page
_LD_RECORDS=[]

def ld_axes(fig,x,y,w,h):
    a=fig.add_axes([x/PW,y/PH,w/PW,h/PH]);a.set(xlim=(0,w),ylim=(0,h));a.axis('off');a.s=1;a._ld_panel=(x,y,w,h)
    return a

def ld_chain(a,values,origin,scale,fixed,axis,offset):
    vv=sorted({round(float(v),5) for v in values});last=-100
    for i,(u,v) in enumerate(zip(vv,vv[1:])):
        if v-u<1e-4:continue
        # Very short intervals use a second nearby lane, rather than overlapping figures.
        lane=offset+(6 if (v-u)*scale<8 and i%2 else 0)
        if axis=='X':dimh(a,origin+u*scale,origin+v*scale,fixed-lane,fixed,fixed,od_n(v-u))
        else:dimv(a,origin+u*scale,origin+v*scale,fixed+lane,fixed,fixed,od_n(v-u))

def ld_label(a,point,text,bounds):
    # Glyph-aware local placement; every leader stays within one panel.
    a.figure.canvas.draw();renderer=a.figure.canvas.get_renderer()
    occupied=[q.get_window_extent(renderer) for q in a.texts if q.get_text()]
    best=None
    for dx,dy,ha in [(5,5,'left'),(-5,5,'right'),(5,-7,'left'),(-5,-7,'right'),(0,10,'center'),(0,-12,'center'),(9,12,'left'),(-9,12,'right'),(9,-14,'left'),(-9,-14,'right')]:
        tx,ty=point[0]+dx,point[1]+dy
        probe=a.text(tx,ty,text,fontsize=FS_NOTE,ha=ha,va='center',linespacing=1.1);a.figure.canvas.draw();bb=probe.get_window_extent(renderer);probe.remove()
        inv=a.transData.inverted();lo,hi=inv.transform([[bb.x0,bb.y0],[bb.x1,bb.y1]])
        outside=max(0,bounds[0]-lo[0])+max(0,hi[0]-bounds[1])+max(0,bounds[2]-lo[1])+max(0,hi[1]-bounds[3])
        collisions=sum(bb.overlaps(b) for b in occupied);score=outside*100+collisions*1000+math.hypot(dx,dy)
        if best is None or score<best[0]:best=(score,tx,ty,ha)
        if outside==0 and collisions==0:break
    _,tx,ty,ha=best
    a.annotate('',point,(tx,ty),zorder=1,arrowprops=dict(arrowstyle='-',lw=.35,color=BLU))
    a.text(tx,ty,text,fontsize=FS_NOTE,color=BLU,ha=ha,va='center',linespacing=1.1,zorder=5,bbox=dict(facecolor='white',edgecolor='none',pad=.6))
    _LD_RECORDS.append(dict(kind='local_label',text=text,leader_mm=math.hypot(tx-point[0],ty-point[1]),local_panel=True))

def ld_face_data(face):
    out=[]
    for f in review_face_features(face):
        # Handle centres define the complete repeated mounting pattern on page5.
        if face=='top' and f['label'].startswith('Ø6.6'):continue
        first=f['label'].split('\n')[0]
        kind='handle' if f.get('center_mark') else 'fix' if first.startswith('M4') else 'feature'
        out.append(dict(x=f['x'],y=f['y'],text=first,kind=kind))
    return out

def ld_face_panel(fig,face,ox,oy,cw,ch):
    a=ld_axes(fig,ox,oy,cw,ch);ww=LOL if face=='top' else L if face=='front' else W;hh=LOW if face=='top' else H;fs=ld_face_data(face)
    functional=[f for f in fs if f['kind']=='feature'];ym=0
    if face in ('left','right') and len(functional)>4 and min(f['y'] for f in functional)>hh*.5:
        ym=max(0,min(f['y'] for f in functional)-18)
    if ym:
        for rect in JOB.get('rect_cutouts') or []:
            target='left' if rect['part_id']=='END_L' else 'right' if rect['part_id']=='END_R' else 'front'
            if target==face:ym=min(ym,max(0,rect['center'][2]-rect['size_xy'][1]/2-6))
    ymax=hh;scale=min((cw-58)/ww,(ch-39)/(ymax-ym));gx=(cw-ww*scale)/2;gy=24
    title={'front':'正视','right':'右端外视','left':'左端外视','top':'盖顶俯视'}[face]
    a.text(cw/2,ch-2,title+('｜上部放大，Z仍自箱底' if ym else ''),fontsize=FS_NOTE,ha='center',va='top',color=NAVY)
    fn={'front':lambda u,v:(v,-u),'right':lambda u,v:(-v,u),'left':lambda u,v:(W+v,-u),'top':lambda u,v:(u+OH,v+OH)}[face]
    # Clip projection to the local diagram, not to unrelated dimensions.
    va=fig.add_axes([(ox+gx)/PW,(oy+gy)/PH,ww*scale/PW,(ymax-ym)*scale/PH]);va.set(xlim=(0,ww),ylim=(ym,ymax));va.axis('off');va.s=scale
    view(va,'LID' if face=='top' else 'ASSEMBLY',face,fn,hidden=False)
    coordsx=[0,ww]+[f['x'] for f in fs];coordsy=[ym,ymax]+[f['y'] for f in fs if f['y']>=ym]
    ld_chain(a,coordsx,gx,scale,gy,'X',6)
    ld_chain(a,coordsy,gy-ym*scale,scale,gx+ww*scale,'Y',7)
    dimh(a,gx,gx+ww*scale,gy-19,gy,gy,f'{od_n(ww)}'+(' 盖外' if face=='top' else ' 箱体'))
    if JOB.get('show_review_overall_dimensions') and not ym:
        dimv(a,gy,gy+hh*scale,gx+ww*scale+20,gx+ww*scale,gx+ww*scale,
             f'{od_n(hh)}'+(' 盖宽' if face=='top' else ' 含盖高'))
    # Unique diameter/shape group, not a separate four-line leader for every identical hole.
    groups={}
    for f in fs:
        if f['kind']=='fix':continue
        groups.setdefault(f['text'],[]).append(f)
    for text,group in groups.items():
        f=min(group,key=lambda q:abs(q['x']-ww/2));pt=(gx+f['x']*scale,gy+(f['y']-ym)*scale)
        label=(f'{len(group)}×' if len(group)>1 else '')+text
        if f['kind']=='handle':label+='\n4×Ø6.6；85/62/30'
        ld_label(a,pt,label,(0,cw,21,ch-7))
    mounts=[f for f in fs if f['kind']=='fix']
    if mounts:a.text(2,ch-10,f'本面{len(mounts)}对M4；体Ø3.3／裙Ø4.5',fontsize=FS_NOTE,color=BLU)
    if ym:
        for z in sorted({f['y'] for f in functional}):
            zz=gy+(z-ym)*scale;a.plot([gx-2,gx],[zz,zz],color=BLU,lw=.4);a.text(gx-3,zz,'Z'+od_n(z),fontsize=FS_NOTE,color=BLU,ha='right',va='center')
        a.plot([gx-2,gx,gx+2],[gy-1,gy+1,gy-1],color='k',lw=.6);a.text(2,4,f'下截面Z{od_n(ym)}，非零点',fontsize=FS_NOTE,color=BLU)
    _LD_RECORDS.append(dict(kind='face',face=face,chain_x=sorted(set(coordsx)),chain_y=sorted(set(coordsy)),panel=[ox,oy,cw,ch],crop_y=ym))
    for txt in a.texts:txt.set_bbox(dict(facecolor='white',edgecolor='none',pad=.4))

def ordinary_overview(pdf):
    if not JOB.get('ordinary_local_dimensions_review'):return _ld_old_overview(pdf)
    fig,ax=ordinary_new_page(1)
    ia=fig.add_axes([12/PW,211/PH,92/PW,43/PH]);ia.imshow(np.asarray(Image.open(JOB['customer_image'])));ia.axis('off');ia.set_title('客户原图',fontsize=FS_NOTE,loc='left')
    ordinary_iso(fig,'ASSEMBLY',112,211,82,43)
    for i,txt in enumerate([f'订单{JOB.get("order_id","")}；数量{JOB.get("quantity",1)}',f'箱体外{L:g}×{W:g}；体高{od_n(rep["params"]["Hb"])}；含盖{H:g}',f'盖外{LOL:g}×{LOW:g}；四边裙15；材质201 t{t:g}',f'四边{len(rep["holes"])}对M4；孔距按各面尺寸链', '孔心定位；盖从实际外边量；mm。把手孔型见第5页。']):ax.text(210,250-i*7,txt,fontsize=FS_NOTE,color=NAVY)
    for j,note in enumerate(JOB.get('local_review_notes') or []):ax.text(210,215-j*6,note,fontsize=FS_NOTE,color=REDC)
    for f,x,y in [('front',12,114),('right',218,114),('left',12,22),('top',218,22)]:ld_face_panel(fig,f,x,y,190,87)
    save_page(pdf,fig)

def ld_native_features(name):
    p=P[name];allc=sorted(p['flat_circles']);features=[];handle_points=[]
    for i,(x,y,d) in enumerate(allc,1):
        if name=='LID' and abs(d-6.6)<1e-5:handle_points.append((x,y,d));continue
        features.append(dict(x=x,y=y,text=f'Ø{od_n(d)}',id=f'F{i:02}',kind='fix' if abs(d-(4.5 if name=='LID' else 3.3))<1e-5 else 'feature'))
    # Preserve independent rotations; centre average is the actual four-hole pattern centre.
    remaining=handle_points[:]
    while remaining:
        seed=remaining[0];group=sorted(remaining,key=lambda q:math.dist(q[:2],seed[:2]))[:4]
        if len(group)!=4:raise ValueError('handle group incomplete')
        for q in group:remaining.remove(q)
        cx=sum(q[0] for q in group)/4;cy=sum(q[1] for q in group)/4
        features.append(dict(x=cx,y=cy,text=f'把手 {len([f for f in features if f["kind"]=="handle"])+1}',kind='handle',holes=group))
    for i,(x0,y0,x1,y1) in enumerate(sorted(p.get('flat_rectangles') or []),1):features.append(dict(x=(x0+x1)/2,y=(y0+y1)/2,text=f'R{i} {od_n(x1-x0)}×{od_n(y1-y0)}',kind='feature'))
    return features

def ld_native_panel(fig,name,ox,oy,cw,ch,with_bends=True):
    a=ld_axes(fig,ox,oy,cw,ch);fx,fy=P[name]['flat_size'];scale=min((cw-80)/fx,(ch-69)/fy);gx=(cw-fx*scale)/2;gy=34
    for wire in flats[name]['wires']:pl(a,[(gx+x*scale,gy+y*scale) for x,y in wire+[wire[0]]],lw=.7)
    features=ld_native_features(name)
    xs=[0,fx]+[f['x'] for f in features];ys=[0,fy]+[f['y'] for f in features]
    ld_chain(a,xs,gx,scale,gy,'X',6);ld_chain(a,ys,gy,scale,gx+fx*scale,'Y',7)
    dimh(a,gx,gx+fx*scale,gy-21,gy,gy,f'展开长{od_n(fx)}');dimv(a,gy,gy+fy*scale,gx-8,gx,gx,f'展开宽{od_n(fy)}')
    if with_bends:
        BB=bidir(rep,name)
        for axis in ('X','Y'):
            vals=BB[axis]
            # Only a few native fold lines: each gets both edge offsets at the local side.
            for i,b in enumerate(vals):
                pos=b['pos']
                if axis=='X':
                    dimh(a,gx,gx+pos*scale,gy+fy*scale+8+i*7,gy+fy*scale,gy+fy*scale,f'{b["id"]}左{od_n(pos)}')
                    dimh(a,gx+pos*scale,gx+fx*scale,gy-28-i*7,gy,gy,f'右{od_n(fx-pos)}')
                else:
                    dimv(a,gy,gy+pos*scale,gx-17-i*7,gx,gx,f'{b["id"]}下{od_n(pos)}')
                    dimv(a,gy+pos*scale,gy+fy*scale,gx+fx*scale+20+i*7,gx+fx*scale,gx+fx*scale,f'上{od_n(fy-pos)}')
            if len(vals)==2:
                u,v=vals
                if axis=='X':dimh(a,gx+u['pos']*scale,gx+v['pos']*scale,gy+fy*scale+24,gy+fy*scale,gy+fy*scale,f'{u["id"]}–{v["id"]} {od_n(v["pos"]-u["pos"])}')
                else:dimv(a,gy+u['pos']*scale,gy+v['pos']*scale,gx+fx*scale+35,gx+fx*scale,gx+fx*scale,f'{u["id"]}–{v["id"]} {od_n(v["pos"]-u["pos"])}')
        for b in P[name]['bend_records']:
            p,q=b['flat_line_mm'];sp=[(gx+x*scale,gy+y*scale) for x,y in (p,q)];pl(a,sp,color=REDC,lw=.8)
            pt=((sp[0][0]+sp[1][0])/2,(sp[0][1]+sp[1][1])/2)
            # B number printed directly beside its own line; no long sequence-card leader.
            a.text(pt[0]+2,pt[1]+2,b['id'],fontsize=FS_NOTE,color=REDC)
    groups={}
    for f in features:groups.setdefault(f['text'],[]).append(f)
    for text,group in groups.items():
        # Each diameter or repeated pattern labelled next to an actual feature, no page-wide fans.
        f=min(group,key=lambda q:abs(q['x']-fx/2)+abs(q['y']-fy/2));label=(f'{len(group)}×' if len(group)>1 else '')+text
        if f['kind']=='handle':label+='\n4×Ø6.6，孔型见第5页'
        ld_label(a,(gx+f['x']*scale,gy+f['y']*scale),label,(1,cw-1,gy-1,ch-6))
    for txt in a.texts:txt.set_bbox(dict(facecolor='white',edgecolor='none',pad=.4))
    _LD_RECORDS.append(dict(kind='native',part=name,circle_count=len(P[name]['flat_circles']),rect_count=len(P[name].get('flat_rectangles',[])),chain_x=sorted(set(xs)),chain_y=sorted(set(ys)),handle_groups=[f for f in features if f['kind']=='handle'],panel=[ox,oy,cw,ch]))

def ordinary_piece_page(pdf,name,page):
    if not JOB.get('ordinary_local_dimensions_review'):return _ld_old_piece(pdf,name,page)
    fig,ax=ordinary_new_page(page);ax.text(12,252,f'{name} 真实展开｜尺寸按位置围绕本图排列｜外表面朝读者',fontsize=FS_TITLE,color=NAVY)
    ax.text(12,241,'孔心链尺寸含两端板边；相同孔径共用数量标注。把手按中心定位＋第5页完整孔型。单位mm。',fontsize=FS_NOTE,color=BLU)
    ip=render_assy_iso_png(R/'PREVIEW'/f'{VER}_{name}_local_iso.png',[name]);ia=fig.add_axes([344/PW,240/PH,60/PW,16/PH]);ia.imshow(plt.imread(ip));ia.axis('off')
    ld_native_panel(fig,name,12,49,396,184)
    rows=sorted(P[name]['bend_records'],key=lambda b:-math.dist(*b['flat_line_mm']))
    for i,b in enumerate(rows):
        ax.text(12+i*99,34,f'{i+1}. {b["id"]} {b["direction"]} 90°\n折线长{od_n(math.dist(*b["flat_line_mm"]))}',fontsize=FS_NOTE,color=BLU)
    ax.text(12,18,f'Ri{ri:g} / Ro{ri+t:g}；K{K:.5f}；先长后短。UP朝读者，DOWN背向读者；机床靠面/挡料须首件校准。',fontsize=FS_NOTE,color=REDC)
    save_page(pdf,fig)

def ordinary_end_page(pdf):
    if not JOB.get('ordinary_local_dimensions_review'):return _ld_old_end(pdf)
    fig,ax=ordinary_new_page(3);ax.text(12,252,'两端板真实展开｜各件独立尺寸链，不跨图拉线',fontsize=FS_TITLE,color=NAVY)
    for name,x in [('END_L',12),('END_R',218)]:
        ax.text(x,240,name+' 外视｜零折；Y′=Z',fontsize=FS_NOTE,color=NAVY)
        ip=render_assy_iso_png(R/'PREVIEW'/f'{VER}_{name}_local_iso.png',[name]);ia=fig.add_axes([(x+157)/PW,235/PH,30/PW,14/PH]);ia.imshow(plt.imread(ip));ia.axis('off')
        ld_native_panel(fig,name,x,40,190,187,with_bends=False)
    ax.text(12,24,'左端X′=W−Y；右端X′=Y；相同孔径按数量共用标注。底角内R'+od_n(ri)+'／外R'+od_n(ri+t)+'。',fontsize=FS_NOTE,color=BLU)
    ax.text(12,16,'Ø3.3为攻M4底孔；盖裙Ø4.5。完整圆孔/方口四向坐标CSV仍随完整包保留。',fontsize=FS_NOTE,color=REDC)
    save_page(pdf,fig)

def source_side_region_overview(pdf):
    if STRUCTURE!='u_endplates' or _TOP4 or HANDLE_CX or JOB.get('lid_ports') or JOB.get('rect_cutouts'):
        raise ValueError('source side-region overview requires two external end panels and no roof features')
    if JOB['source_side_region']!={'wall':3,'width':224,'height':192,'origin_physical':[3,3],'functional_source_UI_left':[55,95,135,175],'functional_source_UI_bottom':130,'functional_physical_left':[58,98,138,178],'functional_physical_Z':133} or (L,W,H)!=(420,230,195):
        raise ValueError('source_side_region overview is scoped to the audited 420x230x195 source-frame case')
    fig,ax=ordinary_new_page(1)
    ia=fig.add_axes([12/PW,191/PH,98/PW,63/PH]);ia.imshow(np.asarray(Image.open(JOB['customer_image'])),interpolation='none',resample=False);ia.axis('off');ia.set_title('客户原图（原样）',fontsize=FS_NOTE,loc='left')
    ld_face_panel(fig,'top',117,186,125,69)
    ax.text(12,179,f'订单{JOB["order_id"]}；序号002；201不锈钢 t{t:g}',fontsize=FS_NOTE,color=NAVY)
    ax.text(12,172,f'箱体外{L:g}×{W:g}；含盖高{H:g}；长宽不含盖',fontsize=FS_NOTE,color=BLU)
    ax.text(12,165,f'盖外{LOL:g}×{LOW:g}；四边裙15；盖体12对M4',fontsize=FS_NOTE,color=BLU)
    ax.text(12,158,'源区O距本面物理左/底3；源孔高130＝箱底133',fontsize=FS_NOTE,color=GRN)
    for part,ox,title in [('END_L',254,'左侧把手'),('END_R',334,'右侧把手')]:
        hh=[q for q in JOB['panel_holes']if q['part_id']==part and q.get('purpose')=='handle'];assert len(hh)==4
        pts=[(W-h['point'][1]if part=='END_L'else h['point'][1],h['point'][2])for h in hh];cx=sum(x for x,y in pts)/4;cz=sum(y for x,y in pts)/4
        a=ld_axes(fig,ox,191,72,63);a.text(36,62,title+'｜4×Ø6.6',fontsize=FS_NOTE,color=NAVY,ha='center');sc=.40;gx=36;gy=31
        for x,z in pts:a.add_patch(Circle((gx+(x-cx)*sc,gy+(z-cz)*sc),3.3*sc,fill=False,ec=REDC,lw=.65))
        a.plot(gx,gy,'+',color=GRN,ms=4)
        dimh(a,gx-42.5*sc,gx+42.5*sc,gy-6-8,gy-6,gy-6,'85')
        dimh(a,gx-31*sc,gx+31*sc,gy+6+7,gy+6,gy+6,'62')
        dimv(a,gy-6,gy+6,gx+42.5*sc+8,gx+42.5*sc,gx+31*sc,'30')
        a.text(36,3,f'孔组中心：距面左{cx:g} / 箱底{cz:g}',fontsize=FS_NOTE,color=BLU,ha='center')
    for face,x,w in [('front',12,125),('right',147,125),('left',282,126)]:
        ld_face_panel(fig,face,x,23,w,127)
        aa=next(a for a in fig.axes if getattr(a,'_ld_panel',None)==(x,23,w,127));ww=L if face=='front'else W;sc=min((w-58)/ww,(127-39)/H);xx=(w-ww*sc)/2+ww*sc
        dimv(aa,24,24+H*sc,xx+20,xx,xx,f'含盖{H:g}')
    # A source-origin marker and two true dimensions on the actual LEFT outward projection.
    a=next(a for a in fig.axes if getattr(a,'_ld_panel',None)==(282,23,126,127));scale=min((126-58)/W,(127-39)/H);gx=(126-W*scale)/2;gy=24
    for x0,x1 in zip([58,98,138],[98,138,178]):dimh(a,gx+x0*scale,gx+x1*scale,gy+169*scale,gy+133*scale,gy+133*scale,'40')
    a.plot(gx+3*scale,gy+3*scale,'+',color=GRN,ms=5)
    a.text(gx-2,gy+1,'O(3,3)',fontsize=FS_NOTE,color=GRN,ha='right')
    dimv(a,gy+3*scale,gy+133*scale,gx-10,gx+3*scale,gx+58*scale,'源130',c=GRN)
    dimv(a,gy,gy+133*scale,gx-23,gx,gx+58*scale,'箱底133')
    ax.text(12,16,'孔心尺寸，单位mm；前后固定孔同排。Ri/K、薄板M4与把手承重须首件试折试装；非批量放行。',fontsize=FS_NOTE,color=REDC)
    save_page(pdf,fig)

def image_dimension_priority_overview(pdf):
    if STRUCTURE!='u_endplates' or (L,W,H,t)!=(445,220,160,1) or _TOP4 or len(HANDLE_CX)!=2 or JOB.get('lid_ports') or JOB.get('rect_cutouts'):
        raise ValueError('image_dimension_priority_review is scoped to the audited445x220x160 case')
    hs=sorted((W-h['point'][1],h['point'][2],h['diameter'])for h in JOB['panel_holes'])
    if hs!=[(30,125,12),(60,125,10),(100,125,10)] or sorted(zip(HANDLE_CX,HANDLE_CYS))!=[(109.75,108.5),(332.25,108.5)]:
        raise ValueError('latest physical drawing dimensions were not applied')
    fig,ax=ordinary_new_page(1)
    for i,path in enumerate(JOB['customer_images']):
        ia=fig.add_axes([(12+i*51)/PW,193/PH,49/PW,61/PH]);ia.imshow(np.asarray(Image.open(path)),interpolation='none',resample=False);ia.axis('off');ia.set_title('客户原图'+str(i+1),fontsize=FS_NOTE,loc='left')
    ax.text(12,181,f'订单{JOB["order_id"]}；序号004；201不锈钢 t{t:g}',fontsize=FS_NOTE,color=NAVY)
    ax.text(12,174,f'箱体外{L:g}×{W:g}；含盖高{H:g}；长宽不含盖',fontsize=FS_NOTE,color=BLU)
    ax.text(12,167,f'盖外{LOL:g}×{LOW:g}；四边裙15；盖体{len(rep["holes"])}对M4',fontsize=FS_NOTE,color=BLU)
    ax.text(12,160,'孔位以最新客户图为准：侧孔距箱底125',fontsize=FS_NOTE,color=REDC)
    # Actual roof projection with physical cover-edge centre dimensions.
    a=ld_axes(fig,117,173,194,84);a.text(97,83,'盖顶俯视｜孔心距实际盖边',fontsize=FS_NOTE,color=NAVY,ha='center',va='top');sc=min(158/LOL,58/LOW);gx=(194-LOL*sc)/2;gy=18
    view(a,'LID','top',lambda u,v:(gx+(u+OH)*sc,gy+(v+OH)*sc),hidden=False)
    xx=[0,111.25,333.75,LOL]
    for u,v in zip(xx,xx[1:]):dimh(a,gx+u*sc,gx+v*sc,gy-5,gy,gy,od_n(v-u))
    dimh(a,gx,gx+LOL*sc,gy-14,gy,gy,f'{LOL:g} 盖外')
    xend=gx+LOL*sc
    dimv(a,gy,gy+110*sc,xend+7,xend,xend,'110')
    dimv(a,gy+110*sc,gy+LOW*sc,xend+7,xend,xend,od_n(LOW-110))
    dimv(a,gy,gy+LOW*sc,xend+18,xend,xend,f'{LOW:g} 盖外')
    for cx,rot in [(111.25,270),(333.75,90)]:
        a.plot(gx+cx*sc,gy+110*sc,'+',color=GRN,ms=4)
        a.text(gx+cx*sc,gy+110*sc+18,str(rot)+'°',ha='center',fontsize=FS_NOTE,color=BLU)
    # Both actual trapezoid orientations, with pitches immediately beside each pattern.
    for ox,cx,rot,label in [(316,111.25,270,'左'),(362,333.75,90,'右')]:
        aa=ld_axes(fig,ox,180,44,75);aa.text(22,74,label+'把手 '+str(rot)+'°',ha='center',va='top',fontsize=FS_NOTE,color=NAVY);sgn=1 if rot==90 else -1;scale=.34;xc=22;yc=42
        xw=xc+sgn*15*scale;xn=xc-sgn*15*scale
        for x,pitch in [(xw,85),(xn,62)]:
            for side in [-1,1]:aa.add_patch(Circle((x,yc+side*pitch/2*scale),3.3*scale,fill=False,ec=REDC,lw=.65))
        dimv(aa,yc-42.5*scale,yc+42.5*scale,xw+sgn*6,xw,xw,'85')
        dimv(aa,yc-31*scale,yc+31*scale,xn-sgn*6,xn,xn,'62')
        dimh(aa,min(xw,xn),max(xw,xn),yc-42.5*scale-7,yc-42.5*scale,yc-42.5*scale,'30')
        aa.text(22,13,'4×Ø6.6 M6过孔',ha='center',fontsize=FS_NOTE,color=BLU)
        aa.text(22,7,'盖左'+od_n(cx),ha='center',fontsize=FS_NOTE,color=BLU)
        aa.text(22,1,'盖下110',ha='center',fontsize=FS_NOTE,color=BLU)
    for face,x,w in [('front',12,125),('right',147,125),('left',282,126)]:
        ld_face_panel(fig,face,x,23,w,127)
        aa=next(a for a in fig.axes if getattr(a,'_ld_panel',None)==(x,23,w,127));ww=L if face=='front'else W;scale=min((w-58)/ww,(127-39)/H);gx=(w-ww*scale)/2;xe=gx+ww*scale
        dimv(aa,24,24+H*scale,xe+20,xe,xe,f'含盖{H:g}')
    # Explicit functional chain and absolute height, kept apart from the fixing row.
    aa=next(a for a in fig.axes if getattr(a,'_ld_panel',None)==(282,23,126,127));sc=min((126-58)/W,(127-39)/H);gx=(126-W*sc)/2;gy=24
    dimv(aa,gy,gy+125*sc,gx-15,gx,gx+30*sc,'孔心高125')
    for x0,x1 in [(0,30),(30,60),(60,100)]:dimh(aa,gx+x0*sc,gx+x1*sc,gy+108*sc,gy+125*sc,gy+125*sc,od_n(x1-x0))
    ax.text(12,16,'孔心尺寸，单位mm；前后固定孔同排。Ri/K、薄板M4与把手承重须首件试折试装；非批量放行。',fontsize=FS_NOTE,color=REDC)
    save_page(pdf,fig)

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
if JOB.get('ordinary_side_fixings_review'):
    NPAGES=5+len(_REQ_PAGES)
    with PdfPages(_candidate) as pdf:ordinary_side_fixing_pages(pdf)
elif STRUCTURE == 'u_l_t7u' and not JOB.get('compact_wrap_review'):
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
        if (JOB.get('battery_lid_edge_review') or JOB.get('battery_lid_region_review')):
            fig=draw_battery_lid_edge_overview();save_page(pdf,fig)
        elif JOB.get('dual_end_interfaces_review'):
            fig=draw_dual_end_overview();save_page(pdf,fig)
        elif JOB.get('lid_pair_end_review'):
            fig=draw_lid_pair_end_overview();save_page(pdf,fig)
        else:
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
            if not JOB.get('compact_panel_review') and not JOB.get('handle_pair_review') and not JOB.get('lid_two_circle_review'):
                a.text(L * 0.12, Hb*.4 if (_PANEL or JOB.get('handle_pair_review')) else ZH - 28, (('盖顶四角4×M4；焊接支承片见第5页' if _TOP_SUPPORTS else '盖顶四角4孔；螺钉承接结构未定') if _TOP4 else f'长边每侧 M4×{len(LONG_X)}  Z={ZH:g}（Ø3.3攻 / 盖Ø4.5）'), fontsize=_fs(9.4), color=BLU)
            if not JOB.get('compact_panel_review') and not JOB.get('handle_pair_review') and not JOB.get('lid_two_circle_review'):
                a.text(L * 0.12, 35, f'盖裙下沿 Z={H - skirt:g}；箱体顶 Z={Hb:g}；顶隙 q={q:g}', fontsize=_fs(9.4))
            if JOB.get('compact_panel_review'):
                front=sorted([h for h in _PANEL if h['part_id']=='U'],key=lambda h:h['point'][0])
                for i,h in enumerate(front):
                    xx,_,zz=h['point']
                    dimh(a,-OH,xx,92-24*i,-OH,zz,f'{xx+OH:g}')
                if front:
                    xx,_,zz=front[0]['point']
                    dimv(a,0,zz,L*.74,xx,xx,f'{zz:g}')
                    a.text(L*.58,H*.62,f'{len(front)}×Ø{front[0]["diameter"]:g}',fontsize=FS_NOTE,color=BLU)
                for left,right in zip(front,front[1:]):
                    dimh(a,left['point'][0],right['point'][0],128,left['point'][2],right['point'][2],f'{right["point"][0]-left["point"][0]:g}')
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
            a2.text(15, 35, ((f'箱体侧面 {W:g}×{Hb:g}' if STRUCTURE=='u_l_t7u' else f'端板 {W:g}×{Hb:g}；零折') if _TOP4 else f'每侧 M4×{len(SHORT_Y)}；端板 {W:g}×{Hb:g}'), fontsize=_fs(9.4), color=BLU)
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
            a2.text(8, 65, '端板把手坐标见附页' if _PANEL_HANDLES else ('端板功能孔见第3页' if _END_HOLES else ('箱体无功能孔' if STRUCTURE=='u_l_t7u' else '端板无功能孔')), fontsize=_fs(9.4), color=REDC)
            # --- 俯视图 top: length × width ---
            sT = min(0.45 if JOB.get('handle_pair_review') else 0.32, 190 / (L + 110), (146 if JOB.get('handle_pair_review') else 118) / (W + 120))
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
                a3.text(cx, HANDLE_CY + 55, (f'把手\n盖左下({cx+OH:g},{HANDLE_CY+OH:g})' if _TOP4 else f'把手\n({cx:g},{HANDLE_CY:g})'), fontsize=_fs(9.4), ha='center', color=BLU)
            for h in LID_HOLES:
                a3.add_patch(Circle((h['x'], h['y']), h['d'] / 2, fill=False, ec=REDC, lw=0.6))
            if not JOB.get('handle_pair_review') and not JOB.get('lid_two_circle_review'):
                hole_labels(a3, [h for h in LID_HOLES if not (_TOP4 and h["id"].startswith("F"))])
            if _TOP4:
                for item in _TOP4:
                    xx, yy, _ = item['formed']
                    a3.add_patch(Circle((xx,yy),2.25,fill=False,ec=REDC))
                # Actual baseline/chain dimensions; all values use this order's geometry.
                ports=sorted(JOB.get('lid_ports') or [],key=lambda h:h['y'])
                if ports and JOB.get('lid_two_circle_review'):
                    if len(ports)!=2 or len(HANDLE_CX)!=1 or _PANEL or _RECTS or _TOP_SUPPORTS:
                        raise ValueError('lid_two_circle_review requires two lid circles, one lid handle, and lid-only fixings')
                    lower,upper=ports
                    for i,port in enumerate(ports):
                        xx,yy=port['x'],port['y']
                        dimh(a3,-OH,xx,-12 if i==0 else W+4,-OH,yy,f'{xx+OH:g}')
                        dimv(a3,-OH if i==0 else yy,yy if i==0 else W+OH,xx+29,xx,xx,f'{yy+OH if i==0 else W+OH-yy:g}')
                        a3.annotate(f'P{i+1} Ø{port["d"]:g}',(xx,yy),(xx+(35 if i==0 else 90),yy+(20 if i==0 else -2)),fontsize=FS_NOTE,color=REDC,arrowprops=dict(arrowstyle='-',color=REDC,lw=.4))
                    dimv(a3,lower['y'],upper['y'],upper['x']+59,lower['x'],upper['x'],f'Y心距{upper["y"]-lower["y"]:g}')
                    a3.annotate(f'两孔X差{abs(upper["x"]-lower["x"]):g}',(upper['x'],upper['y']),(-30,W*.66),fontsize=FS_NOTE,color=BLU,arrowprops=dict(arrowstyle='-',color=BLU,lw=.4))
                elif ports:
                    xx=ports[0]['x']; ys=[h['y'] for h in ports]
                    dimh(a3,-OH,xx,24,-OH,ys[0],f'{xx+OH:g}')
                    for low,high in zip([-OH]+ys,ys):
                        dimv(a3,low,high,xx+30,xx,xx,f'{high-low:g}')
                    if len(ys)>1: dimv(a3,ys[0],ys[-1],xx+65,xx,xx,f'{ys[-1]-ys[0]:g}')
                    a3.text(xx+48,ys[-1]+15,f'{len(ports)}×Ø{ports[0]["d"]:g}',fontsize=FS_NOTE,color=BLU)
                for i,cx in enumerate(HANDLE_CX):
                    dimh(a3,-OH,cx,(-42 if JOB.get('lid_two_circle_review') else (-14-20*i if JOB.get('handle_pair_review') else (-60-18*i if JOB.get('lid_rectangles') else 42+24*i))),-OH,HANDLE_CY,f'{cx+OH:g}')
                    if not JOB.get('handle_pair_review'):
                        dimv(a3,-OH,HANDLE_CY,cx+70,cx,cx,f'{HANDLE_CY+OH:g}')
                if JOB.get('handle_pair_review'):
                    centers=sorted(HANDLE_CX)
                    dimv(a3,-OH,HANDLE_CY,L+14,centers[-1],centers[-1],f'{HANDLE_CY+OH:g}')
                    for left,right in zip(centers,centers[1:]):
                        dimh(a3,left,right,W+16,HANDLE_CY,HANDLE_CY,f'心距{right-left:g}')
                if not JOB.get('lid_rectangles') and not JOB.get('handle_pair_review') and not JOB.get('lid_two_circle_review'):
                    a3.text(L*.22,W*.9,'4×Ø6.6；宽排85/窄排62/排距30',fontsize=FS_NOTE,color=BLU)
                for i,rect in enumerate(JOB.get('lid_rectangles') or []):
                    xx,yy=rect['center'];ww,hh=rect['size']
                    dimh(a3,xx-ww/2,xx+ww/2,yy+hh/2+12,yy+hh/2,yy+hh/2,f'{ww:g}')
                    dimv(a3,yy-hh/2,yy+hh/2,xx-ww/2-12,xx-ww/2,xx-ww/2,f'{hh:g}')
                    dimh(a3,-OH,xx,-18-i*18,-OH,yy,f'{xx+OH:g}')
                    dimv(a3,-OH,yy,xx+ww/2+12+i*18,xx,xx,f'{yy+OH:g}')
                    a3.text(xx,yy,rect['id'],fontsize=FS_NOTE,color=REDC,ha='center')
                rr=JOB.get('lid_rectangles') or []
                if len(rr)==2:
                    xx=rr[0]['center'][0];y1,y2=sorted(r['center'][1] for r in rr)
                    dimv(a3,y1,y2,xx+64,xx,xx,f'心距{y2-y1:g}')

                dimh(a3,-OH,_FIX_X[0]-OH,W+22,W,W,f'{_FIX_X[0]:g}')
                dimv(a3,-OH,_FIX_Y[0]-OH,L+20,L,L,f'{_FIX_Y[0]:g}')

            # --- 装配轴测：2D iso solid + outer dim arrows (ref 001 isoview L/W/H) t107u/t109u ---
            if HAS_HANDLES and HANDLE_MOUNT in ('END_L+END_R','END_R','END_L'):
                _iso_parts = ['U', 'END_L', 'END_R', 'LID'] + [f'HANDLE_REF_{p[-1]}' for p in HANDLE_PARTS]
            elif HAS_HANDLES and HANDLE_CX:
                # LID_TOP: build.py names HANDLE_REF_L if cx<L/2 else HANDLE_REF_R (center → R)
                _iso_parts = ['U', 'END_L', 'END_R', 'LID'] + [f'HANDLE_REF_{"L" if cx < L/2 else "R"}' for cx in HANDLE_CX]
            else:
                _iso_parts = ['U', 'END_L', 'END_R', 'LID']
            if STRUCTURE == 'u_l_t7u': _iso_parts = ['U','L','LID']
            if _TOP_SUPPORTS: _iso_parts += ['TAB'+str(i+1) for i in range(len(_TOP4))]
            _iso_dir = ORDER / 'logs' / 'iso'; _iso_dir.mkdir(parents=True, exist_ok=True)
            _iso_png = render_assy_iso_png(_iso_dir / f'{VER}_ASSEMBLY_iso.png', _iso_parts, exploded=False)
            _exp_png = render_assy_iso_png(_iso_dir / f'{VER}_EXPLODED_iso.png', _iso_parts, exploded=True)
            try:
                _prev = R / 'PREVIEW'; _prev.mkdir(parents=True, exist_ok=True)
                (_prev / f'{VER}_ASSEMBLY_iso.png').write_bytes(_iso_png.read_bytes())
                (_prev / f'{VER}_EXPLODED_iso.png').write_bytes(_exp_png.read_bytes())
            except Exception:
                pass
            # Customer source stays unmodified; actual model remains beside the review views.
            customer_image = JOB.get('customer_image')
            if customer_image:
                customer_path = Path(customer_image)
                if not customer_path.is_file():
                    raise ValueError('Customer image missing: '+str(customer_path))
                customer_ax = fig.add_axes([.51, 75/PH, .25, 90/PH])
                customer_ax.imshow(np.asarray(Image.open(customer_path)), interpolation="none", resample=False); customer_ax.set_axis_off()
                customer_ax.set_title('客户原图（原样）', fontsize=FS_TITLE, loc='left')
                a3d = fig.add_axes([270/PW, 17/PH, 50/PW, 43/PH])
            else:
                a3d = fig.add_axes([0.51, 0.23, 0.25, 0.28])
            a3d.imshow(plt.imread(str(_iso_png))); a3d.set_axis_off()
            a3d.set_title(f'装配轴测  {OUTER_L:g}×{OUTER_W:g}×{H:g}', fontsize=_fs(9.4), loc='left')
            if _TOP4:
                ha=vax(fig,220,20,(-25,65),(-65,65),.34,('右把手孔型；左件反向；各4×Ø6.6' if JOB.get('handle_pair_review') else '把手安装孔局部：4×Ø6.6'))
                for xx,pitch in ([(30,85),(0,62)] if (JOB.get('handles') or {}).get('rotations')==[90] else [(0,85),(30,62)]):
                    for yy in [-pitch/2,pitch/2]:ha.add_patch(Circle((xx,yy),3.3,fill=False,ec=BLU))
                if (JOB.get('handles') or {}).get('rotations')==[90]:
                    dimv(ha,-42.5,42.5,45,30,30,'85');dimv(ha,-31,31,-15,0,0,'62')
                else:
                    dimv(ha,-42.5,42.5,-15,0,0,'85');dimv(ha,-31,31,45,30,30,'62')
                dimh(ha,0,30,-52,-42.5,-31,'30')
            elif not customer_image:
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
                ('· 件1 U：三面围板' if STRUCTURE=='u_l_t7u' else '· 件1 U：底+两长侧壁'),
                ('· 件2 L：底＋前侧，一折' if STRUCTURE=='u_l_t7u' else '· 件2/3 外封端板零折'),
                '  拼缝0/不退让/齐口',
                f'· {"件3" if STRUCTURE=="u_l_t7u" else "件4"} 盖裙{skirt:g} 03角缝候选0.2',
                *(['· 件5-8：4块25×25×0.8角部支承片'] if _TOP_SUPPORTS else []),
                f'· 把手：{_HDL_LINE}',
                *([JOB['customer_image_note']] if JOB.get('customer_image_note') else []),
                *([JOB['review_datum_note']] if JOB.get('review_datum_note') else []),
                f'· 盖顶孔共{len(LID_HOLES)}个（含把手及固定）',
                '· 功能孔及把手坐标见附页' if _PANEL else ('· 箱体无孔；L件展开见第3页' if STRUCTURE=='u_l_t7u' else ('· 功能孔仅盖顶；端板无孔' if JOB.get('lid_two_circle_review') else '· 端板功能孔见第3页')),
                (('· 盖顶4×Ø4.5；支承片Ø3.3攻M4' if _TOP_SUPPORTS else '· 盖顶4×Ø4.5；承接结构未定 HOLD') if _TOP4 else '· 仍开盖-体M4（规则4/23）'),
                f'· {_SKIRT_NOTE}',
                ('待确认', REDC),
                '· 端板接合/RiK/角缝',
                '· 薄板攻M4替代',
                ('· 四角小边距/螺钉承接结构待核' if JOB.get('handle_pair_review') else '· 法兰用途/卫星是否改攻丝'),
            ], title='关键参数', fs=_fs(9.4))
            box(ax, 330, 25, 82, 55, [
                (f'盖顶四角：距邻边{_FIX_X[0]:g}' if _TOP4 else f'长X={"/".join(f"{x:g}" for x in LONG_X)}'),
                (f'孔心X：{_FIX_X[0]:g} / {_FIX_X[-1]:g}' if _TOP4 else f'短Y={"/".join(f"{y:g}" for y in SHORT_Y)}'),
                (f'孔心Y：{_FIX_Y[0]:g} / {_FIX_Y[-1]:g}' if _TOP4 else f'Z={ZH:g}；箱Ø3.3/盖Ø4.5')
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
            (f'U三面围板：折线长{math.dist(*P["U"]["bend_records"][0]["flat_line_mm"]):g}，两折；夹持与翻面需首件核验' if STRUCTURE=='u_l_t7u' else f'U：弯线沿长{L-2*t:g}；第2道侧壁高{Hb:g}、内宽{W-2*t:g} — 深U折弯避让 WARN'),
            f'拼缝0、inset0、上边齐口；接合=内侧角焊或外侧激光焊（待确认）',
            (f'BD={BD:.4f}；实际U展开{ufx:.2f}×{ufy:.2f}' if STRUCTURE=='u_l_t7u' else f'BD={BD:.4f}；U展开宽公式 {W:g}+2×{Hb:g}−2×BD = {W+2*Hb-2*BD:.2f}'),
            f'视觉：参考 S-201-1-20261031-001-v1；字号≥{MINPT}pt；拥挤则加页不缩字',
            '处理面朝外（规则31）；展开外表面朝读者',
        ] + (['展开孔表：平坯左下为原点，X / Y / Φ'] + [f'{a[0]:.3f} / {a[1]:.3f} / {a[2]:g}' for a in P['U']['flat_circles']] if JOB.get('compact_panel_review') else []), title='U 说明（右栏）', fs=FS_BOX)
        if (JOB.get('battery_lid_edge_review') or JOB.get('battery_lid_region_review')) or JOB.get('dual_end_interfaces_review') or JOB.get('compact_wrap_review') or JOB.get('lid_pair_end_review') or JOB.get('lid_two_circle_review'):
            up=render_assy_iso_png(R/'PREVIEW'/f'{VER}_U_iso.png',['U'])
            ui=fig.add_axes([275/PW,45/PH,125/PW,110/PH]);ui.imshow(plt.imread(up));ui.axis('off');ui.set_title('U件实际成形轴测',fontsize=FS_TITLE,loc='left')
        save_page(pdf, fig)

        if STRUCTURE == 'u_l_t7u':
            fig=plt.figure(figsize=(PW/25.4,PH/25.4),dpi=120)
            ax=fig.add_axes([0,0,1,1]);header(ax,3);foot(ax)
            fx,fy=P['L']['flat_size'];BB=bidir(rep,'L')
            aa=vax(fig,18,40,(-40,fx+45),(-35,fy+40),min(230/(fx+85),195/(fy+75)),f'件2 L形底侧板：实际展开 {fx:.2f}×{fy:.2f}')
            flatdraw(aa,'L');bilateral_dims(aa,BB)
            for sg in BB['X_seg']:dimh(aa,sg[0],sg[1],fy+10,fy,fy,f'{sg[2]:.2f}')
            for sg in BB['Y_seg']:dimv(aa,sg[0],sg[1],-12,0,0,f'{sg[2]:.2f}')
            dimh(aa,0,fx,-24,0,0,f'{fx:.2f}');dimv(aa,0,fy,fx+20,fx,fx,f'{fy:.2f}')
            notes=[f'L盖U，拼缝0、退让0；实际厚度{t:g}。',f'成形外包{P["L"]["size"]}；一折，内R{ri:g}。']
            notes += [f'{row["id"]}：{row["axis"]}距A{row["a"]}/距B{row["b"]}；{row["seg_prev"]}；{row["seg_next"]}；90°' for row in table_rows(BB,'L')]
            box(ax,270,135,140,110,notes,title='L件工艺与定位')
            path=render_assy_iso_png(R/'PREVIEW'/f'{VER}_L_iso.png',['L'])
            ai=fig.add_axes([275/PW,38/PH,125/PW,85/PH]);ai.imshow(plt.imread(path));ai.axis('off');ai.set_title('L件实际成形轴测',fontsize=FS_TITLE,loc='left')
            save_page(pdf,fig)
        elif JOB.get('dual_end_interfaces_review'):
            draw_dual_end_parts(pdf)
        elif JOB.get('lid_pair_end_review'):
            draw_lid_pair_end_parts(pdf)
        else:
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
                ('本单两端板均无孔，零折' if (_TOP4 or _BATTERY_SIDE) else ('两端板把手居中；坐标及孔表见附页' if _PANEL_HANDLES else 'END_R：功能孔见左图；END_L：通常仅M4（以本单为准）')),
                ('连接孔在前后长侧壁，不在端板' if _BATTERY_SIDE else (('支承片Φ3.3攻M4；盖顶Φ4.5，见首页与第5页' if _TOP_SUPPORTS else '仅盖顶Φ4.5固定孔；螺钉承接结构未定') if _TOP4 else '仍开盖-体 M4（规则23）：端板短边 Y 上攻丝 Ø3.3')),
                '规则31：处理面朝外；DXF与PDF同手性',
                'NEST：端板可旋转90°塞进单张2440×1220；单件CUT未旋转',
            ], title='端板说明（右栏）', fs=FS_BOX)
            save_page(pdf, fig)

        # PAGE 4 — LID flat + roof holes + handles
        fig = plt.figure(figsize=(PW / 25.4, PH / 25.4), dpi=120)
        ax = fig.add_axes([0, 0, 1, 1]); header(ax, 4); foot(ax)
        lfx, lfy = P['LID']['flat_size']
        a = vax(fig, 15, 35, (-50, lfx + 40), (-40, lfy + 35), min(.48, 245/(lfx+90), 190/(lfy+75)), f'件{3 if STRUCTURE=="u_l_t7u" else 4} 上盖展开 {lfx:.2f}×{lfy:.2f}（外表面朝读者；双向尺寸）')
        flatdraw(a, 'LID')
        if (JOB.get('battery_lid_edge_review') or JOB.get('battery_lid_region_review')) or JOB.get('dual_end_interfaces_review') or JOB.get('handle_pair_review') or JOB.get('lid_pair_end_review') or JOB.get('lid_two_circle_review'):
            for i,(xx,yy,dd) in enumerate(sorted(P['LID']['flat_circles']),1):
                delta=(12 if xx<lfx/2 else -12)
                if (JOB.get('lid_two_circle_review') or JOB.get('dual_end_interfaces_review') or (JOB.get('battery_lid_edge_review') or JOB.get('battery_lid_region_review'))) and abs(dd-6.6)<1e-6:delta=-delta
                if _BATTERY_SIDE and abs(dd-4.5)<1e-6:
                    delta=8 if xx<lfx/2 else -8
                    a.annotate(f'F{i:02}',(xx,yy),(xx+delta/a.s,yy),fontsize=FS_NOTE,color=BLU,va='center',ha='left' if delta>0 else 'right',arrowprops=dict(arrowstyle='-',color=BLU,lw=.35))
                else:
                    a.annotate(f'F{i:02}',(xx,yy),(xx+delta/a.s,yy+(3 if yy<lfy/2 else -3)/a.s),fontsize=FS_NOTE,color=BLU,ha='left' if delta>0 else 'right',arrowprops=dict(arrowstyle='-',color=BLU,lw=.35))
        if (JOB.get('battery_lid_edge_review') or JOB.get('battery_lid_region_review')):
            for i,(x0,y0,x1,y1) in enumerate(sorted(P['LID'].get('flat_rectangles') or []),1):
                a.text((x0+x1)/2,(y0+y1)/2,f'R{i}',fontsize=FS_NOTE,color=BLU,ha='center',va='center')
        BL = bidir(rep, 'LID')
        for i, sg in enumerate(BL.get('X_seg', [])):
            dimh(a, sg[0], sg[1], lfy + 6 + (i % 2) * 5, lfy + 1, lfy + 1, f'{sg[2]:.2f}', fs=_fs(9.4))
        for i, sg in enumerate(BL.get('Y_seg', [])):
            dimv(a, sg[0], sg[1], -6 - (i % 2) * 7, -1, -1, f'{sg[2]:.2f}', fs=_fs(9.4))
        dimh(a, 0, lfx, -22, 0, 0, f'{lfx:.2f}'); dimv(a, 0, lfy, lfx + 12, lfx, lfx, f'{lfy:.2f}')
        bilateral_dims(a, BL)
        if (JOB.get('battery_lid_edge_review') or JOB.get('battery_lid_region_review')) or JOB.get('dual_end_interfaces_review') or JOB.get('compact_wrap_review') or JOB.get('lid_pair_end_review') or JOB.get('lid_two_circle_review'):
            lp=render_assy_iso_png(R/'PREVIEW'/f'{VER}_LID_iso.png',['LID'])
            li=fig.add_axes([20/PW,(216 if (JOB.get('lid_two_circle_review') or JOB.get('dual_end_interfaces_review') or (JOB.get('battery_lid_edge_review') or JOB.get('battery_lid_region_review'))) else 175)/PH,160/PW,(34 if (JOB.get('lid_two_circle_review') or JOB.get('dual_end_interfaces_review') or (JOB.get('battery_lid_edge_review') or JOB.get('battery_lid_region_review'))) else 75)/PH]);li.imshow(plt.imread(lp));li.axis('off');li.set_title('盖件实际成形轴测',fontsize=FS_TITLE,loc='left')
        # formed lid top sketch
        a2 = vax(fig, 280, 180, (-20, L + 20), (-20, W + 20), min(.25, 120/(L+40), 65/(W+40)), ('盖顶俯视（本单成形坐标）' if (_TOP4 or _BATTERY_SIDE) else '盖顶俯视（成形坐标，孔位待确认）'))
        a2.add_patch(Rectangle((-g, -g), L + 2 * g, W + 2 * g, fill=False, ec=GRN, lw=0.9))
        a2.add_patch(Rectangle((0, 0), L, W, fill=False, ec='0.5', lw=0.4, ls='--'))
        for cx in (HANDLE_CX if HANDLE_MOUNT not in ('END_L+END_R','END_R','END_L') else []):
            a2.add_patch(Rectangle((cx - HREF_BX / 2, HANDLE_CY - HREF_BY / 2), HREF_BX, HREF_BY, fill=False, ec='0.4', ls=':', lw=0.6))
            a2.plot(cx, HANDLE_CY, 'k+', ms=5)
            a2.text(cx, HANDLE_CY + 55, ('把手' if JOB.get('lid_rectangles') else (f'把手\n盖左下({cx+OH:g},{HANDLE_CY+OH:g})' if _TOP4 else f'把手\n({cx:g},{HANDLE_CY:g})')), fontsize=_fs(9.4), ha='center', color=BLU)
        for h in LID_HOLES:
            a2.add_patch(Circle((h['x'], h['y']), h['d'] / 2, fill=False, ec=REDC, lw=0.7))
        hole_labels(a2, [h for h in LID_HOLES if not (_TOP4 and h['id'].startswith('F'))])
        for rr in JOB.get('lid_rectangles') or []:
            xx,yy=rr['center'];ww,hh=rr['size'];a2.add_patch(Rectangle((xx-ww/2,yy-hh/2),ww,hh,fill=False,ec=REDC));a2.text(xx,yy,rr['id'],fontsize=FS_NOTE,color=REDC,ha='center')
        if (JOB.get('battery_lid_edge_review') or JOB.get('battery_lid_region_review')) or JOB.get('dual_end_interfaces_review') or JOB.get('handle_pair_review') or JOB.get('lid_pair_end_review') or JOB.get('lid_two_circle_review'):
            box(ax,280,25,125,145,[
                '展开孔心：平坯左/右、下/上；mm',
            ]+[f'F{i:02} Ø{dd:g} X{xx:.2f}/{lfx-xx:.2f} Y{yy:.2f}/{lfy-yy:.2f}' for i,(xx,yy,dd) in enumerate(sorted(P['LID']['flat_circles']),1)]+[
            ]+[f'R{i} {x1-x0:g}×{y1-y0:g} 心X{(x0+x1)/2:.2f}/{lfx-(x0+x1)/2:.2f} Y{(y0+y1)/2:.2f}/{lfy-(y0+y1)/2:.2f}' for i,(x0,y0,x1,y1) in enumerate(sorted(P['LID'].get('flat_rectangles') or []),1)]+[
                '各孔F号与本页展开对应；成形位置见首页。',
                f'功能圆孔{len(JOB.get("lid_ports") or [])}；方口{len(JOB.get("lid_rectangles") or [])}；把手孔{len(rep.get("handle_holes") or [])}；角部孔{len(_TOP4)}。',
                (f'{len(rep["holes"])}个Ø4.5位于盖裙侧面，非盖顶角孔。' if _BATTERY_SIDE else '盖顶螺钉承接结构未定HOLD。'),
                '外表面朝读者，展开未镜像。',
            ],title='实际CUT全部孔双向尺寸',fs=_fs(9.4),ec=REDC)
        else:
            box(ax, 280, 25, 125, 145, [
                '孔号 / 直径 / 成形X / 成形Y（mm）',
            ] + [f"{h['id']} / Ø{h['d']:g} / {h['x']:g} / {h['y']:g}" for h in LID_HOLES] + [f'{rect["id"]} {rect["size"][0]:g}×{rect["size"][1]:g}；X{rect["center"][0]:g}/Y{rect["center"][1]:g}' for rect in JOB.get('lid_rectangles') or []] + [
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
            (f'· 盖裙与体侧壁{len(rep["holes"])}处M4连接；顶面无额外角孔' if _BATTERY_SIDE else ((f'· 盖顶/支承片 M4孔{len(_TOP4)}对；同轴见实际STEP回读报告' if _TOP_SUPPORTS else '· 仅盖顶四角孔已建模；螺钉承接结构尚未设计') if _TOP4 else f'· M4孔盖↔箱体 {len(rep["holes"])}/{len(rep["holes"])} 同轴 {"通过" if coax else "见报告"}')),
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
        box(ax, 270, 40, 140, 220, [f'{i+1}. {p}' for i, p in enumerate(pending)] + ([('折弯定位与建议顺序（先长后短）', NAVY)] + [f'{part} {row["id"]}：90° Ri{ri:g}；线长{next(math.dist(*b["flat_line_mm"]) for b in P[part]["bend_records"] if b["id"]==row["id"]):g}；{row["axis"]}距A{row["a"]}/距B{row["b"]}；{row["seg_prev"]}；{row["seg_next"]}' for part in (('U','L','LID') if STRUCTURE=='u_l_t7u' else ('U','LID')) for row in sorted(table_rows(bidir(rep,part),part), key=lambda row: (-next(math.dist(*b['flat_line_mm']) for b in P[part]['bend_records'] if b['id']==row['id']),row['id']))] + ['折弯方向：展开外表面朝读者，翼边背向读者。顺序随模具和夹持空间首件确认。'] if _TOP4 else []), title='工艺 / 折弯定位', fs=_fs(9.4), ec=REDC)
        if _TOP_SUPPORTS:
            ta=vax(fig,18,42,(-10,125),(-12,65),1.1,'角部焊接支承片：25×25×0.8；4件；零折')
            for i,item in enumerate(_TOP4):
                name='TAB'+str(i+1);dx=i*30
                for wire in flats[name]['wires']:
                    ta.plot([q[0]+dx for q in wire],[q[1] for q in wire],color='k',lw=.7)
                circles=P[name]['flat_circles'];hx,hy,dd=circles[0]
                dimh(ta,dx,dx+25,-5,0,0,'25')
                dimh(ta,dx,dx+hx,35,25,hy,f'{hx:g}')
                dimv(ta,0,hy,dx-3,dx,dx,f'{hy:g}')
                if i==3: dimv(ta,0,25,dx+29,dx+25,dx+25,'25')
                ta.text(dx+12,48,name+' Ø3.3攻M4',fontsize=FS_NOTE,ha='center',color=BLU)
            ax.text(18,28,'支承片上表面贴盖内面，角部两邻边点焊至内壁；0.8薄板攻M4强度须首件核验。',fontsize=FS_NOTE,color=REDC)
        else:
            box(ax, 12, 40, 250, 100, [
                f'BA=π/2×(Ri+K·t)={BA:.4f}；OSSB={OSSB:.1f}；BD={BD:.4f}',
                (f'U实际展开{P["U"]["flat_size"][0]:.2f}×{P["U"]["flat_size"][1]:.2f}' if STRUCTURE=='u_l_t7u' else f'U展开宽={W:g}+2×{Hb:g}−2BD={W+2*Hb-2*BD:.2f}（CAD {P["U"]["flat_size"][1]:.2f}）'),
                (f'盖展开{P["LID"]["flat_size"][0]:.2f}×{P["LID"]["flat_size"][1]:.2f}；L展开{P["L"]["flat_size"][0]:.2f}×{P["L"]["flat_size"][1]:.2f}' if STRUCTURE=='u_l_t7u' else f'盖展开 CAD {P["LID"]["flat_size"][0]:.2f}×{P["LID"]["flat_size"][1]:.2f}；端板零折 {P["END_L"]["flat_size"][0]:.2f}×{P["END_L"]["flat_size"][1]:.2f}'),
                f'K={K:.4f} / Ri{ri:g}：候选，须试折；孔坐标：箱体外角 X0/Y0/Z0',
                f'把手：{_HDL_LINE}；{_END_SUMMARY}',
                f'订单{JOB.get("quantity", 1)}套；套料1盒；production_release={str(bool((JOB or {}).get("production_release", False))).lower()}；版本 {VER}',
            ] + [f'{part}/{row["id"]} {row["axis"]} 距A {row["a"]} / 距B {row["b"]} / '
                 f'段长 {row["seg_prev"]}；{row["seg_next"]} / {row["dir"]} {row["ang"]:g}°'
                 for part in (('U','L','LID') if STRUCTURE=='u_l_t7u' else ('U','LID')) for row in table_rows(bidir(rep, part), part)],
                title='K值 / 折弯扣除 / 折弯表（原生编号，非机台工序）', fs=_fs(9.4))
        save_page(pdf, fig)

        if _PANEL and not JOB.get('dual_end_interfaces_review') and not JOB.get('compact_panel_review') and not JOB.get('lid_pair_end_review'):
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

if JOB.get('ordinary_local_dimensions_review'):
    (W_/'local_dimension_coverage.json').write_text(json.dumps(_LD_RECORDS,ensure_ascii=False,indent=2))

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
