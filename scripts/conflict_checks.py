#!/usr/bin/env python3
"""v2.8.2 automatic design-conflict checks (pure python, no CAD needed). Audit item #8.

Each check returns {'id','level':'ERROR'|'WARN'|'INFO','ok':bool,'msg_cn':..., 'data':{...}}.
ERROR = must be resolved (or explicitly accepted by the user) before a confirmation draft is shown;
WARN  = goes into the confirmation draft "冲突与风险" list; INFO = recorded only.
Checks:
  lid_root_vs_body_edge  lid inner bend radius vs body top outer edge (Ri > g needs a top gap q; skill q rule)
  m4_tap_thin_sheet      M4 tapped directly in sheet t<=1.2 -> WARN with the full thin-sheet warning (user t52u, 2026-10-26):
                         ~1 effective thread, low strength, strips easily, not for repeated removal; alternatives
                         press nut / blind rivet nut / weld nut are LISTED AS PENDING (待确认). M4 tapping stays the default
                         for lid<->body fixing (user t16u) - the alternatives are never silently applied. Every template that
                         prints M4 tapped holes in t<=1.2 must print m4_thin_sheet_warning_cn() (PDF + README + checklist).
  connector_screw_taps   cable-gland / 品字口 / panel connector screw holes must be tapped and say so (thread + tap drill) (user t16u)
  joint_flush            L盖U / 端板盖U: zero seam, zero setback unless the user explicitly gave a value for this job (user t16u)
  press_brake_deep_u     second bend of a deep U: formed wall height vs inner width / punch height (factory must confirm)
  hole_to_bend_tangent   hole edge to bend-zone tangent line in the FLAT (from report flat circles + bend lines)
  unrequested_features   handle/roof/cable holes present although the brief did not ask for them (never invent features)
  cable_hole_min_count   user t35u (2026-10-26, v2.8.5): an order with cable/wire holes (线孔) gets AT LEAST 2 per box. Only one
                         on the sketch/order -> add a 2nd of the same diameter, same height, same face, default 25 mm centre pitch
                         toward the face centre (suggest_second_cable_hole), clearance-checked, listed as a HOLD for position.
                         Opt-in: runs only when PARAMS has 'cable_holes' (backward compatible); <2 -> WARN, 0 -> INFO (not invented).
  hole_to_lid_skirt      user t99u / audit t98u (2026-10-31, v2.8.20, rule ~22): body-face cable/IEC/meter cutouts vs lid skirt
                         free bottom when lid closed. clearance = (H-skirt) - feature_top_Z. ERROR if <0 (msg MUST say 盖裙遮挡);
                         WARN if 0<=clearance<10 (rule16 靠盖裙10mm). Excludes body M4 rim fasteners and lid screw holes.
                         Params: H, skirt, end_features (dict circles/rects or list) and/or report['end_features']; optional
                         cable_holes with z; hold_skirt_clearance_waived demotes ERROR->WARN. Force lines via lid_skirt_force_lines_cn
                         into PDF p1 / CONFIRMATION / README.
CLI: conflict_checks.py PARAMS.json [REPORT.json] -> JSON list, exit 1 if any ERROR
PARAMS.json keys: t, Ri, K, g, q, (optional) punch_height_mm, hole_bend_min_mm, deep_u:[{part,wall_h,inner_w}],
                  requested:{handles:bool, roof_ports:bool}, features:{handles:int, roof_ports:int},
                  connectors:[{name, screw_holes:[{d, thread?, tap_drill?, process?}]}],
                  l_cover_setback_mm / end_inset / seam_gap / lid_long_skirt_setback_mm (+ setback_source_user:str),
                  (v2.8.5, optional) cable_holes:[{id, d, face?, u?, v?, added_by_rule?:bool}],
                  (v2.8.20) H, skirt, end_features, hold_skirt_clearance_waived?:bool
"""
import json, math, sys


