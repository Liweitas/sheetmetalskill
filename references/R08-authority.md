# R08：PDF尺寸与最终数量必须有独立权威

R07独立验收不通过：真实源/CAD218×148×94，PDF与工艺回执同时改999×888、刷新SHA/ZIP后仍通过；封套sets999而源/BOM/套料/PDF为2也通过。原R07冻结包和失败目录完整保留，不重写历史。

R08从原source_job重新resolve本次尺寸、材料、t、数量和补偿，核对canonical项目，再重新生成应有的完整工艺首页文字。process_pdf.header只是回执，不能作为文字真值；首页及实际工艺总览均须符合重新推导结果。

完整门禁额外用独立只读Part.read加载本次实际成形分件、装配和爆炸STEP，核体外边界与源L/W/高度口径。每张实际三视的6个尺寸标注须与实际STEP外包尺寸相符，数值比较1e-5mm仅用于6位小数和CAD读回一致性，不是制造公差，没有改变现有几何容差。沿用R06原生方向、角度、孔/展开、权威干涉体积和专项许可检查。

最终封套sets必须与经过源输入约束的spec、canonical quantity_sets、全部BOM件数、套料sets完全相同；实际板数、板材来源状态、工程状态及待视觉/独立复验状态也交叉校验，数量类型不接受字符串或bool冒整数。封套虽因自引用排除在自身ZIP/清单外，仍必须做语义校验。

R08生成新包；只读验证兼容原R07正常包，以便原字节正例和失败反例直接重放，不能靠拒绝旧版本冒充修复成功。R08项目不得改标为R07降级。检查返回package contract和validator_version分开；check_cad=False只做传输/源参数检查，不声称完成实际CAD完整门禁。

复现：scripts/selftest_delivery_contract.py运行两结构、源partial和既有31项反例；scripts/selftest_receipt_authority.py REVISION_ROOT --output NEW_DIR额外制造PDF+工艺回执+SHA+清单+ZIP同步伪报、封套sets与板数伪报的副本，并验证合法重打包仍通过。副本保留原始输入、参数、所有成形/展开STEP及单件DXF字节。独立复验仍待新一轮完成；所有工艺/首件/投产HOLD不变。
