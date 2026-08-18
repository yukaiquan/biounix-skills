# OatLodgingGWAS 脚本概览

> 仓库地址：https://github.com/LiangXiaotian-oat/OatLodgingGWAS
> 许可证：MIT
> 作者：liangxiaotian+BioUnix+GLM5.2

## 脚本清单

| 序号 | 文件名 | 语言 | 功能 |
|------|--------|------|------|
| 01 | `01_phenotype_stats.R` | R | 表型描述统计（Mean/SD/CV/Range） |
| 02 | `02_correlation_visualization_PerformanceAnalytics.R` | R | 跨环境表型相关性（PerformanceAnalytics） |
| 03 | `03_correlation_visualization_GGally.R` | R | 分环境成对相关性矩阵（GGally） |
| 04 | `04_xgboost_feature_importance.py` | Python | XGBoost 核心性状筛选（特征重要性） |
| 05 | `05_normality_checks_visualization.R` | R | 正态性检验（直方图+正态曲线） |
| 06 | `recalculate_H2_LRT_RCBD.R` | R | 遗传力 + BLUP 计算（全自动双模式） |
| 07 | `07_gapit_gwas.R` | R | GWAS 分析（GAPIT FarmCPU 模型） |
| 08 | `08_Manhattan_QQ_Plots.R` | R | Manhattan 图 + Q-Q 图 |
| 09 | `09_SNP_genotype_visualization.py` | Python | KASP 基因型散点图 + 基因结构 |
| 10 | `10_haplotype_verification.py` | Python | 单 SNP 效应箱线图 + 聚合效应回归 |

## 遗传力与 BLUP 计算（同一脚本，双模式）

统一脚本 `recalculate_H2_LRT_RCBD.R`，通过 `--mode A|B` 切换两种方案，性状/环境名称与数量**不写死**，由脚本从列名自动识别（通用化为「性状1、性状2…性状N」）。两种方案均计算并输出基因型 BLUP。

### 方案A：`--mode A`
- **适用田间设计**：情况1（3 plots × 3 plants = 9株，取均值后分析）
- **数据级别**：环境均值（1值/品种/环境，列名 `{环境}_{性状}`）
- **模型**：`Value ~ (1|Genotype) + (1|Environment)`
- **H²**：Vg/(Vg+Ve/e)
- **BLUP**：输出（ranef 基因型效应）
- **输出**：H2_Summary + BLUP + Notes
- **适用**：初步分析、数据已预平均

### 方案B：`--mode B`
- **适用田间设计**：情况2（3 plots × 1 plant = 3个值，保留重复）
- **数据级别**：重复级（r值/品种/环境，列名 `{环境}_{性状}_{1~r}`）
- **模型**：`Value ~ (1|Genotype) + (1|Environment) + (1|Environment:Replicate) + (1|Genotype:Environment)`
- **H²**：Vg/(Vg+Vge/e+Ve/(e×r))
- **额外功能**：LRT 检验（基因型随机效应显著性）
- **BLUP**：输出（ranef 基因型效应）
- **输出**：H2_Summary + BLUP + Variance_Components + Notes
- **适用**：返修验证、精确估算

### 使用前必做：确认取样重复来源

用 `select_option` 询问用户，不可自行猜测：
- 情况1（3×3=9株，取均值）→ 方案A
- 情况2（3×1=3个值，保留重复）→ 方案B

### 命令行用法

```bash
# 方案A
Rscript recalculate_H2_LRT_RCBD.R --input 表型文件 --output 结果.xlsx --mode A

# 方案B
Rscript recalculate_H2_LRT_RCBD.R --input 表型文件 --output 结果.xlsx --mode B --reps 3
```

可选参数：`--id-col`（基因型列名，默认 Sample）、`--sheet`（xlsx 工作表名，默认第 1 张）、`--reps`（重复数，默认 3）、`--envs`、`--traits`（均默认从列名自动推断）。

## 田间设计与方案选择指南

| 田间设计 | 每品种×每环境观测数 | 推荐方案 | 原因 |
|----------|---------------------|----------|------|
| 3 plots × 3 plants = 9株 | 9（取均值后1个） | 方案A | 数据已预平均到环境均值，H²公式不体现 r |
| 3 plots × 1 plant = 3个值 | 3（直接使用） | 方案B | 保留重复间变异，H²公式分解 Vge 和 Ve |

## 表型文件格式（方案A和方案B共用同一脚本，列结构随方案而变）

| 项目 | 说明 |
|------|------|
| 格式 | CSV 或 XLSX |
| 第 1 列 | 基因型名称（默认列名 Sample，可自定义） |
| 数据列命名 | 方案A：`{环境}_{性状}`；方案B：`{环境}_{性状}_{重复号}` |
| 环境/性状 | 不预设，由脚本自动识别；名称内部不含下划线 `_` |
| 性状数量 | 不固定，随用户文件实际列决定 |

### 列命名示例（方案B，3 个环境 × 2 个性状）

```
Sample, 24WJ_性状1_1, 24WJ_性状1_2, 24WJ_性状1_3, 24WJ_性状2_1, ..., 24BC_性状2_3
G001,  45.2,         44.8,         46.1,         3.5,           ..., 3.8
G002,  52.3,         51.7,         53.0,         4.1,           ..., 4.0
```

> 说明：环境名与性状名均为占位示例，实际值完全取决于用户表型文件的列名。

## 依赖汇总

### R 包
| 包名 | 用途 | 对应脚本 |
|------|------|----------|
| GAPIT | GWAS (FarmCPU) | 07 |
| lme4 | 遗传力/BLUP (LMM) | 06 |
| emmeans | BLUP 估算（原 06 脚本） | — |
| readxl | 读取 XLSX | 06 |
| writexl | 写出 XLSX | 06 |
| dplyr | 数据处理 | 06, 多个 |
| PerformanceAnalytics | 相关性矩阵 | 02 |
| GGally | 分组相关性 | 03 |
| ggplot2 | 通用绘图 | 05, 08 |
| CMplot | Manhattan/QQ 图 | 08 |
| tidyverse | 数据处理 | 多个 |
| data.table | 数据处理 | 多个 |

### Python 包
| 包名 | 用途 | 对应脚本 |
|------|------|----------|
| pandas | 数据处理 | 04, 09, 10 |
| numpy | 数值计算 | 04, 09, 10 |
| scipy | 统计检验 | 10 |
| statsmodels | 统计建模 | 10 |
| scikit-learn | 机器学习 | 04 |
| xgboost | 特征重要性 | 04 |
| matplotlib | 绘图 | 04, 09, 10 |
| seaborn | 统计绘图 | 04, 09, 10 |