def q_rule(ri, t, g):
    """skill rule (references/lid-root-fit): qmin = ri - sqrt(ri^2-(ri-g)^2) (0 if ri<=g); q = ceil((qmin+max(.05,.05t))*10)/10"""
    if ri <= g: return 0.0, 0.0
    qmin = ri - math.sqrt(ri * ri - (ri - g) ** 2)
    return qmin, math.ceil((qmin + max(.05, .05 * t)) * 10 - 1e-9) / 10


def lid_root(t, ri, g, q):
    qmin, qrec = q_rule(ri, t, g)
    if ri <= g:
        return {'id': 'lid_root_vs_body_edge', 'level': 'INFO', 'ok': True, 'msg_cn': f'盖内R{ri:g} ≤ 单边间隙g{g:g}，盖根圆角不碰箱体顶棱', 'data': {'q_min': 0}}
    d = math.hypot(ri - g, ri - q); clr = ri - d; clr0 = ri - math.hypot(ri - g, ri)
    ok = clr > 0
    return {'id': 'lid_root_vs_body_edge', 'level': 'WARN' if ok else 'ERROR', 'ok': ok,
            'msg_cn': (f'冲突：盖内R{ri:g} > g{g:g}，q=0时盖根圆角压箱体顶外棱{-clr0:.3f}；' +
                       (f'已用顶隙q={q:g}（箱体高=总高−t−q），最小间隙{clr:.3f}' if ok else f'当前q={q:g}仍干涉{-clr:.3f}，需q≥{qrec:g}或改Ri/g')),
            'data': {'Ri': ri, 'g': g, 'q': q, 'q_min': qmin, 'q_rule': qrec, 'clearance': clr, 'clearance_if_q0': clr0}}


M4_THIN_LIMIT_MM = 1.2   # user t52u: thin-sheet tapping warning for t<=1.2
M4_ALTERNATIVES_CN = ('压铆螺母', '拉铆螺母', '点焊螺母')


def m4_thin_sheet_warning_cn(t, material_cn='', tap_drill=3.3):
    """user t52u wording; must appear in PDF, README and checklist whenever M4 is tapped directly in t<=1.2."""
    mat = f' {material_cn}' if material_cn else ''
    return (f'{t:.1f} mm{mat} 板直接攻M4（底孔Ø{tap_drill:g}）仅约1扣有效螺纹，强度偏低、易滑牙，不建议反复拆装；'
            f'替代方案 {" / ".join(M4_ALTERNATIVES_CN)} 列为待确认')


def m4_tap(t, pitch=0.7, n=None, material_cn=''):
    threads = t / pitch
    if t > M4_THIN_LIMIT_MM + 1e-9:
        return {'id': 'm4_tap_thin_sheet', 'level': 'INFO', 'ok': True, 'msg_cn': f't{t:g} 直接攻M4约{threads:.1f}扣', 'data': {'threads': threads}}
    return {'id': 'm4_tap_thin_sheet', 'level': 'WARN', 'ok': False,
            'msg_cn': m4_thin_sheet_warning_cn(t, material_cn) + f'（理论{threads:.1f}扣；缺省仍按M4直接攻丝出图，首件试装确认）' + (f'，共{n}处' if n else ''),
            'data': {'t': t, 'pitch': pitch, 'threads': threads, 'limit_mm': M4_THIN_LIMIT_MM,
                     'pending_alternatives': list(M4_ALTERNATIVES_CN), 'default_kept': 'M4 tapped'}}


TAP_DRILL = {'M3': 2.5, 'M4': 3.3, 'M5': 4.2, 'M6': 5.0}
_CLEAR_TO_THREAD = [(3.2, 'M3'), (3.5, 'M3'), (4.3, 'M4'), (4.5, 'M4'), (5.3, 'M5'), (5.5, 'M5'), (6.4, 'M6'), (6.6, 'M6')]


