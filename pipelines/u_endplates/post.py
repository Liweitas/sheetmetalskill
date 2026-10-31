# v2.8.2 pipeline u_endplates: CUT / BEND / NEST via the shared scripts/release_dxf.py (replaces the order-side dxf_post.py).
# usage: AV post.py WORK STAGE_DIR (env SM_JOB). Writes WORK/dxf_checks.json {dxf_checks:[...], nest:{...}}; exit 1 if any check fails.
import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent)); sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts'))
from cfg import *
import release_dxf as RD
W_, R = Path(sys.argv[1]), Path(sys.argv[2])
CN = {'U': 'U形底壳', 'END_L': '左端板', 'END_R': '右端板', 'LID': '上盖'}
rep = json.load(open(W_ / 'report.json'))
bt = lambda n, b: f"{b['id']} 90° Ri{ri:g} 向内折(翼边背离读者)"
lab = {}
for n in CN:
    fx, fy = rep['parts'][n]['flat_size']
    lab[n] = [f"{VER} {CN[n]} {n} {MATERIAL_CN} t{t:g} 展开{fx:.2f}x{fy:.2f} K{K}({'经验值' if KR_SOURCE == 'empirical' else KR_SOURCE}) 视图=成品外表面朝读者 客户确认图-非生产放行"]
if HAS_HANDLES:
    lab["LID"].append(f"把手铆接孔 Ø{D_HDL:g}x{len(handle_holes())} (每只4孔: 宽排{HDL_WIDE:g}/窄排{HDL_NARROW:g}/排距{HDL_ROWS:g}, 宽排朝盖中心) M6过孔（默认孔型85/62/30）")
for n in ('END_L', 'END_R'):   # v2.8.3: outer cover end plates, zero bend
    lab[n].append(f"外封端板 零折平板（无折弯线）：外形=U端部外轮廓{W:g}x{Hb:g}，底角R{ro:g}与U外圆同心；盖住U端面，拼缝{SEAM:g}、轮廓退让{END_INSET:g}、上边{'齐口' if END_TOP_FLUSH else '低于口'}")
c3 = rep['corner03']   # v2.8.3: lid corners = skill 03 scheme
lab['LID'].append(f"盖角=技能03方案(斜角03 斜角折弯收口) corner_gap={c3['corner_gap']:g}({'用户指定' if CORNER_GAP_SOURCE == 'user' else '候选值,待确认'}) 长裙全长 短裙两端各退{c3['short_skirt_retreat']:g} 每角斜边 P1({c3['P1'][0]:.3f},{c3['P1'][1]:.3f}) P2({c3['P2'][0]:.3f},{c3['P2'][1]:.3f}) P3({c3['P3'][0]:.3f},{c3['P3'][1]:.3f}) 距展开外角")
checks, nest = RD.post_release(W_, W_ / 'report.json', R, VER, list(CN), order=NEST_ORDER, sheet=SHEET, margin=NEST_M, gap=NEST_G,
                               material_cn=MATERIAL_CN, bend_text=bt, extra_labels=lab)
json.dump({'dxf_checks': checks, 'nest': nest}, open(W_ / 'dxf_checks.json', 'w'), indent=1, ensure_ascii=False)
for c in checks: print(c['file'], c['role'], 'PASS' if c['pass'] else 'FAIL ' + '; '.join(c['fails']))
sys.exit(0 if all(c['pass'] for c in checks) else 1)
