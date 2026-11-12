# v2.8.2 pipeline u_endplates - parameters from the brief JSON (env SM_JOB), single source of truth.
# Vendored from /workspace/orders/box-400x220x150/tools/cfg.py (S-201-1-20261021-001-v1, t46u 03 corners + outer end plates); only the source of values changed.
import json, math, os
from pathlib import Path
_J = json.load(open(os.environ['SM_JOB']))
STRUCTURE = _J['structure']
assert STRUCTURE in ('u_endplates', 'u_l_t7u')
VER = _J['release']                      # used exactly as given - never normalized
MATERIAL_CN = _J['material_cn']; DENSITY = _J.get('density_kg_mm3', 7.93e-6)
L, W, H = float(_J['L']), float(_J['W']), float(_J['H'])     # L,W = body external; H = total height incl. lid
OUTER_L, OUTER_W, OUTER_H = _J.get('finished_outer_mm', [L + 2*(_J['g']+_J['t']), W + 2*(_J['g']+_J['t']), H])
assert _J.get('dim_basis', 'body_outer') == 'body_outer' and _J.get('height_basis', 'total_incl_lid') == 'total_incl_lid'
t = float(_J['t']); ri = float(_J['Ri']); ro = ri + t; K = float(_J['K'])   # K/R: source in _J['kr_source'] (empirical unless measured)
KR_SOURCE = _J.get('kr_source', 'empirical')
g = float(_J['g'])
qmin = ri - math.sqrt(ri * ri - (ri - g) ** 2) if ri > g else 0.0
q = _J['q'] if _J.get('q') is not None else math.ceil((qmin + max(.05, t * .05)) * 10) / 10   # skill q rule
Hb = H - t - q
skirt = float(_J.get('skirt', 15.0))
assert 'end_flange' not in _J, 'v2.8.3: u_endplates end plates are flat zero-bend OUTER cover plates (no return flange); remove end_flange from the brief'
# v2.8.3 end plates = skill u_external_ends outer cover plates (user t16u: 端板盖U，不留缝隙，不退让)
SEAM = float(_J.get('seam_gap', 0.0)); END_INSET = float(_J.get('end_inset', 0.0)); END_TOP_FLUSH = bool(_J.get('end_top_flush', True))
# v2.8.3 lid corners = skill 03 scheme (references/lid-defaults03.md §03方案定义), default for lidded jobs; recomputed per job.
# corner_gap: user explicit value, else CANDIDATE 0.2 (labelled candidate, listed as pending). Never switch silently.
CORNER_SCHEME = _J.get('corner_scheme', '03'); assert CORNER_SCHEME == '03', 'u_endplates lid builds the 03 corner scheme only'
if _J.get('corner_gap') is not None: CORNER_GAP = float(_J['corner_gap']); CORNER_GAP_SOURCE = _J.get('corner_gap_source', 'user')
else: CORNER_GAP = 0.2; CORNER_GAP_SOURCE = 'candidate'
ZH = H - float(_J.get('hole_z_below_lid_top', skirt / 2))
D_BODY = float(_J.get('d_body', 3.3)); D_LID = float(_J.get('d_lid', 4.5))
LONG_X = [float(x) for x in _J['long_x']]; SHORT_Y = [float(y) for y in _J['short_y']]
BA = math.pi / 2 * (ri + K * t); OSSB = ri + t; BD = 2 * OSSB - BA
# handles: ONLY when the brief asks (never invented). Pattern from assets/profiles/<profile>.json
_HJ = _J.get('handles') or {}
if _HJ:
    _pf = json.load(open(Path(__file__).resolve().parents[2] / 'assets/profiles' / (_HJ['profile'] + '.json')))
    _pp = _pf.get('per_handle', _pf)
    D_HDL = _pf['laser_diameter_mm']; HDL_WIDE = _pp['wide_pitch_mm']; HDL_NARROW = _pp['narrow_pitch_mm']; HDL_ROWS = _pp['row_spacing_mm']
    HANDLE_CX = [float(x) for x in _HJ['cx']]; HANDLE_CY = W / 2 if _HJ.get('cy') is None else float(_HJ['cy'])
