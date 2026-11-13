## 2.8.48 本地规则合并 — 2026-11-13（Asia/Shanghai）

- 整合本地新规则：红蓝金样折弯 PDF 最多 6 页、逐道折线及相邻定位尺寸、先长后短及先外后内的建议工序、长箱盖体固定孔，以及第一页成品外形和孔状态；统一入口打包时执行 6 页门禁，超页订单需排版优化后重出。
- 补充开口接水盘一体折结构与异形台阶盖耳的订单经验；当前统一出图入口仍只支持已声明的两类矩形箱体，未覆盖结构须明确暂停，不得回退到旧生成器。
- 保留 2.8.47 的客户原始需求 PDF 追溯与较新的 CAD/DXF/金样实现；修复源 STEP 文件头包含非 UTF-8 字节时的单位识别。
- 本次为规则与审核工具更新，不代表工厂试折、实体装配或生产放行。

## 2.8.47 客户原始需求入 PDF — 2026-11-12（Asia/Taipei）

- 统一入口要求 `customer_requirement_text`，原文逐字传入解析 job；后续客户消息以 `customer_requirement_updates` 追加，不覆盖初始原文，几何仍由显式参数驱动。
- 现有金样引擎为两种结构统一追加客户需求页；保留红蓝版式、原单位、换行和页码，长文本自动续页并通过原有重叠门禁。
- ZIP 增加原文 TXT，PDF 生成记录增加原文 SHA256。旧输入缺原文时服务在 CAD 前拒绝；仅历史 PDF 重绘明确标注缺失，不从参数反编原话。
- 无图片嵌入或 OCR 功能；需求文本可以注明附件文件名。工程验收和确认稿放行边界不变。

## 2.8.46 部署快照同步 — 2026-11-12（Asia/Taipei）

- 将 27 服务器当前 skill 同步至 `Liweitas/sheetmetalskill`，保留原仓库历史；运行代码和金样文件按部署快照原字节保留。
- 包含统一 `build_golden_package.py` 入口、U围＋L适配、矩形开孔、端板把手方向及最新 PDF 排版和回归测试。
- `VERSION` 与既有 `SKILL.md` 元数据统一为 2.8.46；更新 README、当前入口说明及完整文件哈希清单。排除临时备份、缓存和误存字体文件 `--help`。
- 本次为源码同步，不升级工程或实物验收状态。同步范围和本轮检查见 `references/repository-sync-20261112.md`。

## 2.8.45 hotfix — 2026-11-06（Asia/Shanghai）engine_u_endplates 文案去硬编码

来源：Harry t133u / S-201-1-20261106-004-v2 出图时发现 `bend-pdf-golden-001-visual/engine_u_endplates.py` 残留 009 单「3×Φ12+16A品字/盖顶把手」硬编码文案，与本单法兰孔/无把手不符。

### 变更
- `engine_u_endplates.py`：侧视/俯视/关键参数/检查摘要等叙述改为从 JOB `end_features`/`handles` 动态生成；裙净空按孔组最上缘计算并标 WARN/PASS。
- 更新 `GOLDEN_SCRIPTS.sha256`（仅 engine 哈希变；其余四文件不变）。
- VERSION 仍为 2.8.45（视觉锚点未变；属同版正确性补丁）。

## 2.8.45 — 2026-11-06（Asia/Shanghai）

来源：用户 **Harry t59u/t60u** — `S-201-1-20261031-001-v1` PDF「效果非常好」；其他单字号/尺寸位置差很多；可不要限制 4 页；要求更新 skills。

### 根因
- 001-v1：reportlab `make_bend_pdf`+`pdf_common`，`MINPT=9.4`，dim≈9.5，视图 sc≈0.55–1.1。
- 后期 u_endplates 实单：`make_bend_pdf` 分发到 **matplotlib** `engine_u_endplates.py`，默认 dim `fs=6.5`（展开常 5–5.5），页眉硬编码 `n/4`；旧规则26只哈希四文件，**未门禁 engine**，故 009 等与金样四文件 MATCH 却观感远差于 001。

### 变更
- **新金样目录** `assets/bend-pdf-golden-001-visual/`（五文件：四件 reportlab + `engine_u_endplates.py`）。
- engine：`MINPT/FS_DIM=9.4/9.5` 强制；默认拆成 ≥5 页（ASSEMBLY/U/END/LID/Checks）；禁止为卡 4 页缩字。
- reportlab `make_bend_pdf`：bidir `size=8.5`→`9.5`。
- 保留：重叠避让、规则9、页眉出图时间、CJK、海军蓝+红条、规则31 处理面朝外。
- `scripts/check_bend_pdf_golden.py` + `references/bend-pdf-golden.md` 指向新金样；旧 `bend-pdf-golden-004-v2/` 标历史。
- **新规则32**（001 视觉语言）；规则6/12/26 交叉更新。规则31 保留。
- **未**批量重出 009/004/006/008 等客户包（用户只要原因+后续出图+skill）。

证据：`orders/box-320x155x105-inner/work/pdf_style_proof_t59u/EVIDENCE_t59u.md`

## 2.8.44 — 2026-11-06（Asia/Shanghai）

- 用户 **Harry t58u**：`20261105-009` 带孔端板 DXF 相对外侧视角/PDF 被镜像；板材单面表面处理须朝箱体外侧。
- **新规则31**（表面处理面朝外 + 展开手性一致 / chirality / treated-face / exterior-up）：
  - 处理面 = 成形后箱体外侧；下料默认 treated face UP。
  - DXF_CUT/BEND/NEST 与折弯 PDF 展开必须同手性；禁止 PDF 外侧 / DXF 内侧镜像。
  - 展开一律对着外表面看；勿与「镜像同件合 1 页」混淆。
  - `u_endplates` 刚体转平：`END_R` → `X′=Y, Y′=Z, Z′=X−L`（废止旧 `X′=W−Y` 内侧镜像）；`END_L` → `X′=W−Y, Y′=Z, Z′=−X`。
  - 交付前坐标/目视核对 END 孔序 vs brief 外侧 Y；镜像则不得交付。
