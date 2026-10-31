# R05独立验收：部分通过，方向复核仍有真实漏检

2026-10-22；本地根目录：`/Users/harryma/Documents/Codex/2026-10-21/task-6/acceptance_R05`。

**结论：不予两项范围整体通过。** 现场修配的项目/设计绑定、保留实际几何及未试装状态的主流程通过本轮正反例；正常生成的两类结构与已有STEP PDF也确有真实轴测图，B编号、弯轴、原生方向和平坯关联通过独立核对。但是，新箱体和已有STEP两条输出复核路径均接受了“实际DOWN/−90°，输出同步伪改成UP/+90°”的反例。另有一项较小的干涉数值口径差异需明示。

未修改源码、原件、作者候选或旧证据；全部反例只动本轮输出副本。未上传，也未向外部用户/应用发送产物。没有权限拒绝、待批或结果不确定的动作。本文供父线程交付判断。

## 1. 冻结包与使用边界

ZIP：`/Users/harryma/Documents/Codex/2026-10-20/task/sheetmetal-v2.6.0-root-fit-repair/dist/step-sheetmetal-delivery_v2.6.0_full_candidate_R05_20261022_1012.zip`。

大小290510字节，SHA256 `1f1cf1faa5478aa768298a15f9f970e77ea23e09af039541d125ea9f93d1d312`，均匹配指定值。全新目录解压121条目；包内verify_install核120文件完整，最终逐ZIP成员字节比对零修改、CRC正常。公开依赖探测成功：FreeCAD1.1.1/OCCT7.8.1、SheetMetal0.8.21、networkx3.6.1及Poppler。没有全局安装或插件源码改动。

先读完整SKILL.md及QUICKSTART、site-fit、formed-isometric、box-generation；按其支持入口record_site_fit/build_package/audit_step/validate_manifest/validate_source_manifest执行。作者交接只用于定位，不采用其中PASS、预期页数、体积或测试结果作为判定依据，没有读取author-tests结果文件或运行作者selftest。包外仅使用公开CAD依赖、指定原件及此前自己生成的独立L形STEP/旧失败证据，当前工作流没有作者目录/客户模型依赖。

当前用户现场修配原话仅作为本项目授权历史保留；本轮没有将其绑定到猜测的客户job。两个新正例的授权source/quote明确写成`SYNTHETIC TEST DATA ONLY`，ID也为SYNTHETIC_INDEPENDENT_R05_*。它们是软件测试夹具，不代表真实客户授权，不传播到003、ASM0027或其它项目。

## 2. 有效正例：真实流程已跑通

| 本轮输入 | 实跑结果 | PDF | 关键事实 |
|---|---|---:|---|
| 外端板结构：196×126×86，t1.2/Ri0.8，g0.5/q0；U+双端板+盖，3个测试孔 | 退出0，DELIVERED_FOR_AUTHORIZED_SITE_FIT_WITH_HOLD | 19页 | U/LID各有自己的实际成形轴测，2+4个原生B记录；实际正干涉2.2241212179141057mm³保留 |
| U围+底侧L：96×76×166，同t/Ri/g/q，3个测试孔 | 同上 | 18页 | U/L/LID各有自己的轴测，2+1+4个原生B记录；逐件交叠和2.019099125183112mm³保留 |
| 既有STEP独立合成L：40×20×20，t1/Ri1，1个D3孔；显式测试K0.4 assumed | 退出0，AUDIT_COMPLETE_WITH_HOLD | 9页 | 实际成形轴测、B1 DOWN/−90°、40mm长原生弯线及其平坯标记对应 |
| 指定ASM0027原件默认材料/K未知 | 退出2，PARTIAL_HOLD | 17页 | 原框及原盖各有真实轴测；原生方向UNKNOWN、无假B方向；原盖BOP失败仍失败，原框缺制造补偿仍BLOCKED |

全部production_release=false；现场修配两个正例中assembly_interference_free=false、geometry_interference_eliminated=false、trial_assembly_confirmed=false。未为“求通过”调Ri/g/q、删交叠或切原件。