def connector_screw_taps(connectors):
    """user t16u (2026-10-26): 线孔/品字口等接口的螺钉孔需要攻丝，并在PDF中说明. Every connector screw hole must carry
    process=tap, a thread (M3..M6) and the matching tap-drill diameter. A bare clearance hole -> ERROR with the suggested tap."""
    bad = []; n = 0
    for c in connectors or []:
        for h in c.get('screw_holes', []):
            n += 1; th = h.get('thread'); d = h.get('d', h.get('diameter_mm'))
            if h.get('process') != 'tap' or th not in TAP_DRILL or abs((h.get('tap_drill', d) or 0) - TAP_DRILL[th]) > 0.05:
                sug = th if th in TAP_DRILL else next((t_ for dd, t_ in _CLEAR_TO_THREAD if d is not None and abs(d - dd) < .05), None)
                bad.append({'connector': c.get('name'), 'd': d, 'thread': th, 'suggest': (f'攻{sug} / 底孔Φ{TAP_DRILL[sug]:g}' if sug else '定螺钉规格后攻丝')})
    return {'id': 'connector_screw_taps', 'level': 'ERROR' if bad else 'INFO', 'ok': not bad,
            'msg_cn': ('接口螺钉孔须攻丝并在PDF孔表写明（用户规则）：' + '；'.join(f"{b['connector']} Φ{b['d']}→{b['suggest']}" for b in bad)) if bad else (f'接口螺钉孔{n}个均为攻丝并写明规格' if n else '无接口螺钉孔'),
            'data': {'violations': bad, 'holes_checked': n, 'tap_drill_table': TAP_DRILL}}


def joint_flush(p):
    """user t16u (2026-10-26): U+L -> L盖U; U+两端板 -> 端板盖U; 不留缝隙，不退让0.2mm. Non-zero values need setback_source_user."""
    keys = ('l_cover_setback_mm', 'end_inset', 'seam_gap', 'lid_long_skirt_setback_mm')
    nz = {k: p[k] for k in keys if p.get(k) not in (None, 0, 0.0)}
    src = p.get('setback_source_user')
    lvl = 'INFO' if not nz else ('WARN' if src else 'ERROR')
    return {'id': 'joint_flush', 'level': lvl, 'ok': not nz or bool(src),
            'msg_cn': ('L盖U/端板盖U：0缝、不退让（用户默认）' if not nz else
                       (f'非0退让/缝 {nz}，来源：{src}' if src else f'非0退让/缝 {nz} 无用户来源：用户规则为不留缝隙、不退让0.2mm，改为0或写明用户本单要求')),
            'data': {'nonzero': nz, 'source': src}}


def press_brake(part, wall_h, inner_w, punch_height=None):
    """second bend of a U: the already formed wall (height wall_h) swings toward the ram. Without factory tooling data we can
    only flag; we never claim it is formable."""
    lvl = 'INFO'; why = []
    if punch_height is not None and wall_h + 5 > punch_height: lvl = 'ERROR'; why.append(f'已成形侧壁{wall_h:g} > 上模可用高度{punch_height:g}−5')
    elif wall_h >= 100 or wall_h >= 0.5 * inner_w: lvl = 'WARN'; why.append(f'侧壁高{wall_h:g}、内宽{inner_w:g}')
    return {'id': 'press_brake_deep_u', 'level': lvl, 'ok': lvl == 'INFO',
            'msg_cn': (f'{part} 深U第2道折弯：' + '，'.join(why) + '，须确认上模高度/鹅颈刀/滑块避让，必要时改U+L或加高刀') if why else f'{part} U形侧壁{wall_h:g}/内宽{inner_w:g}，常规刀具可折（仍按首件确认）',
            'data': {'part': part, 'wall_h': wall_h, 'inner_w': inner_w, 'punch_height_mm': punch_height}}


def _seg_dist(p, a, b):
    ax, ay = a; bx, by = b; px, py = p; ux, uy = bx - ax, by - ay; L2 = ux * ux + uy * uy
    s = max(0.0, min(1.0, ((px - ax) * ux + (py - ay) * uy) / L2)) if L2 else 0.0
    return math.hypot(px - ax - s * ux, py - ay - s * uy), s


