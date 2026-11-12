# 2026-11-12 仓库同步记录

目标仓库：<https://github.com/Liweitas/sheetmetalskill>，分支 `main`。GitHub 旧地址 `TaoSeekAI/sheetmetalskill` 已重定向到同一仓库，仓库 ID 为 `1440402422`；本次在原提交 `4a5a0d0acf472b17a8ffdb7aff2ebd0fb5472aa1` 上追加提交，保留历史。

## 来源与范围

来源为 27 服务器的 `/mnt/DATA/harry/fc-skills/step-sheetmetal-delivery/` 实际部署快照。本机安装目录与27存在差异，因此本次采用27的整套代码，不混入本机未部署的分角计算、独立展开 worker 或测试草稿。

快照共345个文件；排除临时 `SKILL.md.backup-20261107-171312-pre-2.8.46` 和误存字体 `--help`。缓存、Git 元数据和客户任务产物不进入发布清单。历史参考资料及其验收日志保留。

所有158个 Python 源文件与27快照逐字节一致，包括测试文件；几何、展开、校验、打包及 PDF 引擎均未在本次同步中改写。额外变更只涉及 README、当前入口文档、CHANGELOG、VERSION、忽略规则、本记录和完整文件哈希清单。`SKILL.md` 原已标记2.8.46，`VERSION` 原仍为2.8.45，本次统一为2.8.46。

## 本轮验证

测试在27的隔离目录 `/mnt/DATA/harry/sm-jobs/repo-sync-20261112/skill/` 中运行，未覆盖实际部署。

| 检查 | 实测结果 |
|---|---|
| `python3 -B -m unittest discover -s tests -v` | 399项，398通过，1失败；0错误，0跳过；5.868秒 |
| 当前金样五文件SHA256 | 5/5与`GOLDEN_SCRIPTS.sha256`匹配，且与27部署版一致 |
| Python源文件语法及来源比对 | 158个文件语法通过，全部与27快照原字节一致 |
| JSON文件 | 全部可解析 |
| `git diff --check` | 通过 |

唯一失败为 `test_user_rules_t52u.TemplatesEmitWarning.test_u_l_t7u_pdf_readme`：历史 `pipelines/u_l_t7u/make_bend_pdf.py` 缺少测试要求的“约1扣有效螺纹”等薄板M4警告文案。用同一 Python 环境对27原部署的 `test_user_rules_t52u.py` 复核，7项中同一项失败，0错误，0跳过，确认同步前已存在。该历史模板不作为当前统一服务PDF引擎；当前入口及金样另有警告生成逻辑。本次保留失败，未修改运行代码或删除测试来宣称全绿。

完整源码清单及SHA256见根目录 `PACKAGE-SHA256.json`。该清单对下载源码ZIP解压后的发布文件有效，不包含 `.git/`、缓存或清单自身。

## 未执行及限制

本次未重新建模、重出订单PDF、运行完整R10制造合同验收或实物试折试装；既有图纸验收状态不变。未覆盖本机安装版、27实际部署或MCP/HTTP服务代码，未重启服务。此提交用于版本归档和源码同步，不是生产放行；`production_release=false`，独立验收仍待完成。
