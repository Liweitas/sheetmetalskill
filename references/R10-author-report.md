# R10 发布契约漏检修复与作者验证

版本v2.7.3 R10。作者限定验证通过，独立复验待完成，production_release=false。R09独立验收的真实失败保留，不将其历史改成通过。

## 根因

R09公开publish_named_delivery发布R08旧包时保留源制造契约2.7.1-R08；check_envelope却只在manifest.delivery_contract等于包内VERSION（2.7.2-R09）时强制默认投递字段。删封套final_message_plan/message_dispatch_contract后变成不检查，导致真实已命名发布产物的完整门禁错误通过。

## 修复

新增publication_contract.py，将当前发布契约named-single-zip-v2、发布实现版本2.7.3-R10在封套、清单/ZIP内的manifest和命名记录三处绑定，命名记录另绑定源制造契约。发布器实际升级这一层，保持原制造契约、project/PDF版本和CAD/DXF/PDF/job字节。这样没有通过虚改工程版本破坏原CAD/PDF/授权或假称重新制造。

门禁依据命名记录、实际正式码/待命名目录、artifact文件名和发布字段识别发布产物；不因源是R08而免检，不依赖可删除的单一声明。凡发布产物必须有默认单ZIP计划；三处发布契约/版本不一致、删除或降级也拒绝。检查在昂贵CAD读取之前先阻断错误发布字段，正常产物仍完整运行实际CAD/原生展开/方向/干涉/数量等门禁。

兼容边界：合法原始未发布R08可以只读核验，返回LEGACY_UNPUBLISHED_READ_ONLY，不称为R10命名发布。旧R09合法命名包有默认计划时，可以作为公开发布器的升级源；源仍实际核CAD/文件/计划，再出当前发布副本。原失败副本缺计划，入口即拒绝，不静默补计划洗成通过；未升级R09命名包不直接作为当前正式发布通过。单跑几何manifest不替代validate_delivery完整发布门禁。

## 实际作者验证（不是只有单测）

1. 不改原字节，直接用R10 validate_delivery重放R09独立失败目录：返回2，DISPATCH_REQUIRED_PUBLISHED。原失败输入2个字段缺失均以明确投递政策拒绝，不是简单按旧版号全拒绝。
2. 两份合法原始R08结构均返回0、fresh_CAD_checks_executed=true、源契约R08保留及LEGACY_UNPUBLISHED_READ_ONLY。
3. 通过公开publish_named_delivery实际完成R08正式首发、工厂v1到v2、缺字段待命名，以及合法旧R09命名副本升级4例。目的包完整CAD/文件门禁均通过，三处发布契约为v2/R10，源制造契约仍R08；18/18/16/18个全部CAD/DXF和job保护文件字节未变。原输入75/69/76/76共296文件哈希前后相同。工厂编号均TEST ONLY；未给BOX530分号。
4. 基于实际正式/待命名/升版输出构造19反例，均实际调用validate_delivery或公开发布入口，返回2：三类产物分别删除计划/投递契约/两者9例；封套发布契约/发布版本单改2例；三处同步降级且重绑清单/ZIP、删除全部发布标识和计划并重绑、连命名描述也删后重绑、仅删全部发布标识但保留计划、源制造版本伪报并重绑5例；同消息/跨消息散发2例；缺计划旧失败包试图再发布洗白1例。版本与SHA/ZIP同步改写反例仍按语义拒绝，不靠陈旧哈希碰巧拒绝。原正常发布源文件未变。
5. 实际prepare_delivery_message公开CLI四例：默认0、跨消息散发2、明确当前单PDF测试例外0、先确认图测试例外0，正常路径实际CAD核验；未发消息。
6. 267单元测试通过，包含原命名/投递/参数规则及8项发布权威用例。制造/授权核心算法8文件与R09逐字节相同；版本路由只追加R10，绘图仅版本标记。没有重复建模，没有改Ri/g/q、材料、K、孔或工厂命名规则。

证据：actual_R10_publications/AUTHOR_PUBLICATION_RESULTS.json；actual_R10_negative_cases/AUTHOR_NEGATIVE_RESULTS.json；actual_R10_message_CLI/AUTHOR_MESSAGE_CLI_RESULTS.json；unit-R10.log；R10_AUTHOR_SUMMARY.json。以上均在本报告同级项目根。原独立报告和failure_proof.json保留原件，复制到新包作为历史失败证据；没有读取其它会话日志。

## 限制和交接

原BOX530 ZIP仍为SHA256 1c2acbe3598cfdc31dcd056e88990482e025089855dbffba68c4e26b453459b9；冻结R09仍de8a16066dc4a92a1866e0330a36e6450c800f418391e6200ff5b67e3f8dcc9d。全局未安装、未上传或发送附件。BOX530编号未知不阻断本轮软件测试，也没有从示例猜号。

保留实际干涉和本项目现场授权、试装/首件/工艺HOLD，软件与命名/投递检查不等于生产放行。没有全册重新目视或实折；CAD/DXF/PDF原字节复用，正常门禁实际回读。本轮不扩展阶梯异形、源STEP制造支持或保证所有agent遵守实际发送。完整候选单ZIP交父线程进行同一独立审查；只发完整包，不散发补丁。