- 代码：`pipelines/u_endplates/build.py` RIG；订单 `tools/build.py` 同改；订单 `addendum-tools/engine_u_endplates.py` 的 `_er_flat` 与 M4 标记改 `X′=Y`（**未**改金样 `make_bend_pdf.py`/`pdf_common`/`bidir`/`views`，规则26）。
- 实单升版：`S-201-1.5-20261105-009-v1` → **`S-201-1.5-20261105-009-v2`**（几何孔位不变，仅展开手性/处理面朝外）。

## 2.8.43 — 2026-11-05（Asia/Shanghai）

来源：用户 t116u — 实测折弯扣除 BD=4.24（对 v18 实物机测）

- 规则30：**本厂 t=2.0 实测 BD=4.24** 优先于先前口头 3.3（t111u）。
- 换算 BA=2(Ri+t)−BD=3.76、K≈0.196845172（PDF 可写 K≈0.197）。
- 更新 `references/bend-deduction.md`；展开须重算不得只改字。
- 实单 `S-201-2-20261028-001-v19`（几何同 v18；production_release=false）。

## 2.8.42 — 2026-11-05（Asia/Shanghai）

来源：用户 t115u — 台阶盖两端外凸角斜角03

- **台阶盖**：高/低两段 **外端短裙与 ±Y 长裙** 交接的外凸角可套斜角03（按本单 t/Ri/skirt/cg/BA 重算）。
- **中间台阶拐角仍非 03**：高段↔立面干净 45° V；立面↔低段正方缺口+补件等既有方案保留。
- 不得把 native03 全盖 8 斜边门禁硬套到台阶中间拐角并伪造通过；应做局部四角校验并写进 EVIDENCE。

## Order 1105#005 — 2026-11-05（Asia/Shanghai）

来源：用户草图 t37u/t38u（Harry）— 新单 `S-201-1-20261105-005-v1` / `box-400x280x300-1105-005`

- 外形 400×280×300；201 t=1.0；u_endplates；production_release=true → OPEN_ME
- 盖顶双把手相向 cx=90/310 cy=140；wide_row_toward=box_center_x（宽排朝里）
- END_R：Φ18/Φ5/Φ18 横排 Y=60/140/220 Zc=225；孔边距60；孔距居中；距盖裙60；hole_to_lid_skirt=51 PASS
- END_L 空白；薄板攻M4 WARN；BD≈1.7 候选 HOLD（本厂3.3仅t2.0）

## 2.8.41 — 2026-11-05（Asia/Shanghai）

来源：用户 t111u — 折弯扣除系数

- 规则30：BD 常用 ≈1.7×t（1.6~1.7）；**本厂 t=2.0 201 → BD=3.3**。
- 换算 BA=2(Ri+t)−BD、K=(BA/(π/2)−Ri)/t；例 BA=4.7、K≈0.496。
- 新增 `references/bend-deduction.md`；PDF须标 BD；展开须重算不得只改字。

## 2.8.40 — 2026-11-05（Asia/Shanghai）

来源：用户 t109u/t110u（干画图4）— 带把手图中梯形孔朝向

- **盖顶双把手相向**：长孔距（宽排85）朝里（朝盖中心）；窄排朝外。
- **端侧把手**：长孔距（宽排85）靠下；窄排靠上（纠正规则16旧「窄下宽上」）。
- 草图归档 `assets/user-sketches/t109u-handle-wide-pitch-inward.png`。
- 同步：`SKILL.md` 规则2/16、`references/handle85.md`。本条只改朝向默认，不擅自加把手。

## 2.8.36 — 2026-11-05（Asia/Shanghai）

## 2.8.38 — 2026-11-05
- **规则28 补记 t105u/t106u/t107u（S-201-2-20261028-001-v15）**：立面裙↔低盖交界仅干净 45° 斜切，竖直深=skirt，无单独三角补块（收窄 t104u）；用户「不要把手」→ HAS_HANDLE=false。


来源：用户 t124u — 「#005 pdf布局太乱…不要求一定要4页…保证尺寸，图不要重叠清晰明了，布局合理」。

变更
- 规则6：可读优先；拥挤/重叠/裁切时拆页加页，不硬卡 4 页；零件页左图右注（t110u）。
- 实单 `S-201-1-20261104-005-v2`：U 展开 ~1094 高不再与端板挤同页；6 页（总装/U/END_L/END_R/LID/检查）；golden PASS；overlap remaining=0；几何同 v1。
- 11-04#005 升版 PDF 重排（几何不变）。

## 2.8.35 — 2026-11-05（Asia/Shanghai）

来源：用户 t103u — S-201-2 阶梯盖展开「这里收口太不合理了」：低↔立面交界呈台阶/锯齿/Z 形缺口，非干净 45° 刀口。

新增/修订
- 用户硬性规则28 增补：**收口外形须干净 45°，禁止台阶/Z 锯齿**；flat/CUT 两侧对称、与高段 V-notch 同形可读；禁止 reverse+BA 袋叠成 Z；折后 dist≈CORNER_GAP 或可焊小缝；禁约 90° 张口；CORNER_GAP=0 勿回归。
- 实现提示：低段交界用共享 45° 刀口（斜边落 BA 让位两端）；勿用 reverse 翻斜率叠 BA 矩形袋。

## 2.8.34 — 2026-11-05（Asia/Shanghai）

来源：用户 t122u — 「并且保证pdf与dxf图一定要一致」。

变更
- 规则29 增补：折弯 PDF 孔位标注必须与本版 DXF_CUT/STEP/report 同源；容差 ≤0.05 mm；不一致不得交付。
- 与 t121u #007 沿短边改孔一并执行：出图前门禁核对 PDF↔DXF。

## 2.8.33 — 2026-11-05（Asia/Shanghai）

来源：用户 t121u — #007 PDF 首页孔沿长边排，纠正为沿短边；澄清规则29。

变更
- 规则29 硬写：**孔心连线平行于短边**（同 X、变 Y）；禁止同 Y 变 X 冒充沿短边。
- 靠右边距：距右短边 15；右下起排时首孔距下长边 15。
- #007 须升版：孔心 (378.7,21.3)/(378.7,51.3)（原错误 (378.7,21.3)/(348.7,21.3)）。

## 2.8.32 — 2026-11-05（Asia/Shanghai）