else:
    D_HDL = HDL_WIDE = HDL_NARROW = HDL_ROWS = 0.0; HANDLE_CX = []; HANDLE_CY = W / 2
HAS_HANDLES = bool(HANDLE_CX)
HANDLE_MOUNT = "NONE"
HANDLE_REF = bool(_HJ.get('reference_envelope', False))
def handle_holes():
    out = []
    for cx in HANDLE_CX:
        s = 1 if cx < L / 2 else -1          # wide row toward lid centre X (handles face each other)
        tag = 'L' if s > 0 else 'R'
        xw = cx + s * HDL_ROWS / 2; xn = cx - s * HDL_ROWS / 2
        out += [dict(id=f'H{tag}-W1', handle=tag, row='wide', x=xw, y=HANDLE_CY - HDL_WIDE / 2), dict(id=f'H{tag}-W2', handle=tag, row='wide', x=xw, y=HANDLE_CY + HDL_WIDE / 2),
                dict(id=f'H{tag}-N1', handle=tag, row='narrow', x=xn, y=HANDLE_CY - HDL_NARROW / 2), dict(id=f'H{tag}-N2', handle=tag, row='narrow', x=xn, y=HANDLE_CY + HDL_NARROW / 2)]
    return out
# reference handle body (envelope only, NOT supplier geometry)
_E = (_pf.get('reference_envelope_mm') if _HJ else None) or {'base': [50, 105, 3], 'posts': [10, 10, 35], 'bar': [10, 100, 8]}
HREF_BX, HREF_BY, HREF_BT = _E['base']; HREF_POST = _E['posts'][2]; HREF_BAR = _E['bar'][2]
NEST = _J.get('nest', {}); SHEET = tuple(NEST.get('sheet', (2440, 1220))); NEST_M = NEST.get('margin', 10); NEST_G = NEST.get('gap', 10)
NEST_ORDER = NEST.get('order', ['U', 'LID', 'L'] if STRUCTURE == 'u_l_t7u' else ['U', 'LID', 'END_L', 'END_R'])
# Anderson / side connector cutouts. Only the named end plate is cut, after the L/R mirror,
# so a right-side opening is not copied to the left. Coordinates are on the end plate:
# y from the Y=0 long wall, z from the bottom. This order only; absent means no cutout.
AND_CUTS = [dict(c) for c in (_J.get('end_cutouts') or [])]
# This order only. Lid-top Anderson ports are not the end-plate cutouts above.
LID_PORTS = [dict(c) for c in (_J.get('lid_ports') or [])]
PANEL_HOLES = _J.get('panel_holes') or []
RECT_CUTOUTS = _J.get('rect_cutouts') or []
# PDF engine reads LID_HOLES as id/d/x/y. This order only.
LID_HOLES = []
for i, c in enumerate(LID_PORTS, 1):
    LID_HOLES.append({"id": f"P{i}", "d": float(c["d"]), "x": float(c["x"]), "y": float(c["y"])})
    if c.get("d_bolt") and c.get("pitch"):
        for sx in (-1, 1):
            for sy in (-1, 1):
                LID_HOLES.append({"id": f"P{i}{sx:+d}{sy:+d}", "d": float(c["d_bolt"]), "x": float(c["x"]) + sx * float(c["pitch"]) / 2, "y": float(c["y"]) + sy * float(c["pitch"]) / 2})
LID_HOLES += [dict(h, d=D_HDL) for h in handle_holes()]
JOB = _J
# PDF/DOC page layout (pdf.py, docs.py narrative) is a hand-laid template validated ONLY for this geometry:
TEMPLATE_DIMS = dict(L=400.0, W=220.0, H=150.0, t=1.0, ri=0.8, g=0.5, skirt=15.0, handles=2)
TEMPLATE_OK = all(abs(globals()[k] - v) < 1e-9 for k, v in TEMPLATE_DIMS.items() if k != 'handles') and len(HANDLE_CX) == 2
