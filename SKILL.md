---
name: step-sheetmetal-delivery
description: 核验STEP与钣金要求；为两类矩形箱体生成分件/装配/爆炸STEP、真实展开激光DXF及三视折弯PDF，强制核验03盖角和完整交付；也用于既有项目审核及窄改，纯格式转换不适用。
metadata:
  version: "2.8.12"
---

# STEP 钣金审核与可复现出图

这是完整技能，包含实际CAD生成路径；FreeCAD、SheetMetal与PDF工具是公开外部依赖。安装、最小调用及依赖见[QUICKSTART](QUICKSTART.md)，支持范围和参数见[新箱体运行契约](references/box-generation.md)。参数、几何、首件与批量放行分别报告；不能把自测或HOLD候选称为生产放行。

## 用户硬性规则（2026-10-26，来源：用户 t16u；优先于本文件、references、pipelines 中任何冲突的默认值和历史写法）

用户原话：1. 如果是U+L形式，L盖U；如果U+两个端板，端板盖U；不留缝隙，不退让0.2mm。2. 默认把手是原skills中的默认尺寸，M6孔；如果已经是了就保持。3. 所有DXF中不能有虚线（影响切割）。4. 没有特殊要求时，盖与体的固定螺丝都是M4攻丝。5. 如果有线孔、品字口，需要攻丝，也要在PDF中说明。6. PDF页数要尽可能压缩，现在这几版就很好。

