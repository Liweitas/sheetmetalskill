# R08 独立复验报告

**限定通过：R07两项真实漏检已修复，本轮定向复验未发现同类逃逸或合法包误阻。** 此结论仅覆盖下列实际输入、公开依赖、两种受支持矩形结构和已执行反例，不是全适用或生产放行结论。冻结包、源码、全局技能、原件、旧证据与正常产物未修改；没有上传。

## 对象与独立性

冷解包：`step-sheetmetal-delivery_v2.7.1_full_candidate_R08_20261022_2044.zip`，366880字节，SHA256 `fe318c7b1ca9a0a0468aae99708b8a60db9d4e7b790c1a8395ba4b6b1c245129`。本地测试根是当前 `acceptance_R08/`，包位于 `package/step-sheetmetal-delivery/`。已读完整SKILL、QUICKSTART、齐套契约及R08权威修复契约；作者复现文档仅用于入口定位，未读取/引用作者230 tests通过结论作为验收依据，未运行作者自测替代独立检查。

verify_install实际核151项；最终对ZIP的152个非目录成员逐字节比较均未变。运行依赖实际探测为FreeCAD1.1.1 / OCCT7.8.1 / SheetMetal0.8.21 / networkx3.6.1，普通Python、pypdf、Pillow及Poppler；依赖是外部公开安装项，不是包内自带CAD。沙箱Qt探测初次报NEON限制，经正常本机隔离执行审批后成功，未发生拒绝或绕过。

## 原R07输入直接只读重放

新包validate_delivery直接读取原R07字节，没有改版号、重打包或迁移：

| 原输入 | 实际返回 | 判定 |
|---|---|---|
| 四件式R01 | 0 / ok=true | 合法包通过 |
| 三件式R02，保留测试专项修配 | 0 / ok=true | 合法包通过 |
| 四件式另一修订R02 | 0 / ok=true | 合法包通过 |
| 合法重打包副本 | 0 / ok=true | 合法包通过 |
| 原F1：PDF999×888、源/CAD218×148×94，回执/哈希/ZIP同步 | 2 | PROCESS_PDF_HEADER_AUTHORITY_MISMATCH |
| 原F2：封套999套、实际2套 | 2 | ENVELOPE_SOURCE_QUANTITY_OR_STATE_MISMATCH: sets receipt=999 source=2 |
| 原源STEP审计目录 | 2 | SOURCE_AUDIT_ONLY_PARTIAL_HOLD |

合法返回保留 `contract=2.7.0-R07`，另列 `validator_version=2.7.1-R08`，fresh_CAD_checks_executed=true并给出实际STEP尺寸读回，因此不是一律拒绝旧版来掩盖问题。详见 `replay_R07_results.json`、`replay_R07/`。原R07仍保持其历史不通过结论，不回写历史报告。

## R08新生成与真实内容核对

独立合成输入明确标SYNTHETIC，材料304_TEST_ONLY、t1.2、Ri0.8、K0.4 assumed，不是客户材料证书。三件式通过record_site_fit支持入口记录明确TEST ONLY专项授权，不能用于真实客户或ASM550003。

| 路径 | 源尺寸口径 | 数量与实际套料 | PDF |
|---|---|---|---|
| customer_INDEPENDENT_R08/revisions/R01 | 盒体外长宽218×148，含盖高94，q0.2 | 2套×4件=8件，2张600×450 | 工艺24页＋套料2页 |
| requirement_INDEPENDENT_R08/revisions/R02 | 盒体外长宽112×82，含盖高174，q0 | 3套×3件=9件，3张600×450 | 工艺21页＋套料3页 |

两次build_package均退出0，完整交付校验再次退出0。同修订重复生成退出2 REVISION_EXISTS，原文件哈希不变。两结构manifest的22类产物一致，确认图/分件/装配/爆炸STEP、分件真展开CUT、集中套料CUT、预览PDF、工艺PDF、BOM、参数、孔表、回读证据、清单和ZIP均齐全。独立核清单72/66文件、ZIP73/67成员，覆盖/CRC/字节一致，见 `independent_transport.json`。

独立测量脚本不导入包内bbox、尺寸或PDF权威帮助函数，直接Part.read实际STEP：

- 各制造分件有效且严格BOP通过；实际盒体外包为0..218/148、0..112/82；盒体顶分别92.6和172.8，与H−t−q一致。
- 外盖总装包络分别221.4×151.4×94和115.4×85.4×174；每侧相对盒体增加g+t=1.7，未与“盒体外长宽”混为同一口径。装配/爆炸体积与分件之和在数值范围内一致。
- 共11张实际三视页，**66个尺寸标注**逐项与独立STEP外包核对通过，包括分件、整装与爆炸图。数值比较1e-5mm是CAD/六位打印读回容差，不是制造公差。
- 13个弯直接重新getUnfold，核实际圆柱弯轴、signed angle、原生B编号、根面及sketch逆变换、平坯折线/点、实际成形轴测PDF向量；展开面积差0，未把BendInfo第5返回值直接充当平坯坐标。
- 正常PDF首页与工艺总览材料/t/尺寸/数量对应源输入，逐弯实际基准距离、候选折序和盖裙信息正确；机台BG、刀模/V槽/首件未知保持空白或待核，不伪造投产。
- 套料独立ASCII回读显式INSUNITS4、毫米1:1、纯CUT，实际实体多重集/孔/件数等于分件平移副本；无重复实体，最小边距12、保守矩形件距8。封套套数、实际DXF板数、BOM、spec和layout一致。

