# 体面孔 vs 盖裙下沿遮挡（hole_to_lid_skirt）

版本：v2.8.26（判定基线 v2.8.20 / t99u；主动修复 t27u/t28u，2026-11-01 Asia/Shanghai）。硬性规则22 + 规则25；与规则16「靠盖裙10mm」联动。

## 目的

合盖后盖裙自由下沿会挡住箱体口附近过高的线孔/品字/电表口/侧壁安装孔组。确认稿与投产包都必须先清掉「盖裙遮挡」，不得只报展开孔边距、也不得只标 HOLD 继续出图。

## 几何

- 盖裙自由下沿 Z = **H − skirt**（与 `pipelines/*/build` 中 `zb=H-skirt` 一致）。
- 圆孔特征顶 Z = z + d/2；矩形口顶 Z = cz + h/2。
- **整组最高点**：中心孔与卫星孔/法兰取严者（例：Φ18 + 4×Φ4.5@±9.8 → 最高偏移 = max(9, 9.8+2.25)=12.05）。
- **净空** = 裙下沿 Z − 整组特征顶 Z。

## 判定

| 净空 | 级别 | 文案要点 |
|------|------|----------|
| < 0 | ERROR | msg_cn **必须含「盖裙遮挡」**；列 part/id/尺寸/侵入量 |
| 0 ≤ 净空 < 10 | WARN | 规则16 靠盖裙不足 10 mm |
| ≥ 10 | INFO | 通过 |

## 主动修复（默认，t27u/t28u）

1. ERROR（或用户要投产/「不要确认稿」）→ **下移孔心 Z**，使整组净空 **≥ 10 mm**；升 VER；CHANGELOG 写旧Z→新Z。
2. **禁止**开盖裙缺口/切裙让位，除非本单用户明确要求。
3. **禁止**带着未清除的 ERROR 交付确认稿或投产包（不得以 HOLD 代替修复）。
4. 豁免仅限用户书面接受遮挡：`hold_skirt_clearance_waived` / `skirt_occlusion_accepted` → ERROR→WARN，仍须写「盖裙遮挡」。

目标 Zc 近似：`Zc ≤ (H − skirt) − 10 − pattern_top_offset`。

## 范围

- **检查**：线孔/格兰头、品字口/IEC、电表口、侧壁安装孔组及同类箱体面切口（`end_features` circles/rects；可选带 z 的 `cable_holes`）。
- **排除**：箱体 M4 口沿固定孔（Ø3.3 攻丝）、盖裙螺钉过孔（Ø4.5）——螺钉路径本就在裙下。

## 强制反馈

WARN/ERROR 出现时，`lid_skirt_force_lines_cn(conflicts)` 的每一行必须进：

1. PDF 第1页（红字/待确认栏）
2. `{VER}_CONFIRMATION_DRAFT.txt`（待确认 + 冲突与风险）
3. README / `*_LID_SKIRT_FINDINGS.txt`

ERROR 未清除前不得宣称门禁生产放行。

## 调用

```text
python3 scripts/conflict_checks.py PARAMS.json [report.json]
```

PARAMS 至少：`H`、`skirt`、`end_features`（或 report 含 `end_features`）。管线：`pipelines/u_endplates/run.py` 已从 report 注入。

## 审计样例

- `S-201-1.2-20261029-003-v1`：H=230 skirt=15 → 裙下沿 Z=215；END_L Ø30@Zc=210.6 孔顶 225.6 → 净空 −10.6 → ERROR「盖裙遮挡」。
- `S-201-1-20261101-004-v1`：H=360 skirt=15 → 裙下沿 345；正面安装 Φ18+4×Φ4.5@Zc=343 → 侵入 → ERROR；**v2** 下移 Zc≈323（整组净空≥10），不开裙缺口（t27u/t28u）。
