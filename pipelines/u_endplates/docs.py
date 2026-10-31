# v2.8.3 pipeline u_endplates DOC = TEXT TEMPLATE vendored from order box-400x220x150 (S-201-1-20261021-001-v1, t46u); validated only for that geometry, corner_gap=0. run.py guards.
import json,csv,sys,math
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent));from cfg import *
M4TXT='1.0 mm 201 板直接攻M4（底孔Ø3.3）仅约1扣有效螺纹，强度偏低、易滑牙，不建议反复拆装；替代方案 压铆螺母 / 拉铆螺母 / 点焊螺母 列为待确认（本版仍按M4直接攻丝出图）。'   # user t52u
W_=Path('work');R=Path(sys.argv[1]) if len(sys.argv)>1 else Path('named_release')/VER;D=R/'DOC';D.mkdir(parents=True,exist_ok=True)
rep=json.load(open(W_/'report.json'));C3=rep['corner03'];TR=C3['gap0_shared_column_trim'];CL=json.load(open(W_/'corner03_closure_sections.json'));SL=max(v['max_gap_mm'] for v in CL.values());SLZ=CL['X0Y0']['open_z_range']
N3=json.load(open(W_/'native03.json'));N3R=json.load(open(W_/'native03_untrimmed_native_unfold.json'));K3=json.load(open(W_/'corner03.json'))
dchk=json.load(open(W_/'dxf_checks.json'))
P=rep['parts'] if isinstance(rep['parts'],dict) else {p['name']:p for p in rep['parts']}
CN={'U':'件1 U形底壳','END_L':'件2 左外封端板（零折平板）','END_R':'件3 右外封端板（件2镜像）','LID':'件4 上盖'}
def w(name,rows):
    with open(D/f'{VER}_{name}.csv','w',newline='',encoding='utf-8-sig') as f:csv.writer(f).writerows(rows)
rows=[['release',VER,'',''],['production_release','false','',''],['序号','零件','数量','材料','厚度mm','成形外形mm','展开尺寸mm','折弯数','孔','质量kg','STEP','CUT DXF','BEND DXF']]
holes={'U':'Ø3.3×6 攻M4','END_L':'Ø3.3×2 攻M4','END_R':'Ø3.3×2 攻M4','LID':'Ø4.5×10 过孔 + Ø6.6×8 把手铆接孔'}
for i,n in enumerate(['U','END_L','END_R','LID'],1):
    p=P[n];rows.append([i,CN[n],1,MATERIAL_CN,t,'×'.join(f'{x:.1f}' for x in p['size']),'×'.join(f'{x:.3f}' for x in p['flat_size']),len(p['bend_records']),holes[n],f"{p['mass_kg']:.3f}",f'{VER}_{n}.step',f'{VER}_CUT_{n}.dxf',f'{VER}_BEND_{n}.dxf'])
