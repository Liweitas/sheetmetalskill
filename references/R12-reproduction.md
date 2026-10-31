# R12 复现与独立验收入口

解压后先读QUICKSTART.md，配置公开依赖并执行 `python3 -B scripts/verify_install.py`。以下输出目录必须未存在；测试编号0423仅合成夹具，不得给客户分号。

```bash
python3 -m unittest discover -s tests
python3 -B scripts/build_general_package.py assets/examples/general-explicit1234.brief.json --output /ABS/new-F1
python3 -B scripts/build_general_package.py assets/examples/general-default15-t1.brief.json --output /ABS/new-t1 --naming assets/examples/general-material201-synthetic.naming.json
python3 -B scripts/build_general_package.py assets/examples/general-default15-t2-baseline.brief.json --output /ABS/new-t2-baseline
python3 -B scripts/build_general_package.py assets/examples/general-default15-t2-corner-candidate.brief.json --output /ABS/new-t2-candidate
```

前三类含两条正例与一个必须退出2的t2原角缝反例；独立角缝候选应实际生成3件、裙15并保留确认稿HOLD。也可先用derive_corner_candidate.py从原基线和本次真实诊断另派生新文件，禁止覆盖基线。依赖不在标准位置时使用QUICKSTART中四个显式路径选项。

对每份公开入口返回的revision_root执行：

```bash
python3 -B scripts/validate_delivery.py /ABS/actual-returned-revision-root
python3 -B scripts/prepare_delivery_message.py /ABS/actual-returned-revision-root
python3 -B scripts/selftest_archive_roundtrip.py /ABS/actual-complete.zip --output /ABS/new-roundtrip
python3 -B scripts/selftest_material_mapping.py /ABS/actual-mapped-revision-root --output /ABS/new-mapping-negatives --keep-full-copies
python3 -B scripts/selftest_general_integrity.py /ABS/actual-general-revision-root --output /ABS/new-source-negatives
```

验收必须实读源brief、成形/展开STEP、CUT/BEND、套料和中文PDF；不能用作者“通过”字段替代独立检查。默认15与显式12.34分别核来源和实体；盖体间隙、顶隙计算候选及体高联动要可见。所有未确认项仍HOLD。

作者同步篡改复现脚本保留在本项目 `check_CN03_payload_negatives.py`，实际失败副本目录为 `CN03_repacked_negatives/`，简要错误见包内 `R12-evidence/coherent-tamper-negatives.json`。独立者应自行从新正例制作同步PDF/回执/清单/ZIP篡改副本，核错尺寸、UP/+90、999套及删协议拒绝；不必信任作者脚本。其它详细原产物路径与命令见 `R12-evidence/public-entry-results.json`。

作者范围只覆盖本报告列出的矩形结构与限制路径，未新跑既有源STEP CAD审计；源STEP的partial结果明确限定复用旧独立证据。独立复验及全局安装还未完成。安装顺序见QUICKSTART，不可先覆盖旧2.3.0或链接。