来源：用户 t101u/t102u — 阶梯盖立面↔低段裙 45° 斜切收口方向反了（B7 上折后开口约 90°）；要求纠正 + t=2/Ri=2/ro=4 展开与贴合复核。

新增/修订
- 用户硬性规则28 增补：**立面↔低段（及高段↔立面）裙角 45° 斜切收口方向**须按弯向核对——B4 下折外凸角用 V-notch；B7 上折收口须 reverse miter（翻斜率），使折后刀口贴合而非约 90° 张口；flat 目视/坐标核对斜率相对 v-notch 是否已翻转；knife-edge dist≈CORNER_GAP。
- 出确认稿前 rule28 清单含斜切方向；K/BA 无试折仍标候选+HOLD。

## 2.8.31 — 2026-11-05（Asia/Shanghai）

来源：用户 t120u — 「没有明确说明线孔的位置的时候默认在沿着盖短边布局多个线孔，并且靠右边」。

新增
- 用户硬性规则29：线孔未给面/坐标 → 默认盖顶、沿盖短边一排、靠右；孔边距短边/右边缺省 15 mm；孔距缺省 25（本单覆盖）。
- 规则16「未给坐标→面宽居中」改为仅适用于品字口/体壁孔组；线孔改走规则29。
- `references/holes-and-hardware.md`、`references/field-experience.md` 同步。

## 2.8.30 — 2026-11-05（Asia/Shanghai）

来源：用户 t98u/t99u/t100u — 阶梯箱现场「高平面盖与盒体盖不上，差约1板厚」；要求重核折弯误差、盖内与盒口直接贴合、螺丝孔对齐，并补技能检查项。

新增
- 用户硬性规则28：盖内↔盒口贴合 + 折弯误差（K/BA）核对 + 盖-体螺孔同轴；禁止只消布尔干涉；优先端板/U 让位、保留底 Ro；确认稿诚实分列几何贴合 vs 未试折。
- 出图前盖配门禁指针（规则28）写入规则9 checklist 旁门禁条。

## 2.8.29 — 2026-11-03（Asia/Shanghai）

来源：用户 t21u（经 UserAgent / 干画图站规同步）——确认稿交付必须同步 Mac 客户图纸按日目录。

新增
- 用户硬性规则27：`/Users/harryma/Documents/Liweitas/20267/liu_0805/骊臻/客户图纸/YYYYMMDD/`；`{VER}_CONFIRM_DRAFT.zip` 或投产 `{VER}_OPEN_ME.zip`(+sha256)、可选 `*_BEND_PDF_A3_CN.pdf`；只丢 Downloads 不算完成。
- `references/message-delivery.md` 增补同条。

## 2.8.28 (2026-11-03)

- 用户 **t110u**：展开页「尺寸线伸进页眉 / 图下文字挤叠 / 右侧空白」——订单引擎排版：`fit_flat_left` 左栏大图占满可用高度（TITLE_BAND 在红条下）；折弯表/说明/HOLD/轴测移**右栏**；`vax` 顶夹在 PH-42 下；几何不变仅 PDF。实单 `010-v20` / `005-v10`（`003` 未改）。golden 四文件未动；overlap remaining=0。

- 用户 **t106u**：补件展开「没有双向折弯尺寸」——根因：t105u 的 `patchflatdims`/`shellflatdims` 对规则9(b) 只用折旁「左xx/右xx」文字，**未画**折线到两侧对边的真实尺寸线；用户附图（仅总宽+短边）不合格。
  - 规则9/18 旁增加**稳定出 PDF 可执行 checklist**（链式 + 折→两侧尺寸线 + 总外形 + 折弯表；golden + overlap=0 + **目视补件/SIDE**；诚实写明无 OCR 自动门禁）。
  - 引擎：`patchflatdims`/`shellflatdims`/`lidflatdims` 与 `dxf_post.rule9` 为每折画「距A」「距B」两条尺寸线；禁止文字冒充 9b。
  - 实单 bump：`003-v11` / `010-v18` / `005-v8`（几何不变，`production_release=false`）。

## 2.8.27 (2026-11-02)

- 用户 t61u：折弯 PDF **金样只读公共库** + **哈希门禁** + **尺寸 bbox 避让原型**。
  - `assets/bend-pdf-golden-004-v2/` 四文件为权威；订单 addendum 仅允许 symlink/cp 后 sha256 一致，否则 BLOCK。
  - 新 `scripts/check_bend_pdf_golden.py`；`GOLDEN_SCRIPTS.sha256`；`engine_u_endplates.py`（`make_bend_pdf WORK STAGE`）。
  - `pdf_common.dim`/`dimA`（及 u_endplates dimh/dimv）lane 外推/换侧；`logs/bend_pdf_overlap.json`；`remaining=0` 布局 PASS。
  - 更新 `references/bend-pdf-golden.md`、规则12/18 指针、新增规则26；验证单 `S-201-1-20261029-009-v3`（换货参 379×270×240，把手 90/289）。

## 2.8.26 (2026-11-01)

- 用户 t27u/t28u：强化规则22 + 新增规则25——`hole_to_lid_skirt` ERROR 须**主动下移孔心**使整组净空≥10 mm；**禁止**开盖裙缺口（除非本单明确）；**禁止**带着该 ERROR 交付确认稿或投产包。同步 hole-to-lid-skirt / rules-checklist / field-experience；样例 004-v1→v2。

## 2.8.25 (2026-11-01)

- 用户 t50u：新增硬性规则24——外形 H 默认=含盖体外总高，**不含**盖顶把手凸出；含把手总高仅另注或本单明确。同步 field-experience / v2.8.2-delivery-rules / parameters。

## 2.8.24 (2026-11-01)

- 用户 t48u：废止规则20 作为矩形箱默认（一体折端壁主要针对异形件）。规则7 / v2.8.2§1 / structure-selection / field-experience 恢复默认 `u_external_ends`（U+两外封端板+盖，`pipelines/u_endplates/`）。一体折仅异形或本单明确。

## 2.8.23 (2026-11-01)

- 用户 t86u：新增硬性规则23——「不开孔」=不开线孔/功能孔，盖-体 M4 固定孔默认仍开；「不要把手」仍无把手。规则4交叉引用。纠正 006-v1 误判。

## 2.8.22 — 2026-10-31（Asia/Shanghai；来源：用户 t68u/t70u）

