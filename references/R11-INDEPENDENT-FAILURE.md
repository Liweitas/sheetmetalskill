# R11 独立复验：不通过，限定范围

日期：2026-10-23。仅本地验收，未安装全局技能、未修改作者冻结包/客户图/历史证据，未上传。本报告依据独立执行结果，不采用作者测试结论。材料名称映射缺陷已另交作者后续版本处理；冻结 R11 不变。

## 已确认失败 F1

用户显式输入 `lid.skirt_height=12.34 mm`，公开入口编译为 12.4 mm，参数来源仍写 `origin=user`、`needs_confirmation=false`。实际生成的盖 STEP 高度为 12.400000000000006 mm；PDF 第22页写盖裙外高12.4，第23页仍称“用户指定”。构建退出0，公开 `validate_delivery.py` 也退出0。

这不是显示精度差异：源意图、实际几何已改变。根因位于 `scripts/general_process.py` 对默认和显式 skirt 一并执行 `math.ceil(skirt*10)/10`。冻结源码未修。证据：`F1_explicit_skirt_failure_proof.json`、`inputs/explicit_decimal_skirt.brief.json`、`explicit_decimal_skirt_resolve.stdout.json`、`explicit_decimal_skirt_build_result.json`、`independent_geometry.json`、`decimal_PDF_skirt_readback.json`、`public_gate_results.json`。

## 已实际完成

| 范围 | 结果及证据 |
|---|---|
| 冷解包 | 544481字节，SHA256 `9c72490c3a0567fdd2f9104f7b5c224941edc0372ad60f27acf4f8ef4f4f2897`；完整技能已读；安装自检见 `install_check.json`。末次逐成员与冻结ZIP比对无差异。 |
| 16组编译输入 | 最小输入、默认来源、显式无孔无把手、两结构选择/显式覆盖、无盖、cm内尺寸转换、相等长高选型、材料未知、q冲突、缺关键输入、异形、K证据跨材料、裙高越界、无工厂记录的投产请求、错误设计绑定记录均执行。见 `resolve_results.json` 与 `additional_resolve_results.json`。显式小数裙高为F1失败，其余已检查分支符合相应HOLD/拒绝边界。 |
| 四组真实CAD | 外U+两端板+盖236×156×98/t1.2；U围+L+盖122×104×186/t1无孔；显式参数245×163×109/t1.2（F1）；无盖138×96×73/t1。均由公开入口生成STEP、真实展开、套料、PDF、清单、ZIP。均为合成测试，工艺证据/编号夹具不是真实客户授权或工厂认证。 |
| 独立几何回读 | 四组实际 `Part.read`，各分件严格BOP；装配与爆炸件按平移匹配原分件，对称体积差为0。实际尺寸/孔圆柱面/主体盖干涉均保存，见 `independent_geometry.json`。无孔例实际CAD未检出完整圆柱孔面。 |
| 独立21道折弯 | 外U6、U围7、显式参数6、无盖2。直接原生展开核实际弯轴、根面法向、方向/角度、B编号、实际BEND实体与展开坐标；原生展开与存储平坯面积差0；实际轴测投影误差0。已处理第5返回值与平坯坐标不同的变换风险，见 `independent_bends.json`。 |
| 四组限制路径 | 材料未知、显式q=0干涉：实际成形确认资料，不生成DXF；缺关键输入/异形：确认清单不生成CAD。四组确认资料自检退出0，完整制造交付门禁均退出2 `GENERAL_CONFIRMATION_ONLY_HOLD`。见 `public_gate_results.json`。 |
| 正常门禁与强反例 | 四组生成包公开交付门禁均退出0；其中显式裙高仍为F1，退出0不能覆盖源意图错误。正常重封装副本退出0；同步改封套伪造工厂等级退出2；真实BEND整体偏移1mm且同步记录/哈希/清单/ZIP退出2；真实装配STEP漏盖且同步引用/哈希/ZIP退出2。见 `negative_results.json` 及 `negative_cases/`，原产物未动。 |
| 等级/HOLD | 三组默认完整数字候选仍confirmation_draft、manufacturing_delivery_complete=false；无盖试折夹具为evidence_based_trial，所有production_release=false。未实际工厂试折，不宣称投产放行。 |

## PDF检查的实际边界

已统计12份主工艺/主确认/套料PDF共109页，见 `PDF_inventory.json`。现有联系页已生成；人工抽看14张联系页，39个不同页面，覆盖两结构首页、三视、装配/爆炸、盖展开与03角、真实轴测、中文逐弯说明、参数来源、未知材料/q冲突、缺资料/异形和两张套料预览。未逐页精读全部109页，不能声称全页审图通过。

抽看可见中文材料/板厚/数量、尺寸口径、方向角度/坐标、顺序候选、盖裙、刀模/BG/首件待填及HOLD。主图仍保留英文标题和技术字段，参数长列表较密；仅可确认所看页面可显示，不给“所有车间人员一次理解”的普遍保证。F1在PDF中复现。可复用图片在 `visual_sheets/`；本轮不再新增渲染。

## 命名/发布与未完成范围

本轮四组真实输出包括三份待命名和一份测试正式码 `X-Q235-1.0-20261023-0573-v1`；公开门禁实际检查单ZIP发布计划、源尺寸数量、库存/ZIP及当前发布合同。测试编号0573仅为合成夹具，不是客户正式编号。未重放全部历史R06–R10反例、未重建BOX530/客户异形件、未对现有源STEP再做一次全流程，也未重新独立计算所有套料实体间距；这些不列为本轮新增通过。既有专项现场修配授权不扩展到其他项目。

本机生效与四客户包命名审计已完成，详见同级目录 `../installation_naming_audit_20261023/本机生效与命名只读审计.md`：当前全局实际仍2.3.0；R10只在隔离任务使用。BOX530旧包未走待命名发布；另外三份为待命名候选，不能把内部R02/R03当工厂v2/v3，不能猜0001。材料描述与正式短码映射问题另列于该报告。

## 精确阻塞及保留记录

独立测量初稿曾因compound无CenterOfMass报错，仅修正自己的测量脚本，原失败日志保留。磁盘耗尽曾在结果落盘阶段失败：已核对既有JSON后只恢复尚未保存的两例测量，没有重复已完成CAD生成。日志见 `decimal_geometry_attempt1.log`、`normal_geometry_ENOSPC.log`、`remaining_geometry.log`。

收尾时再次出现 `zsh: can't create temp file for here document: no space left on device`，该读取命令的Python未启动。改用不需临时文件的只读命令后可核既有证据；空间随外部活动波动，末次可用约323MiB。按父要求暂停新增大型副本/渲染，未删除任何数据。剩余为未执行的扩大回归、全109页逐页精读及工程现场认证；不影响F1真实失败结论。
