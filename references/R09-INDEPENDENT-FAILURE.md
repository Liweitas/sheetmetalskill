# R09 独立验收报告

**结论：本轮不通过，发现1项默认投递门禁可被删除的真实漏检。** 正常统一命名、单ZIP计划及多数定向反例通过；不把这些局部通过扩大为原冻结包全部通过。未修改被验代码，未上传、发送附件或更改BOX530原包。

## 对象与范围

冷解包对象：`step-sheetmetal-delivery_v2.7.2_full_candidate_R09_20261023_1232.zip`，422748字节，SHA256 `de8a16066dc4a92a1866e0330a36e6450c800f418391e6200ff5b67e3f8dcc9d`。完整SKILL、命名/投递契约和公开入口已读；verify_install核167项，最终与ZIP168个非目录成员逐字节比较未变。未读取作者259单测/11投递/6命名通过报告作为预期答案，未以作者自测代替独立结果。

本轮仅用新包支持入口发布已有R08两种结构的副本，不重新生成CAD；完整门禁仍实际重新读取CAD/原生展开/尺寸/干涉。没有重新目视50页旧图册，改为独立核PDF字节不变。所有工厂编号、材料及例外请求均明确SYNTHETIC TEST ONLY，不是客户/BOX530实际分号或发送授权。BOX530只按“渠道S、编号未知”测试规则，不读取/改名/重建其原包；未额外核读图片libfile，规则来自本次明确文字要求。

## F1：R09发布旧包后，删默认单ZIP计划仍获完整通过

先用R09的公开 `publish_named_delivery.py` 对R08合法包做正式测试命名发布，成功且默认计划存在；源制造契约保持 `2.7.1-R08`。复制此新发布目录，仅删除其交付封套的：

```text
final_message_plan
message_dispatch_contract
```

命名记录仍在、所有命名合法；除该封套外所有文件逐字节相同，ZIP哈希也相同。R09 `validate_delivery.py` 对此副本实际返回：

```json
{
  "ok": true,
  "contract": "2.7.1-R08",
  "validator_version": "2.7.2-R09",
  "message_dispatch": null,
  "fresh_CAD_checks_executed": true,
  "digital_deliverables_complete": true,
  "production_release": false
}
```

精确失败目录：

`named_negative_cases/remove_default_plan_from_R09_published_legacy/customer_INDEPENDENT_R08/revisions/S-304_TEST_ONLY-1.2-20261020-0427-v1_R01/`

原始返回：`named_negative_cases/remove_default_plan_from_R09_published_legacy.stdout.json`；最小字节差证明：`failure_proof.json`。不是绕过发送器另发消息的不可控行为，而是送检的R09命名发布产物缺少默认投递计划时，完整文件门禁仍接受。

根因：`scripts/delivery_contract.py` 的check_envelope仅在 `manifest.delivery_contract == VERSION`（当前2.7.2-R09）时强制投递字段；R09支持入口publish_named_delivery保留源R08契约，因此其新发布、已有命名记录的产物可走旧版缺字段宽容分支。计划存在时会检查，删除计划却变成不检查。建议作者在新版本为“R09发布/命名产物必须有默认单ZIP计划”建立不能被删除的判定，同时继续允许原始未发布R08包只读几何兼容；本轮没有实现补丁。

边界：明确提交的散发/跨消息计划仍被正确拒绝，prepare_delivery_message默认也会生成单ZIP计划。本失败不证明脚本实际散发附件，也不推定原生R09新CAD生成路径同样能删字段通过；实证范围是新包明确支持的“旧完整包命名发布副本”。

## 已通过的命名与发布检查

通过新包公开发布入口实际生成4个副本，均执行完整CAD门禁：

| 情形 | 实际结果 |
|---|---|
| 首次S线上测试码 | S-304_TEST_ONLY-1.2-20261020-0427-v1_R01 |
| 升版 | 前五段不变，v1→v2，内部仍R01；旧v1保留 |
| X线下、内部R02 | X-304_TEST_ONLY-1.2-20261020-0432-v1_R02，未误作v2 |
| 仅渠道S，缺正式字段 | UNNAMED_PENDING_CONFIRMATION、code=null；未补0001或v2 |

独立检查全部文件、目录与唯一ZIP共享正式码/待确认前缀，套料CUT、套料预览PDF、完整折弯工艺PDF的用途后缀明确，所有basename无冲突。ZIP仅一个本修订顶层，74/74/68/68成员，CRC、清单覆盖、成员SHA和实际文件字节一致。ZIP排除自身及外部封套以避免循环，包含文件清单与命名记录。例外消息计划放修订目录外。

所有成形/展开/装配/爆炸STEP、分件/套料DXF及源job在发布前后逐一字节一致，四件式保护18项、三件式16项；PDF与历史log也保持原字节。更名只改文件名/JSON路径与依赖哈希，现场专项授权原job设计绑定未变。升版没有重取今日日期或重置编号。同目标发布冲突实际退出2 `NAMING_DUPLICATE_OUTPUT`，未覆盖、自动加号或分配工厂编号。

