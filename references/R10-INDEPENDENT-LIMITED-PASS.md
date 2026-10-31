# R10 独立复验报告

**结论：限定通过。** 原R09“命名发布旧R08后删默认投递字段仍通过”漏洞已按原始失败字节重放确认修复；本轮发布、删字段/降级、跨消息及旧门禁定向复验未发现新的同类逃逸。此结论只覆盖列明输入和路径，不是所有案例、宿主、agent或生产放行通过。

## 对象与方法

冻结包：`step-sheetmetal-delivery_v2.7.3_full_candidate_R10_20261023_1300.zip`，464519字节，SHA256 `19fc86d331e2f863d57e764f27b8a42a678c994223e601109baa7e86ef4e8cdf`。在全新 `acceptance_R10/package/` 冷解包，读取完整SKILL及R10发布契约后，使用新包公开支持入口。安装检查通过，最终对ZIP177个非目录成员逐字节核对未变。未修改作者代码或全局技能，未读作者自测通过报告作为预期答案。

本轮复用独立验收保存的R08实际成形/展开及R09发布包，只做命名发布副本和只读门禁回归，**没有重新生成CAD**。完整门禁仍实际读取CAD、原生展开和尺寸/干涉。命名、编号、材料、发送例外均为明确SYNTHETIC TEST ONLY夹具，不是真实客户或BOX530授权。未接触BOX530原包，未进入通用工艺参数分支。

## 原始R09漏洞与兼容边界

原失败目录完全只读，直接送R10 `validate_delivery.py`，实际退出2：

`DISPATCH_REQUIRED_PUBLISHED: source manufacturing version cannot waive the publication plan`

此目录仍是R09发布旧R08得到的副本，保留源制造契约2.7.1-R08，缺final_message_plan/message_dispatch_contract；没有为了复验修改版号或重打包。失败源再送R10公开publish_named_delivery入口也退出2，同一错误，不能静默补计划后洗成通过。

旧R09合法命名包直接用当前末端校验退出2 `PUBLICATION_CONTRACT_BINDING`，明确要求升级发布契约；但用R10公开发布入口重发布成功，制造原字节保持。原始未命名发布的R08两合法包继续退出0，返回 `LEGACY_UNPUBLISHED_READ_ONLY`，不会伪称当前发布通过。

证据：`replay_R09_results.json`、`replay_R09/`、`R10_repair_proof.json`。R09历史不通过报告和失败副本没有回写。

## 当前发布契约及定向强反例

当前发布副本将以下字段共同写入封套、被清单/ZIP覆盖的manifest和命名记录，制造版本继续保留原R08值：

```text
publication_contract = named-single-zip-v2
publisher_release = 2.7.3-R10
source_manufacturing_contract = 2.7.1-R08
```

独立实际副本测试结果如下。需要修改manifest/命名记录时同步刷新文件清单、ZIP和封套ZIP/计划哈希，避免把陈旧SHA拒绝冒充语义修复：

| 测试 | 实际结果 |
|---|---|
| 合法重打包副本 | 0 / ok=true |
| 仅删封套默认计划和投递契约 | 2 / DISPATCH_REQUIRED_PUBLISHED |
| 三处发布标记及默认计划全部删除 | 2 / DISPATCH_REQUIRED_PUBLISHED |
| 三处发布版本同步降为R09/v1，保留计划 | 2 / PUBLICATION_CONTRACT_BINDING |
| 删除三处发布标记并跨消息散发ZIP/PDF | 2 / DISPATCH_DEFAULT_ONE_COMPLETE_ZIP |
| 正常发布标记下跨消息散发ZIP/PDF | 2 / DISPATCH_DEFAULT_ONE_COMPLETE_ZIP |

正式码/待命名实际目录、artifact名称和命名记录仍被识别，不能仅因源制造版本旧或删封套字段而回退为不检查。原漏洞是内容检查拒绝，不是一律拒绝旧版。上述5项破坏输入全部拒绝，合法重打包通过。证据：`named_negative_results.json`、`named_negative_cases/`、`scripts/named_negatives.py`。

## 合法发布、命名与实际原字节

实际完成5个公开发布正例，并执行完整CAD门禁：

1. 原R08四件式首次正式S码测试发布。
2. 由该副本v1升v2，前五段不变、内部仍R01，旧版保留。
3. 原R08三件式X码测试发布，内部R02没有误作工厂v2。
4. 仅有渠道S、缺正式字段的待命名发布，code=null、UNNAMED_PENDING_CONFIRMATION，不分配0001或v2。
5. 旧R09合法命名包经R10公开入口重发布，得到当前发布契约。