1. **到头裙 + 盒体闭合耳**：当用户要消除经典短裙矩形缺角、折后收口闭合角部缺角时 — 盖 `short_skirt_retreat=0` + 外凸角双侧 45° miter；盒体盘角壁伸入 t×t 角柱后 45° miter（TAB_W=t），弯保持安全端点；formed tip 闭合；弯根残余缝 ~Ri 标 HOLD。
2. 同步：`references/field-experience.md` §2/§5；`SKILL.md` 规则22；frontmatter/`VERSION`→2.8.22。
3. 本版例：订单 010 确认稿 v6（S-201-1-20261029-010-v6）。

## 2.8.21 — 2026-10-31（Asia/Shanghai；来源：用户 t67u）

备份：`/workspace/skills/_backup/step-sheetmetal-delivery.before_t67u_rule21_03_default_20261031`。

用户 t67u：「盖改回斜角03；盒体向上的也是斜角03；盖与盒体间隙0.5mm——都是 skills 默认方案」。

1. **规则21 纠正**：T/台阶盖与矩形盖缺省恢复 **斜角03** + g=0.5；**连续等高校裙**改为显式 opt-in（「独立盖角取消 / 要连续裙」）。保留连续裙实现说明，不删。
2. 同步：`references/lid-defaults03.md` 横幅、`field-experience.md` §2、v2.8.2§8 03 缺省说明；规则20 一体折端壁不变。
3. 实单：`box-470x260x170-010` 确认稿升 **v5**（自 v3/v4 连续裙回退 work_v2 / 010-v2 斜角03）。

## 2.8.20 — 2026-10-31（Asia/Shanghai；来源：用户 t99u / 审计 t98u）

备份：`/workspace/skills/_backup/step-sheetmetal-delivery.before_t99u_hole_to_lid_skirt_20261031`。

审计：`S-201-1.2-20261029-003-v1` 端板顶排 Ø30/Ø20/电表口侵入盖裙下沿，确认稿未反馈「盖裙遮挡」（仅有 hole_to_outline 激光边距 WARN）。

1. **用户硬性规则22**：体面孔（线孔/IEC/电表等，不含箱体 M4 / 盖裙螺钉孔）合盖后孔顶→盖裙自由下沿（Z=H−skirt）净空；<0 → ERROR（msg 必含「盖裙遮挡」）；0≤净空<10 → WARN（规则16）。
2. `scripts/conflict_checks.py`：新增 `hole_to_lid_skirt` / `collect_lid_skirt_features` / `lid_skirt_force_lines_cn`；`run()` 在有 H+skirt（或 end_features）时执行。
3. 强制反馈：`confirm_draft.py` 写入待确认+冲突与风险；`pipelines/u_endplates/run.py` 传 H/skirt/end_features 并写 `*_LID_SKIRT_FINDINGS.txt` / 追加 README；`pipelines/u_endplates/pdf.py` 第1/4页红字注入。
4. 文档：`references/hole-to-lid-skirt.md`、`holes-and-hardware.md`、`rules-checklist-cn.md`、`v2.8.2-delivery-rules.md`；`tests/test_user_rules_t99u.py`；frontmatter/`VERSION`→2.8.20。

## 2.8.19 — 2026-10-31（Asia/Shanghai）

来源：用户 t64u「独立盖角取消，重新规划折弯方案」。

- 新增用户硬性规则21：T/台阶盖默认连续等高校裙；禁止默认外凸独立03短裙端片与内凹让位缺口；矩形盖仅在用户取消独立盖角时改连续裙。
- 更新 `references/field-experience.md` §2/§5、`references/lid-defaults03.md` 适用范围说明；v2.8.2§8 03 缺省对 T/台阶盖让位于规则21。
- 实单：010 自 v3 起对齐 003-v4 continuous skirt。

## 2.8.18 — 2026-10-31（Asia/Shanghai）

来源：用户 t60u「盒体折弯端板也不用单独切割，放在一起折」。备份：`/workspace/skills/_backup/step-sheetmetal-delivery.before_t60u_integral_ends_20261031`。

- 新增硬性规则20：盒体两端壁（及可折的台阶立面）默认与相邻底板/侧壁同坯一体折弯；禁止默认出零折单独下料外封端板。
- 规则7 / v2.8.2 结构条 / `references/structure-selection.md` / `field-experience.md` 同步：外封平板端板仅用户明确要求或源 STEP 分件时用；「两边加把手」装在一体折端壁。
- 010 确认稿随本规则升 v2 重建（见订单 box-470x260x170-010）。

## 2.8.17 — 2026-10-31

- 用户硬性规则19（t43u）：锁定 S-201-0.8-20261030-004-v2 折弯 PDF 为金样；`assets/bend-pdf-golden-004-v2/` 冻结脚本；新单必须 cp 金样以保证后续一致性。规则12 模板指针改指金样。

## 2.8.16 — 2026-10-31

- 用户硬性规则18（t41u）：折弯 PDF 必含三视+斜视；双向折弯尺寸；关键参数（板厚/尺寸/编号/日期）醒目供 ERP；去冗余保简洁。在 2.8.15 之上增量。

## 2.8.15 — 2026-10-31（Asia/Shanghai；来源：用户 t95u/t96u/t97u）

备份：`/workspace/skills/_backup/step-sheetmetal-delivery.before_t97u_step_sot_20261031`。

订单含源 STEP 时，几何以 STEP 为准；出图前先做差异表，禁止静默用文字默认覆盖 STEP。

1. **用户硬性规则17**：STEP 为孔型/孔径/CSK/品字·IEC/螺钉孔/坐标/板厚/外廓真源；文字只补料号·qty·公差·工艺·把手标志等；确认稿偏离前须 EVIDENCE 差异表并问冲突；批准偏差写 README/PDF/CHANGELOG；海军蓝 PDF 页图与重建零件同结构同内容，重建对齐 STEP；与规则4冲突时 STEP 优先（除非用户明确选工厂 M4 并书面记偏差）。
2. 规则4 交叉引用一句：「有源 STEP 时孔型/孔径以 STEP 为准，见规则17」。
3. 新增 `references/step-source-of-truth.md`（差异表清单与流程）；`rules-checklist-cn.md` 加规则17 指针；frontmatter/`VERSION`→2.8.15。