def hole_to_bend(report, t, ri, K, min_mm=None):
    """flat circles [[x,y,d]] vs bend centre lines; bend zone = centre line +- BA/2. Edge distance = dist - BA/2 - r."""
    BA = math.pi / 2 * (ri + K * t); lim = min_mm if min_mm is not None else max(3.0, 2 * t + ri)
    worst = []; out = []
    for n, P in report['parts'].items():
        if P.get('reference_only') or 'flat_circles' not in P: continue
        for x, y, d in P['flat_circles']:
            best = None
            for bl in P.get('bend_lines', []):
                dist, s = _seg_dist((x, y), tuple(bl[0]), tuple(bl[-1]))
                if 0 < s < 1 or dist < d:  # only bends whose extent faces the hole
                    e = dist - BA / 2 - d / 2; best = e if best is None else min(best, e)
            if best is not None: out.append({'part': n, 'x': x, 'y': y, 'd': d, 'edge_to_tangent': round(best, 3)})
    bad = [o for o in out if o['edge_to_tangent'] < lim - 1e-9]
    mn = min((o['edge_to_tangent'] for o in out), default=None)
    return {'id': 'hole_to_bend_tangent', 'level': 'WARN' if bad else 'INFO', 'ok': not bad,
            'msg_cn': (f'{len(bad)}个孔边距折弯切线<{lim:g}（最小{mn:.2f}），折弯会拉椭圆，需移孔或折后加工' if bad else f'全部孔边→折弯切线≥{lim:g}（最小{mn:.2f}）' if mn is not None else '无孔/无折弯'),
            'data': {'limit_mm': lim, 'BA': BA, 'min': mn, 'violations': bad, 'holes_checked': len(out)}}


def hole_to_outline(report, min_mm=4.0):
    """v2.8.2: hole edge -> flat outline >= 4 mm (lessons L5.4). Uses the flat bbox [0,fw]x[0,fh] (flat_circles share that
    origin); corner notches are not modelled, so this is a lower-bound screen, the DXF review stays authoritative."""
    out = []
    for n, P in report['parts'].items():
        if P.get('reference_only') or 'flat_circles' not in P or 'flat_size' not in P: continue
        fw, fh = P['flat_size']
        for x, y, d in P['flat_circles']:
            out.append({'part': n, 'x': x, 'y': y, 'd': d, 'edge_to_outline': round(min(x, y, fw - x, fh - y) - d / 2, 3)})
    bad = [o for o in out if o['edge_to_outline'] < min_mm - 1e-9]
    mn = min((o['edge_to_outline'] for o in out), default=None)
    return {'id': 'hole_to_outline', 'level': 'WARN' if bad else 'INFO', 'ok': not bad,
            'msg_cn': (f'{len(bad)}个孔边距展开外形<{min_mm:g}（最小{mn:.2f}），激光易烧穿/变形，需移孔' if bad else f'全部孔边→展开外形≥{min_mm:g}（最小{mn:.2f}，按外包框）' if mn is not None else '无孔'),
            'data': {'limit_mm': min_mm, 'min': mn, 'violations': bad, 'holes_checked': len(out)}}


def unrequested(requested, features):
    bad = [k for k, v in features.items() if v and not requested.get(k, False)]
    return {'id': 'unrequested_features', 'level': 'ERROR' if bad else 'INFO', 'ok': not bad,
            'msg_cn': ('未经要求生成了：' + '、'.join(f'{k}×{features[k]}' for k in bad) + '——不得自行添加把手孔/线孔/顶孔，删除或先问用户') if bad else '无未要求的开孔/特征',
            'data': {'requested': requested, 'features': features}}


CABLE_HOLE_MIN = 2            # user t35u 2026-10-26: "线孔至少两个"
CABLE_HOLE_PITCH_MM = 25.0     # default centre pitch for the added hole (user's order 008 pitch)


