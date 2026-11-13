# 当前部署与历史安装说明

## 当前入口（2026-11-12，优先于下文历史调用）

当前版本 2.8.58，基于 27 服务器 2.8.46 部署快照。新箱体出图统一为 `sm golden` → `scripts/build_golden_package.py`，PDF 只走 `bend-pdf-golden-001-visual`。brief 必填客户原话 `customer_requirement_text`，可选后续原话数组 `customer_requirement_updates`，几何参数仍需单独填写；原文及修改记录自动排入工艺 PDF 末尾。实际参数、支持结构、环境变量和调用方式见 [README](README.md)。本仓库不包含另行部署的 MCP/HTTP 服务。

下文保留早期安装、审核工具和 R12/R10 验收说明；其中 `build_package.py` / `build_general_package.py` 等历史出图 CLI 已退役，不能作为当前新箱体出图入口。旧验收记录不代表当前部署版本已通过完整制造合同或实物验收。

# 完整 v2.8.1 R12 候选：历史安装与最小调用

## v2.8.2 快速路径（2026-10-26）

```bash
# U+L+t7u（max(L,W)<H 或用户指定；L盖U 0缝不退让）：见 pipelines/README.md A 节（SM_ORDER + release_config.json；features 缺省=不开任何额外孔）
# U+两端板：python3 pipelines/u_endplates/run.py BRIEF.release.json /new/out/dir
python3 scripts/conflict_checks.py PARAMS.json [report.json]          # Ri>g / M4薄板 / 深U / 孔边距 / 未要求特征
python3 scripts/confirm_draft.py BRIEF.release.json conflicts.json OUTDIR   # 只写 <VER>_CONFIRMATION_DRAFT.txt，不发送
python3 scripts/release_package.py package STAGE VER --zip OUT.zip --pdf-pages 4 --orders /workspace/orders
python3 scripts/release_package.py rename OLD OLDVER NEWVER NEW        # 几何哈希必须不变；PDF 需重出
/workspace/addendum-venv/bin/python scripts/release_dxf.py check --role cut|bend|nest FILES...
```
发布前逐项过 [v2.8.2 规则 §8 的 11 项核验](references/v2.8.2-delivery-rules.md)。


本版是可独立解压的完整技能候选，不是增量包。先读[中文作业册与边界](references/R12-CN-workshop.md)、[通用参数契约](references/general-process.md)、[材料码映射](references/R12-material-code.md)和[显式精度](references/R12-explicit-precision.md)。默认盖裙15mm；用户显式12.34mm等值精确保留，不静默升高或取整。默认发生几何冲突须报告并阻断相应制造路径，独立派生角缝候选不修改通用默认。

作者已完成固定CN03快照的有界实际回归、53页中文作业/确认/套料PDF视觉及三份ZIP解包回读，见[作者报告](references/R12-author-report.md)。独立复验尚未执行，未更新全局安装。R11独立失败及历史阶段证据保留；R10限定通过不代表本候选通过。仅更名旧包不会重新渲染最新中文PDF，也不升级其原工程验收结论。

## 安装顺序与当前状态

先在解压隔离目录使用下列调用，无需提前覆盖全局。正式更新顺序为：冻结完整ZIP及SHA256 → 独立验收通过 → 备份旧v2.3.0实际目录、文件哈希及符号链接结构 → 安装已验收同一哈希内容 → 全新调用上下文核实际路径/版本/完整清单并运行完整烟测。不得提前安装未验收候选。

备份前记录 `~/.codex/skills/step-sheetmetal-delivery` 与 `~/.agents/skills/step-sheetmetal-delivery` 的实际类型/链接目标；不能假定它们是两个独立副本，也不能将其中的链接误作完整备份。保留原目录和链接记录，不删除旧备份，不改客户图纸。`verify_install.py`只验包文件清单，不能代替独立CAD/PDF验收或证明新会话已加载正确路径。

## 通用需求最小调用

```bash
python3 -B scripts/build_general_package.py /ABS/current-brief.json --output /ABS/new-archive --resolve-only
python3 -B scripts/build_general_package.py /ABS/current-brief.json --output /ABS/new-archive --naming /ABS/factory-naming.json
```

