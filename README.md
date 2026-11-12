# step-sheetmetal-delivery

Version **2.8.46** · [Liweitas/sheetmetalskill](https://github.com/Liweitas/sheetmetalskill)

核验 STEP 与钣金要求；为两类矩形箱体生成分件/装配/爆炸 STEP、真实展开激光 DXF 及三视折弯 PDF，强制核验 03 盖角和完整交付；也用于既有项目审核及窄改，纯格式转换不适用。

本次同步以 2026-11-12 的 27 服务器部署目录 `/mnt/DATA/harry/fc-skills/step-sheetmetal-delivery/` 为准。保留原仓库提交历史；代码、测试、模板和红蓝 PDF 金样来自该部署快照。`VERSION` 与 `SKILL.md` 元数据统一为 2.8.46，文件清单重新生成。

当前出图入口为服务目录中的 `sm golden`，实际执行本仓库的 `scripts/build_golden_package.py`。支持 201 不锈钢的 U＋两外封端板＋03盖，以及 U围＋L＋03盖；包含盖顶把手、端板把手孔方向、圆孔和支持面上的矩形开孔。尺寸、孔位和适用范围以输入校验为准。

在已配置依赖的运行环境中调用：

```bash
python3 scripts/build_golden_package.py BRIEF.json --output /ABS/new-job/out --naming NAMING.json
```

每单使用独立的父目录，入口会在父目录内创建 `pipe/`，输出目录不得已存在。正式图号必须显式提供。27 上仍可使用现有 `/mnt/DATA/harry/sheetmetal-api/sm golden` 包装命令；MCP/HTTP 服务代码另行部署，不属于本 skill 仓库。

PDF 统一使用 `assets/bend-pdf-golden-001-visual/` 的五文件引擎与 SHA256 门禁；旧生成 CLI 已退役，旧库函数保留供审核和回归。当前门禁通过不代表历史 R10 完整制造合同验收通过，输出仍为确认稿，`production_release=false`。

依赖包括 FreeCAD、SheetMetal、Python 库、Poppler、GNU time 和可嵌入的中文字体，均不随仓库分发。运行时路径由 `SM_FC`、`SM_FCLIB`、`SM_AV`、`SHEETMETAL_PATH`、`SM_CJK_FONT` 指定；详见 [QUICKSTART.md](QUICKSTART.md)。

```bash
python3 -B -m unittest discover -s tests -v
```

从 GitHub 下载源码 ZIP 并解压后，可运行 `python3 scripts/verify_install.py` 校验完整文件清单；Git 工作目录中的 `.git/` 不属于发布包。

本次同步范围与验证结果见 [同步记录](references/repository-sync-20261112.md)。许可沿用 [COMMERCIAL-LICENSE.md](COMMERCIAL-LICENSE.md)。
