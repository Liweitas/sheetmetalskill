# R07 独立验收报告

结论：**本轮不通过，须修复后以新冻结包复验。** 实际生成、套料与多数门禁正常，但两项语义矛盾输入被完整交付校验误判为 `ok=true`、`digital_deliverables_complete=true`。没有修改冻结包、生成器、全局技能、原件或正常交付物，没有上传。

## 包与方法

对象为 `step-sheetmetal-delivery_v2.7.0_full_candidate_R07_20261022_1957.zip`，352614 字节，SHA256 `4211482b5c66adec29b058a02c3566d47d559f4a60e562976baa528e6e8ad994`。在本目录 `package/` 冷解包，读取完整 SKILL、快速入口及交付契约后使用包内支持入口；作者复现文档仅用于定位，未采用其测试通过结论。安装检查核 144 项；最终逐字节比对 ZIP 的 145 个非目录成员，未修改。

环境：FreeCAD 1.1.1 / OCCT 7.8.1，SheetMetal 0.8.21，networkx 3.6.1，Poppler；详见 `runtime_probe.json`。外部 CAD/SheetMetal 是已声明的运行依赖，包不等于无依赖 CAD 安装器。

独立脚本仅测量/构造输出副本反例，不补生成器。原生 CAD 检查直接回读 STEP，调用原生 getUnfold，另行捕捉圆柱弯轴与展开 sketch 变换；PDF 检查读取实际向量和文字；套料检查使用独立 ASCII 解析器，比较每个分件平移后的实体多重集。没有把字段存在、文件哈希或作者 PASS 当几何证明。

## 两项失败

### F1：PDF 尺寸与回执同步伪报被接受

证据目录：`negative_cases/strong_wrong_PDF_dimensions_and_receipts/customer_INDEPENDENT_R07/revisions/R01/`。

实际源 job、canonical 参数及 CAD 是外长宽高 **218×148×94 mm**。副本工艺 PDF 首页和工艺总览两处长宽改为 **999×888 mm**；同步修改 DELIVERY_SPEC 的 process_pdf.header、PROCESS_PDF 回执、PDF 哈希、manifest、完整文件清单、ZIP 及封套 ZIP 哈希。源 job、canonical 参数、全部分件/装配/爆炸/展开 STEP 和分件 DXF 保持字节一致。

包内 `validate_delivery.py` 返回 **0 / ok=true / digital_deliverables_complete=true**。进一步 `validate_manifest.py` 也返回 **0 / ok=true**，明确实际 CAD 已执行。不是未触发原生检查或陈旧哈希导致的假反例。`strong_failure_proof.json` 保存 16 项权威输入/CAD 字节未变、实际尺寸和错误 PDF 原文；原始完整返回见 `negative_cases/strong_wrong_PDF_dimensions_and_receipts.stdout.json` 和 `strong_dimensions_manifest.stdout.json`。

代码定位：`scripts/workshop_pdf.py:82` 的 check_process_pdf 对材料、厚度、版本等重新取 canonical 值；尺寸整行则只与传入的 `spec['header']` 自洽，没有按 canonical/source 重新构造尺寸口径。因此“PDF＋回执”可共同说错。风险是车间能收到与实际 CAD 不同的总体尺寸，仍被标为数字齐套。

### F2：交付封套套数伪报被接受

证据目录：`negative_cases/false_envelope_sets/customer_INDEPENDENT_R07/revisions/R01/`。

DELIVERY_ENVELOPE 的 sets 改为 **999**，实际 source/spec/layout/PDF 均为 **2 套**，BOM 四个件号各 **2**；完整交付校验仍返回 **0 / ok=true / digital_deliverables_complete=true**。详见 `strong_failure_proof.json` 和 `negative_cases/false_envelope_sets.stdout.json`。

代码定位：`scripts/delivery_contract.py:214` 的 check_envelope 检查 contract、production_release、digital_complete，再验证清单及 ZIP，但没有将封套 sets 与可信源/spec/BOM/layout 交叉核对。封套本身又不进入自身清单/ZIP，这是避免自引用所需，但不应免除语义检查。本轮实证仅指 sets；不把其它未测字段推定为已验证漏洞。

## 正常路径及限定通过项

所有制造正例均为明确标记的独立合成测试数据，材料 `304_TEST_ONLY`、t1.2、Ri0.8、假定 K0.4；不是客户材料证书或真实授权。现场修配夹具由支持入口 record_site_fit 产生，并明确标注测试数据，不适用于 ASM550003 或其他客户。

| 路径 | 实际输入/数量 | 结果与交付 |
|---|---|---|
| 四件式 U＋两端板＋盖 | 218×148×94，2套，q0.2 | 正常入口退出0；工艺PDF24页，套料PDF2页；8件/2张板；保持HOLD |
| 三件式 U围＋L＋盖 | 112×82×174，3套，q0，测试专项修配授权 | 正常入口退出0；工艺PDF21页，套料PDF3页；9件/3张板；授权现场修配且HOLD |
| 同客户另一个修订 | 四件式同参数，R02 | 实际生成成功；与R01隔离，22类产物一致 |
| 同修订重复生成 | 已有R01 | 退出2，REVISION_EXISTS；全部原文件哈希不变 |
| 原始已有STEP | 指定 asm0027_asm.stp，材料/K未知 | 退出2，SOURCE_AUDIT_ONLY_PARTIAL_HOLD；无伪造完整制造齐套 |

