# STEP钣金审核与可复现交付 / 完整技能

版本2.7.3 R10候选，独立复验待完成。R09独立验收因发布旧包删计划漏检不通过，历史冻结与失败证据保留。R08在两项漏检及列明范围独立复验限定通过，历史冻结不改。保留原单人商业使用许可，见COMMERCIAL-LICENSE.md；本包不扩大第三方CAD许可或用户项目授权。

本版为可独立解压的完整目录，不是增量包。包含实际两种矩形箱体的成形CAD、真实展开、逐件激光DXF、装配/爆炸STEP、三视折弯PDF、强制03回读、完整交付门禁、schema/模板、必要资产、回归及实际CAD作者自测脚本。使用范围及输入限制见references/box-generation.md。

依赖普通Python3.10+、jsonschema、ReportLab、pypdf、Pillow、NumPy；实际生成必须具备FreeCAD/SheetMetal及Poppler。03真实原生验证为交付必经步骤。第三方引擎、插件、厂家图纸、历史客户模型和聊天记录不随包分发，不依赖客户目录。

结构选择已接入intake/schema/生成器/校验，U+L及bottom_l有明确角色；每计划钣金件恰一份制造DXF。显式用户结构选择优先，既有保护及无盖范围保留。条件默认g0.5和03、把手宽排85规则保留；q/Ri/裙高/机台BG不臆造；仅显式common_review_v1允许带来源的K/角缝试折候选。

支持范围内的可复现运行不等于所有agent/宿主/几何都绝对成功。缺依赖或非支持需求应BLOCKED。正根部交叠、未知材料批次、工装、回弹和首件保持HOLD；作者自测与独立agent验收分别报告。任何自动生成结果均不构成制造或批量放行。

从QUICKSTART.md开始。
R03新增保留源结构的既有STEP审计/展开/规范DXF/全源件审核折弯图册入口，严格BOP、真实partial及诊断隔离。支持范围见references/existing-step.md；不保证任意STEP制造完成。

R07强制独立身份/修订根目录、集中套料及预览、完整材料数量/逐弯工艺图册、BOM与完整性/ZIP门禁；源审计模式明确只出审核PARTIAL_HOLD。详见references/delivery-contract.md。

R07独立复验两项语义漏检不通过，R08新增源输入/实际STEP/PDF尺寸与封套数量权威交叉校验。新作者结果与独立R08复验分开报告。
