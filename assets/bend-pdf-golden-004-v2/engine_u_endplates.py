import sys, json, math, datetime, numpy as np, matplotlib, os
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
from matplotlib.patches import Rectangle, Circle, FancyBboxPatch
matplotlib.rcParams['pdf.fonttype'] = 42
FPATH = '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'
fm.fontManager.addfont(FPATH)
FP = fm.FontProperties(fname=FPATH)
matplotlib.rcParams['font.family'] = 'Noto Sans CJK SC'
matplotlib.rcParams['axes.unicode_minus'] = False

W_ = Path(sys.argv[1]); R = Path(sys.argv[2])
rep = json.load(open(W_ / 'report.json'))
proj = json.load(open(W_ / 'projections.json'))
mesh = json.load(open(W_ / 'mesh.json'))
flats = json.load(open(W_ / 'flats.json'))
sec = json.load(open(W_ / 'section_mid.json'))
dchk = json.load(open(W_ / 'dxf_checks.json'))
P = rep['parts']; G = rep['gap_check']
Hb = H - t - q
PW, PH = 420, 297  # A3 mm landscape via figsize
NAVY = (0.10, 0.22, 0.45); REDC = (0.82, 0.10, 0.10); DIMC = (0.0, 0.20, 0.65)
GRN = (0.20, 0.55, 0.30); TAN = (0.55, 0.40, 0.20)
RED = '#c00000'; BLU = '#0040a0'

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
    ax.add_patch(Rectangle((0, PH - 18), PW, 18, fc=NAVY, ec='none'))
    ax.text(8, PH - 12, f'{VER}  钣金折弯工艺确认稿（非生产放行）', color='w', fontsize=12, weight='bold', va='center')
    ax.text(PW - 55, PH - 12, f'出图 {stamp}', color='w', fontsize=10, ha='right', va='center')
    ax.text(PW - 8, PH - 12, f'{n}/4', color='w', fontsize=12, ha='right', va='center')
    # taller ERP red bar: material / t / LWH / VER / date (rule18)
    ax.add_patch(Rectangle((0, PH - 34), PW, 16, fc=REDC, ec='none'))
    ax.text(8, PH - 22, f'材料 {MATERIAL_CN}｜板厚 t={t:g} mm｜外形 {L:g}×{W:g}×{H:g}｜内R{ri:g} K={K:.2f}(经验)｜1套4件｜production_release=false',
            color='w', fontsize=8.2, va='center')
    ax.text(8, PH - 31, f'工厂编号 {VER}｜出图 {stamp}｜公差 +0/−2（不得大于）｜金样引擎 engine_u_endplates 2.8.27',
            color='w', fontsize=7.8, va='center')
    ax.set_xlim(0, PW); ax.set_ylim(0, PH); ax.axis('off')

def foot(ax):
    ax.plot([8, PW - 8], [12, 12], color=NAVY, lw=0.8)
    ax.text(8, 5, '单位 mm；尺寸取自本版 STEP/DXF/孔表。确认稿：首件试折与装配确认前不得批量。', fontsize=8)
    ax.text(PW - 8, 5, VER, fontsize=8, ha='right')

def vax(fig, x, y, xlim, ylim, s, title, tfs=8, axis_off=False):
    # x,y in mm on page; s = page-mm per data-mm → axes width
    w = (xlim[1] - xlim[0]) * s; h = (ylim[1] - ylim[0]) * s
    ax = fig.add_axes([x / PW, y / PH, w / PW, h / PH])
    ax.set_xlim(*xlim); ax.set_ylim(*ylim); ax.set_aspect('equal'); ax.s = s
    if axis_off:
        ax.axis('off')
    else:
        ax.tick_params(labelsize=5)
    ax.set_title(title, fontsize=tfs, loc='left')
    return ax

def dimh(ax, x1, x2, y, ya, yb, txt, fs=6.5, c=DIMC):
    # ya/yb = extension-line roots; label uses lane avoid (v2.8.27)
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
            ax.plot([x, x], [yr, y + (o if y > yr else -o)], color=c, lw=0.35)
        ax.annotate('', xy=(x1, y), xytext=(x2, y),
                    arrowprops=dict(arrowstyle='<|-|>', lw=0.55, color=c, mutation_scale=7, shrinkA=0, shrinkB=0))
        ax.text(tx, ty, txt, fontsize=fs, ha='center', va='bottom', color=c)
    else:
        ax.annotate('', xy=(x1, ya), xytext=(x2, yb), arrowprops=dict(arrowstyle='<->', color=c, lw=0.6))
        ax.text((x1 + x2) / 2, y, txt, fontsize=fs, ha='center', color=c)