def suggest_second_cable_hole(u, v, d, face_u_min, face_u_max, pitch=CABLE_HOLE_PITCH_MM):
    """Second cable hole for an order that shows only one (user t35u): same diameter d, same height v, same face,
    centre `pitch` along the face toward the face centre. Returns {'u','v','d','pitch','web'} - web = pitch - d (metal between holes).
    Caller must still check clearance to edges/bends/skirt/fixing holes (hole_to_outline / hole_to_bend / its own 3D check)
    and must list the new position as a HOLD for user confirmation."""
    c = (face_u_min + face_u_max) / 2.0
    s = 1.0 if c >= u else -1.0
    u2 = u + s * pitch
    if not (face_u_min + d / 2 <= u2 <= face_u_max - d / 2):
        u2 = u - s * pitch
    return {'u': round(u2, 3), 'v': v, 'd': d, 'pitch': pitch, 'web': round(pitch - d, 3), 'toward_centre': (u2 - u) * (c - u) >= 0}


def cable_hole_count(cable_holes, min_count=CABLE_HOLE_MIN):
    """user t35u: if an order has cable holes there must be >= 2 per box. <2 -> WARN (add the 2nd per suggest_second_cable_hole,
    list it as HOLD); 0 -> INFO only (never invent cable holes for an order that has none - unrequested rule)."""
    n = len(cable_holes or []); added = [h.get('id', '?') for h in (cable_holes or []) if h.get('added_by_rule')]
    if n == 0:
        return {'id': 'cable_hole_min_count', 'level': 'INFO', 'ok': True, 'msg_cn': '本单无线孔（未要求不添加；如有线孔则至少2个）', 'data': {'count': 0, 'min': min_count}}
    if n < min_count:
        return {'id': 'cable_hole_min_count', 'level': 'WARN', 'ok': False,
                'msg_cn': f'线孔仅{n}个 < {min_count}（用户规则t35u：线孔至少2个）——按同径、同高、同面、孔距{CABLE_HOLE_PITCH_MM:g}向面中心补第2个，核间距后列HOLD待确认位置',
                'data': {'count': n, 'min': min_count}}
    msg = f'线孔{n}个 ≥ {min_count}' + (f'（其中按规则t35u补加：{"、".join(added)}，位置待确认HOLD）' if added else '')
    return {'id': 'cable_hole_min_count', 'level': 'INFO', 'ok': True, 'msg_cn': msg, 'data': {'count': n, 'min': min_count, 'added_by_rule': added}}


LID_SKIRT_CLEAR_MM = 10.0   # user rule16 靠盖裙10mm; hole_to_lid_skirt WARN band (v2.8.20 / t99u)
_LID_SKIRT_EXCLUDE_TOKENS = (
    'm4_body', 'm4_lid', 'body_m4', 'lid_m4', 'lid_screw', 'body_fixing', 'skirt_screw', 'fixing_m4',
    '盖裙螺钉', '裙边螺钉', '箱体固定', '盖-体固定', '盖体固定', ' rim m4', 'fixing hole',
)


def skirt_free_edge_z(H, skirt):
    """Lid closed: free bottom edge of skirt in world Z (pipelines zb=H-skirt)."""
    return float(H) - float(skirt)


def _lid_skirt_feature_excluded(f):
    """Exclude body M4 rim fasteners and lid screw/skirt fixing holes (t98u m4_note)."""
    if f.get('exclude_from_lid_skirt') or f.get('fixing') or f.get('is_m4_fixing') or f.get('is_lid_screw'):
        return True
    role = ' '.join(str(f.get(k) or '') for k in ('role', 'kind', 'use', 'note', 'id')).lower()
    if any(tok.lower() in role for tok in _LID_SKIRT_EXCLUDE_TOKENS):
        return True
    # bare M4 body tap Ø3.3 / lid clearance Ø4.5 when explicitly tagged as fixing or ZH rim
    d = f.get('d', f.get('diameter_mm'))
    if f.get('role') in ('m4', 'fixing') or f.get('kind') in ('m4', 'fixing'):
        return True
    if d is not None and abs(float(d) - 3.3) < 0.05 and ('m4' in role or '攻' in role or '固定' in role):
        return True
    if d is not None and abs(float(d) - 4.5) < 0.05 and ('盖裙' in role or 'lid' in role or '过孔' in role or '固定' in role):
        return True
    return False