独立回读两种新结构实际圆柱内R均0.8、板厚1.2；四面直壁g均0.5（仅浮点尾差）、q为0（最大尾差约1.4e−14mm）。各正交叠均位于盖根区域，盒体件互相正体积交叠为0。明确接受现场修配的正交叠本身**不作为软件失败**；工厂物理修配/试折/五金仍另有验证边界。

首次准备U围夹具时误加了仅用于外端板的end_inset；入口正确阻断。已将自己的夹具改成不含此字段的新输入`wrap_l_valid.job.json`，保留初次失败日志，未修改包源码，也不把夹具输入错误算成包缺陷。

证据：`external/`、`wrap_l/`、`source_L_supported/`、`source_original_unknown/`及对应入口日志；`independent_fit.json`。

## 3. 现场授权范围与输出一致性

无授权的两类正交叠job均在CAD前退出2，提示LID_ROOT_FIT_REVIEW_REQUIRED，未创建成功交付目录。记录测试授权后，同一设计正常交付；引用原文/来源/设计SHA及待修配状态出现在PDF第1–2页和canonical exception、native03、最终结果中。

针对同一授权副本，以下7项均在CAD前被拒绝，输出目录未创建：去掉授权、换成003_OTHER_CUSTOMER_NOT_AUTHORIZED、Ri改0.9、g改0.6、q改0.01、孔心移0.25mm、授权中伪称geometry_interference_eliminated=true。旧授权没有被自动重签或复用。record_site_fit不能认证原文真伪，执行agent仍须核真实消息；本轮测试没有把模拟文字冒充客户来源。

输出副本再重绑全部相关SHA后，伪称最终已消除干涉、最终体积0/无干涉、授权PDF页空白、U轴测页空白、展开B坐标表改成B9，均被门禁拒绝。证据：`preflight_results.json`、`output_negative_results.json`及`output_cases/`。

**较小的数值一致性问题：** U围+L例中PDF首页及canonical root_overlap_volume采用逐件求交和`2.019099125183112`，RUN_RESULT/native03采用整体BODY求交`2.0190650778320265`，相差`0.00003404735108558654mm³`，约0.00169%。两处都诚实显示正干涉和待修配，绝非假报消除；但尚非完全相同的单一数字。源自两处分别求交的输出，具体数值差成因本轮未另作证明。建议统一显示同一口径，或同时标明逐件和/整体求交及允许差；不要通过改变几何来消除该差异。外端板例两处数值一致。

## 4. B编号、真实弯轴与坐标风险：独立核对结果

`independent_bends.py`没有调用包内formed_isometric的track_bends/records/validate_flat_link。直接回读实际导出STEP，独立测皮距并由同轴圆柱差验证厚度，调用原生getUnfold；在自己的进程中另行捕获本次圆弯面的实际点/轴和原生signed angle、SketchExtraction移动矩阵，结束后恢复函数，不改插件文件。

对外端板U/盖、U围U/L/盖及导入L共14个原生弯：

- 实际圆弯点到成形实体距离0、与输出记录点误差0，轴向一致；原生签名角均−90°，方向均DOWN，根面/法向也同一口径。
- 将原生第5返回值BendInfo.line先做本次草图逆变换，再做平坯规范化，14个B均唯一覆盖实际裁剪弯线；与实际展开STEP面双向面积差均0。
- **若省略草图逆变换，14/14个B均不能正确匹配实际平坯弯线。** 因而已实际重现已知坐标系风险；R05正常产物的修正有效，不是仅看字段存在。
- 每件实际STEP全部BRep边独立轴测投影，与保存投影最大差0。另写PDF内容流读侧核实际矢量线段：6个逐件轴测页共612段匹配，最大端点误差小于0.000067pt。
- 两类新结构所有13个B的展开文字锚点和B坐标表均由独立重展开线重算后匹配；导入L的B1也对应实际40mm长弯线，Y=19.099557428756427mm，PDF标记锚点误差约0.000026pt。

