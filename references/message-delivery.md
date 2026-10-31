# 统一主目录与最终消息投递（R09）

当前发布入口和最终门禁另强制[R10发布契约](R10-publication.md)；R09规则/目录是基础，原R09独立失败不改写为通过。

文件齐套和消息投递是两个检查对象。BOX530 的 R08 ZIP 已有统一目录、齐套内容和哈希，执行方仍把 ZIP 内各件另发，导致用户收到零散附件。发送方对此负责；R08 文档和代码也缺少默认附件计划约束。不能把这次发送问题说成制造文件缺失或 CAD 失败。

## 目录和默认发送

每客户/需求的每次修订统一为 `customer_ID/revisions/REV/` 或 `requirement_ID/revisions/REV/`。现有打包及覆盖检查已保证完整制造 ZIP 仅有该身份的一个顶层目录、一个修订前缀，所有本版资料在里面；历史版本隔离。不另建一堆孤立下载项代替完整包。

最终默认只发送该修订一个完整 ZIP；消息可简述版本、内容和 HOLD，不再自动附 PDF、装配/爆炸 STEP、分件 DXF、套料、报告或补丁。不得把同一套默认资料拆成多条消息继续散发。发送计划必须涵盖本次拟发送的所有消息和附件。生成器的 `DELIVERY_ENVELOPE.final_message_plan` 为一条消息、一个完整 ZIP，R09 的最终文件门禁检查该默认计划。

若用户询问最新技能完整包，同样默认仅发一个完整技能 ZIP，说明/测试报告可置包内；不自动发增量补丁或多个技能 ZIP。此条不把用户明确索要的单件拒之门外。

## 用户例外与优先级

用户当前明确要求单件时可以单发；要求先看确认图时可以先发本次确认图。确认阶段的文件不能伪称最终齐套交付，后续正式交付仍默认一个完整 ZIP。旧的“好了一个发一个”保留为用户曾给的要求，但与当前统一交付冲突时，当前更具体要求优先；不能凭旧要求继续散发。用户之后新的明确指示优先。

例外必须记录实际用户原文、可核实来源和本次身份/修订/ZIP哈希、确切请求文件。字段 `current_for_this_delivery=true` 仅为执行方声明；程序不能验证聊天真实性或判定所有自然语言冲突。不得编造授权或把某客户例外扩大到其他项目。

```bash
# 完整门禁（含实际CAD）+ 默认单包消息计划；只打印，不发送
python3 scripts/prepare_delivery_message.py /ABS/customer_ID/revisions/R02

# 检查拟发整次消息计划
python3 scripts/prepare_delivery_message.py /ABS/customer_ID/revisions/R02 --plan /ABS/send-plan.json

# 用户确实索要单件时；相对路径必须来自本版manifest
python3 scripts/prepare_delivery_message.py /ABS/customer_ID/revisions/R02 \
  --file PDF/EXACT_CURRENT.pdf --user-request /ABS/actual-user-request.json \
  --output /ABS/checked-send-plan.json
```

确认优先使用 `--phase confirmation --file EXACT_CONFIRMATION.png --user-request ...`；文件必须是本版 manifest 中的 confirmation_png/confirmation_pdf。当前制造入口的计划依附齐套包；尚未齐套的 formed-only/既有STEP审核继续按原审核流程输出并明确 PARTIAL/HOLD，不得伪造完整封套来用此检查器。确认优先的实际发送者须核对应审核文件和当前用户请求。

`actual-user-request.json` 的形状如下，内容必须换成实际用户证据和本次真实值：

```json
{
  "reason":"explicit_single_files",
  "quote":"实际用户索要本次单件的原文",
  "source":"实际消息来源",
  "current_for_this_delivery":true,
  "scope":{"namespace":"customer","entity_id":"ID","revision":"R02","archive_sha256":"本次完整ZIP的实际SHA256"},
  "requested_paths":["PDF/EXACT_CURRENT.pdf"]
}
```

先确认图时 reason 为 `confirmation_first`。程序生成 plan 包含 `dispatch_contract`、身份/修订、`archive_sha256`、`phase`、`messages:[{"attachments":[{"path","kind","sha256"}]}]`、`user_request` 和 `production_release:false`。缺当前用户证据、错范围、重复/未列文件、哈希不符、默认多个附件/多条附件消息都会拒绝。例外计划放冻结修订目录外，不改原完整 ZIP；例外不替换生成器的默认完整 ZIP 计划。

## 能保证与不能保证的范围

- 原完整文件门禁继续检查源参数、实际 CAD/展开/方向/干涉及专项现场授权、PDF/套料/数量、版本、清单和 ZIP；本轮不修改制造算法或生产边界。
- R09 生成入口实际返回默认单 ZIP 计划；完整门禁拒绝缺失或被改成散发的默认计划。独立提供的拟发计划须再次检查真实 ZIP 和附件，例外须有当前本项目用户证据。
- `prepare_delivery_message.py` 不上传、不发消息。它仅检查提供给它的计划；无法看到执行方另发或隐瞒的消息，也不证明授权文字真实，不保证任何 agent 必然遵守。实际发送者须把最终整次发送与已核计划逐一核对。
- 数字齐套、单包发送或本轮软件测试通过均不代表消除真实干涉、已试装或生产放行。保留所有 HOLD 和项目专项授权边界。
