# R12 材料描述与工厂材料码

本轮完整技能版本2.8.1/R12，修复材料命名、用户显式裙高精度及来源记录；新建工程核心为2.8.1-R12。既有项目的源工程版本、CAD、job、PDF材料说明和现场授权不因仅更名发布而改写。当前隔离候选未安装全局；R11独立验收已失败，R12固定CN03快照有界作者实际回归已完成，独立复验尚未执行，见[R12作者报告](R12-author-report.md)。

## 根因与适用范围

R10/R11把命名材料段当成原始材料描述，要求精确相同又禁止空格。因此source_job.material="201 stainless steel"既不能编码201，也不能把完整描述放入材料段。这是软件缺陷，不能全归责缺编号。冻结R11同样受影响，保留原冻结包和独立失败证据。

新请求优先使用material_code，旧material字段仍表示命名代码（与material_code同时出现必须相等），不是用于改写源job的材料描述。

```json
{
  "channel":"S",
  "material_code":"201",
  "material_mapping":{
    "source_description":"201 stainless steel",
    "code":"201",
    "confirmed":true,
    "source":"本项目用户/工厂确认的具体消息或文件引用"
  },
  "thickness":"1.0",
  "date":"20261023",
  "number":423,
  "factory_version":1,
  "source":"工厂本次分号及编码信息的具体引用"
}
```

数字423仅为测试格式例，不能给BOX530/420或其它客户分号。缺编号/日期/工厂v/渠道保持未命名待确认，不猜、不跳过统一发布；缺材料转换确认同样待确认。应读取missing_fields和material_identity，不把待确认前缀当正式主码完成。

源描述本来已经精确是201、304、Q235等安全代码时，可以直接使用同码，不需要虚构描述转换。已有R10合法exact-code或pending输出继续只读核验，仍强制默认完整ZIP计划和全部门禁；新发布统一标publisher_release=2.8.1-R12。

## 显式映射与拒绝规则

assets/process/material-code-aliases-v1.json只有201/304/Q235的列明名称别称，用于文件命名，不是材料性能、材质证明或牌号标准认证。描述201 stainless steel、304 stainless steel、Q235 carbon steel转换分别要同项目明确确认和来源。大小写/重复空白仅用于识别列明别称；证据必须精确保存源描述字符串（包括其原字节内容），不能偷偷trim原job。

描述未列明、未知、含多牌号、304L/304、Q235B/Q235不同后缀，不按数字子串猜。未确认则pending；显式试图确认未知别称/冲突则阻断并要求澄清实际材料。安全的自有材料码若与源值精确相等，可保留同码，不能借此给未知描述套201。扩展其它描述需新增有审查记录的命名适配规则，不能复制示例材料。

material_mapping的source_description须精确等于当前源job.material，code须等于请求代码，confirmed=true且source非空才可转换；已知201→304/Q235即使填confirmed也拒绝。代码字段互相冲突拒绝。软件保存确认引用但不能证明提交的确认引用真实，不能代替用户/工厂负责或认证材料。

## 证据及发布绑定

命名记录保存原始request、material_identity：原描述/其SHA、代码、别称策略SHA、明确确认引用、规则状态。原job完整字节及CAD/DXF/授权哈希继续由既有发布证明绑定；不编辑原job躲材料校验。升级工厂v仍保留前五段，不能更换材料码、日期、编号、厚度/渠道冒充升版。

新映射必须绑定当前R12发布标记；把新映射发布记录三份标记同步降回R10仍拒绝。原有不含新扩展的合法R10命名记录可只读核验，不放松默认投递计划、ZIP、数量、材料/厚度/几何检查。最终默认仍只交一个完整ZIP；套料DXF、套料预览、完整折弯PDF和所有件均共享正式主码+用途后缀。

## 调用

新项目：build_general_package.py BRIEF --output NEW_ARCHIVE --naming NAMING.json；完整显式job仍可build_package.py。

已生成受支持完整交付：publish_named_delivery.py SOURCE_REVISION --output NEW_ARCHIVE --naming NAMING.json，只写新副本，并运行完整门禁。已有客户本轮不执行改名，仅使用纯合成订单验证。未命名候选也必须经发布入口，不能直接散发旧文件。


仅更名发布保留源PDF原字节，不能因此宣称采用最新 `cn-workshop-dimensioned-v1` 中文尺寸模板；模板状态、源工程版本和发布版本须分别核查。最新作业册、默认15、独立角缝候选和安装顺序见[R12中文作业册](R12-CN-workshop.md)。安装须冻结、独立通过、备份旧版及链接、同哈希安装、新调用验证，不能用材料命名测试通过代替完整出图验收。