1. **拼接 0 缝 0 退让**：U+L 时 L 盖 U，L 外露边与 U 外面齐平（`pipelines/u_l_t7u` 的 `release_config.json` 键 `l_cover_setback_mm` 缺省 0）；U+两端板时端板盖 U，`end_inset`=0、`seam_gap`=0（`assets/process/experience-defaults-v2.json`）；t7u 盖角长裙外露端同样不退让（`lid_long_skirt_setback_mm` 缺省 0）。旧“L盖U退0.2 / 端板轮廓退让0.2 / 长裙退0.2”全部作废，只有用户本单明确给非0值才用，并在确认稿写来源。`conflict_checks.py` 的 `joint_flush` 对未注明用户来源的非0退让/缝报 ERROR。
2. **把手**：默认 `assets/profiles/handle-85-62-30-v1.json`（宽排85 / 窄排62 / 排距30，4×Φ6.6 = M6 过孔）；已是则保持，不换型；仍只在用户要求把手时开孔。
3. **DXF 无虚线**：CUT / BEND / NEST 所有图层与实体线型一律 CONTINUOUS；BEND DXF 折弯线用连续实线，放单独 BEND 图层（红色）并旁注 B号/方向/角度文字。`scripts/release_dxf.py check`（任何 role）发现 DASHED/HIDDEN/CENTER/DOT 等非连续线型（实体或图层表）即 FAIL；`write_bend`/`post_release` 拒绝非连续线型。
4. **盖-体固定**：无特殊要求时一律 M4 攻丝——箱体 Φ3.3 攻 M4、盖裙 Φ4.5 过孔；不默认改用拉铆螺母/压铆螺母/焊接螺母（用户本单明确要求才用）；但t≤1.2 时必须输出薄板攻丝警告（用户 t52u）：“1.0 mm 201 板直接攻M4（底孔Ø3.3）仅约1扣有效螺纹，强度偏低、易滑牙，不建议反复拆装；替代方案 压铆螺母 / 拉铆螺母 / 点焊螺母 列为待确认”，写进 PDF、README、校核清单（文本用 `conflict_checks.m4_thin_sheet_warning_cn()`）；替代件只列待确认，不擅自改用。
5. **接口螺钉孔攻丝**：线孔、品字口等带螺钉孔的接口，其螺钉孔默认攻丝（底孔：M3→Φ2.5、M4→Φ3.3、M5→Φ4.2、M6→Φ5.0），PDF 孔表必须写“攻M_ / 底孔Φ_”。模板：`schurter-6100-3-v1`（品字口，2×攻M3）、`anderson-50a-v1`（4×攻M4）。`conflict_checks.py` 的 `connector_screw_taps` 对未写攻丝规格的接口螺钉孔报 ERROR。
6. **PDF 压缩**：参考当前 4 页版式——总装 1 页 + 每个零件 1 页（三视/展开/折弯表/孔表同页），镜像同件合 1 页，不另加说明页；`release_package.py package --pdf-max-pages N` 卡上限。页数少但**尺寸必须齐全、A3 可读**：每个展开图上每个孔、每条折弯线、每个缺口都有坐标尺寸；每件有孔表和折弯表；文字高 ≥约3.3 mm（A3 原尺寸，≈9.4 pt；门禁对更小字只 WARN，仍须逐页目视）。缺尺寸 = 不合格（用户曾因缺尺寸投诉）。
8. **线孔至少2个（用户 t35u，2026-10-26，v2.8.5）**：用户原话“从现在开始线孔都是至少两个”。订单/草图有线孔时，每箱线孔 ≥2；图上只画1个 → 自动补第2个：**同直径、同高度（同Z/同v）、同一面**，缺省孔心距 **25 mm**（用户 008 单所用孔距），朝该面中心方向排（`conflict_checks.suggest_second_cable_hole()`）；必须核间距：孔边→板边/外形 ≥4、→折弯切线 ≥max(3,2t+Ri)、→盖裙下边（有盖时）、→固定孔（M4底孔/过孔），两孔间筋宽 = 孔距−孔径（Ø16@25 → 9），并提示格兰头/锁母外径是否相碰；25 有冲突时取最近的整数/0.5 无冲突值并报告；补加孔的位置一律列 **HOLD 待用户确认**（PDF 第1页、README、确认稿）。`conflict_checks.py` 的 `cable_hole_min_count`（params 键 `cable_holes`，可选）对 1 个线孔报 WARN。订单本身没有线孔时**不**凭空添加（仍受“不擅自加孔”约束），只记 INFO。
7. **结构选型（新箱体强制）**：用户未明确指定结构时，统一单位后 max(L,W) ≥ H（含相等）→ 侧-底-侧 U + 两外封端板 + 盖；否则 U 围 + L + 盖（`scripts/select_structure.py`）。用户明确选择优先。取代 v2.8.2 曾写的“brief 未写 structure 一律 `u_l_t7u`”。
9. **展开图双向标注、免计算（用户 t45u/t46u，2026-10-27，v2.8.6）**：用户原话“为了方便折弯是否选择不同的折弯方向，不用重复计算，尺寸重新标注…也增加红圈的尺寸”“告诉其他的会话后面也要这样做”。每个展开图（PDF 及 BEND DXF 文字标注）在 X、Y 两个方向都必须：(a) 逐段链式尺寸——边→第一折弯、折弯→折弯、最后折弯→对边，每一段都直接标出（不得只标累计尺寸让师傅自己减）；(b) 每条折弯线到**两侧对边**的基线距离各标一个；(c) 总长/总宽；(d) 折弯表每道弯列“距A边 / 距B边 / 段长”；孔位尽量也给两侧基准。这样从哪边定位折弯都能直接读数。缺任一段 = 尺寸不全，不合格。
10. **一盒一个 NEST DXF（用户 t62u，2026-10-28，v2.8.7）**：用户原话「因为现场师傅需要调整套料情况，你给一整个到dxf文件，不要分开，一个盒子，一个dxf的文件」。发布 NEST **默认 kit/1BOX**：只排 **1 套**完整盒体零件（如 U+LID+END_L+END_R 各1），写在同一个 `{VER}_NEST_2440x1220_1BOX.dxf`；仍画 2440×1220 SHEET 板框、CUT 层、CONTINUOUS、边距10、件距10；无折弯线/无文字。订单数量（qty）只写在 README/BOM/确认稿，**不要**为 qty 复制多套进 NEST，也**不要**按物理板拆 `SHEETnn`。套料预览 PDF/PNG 对应 1 页/1 张（1BOX）。单件 `DXF_CUT` 不变。旧 `nest_mode='sheets'`（SHEETnn）仅内部/证据可选，发布默认 1BOX。门禁仍要求一个 SHEET 框且零件在板内。
11. **确认稿版本：工厂 vN vs revN（用户 t69u，2026-10-28，v2.8.8；**部分被规则14 取代**）**：完整配方见[确认稿版本规则](references/confirm-draft-versioning.md)。保留前五段 `S-材质-板厚-日期-编号`，旧厂版完整 ZIP+.sha256 移入 `SUPERSEDED/`。~~原句「PDF 版式/README/打包等非几何微调不升工厂 v」已被用户硬性规则14（t43u/t44u）废止~~——**凡用户将下载/解压的新确认稿包，默认升工厂 vN**（见规则14）。同厂版内部快照仍可用：现场文件始终叫 `{VER}_CONFIRM_DRAFT.zip`（=当前），并另拷 `{VER}_CONFIRM_DRAFT_revN.zip`+.sha256（N 从已有 rev 取下一整数，无则从 0），在 `{VER}_CHANGELOG.txt` 追加一行 `YYYY-MM-DD HH:MM Asia/Shanghai | revN | 简述 | sha256=<hex>`；助手 `scripts/snapshot_confirm_rev.py DIR [note]`（内部快照，**不是**对外区分主路径）。对外只认 live zip+sha256，旧聊天附件不作当前包；revN+CHANGELOG 建立后停止再用 `_before_*` 临时备份名（既有 before_* 可回填进 revN，验证后再进 SUPERSEDED）。
12. **折弯 PDF 统一配色管线（用户 t37u/t38u/t39u，2026-10-28，v2.8.9）**：用户原话「其他图的配色跟你的也不一样」「这个配置一致是之前pdf都在执行的 为什么到你这就不行了」「这个加到最新的skills中」。现场确认稿折弯 PDF **必须**走订单 `addendum-tools/make_bend_pdf.py` + `pdf_common.py`（模板参考 `box-550x195x150/addendum-tools/` 与 `/workspace/shared/sheetmetal_lessons_干画图3.md` §3 / `box-180x420x175`），**禁止**另起灰框 `tools/pdf.py` / 自造 `*_BEND_DRAWING_A3.pdf` 版式顶替交付。固定视觉：海军蓝页眉条（约 RGB 0.10,0.22,0.45）白字标题+发布名+**出图 YYYY-MM-DD HH:MM Asia/Shanghai**（规则15）；其下红条材料栏（约 0.82,0.1,0.1）写材料/板厚/Ri/K/数量/确认稿；尺寸线蓝（DIMC≈0,0.2,0.65）；关键孔位/警告红字；轴测 **绿盖+褐/金箱体**；零件表浅蓝表头；全中文 A3 横 4 页（规则6）；字高≥约3.3 mm（≈9.4 pt）；CJK 用 `scripts/build_cjk_subset_ttf.py` **按本单 PDF 源字面现建子集**（改字后必须重建，否则缺「铰/链/锁/叠」等豆腐字）；尺寸读本版 STEP/DXF/孔表并写 sources。新单：从已验证订单 `cp -r …/addendum-tools` 再改 cfg/孔位，不得复制灰框脚本。技能原生/门禁用的 `pipelines/*/pdf.py` 或 13 页 THREE_VIEWS 只作内部证据，**不**当用户确认稿外观。