独立读取发布前后文件与更名映射，逐项核CAD/DXF/job原SHA：四件式保护18项、三件式16项；全部PDF及历史log也保持原字节。目录、唯一ZIP及所有文件主码一致，套料CUT、套料预览PDF、完整折弯工艺PDF用途后缀正确，无basename冲突。五包ZIP仅各自一个本修订顶层，成员74/74/68/68/74，CRC、覆盖和逐成员SHA一致。ZIP包括清单和命名记录，自身与外部封套因自引用排除。

JSON/log同内容原SHA分叉继续正常：原生报告JSON在引用重绑后改变SHA，历史stdout log保持原SHA，未误将log哈希当改写JSON依赖。原始source job及专项修配授权绑定没有改动。五个副本均fresh CAD gate成功，production_release=false。

证据：`publish_results.json`、`replay_R09_results.json`、`independent_published_readback.json`。重名再次发布实际退出2 `NAMING_DUPLICATE_OUTPUT`，没有覆盖或自动加号。

## 默认投递与明确例外

独立12项命名规则和14项实际附件计划测试全部符合预期：S/X、升版、缺字段、材料/t匹配、日历、BOX530模拟缺编号；默认一条消息一个完整ZIP、同消息或跨消息散发拒绝；当前本项目单件/确认优先测试例外允许，旧请求、错范围/ZIP、未索要文件、缺原文及确认阶段夹入制造PDF拒绝。

公开prepare_delivery_message CLI的4项结果为：默认0、跨消息散发2、明确测试单PDF请求0、测试确认优先0。例外是修订外独立计划，没有替换封套默认单ZIP计划。所有测试只校验和打印，未发送任何消息或附件。

程序无法证明自然语言授权真实性，也不能控制执行方隐瞒、绕过计划另发消息；本轮不承诺所有agent必然遵守。BOX530实际编号仍待工厂/用户指定，本轮没有实际分号或改名。

证据：`naming_and_dispatch_results.json`（26项）、`public_message_cli_results.json`、`duplicate_output_check.json`、`plans/`。

## 旧几何、专项授权与HOLD回归

新校验器只读重放原R08两合法包通过；R08四份保留的PDF首页尺寸、实际三视尺寸、套数、板数同步伪报全部语义拒绝；R06新建/已有STEP两份实际DOWN/−90被同步伪称UP/+90反例仍由实际CAD读回拒绝。源STEP审核目录继续SOURCE_AUDIT_ONLY_PARTIAL_HOLD拒绝完整交付；本轮没有重新运行源审计或改源结构。

改孔后的测试专项授权job经R10 resolve_job仍SITE_FIT_SCOPE拒绝。已授权三件式命名发布保留源job及CAD原字节、Ri/g/q和实际正交叠，仍是现场修配/试装待确认HOLD，未把用户已接受的修配干涉当软件失败，未清零体积或扩大客户授权。

证据：`replay_core_results.json`、`changed_hole_authorization_check.json`、`own_script_diff_index.json`及逐文件diff。本轮不扩展到新的制造适配、阶梯异形或通用工艺参数体系。

## 断线恢复与完整性

恢复后先核已有结果，没有重跑已完成的发布/CAD/CLI测试。发现末端CLI四项、重名拒绝以及final_integrity均已完整落盘。前次断线简报“完整性命令未执行”的判断不准确，已按证据纠正；旧exec会话已不存在，完整结果文件及最后重名记录证明脚本已结束。细节保存于 `recovery_and_integrity_supplement.json`。

final_integrity=true：冻结包/177成员未改，R03–R09旧证据812/550/806/226/1416/913/869共5592项未变，18个历史候选SHA未变；唯一授权原STEP仍256758字节及原SHA。原4个发布副本manifest已核，恢复后另补第5个旧R09重发布副本的37项artifact SHA及三处发布标记核对。没有修改任何原CAD/DXF/BOX530或全局安装。

无剩余阻塞或不确定操作。结论仅可作为当前交付漏洞修复的已验证基础；制造K标定、材料批次、刀模/BG、现场修配、试折/试装、首件及生产放行仍各自HOLD。报告及全部证据只在本地保存，由父统一交付一个完整技能包，不散发多个附件。
