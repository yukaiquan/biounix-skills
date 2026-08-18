# OatLodgingGWAS 分析流程指南

> 基于 GitHub 仓库 [LiangXiaotian-oat/OatLodgingGWAS](https://github.com/LiangXiaotian-oat/OatLodgingGWAS)
> 论文：Multi-environment GWAS identifies stable QTLs and candidate genes for lodging resistance-related traits in oat (Avena sativa L.)
> 作者：liangxiaotian+BioUnix+GLM5.2

## 一、流程概览

```
表型数据 → 描述统计 → 相关性分析 → 核心性状筛选(XGBoost) → 正态性检验
    → 遗传力/BLUP(方案A或B) → GWAS(FarmCPU) → 曼哈顿/QQ图 → SNP可视化 → 单倍型验证
```

## 二、环境准备

### R 依赖 (≥ 4.0)
```r
install.packages(c("lme4", "emmeans", "ggplot2", "CMplot",
                    "tidyverse", "data.table", "GGally", "PerformanceAnalytics",
                    "readxl", "writexl"))
devtools::install_github("jiabowang/GAPIT3")
```

### Python 依赖 (≥ 3.8)
```bash
pip install pandas numpy scipy matplotlib seaborn statsmodels scikit-learn xgboost
```

## 三、输入数据要求

用户只需准备**一个表型文件**。遗传力计算（Step 06）采用方案A还是方案B，**取决于田间取样重复来源**，因此开始前必须先向用户确认属于哪种情况（见第四节）。

### 表型文件
| 项目 | 说明 |
|------|------|
| 格式 | CSV 或 XLSX（若 XLSX 需指定 sheet 名） |
| 第 1 列 | 基因型名称（默认列名 Sample，可自定义） |
| 数据列 | `{环境}_{性状}`（方案A）或 `{环境}_{性状}_{重复}`（方案B） |
| 环境/性状命名 | **不预设**，由脚本从列名自动识别；环境名与性状名内部不含下划线 `_` |
| 性状数量 | **不固定**，完全由用户表型文件的实际列决定 |

> 本文档与脚本不写死任何具体性状名，统称为「性状1、性状2…性状N」。性状数量、名称、环境数量均随用户输入文件自动适配。

### 其他数据（GWAS/单倍型分析阶段需要）
| 数据类型 | 格式 | 说明 |
|----------|------|------|
| 基因型数据 | HMP/Tassel | 用于 GAPIT GWAS 的基因型矩阵 |
| VCF 文件 | VCF | 标准 VCF，含目标基因区域 SNP（单倍型分析用） |

## 四、两种遗传力计算方案（先问取样重复来源）

> ★ 使用前必须用 `select_option` 向用户确认田间取样重复来源，**不要自行猜测**：
> - 情况1：每个品种×每个环境 3 plots × 3 plants = 9 株（先取小区内 3 株均值，再取 3 小区均值）→ 数据是**环境均值** → 选**方案A**
> - 情况2：每个品种×每个环境 3 plots × 1 plant = 3 个独立重复值（保留重复）→ 数据是**重复级** → 选**方案B**
>
> 同一个表型文件两种方案都可用，选择完全取决于用户的数据来源（取样方式），不是文件名。

### 情况1：3 plots × 3 plants = 9株/品种/环境 → 选方案A

- 每个品种×每个环境有 3 个独立小区，每个小区选 3 株测量
- 数据预处理：先取小区内 3 株均值，再取 3 个小区均值 → 每品种×每环境得到 1 个环境均值
- 方案A使用环境均值级别数据（列名 `{环境}_{性状}`，无 `_1/_2/_3` 后缀）

### 情况2：3 plots × 1 plant = 3个值/品种/环境 → 选方案B

- 每个品种×每个环境有 3 个独立小区，每个小区只取 1 株/得到 1 个性状值
- 每环境每品种有 3 个独立重复值
- 方案B直接利用 3 个重复值（列名 `{环境}_{性状}_{1~r}`），保留重复间变异信息

### 方案A：标准 entry-mean 模型（`--mode A`）

- **适用田间设计**：情况1（3 plots × 3 plants = 9株，取均值后分析）
- **数据级别**：环境均值（每品种×每环境 1 个值）
- **模型**：`Value ~ (1|Genotype) + (1|Environment)`
- **H² 公式**：H² = Vg / (Vg + Ve/e)，e = 环境数
  - 残差 Ve 包含了 G×E 和小区内误差
- **BLUP**：输出基因型 BLUP（来自该模型 `ranef` 效应）
- **特点**：计算简单快速，数据已预平均
- **输出**：遗传力表 + BLUP 表

### 方案B：RCBD 重复级模型 + LRT（`--mode B`）

- **适用田间设计**：情况2（3 plots × 1 plant = 3个值，保留重复）
- **数据级别**：重复级（每品种×每环境 r 个值）
- **模型**（所有性状统一）：
  `Value ~ 1 + (1|Genotype) + (1|Environment) + (1|Environment:Replicate) + (1|Genotype:Environment)`
  - 即 `y_ijk = mu + G_i + E_j + R_k(j) + (G×E)_ij + error_ijk`
- **H² 公式**：H² = Vg / (Vg + Vge/e + Ve/(e×r))，e = 环境数，r = 重复数
  - 显式分解 G×E 方差（Vge）和重复间方差
  - 区组/重复方差仅用于建模，不计入基因型均值遗传力的分母
- **LRT 检验**：似然比检验基因型随机效应是否显著（ML 嵌套模型比较）
- **BLUP**：输出基因型 BLUP（来自该模型 `ranef` 效应）
- **重要限制**：
  - 所有性状都要求重复级列 `{环境}_{性状}_{1~r}`；若某性状仅有环境均值，该性状会被记入 `Missing_Data` 且不计算 H²/BLUP
- **输出 XLSX 的 sheet**：
  - `H2_Summary`：各性状方差组分 + H² + LRT
  - `BLUP`：各性状基因型 BLUP
  - `Variance_Components`：各性状随机效应方差组分明细（仅方案B）
  - `Notes`：模型/试验设计/H² 公式/BLUP 说明
  - `Missing_Data`（仅当有性状缺列时出现）：列出未计算的性状及缺失列

### 方案对比表

| 维度 | 方案A | 方案B |
|------|-------|-------|
| 田间设计 | 情况1（3×3=9株，取均值） | 情况2（3×1=3个值，保留重复） |
| 数据级别 | 环境均值（1值/品种/环境） | 重复级（r值/品种/环境） |
| 模型类型 | 标准 LMM（`(1|Genotype)+(1|Environment)`） | RCBD 重复级模型（含 Environment:Replicate 与 Genotype:Environment） |
| H² 公式 | Vg/(Vg+Ve/e) | Vg/(Vg+Vge/e+Ve/(e×r)) |
| Vge 分解 | 不区分（混入残差） | 显式分解 G×E 方差 |
| LRT 检验 | 无 | 有 |
| BLUP | 输出 | 输出 |
| 适用场景 | 初步分析、数据已预平均 | 精确估算、返修验证、审稿人要求 |
| 依赖包 | lme4, readxl, dplyr, writexl | lme4, readxl, dplyr, writexl |

## 五、分步流程

### Step 01: 表型描述统计 (`01_phenotype_stats.R`)
- **功能**：计算 Mean、SD、CV、Range

### Step 02: 相关性分析-PerformanceAnalytics (`02_correlation_visualization_PerformanceAnalytics.R`)
- **功能**：跨环境表型相关性矩阵 + 显著性标注

### Step 03: 相关性分析-GGally (`03_correlation_visualization_GGally.R`)
- **功能**：按环境分组的成对相关性矩阵 + 分布图

### Step 04: XGBoost 核心性状筛选 (`04_xgboost_feature_importance.py`)
- **功能**：计算各农艺性状对目标性状的特征重要性

### Step 05: 正态性检验 (`05_normality_checks_visualization.R`)
- **功能**：频率分布直方图 + 拟合正态曲线

### Step 06: 遗传力与 BLUP 计算

**先确认取样重复来源**（用 `select_option`），再选择方案：

- **情况1（3×3=9株，取均值）→ 方案A**：标准 entry-mean H² + BLUP
- **情况2（3×1=3个值，保留重复）→ 方案B**：RCBD 重复级模型 H² + LRT + BLUP

统一脚本 `recalculate_H2_LRT_RCBD.R`（全自动双模式）：
```bash
# 方案A
Rscript recalculate_H2_LRT_RCBD.R --input 表型文件 --output 结果.xlsx --mode A

# 方案B
Rscript recalculate_H2_LRT_RCBD.R --input 表型文件 --output 结果.xlsx --mode B --reps 3
```
- 详见 [recalculate_H2_LRT_RCBD.R](./recalculate_H2_LRT_RCBD.R)
- 脚本自动从列名识别环境/性状/重复，无需预先指定性状名或数量

### Step 07: GWAS 分析 (`07_gapit_gwas.R`)
- **功能**：GAPIT FarmCPU 模型多环境 GWAS

### Step 08: 曼哈顿图与 QQ 图 (`08_Manhattan_QQ_Plots.R`)
- **功能**：各环境 + BLUP 值的 Manhattan 图和 Q-Q 图

### Step 09: SNP 基因型可视化 (`09_SNP_genotype_visualization.py`)
- **功能**：KASP 基因型散点图 + 基因结构标注

### Step 10: 单倍型验证 (`10_haplotype_verification.py`)
- **功能**：单 SNP 效应箱线图 + 基因聚合效应回归分析

## 六、运行方式

```bash
git clone https://github.com/LiangXiaotian-oat/OatLodgingGWAS.git
cd OatLodgingGWAS

Rscript 01_phenotype_stats.R
Rscript 02_correlation_visualization_PerformanceAnalytics.R
Rscript 03_correlation_visualization_GGally.R
Rscript 05_normality_checks_visualization.R

# Step 06：先确认取样重复来源，再选择方案A或方案B（同一表型文件）
Rscript recalculate_H2_LRT_RCBD.R --input 表型文件 --output 结果.xlsx --mode A
# 或
Rscript recalculate_H2_LRT_RCBD.R --input 表型文件 --output 结果.xlsx --mode B --reps 3

Rscript 07_gapit_gwas.R
Rscript 08_Manhattan_QQ_Plots.R

python 04_xgboost_feature_importance.py
python 09_SNP_genotype_visualization.py
python 10_haplotype_verification.py
```

## 七、引用

Liang Xiaotian, et al. (2025). Multi-environment genome-wide association study identifies stable QTLs and candidate genes for lodging resistance-related traits in oat (Avena sativa L.).