def _norm_lid_skirt_feature(f):
    """Normalize circle/rect/cable feature to {id,part,kind,feature_top_Z,...} or None if incomplete/excluded."""
    if not f or _lid_skirt_feature_excluded(f):
        return None
    fid = f.get('id', '?')
    part = f.get('part') or f.get('face') or ''
    use = f.get('use') or f.get('note') or ''
    # circle: z + d/2; rect: cz + h/2; accept feature_top_Z if precomputed
    if f.get('feature_top_Z') is not None:
        top = float(f['feature_top_Z'])
        kind = f.get('kind') or ('rect' if f.get('w') or f.get('h') else 'circle')
        return {'id': fid, 'part': part, 'kind': kind, 'feature_top_Z': top, 'use': use,
                'd': f.get('d'), 'w': f.get('w'), 'h': f.get('h'), 'z': f.get('z', f.get('cz'))}
    if f.get('w') is not None or f.get('h') is not None or f.get('kind') == 'rect':
        cz = f.get('cz', f.get('z', f.get('v')))
        h = f.get('h', f.get('height_mm'))
        if cz is None or h is None:
            return None
        return {'id': fid, 'part': part, 'kind': 'rect', 'feature_top_Z': float(cz) + float(h) / 2.0,
                'use': use, 'd': None, 'w': f.get('w'), 'h': float(h), 'z': float(cz)}
    d = f.get('d', f.get('diameter_mm'))
    z = f.get('z', f.get('cz', f.get('v')))
    if d is None or z is None:
        return None
    return {'id': fid, 'part': part, 'kind': 'circle', 'feature_top_Z': float(z) + float(d) / 2.0,
            'use': use, 'd': float(d), 'w': None, 'h': None, 'z': float(z)}


def collect_lid_skirt_features(params, report=None):
    """Gather body-face cutouts from params end_features / end_holes / end_rects / cable_holes and report."""
    out, seen = [], set()

    def add(f):
        n = _norm_lid_skirt_feature(f)
        if not n:
            return
        key = (n['part'], n['id'], round(n['feature_top_Z'], 3), n.get('d'), n.get('w'), n.get('h'))
        if key in seen:
            return
        seen.add(key); out.append(n)

    sources = []
    ef = params.get('end_features')
    if ef is None and report is not None:
        ef = report.get('end_features')
    if isinstance(ef, dict):
        for c in ef.get('circles') or []: sources.append(c)
        for r in ef.get('rects') or []: sources.append(r)
        for f in ef.get('features') or []: sources.append(f)
    elif isinstance(ef, list):
        sources.extend(ef)
    for key in ('end_holes', 'end_rects', 'face_features'):
        for f in params.get(key) or []: sources.append(f)
        if report is not None:
            for f in report.get(key) or []: sources.append(f)
    for h in params.get('cable_holes') or []:
        sources.append(h)
    for f in sources:
        add(f)
    return out