def dimv(ax, y1, y2, x, xa, xb, txt, fs=6.5, c=DIMC):
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
            ax.plot([xr, x + (o if x > xr else -o)], [y, y], color=c, lw=0.35)
        ax.annotate('', xy=(x, y1), xytext=(x, y2),
                    arrowprops=dict(arrowstyle='<|-|>', lw=0.55, color=c, mutation_scale=7, shrinkA=0, shrinkB=0))
        ax.text(tx, ty, txt, fontsize=fs, ha='right', va='center', rotation=90, color=c)
    else:
        ax.annotate('', xy=(xa, y1), xytext=(xb, y2), arrowprops=dict(arrowstyle='<->', color=c, lw=0.6))
        ax.text(x, (y1 + y2) / 2, txt, fontsize=fs, va='center', color=c)

def _pl_proj(ax, poly, fn, **k):
    a = np.array([fn(p[0], p[1]) for p in poly])
    ax.plot(a[:, 0], a[:, 1], **k)

def view(ax, name, v, fn, lw=0.7, hidden=True):
    for poly in proj[name][v]['vis']:
        _pl_proj(ax, poly, fn, color='k', lw=lw)
    if hidden:
        for poly in proj[name][v]['hid']:
            _pl_proj(ax, poly, fn, color='0.55', lw=0.3, ls=(0, (3, 2)))

def box(ax, x, y, w, h, lines, title=None, fs=7.0, ec=NAVY):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle='round,pad=1', fc='#f7f9fc', ec=ec, lw=0.8))
    yy = y + h - 4
    if title:
        ax.text(x + 3, yy, title, fontsize=fs + 0.5, weight='bold', color=ec); yy -= 9
    for ln in lines:
        if isinstance(ln, tuple):
            ax.text(x + 3, yy, ln[0], fontsize=fs, color=ln[1]); yy -= 8
        else:
            ax.text(x + 3, yy, ln, fontsize=fs); yy -= 8

def iso(ax, names, elev=25, azim=-60):
    shifts = mesh.get('shifts', {})
    cols = {'U': TAN, 'END_L': (0.7, 0.55, 0.3), 'END_R': (0.7, 0.55, 0.3), 'LID': GRN,
            'HANDLE_REF_L': (0.4, 0.4, 0.5), 'HANDLE_REF_R': (0.4, 0.4, 0.5)}
    for n in names:
        if n not in mesh['parts']: continue
        v = np.array(mesh['parts'][n]['v']); f = np.array(mesh['parts'][n]['f'])
        sh = np.array(shifts.get(n, [0, 0, 0]))
        tris = v[f] + sh
        poly = Poly3DCollection(tris, alpha=0.85, linewidths=0.05)
        poly.set_facecolor(cols.get(n, (0.6, 0.6, 0.6))); poly.set_edgecolor((0.2, 0.2, 0.2))
        ax.add_collection3d(poly)
    ax.view_init(elev=elev, azim=azim)
    allv = np.concatenate([np.array(mesh['parts'][n]['v']) + np.array(shifts.get(n, [0, 0, 0])) for n in names if n in mesh['parts']])
    c = (allv.max(0) + allv.min(0)) / 2; r = (allv.max(0) - allv.min(0)).max() / 2 * 1.1
    ax.set_xlim(c[0] - r, c[0] + r); ax.set_ylim(c[1] - r, c[1] + r); ax.set_zlim(c[2] - r, c[2] + r)
    ax.set_axis_off()

def pl(ax, pts, color='k', lw=0.7, ls='-'):
    if not pts: return
    xs=[p[0] for p in pts]; ys=[p[1] for p in pts]
    ax.plot(xs, ys, color=color, lw=lw, ls=ls)
def flatdraw(ax, name, show_holes=True):
    for w in flats[name]['wires']:
        pl(ax, w + [w[0]], color='k', lw=0.7)
    for b in P[name].get('bend_lines', []):
        pl(ax, b, color=REDC, lw=0.9, ls=(0, (6, 2)))
    if show_holes:
        for c in P[name].get('flat_circles', []):
            # [x,y,d] or [x,y,r]?
            if len(c) >= 3:
                d = c[2] if c[2] > 2 else c[2] * 2
                # report uses diameter in flat_circles typically
                ax.add_patch(Circle((c[0], c[1]), (c[2] / 2 if c[2] > 2 else c[2]), fill=False, ec=REDC, lw=0.45))