13. **ZIP 解压不混单（用户 t40u，2026-10-28，v2.8.10）**：用户原话「当我下载下来，解压出来以后还是跟其他已经解压的一样的目录，这个就容易混」。对外发送的 zip **文件名必须以工厂码 VER 开头**：`{VER}_CONFIRM_DRAFT.zip`、`{VER}_CONFIRM_DRAFT_revN.zip`、`{VER}_OPEN_ME.zip`；**禁止**发送无 VER 前缀的 `CONFIRM_DRAFT.zip` / `CONFIRM_DRAFT_revN.zip` / `CONFIRM_DRAFT_current.zip`（下载名撞车；macOS 多顶层时还会按 zip 名建同名文件夹导致混单）。zip **内部有且仅有一个顶层目录**，目录名 = VER；CHANGELOG 放进该目录内（推荐 `{VER}/DOC/{VER}_CHANGELOG.txt`）；禁止顶层散落其它文件。聊天附件必须指向上述 VER 前缀路径，这样下载到本地的文件名也带 VER。详见[确认稿版本规则](references/confirm-draft-versioning.md)与[交付契约](references/delivery-contract.md)。


14. **新确认稿包默认升工厂 vN（用户 t43u/t44u，2026-10-28，v2.8.11；取代规则11 中「PDF/打包不升工厂 v」）**：用户原诉求——解压后文件夹/文件仍是 `…-v1`，要把尾缀改成真实版本 `v2/v3/…`。**凡用户将下载/解压的新 outbound CONFIRM_DRAFT**（含 PDF 版式/布局、打包/zip 命名、README，**以及**几何/孔位/结构变更）**一律 bump 工厂尾缀 vN**（v1→v2→v3…）。完整更名：zip 文件名=`{NEW_VER}_CONFIRM_DRAFT.zip`；zip 内有且仅有一个顶层目录=`{NEW_VER}/`；目录内每个文件前缀=`{NEW_VER}`（PDF 页、STEP 头、DXF 名、DOC、NEST 等）；旧厂版完整 live zip(+sha256) 移入 `SUPERSEDED/`；写 CHANGELOG 说明升版原因；`production_release=false` 除非用户另说。前五段 `S-材质-板厚-日期-编号` 在同单修订时不变，只升尾缀 `-vN`；几何未变时用 `release_package.py rename`（几何哈希必须不变）。**revN** 仍可作*当前*工厂 VER 下的内部快照，但**对外区分以工厂 vN 为准**，不要靠旧 v1 名下的裸 `CONFIRM_DRAFT_revN` 给用户当解压目录；新 outbound 优先 bump 工厂 v，而不是只打 revN。详见[确认稿版本规则](references/confirm-draft-versioning.md)。

