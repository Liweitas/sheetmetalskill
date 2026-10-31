# R09 单包投递与工厂命名修复、作者验证报告

结论：本轮作者限定验证完成，完整候选待独立复验；不是生产放行，也不保证所有agent实际发送行为。

## BOX530投诉的准确原因

BOX530原ZIP SHA256为1c2acbe3598cfdc31dcd056e88990482e025089855dbffba68c4e26b453459b9。单一顶层requirement_BOX530_PG7_HANDLES/revisions/R02，88成员、87清单数据，CRC/清单/各artifact及ZIP成员字节全部一致；4分件CUT、2BEND、套料DXF、套料PDF、完整工艺PDF及装配/爆炸/分件STEP等在内。原生成齐套并未缺ZIP。父会话又把包内各项分两批逐个发送，这是发送方行为失误，不能全推给技能。

R08 SKILL.md:14规定完整ZIP；references/delivery-contract.md:26、49–53规定归档/齐套；scripts/delivery_contract.py:212–215、250–256实际保证ZIP单一身份/修订目录和成员覆盖，但没有默认最终附件数量、消息计划或单件例外规则。这是技能指令/投递接口的缺口，不是此次CAD制造缺件。

## 实现

R09新增delivery_dispatch.py、prepare_delivery_message.py，生成封套实际提供默认一个完整ZIP计划，最终门禁强制检查。外部拟发整次消息可送检；默认ZIP+PDF、单件STEP、多条附件散发均拒绝。当前用户确实索要单件/先确认图时，须提供本次原文/来源、身份/内部修订/ZIP哈希及文件范围。旧“好了一个发一个”不覆盖当前统一交付；先确认图不等于最终散发。脚本不上传/发送，也不能证明授权原文真实或看见被隐瞒的后续消息；发送方仍负责。

新增factory_naming.py、naming.schema.json及publish_named_delivery.py。主码为S/X-材质-板厚-YYYYMMDD-四位编号-vN。材料/t绑定原需求，日期有效、1补0001、范围1–9999、v正整数。工厂编号是否重置及全局唯一性归工厂；同目标拒绝覆盖，不自动分号。工厂v独立于内部R02；升级保留前五段。缺字段/空字段为未命名待确认，code=null，不猜正式码。BOX530只有S被用户确认，没有采用示例0001；本轮对该箱只做隔离测试副本，不作为新正式交付。

生成入口在私有工程阶段后发布同一主码副本；套料DXF、完整折弯PDF、套料预览PDF以及所有其他文件/唯一ZIP/修订目录均同码前缀，后接中文用途/零件/板号。更名映射、相对引用、参数引用哈希、JSON依赖、manifest/清单/ZIP重绑，原CAD/DXF与原始job字节保持。原始job不加入命名字段，从而不擅自改变现场授权设计哈希。正式工厂命名范围是已有完整受支持制造包；既有源STEP未知材质/K/闭框等审计模式维持PARTIAL_HOLD，不能借命名发布升级齐套。

## 实际验证

- 259单测通过。BOX530原包9项只读运输/消息正反例符合预期；正式更名R09包11项符合预期，包括缺PDF、多个顶层、错ZIP修订、默认散发、用户明确单件/确认图、删除默认计划。
- 合成X-201-1.2-20261023-0007-v1首发、v2升版及BOX530渠道S但缺编号的待命名副本，均重新执行实际CAD/完整文件门禁。17/17/19个全部CAD/DXF及原始job保护文件逐个SHA相同，源目录所有文件不变。新版本前五段不变；目的目录重复被拒绝。0007/X仅合成输入，不是BOX530编号/渠道。
- 6个命名反例拒绝；其中分别去掉主工艺PDF、套料DXF、套料预览PDF的主码，已同步路径引用、manifest/SHA/清单和ZIP，仍由NAMING_ALL_FILES_REQUIRE_SHARED_PREFIX拒绝。缺命名记录、错材质Q235、错目录同样拒绝。
- 更名包合法重打包通过；原R08的PDF尺寸+回执同步伪报、实际三视标注、999套、999板四反例仍拒绝，未拿旧哈希拒绝冒充语义防护。实际prepare_delivery_message CLI通过，返回一个完整ZIP。
- 生成入口衔接用已完成CAD及原finalize作为缓存fixture执行execute，再对命名后的目的完整包实际CAD核验，返回engineering.project/manifest/pdf均指向真实更名文件。此项明确不是重新从零CAD生成的冷测。最初唯一一次合成CAD完成后因漏改三视PDF版本标记被门禁阻断；保留原失败，修正标记后在新副本只续PDF/打包，不重复建模。后续更名全部复用几何。

详细证据与路径见同目录R09_AUTHOR_SUMMARY.json；包内references/R09-author-summary.json保留摘要。版本差异见R08_to_R09.diff。制造核心cad_build/corner03/cut_dxf/native_direction_readback/pdf_dimension_authority/step_dimensions_readback/site_fit/record_site_fit字节与R08完全相同。native03/manifest只追加R09版本路由，数值/展开/方向/授权算法未变；绘图代码仅版本标记。保留所有失败目录，没有把构造失败计通过。

## 交接边界

原BOX530、冻结R08、客户几何和全局安装未改；BOX530编号仍待用户，不阻碍通用技能验证。已有干涉、现场专项授权、K/材质来源和试折/首件/HOLD按原件，不因命名或单包检查变生产通过。人工逐页视觉/实折确认与本次软件回归分开；本轮没有另做全册视觉验收。没有上传或对用户散发补丁/报告。父线程可先据准确原因回答，再安排完整候选独立复验；用户要技能时只发一个完整ZIP。