目录根分别为 `archive/customer_INDEPENDENT_R07/revisions/R01`、`archive/requirement_INDEPENDENT_R07/revisions/R02`、`archive/customer_INDEPENDENT_R07/revisions/R02`。客户与需求命名空间未混用；源审计另在 `archive/requirement_SOURCE_INDEPENDENT_R07/revisions/R01`。

正常制造目录中确认图、实际装配/爆炸/分件 STEP、真实分件展开 DXF、集中 CUT、套料预览、完整工艺 PDF、BOM CSV/JSON、参数、源 job、孔表、回读证据、清单和 ZIP 齐全。manifest 的 22 类 artifact 在两结构与新修订一致。独立清单/ZIP 核对分别为 72/73、66/67、72/73 项/成员，CRC、成员覆盖和字节一致；ZIP有清单，封套和ZIP本身排除以免循环。证据：`independent_transport.json`。

独立实际展开检查覆盖 **13 个弯**：四件式 U2/盖4，三件式 U2/L1/盖4。厚度、BOP、真实弯轴方向、signed angle、B编号、source formed point、原生平坯坐标/折线均核对。平坯面积与存储展开差为0；所有13弯若忽略原生 sketch 逆变换均会错位，本轮已正确使用该变换。PDF真实成形轴测投影向量、展开标签锚点和坐标表另行回读；工艺基准取实际CUT直边，距离独立核验。证据：`independent_bends.json`、`independent_pdf_geometry.json`、`workshop_readback.json`。

主要两结构工艺/套料合计 **50页逐页目视核验**，中文首页及工艺页可读，无明显缺字或裁切；三视、真实斜视、分件、展开与盖裙信息存在且与回读一致。主CAD视图标题/部分注记仍为英文，不能声称全中文化；密集工艺表需A3或放大阅读。未把源审计17页和次修订24页计入本次50页目视范围。见 `PDF_visual_review.json` 和 `visual_sheets/`。

材料、厚度、尺寸口径、数量、状态正常首屏正确。逐弯位置、方向、角度、候选顺序、展开坐标和基准关联正确。盖裙外高14、自由直段12、假定BA90=2.010619 mm，中心线距13.005309 mm，未混为同一高度。K保留assumed；实际刀模/V槽/BG/机台折序/退刀与首件记录未确认，均保持HOLD，没有编造投产放行。

套料DXF独立回读：显式 `$INSUNITS=4`、毫米1:1、仅CUT、平面LINE/ARC/CIRCLE，轮廓和孔的实体多重集与实际分件DXF平移副本完全一致；件数8/9，无重复实体，600×450候选板，最小边距12、保守包围框件距8 mm。只证明当前零旋转保守排样的无重叠与覆盖，不证明最优排样、刀路、割缝、桥接或纹向。证据：`independent_nest.json`。

## 状态、授权与回归

三件式保留实际正交叠 **2.292783468825668 mm³**，canonical/native/final/worker四处权威值一致；逐件对求和约2.2928202366940686仅作诊断，不替换权威值。状态 `DELIVERED_FOR_AUTHORIZED_SITE_FIT_WITH_HOLD`；Ri0.8/g0.5/q0未暗改，geometry_eliminated=false、trial_assembly_confirmed=false、production_release=false。这是允许的测试夹具现场修配情形，不是本轮失败原因；真实客户授权没有被扩展。见 `R06_authority_scope_check.json`。

R05保留的两份 UP/+90 同步伪报真实反例，交给R07的新建/已有STEP校验入口，均退出2，实际CAD读回DOWN/-90并拒绝。已有STEP原件的材料/K未知及BOP/闭框限制继续审计/部分HOLD；完整交付校验拒绝此审计目录。没有切源件或更改参数求通过。见 `legal_and_core_results.json`。

输出副本定向反例11项，**9项正确拒绝、2项漏检**；另有合法重打包正例通过，证明同步清单/ZIP方法本身不会必然触发拒绝：

| 反例 | 实测 |
|---|---|
| 缺工艺PDF、缺交付ZIP | 拒绝 |
| 错交付版本 | 拒绝 |
| BOM材料同步错、厚度同步错 | 拒绝 |
| 实际CUT漏一件 | 拒绝 |
| layout与CUT同步移动重叠 | 拒绝 |
| 删除齐套/工作流标识试图降级 | 完整入口和manifest入口均拒绝 |
| PDF材料＋回执同步伪报 | 按canonical材料拒绝 |
| PDF尺寸＋回执同步伪报 | **漏检F1** |
| 封套套数伪报999 | **漏检F2** |

详见 `negative_results.json`、`negative_console.log` 及每项目录。未无限扩展安全测试；没有阶梯异形适配结论。

## 保存与剩余边界

最终完整性检查 `final_integrity.json` 为true：冻结ZIP/145成员未改，原STEP仍256758字节且SHA256为 `4e1ef4ec483c1b9b0d5c77e78a04afaa7c4b1acc83a62820f4c638d8d4d5698a`；R03/R04/R05/R06旧证据812/550/806/226项全部未变，历史重建候选18文件SHA未变。仅读取指定blind_test原件，未读其余目录。未修改ASM550003；本轮未重新打开其模型做几何验收。

断线恢复后核查最后transport/proof操作已完整结束，再继续收尾；没有不确定或重复写入。无权限拒绝、无待审批操作。源审计部分阻断和工程试折/五金仍是真实边界；不能用正常数字齐套推导可投产。需要作者在新冻结包修复F1/F2，再交独立复验；本轮未自行修补后宣称原包通过。所有文件仅本地保存。

复现见 `R07复现步骤.md`；机器摘要见 `R07_results_summary.json`；完整本轮文件哈希见 `evidence_manifest.json`。