## 2.8.14 — 2026-10-31（Asia/Shanghai；来源：用户 t55u）

备份：`/workspace/skills/_backup/step-sheetmetal-delivery.before_t55u_pinzi_horizontal_20261031`。

用户原话：「品字口也横向安装」。

1. **规则16补充**：品字口本体默认横向安装（开口 28 沿面宽、20 沿高；螺钉孔 pitch40 同高沿面宽）；未要求时不竖装。
2. 同步 `holes-and-hardware.md`、`field-experience.md`、`schurter-6100-3-v1.json`；frontmatter/`VERSION`→2.8.14。
3. 实单回填：`S-201-1.2-20261030-007-v2` → `…-v3`（品字由竖装改横装）。

## 2.8.13 — 2026-10-31（Asia/Shanghai；来源：用户 t53u/t54u）

备份：`/workspace/skills/_backup/step-sheetmetal-delivery.before_t53u_handle_endplates_20261031`。

用户原话：「两边加把手，一般是指端板位置增加把手，把手方向朝上…」「不论是品字口，圆线孔，都是横向排列」「不明确说明位置就是居中…靠盖裙10mm默认…不要与把手干扰」「有干扰…左右平移…距离边也不要小于10mm」；并要求更新 skills。

1. **用户硬性规则16**：两边把手→两端板握把朝上；品字/圆线孔横向；未标位置→居中+靠裙10mm；干涉整组平移且距边≥10mm。
2. 同步 `references/holes-and-hardware.md`、`handle85.md`、`field-experience.md`；frontmatter/`VERSION`→2.8.13。
3. 实单回填：`S-201-1.2-20261030-007-v1` → `…-v2`（端板双把手 + 横向孔组）。

## 2.8.12 — 2026-10-30（Asia/Shanghai）

- 用户硬性规则15（t75u）：折弯 PDF 每页海军蓝页眉显眼写出图时间 `出图 YYYY-MM-DD HH:MM Asia/Shanghai`。

# CHANGELOG

## 2.8.11 — 2026-10-28（Asia/Shanghai；来源：用户 t43u/t44u / pt44u）

备份：`/workspace/skills/_backup/step-sheetmetal-delivery.before_t43u_factory_v_bump_20261028`（整目录）。

用户诉求：解压后文件夹/文件仍是 `…-v1`，要把尾缀改成真实版本 `v2/v3/…`；并更新 skills。

1. **用户硬性规则14 — 新确认稿包默认升工厂 vN**（取代规则11 中「PDF 版式/README/打包等非几何微调不升工厂 v」）：凡用户将下载/解压的新 outbound CONFIRM_DRAFT（含 PDF 版式/布局、打包/zip 命名、README，以及几何/孔/结构变更）一律 bump 工厂尾缀 vN；完整更名（zip 名、单顶层 `{NEW_VER}/`、内文件前缀）；旧厂版 live zip(+sha256)→`SUPERSEDED/`；CHANGELOG 写升版原因；`production_release=false` 除非用户另说。同单修订只升尾缀，前五段不变；几何未变用 `release_package.py rename`。revN 仍可作当前工厂 VER 下内部快照，但**对外区分以工厂 vN 为准**。
2. 文档：`SKILL.md` 规则11 标注废止句 + 新规则14；`references/confirm-draft-versioning.md` 重写 bump 默认；`factory-naming.md` / `delivery-contract.md` / `field-experience.md` §7；`scripts/snapshot_confirm_rev.py` 注释标明工厂-v bump 优先于 revN 作对外路径；frontmatter/`VERSION`→2.8.11。
3. 实单回填：`box-280x210x70` `S-201-1-20261026-003-v1` → `…-v2`（用户要求版本可见性：此前版式+zip 迭代仍标 v1）；几何不变；production_release=false。

## 2.8.10 — 2026-10-28（Asia/Shanghai；来源：用户 t40u / pt40u）

备份：`/workspace/skills/_backup/step-sheetmetal-delivery.before_t40u_zip_unique_20261028`（整目录）。

用户原话：「当我下载下来，解压出来以后还是跟其他已经解压的一样的目录，这个就容易混」。

1. **用户硬性规则13 — ZIP 解压不混单**：对外 zip 文件名必须以工厂码 VER 开头（`{VER}_CONFIRM_DRAFT.zip` / `{VER}_CONFIRM_DRAFT_revN.zip` / `{VER}_OPEN_ME.zip`）；**禁止**裸名 `CONFIRM_DRAFT.zip` / `CONFIRM_DRAFT_revN.zip` / `CONFIRM_DRAFT_current.zip`。zip 内部有且仅有一个顶层目录 = VER；CHANGELOG 放进该目录内；聊天附件必须指向 VER 前缀路径。
2. 文档：`SKILL.md` 规则13 + v2.8.2 命名/ZIP 条；`references/confirm-draft-versioning.md`、`references/delivery-contract.md`、`references/field-experience.md` §7；frontmatter/`VERSION`→2.8.10。
3. 实单回填：`S-201-1-20261026-003-v1`（box-280x210x70）裸 `CONFIRM_DRAFT_rev1/current.zip` 移入 `_before_zip_unique_name/`；新建 VER 前缀 live + OPEN_ME + rev2（单顶层 VER/）；geometry/PDF 未改；production_release=false。

## 2.8.9 — 2026-10-28（Asia/Shanghai；来源：用户 t37u/t38u/t39u）

备份：`/workspace/skills/_backup/step-sheetmetal-delivery.before_t39u_pdf_style_20261028`（整目录）。

用户原话：「其他图的配色跟你的也不一样」「这个配置一致是之前pdf都在执行的 为什么到你这就不行了」「这个加到最新的skills中」。