15. **折弯 PDF 显眼写出图时间（用户 t75u，2026-10-30，v2.8.12）**：用户原话「出PDF的时候，将时间也写在文档显眼的位置」。每页海军蓝页眉条（或紧挨其下的红条材料栏）必须用白字写 **出图时间**，格式 `出图 YYYY-MM-DD HH:MM Asia/Shanghai`（本机 Asia/Shanghai 墙钟，生成 PDF 当下时刻，不是订单日期编号）。位置：页眉右侧、页码左侧，字号不小于材料栏；不得只写在页脚小字或 PDF 元数据里。确认稿与正式图均适用。`pdf_common.Pg.head` / 订单 `tools/pdf.py` 的 `page()` 统一实现。


## v2.8.2 交付硬规则（先读，优先于下面的历史章节）

完整规则、来源与 11 项核验见[v2.8.2 交付规则](references/v2.8.2-delivery-rules.md)（合并了 `/workspace/shared/sheetmetal_lessons_干画图3.md`），管线用法见 [pipelines/README.md](pipelines/README.md)。

1. **结构由 brief 选**：缺省按用户硬性规则7选型：max(L,W)≥H → U + 两外封端板（端板盖U）+ 盖，否则 `u_l_t7u`（U + L，L 盖 U 0缝不退让 + t7u 盖角，`pipelines/u_l_t7u/`）；用户明确选择优先；`"structure":"u_endplates"` 用 U + 两块平板外封端板（零折、完全遮盖U端、零缝零退让，盖角缺省03）（`pipelines/u_endplates/`）；原生 `build_general_package.py` 只出确认稿候选。
2. **DXF**：CUT/NEST 只有切割轮廓（连续、闭合、1:1 mm、无重复/重叠），**不带折弯线**；折弯线只在单独 BEND DXF（连续实线、红色 BEND 层＋文字；**任何 DXF 不得有虚线**）；NEST 只 CUT+SHEET，2440×1220 板框，边距10、件距10；**发布默认一盒一文件** `{VER}_NEST_2440x1220_1BOX.dxf`（用户 t62u，订单 qty 不进 NEST、不拆 SHEETnn）。门禁 `scripts/release_dxf.py check --role cut|bend|nest`。原生套料无板框，只作证据。
3. **命名/ZIP**：发布名原样使用（只允许 `[A-Za-z0-9._-]`，否则问用户；不规范化、不自编号）；每个文件和 PDF 每页带发布名，STEP 头/DXF 内也写；文件名 ASCII；每次发布一个完整 zip（**有且仅有一个顶层目录 `<VER>/`**，显式映射重打，testzip+逐条字节比对）；对外 zip **文件名必须以 VER 开头**（`{VER}_CONFIRM_DRAFT.zip` / `{VER}_CONFIRM_DRAFT_revN.zip` / `{VER}_OPEN_ME.zip`），**禁止**裸名 `CONFIRM_DRAFT*.zip` / `CONFIRM_DRAFT_current.zip`（用户硬性规则13 / t40u）。门禁 `scripts/release_package.py package STAGE VER --zip ...`；改名 `release_package.py rename`（几何哈希必须不变）。
4. **折弯 PDF**：全中文、A3、页数尽量少（总装1页+每零件1页，参考现4页版）且尺寸齐全（见用户硬性规则6）、尺寸从本版 DXF/STEP 读、字体嵌入（`scripts/build_cjk_subset_ttf.py`）；**对外确认稿必须用 addendum `make_bend_pdf` 海军蓝+红条配色（用户硬性规则12）**，禁止灰框自造版式。 **每页页眉显眼写出图时间 `出图 YYYY-MM-DD HH:MM Asia/Shanghai`（用户硬性规则15 / t75u）。**
5. **诚实**：“计算检查通过”与“实物试折试装：未进行”分开写；production_release=false；Ri0.8/K0.4 标经验值；**不擅自加把手孔/线孔/顶孔**（模板见 `assets/profiles/`，仅在用户要求时用；例外：用户要求了线孔但只画1个时，按用户硬性规则8补第2个并列HOLD）；“斜角03”=本技能03盖角方案（斜角折弯收口，[lid-defaults03](references/lid-defaults03.md)），不是未知工艺；其他未知工艺名才要参考图。
6. **冲突检查** `scripts/conflict_checks.py`：Ri>g→需 q；t≤1.2 攻 M4 → WARN 薄板攻丝警告（约1扣、易滑牙、不建议反复拆装；压铆/拉铆/点焊螺母替代列待确认，缺省仍攻丝）；接口螺钉孔须攻丝；非0退让/缝须用户来源；深 U 折弯避让；孔边→折弯切线 ≥max(3,2t+Ri)、→外形 ≥4；未要求的特征。
8. **03盖角（v2.8.3）**：带盖新单缺省 corner_scheme=03（斜角03）；每单按本单 t/Ri/K/裙高/corner_gap 重算 P1/P2/P3（不得照抄旧单坐标）；`scripts/corner03.py` 与 `scripts/native03_check.py`（含盖/箱体根部重叠、q 实测）必须都跑且通过；corner_gap 取用户明确值（如“不要有缝”=0），用户未给时用候选 0.2 并在确认稿/PDF 标“候选值，待确认”；native 拦下用户值时如实报数，不得静默改 0.2/0.4。
7. **确认稿** `scripts/confirm_draft.py` 只写 `<VER>_CONFIRMATION_DRAFT.txt`（含 包含/未添加/假设/待确认/冲突），**从不发送**；任何对外消息由用户决定。

