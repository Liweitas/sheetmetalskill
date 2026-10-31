# v2.8.2 pipeline u_l_t7u (DEFAULT structure): vendored from 干画图3's /workspace/orders/box-180x420x175/addendum-tools (S-201-1-20261021-007-v1).
# v2.8.2 changes: hardcoded order/skill/tmp paths -> env SM_ORDER (order folder) + this folder; job features from release_config.json.
# README / NAMING_NOTE / CONFIRMATION_DRAFT for box-180x420x175 (002 format). Values read from this job's reports. plain python3
import json,sys,datetime,os
# v2.8.2 guard: this file is the 007 TEXT template (customer quote "开孔距离离边5厘米", Ø12 roof pair, 002 references).
# It must not be reused verbatim for another job (would invent holes / quote the wrong customer). Other jobs: write README by hand
# and generate the confirmation draft with scripts/confirm_draft.py. Override only to reproduce 007: SM_README_TEMPLATE=007.
if os.environ.get('SM_README_TEMPLATE')!='007':sys.exit('make_readme.py is the 007 text template - see pipelines/README.md (set SM_README_TEMPLATE=007 only to reproduce 007)')
from pathlib import Path
sys.path.insert(0,__import__('os').path.dirname(__import__('os').path.abspath(__file__)));import cfg
VER=cfg.VER;B=Path(cfg.B);W=Path(cfg.W);OUT=B/'named_release'/VER;OUT.mkdir(parents=True,exist_ok=True)
rep=json.load(open(W/'E_main_report.json'));nest=json.load(open(W/'nest_report.json'));cl=json.load(open(B/'logs/clearance.json'))
lay=json.load(open(B/'logs/bend_pdf_layout_check.json'));src=json.load(open(B/'logs/bend_pdf_dimension_sources.json'))
fs=nest['flat_sizes'];f=lambda v:f'{v[0]:.2f} x {v[1]:.2f}';g=lambda v:f'{v:.2f}'.rstrip('0').rstrip('.')
lb=cl['LID_box_coords'];bm=cl['bend_margin_check'];m4=cl['body_M4_box_coords'];nb=nest['no_bend_no_dash']
ncoll=sum(len(p['collisions']) for p in lay['pages'])+len(lay['placement_issues']);assert ncoll==0,ncoll
assert not nb['bend_layer_present'] and nb['bend_entities']==0 and nb['non_continuous_entities']==0
nsrc=len(src) if isinstance(src,list) else len(src.get('entries',src))
(x1,y1),(x2,y2)=lb['Oroof_centres'];xs=[g(v) for v in m4['x_positions_long_walls']];ys=[g(v) for v in m4['y_positions_short_walls']]
xsl=[g(v+1.5) for v in m4['x_positions_long_walls']];ysl=[g(v+1.5) for v in m4['y_positions_short_walls']]
now=datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
# 180x420x175 values derived from reports
LX,WY,HZ=rep['params']['L'],rep['params']['W'],rep['params']['H']
fl=rep['parts']['LID'];Fh=sorted(json.load(open(W/'verification_E.json'))['LID_dxf_roof_holes_flat'],key=lambda q:q[1])
nl=nest['placement']['LID'];Nh=[(q[0]+nl[0],q[1]+nl[1]) for q in Fh]
ly1,ly2=y1-lb['lid_outer_ymin'],y2-lb['lid_outer_ymin']
nU=len(rep['parts']['U'].get('holes',[])) if isinstance(rep['parts']['U'].get('holes'),list) else 10
readme=f"""{VER}  -  CONFIRMATION DRAFT (production_release=false) / 确认稿，未放行生产
Generated {now} Asia/Shanghai (UTC+8)  - R01 first issue. Same workflow / tools / format / style as S-201-1-20261025-002-v1 (650x375x170).

Order / 订单: {cfg.MATERIAL_EN} (材料 {cfg.MATERIAL_CN}), t=1.0 mm, {g(LX)} x {g(WY)} x {g(HZ)} mm (outer {g(LX)} x {g(WY)}, total height {g(HZ)} incl. lid), 1 set
  "新的图 S-201-1-20261021-007-v1 长42宽18高17.5 开孔距离离边5厚米 样式跟上面一样"  (5厚米 read as 5厘米 = 50 mm)
  -> 长420 宽180 高175(含盖)；盖顶 Ø12 x2：靠左短边({g(WY)}边)居中，孔距30（沿{g(WY)}方向），孔心距盖左外边50（孔边44）；无把手；
     其余同 S-201-1-20261025-002-v1（U+L、L盖U退0.2、盖裙15、盖角长裙盖短裙退0.2、固定孔按尺寸排布）

Structure / 结构 (same scheme as 002)
  Part 01 U   : left/back/right wrap, 2 vertical bends B1/B2 (UP 90), flat {f(fs['U'])}, Ø3.3 (M4 tap) x{bm['U_M4']['holes']}
  Part 02 L   : front + bottom, 1 bend B1, covers U, exposed edges set back 0.2, flat {f(fs['L'])}, Ø3.3 (M4 tap) x{bm['L_M4']['holes']}
  Part 03 LID : lid with 4 skirts (DOWN 90), skirt 15, flat {f(fs['LID'])}, Ø4.5 x{bm['LID_skirt_O4.5']['holes']} + Ø12 x2
                corners as 002: long ({g(LX)}) skirts cover short ({g(WY)}) skirt ends, exposed end set back 0.2, zero gap; bend order B1/B4 (short) then B2/B3 (long)
  Body height {g(HZ-1.2)} (={g(HZ)}-1.0-0.2); lid outer {g(LX+3)} x {g(WY+3)} x 15; lid-to-body clearance 0.5 per side.
  Bend: inner R0.8, K(ANSI)=0.4 (experience values, NOT calibrated - first-article check).

Lid top holes (box coords: origin = body outer corner, X along {g(LX)}, Y along {g(WY)}, X=0 = left short edge)
  Ø12 x2 at ({g(x1)},{g(y1)}) and ({g(x2)},{g(y2)}); pitch {g(lb['Oroof_pitch_y_t13u'])} along Y, centred about Y={g(WY/2)} (body {g(WY)}) = centre of lid outer {g(lb['lid_outer_width_y'])} (Y {g(lb['lid_outer_y_range'][0])}..{g(lb['lid_outer_y_range'][1])}).
  Centre {g(lb['Oroof_centre_to_lid_outer_face_x'])} from the lid left outer face; hole edge {g(lb['Oroof_edge_to_lid_outer_face_x'])} from it ("开孔距离离边5厘米" taken as CENTRE 50 from the lid edge - assumption, see open points).
  Lid-edge coords: X {g(lb['Oroof_centre_to_lid_outer_face_x'])} from lid left outer edge; Y {g(ly1)} / {g(ly2)} from lid front outer edge (= {g(ly1)} from the back edge too, symmetric).
  LID flat (DXF) centres: ({Fh[0][0]:.3f}, {Fh[0][1]:.3f}) / ({Fh[1][0]:.3f}, {Fh[1][1]:.3f})  (symmetric about flat centre Y={fs['LID'][1]/2:.3f}).
  NEST sheet centres: ({Nh[0][0]:.3f}, {Nh[0][1]:.3f}) / ({Nh[1][0]:.3f}, {Nh[1][1]:.3f}).
  No handle, no handle holes.

Fixing holes (same logic as 002: holes on all 4 walls, centre 7.5 below lid top, z={g(m4['body_fixing_hole_centre_z'])}; spacing scaled to this size)
  Front (L) / back (U) long walls: X = {' / '.join(xs)}   ({len(xs)} each)
  Left / right (U) short walls   : Y = {' / '.join(ys)}   ({len(ys)} each)
  Body Ø3.3 (M4 tap) x{bm['U_M4']['holes']+bm['L_M4']['holes']} (U x{bm['U_M4']['holes']}, L x{bm['L_M4']['holes']}); lid skirts Ø4.5 x{bm['LID_skirt_O4.5']['holes']} at the same positions
    (lid-edge coords: long skirts X {' / '.join(xsl)}, short skirts Y {' / '.join(ysl)}; centre 7.5 below lid top).
  M4 centre {g(m4['centre_below_body_top'])} below the body top, hole edge {g(m4['hole_edge_to_body_top_edge'])} from the top cut edge (no rim flange, no bend at the top edge);
  nearest M4 centre to a vertical corner outer face {g(m4['min_centre_to_vertical_corner_outer_face'])}.

Bend-margin check (edge of hole to bend line; rule >= 3 mm)
  U M4  : centre {g(bm['U_M4']['min_centre_to_bend_line'])} / edge {g(bm['U_M4']['min_edge_to_bend_line'])}  OK
  L M4  : edge {g(bm['L_M4']['min_edge_to_bend_line'])}  OK
  LID Ø4.5 skirt holes: edge {g(bm['LID_skirt_O4.5']['min_edge_to_bend_line'])} (to bend tangent {g(bm['LID_skirt_O4.5']['min_edge_to_bend_tangent'])})  OK (same as 002)
  LID Ø12: edge {g(bm['LID_roof_O12']['min_edge_to_bend_line'])} (to bend tangent {g(bm['LID_roof_O12']['min_edge_to_bend_tangent'])})  OK
  Ø12 edge-to-edge {g(lb['Oroof_edge_to_Oroof_edge'])}; Ø12 to nearest skirt Ø4.5 hole (flat, edge-to-edge) {g(cl['LID']['Oroof_to_nearest_skirt_hole_edge'])} - no clash
  Ø12 edge to body inner wall: left {g(lb['Oroof_edge_to_body_inner_wall_x'])}, front/back {g(lb['Oroof_edge_to_body_inner_wall_y'])}; Ø12 edge to roof bend tangent {g(lb['Oroof_edge_to_roof_bend_tangent_x'])}.

Checks
  STEP: U/L/LID each 1 valid solid; ASSEMBLY {g(LX+3)} x {g(WY+3)} x {g(HZ)}; hole probes open; part intersections 0.
  DXF: native SheetMetal unfold; DXF_CUT = cut contours + holes; DXF_BEND = same flats with bend lines.
  NEST: 1 sheet 2440x1220 (margin 10, gap 10), {nest['layout']}, used {nest['used_length_x']:.2f} x {nest['used_height_y']:.2f};
        layers {', '.join(nb['layers'])}; NO BEND layer, 0 bend entities, 0 dashed/non-continuous entities; audit errors {nest['audit_errors']}.
  PDF: 4 A3 landscape pages, {nsrc} dimension values sourced from DXF/STEP, text/line collision check 0 on all pages + visual check.

Files (every file name starts with {VER})
  {VER}_完整折弯工艺PDF_折弯师傅作业图_4页.pdf : page1 assembly, 2 U, 3 L, 4 LID  (in OPEN_ME.zip as {VER}_BEND_PDF_4p.pdf)
  STEP/      : U, L, LID, ASSEMBLY, EXPLODED
  DXF_CUT/   : laser cut flats (layer CUT, mm)          DXF_BEND/ : flats + bend lines (layer BEND)
  NEST/      : 2440x1220 sheet, cut only (no bend lines)
  PREVIEW/   : PAGE-1..4, LID_iso, ASSEMBLY_iso, LID_CORNER_closeup, NEST_preview
  EVIDENCE/  : brief, main report, verification, clearance, nest report, PDF dimension sources, PDF layout check, lid corner probe
  *_OPEN_ME.zip : all of the above deliverables in one ASCII-named folder
  *_CONFIRMATION_DRAFT.txt : customer confirmation text (NOT sent)
Units mm. Use numbers, do not scale from paper.

Open points (HOLD / 待确认)
  1. "开孔距离离边5厘米" (written 5厚米) is taken as hole CENTRE 50 from the lid outer left edge (hole edge 44). If the customer meant hole EDGE 50, centre moves to 56 (box X 54.5).
  2. Ø12 pair placed at the left short end (X=0, U left wall / LID bend B1), centred on {g(WY)}, pitch 30 (pitch and short-edge placement taken from 002 "样式跟上面一样").
  3. Date in the prefix is 20261021 as given in the order.
  4. K/R not calibrated on your press brake; first article to confirm. Lid corner apex as 002 (tiny <=0.6 opening only at the bend apex).
Source: skill step-sheetmetal-delivery v2.8.2 pipeline u_l_t7u (skill_R01, brief briefs/*.brief.json, revision R01_201T1_OUTER) + E-style addendum (addendum-tools/, work_main/).
All other order folders under /workspace/orders are untouched (box-375x650x170 read only, as the style reference).
"""
note=f"""Release prefix {VER} (given by the order). Status: confirmation draft, production_release=false.
Every delivered file name starts with {VER} (incl. README / NAMING_NOTE / EVIDENCE files and all files inside OPEN_ME.zip).
Name parts: S-201 = material 201 stainless | 1 = t 1.0 | 20261021 = date (as given) | 007 = serial | v1 = version.
To rename: SM_ORDER=<order dir> python3 <skill>/pipelines/u_l_t7u/rename_release.py NEWVER
  (updates release_config.json, regenerates previews / PDF / README / release, removes the old named folder, checks STEP/DXF/NEST are byte-identical).
Built with the same workflow/tools as S-201-1-20261025-002-v1 (box-375x650x170, tools copied into this folder); that release is untouched.
"""
_t=rep['params']['t'] if 'params' in rep else 1.0   # user t52u thin-sheet M4 warning
M4W=(f'\n   警告：{_t:.1f} mm 板直接攻M4（底孔Ø3.3）仅约1扣有效螺纹，强度偏低、易滑牙，不建议反复拆装；替代方案 压铆螺母 / 拉铆螺母 / 点焊螺母 待确认。' if _t<=1.2+1e-9 else '')
draft=f"""[CONFIRMATION DRAFT - NOT SENT]  {VER}  (production_release=false)
您好，{g(LX)}×{g(WY)}×{g(HZ)} 箱子（{cfg.MATERIAL_CN} 1.0，含盖总高{g(HZ)}）首版确认稿已出，请确认：
1. 盖顶 Ø12 两孔，样式同上一单：放在左侧短边（{g(WY)}边）一侧，沿{g(WY)}方向排列，孔距30，左右居中（中心距箱体前外面 {g(y1)} / {g(y2)}，距盖前后外边各 {g(ly1)}）；
   "开孔距离离边5厘米"按孔中心距盖左外边50做（孔边距盖外边44）；如您指的是孔边距50，请告知（孔心改为56）。
2. 不做把手，无把手孔。
3. 固定孔同上一单做法：箱体 Ø3.3 攻M4，盖裙 Ø4.5，长边各{len(xs)}个、短边各{len(ys)}个（按尺寸排布），孔中心距盖顶7.5；孔离折弯线都大于3mm。{M4W}
4. 其余同上一单：U+L结构L盖U退0.2，盖裙15，盖角长裙盖短裙退0.2，内R0.8，K0.4（首件试折确认）。
5. 下料：三件排在一张 2440×1220 板上。
确认后再放行生产。附：4页折弯图PDF、STEP、DXF、排版。
"""
for p,t in ((f'{VER}_README.txt',readme),(f'{VER}_NAMING_NOTE.txt',note),(f'{VER}_CONFIRMATION_DRAFT.txt',draft)):(OUT/p).write_text(t,encoding='utf-8')
print('written',OUT,'pdf dims',nsrc,'collisions',ncoll)