UP/DOWN始终是相对选定根皮面的原生符号，不是机床操作先后、冲头可达或试折合格。

证据：`independent_bends.json`、`independent_pdf_geometry.json`、`source_flat_anchor_check.json`及其日志。

## 5. 失败：同步伪报原生方向仍被接受

这是本轮阻止整体通过的主要问题，正常原产物未动。

### 新箱体输出反例

复制外端板正例到`output_cases/coherent_native_direction_flip/`：

1. 成形STEP、展开STEP、DXF、root_face/root_skin_normal和实际折线都不动。
2. 把U件B1/B2的记录从DOWN/−90°改为UP/+90°，同步iso报告与cad_report。
3. PDF的U轴测页和展开页B标记及signed angle同步改成UP/+90°；更新PDF/报告SHA与manifest。
4. 调用原包公开`validate_manifest.py`，真实返回退出0、ok=true、errors=[]。

同一未变成形STEP已在独立脚本中实跑原生展开，实际仍DOWN/−90°，因此接受的是错误方向，不是另一根面下的合法重新展开。

### 已有STEP输出反例

复制导入L正例到`output_cases/source_coherent_native_direction_flip/`，将source_audit中B1方向/签名角、SOURCE_DRAWING_GEOMETRY对应记录及PDF轴测/展开文字一起改成UP/+90°，更新全部SHA，保持源/成形/展开STEP与DXF不变。

公开`validate_source_manifest.py --expect-source-sha256 ...`真实返回退出0、ok=true；其中actual_geometry_readback.CAD_executed=true，说明即使进行了源CAD回读，仍未核BendInfo方向。实际B1原生值仍DOWN/−90°。

定位：新箱体门禁检查报告间、PDF文字与折线锚点的自洽，却不重新从实际STEP/所选根面取native signed angle；已有STEP实际回读检查平坯几何/折数/孔，但未比较输出bend_records的原生方向/签名角及实际弯轴关联。即使JSON+PDF一起错，现门禁会接受。

建议限定修复：在实际CAD复核中将当前成形STEP、实际root面/法向、原生圆弯轴/点、BendInfo signed angle、逆变换后的平坯线逐条关联，再比对输出B记录与PDF，不能只增加“方向字段存在”检查。本轮未修源码。

证据：`direction_counterexample_proof.json`；`output_negative_results.json`最后一项；`source_direction_case_result.json`；两份完整反例目录、stdout/stderr及`scripts/output_negatives.py`、`scripts/source_direction_case.py`。

## 6. R04核心回归与PDF目视

R05对R04合法L基线接受；对旧伪geometry_complete、伪AUDIT_RESULT、两倍DXF，以及BOP有效且展开STEP/DXF同步两倍的反例均拒绝。最后一项实际源/STEP面积差约240168.692917921mm²，而STEP/DXF差0，源锚定的防缩放没有回退。未扩展无关安全测试。证据：`core_regression_results.json`。

本轮4份PDF共63页（19/18/9/17）全部渲染并逐页目视，保留每页PNG、文字和联系表。授权测试来源/原文明确；全部折弯件轴测覆盖齐全；原件失败件方向UNKNOWN、M编号与原生B编号分开。未见实质中文缺字或页边裁切。线框“全部边可见”已注明，局部B标签靠近/叠在线框边上，建议留白或拉开引线，但本轮编号仍可辨。图册不是机台/首件放行。

## 7. 保全与交付给父线程

`final_integrity.json`：R05冻结包源码成员零变化；原件仍256758字节且SHA匹配；R03的812证据和R04的550证据逐项未改；旧候选18文件SHA未变；本轮4组正常run的清单绑定文件未改。所有失败保留在副本，未覆盖作者输出。

复现见`R05复现步骤.md`；重点先读`direction_counterexample_proof.json`与两个门禁ok=true的反例结果。当前无权限阻塞；剩余是方向复核缺口和数值口径问题。现场修配已接受的物理干涉不列为修复失败，工厂试折、五金及量产放行继续各自HOLD。