## R12 材料码与描述分离

发布前读[材料码映射规则](references/R12-material-code.md)。文件主码的材质段使用material_code；源job里的材料描述保持原样。201 stainless steel→201等转换必须有绑定精确源描述/代码的明确确认和来源，不能静默截取数字、混淆304L或Q235B等牌号。缺确认返回未命名待确认；冲突/未知已确认映射阻断。原描述已等于安全代码时可沿用同码；旧material命名字段兼容但不得与material_code冲突。所有DXF/PDF/目录/唯一ZIP仍按同一主码，工厂v独立于内部R；缺编号不得猜。

R12工程核心为2.8.1-R12；显式裙高保留原精度；用户最新通用默认盖裙固定15mm，禁止按厚度/尺寸静默升高，显式数值来源必须指向本次brief。旧R11错误取整或错误来源的编译记录不得冒充当前通过，应从原brief重编译新候选；冻结R11失败记录保留。当前隔离开发不改客户原几何或全局安装；后续仅按已授权安装顺序更新技能。新发布标记2.8.1-R12；合法旧R10发布仍可只读校验，但新材料映射不得降标记伪称由R10生成。命名通过不等于制造放行，HOLD与专项授权边界保持。

## R12 中文师傅作业册与当前验证状态

出图前读[中文作业册与限制](references/R12-CN-workshop.md)。新完整制造路径采用 `cn-workshop-dimensioned-v1`：说明全中文，突出材料、板厚、数量、零件号、实际成形/展开尺寸、Ri、K及补偿来源、逐弯位置/方向/角度/折序与靠边候选。三视、斜视、展开、03局部及爆炸图凡展示均标实际尺寸；爆炸只平移同一零件，不能把位移后的整体范围当产品尺寸。参数审计长文单独归档为MD，不塞进师傅作业册。确认稿由 `cn_confirmation.py` 渲染，缺参或冲突清单不伪造CAD或制造展开。

接单读图和出图前读[现场经验](references/field-experience.md)：手绘图读图、常用开孔模板、接头空间、台阶箱、PDF标注、命名与打包坑。

默认盖裙15mm不保证任意板厚/圆角组合都可展开。已知t2、Ri0.8、角缝0.2组合会因微小角部自交被阻断，应保留原失败；`derive_corner_candidate.py` 可另外派生角缝0.4候选，保留原brief哈希及原角缝，标待确认/HOLD，不能将0.4写成通用默认或直接放行。显式12.34mm仍精确保留，不能为凑默认15或便于机台而取整。