独立直接调用命名规则验证12项：S/X正例、升版正例、改日期/编号升版拒绝、不增v拒绝、材料/t与源不符拒绝、缺编号待确认、内部R02不映射v2、BOX530模拟缺编号不分号、无效日历日期拒绝。全部符合预期。`BOX530_model_only`仅是规则夹具，不是实际客户模型验收或分号。

证据：`publish_results.json`、`independent_published_readback.json`、`naming_and_dispatch_results.json`、`duplicate_output_check.json`。

## JSON与同内容log哈希分叉

原R08 `evidence/LID_native03_20261022_2047.json` 与 `native03_execution_20261022_2047.log` 的SHA相同。R09发布后JSON因引用重绑改变SHA，log仍保持原SHA，三个首次/待确认副本实际发现并核验此分叉，完整门禁均通过。不是仅比较作者记录：独立从原文件分组找相同SHA，再逐项读取发布后的JSON/log和manifest。

四件式原SHA e265a0137b1129ed99a65235721c832c395cd4eb5409d106608ca44253a8b0fc；发布JSON SHA 078b761271489af450aea3c4c827abc354a0937665ff25ceb62ffd16d4f2b79f；log仍为原SHA。三件式对应证据亦列在independent_published_readback.json。新版只由改写JSON推导依赖映射，没有把同原SHA的未改写log错误覆写成新的JSON依赖。

新命名副本的同步PDF尺寸＋回执＋SHA/清单/ZIP伪报，被HEADER_AUTHORITY_MISMATCH拒绝；命名请求材料改Q235且刷新清单/ZIP，被NAMING_MATERIAL_DIFFERS_SOURCE拒绝；合法同步重打包通过。它们证明新路径实际可运行且语义拒绝不是陈旧哈希偶然命中。上述F1依然漏检，详见 `named_negative_results.json`。

## 投递计划与公开CLI

直接在实际发布产物上验证14项计划：默认一条消息一个完整ZIP通过；ZIP+PDF同消息、ZIP/PDF跨消息、无请求只发PDF、重复ZIP均拒绝。明确当前单件/确认图测试请求通过；旧请求current=false、错客户/ZIP哈希、未索要路径、缺原文、确认阶段夹入制造PDF均拒绝；明确索要两文件的测试例外可按两消息发送，符合新用户明确例外优先规则。

另通过公开prepare_delivery_message CLI实际复测4项：默认0、跨消息散发2、明确当前单PDF测试请求0、先确认图测试计划0。它们没有发送任何消息。完整默认计划的附件仅一个ZIP；例外保持独立计划，不替换完整包内默认计划。

程序只能检查提交的整次计划、范围和实际附件SHA，不能证明自然语言授权真伪，也不能看到执行方隐瞒或另发的消息；本轮不声称所有agent必然遵守。测试授权均明确TEST ONLY，无真实发送授权。证据：`plans/`、`public_message_cli_results.json`、`naming_and_dispatch_results.json`。

## 旧几何、授权、HOLD没有弱化的抽测

R09直接只读验证原R08两合法结构均通过。R08保留的4份同步反例——PDF首页尺寸、实际三视尺寸、封套套数、板数——全部按对应语义拒绝；R06两份UP/+90实际弯向伪报仍从源CAD读回DOWN/−90拒绝。源STEP审核目录仍SOURCE_AUDIT_ONLY_PARTIAL_HOLD，完整门禁拒绝；材料/K未知未升级。

改孔后的旧专项修配job通过新包resolve_job仍 `SITE_FIT_SCOPE` 拒绝；实际命名发布三件式的source job与授权绑定原字节不变，保留真实2.292783 mm³权威干涉、现场修配/试装未确认和production_release=false。没有把用户接受的修配干涉当本轮软件失败，没有改Ri/g/q或重建CAD求通过。

独立R08→R09脚本差异索引及逐文件diff保存在当前目录。cad_build、方向读回、STEP尺寸读回、site_fit等核心几何/授权脚本字节未改；发生变化的旧制造/图纸脚本主要为版本支持及路径适配，并以实际旧反例重放核对，而非只信diff结论。详见 `replay_core_results.json`、`changed_hole_authorization_check.json`、`own_script_diff_index.json`。

## 完整性与剩余工作

final_integrity=true：冻结ZIP/解包成员未改；R03–R08旧证据812/550/806/226/1416/913项共4723项未变；18个历史候选SHA未变；唯一授权的原STEP仍256758字节及原SHA。BOX530原包未打开/改名，全局技能未替换。本轮只写acceptance_R09独立目录，无权限拒绝、无待确认或不确定操作。

所有定向工作已完成，不等待长任务、不扩大测试。剩余是作者修复F1并提供新冻结候选，再独立重放该失败、合法旧包发布与默认/例外计划；本轮不自改代码后宣称原包通过。报告仅本地保存，由父统一交付一个完整技能ZIP，不散发多个附件。