1. **确认稿折弯 PDF 统一管线**：必须走订单 `addendum-tools/make_bend_pdf.py` + `pdf_common.py`（模板 `box-550x195x150` / lessons `sheetmetal_lessons_干画图3.md` §3）；**禁止**灰框 `tools/pdf.py` / `*_BEND_DRAWING_A3.pdf` 顶替交付。
2. **固定视觉**：海军蓝页眉（≈0.10,0.22,0.45）+ 红条材料栏（≈0.82,0.1,0.1）+ 蓝尺寸 + 红警告 + 轴测绿盖/褐箱；全中文 A3 横 ≤4 页（规则6）；字高≥≈3.3 mm；CJK 子集按本单 PDF 源现建（`scripts/build_cjk_subset_ttf.py`）。
3. 文档：`SKILL.md` 用户硬性规则12 + frontmatter/`VERSION`→2.8.9；v2.8.2 折弯 PDF 条交叉引用规则12；`references/field-experience.md` §6。
4. 新单从已验证订单 `cp -r …/addendum-tools`；技能 `pipelines/*/pdf.py` / 长页 THREE_VIEWS 仅内部证据，不作确认稿外观。

实单回填进行中：`S-201-1-20261026-003-v1`（box-280x210x70）由灰框改回 addendum 配色（同厂版 rev，不升 v）。


## 2.8.8 — 2026-10-28（Asia/Shanghai；来源：用户 t69u）

备份：`/workspace/skills/_backup/step-sheetmetal-delivery.before_t69u_versioning_20261028`（整目录）。

确认稿版本默认规则（工厂 vN vs 同厂版 revN）：

1. **工厂 vN**：仅结构/外形尺寸/孔变化时升版；保留前五段 `S-材质-板厚-日期-编号`；旧厂版完整 ZIP+.sha256 移入 `SUPERSEDED/`。PDF 版式/README/打包等非几何微调**不**升工厂 v。
2. **同厂版微调**：live 始终 `{VER}_CONFIRM_DRAFT.zip`；另拷 `{VER}_CONFIRM_DRAFT_revN.zip`+.sha256（N 递增，无则从 0）；`{VER}_CHANGELOG.txt` 追加 `YYYY-MM-DD HH:MM Asia/Shanghai | revN | 简述 | sha256=<hex>`。
3. **对外**：只认 live zip + 其 sha256；旧聊天附件不作当前包。revN+CHANGELOG 建立后停止 `_before_*` 临时备份名（既有 before_* 可回填进 revN）。
4. 新参考 `references/confirm-draft-versioning.md`；`SKILL.md` 用户硬性规则11 + frontmatter/`VERSION`→2.8.8；交叉引用 `factory-naming.md` / `delivery-contract.md` / `v2.8.2-delivery-rules.md`；`QUICKSTART.md` 提及助手脚本。
5. 新脚本 `scripts/snapshot_confirm_rev.py`（stdlib：pathlib/hashlib/shutil/datetime ZoneInfo Asia/Shanghai）：同厂版快照 next revN，不升工厂 v。

实单回填：`S-201-1-20261028-001-v1`（box-550x260-stepped-620）rev0–rev3 自 before_t64u / before_t65u_pdf / before_t67u_pdf_home / live；工厂码仍 v1；production_release=false。


## 2.8.7 — 2026-10-28（Asia/Shanghai；来源：用户 t62u）

备份：`/workspace/skills/_backup/step-sheetmetal-delivery.before_t62u_1box_20261028`（整目录）。

用户原话：「因为现场师傅需要调整套料情况，你给一整个到dxf文件，不要分开，一个盒子，一个dxf的文件」。

1. `scripts/release_dxf.py`：`post_release` / `write_nests` 默认 `nest_mode='kit'` —— NEST 只放 **1 套**完整盒体零件（各件 qty 强制 1），写出单个 `{ver}_NEST_{W}x{H}_1BOX.dxf`；订单套数写在 README/BOM，不复制进 NEST、不拆 `SHEETnn`。仍画 2440×1220 SHEET 框、CUT 层、CONTINUOUS、边距10、件距10；无折弯线/无文字。一盒装不下单板时 `NEST_KIT_NEEDS_N_SHEETS`。保留 `nest_mode='sheets'`（旧 SHEETnn）仅作内部/证据。`check --role nest` 仍要求一个 SHEET 框且零件在板内。
2. 文档：`SKILL.md` 用户硬性规则10、v2.8.2 DXF 条；`references/v2.8.2-delivery-rules.md`、`references/delivery-contract.md`、`references/factory-naming.md`；`VERSION`→2.8.7。
3. 测试：`tests/test_user_rules_t62u.py`（1BOX 默认、qty 不扩板、sheets 可选）。
4. 实单 S-201-1-20261027-003-v1（box-600x440x200，qty=2）NEST 从 SHEET01/02 改为 `_1BOX.dxf`（旧板备份 `NEST_before_t62u_sheets/`）；单件 CUT/BEND/STEP 未改；production_release=false。


## 2.8.6 — 2026-10-27 23:35（Asia/Shanghai；来源：用户 t45u/t46u）

备份：`/workspace/skills/_backup/step-sheetmetal-delivery.before_t46u_bothsidedims_20261027`（整目录）。

- SKILL.md 用户硬性规则新增第 9 条：展开图双向标注、免计算（逐段链式尺寸 + 每条折弯到两侧对边距离 + 总尺寸 + 折弯表“距A边/距B边/段长”）。仅文档规则，尚无自动门禁脚本，需逐页目视核对。

## 2.8.5 — 2026-10-26 21:45（Asia/Shanghai；来源：用户 t35u “从现在开始线孔都是至少两个”）

备份：`/workspace/skills/_backup/step-sheetmetal-delivery.before_t35u_cablehole2_20261026`（整目录）、`/workspace/skills/_backup/SKILL.md.before_t35u_cablehole2_20261026`。
1. 新用户硬性规则8（`SKILL.md`）：订单有线孔时每箱 ≥2；只画1个 → 补第2个，同径、同高、同面，缺省孔心距25（用户008单孔距）朝面中心，核孔边→外形/折弯/盖裙/固定孔间距与筋宽（孔距−孔径），补加位置列 HOLD；无线孔的订单不添加。v2.8.2 规则5“不擅自加线孔”加注此例外。
2. `scripts/conflict_checks.py`：新增 `CABLE_HOLE_MIN=2`、`CABLE_HOLE_PITCH_MM=25.0`、`suggest_second_cable_hole()`、`cable_hole_count()`（id `cable_hole_min_count`）；`run()` 仅在 params 含 `cable_holes` 时运行（向后兼容，旧 params 结果不变）。
3. 文档：`references/holes-and-hardware.md`、`references/v2.8.2-delivery-rules.md`（§6 第8项）。
4. 测试：新增 `tests/test_user_rules_t35u.py`。
5. 实单 S-201-1-20261025-006-v1（box-270x150x210）按本规则补第2个Ø16线孔（END_L Y85 Z185，孔距25）。

