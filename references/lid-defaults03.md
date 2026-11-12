> **v2.8.21 / 用户 t67u（纠正 t64u/v2.8.19）**：T/台阶盖与矩形盖均**默认斜角03**短裙端（+ g=0.5）；本页几何适用于缺省盖角。**连续等高校裙**仅用户明确「独立盖角取消 / 要连续裙」时启用；彼时经典 8 斜边 corner03/native03 门禁不得硬套到连续 T 盖上冒充通过。

> **v2.8.42 / 用户 t115u**：台阶盖 **两端外凸角可套 03**；**中间台阶拐角仍非 03**（45° V / 正方补件等）。native03 全盖 8 斜边门禁不得硬套中间台阶并伪造通过。

> R12分层说明：本页描述底层显式job或历史审核适配器。新需求优先使用 [通用brief入口](general-process.md)；其盖裙缺省固定15mm、Ri缺省0.8mm、单边g缺省0.5mm，q按本款条件计算为待确认候选，来源须保留。显式值优先，旧项目不套默认。完整中文加工册见 [R12中文作业册](R12-CN-workshop.md)，本页旧式审核PDF不代表最新制造齐套。

# 盒盖默认、覆盖与03真实几何

## 条件默认及来源

只对明确有盖的新项目激活：四周盖内直壁到盒外直壁的单边g=0.5mm，两个平面轴总差均为2g=1.0mm。这个口径不是盖外尺寸减盒外尺寸；盖外尺寸还涉及两侧板厚。配合方向、内外尺寸、基准和长宽轴必须明确。

新模板policies声明默认；范围未定时lid.gap仍null，理由是尚未激活。`create_intake.py --lid yes`激活默认，`--lid no`标不适用。值为status=default并引用default_policy来源；用户明确值使用自己的来源和requested/confirmed状态，不伪装为默认。总差输入保留原口径后归一为单边；显式单边1.0就是总差2.0，不能升级成0.5。

`migrate_project.py old.json --output new.json`只写新文件、标existing并保留原参数；不把新默认补进旧订单。经明确选择的新项目可用`--new-project`解析缺项。验证器只在副本中解析new项目默认，输入文件不改；`--resolved-output`可保存同一有效参数，不覆盖原文件。canonical参数SHA与有效默认一致，明确值与默认来源仍不同。

顶部落座间距q独立，无默认；g不设定q。Ri、t、角缝、裙高、K/BD/BG、硬件、公差及余厚标准也没有这次新增的默认。无盖不激活配合或盖角；不要为了默认规则新加盖或螺母。

## 03方案定义

本适配器针对四个90度裙边：长裙保全外长，短裙两端各退t+corner_gap；四个镜像角在折弯根部均有两段斜线。必须按当前实际/明确候选t、Ri、裙高、角缝和展开补偿重算。没有固定角缝或Ri。超出适配器几何范围须另用实际CAD设计，不能硬套。

记Ro=Ri+t，A=裙高-Ro，B=A+BA90。标准化左下角：P1=(B-Ro,A)，P2=(B,B)，P3=(A,B-(Ri-corner_gap))。四角镜像；短裙退让=t+corner_gap。第三点由实际短折弯端点展开推导，不能因某组历史数值碰巧相同而改用带固定板厚偏移的旧坐标关系。BA由当前K定义或直接BD制度计算，不能二次叠加。

`corner03.py`只做参数及实际DXF/矢量PDF几何检查，不调用CAD；它核四角各两斜边和当前参数坐标，不接受“文件名03但20直边0斜边”。`native03_check.py`是所有03盖交付的强制门禁，在宿主配置好的FreeCAD/SheetMetal Python中只读STEP、重新真实展开，核4折/8斜边，与提供的展开STEP和DXF做几何面积对比，并独立求盒盖/盒体交叠。缺模块、API不符或几何失败必须阻断，不当作通过。

## 出图与证据

执行顺序：保存有效参数→实际成形STEP→真实原生展开及展开STEP→实际CUT→原生重新展开核对报告→由实际DXF轮廓生成/回读PDF→目视。示意调用中的路径由当前项目提供，不带固定本机位置：

```bash
python3 scripts/corner03.py resolved-project.json --dxf actual-lid.dxf
python3 scripts/native03_check.py resolved-project.json --formed lid.step --unfold true-unfold.step --dxf actual-lid.dxf --body body.step --output native-report.json
python3 scripts/render_review_pdf.py resolved-project.json --output review.pdf --dxf actual-lid.dxf --native-report native-report.json --mapping-output pdf-map.json
```

native03_check要在已配置的CAD Python环境运行；可显式传模块路径，不安装或改全局配置。它只建立临时内存文档、不保存源模型。生成的审核PDF是参数/实际展开核对页，不冒充完整生产三视工艺图；实际三视、孔表、折序和复杂剖面仍按总检查清单输出。

清单中lid03的DXF项还需formed_step、unfold_step、native_geometry_report、geometry_pdf、pdf_flat_page_index及pdf_flat_map（6个PDF相似变换系数）。门禁读取实际斜边、绑定同参数/同SHA原生报告、核PDF首页与实际矢量轮廓。原生报告必须由本次真实CAD执行取得；清单读取绑定不等于重新执行CAD，也不是制造认证。栅格/Form或其它不支持的PDF绘图交另一个已验证适配器与逐页目视，不能说自动核验通过。

## g与R角不混用

四周直壁g达到默认不证明盖根圆弧不碰盒口。实际Ri、q和实体求交独立检查；正体积干涉、授权局部修整及首件事项单列，不能删交叠再宣称零干涉。未确认q、工装、试折、螺钉/压铆适配或验收标准继续HOLD。

2.4完整入口要求body STEP参与实际根部/q核验。缺报告、缺任一计划件DXF或缺绑定文件均阻断；不能只运行参数校验声称通过。新箱体统一入口见box-generation.md。