当前为已冻结待独立验收候选：作者已完成固定CN03快照的两结构全链路、默认15/显式12.34、中文53页视觉、解包回读和定向负测试；详见[R12作者报告](references/R12-author-report.md)。独立验收尚未执行，未更新全局安装。旧输出仅更名发布不等于重新生成了最新中文模板。安装须依次完成冻结、独立通过、备份旧v2.3.0及符号链接结构、安装同一哈希版本、新调用上下文核路径/版本/哈希和完整烟测；见[安装与调用](QUICKSTART.md)。不得把当前实现、历史阶段证据或单测数量写成整包已通过。

## 通用需求入口（R12修订，待独立复验）

新矩形订单优先读取[通用输入与分级工艺](references/general-process.md)，使用 `scripts/build_general_package.py BRIEF.json --output ARCHIVE`。不要求先手填全部显式 job，也不能从某客户复制孔坐标。编译器真实执行四层：通用约束、条件经验候选、本款计算、用户覆盖/带来源记录；原始 brief、逐参数来源 CSV/JSON 与 PDF 同版归档并复算交叉核验。正式编号缺失仅标未命名待确认，不阻建模。显式无孔、结构和尺寸参数优先。

单位、尺寸、尺寸口径/含盖、板厚、是否有盖缺失时生成缺参确认资料，不猜测必要输入；材料未知或显式配合冲突仅生成真实成形确认图/STEP及数值，明确没有制造展开。`validate_general_review.py`只验确认资料来源和完整性，`validate_delivery.py`拒绝把该资料当制造齐套。完整几何路径还需实际成形/原生展开/03/孔轴/CUT与BEND/套料/PDF及装配爆炸仅平移核验。

默认盖裙15mm（来源用户 Sentinel_a06b1b0204b8819192a24d11cae4cdc4）、Ri0.8、单边 g0.5、外封端板轮廓退让默认0（端板盖U、不留缝、不退让；用户硬性规则1，仅本单用户明确给值才非0）；退让不是轴向接合缝。未给 q 时按本款 Ri/g 计算建议顶隙并在固定闭合总高中联动体高，来源表及 PDF 必须显示；已有 q 不自动更改。默认参考两圆孔可以显式 `none` 覆盖；不是自动选择 PG 接头。把手只有用户选用后才生成安装参考，活动包络与承载未验证。不能把未知 K、刀模、材料批次或现场修配当确认事实；不跨项目继承授权。

分确认稿、带来源试折包、工厂签署首件装配记录。最后一种只核验用户/工厂提交记录的作用范围和一致性，软件未见证实物或鉴定签名，仍不自动签生产放行。所有阶段保留真实几何检查及最终单 ZIP 规则。此通用入口只支持列明的矩形钣金适配器；异形/既有 STEP 进入明确适配/审核路径，不偷换矩形生成器。

## 当前发布契约（R10）

发布和最终投递前读[R10发布契约](references/R10-publication.md)。R09曾漏检旧R08命名发布副本删默认计划，本轮不得沿用其不通过结论冒充完成。新发布独立绑定封套/manifest/命名记录的发布契约与默认单ZIP计划，不能因源制造版本旧或删除字段而跳过；原CAD/DXF/PDF/job和现场授权保持原字节。原始未发布R08仍可只读验核；旧R09合法命名副本须经公开发布入口升级，不直接当作R10发布通过。

## 工厂编码命名

新交付必须读[工厂命名规则](references/factory-naming.md)与[确认稿版本规则](references/confirm-draft-versioning.md)：`S或X-材质-板厚-YYYYMMDD-四位编号-vN`，每个文件（尤其套料DXF、完整折弯PDF和套料预览PDF）、修订主目录及唯一ZIP共享主码前缀，再加中文用途/零件后缀。工厂v不等于内部R修订；升版保留前五段。用独立`--naming`输入，不改原始设计job/专项授权。缺正式字段标“未命名待确认”，不猜渠道、编号或重置规则；示例Q235/0001不覆盖本项目材料或替工厂分号。执行默认命名发布入口后再核最终门禁，保留更名映射和CAD/DXF原字节。

## 最终默认一个完整 ZIP

发送前必须读[统一投递约定](references/message-delivery.md)。每客户/需求及修订只有一个统一主目录，最终默认仅附本修订完整 ZIP；不同时逐项附 PDF、STEP、DXF，不跨多条消息拆发同一套资料。先确认图是确认阶段，不等于最终可以散发。用户当前明确索要单件或要求先看确认图才例外，记录本次原文、来源、身份/修订/ZIP哈希及所选文件；旧“好了一个发一个”不能覆盖当前统一交付要求。用户新指令优先。

