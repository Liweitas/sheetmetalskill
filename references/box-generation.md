> R12分层说明：本页描述底层显式job或历史审核适配器。新需求优先使用 [通用brief入口](general-process.md)；其盖裙缺省固定15mm、Ri缺省0.8mm、单边g缺省0.5mm，q按本款条件计算为待确认候选，来源须保留。显式值优先，旧项目不套默认。完整中文加工册见 [R12中文作业册](R12-CN-workshop.md)，本页旧式审核PDF不代表最新制造齐套。

> R07新齐套归档/板材/数量及完整ZIP门禁见[delivery-contract.md](delivery-contract.md)，优先于本页旧单次output路径说明。canonical参数schema保留2.4.1；程序版本为2.7.0。

# 新箱体完整运行契约 / 2.4.1

## 支持的实际几何

统一单位后max(L,W)≥H：沿X通长的侧—底—侧U，两块X端封板；否则：三面竖向U围（左、后、右），内置底—前侧L。请求有盖时加一个03盖。显式method可覆盖尺寸默认。件数不含五金。新生成的拼缝、圆角、端板轮廓由当前参数决定，不能把候选结构当焊接/折弯工艺认证。

当前可运行适配器为矩形开口薄板盒体、单层圆柱90度弯、外包式四裙03盖、直壁/平板处明确声明的圆形通孔。它不自动生成箱口内折边、台阶、压平、扣锁、压铆、沉座、把手实体、复杂槽或CAM排样。这些要求不得从客户需求中删除：缺对应真实CAD适配器就BLOCKED，不能以基础盒代替。

U+两端板：U两折；封板零折，底部圆角随U外轮廓，沿X拼缝按seam_gap。U围+L：U两折；L一折，L底板嵌入U内，后角按当前Ri/拼缝避让。具体孔轴在装配基准内按job声明。默认U方向是此基础适配器的明确实现，不是所有产品的通用工艺默认；客户另有方向、内折20等要求时需要新适配器。

## job 输入

使用references/job.schema.json或assets/templates/box-job.blank.json。空模板的null用于显式阻断，不能直接建模。

- id：安全文件标识；units默认mm，可为mm/cm/m/inch，所有线性参数和hole.point/diameter同时换算。
- dimensions.length/width/height：盒体名义外L/W；有盖height为闭盖金属外高H，无盖为裸盒高。不含把手五金。
- material、thickness、Ri、K_ANSI、seam_gap：当前明确材料和名义几何/补偿输入，无工厂标定承诺。seam_gap必须小于Ri。新输入只支持ANSI K法，旧参数适配器仍保留直接BD法，禁止重复补偿。
- lid_required：必须声明。true要求lid.skirt_height、corner_gap、roof_gap；Ri+t<裙高<裸盒高，0≤角缝<Ri。新项目g未覆盖时仅默认单边0.5mm，corner_scheme未覆盖时默认03。q没有默认，必须明确。当前CAD适配器仅03，非03显式覆盖会保留并BLOCKED，等待相应经过验证的适配器。
- 裸盒高=有盖H−t−q。g是盖内直壁至盒外直壁，独立于q。输入Ri0.8、g0.5、q0可能发生根部正交叠；实际求交保留数值；无本项目授权阻断完整交付，有明确现场修配授权则按site-fit.md交付并待试装，不能改q/g/Ri求通过。
- method可显式u_external_ends或u_wrap_bottom_l。record_kind默认new；existing必须显式method和rebuild_existing_authorized=true，有盖还须显式g与corner_scheme，防止旧单套新默认。永不改原CAD或覆盖旧输出。
- holes可省略，表示无声明孔，不能把客户要求的孔省略。每项id/part_id/diameter/point/axis，point为装配mm基准中明确选定的板面孔心；axis为单位法向量。允许的归属由结构决定：U、END_L/END_R或L，以及适用时LID。实际STEP须找到两处同轴圆边且间距等于t，曲面孔或异常贯穿会BLOCKED。孔表中的切孔直径必须有当前来源，M4不自动补孔径。

material/t/K等job值是用户名义输入，不是实测批次或机床标定；未知项应询问/阻断依赖步骤。运行模板不是历史客户样例，未给任何订单通用Ri/K/q/角缝/裙高默认。

## 同源执行与门禁

build_package.py调用同一选择器，生成canonical project（schema2.4.1兼容2.4/2.2），并实际调用cad_build.py。每件成形STEP有效、单实体且导出回读匹配；弯件用SheetMetalNewUnfolder.getUnfold，零折封板对真实轮廓刚体转平；核折数、平坯t、孔数直径。将实际DXF重新建面，与原生展开及导出的展开STEP做双向面积差，当前容差1e-5 mm²。

03盖另调用native03_check.py从已导出成形STEP重新真实展开，检查4折、8斜边、按本件t/Ri/角缝/BA计算的镜像坐标、展开STEP/DXF面积一致、实际盒体根部交叠与q。body STEP为必需输入。缺模块、失败、缺报告/文件或SHA不符均不能通过。

manifest要求每计划钣金件恰一份制造DXF，完整请求覆盖各分件STEP、装配/爆炸及PDF。new_design的每件DXF绑定实际CAD/原生展开报告和STEP/DXF SHA；03另绑定盒体、native报告、PDF首页与实际轮廓矢量。排样预览不能代替逐件制造DXF。

普通validate_project仅检查参数，不执行CAD；旧记录允许参数审计HOLD，但cut阶段有盖必须有角方案、根部及几何证据。release仍需要独立工厂/首件/批准，不由生成器设置。

## 输出与边界

PDF来源于实际导出STEP投影和实际DXF，含装配/爆炸、逐件三视尺寸、真实展开、折弯中心坐标/BA/BD、实际03角部放大。折线坐标、BA/BD及从裙自由边量入的几何中心都不是实测机台BG。当前接口不接受机床BG或现场验收的臆测替代值。

每页PDF强制渲染PNG，仍需执行agent逐页目视。几何检查成功状态为GEOMETRY_CHECKED_WITH_HOLD，不是制造或批量放行。所有输入/输出文件哈希、CAD版本、原生报告和首件事项应随交付保留。运行失败退出2，只可把部分文件作为带BLOCKED诊断的中间产物。

完整技能无外部客户目录、旧聊天日志或历史模型依赖；依赖路径可只读发现或由命令行提供。先做普通软件回归和selftest_cad作者实际测试，再另由无历史上下文agent使用冻结包验收。

## R02补充

外端板支持end_inset（默认0：端板盖U、不留缝隙、不退让，用户 t16u，2026-10-26；仅本单明确给值才非0）：在YZ轮廓向内退让，与沿X的seam_gap独立；底角半径为Ri+t−end_inset，与U外圆同心。默认上边也退让，明确end_top_flush=true则上边齐口。原生展开厚度采用真实板面与圆柱的交叉测量，不以03斜角短边代替，见[厚度规则](thickness-measurement.md)。常用安装孔/周边孔、试折候选和来源状态见[配置规则](common-profiles.md)。

完整输出另有由实际STEP三角面生成的装配/爆炸确认PNG。部分失败写BLOCKED_RESULT.json，列stage、全部部分文件哈希、若已进入CAD则列已实际核过的成形/展开件；这些不能当完整交付。成功才写RUN_RESULT。
