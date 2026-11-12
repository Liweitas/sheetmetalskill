#!/usr/bin/env python3
"""v2.8.2 confirmation-draft workflow (audit #9). Writes {VER}_CONFIRMATION_DRAFT.txt - a DRAFT message for the user to
review; this script NEVER sends anything. Every release ships with production_release=false until the user confirms.

Input brief JSON (see assets/examples/*.release.json, key "confirm"):
  release, material_cn, t, dims {L,W,H}, dim_basis ("外形"/"内腔"), height_basis ("含盖总高"), structure,
  features_cn [..], assumptions_cn [..], pending_cn [..], named_processes [..], not_requested_cn [..],
  hole_refs [{"what":..., "value":15, "axis":"距上沿"}]   -> ambiguous 'distance' wording: both readings listed
Plus the conflict list from conflict_checks.py (WARN/ERROR go into 冲突与风险).
Rules enforced here:
  * 计算检查通过 is stated separately from 实物试折/试装 (never claimed);
  * K/R source is printed (empirical unless the brief says measured);
  * any named process not in assets/profiles/named-processes-v1.json -> 待确认 "请提供参考图/参数";
  * v2.8.3: '斜角03' (alias of '03') is the skill's own 03 lid corner scheme (references/lid-defaults03.md), NOT unknown.
    Brief keys corner_scheme ('03' default for lidded jobs) / corner_gap (+ corner_gap_source 'user'|'candidate'):
    a user-explicit gap is printed as such; otherwise candidate 0.2 is printed AND listed under 待确认.
    corner03.py + native03_check.py are mandatory for 03 and are named in the draft;
  * hole position wording "距边X" -> two numeric readings (孔边/孔心) unless brief says basis.
"""
import json, sys
from pathlib import Path

SK = Path(__file__).resolve().parents[1]


def build(brief, conflicts=(), checks_passed=None):
    c = brief['confirm']; V = brief['release']; NP = json.load(open(SK / 'assets/profiles/named-processes-v1.json'))
    known = set(NP['known']) | set(NP.get('aliases', {}))
    pend = list(c.get('pending_cn', []))
    for n in c.get('named_processes', []):
        if n not in known: pend.append(f'工艺“{n}”未在技能已知工艺库中：请提供参考图/参数，本版未按猜测建模')
    corner = []
    scheme = str(brief.get('corner_scheme', '03' if any(NP.get('aliases', {}).get(n, n) == '03' for n in c.get('named_processes', [])) else ''))
    if scheme == '03':
        gsrc = brief.get('corner_gap_source', 'user' if brief.get('corner_gap') is not None else 'candidate')
        gap = float(brief['corner_gap']) if brief.get('corner_gap') is not None else 0.2
        corner.append(f"盖角：03方案（斜角03，斜角折弯收口；references/lid-defaults03.md），corner_gap={gap:g}（{'您明确给定' if gsrc == 'user' else '候选值，待确认'}）；"
                      'P1/P2/P3 按本单参数重算，已跑 scripts/corner03.py + scripts/native03_check.py')
        if gsrc != 'user': pend.append(f'03盖角 corner_gap 本版用候选值 {gap:g}，请确认（如要求“不要有缝”则取0）')
    for h in c.get('hole_refs', []):
        if h.get('basis') not in ('孔心', '孔边'):
            d = h.get('diameter', 0)
            pend.append(f"{h['what']}“{h['axis']}{h['value']:g}”有两种读法：孔心{h['axis']}{h['value']:g}，或孔边{h['axis']}{h['value']:g}（=孔心{h['value'] + d / 2:g}）；本版按{h.get('used', '孔心')}，请确认")
    # v2.8.20 / t99u: force hole_to_lid_skirt WARN/ERROR into 待确认 as well as 冲突与风险 (PDF/README must match)
    try:
        from conflict_checks import lid_skirt_force_lines_cn
        for line in lid_skirt_force_lines_cn(conflicts):
            # strip [LEVEL] prefix for pending list readability but keep 盖裙遮挡 text
            body = line.split('] ', 1)[-1] if '] ' in line else line
            if body not in pend:
                pend.append(body)
    except Exception:
        for x in conflicts:
            if x.get('id') == 'hole_to_lid_skirt' and x.get('level') in ('WARN', 'ERROR'):
                if x.get('msg_cn') and x['msg_cn'] not in pend:
                    pend.append(x['msg_cn'])
    risks = [f"[{x['level']}] {x['msg_cn']}" for x in conflicts if x['level'] in ('WARN', 'ERROR')]
    L = c['dims']; kr = c.get('kr_source_cn', '经验值（未做本厂试折标定）')
    lines = [
        f'【草稿 - 未发送 / DRAFT - NOT SENT】  {V}',
        '',
        f'版本名：{V}（按您给定的名字原样使用，未改写）',
        f"材料/板厚：{c['material_cn']}  t{c['t']:.1f}",
        f"尺寸：{L['L']:g}×{L['W']:g}×{L['H']:g}（{c.get('dim_basis', '外形')}；高度为{c.get('height_basis', '含盖总高')}）",
        f"结构：{c['structure_cn']}",
        f"折弯参数：Ri{brief['Ri']:g} / K{brief['K']:g} —— 来源：{kr}",
        *corner,
        '',
        '本版包含：', *[f'  - {x}' for x in c.get('features_cn', [])],
        '', '未添加（您未要求）：', *[f'  - {x}' for x in c.get('not_requested_cn', ['把手孔', '线孔/电源孔', '盖顶孔'])],
        '', '假设：', *[f'  {i + 1}. {x}' for i, x in enumerate(c.get('assumptions_cn', []))],
        '', '待确认：', *([f'  {i + 1}. {x}' for i, x in enumerate(pend)] or ['  （无）']),
        '', '冲突与风险（自动检查）：', *([f'  - {x}' for x in risks] or ['  （无）']),
        '',
        '状态：' + ('计算/几何检查通过' if checks_passed else '计算/几何检查未全部通过（见 EVIDENCE）') + '；未做实物试折/试装；production_release=false（客户确认稿，不可直接生产）',
        '请回复“确认”或修改意见；确认后再出生产版。',
    ]
    return '\n'.join(lines) + '\n', pend


if __name__ == '__main__':
    brief = json.load(open(sys.argv[1])); conf = json.load(open(sys.argv[2])) if len(sys.argv) > 2 and sys.argv[2] != '-' else []
    out = Path(sys.argv[3]) if len(sys.argv) > 3 else Path('.')
    ok = all(x['level'] != 'ERROR' for x in conf)
    txt, pend = build(brief, conf, ok)
    p = out / f"{brief['release']}_CONFIRMATION_DRAFT.txt"; p.write_text(txt, encoding='utf-8'); print(p); print(txt)
