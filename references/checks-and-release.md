> R07新尺寸订单必须validate_delivery.py REVISION_ROOT成功，自动归档BOM/套料/完整工艺PDF/哈希及ZIP；旧manifest PASS不足以声明R07齐套。见[delivery-contract.md](delivery-contract.md)。

# 文件检查与放行边界

同一参数文件及其canonical SHA、版本和时区绑定所有下游。修改后标相关证据stale；不得把另一候选通过记录带进当前版。缓存无关件可保留字节SHA，重绑定当前版需有不变参数/几何证据，不要求因排版重建CAD。

1. 源原件：本次附件身份、单位/换算、SHA、有效实体/厚度/尺寸/孔与源干涉；同名历史不能代读。
2. 成形与装配：逐件有效性、实体数、尺寸链、孔轴/朝向、每对正体积干涉；爆炸仅刚体变换，回读复位后形状与数量保持。
3. 真展开：保存展开体/面、外圈/孔/弯线和来源；厚度、折数、孔数与映射一致。展开失败可交审计/成形阶段，不交伪CUT。
4. CUT：实际文件回读，纯CUT、非空、mm、Z0、闭合外圈、无重复、孔数/径/位置、净面积/对称差与真实展开面一致。R12基础LINE/ARC/CIRCLE优先；兼容转换不得静默损失曲线精度。组合排布不是套料。
5. PDF：第一页明确实际单边g、盖内对盒外长宽总差、独立q及03/角缝/Ri来源和HOLD；按实际scope出总体/分件三视尺寸、复杂角部/剖视、真实展开、孔表、二次加工、折序/补偿基准、装配爆炸及状态。无盖不出虚构盖页。逐页渲染检查乱码、重叠、裁切、尺寸与孔表，保留最终PDF SHA及页图。
6. 封包：参数和文件清单、每文件SHA、ZIP CRC与解压逐项SHA；报告可验范围、假设、剩余工厂事项及真实本机路径。未成功上传不说已上传；拒绝的上传不绕过或反复尝试。

证据等级分开：theoretical；digitally_checked（指定文件/几何链）；first_article_checked（指定材料、机台、工装的首件实测）；production_released（有权限、范围和时间的批准）。普通JSON/schema/链接/ZIP合规只证明格式和包结构。脚本从不签发生产证书；即使所有输入字段齐全，仍需实际CAD、独立CAM/机台或现场证据。没有新的批准，不因数字检查通过自动提升等级。

03不能只验标签：实际STEP重展开、DXF两斜边四角及PDF矢量轮廓/首页见[lid-defaults03](lid-defaults03.md)。

四孔梯形把手宽排条件默认85.00mm，其他孔距/排距/孔径不推定。参数实例、导出STEP/DXF真实孔心回读和报告绑定见[handle85](handle85.md)。

v2.8.2：发布前 11 项核验与自动门禁对照见[v2.8.2规则§8](v2.8.2-delivery-rules.md)；`scripts/release_package.py` 的 release_gate.json 写入 EVIDENCE，FAIL 不打包。
