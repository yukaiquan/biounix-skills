---
name: oat-lodging-gwas
description: "燕麦抗倒伏多环境 GWAS 完整分析流程，基于 LiangXiaotian-oat/OatLodgingGWAS 仓库。含两种遗传力计算方案：方案A→情况1（3 plots×3 plants=9株取均值，环境均值模型，H²公式无r）；方案B→情况2（3 plots×1 plant=3值，RCBD重复级模型+LRT，H²公式有r=3）。新版方案B不再重算 BLUP、不做 BLUP QC，LS 也要求提供重复级列，模型为 (1|Environment:Replicate)+(1|Genotype:Environment)。当用户执行燕麦 GWAS、抗倒伏性状遗传解析、BLUP、广义遗传力 H²、FarmCPU GWAS、Manhattan/QQ 图、单倍型验证时必须先让用户确认取样重复来源（9株均值 vs 3值重复级）再选择方案。"
triggers:
  - 燕麦GWAS
  - 抗倒伏
  - lodging GWas
  - BLUP
  - 广义遗传力
  - H2
  - heritability
  - RCBD
  - replicate
  - FarmCPU
  - Manhattan图
  - QTL
  - 单倍型验证
  - oat-lodging-gwas
  - 遗传力重新计算
  - H2_LRT_RCBD
always_active: false
version: 0.2.0
category: other
author: liangxiaotian+BioUnix+deepseek-v4-pro
---
## 任务使用前必做：确认取样重复来源

用户只需要提供一份表型文件。但分析前必须向用户确认其数据属于哪种取样重复来源：

**情况 1（方案A）：** 3 plots × 3 plants = 9 株取均值，环境均值模型。H² 公式无 r。

**情况 2（方案B，新版）：** 3 plots × 1 plant = 3 值，RCBD 重复级模型 + LRT。H² 公式含 r=3。

禁止根据文件名或后缀直接推断，必须主动询问：

- 每个环境每个品种有多少个田间重复？
- 每个重复是单株测定还是多株取均值？

## 方案B 新版逻辑（recalculate_H2_LRT_RCBD.R）

- 输入：宽格式表型表 `input_TableS1.xlsx`（sheet 变量可配置）。
- 6 个性状：TIL、TID、TIWT、LS、SD、CS。
- 不重算 BLUP，不做 BLUP QC（无 BLUP_QC sheet）。
- LS 也必须提供重复级列（如 24WJ_LS_1...25CZ_LS_3），否则该环境/性状置为 NOT CALCULATED，不再做环境均值兜底。
- 模型：`(1|Environment:Replicate) + (1|Genotype:Environment)`。
- 输出：variance components、H2、LRT 结果。

## 步骤

1. 确认用户输入文件与 sheet 名（默认读宽格式表型表）。
2. 询问取样重复来源，判定使用方案 A 还是方案 B。
3. 若为方案 B，用新版脚本：

```bash
Rscript recalculate_H2_LRT_RCBD.R input_TableS1.xlsx <output_dir>
```

4. 检查 6 个性状列是否齐全，缺 LS 重复级列时输出 NOT CALCULATED。
5. 汇总输出：variance components、H2、LRT p 值。

## 方案 A 与方案 B 对比

| 项 | 方案 A（情况1） | 方案 B（情况2，新版） |
|------|----------------|----------------------|
| 数据 | 3 plots×3 plants=9株取均值 | 3 plots×1 plant=3值 |
| 模型 | 环境均值模型 | RCBD 重复级模型 (1|Environment:Replicate)+(1|Genotype:Environment) |
| H² 公式 | 无 r | 含 r=3 |
| BLUP | 计算 | 不重算 |
| BLUP QC | 有 | 无 |
| LS 兜底 | 环境均值可兜底 | 必须提供重复级列，否则不计算 |

## Resource files

- `scripts/recalculate_H2_LRT_RCBD.R`：新版方案B主脚本（去掉 BLUP 重算/BLUP QC）。
- `references/pipeline-guide.md`：完整分析流程（需按新版方案B同步更新）。
- `references/scripts-overview.md`：脚本清单（06B 描述需同步新逻辑）。