证据：`independent_dimensions.json`、`independent_dimension_quantity_checks.json`、`independent_bends.json`、`independent_pdf_geometry.json`、`workshop_readback.json`、`independent_nest.json`。主要两结构的工艺/套料合计50页已逐页目视，中文交接和工艺信息可读，无明显缺字/裁切；主CAD视图仍含英文标题/注记，密集表建议A3/放大。没有声称全中文化或按纸测量；见 `PDF_visual_review.json`、`visual_sheets/`。

## 新同步强反例

全部只在新输出副本修改。源job、canonical参数、成形/展开/装配/爆炸STEP与分件DXF保留字节，PDF回执、manifest、PDF哈希、完整清单、ZIP和封套ZIP哈希同步刷新，避免把陈旧哈希拒绝冒充语义校验。

| 副本 | 实际返回 |
|---|---|
| 合法重打包 | 0 / ok=true |
| PDF首页＋工艺总览999×888，header回执同步 | 2 / PROCESS_PDF_HEADER_AUTHORITY_MISMATCH |
| U件实际三视215.400000标为999.000000，哈希/ZIP同步 | 2 / ACTUAL_DIMENSION_AUTHORITY: PDF_ACTUAL_STEP_DIMENSION_LABEL_MISMATCH: U |
| 封套sets999，实际2 | 2 / ENVELOPE_SOURCE_QUANTITY_OR_STATE_MISMATCH |
| 封套required_stock_sheets999，实际2 | 2 / ENVELOPE_SOURCE_QUANTITY_OR_STATE_MISMATCH |

详见 `negative_results.json`、`negative_cases/`、`scripts/negative_cases.py`与`negative_remaining.py`。三视反例证明门禁实际将打印标注与新读STEP比对，而非只相信同步JSON/SHA。原两缺陷由source_job重新resolve并核canonical/header及数量链约束，单凭PDF回执自洽不再足够。

## HOLD、方向、专项授权及诊断

R06两份保留的UP/+90同步伪报真实反例，经新建/既有STEP门禁均实际CAD读回DOWN/−90并退出2。新测试授权job改一孔后，build_package在preflight退出2 `SITE_FIT_SCOPE: job id or exact design SHA changed`，未进入制造写出，旧授权没有跨设计继承。见 `legal_and_core_results.json`、`changed_hole_authorization_check.json`。

三件式独立布尔实测BODY/LID正交叠 **2.292783468825668 mm³**，与canonical/native/final/worker四处权威值一致，PDF显示2.292783；逐件和2.2928202366940686仅作诊断。Ri/g/q保持0.8/0.5/0，状态为DELIVERED_FOR_AUTHORIZED_SITE_FIT_WITH_HOLD，geometry_interference_eliminated=false、trial_assembly_confirmed=false、assembly_interference_free=false、production_release=false。**实际保留的干涉不是本轮软件失败。** 测试专项授权不构成真实客户许可。

独立额外记录的三件式整装和爆炸示意复合严格BOP均有SelfIntersect诊断，各制造分件BOP通过；诊断完整保留在 `independent_dimensions.json` 和attempt日志，未改几何求通过。整装正交叠符合上述明确保留的修配情形；爆炸图是视图布置，不据此承诺其布局零交叠或可装配。此轮限定验收不扩展为消除既有爆炸示意交叠的任务。四件式整装/爆炸BOP通过。

指定原件asm0027_asm.stp通过R08的audit_step重新实跑，退出2，SOURCE_AUDIT_ONLY_PARTIAL_HOLD；材料/K未知，部分真实展开/诊断、源BOP与闭框限制按槽位保留，完整制造齐套入口明确拒绝。没有切开源件、重拆件或改参数求通过。证据 `source_entry.log` 和 `archive/requirement_SOURCE_INDEPENDENT_R08/revisions/R01/`。

## 测试脚本修正与完整性

独立测试工具的失败尝试没有隐去：首次三视反例寻找218标注未匹配（U实际宽215.4），保留构造失败目录/日志后新建215.4反例成功；独立测量曾因先import Part退出139、误把盒体长宽当盖总装包络、对保留交叠的复合装配作零交叠断言，以及PDF旋转文字空白匹配过严而停止。对应attempt脚本/日志均保留，修正的是独立测量工具及预期口径，未改候选/几何/公差。最终成功结果才纳入通过计数，未执行成功的构造不计反例通过。

final_integrity为true：原STEP仍256758字节、SHA256 `4e1ef4ec483c1b9b0d5c77e78a04afaa7c4b1acc83a62820f4c638d8d4d5698a`；R03–R07旧证据812/550/806/226/1416项全部未变，18个历史重建候选SHA未变。只读指定blind_test原件，未读其它blind_test内容，未修改ASM550003。无上传、无权限拒绝、无不确定或待执行操作。

本轮可以接受两项缺陷修复及列明的输出稳定/内容约束；实际材质批次、K标定、刀模/退刀/机台BG、五金、现场修配/试折/试装和首件仍需工程确认。不对阶梯异形、所有模型/宿主/agent或生产放行给出泛化承诺。精确复现见 `R08复现步骤.md`，机器摘要 `R08_results_summary.json`，全证据哈希 `evidence_manifest.json`。