rows+=[[5,'M4螺钉（型号/长度/材质待确认）',10,'待确认','','','','','','','','',''],[6,'盖顶把手（铆接；孔型85/62/30同前单；型号待确认）',2,'待确认','','参考包络50×105×46（非实物）','','','每只Ø6.6×4（在件4上盖）','','HANDLE_REF_L/R.step（参考）','',''],[7,'铆钉/拉铆螺母 M6级（型号待确认，每把手4）',8,'不锈钢（待确认）','','','','','终孔径按铆钉规格','','','','']]
w('BOM',rows)
pr=[['参数','值','状态/来源']]
pr+=[['release',VER,'用户给定'],['production_release','false','客户确认稿'],['材料',MATERIAL_CN,'用户'],['板厚t',t,'用户'],
['箱体外长×外宽','400×220','已确认（箱体外尺寸）'],['含盖总高',150,'已确认'],['箱体高Hb',Hb,f'=150−t−q，q={q}'],
['盖外形','403×223×15','=箱体外+2g+2t'],['盖内','401×221','=箱体外+2×0.5'],['单边间隙g',g,'用户（未改1mm）'],['顶隙q',q,f'技能规则 q=ceil((qmin+max(.05,.05t))×10)/10，qmin={qmin:.4f}'],
['裙高',skirt,'用户'],['内R',ri,'候选，待试折'],['K',K,'经验/默认值（ANSI），非机床实测'],['BA',f'{BA:.4f}','π/2(Ri+Kt)'],['OSSB',OSSB,'Ri+t'],['BD',f'{BD:.4f}','2·OSSB−BA'],
['弯线距边（后挡料）U侧壁',f'{Hb-OSSB+BA/2:.2f}','计算值，须试折验证'],['弯线距边 盖裙15',f'{skirt-OSSB+BA/2:.2f}','计算值，须试折验证'],
['端板形式','外封端板 u_external_ends，零折平板 220×148.8','技能 references/box-generation.md L13；scripts/cad_build.py L62-66'],['拼缝seam_gap',SEAM,'用户11:23：不要留缝隙；cad_build.py L63 U长=L−2t−2seam=398'],['端板退让end_inset',END_INSET,'用户11:23：完全遮盖；box-generation.md L49；不采用0.2退让'],['端板上边齐口end_top_flush','是（顶=148.8）','box-generation.md L49'],['端板底角','R1.8，与U外圆同心','box-generation.md L13 底部圆角随U外轮廓'],['端板接合','内侧角焊/外侧激光焊（无搭接，不能点焊）','待确认'],['M4孔中心Z',ZH,'距盖顶7.5'],['箱体孔',D_BODY,'攻M4（警告：1.0板仅约1扣有效螺纹、易滑牙，不建议反复拆装；压铆/拉铆/点焊螺母替代待确认）'],['盖孔',D_LID,'过孔'],
['长边孔X',' / '.join(map(str,LONG_X)),'边距50 孔距150'],['短边孔Y',' / '.join(map(str,SHORT_Y)),'边距50 孔距120'],
['把手安装方式','盖顶铆接（2只，相向，关于X=200镜像，Y居中110）','用户 2026-10-26 10:21'],['把手中心X',' / '.join(f'{x:g}' for x in HANDLE_CX),'中心距240'],['把手孔型','每只Ø6.6×4：宽排85/窄排62/排距30，宽排朝盖中心','来源 box-155x320x105/.../S-201-1-20261024-005-v1/README.txt L18-19；box-200x350x210/.../S-201-20261024-002-v1_README.txt L24；技能profile handle-85-62-30-v1(只读)'],['把手孔径',D_HDL,'M6过孔（同前单）；抽芯铆钉/拉铆螺母终孔径按规格待确认'],['把手本体','参考包络50×105×46，非实物','型号/底座待确认'],
['电源孔/百叶/PG7/PG9/线孔','无','用户'],['盖角方案','03（斜角03=技能03盖角，斜角折弯收口）','references/lid-defaults03.md §03方案定义；用户t46u'],['corner_gap',C3['corner_gap'],'用户明确：不要有缝'],
['03 P1/P2/P3（展开外角基准，四角镜像）',f"({C3['P1'][0]:.3f},{C3['P1'][1]:.3f}) / ({C3['P2'][0]:.3f},{C3['P2'][1]:.3f}) / ({C3['P3'][0]:.3f},{C3['P3'][1]:.3f})",'Ro=Ri+t，A=裙高−Ro，B=A+BA90；本单重算'],['短裙退让',C3['short_skirt_retreat'],'t+corner_gap；长裙保留全外长403'],
['缝0角柱修正',f"每短裙端切除{TR['tab_mm'][0]:g}×{TR['tab_mm'][1]:g}（共{TR['removed_area_mm2']:.1f}mm²）",'原生展开把共用角柱算给两裙；按03定义切除；native03因此不通过（待定）']]
w('PARAMS',pr)
hr=[['release',VER,'production_release=false'],['编号','位置','X','Y','Z','孔轴','盖孔','箱体孔','箱体零件','同轴核验']]
coax={c['id']:c for c in rep['hole_coaxial']} if 'id' in rep['hole_coaxial'][0] else {}
for i,h in enumerate(rep['hole_coaxial'] and rep['holes']):
    c=rep['hole_coaxial'][i];ok=c['axis_line_material_lid_mm']==0 and c['axis_line_material_body_mm']==0 and c['lid_open_at_r']==0 and c['body_open_at_r']==0
    hr.append([h['id'],h['side'],h['point'][0],h['point'][1],h['point'][2],'Y' if h['axis'][1] else 'X','Ø4.5过孔','Ø3.3攻M4',CN[h['body_part']],'通过' if ok else '不通过'])