## 2.8.4 — 2026-10-26 15:37（Asia/Shanghai；来源：用户 t52u，方案A + 恢复M4薄板警告）

备份：`/workspace/skills/_backup/step-sheetmetal-delivery.before_t52u_m4`、`.next.before_t52u_m4`、`step-sheetmetal-delivery-next.before_t52u_m4.zip`。

1. 恢复 t≤1.2 直接攻M4 薄板警告（t16u 版本曾删去“压铆/拉铆”提示，用户 t52u 要求恢复）：`scripts/conflict_checks.py` 新增 `M4_THIN_LIMIT_MM=1.2`、`M4_ALTERNATIVES_CN`、`m4_thin_sheet_warning_cn()`；`m4_tap()` 对 t≤1.2 给 WARN，文案“{t} mm {材料} 板直接攻M4（底孔Ø3.3）仅约1扣有效螺纹，强度偏低、易滑牙，不建议反复拆装；替代方案 压铆螺母 / 拉铆螺母 / 点焊螺母 列为待确认”，缺省仍按M4直接攻丝出图（替代方案只列待确认，不自动替换）。
2. 模板必须输出该警告：`pipelines/u_endplates/pdf.py`（第1页参数框、第4页M4孔表、待确认第5项）、`pipelines/u_endplates/docs.py`（M4TXT：核验清单 WARN 行、README 待确认/风险）、`pipelines/u_l_t7u/make_bend_pdf.py`（TT≤1.2 红字3行）、`pipelines/u_l_t7u/make_readme.py`（草稿第3项）。
3. 规则文档：`SKILL.md` 规则4/6、`references/v2.8.2-delivery-rules.md`、`references/holes-and-hardware.md`、`references/field-experience.md`。
4. 测试：改 `tests/test_user_rules_t16u.py`（`test_m4_tapping_stays_default_alternatives_only_pending` 取代“不得提压铆”断言）；新增 `tests/test_user_rules_t52u.py`（7 项）。
5. 实单 S-201-1-20261021-001-v1：用户确认方案A（切除小条展开，native03 FAIL 为已知原因，标 WARN·用户已确认，不隐藏）——实单工具层面处理，技能 native03 文案保持通用。
复核管线：`/workspace/skilltest/u_endplates_v284_154608`（门禁 11 PASS / 0 FAIL / 8 WARN；README/核验清单/PDF 均含“易滑牙”）。

## 2.8.3 — 2026-10-26（Asia/Shanghai；来源：用户 pt46u “不要有缝”）

备份：`/workspace/skills/_backup/step-sheetmetal-delivery.before_t46u_v283`、`.next.before_t46u_v283`、`step-sheetmetal-delivery-next.before_t46u_v283.zip`、`_backup/u_endplates_before_t46u_port`。

1. “斜角03” = 技能自带 03 盖角方案（不再当未知工艺“待提供”）：有盖箱体缺省用 03，每单按 t/Ri/裙高重算 P1/P2/P3；corner03.py 与 native03_check.py 必跑。缝 = 用户给值（标 user），未给则候选 0.2（标 candidate，须用户确认）。改：`SKILL.md`（规则 1/5/8）、`references/v2.8.2-delivery-rules.md`、`assets/profiles/named-processes-v1.json`（斜角03 已知，别名→03）、`scripts/confirm_draft.py`、`tests/test_v282_release.py`（`test_xiejiao03_known_unknown_still_pending`）。
2. gap=0 发现：熔合盖角 1×1×13.2 共享柱被 native 展开同时分给两片折边 → +52.8 mm²（每角 13.2 mm³ 干涉）；裁后展开符合03但 native03 FAIL（52.8 mm² vs 1e-5），未裁 native 通过。须如实报告并让用户在 A/B/C 中选，不得静默改缝。
3. `pipelines/u_endplates` 移植 t46u 实单工具：端板改外封平板全盖（`end_flange` 废弃，seam_gap/end_inset 0、end_top_flush）；盖角 03（CORNER_SCHEME 断言）；新增 `corner_probe03.py`、`corner_slice03.py`、`preview.py`；`project03.py`；run.py 必跑 corner03/native03（`SM_ACCEPT_NATIVE03_FAIL=1` 才放行已知 gap0 FAIL）、BODY.step 不入 STEP、PDF 改 ASCII 名、docs 以输出目录为 cwd、门禁 `--pdf-max-pages 4`；post.py 端板/03角文案；示例 brief 同步；`pipelines/README.md` B 节重写。
4. 遵守 t16u：BEND 层 CONTINUOUS、M4 攻丝、Φ6.6=M6 过孔。
测试：sm-venv `unittest discover -s tests`。复核管线：`/workspace/skilltest/u_endplates_v283_125328`（门禁 0 FAIL；DXF 几何与实单一致）。

## 2026-10-26 用户硬性规则（来源：用户 t16u；Asia/Shanghai）

备份：`/workspace/skills/_backup/step-sheetmetal-delivery.before_userrules_20261026`（.next 与 zip 同目录 `*.before_userrules_20261026*`）。

