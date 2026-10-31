# 本项目现场修配接受（R05）

这条路径记录用户选择，不解决几何交叠。g 是直墙单边间隙，q 是盖内顶至盒体顶的独立间距。对本适配器的圆弯直边，0≤g<Ri 时理想不进入弧形材料的必要条件为 q≥Ri−sqrt(Ri²−(Ri−g)²)；这是相切条件，不是制造公差。Ri0.8/g0.5/q0 会产生已知根部冲突。脚本只显示该关系与当前体高 H−t−q，不自动改任何值。

没有本次用户授权：resolve/model 返回 USER_REVIEW_REQUIRED 提示，review_box.py 可做明确非完整交付的确认审核；build_package.py 在 CAD 前退出2，不能仅凭 HOLD 交付相交设计。

用户明确说本项目交由师傅修配时，先核对实际原文、授权对象及参数，再记录：

```bash
python3 scripts/record_site_fit.py /absolute/THIS_JOB.json --output /absolute/new-site-fit-record --authorization-source '本项目用户消息编号/日期' --authorization-quote '本项目用户授权原文'
python3 scripts/build_package.py /absolute/new-site-fit-record/site-fit.job.json --output /absolute/new-delivery
```

占位文字不是授权，不能直接复制为真实证据。工具不能认证用户文字真伪，执行 agent 必须从本次实际授权取得 source/quote。完整 job SHA（仅排除 site_fit_acceptance 本身）绑定材料、单位、尺寸、t/R、K、角缝、结构及孔等全部输入；变更任一输入或换客户后旧授权失效。schema 不提供全局接受、忽略碰撞或假装试装完成的开关。无盖项目不能附此授权。

运行仍须逐件有效实体/BOP、孔轴、真实展开、03及DXF闭合等检查。实际求交为正时仅接受盖弯根高度区域内的碰撞；盒体间相交及延伸到盖直裙下方的其它碰撞不能借此授权通过。原件拓扑无效、缺件或03不符仍阻断。现场修配接受不会传播到既有 STEP 审计，也不能替 ASM0027 g0 原件取得新授权。

完整格式可交付时状态为 DELIVERED_FOR_AUTHORIZED_SITE_FIT_WITH_HOLD；实际干涉量、assembly_interference_free=false、geometry_interference_eliminated=false、trial_assembly_confirmed=false 同时保留。PDF 首页写明干涉保留和待试装，授权页包含本次来源/原文/设计SHA；canonical exception、native03、最终结果及清单必须一致。legacy root_check_passed 只表示检查已执行、已记录，不代表零交叠；零干涉请读取 assembly_interference_free 与实测体积。

本次现场选择不确认材料、K标定、工装、首件或生产放行。若用户日后要求几何无交叠，再另出尺寸/避让影响方案，取得对应选择；不能使用本授权自动改变 g/q。

作者自测使用明确标记 SYNTHETIC 的模拟授权，仅验证软件正例，不是任何客户授权。通用包不预装真实客户授权或客户模型。独立测试应重测无授权、授权有效、改客户/孔/尺寸、假“已消除”及缺授权 PDF 等反例。