def hole_to_lid_skirt(params, report=None, clear_mm=None):
    """v2.8.20 / t99u: feature top edge vs lid skirt free bottom (lid closed).
    clearance = skirt_free_edge_Z - feature_top_Z. ERROR if <0 (盖裙遮挡); WARN if 0<=clr<clear_mm (default 10).
    Opt-in when H+skirt present and at least one body-face feature is available; otherwise INFO skip.
    hold_skirt_clearance_waived / skirt_occlusion_accepted: ERROR demoted to WARN (must still say 盖裙遮挡)."""
    H, skirt = params.get('H'), params.get('skirt', params.get('skirt_height'))
    lim = float(clear_mm if clear_mm is not None else params.get('lid_skirt_clear_mm', LID_SKIRT_CLEAR_MM))
    feats = collect_lid_skirt_features(params, report)
    if H is None or skirt is None:
        return {'id': 'hole_to_lid_skirt', 'level': 'INFO', 'ok': True,
                'msg_cn': '未提供 H/skirt，跳过盖裙遮挡检查（有盖且有线孔/品字/电表口时须提供）',
                'data': {'skipped': 'missing_H_or_skirt', 'features_seen': len(feats)}}
    if not feats:
        # only run as INFO when no features — not an invent-features case
        return {'id': 'hole_to_lid_skirt', 'level': 'INFO', 'ok': True,
                'msg_cn': f'无箱体面线孔/品字/电表等切口需核盖裙遮挡（裙下沿 Z={skirt_free_edge_z(H, skirt):.3f}）',
                'data': {'H': H, 'skirt': skirt, 'skirt_free_edge_Z': skirt_free_edge_z(H, skirt),
                         'limit_mm': lim, 'features_checked': 0}}
    zb = skirt_free_edge_z(H, skirt)
    rows = []
    for n in feats:
        clr = zb - n['feature_top_Z']
        rows.append({**n, 'skirt_free_edge_Z': zb,
                     'clearance_featureTop_to_skirtFreeEdge_mm': round(clr, 3),
                     'overlap_under_skirt_mm': round(max(0.0, -clr), 3),
                     'under_or_collides_skirt': clr < -1e-9,
                     'rule16_10mm_ok': clr >= lim - 1e-9})
    overlaps = [r for r in rows if r['under_or_collides_skirt']]
    near = [r for r in rows if (not r['under_or_collides_skirt']) and r['clearance_featureTop_to_skirtFreeEdge_mm'] < lim - 1e-9]
    waived = bool(params.get('hold_skirt_clearance_waived') or params.get('skirt_occlusion_accepted'))
    if overlaps:
        level = 'WARN' if waived else 'ERROR'
        bits = []
        for r in overlaps:
            size = (f"Ø{r['d']:g}" if r.get('d') else (f"{r['w']:g}×{r['h']:g}" if r.get('w') is not None else r['kind']))
            bits.append(f"{r['part'] or '?'} {r['id']} {size} 孔顶/口顶Z={r['feature_top_Z']:g} 高于盖裙下沿Z={zb:g}（侵入{r['overlap_under_skirt_mm']:g}mm）")
        msg = ('盖裙遮挡：' + '；'.join(bits) +
               f'；孔顶→裙下沿净空最小{min(r["clearance_featureTop_to_skirtFreeEdge_mm"] for r in overlaps):g} mm'
               f'（规则16默认≥{lim:g}）。确认稿/PDF第1页/README必须反馈，不得静默通过'
               + ('（用户已书面接受遮挡/开裙缺口：hold_skirt_clearance_waived）' if waived else ''))
        return {'id': 'hole_to_lid_skirt', 'level': level, 'ok': False, 'msg_cn': msg,
                'data': {'H': H, 'skirt': skirt, 'skirt_free_edge_Z': zb, 'limit_mm': lim,
                         'waived': waived, 'violations': overlaps, 'near_misses': near,
                         'features_checked': len(rows), 'min_clearance': min(r['clearance_featureTop_to_skirtFreeEdge_mm'] for r in rows)}}
    if near:
        bits = []
        for r in near:
            size = (f"Ø{r['d']:g}" if r.get('d') else (f"{r['w']:g}×{r['h']:g}" if r.get('w') is not None else r['kind']))
            bits.append(f"{r['part'] or '?'} {r['id']} {size} 净空{r['clearance_featureTop_to_skirtFreeEdge_mm']:g}")
        msg = (f'靠盖裙不足{lim:g}mm（规则16）：' + '；'.join(bits) +
               f'（裙下沿Z={zb:g}）。建议下移孔组使孔顶≤裙下沿−{lim:g}；确认稿须列出')
        return {'id': 'hole_to_lid_skirt', 'level': 'WARN', 'ok': False, 'msg_cn': msg,
                'data': {'H': H, 'skirt': skirt, 'skirt_free_edge_Z': zb, 'limit_mm': lim,
                         'violations': near, 'features_checked': len(rows),
                         'min_clearance': min(r['clearance_featureTop_to_skirtFreeEdge_mm'] for r in rows)}}
    mn = min(r['clearance_featureTop_to_skirtFreeEdge_mm'] for r in rows)
    return {'id': 'hole_to_lid_skirt', 'level': 'INFO', 'ok': True,
            'msg_cn': f'箱体面切口孔顶→盖裙下沿均≥{lim:g}（最小{mn:.2f}，裙下沿Z={zb:g}）',
            'data': {'H': H, 'skirt': skirt, 'skirt_free_edge_Z': zb, 'limit_mm': lim,
                     'features_checked': len(rows), 'min_clearance': mn, 'rows': rows}}