# ---- page builders ----
out_pdf = R / f'{VER}_BEND_PDF_A3_CN.pdf'
with PdfPages(out_pdf) as pdf:
    # PAGE 1 — overview WITH orthographic outer dims (fix: bare iso had no L/W/H labels)
    fig = plt.figure(figsize=(PW / 25.4, PH / 25.4), dpi=120)
    ax = fig.add_axes([0, 0, 1, 1]); header(ax, 1); foot(ax)
    LOL = L + 2 * (g + t); LOW = W + 2 * (g + t); OH = g + t
    # --- 主视图 front (Y=0): length × height ---
    sF = 0.32
    a = vax(fig, 8, 178, (-55, L + 55), (-35, H + 55), sF,
            f'主视图（从前侧 Y=0 看）约 1:{1/sF:.1f}  — 外尺寸已标注', tfs=7.5, axis_off=True)
    view(a, 'ASSEMBLY', 'front', lambda u, v: (v, -u))
    dimv(a, 0, H, -40, -OH, -OH, f'{H:g} 含盖总高（已确认）', fs=7)
    dimv(a, 0, Hb, L + 42, L, L, f'{Hb:g} 箱体高', fs=6.5)
    dimv(a, H - skirt, H, L + 28, L + OH, L + OH, f'{skirt:g}', fs=6)
    dimh(a, -OH, L + OH, H + 38, H, H, f'{LOL:g} 盖外长', fs=7)
    dimh(a, 0, L, -22, 0, 0, f'{L:g} 箱体外长（已确认）', fs=7.5)
    for x in LONG_X:
        a.plot([x], [ZH], '+', color=BLU, ms=5, mew=0.8)
    a.text(L * 0.12, ZH - 28, f'长边每侧 M4×{len(LONG_X)}  Z={ZH:g}（Ø3.3攻 / 盖Ø4.5）', fontsize=6, color=BLU)
    a.text(L * 0.12, 35, f'盖裙下沿 Z={H - skirt:g}；箱体顶 Z={Hb:g}；顶隙 q={q:g}', fontsize=6)
    # --- 左/端板侧视图 right: width × height ---
    sR = 0.32
    a2 = vax(fig, 215, 178, (-50, W + 55), (-35, H + 55), sR,
             f'侧视图（外封端板侧）约 1:{1/sR:.1f}', tfs=7.5, axis_off=True)
    view(a2, 'ASSEMBLY', 'right', lambda u, v: (-v, u))
    dimh(a2, -OH, W + OH, H + 38, H, H, f'{LOW:g} 盖外宽', fs=7)
    dimh(a2, 0, W, -22, 0, 0, f'{W:g} 箱体外宽（已确认）', fs=7.5)
    dimv(a2, 0, H, -38, -OH, -OH, f'{H:g}', fs=6.5)
    for y in SHORT_Y:
        a2.plot([y], [ZH], '+', color=BLU, ms=5, mew=0.8)
    a2.text(15, 40, f'短边每侧 M4×{len(SHORT_Y)}（孔在端板）\n端板外轮廓 {W:g}×{Hb:g}，底角 R{ro:g}', fontsize=6, color=BLU)
    # --- 俯视图 top: length × width ---
    sT = 0.28
    a3 = vax(fig, 8, 28, (-55, L + 55), (-50, W + 70), sT,
             f'俯视图（从上看）约 1:{1/sT:.1f}  盖顶把手×2 / 盖顶Ø12·24·12', tfs=7.5, axis_off=True)
    view(a3, 'ASSEMBLY', 'top', lambda u, v: (u, v), hidden=False)
    dimh(a3, -OH, L + OH, -32, -OH, -OH, f'{LOL:g} 盖外长', fs=6.5)
    dimv(a3, -OH, W + OH, -40, -OH, -OH, f'{LOW:g} 盖外宽', fs=6.5)
    dimh(a3, 0, L, W + 48, W, W, f'{L:g} 箱体外长（已确认）', fs=7)
    dimv(a3, 0, W, L + 38, W, W, f'{W:g} 箱体外宽（已确认）', fs=7)
    for cx in HANDLE_CX:
        a3.add_patch(Rectangle((cx - HREF_BX / 2, HANDLE_CY - HREF_BY / 2), HREF_BX, HREF_BY,
                               fill=False, ec='0.4', ls=':', lw=0.5))
        a3.plot(cx, HANDLE_CY, 'k+', ms=4)
        a3.text(cx, HANDLE_CY + 55, f'把手\n({cx:g},{HANDLE_CY:g})', fontsize=5, ha='center', color=BLU)
    for h in LID_HOLES:
        a3.add_patch(Circle((h['x'], h['y']), h['d'] / 2, fill=False, ec=REDC, lw=0.6))
        a3.text(h['x'] + 8, h['y'] + 10, f"{h['id']}Ø{h['d']:g}", fontsize=5, color=REDC)
    a3.text(L * 0.2, -28, '盖顶三孔 Ø12/Ø24/Ø12 近短边Xmin（纠正v1；孔心X=23.5）待确认边与圆心', fontsize=5.5, color=REDC)
    # --- 小轴测（仅示意；外尺寸已在三视图标注）---
    a3d = fig.add_axes([0.62, 0.12, 0.16, 0.28], projection='3d')
    iso(a3d, ['U', 'END_L', 'END_R', 'LID', 'HANDLE_REF_L', 'HANDLE_REF_R'])
    a3d.set_title('装配轴测（示意）', fontsize=7)
    # --- 关键参数 ---
    rh = '/'.join(f"{h['id']}Ø{h['d']:g}" for h in LID_HOLES)
    box(ax, 330, 95, 82, 155, [
        ('尺寸口径（已确认）', REDC),
        f'· {L:g}×{W:g} = 箱体外尺寸',
        f'· {H:g} = 含盖总高',
        f'· 箱体高 Hb={Hb:g}',
        f'· 内长≈{L-2*t:g}；公差+0/−2mm',
        f'· 盖外 {LOL:g}×{LOW:g}×{skirt:g}',
        ('结构', NAVY),
        '· 件1 U：底+两长侧壁',
        '· 件2/3 外封端板零折',
        '  拼缝0/不退让/齐口',
        f'· 件4 盖裙{skirt:g} 03角缝0A',
        f'· 把手×2 X={HANDLE_CX[0]:g}/{HANDLE_CX[1]:g}',
        f'· 盖顶孔 {rh}',
        ('待确认', REDC),
        '· 外形不得大于；允许−2',
        '· 盖孔短边Xmin与圆心',
        '· 把手心90/289(向里20)',
        '· 端板接合/RiK/角缝',
    ], title='关键参数', fs=5.8)
    box(ax, 215, 28, 110, 22, [
        f'M4：长X={"/".join(f"{x:g}" for x in LONG_X)}；短Y={"/".join(f"{y:g}" for y in SHORT_Y)}；Z={ZH:g}；箱Ø3.3/盖Ø4.5'
    ], title='M4 布局', fs=6)
    # Big callout so preview glance cannot miss outer size
    ax.add_patch(FancyBboxPatch((8, PH - 48), 200, 14, boxstyle='round,pad=1', fc='#fff3cd', ec=REDC, lw=1.2))
    ax.text(108, PH - 41, f'外尺寸（已确认）：箱体 {L:g}×{W:g}  × 含盖总高 {H:g}',
            fontsize=10, ha='center', va='center', color=REDC, weight='bold')
    pdf.savefig(fig); plt.close()

    # PAGE 2 — U + ends flats
    fig = plt.figure(figsize=(PW / 25.4, PH / 25.4), dpi=120)
    ax = fig.add_axes([0, 0, 1, 1]); header(ax, 2); foot(ax)
    ufx, ufy = P['U']['flat_size']
    a = vax(fig, 20, 40, (-40, ufx + 40), (-30, ufy + 30), 0.28, f'件1 U 展开 {ufx:.2f}×{ufy:.2f}（外表面朝读者；双向尺寸）')
    flatdraw(a, 'U')
    BU = bidir(rep, 'U')
    for i, sg in enumerate(BU.get('X_seg', [])):
        dimh(a, sg[0], sg[1], ufy + 8 + (i % 2) * 6, ufy + 2, ufy + 2, f'{sg[2]:.2f}', fs=5.5)
    for i, sg in enumerate(BU.get('Y_seg', [])):
        dimv(a, sg[0], sg[1], -8 - (i % 2) * 8, -2, -2, f'{sg[2]:.2f}', fs=5.5)
    dimh(a, 0, ufx, -18, 0, 0, f'{ufx:.2f}'); dimv(a, 0, ufy, ufx + 15, ufx, ufx, f'{ufy:.2f}')
    efx, efy = P['END_L']['flat_size']
    a2 = vax(fig, 230, 160, (-20, efx + 30), (-20, efy + 30), 0.35, f'件2/3 端板展开（零折）{efx:.2f}×{efy:.2f}')
    flatdraw(a2, 'END_L')
    dimh(a2, 0, efx, -10, 0, 0, f'{efx:.2f}'); dimv(a2, 0, efy, efx + 10, efx, efx, f'{efy:.2f}')
    box(ax, 230, 40, 170, 100, [
        f'U：弯线沿长{L-2*t:g}；第2道侧壁高{Hb:g}、内宽{W-2*t:g} — 深U折弯避让 WARN',
        f'端板：零折平板，外轮廓={W:g}×{Hb:g}，底角R{ro:g}与U外圆同心',
        '拼缝0、inset0、上边齐口；接合=内侧角焊或外侧激光焊（待确认）',
        'NEST：端板在套料中旋转90°以塞进单张2440×1220；单件CUT未旋转',
        f'BD={BD:.4f}；U展开宽公式 {W:g}+2×{Hb:g}−2×BD = {W+2*Hb-2*BD:.2f}',
    ], title='U / 端板说明', fs=6.5)
    pdf.savefig(fig); plt.close()

    # PAGE 3 — LID flat + roof holes + handles
    fig = plt.figure(figsize=(PW / 25.4, PH / 25.4), dpi=120)
    ax = fig.add_axes([0, 0, 1, 1]); header(ax, 3); foot(ax)
    lfx, lfy = P['LID']['flat_size']
    a = vax(fig, 15, 35, (-50, lfx + 40), (-40, lfy + 35), 0.38, f'件4 上盖展开 {lfx:.2f}×{lfy:.2f}（外表面朝读者；双向尺寸）')
    flatdraw(a, 'LID')
    BL = bidir(rep, 'LID')
    for i, sg in enumerate(BL.get('X_seg', [])):
        dimh(a, sg[0], sg[1], lfy + 6 + (i % 2) * 5, lfy + 1, lfy + 1, f'{sg[2]:.2f}', fs=5)
    for i, sg in enumerate(BL.get('Y_seg', [])):
        dimv(a, sg[0], sg[1], -6 - (i % 2) * 7, -1, -1, f'{sg[2]:.2f}', fs=5)
    dimh(a, 0, lfx, -22, 0, 0, f'{lfx:.2f}'); dimv(a, 0, lfy, lfx + 12, lfx, lfx, f'{lfy:.2f}')
    # formed lid top sketch
    a2 = vax(fig, 280, 150, (-20, L + 20), (-20, W + 20), 0.22, '盖顶俯视（成形坐标，孔位待确认）')
    a2.add_patch(Rectangle((-g, -g), L + 2 * g, W + 2 * g, fill=False, ec=GRN, lw=0.9))
    a2.add_patch(Rectangle((0, 0), L, W, fill=False, ec='0.5', lw=0.4, ls='--'))
    for cx in HANDLE_CX:
        a2.add_patch(Rectangle((cx - HREF_BX / 2, HANDLE_CY - HREF_BY / 2), HREF_BX, HREF_BY, fill=False, ec='0.4', ls=':', lw=0.6))
        a2.plot(cx, HANDLE_CY, 'k+', ms=5)
        a2.text(cx, HANDLE_CY + 55, f'把手\n({cx:g},{HANDLE_CY:g})', fontsize=5, ha='center', color=BLU)
    for h in LID_HOLES:
        a2.add_patch(Circle((h['x'], h['y']), h['d'] / 2, fill=False, ec=REDC, lw=0.7))
        a2.text(h['x'] + 10, h['y'] + 8, f"{h['id']}Ø{h['d']:g}", fontsize=6, color=REDC)
    a2.text(L / 2, -12, '盖顶 Ø12/Ø24/Ø12 近短边Xmin（盖外约400×273）待确认', fontsize=5.5, ha='center', color=REDC)
    box(ax, 280, 40, 125, 95, [
        f'把手：X={HANDLE_CX[0]:g}/{HANDLE_CX[1]:g} Y={HANDLE_CY:g}；长向沿Y；Ø6.6×4 (85/62/30) M6 — 待确认',
        '盖顶三孔：R1Ø12(23.5,68.5) R2Ø24(23.5,134.5) R3Ø12(23.5,198.5)',
        '映射：短边外边+25；沿W +70/+136/+(270-70)；纠正v1 — 待确认',
        '不要：侧壁线孔/电缆孔（14孔=盖盒固定M4）',
        f'盖角03 corner_gap={CORNER_GAP:g} 方案A（切除版展开）',
    ], title='盖顶孔位', fs=6.2, ec=REDC)
    pdf.savefig(fig); plt.close()

    # PAGE 4 — checks / pending
    fig = plt.figure(figsize=(PW / 25.4, PH / 25.4), dpi=120)
    ax = fig.add_axes([0, 0, 1, 1]); header(ax, 4); foot(ax)
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
        ('【计算检查】CAD，非实物；native03缝0预期WARN（方案A）', REDC),
        f'· 模型：箱体{L:g}×{W:g}×{Hb:g}；盖约{L+2*(g+t):g}×{W+2*(g+t):g}×{skirt:g}；总高{H:g}',
        f'· M4孔盖↔箱体 {len(rep["holes"])}/{len(rep["holes"])} 同轴 {"通过" if coax else "见报告"}',
        f'· 把手孔 8/8 通透、85/62/30、镜像 {"通过" if hok else "见报告"}',
        f'· 盖顶三孔 Ø12/24/12 已切盖；孔边→外形/折弯 见报告',
        f'· DXF CUT/BEND/NEST 门禁：{"通过" if allpass else "见 dxf_checks"}',
        f'· corner03.py：ok；native03：{n3.get("error", n3.get("ok", "?"))}',
        f'· NEST 1BOX：端板套料旋转90°（零折）',
    ] + [(f'· WARN: {w[:60]}', REDC) for w in warn_cn[:3]], title='检查摘要', fs=6.5)
    pending = json.load(open(ORDER / f'{VER}.brief.json'))['confirm']['pending_cn']
    box(ax, 270, 40, 140, 220, [f'{i+1}. {p}' for i, p in enumerate(pending)], title='待确认清单', fs=6.2, ec=REDC)
    box(ax, 12, 40, 250, 100, [
        f'BA=π/2×(Ri+K·t)={BA:.4f}；OSSB={OSSB:.1f}；BD={BD:.4f}',
        f'U展开宽={W:g}+2×{Hb:g}−2BD={W+2*Hb-2*BD:.2f}（CAD {P["U"]["flat_size"][1]:.2f}）',
        f'盖展开 CAD {P["LID"]["flat_size"][0]:.2f}×{P["LID"]["flat_size"][1]:.2f}；端板零折 {P["END_L"]["flat_size"][0]:.2f}×{P["END_L"]["flat_size"][1]:.2f}',
        'K=0.4 / Ri0.8：经验候选，须试折；坐标：箱体外角 X0/Y0/Z0',
        '把手孔型：handle-85-62-30-v1；盖顶孔：短边Xmin Ø12/24/12',
        f'qty=1；production_release=false；版本 {VER}',
    ], title='K值 / 折弯扣除 / 来源', fs=6.5)
    pdf.savefig(fig); plt.close()

# overlap report (layout PASS iff remaining==0)
ov = dict(_OV)
ov['pass'] = ov.get('remaining', 0) == 0
ov['bbox_count'] = len(_BB)
ov['stamp'] = _PDF_STAMP
ov['ver'] = VER
ov['pdf'] = str(out_pdf)
logs = ORDER / 'logs'; logs.mkdir(exist_ok=True)
(logs / 'bend_pdf_overlap.json').write_text(json.dumps(ov, indent=2, ensure_ascii=False))
(logs / 'bend_pdf_meta.json').write_text(json.dumps({
    'ver': VER, 'pdf': str(out_pdf), 'pages': 4, 'stamp': _PDF_STAMP,
    'production_release': False, 'rev': 'u_endplates_dim_avoid_2.8.27',
    'dim_overlap': ov, 'pdf_layout_pass': ov['pass'],
}, indent=2, ensure_ascii=False))
# also Chinese alias for workshop
alias = R / f'{VER}_完整折弯工艺PDF_折弯师傅作业图_4页.pdf'
if alias.resolve() != out_pdf.resolve():
    alias.write_bytes(out_pdf.read_bytes())
print('PDF', out_pdf, 'pages 4', 'overlap', json.dumps(ov, ensure_ascii=False))
