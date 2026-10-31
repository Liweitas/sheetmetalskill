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