`--resolve-only`只解析，不运行CAD；正式编号缺失可以不传`--naming`，产物明确未命名待确认，不猜编号。关键输入缺失只出确认清单；材质未知或显式配合冲突按实际状态走确认稿，不能冒称制造齐套。不得从历史订单复制不适用于本款的尺寸、孔坐标或现场授权。

## 公开依赖

普通Python3.10+，jsonschema、ReportLab、pypdf、Pillow、NumPy（见references/runtime-requirements.txt）；另需FreeCAD的Part/TechDraw绑定、SheetMetal含SheetMetalNewUnfolder/networkx、Poppler pdftoppm和可渲染CJK的字库。第三方引擎/插件/字体不随包。

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r references/runtime-requirements.txt
.venv/bin/python scripts/discover_runtime.py --probe
.venv/bin/python scripts/verify_install.py
```

作者宿主为macOS arm64/FreeCAD1.1.1/OCCT7.8.1/SheetMetal0.8.21。非标准路径可用--cad-python、--freecad-lib、--sheetmetal-path、--pdf-renderer或FREECAD_PYTHON/SHEETMETAL_PATH。受限沙箱Qt NEON失败须在宿主授权的隔离执行环境使用同一入口；不控制别的FreeCAD进程。缺依赖阻断，不能跳过CAD门禁。

## 先读齐套契约

必读references/delivery-contract.md。job中填写本次材质、t/Ri/K、体外尺寸及高度口径、结构/角缝/g/q/裙高、孔和来源；显式用户值优先。新有盖默认max(L,W)>=H选U+两外端板+盖，否则U围+底侧L+盖。旧项目保护、无盖范围、03真实几何、轮廓退让/轴向缝区分不变（默认均为0：端板盖U、L盖U，不留缝不退让，用户 t16u）。

job.delivery指定namespace=customer或requirement、entity_id、revision、sets和stock来源/状态。未给身份只按job.id归档需求，不猜客户编号；未给板幅只采用带来源的2440×1220/10边距/10件距试折候选，不标客户确认。

```bash
.venv/bin/python scripts/build_package.py /ABS/current.job.json --output /ABS/customer_archive
```

--output现在是归档父目录，入口实际返回revision_root，例如`/ABS/customer_archive/requirement_REQ003/revisions/CODE_R03`（CODE用实际返回主码替换；缺字段返回“未命名待确认”目录）。同修订已存在即阻断，不覆盖。每修订同版含确认PNG、成形分件/装配/爆炸STEP、逐件真展开CUT、每板集中套料CUT和预览PDF、完整三视/斜视/展开/材料数量及逐弯工艺PDF、BOM/参数/孔表/验收/哈希和ZIP。

```bash
.venv/bin/python scripts/validate_delivery.py /ABS/customer_archive/requirement_REQ003/revisions/CODE_R03
```

只有完整交付门禁通过，DELIVERY_ENVELOPE的digital_deliverables_complete才为true。production_release始终false；图册仍须人工逐页目视，首件和独立复验分开。RI/g/q根部正干涉无本项目授权仍阻断；有授权保留真实体积、现场修配/试装待确认，不改几何求通过。record_site_fit.py仅记录已核实的本项目授权，见references/site-fit.md。

源STEP走保留原结构的独立入口：

```bash
.venv/bin/python scripts/audit_step.py /ABS/source.step --output /ABS/source_archive --entity-id ASM0027 --revision R01
```

当前源审计模式即使部分或全部几何可核，也只提供SOURCE_AUDIT_ONLY_PARTIAL_HOLD审核ZIP、必交槽位的逐项限制清单，并退出2；不冒充完整制造工艺和套料。未知K/材料、诊断展开不升级；validate_delivery对审核根目录明确拒绝齐套声明。不得用新箱体生成器绕过源拓扑或擅自变更拆件/尺寸。

## 可复现作者测试

```bash
.venv/bin/python -B -m unittest discover -s tests -v
.venv/bin/python scripts/selftest_delivery_contract.py --output /ABS/new-R08-author-test
.venv/bin/python scripts/selftest_receipt_authority.py /ABS/generated/revision_root --output /ABS/new-R08-receipt-test
```

自测从包内原始合成输入生成380×230×145四件式和185×160×295三件式、未知材料/K的源STEP限制例；重测缺必交类型、错版本/材料/t、套料遗漏/重叠/两倍尺度、ZIP缺失和实际CAD方向伪报。模拟现场许可明确SYNTHETIC，不是任何客户许可。assets/examples/delivery-*.job.json只用于自测，不复制其尺寸/补偿/授权到订单。

原R06方向/权威干涉及后续完整交付、命名发布门禁保留，不得降级或去掉门禁声明。上述脚本验证其声明范围，不能代替R12公开通用入口的实际全链路与最新中文模板验证；旧selftest_cad、selftest_site_fit、selftest_existing_step保留辅助回归。历史资料保留其当时版本，不充作当前独立通过。

FreeCAD: https://www.freecad.org/ ; SheetMetal: https://github.com/shaise/FreeCAD_SheetMetal ; Poppler: https://poppler.freedesktop.org/ 。包内许可不扩大第三方使用许可。

R08额外权威检查与同步篡改复现见references/R08-authority.md。只读兼容验证R07包不表示原R07独立验收通过；其两项失败已明确保留。

## 最终投递（沿用统一单包规则）

完整生成后先看 `delivery.final_message_plan`：默认一条消息、一个本修订完整 ZIP。正式发送前运行 `python3 scripts/prepare_delivery_message.py /ABS/ENTITY/revisions/REV`。不要把包内 PDF/STEP/DXF 另列为默认附件。用户明确索要单件或先确认图的例外及整次消息计划格式见 references/message-delivery.md。计划文件放修订目录外，不破坏冻结清单；本脚本不会联系用户或代发附件。

## 文件主码

生成入口增加 `--naming /ABS/actual-factory-naming.json`，详见references/factory-naming.md和naming.schema.json。缺字段仍可形成带HOLD的齐套工程副本，但前缀明确“未命名待确认”、正式code为null；不得伪造渠道/工厂编号。已有包只更名副本用publish_named_delivery.py，不重建CAD。最终revision_root以生成返回为准，名称是主码_内部修订；旧示例路径仅说明归档层级。

同厂版确认稿微调（不升工厂 v）用 `python3 scripts/snapshot_confirm_rev.py /ABS/named_release/<VER> "简述"`：拷贝 live `{VER}_CONFIRM_DRAFT.zip` → `…_revN.zip`+.sha256，并追加 `{VER}_CHANGELOG.txt`。工厂 v vs revN 规则见 references/confirm-draft-versioning.md（用户 t69u / v2.8.8）。

## R10 发布版本与兼容

必读references/R10-publication.md。新发布将named-single-zip-v2和2.7.3-R10绑定封套/manifest/命名记录；源制造契约和PDF/CAD版本保留原值。原始R08只读检查可通过，不等于已做R10命名发布。旧R09合法命名包经publish_named_delivery升级；缺默认计划或发布字段降级拒绝，不能靠旧制造版本免检。原R09独立失败仍为失败，R10作者验证与独立复验分开。

## 中文作业册与角部候选

新完整制造路径要求 `cn-workshop-dimensioned-v1` 作业册：材料/板厚/数量/R/K/补偿醒目，三视、斜视、展开、03局部和爆炸图均标适用的实际尺寸，逐弯给原生方向、位置和折序/靠边候选；爆炸移位不计产品尺寸。审计来源长文另存MD。完整回归仍须固定版本实际生成、解包读回并全页目视，不能仅检查模板名。

t2、Ri0.8、原角缝0.2的已知自交应被阻；可使用 `derive_corner_candidate.py BRIEF --output NEW_BRIEF --source 本次证据引用` 独立派生本款候选。该例得到0.4，原值和默认15保留，候选待确认/HOLD，不是新的通用默认。具体调用及限制见[中文作业册与边界](references/R12-CN-workshop.md)。