生成入口返回的 `delivery.final_message_plan` 默认只有完整 ZIP；发前运行 `scripts/prepare_delivery_message.py REVISION_ROOT`，按已检查的整次消息计划发送。需要例外或校验拟发附件时，使用该脚本的 `--file/--user-request` 或 `--plan`。它检查文件和送检计划，**不发送消息，也不能保证智能体不绕过计划另发附件**。父/执行智能体仍对实际发送负责。用户索要更新技能时只交付一个完整新技能 ZIP，报告和补丁放包内，不自动再散发。

## R07 强制齐套交付

运行前读 [齐套交付契约](references/delivery-contract.md)。已经具备完整显式参数的订单走 scripts/build_package.py；通用需求走 scripts/build_general_package.py；--output 是归档父目录，入口强制创建 customer/requirement 身份目录与 revisions/修订，禁止覆盖现有修订。它实际生成分件/装配/爆炸STEP、分件真实展开CUT、按板号集中套料CUT与预览PDF、材料/数量/来源/逐弯基准齐全的三视斜视工艺PDF、BOM/参数/孔表/验收清单/哈希及ZIP。交付前必须 scripts/validate_delivery.py REVISION_ROOT 成功；旧manifest门禁通过不能单独声称R07齐套。数字齐套仍HOLD，不等于生产放行；人工逐页看图和独立复验分别记录。

源STEP仍走 audit_step.py，保留源结构；该模式明确产出 SOURCE_AUDIT_ONLY_PARTIAL_HOLD 审核包及逐项必交槽位状态，退出2，不能把未知材质/K、诊断展开或缺制造套料包装成齐套制造交付。禁止为了通过换新箱体生成器改源模型。

## 新矩形箱体：实际生成入口

新增[本项目现场修配接受流程](references/site-fit.md)：Ri/g/q 的已知包络冲突先提示，完整交付需本项目用户明确选择现场修配或尺寸变更。现场修配授权绑定本次 job ID、完整设计哈希、参数与孔；不改几何、不清零交叠，不跨客户自动继承。`record_site_fit.py`只把已核实的授权原文与来源写入新副本；它不能证明授权文字真实。无授权可做 formed-only 确认审核，完整制造格式交付会阻断。

默认折弯 PDF 现在必须含[每个折弯件的真实成形轴测图](references/formed-isometric.md)、同源 B 编号及原生折弯方向；另附整装／爆炸图不能代替。

1. 常用 N02 流程可直接参照[常用候选 job](assets/examples/common-460-review.job.json)和[候选与来源规则](references/common-profiles.md)，其把手/周边孔仅在显式选择时生成。其它需求从[job空模板](assets/templates/box-job.blank.json)建立本次需求，参照纯合成[四件式](assets/examples/box-external.job.json)或[三件式](assets/examples/box-wrap-l.job.json)。单位、材料、t、Ri、K、拼缝，以及有盖时裙高/角缝/q必须有本次来源；未知不得复制示例或历史数值；显式选择common_review_v1仅允许缺失K/角缝采用带来源的assumed试折候选，不能当确认值。新有盖项目未明确覆盖时，盖裙默认15mm、单边g默认0.5mm、角方案默认03；不得复制旧示例裙高代替当前默认。
2. 运行 `scripts/build_package.py`，同一job驱动选型、canonical schema、分件CAD、真实展开及DXF/PDF。无显式结构选择的新箱体：max(L,W)≥H为侧—底—侧U＋两外端板，否则为三面U围＋底侧L；相等归前者，请求有盖才加盖。显式选择优先。
3. 必须完成：成形STEP导出回读→逐件SheetMetal真实展开（零折端板只刚体转平）→每件激光DXF→有盖03重新原生展开，核4折/8斜边/面积一致、实际盒体根部/q→实际三视与展开PDF→完整清单门禁→逐页渲染。无跳过03或缺件继续成功的开关。
4. 非支持几何、缺模块/API不符或检查失败必须BLOCKED，不改用未验证旧生成器后冒称通过。当前入口不生成未声明的内折边、台阶、沉座、压铆或把手实体；这类要求需独立实际CAD适配和校验，不能静默忽略。
5. 每计划钣金件恰有一份制造DXF，并绑定其成形/展开STEP证据；完整请求不能漏格式。03报告绑定本次STEP/DXF/盒体及PDF矢量轮廓。交付依据RUN_RESULT、project、manifest和实际文件，脚本退出0为GEOMETRY_CHECKED_WITH_HOLD，或在有实际交叠且本项目授权时为DELIVERED_FOR_AUTHORIZED_SITE_FIT_WITH_HOLD；后者明确未消除干涉、未试装确认。机台BG、材料批次、工装、回弹、首件未知保持HOLD；Ri0.8/g0.5/q0的正交叠须报告；只有明确本项目现场修配授权才可带原干涉交付，不改尺寸或删交叠。执行agent须逐页目视PDF，自动渲染不等于已目视。