def lid_skirt_force_lines_cn(conflicts):
    """Force-findings lines for PDF p1 / CONFIRMATION_DRAFT / README when hole_to_lid_skirt WARN/ERROR present.
    Callers MUST print every returned line (red/pending); do not drop 盖裙遮挡 wording."""
    lines = []
    for x in conflicts or []:
        if x.get('id') != 'hole_to_lid_skirt' or x.get('level') not in ('WARN', 'ERROR'):
            continue
        msg = x.get('msg_cn') or ''
        if msg:
            lines.append(f"[{x['level']}] {msg}")
        # ensure 盖裙遮挡 appears on ERROR even if a caller rewrote msg
        if x['level'] == 'ERROR' and '盖裙遮挡' not in msg:
            lines.append('[ERROR] 盖裙遮挡：箱体面切口侵入盖裙下沿，见 conflict_checks.hole_to_lid_skirt')
    return lines



def run(params, report=None):
    p = params; res = [lid_root(p['t'], p['Ri'], p['g'], p['q'])] if p.get('g') is not None else []
    res.append(m4_tap(p['t'], n=p.get('m4_count'), material_cn=p.get('material_cn', '')))
    for u in p.get('deep_u', []): res.append(press_brake(u['part'], u['wall_h'], u['inner_w'], p.get('punch_height_mm')))
    if report:
        res.append(hole_to_bend(report, p['t'], p['Ri'], p['K'], p.get('hole_bend_min_mm')))
        res.append(hole_to_outline(report, p.get('hole_outline_min_mm', 4.0)))  # v2.8.2
    if 'requested' in p: res.append(unrequested(p['requested'], p.get('features', {})))
    if p.get('connectors'): res.append(connector_screw_taps(p['connectors']))   # user t16u
    res.append(joint_flush(p))   # user t16u
    if 'cable_holes' in p: res.append(cable_hole_count(p['cable_holes']))   # user t35u (v2.8.5), opt-in
    # v2.8.20 / t99u: lid-skirt occlusion for body-face cutouts (params H+skirt+end_features and/or report)
    if p.get('H') is not None and (p.get('skirt') is not None or p.get('skirt_height') is not None):
        res.append(hole_to_lid_skirt(p, report))
    elif p.get('end_features') is not None or (report and report.get('end_features')):
        res.append(hole_to_lid_skirt(p, report))  # still emit INFO skip if H/skirt missing
    return res


if __name__ == '__main__':
    params = json.load(open(sys.argv[1])); rep = json.load(open(sys.argv[2])) if len(sys.argv) > 2 else None
    r = run(params, rep); print(json.dumps(r, indent=1, ensure_ascii=False)); sys.exit(1 if any(x['level'] == 'ERROR' for x in r) else 0)