1. U+L：L盖U；U+两端板：端板盖U；不留缝隙、不退让0.2mm。`assets/process/experience-defaults-v2.json` external_end_contour_inset_mm 0.2→0；`pipelines/u_l_t7u` L 外露边退让 S 与 t7u 长裙退让 SL 改为 cfg 键 `l_cover_setback_mm` / `lid_long_skirt_setback_mm`，缺省 0（原硬编码 0.2）；PDF/PNG 文案随数值变化；`assets/examples/common-460-review.job.json` end_inset 0.2→0；`conflict_checks.joint_flush` 对无用户来源的非0退让/缝报 ERROR。
2. 把手默认保持 handle-85-62-30-v1（85/62/30，Φ6.6 M6 过孔）；`handle-lid-top-riveted-v1` 终孔径由“待确认”改为 Φ6.6 M6 过孔。
3. 所有 DXF 无虚线：`release_dxf.check_dxf` 对 cut/bend/nest 全部角色检查实体与图层表线型，非 CONTINUOUS 即 FAIL；`write_bend`/`post_release` 缺省 CONTINUOUS 并拒绝其它线型（原缺省 DASHED）；新增 `release_dxf.py nodash`。
4. 盖-体固定默认 M4 攻丝（体Φ3.3、盖Φ4.5）；`conflict_checks.m4_tap` 不再建议压铆/翻孔/焊接螺母；u_endplates PDF/README 文案同步。
5. 线孔/品字口等接口螺钉孔攻丝并在 PDF 孔表说明：`schurter-6100-3-v1` 2×攻M3（底孔Φ2.5）、`anderson-50a-v1` 4×攻M4（底孔Φ3.3）（由原过孔推定，待规格书确认）；新增 `conflict_checks.connector_screw_taps`。
6. PDF 页数尽量压缩（参考现 4 页版：总装1页+每零件1页），尺寸必须齐全、A3 字高≥约3.3mm；`release_package.py package --pdf-max-pages N`，小字 WARN。
7. 结构选型对新箱体强制：max(L,W)≥H → U+两外封端板+盖，否则 U围+L；取代 v2.8.2“缺省一律 u_l_t7u”。
测试：新增 `tests/test_user_rules_t16u.py`；`test_general_process` / `test_common_profiles` 的 end_inset 期望 0.2→0。

## 2.8.2 — 2026-10-26（Asia/Shanghai）

来源：原 2.8.1+field-exp-20261025（备份 `/workspace/skills/step-sheetmetal-delivery.bak-20261026`）+ 本机实单 + 干画图3 经验
`/workspace/shared/sheetmetal_lessons_干画图3.md`。审计 `/workspace/skills/SKILL_AUDIT_20261026.md`，差异 `/workspace/skills/SKILL_DIFF_20261026.md`。

新增
- `scripts/release_dxf.py`：CUT/BEND/NEST 角色门禁（连续、闭合、无重复/重叠、1:1 mm、NEST 只 CUT+SHEET 且有 2440×1220 板框）+ 发布写出器（write_cut / write_bend / write_nests 边距10件距10 / post_release）。
- `scripts/release_package.py`：发布门禁（发布名原样、每文件前缀、ASCII 名、STEP/DXF 内发布名、PDF A3/每页发布名/中文/页数/字体嵌入、DXF 角色、重名扫描）+ ASCII 单 zip（显式映射、testzip、逐条字节比对、.sha256）+ geomhash + rename（几何哈希不变）。扁平 zip 布局按 `<VER>_CUT_/_BEND_/_NEST_` 识别 DXF 角色。
- `scripts/conflict_checks.py`：Ri>g→q、t≤1.0 攻 M4、深 U 折弯避让、孔边→折弯切线、孔边→展开外形 ≥4、未要求特征。
- `scripts/confirm_draft.py`：确认稿草稿（包含/未添加/假设/待确认/冲突/状态，未知工艺名、孔边/孔心两种读数），只写文件。
- `scripts/build_cjk_subset_ttf.py`：Noto CJK SC 子集 → glyf TTF（干画图3 §3.6 方法），reportlab 可嵌入。
- `assets/profiles/`：anderson-50a-v1、schurter-6100-3-v1、handle-lid-top-riveted-v1、named-processes-v1。
- `assets/examples/S-201-1-20261021-001-v1.release.json`：u_endplates brief 实例。
- `pipelines/u_l_t7u/`（默认结构，取自干画图3 007 工具）与 `pipelines/u_endplates/`（取自 400×220×150 工具）+ `pipelines/README.md`。
- `references/v2.8.2-delivery-rules.md`（规范 + 干画图3 经验合并 + 11 项核验 + 踩坑）、`references/history-R07-R12.md`（从 SKILL.md 原样移出）。
- `tests/test_v282_release.py`。

修改（均带 `# v2.8.2` 注释）
- `scripts/general_process.py`：roof_ports 默认 none（不再默认开 Ø12 顶孔）。
- `SKILL.md`：版本 2.8.2；顶部 v2.8.2 硬规则；R07–R12 历史移到 references。`VERSION`、`QUICKSTART.md`、`references/field-experience.md`（§2 结构/盖角变体、§3 Anderson/Schurter/把手模板、§7 PDF 必须在 zip 内）、`references/checks-and-release.md`。
- u_l_t7u 相对 007 原件：订单路径改 `SM_ORDER`；开孔只从 `release_config.json.features` 读；`corner_probe.py` H 取盖顶 ZMax（原默认133只对003有效，007 高175时会全部判开口）；`make_bend_pdf.py` 嵌入字体；`release.py` STEP头/DXF写发布名、brief 不再写死文件名、几何哈希只算 DATA/ENTITIES；`make_readme.py` 为 007 文本模板，需 `SM_README_TEMPLATE=007`。
- u_endplates 相对 400×220 原件：JSON cfg、把手只在 brief 要求时、L/2 剖面、PDF/docs 模板守卫、ASCII 文件名、确认稿、门禁+单 zip。

- 5 个中文文件名改为 ASCII（内容不变，链接已改）：`assets/templates/customer-data-form-cn.{md,pdf}`、`assets/examples/synthetic-example-guide-cn.{md,pdf}`、`references/rules-checklist-cn.md`，使技能 zip 全 ASCII。
- `PACKAGE-SHA256.json` 按 2.8.2 重算（独立验收仍 PENDING）。

未改
- 原生 `delivery_contract` 套料（无板框）保留为证据；发布套料由 `release_dxf.write_nests` 写。
- 状态：作者自测，未独立验收、未安装到全局、未实物试折。production_release=false。

## 2026-11-03 t105u（确认稿执行器核对）
- 用户问「PDF中不同方向的折弯尺寸」：核对 **规则9**（展开 X/Y 双向链式+两侧距+总长宽+折弯表距A/距B/段长）与 **规则18**（双向折弯尺寸同规则9）。缺任一段=不合格。
- 已对 003-v10 / 010-v17 / 005-v7 升版：SIDE 独立页 `shellflatdims`；LID_PATCH/_R `patchflatdims`；几何不变；`check_bend_pdf_golden` PASS；overlap remaining=0。