## 既有STEP：独立可运行入口

收到实际STEP时先走 `scripts/audit_step.py source.stp --output /absolute/new-audit`，不要为迁就新箱体job而改原结构。详读[既有STEP运行契约](references/existing-step.md)；参数模板为assets/templates/existing-step-audit.json。该入口核全部源Solid、基础/严格BOP、真实t/R/分段圆孔与干涉，支持的分件做原生展开、共用毫米/CUT DXF写出回读、全源件三视/折弯审核PDF。未知补偿或源缺陷保留partial/HOLD，不能由诊断平坯升级制造通过。缺原生平坯的件仍在图册和状态表里，不能跳过。

保留既有盖角、g/q和拆件；不套新订单03/g0.5默认。8斜边不等于03，显式03要求仍需native03_check。诊断K与制造K分开，材料未知不伪确认。不开闭合围框接缝、不自动重拆件或改角；设计选择需先给方案并获得用户确认。无设计变更副本试验不得提高公差/删面凑通过，不自动替换原件。错误报告须区分CAD已执行与检查成功，实际运行后BOP失败仍CAD_executed=true。

## 特殊几何及窄改

保留原件、SHA和既有确认值；不因升级改旧结构、角方案、间隙或孔。明确重建既有尺寸项目时，新入口要求显式method与rebuild_existing_authorized=true，仍只写新目录。

读取[参数来源](references/parameters.md)、[制造拆件](references/manufacturing.md)及[工具路线](references/tools.md)，实际核单位、方向、厚度、Ri、有效实体、板厚尺寸链、孔轴和干涉，不用外包或JSON代替BRep。窄改按[变更规则](references/changes.md)回读编辑区域外不变。

涉及盒盖必须读取[03几何与强制核验](references/lid-defaults03.md)：按本件t/Ri/裙高/角缝/补偿重算，g与q独立。明确启用四孔梯形把手时，宽排圆心距条件默认85.00mm；按[把手规则](references/handle85.md)逐实例STEP/DXF回读，不能只改标签。孔型和二次加工按[孔与硬件](references/holes-and-hardware.md)；M4不是激光直径，沉座口大圆不能进CUT，缺硬件/工厂证据继续HOLD。

旧参数、迁移及局部适配工具继续提供，见[验证限制](references/validation.md)。单跑validate_project.py的PASS_WITH_HOLD仅为参数审核草案。最终按[检查放行](references/checks-and-release.md)核实际STEP/DXF/PDF和首件。编号用Asia/Shanghai分钟及明确+08:00。

## R06限定复核

新箱体与既有STEP门禁均须从实际STEP和选定根面重新原生展开，回读signed angle、方向、根法向、弯轴/点及裁剪平坯弯线，再核输出；同步改JSON/PDF的方向不能通过。见[方向实际回读和体积口径](references/R06-direction-volume.md)。新箱体PDF/canonical/native/最终结果统一使用导出回读BODY与LID布尔体积；PDF显示6位，逐件和另列诊断，不宣称所有原始小数都是实测精度。

## 验证边界

普通unittest验证软件规则及反例；scripts/selftest_existing_step.py验证受支持合成STEP导入及未知K反例，实际用户附件另测；scripts/selftest_acceptance.py重测R01实际失败输入；scripts/selftest_cad.py实际生成两种有孔03结构、无盖项目并检查缺件/错误几何阻断。作者自测和无历史上下文独立agent验收分开报告。只承诺在列明公开依赖与支持范围内可复现，不保证所有模型/宿主/agent绝对成功。

商业使用见[现有许可](COMMERCIAL-LICENSE.md)，不扩大第三方软件或项目操作授权。

R07–R12 作者/独立验收历史已原样移到[验收历史](references/history-R07-R12.md)；历史状态不扩大为 v2.8.2 通过。