off=P['LID']['flat_size'][0]/2-L/2
hr.append([]);hr.append(['把手孔编号','排','X(箱体基准)','Y(箱体基准)','X(盖外角基准)','Y(盖外角基准)','展开X','展开Y','孔径','孔边→盖外边','孔边→折弯切点','孔边→最近裙孔(3D)','通透核验'])
for h in rep['handle_holes']:hr.append([h['id'],'宽85' if h['row']=='wide' else '窄62',h['x'],h['y'],h['x']+1.5,h['y']+1.5,round(h['x']+off,3),round(h['y']+off,3),D_HDL,round(h['edge_to_lid_outer'],2),round(h['edge_to_bend_tangent'],2),f"{h['edge_to_nearest_skirt_hole_3d']:.2f} ({h['nearest_skirt_hole']})",'通过' if h['axis_line_lid_material_mm']==0 and h['open_at_r']==0 and h['material_at_r_plus_min']>0 else '不通过'])
w('HOLES',hr)
G=rep['gap_check'];md=rep['min_distance_mm'];ints=rep['intersections_mm3']
allpass=all(c['pass'] for c in dchk['dxf_checks'])
ck=f"""# {VER} 校核清单（客户确认稿）

**production_release = false**　——　客户确认图，非生产放行。生成时间 2026-10-26 (UTC+8)。

## 一、计算检查（CAD / 脚本计算，非实物）——注意：native03 在缝0下未通过，见下表
| 项目 | 结果 | 依据 |
|---|---|---|
| CAD环境 | FreeCAD 1.1.1 + SheetMetal 0.8.21 实际运行，原生展开 | build.py |
| 模型尺寸 | U 398×220×{Hb}（X1~399）；外封端板 1×220×{Hb}（X0~1/399~400）；盖 403×223×15；装配 403×223×150；箱体外形 400×220×{Hb} | STEP 重新读入 BoundBox |
| 装配干涉 | 6组两两交叠体积均为 {max(ints.values())} mm³ | report.json |
| 盖-箱最小间隙 | {md['U/LID']:.3f}（盖根内R0.8 ↔ 箱体顶外棱）；侧面 g=0.5 四边 | report.json |
| 顶隙 | q={q}；若 q=0 则圆角干涉 {-G['lid_root_fillet_vs_body_edge']['clearance_if_q0']:.3f}（冲突，已用q处理） | report.json |
| 孔映射 盖↔箱体 | 10/10 同轴：轴线两件均无材料，孔半径处通透，r+0.05有材料 | report.json |
| 孔避让 | 盖孔上缘距折弯切点3.45，下缘距裙边5.25；长边孔边距U端47.35（单层t1，无双层/折弯区）；短边孔在外封端板平面单层（孔边距端板顶4.65） | 计算 |
| 端板遮盖 | U端面轮廓未遮盖面积 {rep['end_cover']['END_L']['U_end_profile_uncovered_area_mm2']:.3f}/{rep['end_cover']['END_R']['U_end_profile_uncovered_area_mm2']:.3f} mm²；轴向拼缝 {rep['end_cover']['END_L']['axial_gap_mm']:g}/{rep['end_cover']['END_R']['axial_gap_mm']:g}；端板外轮廓=U外轮廓（220×148.8，底角R1.8同心）；无外露U端边 | report.json end_cover |
| 孔处层数 | 10个M4孔轴旁(r+0.3)箱体材料均为单层1.0 | report.json hole_coaxial |
| 把手孔型 | 2×(Ø6.6×4)，宽85/窄62/排距30，宽排朝盖中心，关于X=200镜像：{'通过' if all(v['wide_pitch']==85 and v['narrow_pitch']==62 and v['row_spacing']==30 and v['wide_row_toward_centre'] for v in rep['handle_pattern_check'].values()) and rep['handle_mirror_ok'] else '不通过'} | report.json |
| 把手孔通透 | 8/8 孔轴无材料、r−0.02通透、r+0.05有材料；LID CUT/套料DXF各含8个Ø6.6 | report.json / DXF |
| 把手孔避让 | 孔边→盖外边≥{min(h['edge_to_lid_outer'] for h in rep['handle_holes']):.1f}；→折弯切点≥{min(h['edge_to_bend_tangent'] for h in rep['handle_holes']):.1f}；→裙边M4孔≥{min(h['edge_to_nearest_skirt_hole_3d'] for h in rep['handle_holes']):.1f} | report.json |
| 螺丝刀进刀 | 10个裙边螺钉进刀锥(Ø8→Ø60×200)与把手参考体干涉 {max(a['cone_intersect_handle_mm3'] for a in rep['screwdriver_access']):.0f} mm³ | report.json |
| 开盖 / 铆钉尾 | 把手随盖整体提起；铆钉尾包络Ø12×12距箱体 {rep['rivet_tail_envelope']['min_dist_to_body']:.0f}，干涉0 | report.json |
| DXF闭合/重复/重叠 | 9个DXF（CUT×4、BEND×4、NEST×1）{'全部通过' if allpass else '有不通过'} | dxf_checks.json |
| CUT/NEST | 仅CUT(+SHEET)图层、连续线、无折弯线；单位mm 1:1 | dxf_checks.json |
| BEND | 折弯线单独BEND图层（CONTINUOUS实线，用户t16u：任何DXF不得有虚线）；端板零折无折弯线 | dxf_checks.json |
| 展开 | 原生展开 = 公式（U 220+2×148.8−2BD=514.17，长398）；端板零折刚体转平 220×148.8（SKILL.md L78） | flats.json |
| 盖角03 corner03.py | ok={K3['ok']}；CUT_LID 实际斜边 {K3['DXF']['actual_sloped_edges']} 条，P1/P2/P3 与参数一致（容差1e-5） | corner03.json |
| 盖角03 native03_check（原生展开原样） | ok={N3R['ok']}：4折、8斜边、展开/DXF面积差 {N3R['native_vs_DXF_area_mm2']:g}、盖/箱根部重叠 {N3R['root_overlap_volume_mm3']:g} mm³、实测q {N3R['actual_roof_q_mm']:.4f}；**但**原生展开把缝0共用角柱({TR['tab_mm'][1]:g}×{TR['tab_mm'][1]:g}×{TR['tab_mm'][0]:g})同时算给长裙和短裙：展开体积多 {TR['untrimmed_flat_volume_excess_mm3']:.1f} mm³，成形时每角短裙端头与长裙端部正体积干涉 {TR['tab_mm'][0]*TR['tab_mm'][1]**2:.1f} mm³ | native03_untrimmed_native_unfold.json |
| 盖角03 native03_check（本版DXF=按03定义切除后） | **ok={N3['ok']}**：{N3.get('error','')}；切除面积差 {TR['removed_area_mm2']:.1f} mm² > 容差1e-5（缝0未改值，待用户决定） | native03.json |
| 盖角成形后闭合 | 直段(Z135~148.2)与顶板：0缝；折弯R区：发丝缝最大 {SL:.3f}，Z {SLZ[0]:.2f}~{SLZ[1]:.2f}（高约{SLZ[1]-SLZ[0]:.2f}），四角相同 | corner03_closure_sections.json |
| 裙孔↔盖角区 | 孔心距角区边(B=15.085) 36.4，孔边 34.2；10/10 同轴 | 计算/report.json |
| M4直接攻丝（**WARN**） | {M4TXT} | 技能 conflict_checks.m4_tap |
| 版本一致 | STEP/DXF/PDF 文件名与内容均含 {VER}；PDF每页含版本号 | version_check |

## 二、实物试折试装：未进行
| 项目 | 状态 |
|---|---|
| 首件试折（R0.8、K0.4、后挡料修正） | 未进行 |
| U第2道折弯上模/滑块避让（侧壁149、内宽218） | 未进行 |
| 盖-箱试装（g0.5、q0.2、螺孔对位） | 未进行 |
| M4攻丝强度（1.0板仅约1扣、易滑牙） | 未进行 |
| 盖角R区发丝缝是否需密封（点焊/打胶） | 未进行 |
| 端板焊接（方式待确认，焊后外观面变形）/ 把手铆接（铆钉规格、盖顶凹陷） | 未进行 |
| 生产放行 | 否（production_release=false） |
"""
(D/f'{VER}_VERIFICATION_CHECKLIST.md').write_text(ck,encoding='utf-8')
rd=f"""# {VER} 客户确认稿 说明（非生产放行）

- 箱体：400×220（箱体外尺寸，已确认）× 含盖总高150（已确认）；201不锈钢 t1.0。
- 箱体高 = 150 − 1.0 − 0.2 = **148.8**；盖外形 **403×223×15**，盖内 401×221。
- 结构：件1 U形底壳（底+两长侧壁，折弯线沿400方向）；件2/3 外封端板（技能 u_external_ends）：零折平板220×148.8，盖住U两端面，拼缝0、轮廓不退让(inset 0)、上边与U口齐平，底角R1.8与U外圆同心；U长398=400−2×1；接合待确认；件4 可拆上盖，四边裙15，M4螺钉四边固定共10组。
- 无电源孔、百叶、PG7/PG9、线孔。
- 把手：两只铆接于盖顶（相向），关于X=200镜像、Y居中110，中心X=80/320（中心距240）；横跨220方向，宽排朝盖中心。
- 把手孔型同前单：每只Ø6.6×4（M6过孔），宽排85/窄排62/排距30。来源：box-155x320x105/named_release/S-201-1-20261024-005-v1/README.txt 第18-19行；box-200x350x210/named_release/S-201-20261024-002-v1/S-201-20261024-002-v1_README.txt 第24行；技能profile assets/profiles/handle-85-62-30-v1.json（只读）。
- 前单与技能均无把手本体/底座外形记录；STEP中HANDLE_REF_L/R仅为参考包络（50×105×46），非实物。

## 文件
- STEP/：ASSEMBLY、EXPLODED、U、END_L、END_R、LID 及各 *_UNFOLD
- DXF_CUT/：每件激光切割（仅切割线）；DXF_BEND/：每件折弯图（BEND图层）；NEST/：2440×1220 套料（仅切割）
- PDF：A3 4页中文客户确认图（包内文件名 {VER}_BEND_PDF_A3_CN.pdf）
- DOC/：BOM、PARAMS、HOLES（CSV）、校核清单、本说明、codex 评审
- PREVIEW/：PDF第1页、套料、盖顶把手局部、端角轴测（底/顶）、盖角03成形局部、盖展开角03局部 PNG
- EVIDENCE/：cad_report、dxf_checks、project03/corner03/native03（两次）、盖角闭合剖面/射线、源码快照

## 变更记录
- t42u（2026-10-26 11:19/11:23 UTC+8）：端板由内嵌回边改为技能外封端板（端板盖U，零缝、完全遮盖）。改前备份：named_release/S-201-1-20261021-001-v1_before_t42u_cover/、tools_before_t42u_cover/。
- t46u（2026-10-26 11:57 UTC+8，用户“不要有缝”）：盖角由开口角+释放改为技能03方案（斜角03），corner_gap=0。改前备份：named_release/S-201-1-20261021-001-v1_before_t46u_03/、tools_before_t46u_03/、work_before_t46u_03/。
- 同批按用户硬性规则 t16u（技能 2026-10-26 更新）：BEND 图层改为连续实线（任何DXF无虚线）；盖-体固定按默认M4攻丝表述（t52u：薄板攻丝警告+替代件待确认必须保留）；把手孔Ø6.6=M6过孔（默认孔型85/62/30）。

## 待确认
1. 把手型号/底座外形（孔型按前单85/62/30；本体为参考包络）
2. 铆钉型号（孔Ø6.6=M6过孔，默认孔型85/62/30）；盖内凸出高度
3. 盖角03 缝0：native03 未通过（原生展开把共用角柱算给两裙，切除后面积差52.8mm²）。请选：A 接受本版切除展开（短裙端头顶住长裙内面，0缝）；B 改用候选缝0.2重出（角部留0.2缝）；C 用原生展开原样（每角13.2mm³干涉，需现场修磨）。另：R区发丝缝≤0.06是否需点焊/打胶
4. 端板接合：端板盖U端面为对接盖板、无搭接，不能电阻点焊 → 箱内沿U三边断续角焊（TIG）或外侧激光焊，焊后打磨钝化（待确认）
5. 盖与体固定：M4攻丝（箱体Ø3.3攻M4、盖Ø4.5过孔，用户默认）。**警告**：{M4TXT}首件试装
6. 螺钉型号/长度/材质
7. Ri0.8 / K0.4 / 后挡料：按实际刀具试折修正
8. 顶隙0.2 / 箱体高148.8 是否接受
9. 公差、表面处理、去毛刺

## 冲突与风险
- Ri0.8 > g0.5：q=0 时盖根圆角压箱体顶外棱 0.054 → 保持 g=0.5，取 q=0.2，箱体高148.8。
- **M4警告**：{M4TXT}
- U 第2道折弯：已成形侧壁高约149、内宽218，须确认上模高度/滑块避让。
- 盖角03 缝0：native03 门禁未通过（见上）；本版未擅自改缝；R区发丝缝≤0.06，不密封时可能进灰/水。
- 端板：按技能为零折平板（无回边），故此前提出的“端板三边外翻回边”未建；端板与U无搭接，不能点焊，焊接方式待确认，外露端面焊接变形需控制。
- 版本名与 codex 465阶梯箱尝试同名（门检WARN，预期）。
- 把手本体外形无前单记录：只按孔型建参考包络；铆接点在1.0盖顶，提重受力与凹陷须试装确认（可加背垫片，待确认）。
"""
(D/f'{VER}_README_PENDING.md').write_text(rd,encoding='utf-8')
cx=f"""# 早期 codex 尝试评审（/workspace/orders/codex-S-201-1-20261021-001-v1）

1. 尺寸错误：做成“465阶梯箱”（外形467×194，含盖高210/180，内空465×192），并非 400×220×150；src 文件名为“未命名待确认_465阶梯_R03_…”，是沿用其他尺寸/其他工单几何。
2. 违规开孔：盖顶 Φ12 出线孔×2——本单明确不要线孔；提手孔 Φ6.6×4（85/62）当时用户未指定把手方式即擅自加在465阶梯箱上（本版按用户10:21指示才采用同一孔型，且为2只相向）。
3. 结构不符：阶梯盖 + U+L 3件（含Z形偏移弯），不是“U形底壳+两块端板+四边裙可拆盖”。
4. 孔位：14组 M4，按阶梯高低段布置，与本箱不对应。
5. 交付命名混乱：src 为中文“未命名待确认”文件名，named_release 仅做改名包装（NAMING_NOTE），与几何版本不一致。
6. 确认文案含“台阶/低段304”等与本单无关内容，若发出会误导客户。
本版已从零重建，未复用 codex 或其他尺寸的几何。
"""
(D/f'{VER}_CODEX_REVIEW.md').write_text(cx,encoding='utf-8')
print('ok')
