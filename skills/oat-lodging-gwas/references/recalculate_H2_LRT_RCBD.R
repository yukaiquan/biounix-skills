#!/usr/bin/env Rscript
# =============================================================================
# 通用多环境遗传力(H2)与 BLUP 计算脚本（双模式）
# =============================================================================
# 本脚本从一份宽表型文件自动识别「环境」「性状」「重复」，计算各性状的
# 广义遗传力(entry-mean H2)与基因型 BLUP。性状/环境名称不写死，完全由
# 输入文件的列名决定，可适配不同用户的性状数量与命名。
#
# 两种模式（由取样重复来源决定，二选一）：
#   方案A（--mode A）：3 plots x 3 plants = 9 株，先取株均值再取小区均值，
#                     得到每「环境 x 性状」一个环境均值。
#                     模型：Value ~ (1|Genotype) + (1|Environment)
#                     H2   = Vg / (Vg + Ve/e)
#   方案B（--mode B）：3 plots x 1 plant = 3 个独立重复值，保留重复。
#                     模型：Value ~ (1|Genotype) + (1|Environment)
#                                + (1|Environment:Replicate)
#                                + (1|Genotype:Environment)
#                     H2   = Vg / (Vg + Vge/e + Ve/(e*r))
#                     并做基因型随机效应的 LRT 检验。
#   两种模式都会计算并输出基因型 BLUP（来自对应模型的 ranef 效应）。
#
# 列名约定（环境名与性状名内部均不含下划线 "_"）：
#   方案A：{环境}_{性状}             （环境均值列，无重复后缀）
#   方案B：{环境}_{性状}_{重复号}    （重复级列，重复号 1..r）
#   BLUP 列（若存在）以 "BLUP_" 开头，会被自动忽略，不参与解析。
#
# 用法示例：
#   Rscript recalculate_H2_LRT_RCBD.R \
#     --input  table.xlsx --output out.xlsx --mode A [--sheet 表名]
#   Rscript recalculate_H2_LRT_RCBD.R \
#     --input  table.csv  --output out.xlsx --mode B --reps 3
#
# 可选参数（一般不传，自动推断）：
#   --id-col  基因型列名（默认 Sample）
#   --sheet   xlsx 工作表名（默认第 1 张表）
#   --reps    重复数 r（默认 3，方案B使用）
#   --envs    逗号分隔的环境列表（默认从列名自动推断）
#   --traits  逗号分隔的性状列表（默认从列名自动推断）
# =============================================================================

required_packages <- c("readxl", "lme4", "dplyr", "writexl")
for (pkg in required_packages) {
  if (!requireNamespace(pkg, quietly = TRUE)) {
    install.packages(pkg, repos = "https://cloud.r-project.org")
  }
}

suppressPackageStartupMessages({
  library(readxl)
  library(lme4)
  library(dplyr)
  library(writexl)
})

# -----------------------------------------------------------------------------
# 0. 命令行参数解析
# -----------------------------------------------------------------------------
argv <- commandArgs(trailingOnly = TRUE)

get_arg <- function(key, default = NULL) {
  idx <- which(argv == key)
  if (length(idx) == 0L) return(default)
  val <- argv[idx[1L] + 1L]
  if (is.na(val) || length(val) == 0L || startsWith(val, "--")) return(default)
  val
}

input_file <- get_arg("--input")
output_file <- get_arg("--output", "H2_BLUP_results.xlsx")
sheet_name <- get_arg("--sheet", NULL)
mode <- toupper(get_arg("--mode"))
id_col <- get_arg("--id-col", "Sample")
reps_nominal <- suppressWarnings(as.integer(get_arg("--reps", "3")))
envs_arg <- get_arg("--envs", NULL)
traits_arg <- get_arg("--traits", NULL)

if (is.null(input_file)) {
  stop("缺少 --input。用法：Rscript recalculate_H2_LRT_RCBD.R --input 表型文件 --output 结果.xlsx --mode A|B")
}
if (!mode %in% c("A", "B")) {
  stop("--mode 必须为 A 或 B（A=环境均值模型；B=RCBD 重复级模型+LRT）。")
}
if (is.na(reps_nominal) || reps_nominal < 1L) {
  stop("--reps 必须为正整数。")
}

split_csv <- function(s) {
  if (is.null(s) || !nzchar(s)) return(NULL)
  trimws(strsplit(s, ",", fixed = TRUE)[[1L]])
}

# -----------------------------------------------------------------------------
# 1. 读取宽表
# -----------------------------------------------------------------------------
is_xlsx <- grepl("\\.xlsx?$", input_file, ignore.case = TRUE)
if (is_xlsx) {
  if (is.null(sheet_name)) {
    sheet_name <- excel_sheets(input_file)[1L]
    message("未指定 --sheet，使用第 1 张工作表：", sheet_name)
  }
  wide <- read_excel(input_file, sheet = sheet_name, na = c("", "NA", "NaN"))
} else {
  wide <- read.csv(input_file, stringsAsFactors = FALSE, check.names = FALSE,
                   na.strings = c("", "NA", "NaN"))
}

if (!id_col %in% names(wide)) {
  stop("输入表缺少基因型列：", id_col, "。可用 --id-col 指定实际列名。")
}
wide[[id_col]] <- as.character(wide[[id_col]])

# -----------------------------------------------------------------------------
# 2. 从列名自动识别 环境 / 性状 / 重复
# -----------------------------------------------------------------------------
data_cols <- setdiff(names(wide), id_col)
data_cols <- data_cols[!grepl("^BLUP_", data_cols, ignore.case = TRUE)]

parse_column <- function(colname) {
  p <- strsplit(colname, "_", fixed = TRUE)[[1L]]
  if (length(p) == 2L) return(c(env = p[1L], trait = p[2L], rep = "Mean"))
  if (length(p) == 3L) return(c(env = p[1L], trait = p[2L], rep = p[3L]))
  NULL
}

colinfo <- do.call(rbind, Filter(Negate(is.null), lapply(data_cols, parse_column)))
if (is.null(colinfo) || nrow(colinfo) == 0L) {
  stop("未能从列名解析出任何 {环境}_{性状} 或 {环境}_{性状}_{重复} 形式的数据列。")
}
colinfo <- as.data.frame(colinfo, stringsAsFactors = FALSE)

environments <- if (!is.null(envs_arg)) split_csv(envs_arg) else sort(unique(colinfo$env))
traits       <- if (!is.null(traits_arg)) split_csv(traits_arg) else sort(unique(colinfo$trait))

if (length(environments) == 0L) stop("未能从列名识别任何环境。可用 --envs 显式指定。")
if (length(traits) == 0L)       stop("未能从列名识别任何性状。可用 --traits 显式指定。")

e_nominal <- length(environments)
r_nominal <- reps_nominal

message("模式：方案", mode)
message("识别到的环境(", e_nominal, ")：", paste(environments, collapse = ", "))
message("识别到的性状(", length(traits), ")：", paste(traits, collapse = ", "))

# -----------------------------------------------------------------------------
# 3. 宽 → 长
# -----------------------------------------------------------------------------
build_long_trait <- function(dat, trait, envs, mode, reps, id_col) {
  out <- list()
  missing_cols <- character(0L)
  k <- 1L

  for (env in envs) {
    if (mode == "A") {
      expected <- paste0(env, "_", trait)
      reps_used <- "Mean"
    } else {
      expected <- paste0(env, "_", trait, "_", seq_len(reps))
      reps_used <- as.character(seq_len(reps))
    }

    present <- expected %in% names(dat)
    if (!all(present)) {
      missing_cols <- c(missing_cols, expected[!present])
      next
    }

    for (j in seq_along(expected)) {
      val <- suppressWarnings(as.numeric(dat[[expected[j]]]))
      keep <- !is.na(val)
      if (!any(keep)) next
      out[[k]] <- data.frame(
        Genotype    = dat[[id_col]][keep],
        Environment = env,
        Replicate   = reps_used[j],
        Value       = val[keep],
        stringsAsFactors = FALSE
      )
      k <- k + 1L
    }
  }

  if (length(out) == 0L) {
    return(list(data = NULL, missing = unique(missing_cols)))
  }

  long <- bind_rows(out) %>%
    mutate(
      Genotype    = factor(Genotype),
      Environment = factor(Environment, levels = envs),
      Replicate   = factor(Replicate)
    )

  list(data = long, missing = unique(missing_cols))
}

get_vc <- function(vc_df, candidates, default = 0) {
  hit <- vc_df$grp %in% candidates
  if (!any(hit)) return(default)
  sum(vc_df$vcov[hit], na.rm = TRUE)
}

control <- lmerControl(optimizer = "bobyqa", optCtrl = list(maxfun = 200000))

# -----------------------------------------------------------------------------
# 4. 拟合单个性状，返回 summary / vc / blup
# -----------------------------------------------------------------------------
fit_one_trait <- function(long_dat, trait_name, mode, e, r) {
  if (is.null(long_dat) || nrow(long_dat) == 0L) return(NULL)

  if (mode == "A") {
    formula <- Value ~ 1 + (1 | Genotype) + (1 | Environment)
  } else {
    formula <- Value ~ 1 + (1 | Genotype) + (1 | Environment) +
      (1 | Environment:Replicate) + (1 | Genotype:Environment)
  }

  full_reml <- lmer(formula, data = long_dat, REML = TRUE, control = control)
  vc <- as.data.frame(VarCorr(full_reml))

  VG   <- get_vc(vc, "Genotype")
  VE   <- get_vc(vc, "Environment")
  VR   <- get_vc(vc, c("Environment:Replicate", "Replicate:Environment"))
  VGE  <- get_vc(vc, c("Genotype:Environment", "Environment:Genotype"))
  Vres <- get_vc(vc, "Residual")

  if (mode == "A") {
    H2 <- VG / (VG + Vres / e)
    lrt_chisq <- NA_real_
    lrt_p <- NA_real_
  } else {
    H2 <- VG / (VG + VGE / e + Vres / (e * r))
    full_ml <- update(full_reml, REML = FALSE)
    null_ml <- lmer(
      Value ~ 1 + (1 | Environment) +
        (1 | Environment:Replicate) + (1 | Genotype:Environment),
      data = long_dat, REML = FALSE, control = control
    )
    lrt <- anova(null_ml, full_ml, refit = FALSE)
    lrt_chisq <- suppressWarnings(as.numeric(lrt$Chisq[2L]))
    lrt_p <- suppressWarnings(as.numeric(lrt$`Pr(>Chisq)`[2L]))
  }

  # 基因型 BLUP（两种模式都输出）
  blup_df <- data.frame(
    Genotype = rownames(ranef(full_reml)$Genotype),
    BLUP = as.numeric(ranef(full_reml)$Genotype[, 1L]),
    stringsAsFactors = FALSE
  )

  n_genotype <- length(unique(long_dat$Genotype))
  n_env_observed <- length(unique(long_dat$Environment))
  n_obs <- nrow(long_dat)
  cell_counts <- long_dat %>% count(Genotype, Environment, name = "n_rep")

  summary <- data.frame(
    Trait            = trait_name,
    Mode             = mode,
    N_Genotypes      = n_genotype,
    N_Environments   = n_env_observed,
    Planned_Replicates = if (mode == "A") NA_integer_ else r,
    N_Observations   = n_obs,
    Sigma2_G         = VG,
    Sigma2_E         = VE,
    Sigma2_RepWithinE = VR,
    Sigma2_GxE       = VGE,
    Sigma2_Residual  = Vres,
    Broad_Sense_H2   = H2,
    LRT_ChiSquare    = lrt_chisq,
    LRT_Pvalue       = lrt_p,
    Singular_Fit     = isSingular(full_reml, tol = 1e-4),
    Min_Reps_per_GxE = min(cell_counts$n_rep),
    Median_Reps_per_GxE = median(cell_counts$n_rep),
    Max_Reps_per_GxE = max(cell_counts$n_rep),
    stringsAsFactors = FALSE
  )

  list(summary = summary, vc = vc, blup = blup_df)
}

# -----------------------------------------------------------------------------
# 5. 遍历所有性状
# -----------------------------------------------------------------------------
summary_list <- list()
missing_list <- list()
vc_list <- list()
blup_list <- list()

for (trait in traits) {
  cat("\n==============================\nTrait:", trait, "\n")

  built <- build_long_trait(wide, trait, environments, mode, reps_nominal, id_col)

  if (length(built$missing) > 0L) {
    cat("  缺失列：", paste(built$missing, collapse = ", "), "\n")
  }

  if (is.null(built$data)) {
    missing_list[[trait]] <- data.frame(
      Trait = trait,
      Status = "NOT CALCULATED",
      Reason = if (mode == "A") {
        "缺少环境均值列（{环境}_{性状}）。"
      } else {
        paste0("缺少重复级列（{环境}_{性状}_{1..", reps_nominal, "}）。")
      },
      Missing_Columns = paste(built$missing, collapse = "; "),
      stringsAsFactors = FALSE
    )
    next
  }

  fit <- fit_one_trait(built$data, trait, mode, e_nominal, r_nominal)
  summary_list[[trait]] <- fit$summary

  vc_tmp <- fit$vc
  vc_tmp$Trait <- trait
  vc_list[[trait]] <- vc_tmp

  blup_tmp <- fit$blup
  blup_tmp$Trait <- trait
  blup_list[[trait]] <- blup_tmp
}

summary_df <- if (length(summary_list) > 0L) bind_rows(summary_list) else data.frame()
missing_df <- if (length(missing_list) > 0L) bind_rows(missing_list) else data.frame()
vc_df     <- if (length(vc_list) > 0L)     bind_rows(vc_list)     else data.frame()
blup_df   <- if (length(blup_list) > 0L)   bind_rows(blup_list)   else data.frame()

# -----------------------------------------------------------------------------
# 6. 导出
# -----------------------------------------------------------------------------
notes <- data.frame(
  Item = c("Mode", "Design", "H2 formula", "BLUP"),
  Note = c(
    if (mode == "A") "方案A：环境均值模型 Value ~ (1|Genotype)+(1|Environment)" else
      "方案B：RCBD 重复级模型 Value ~ (1|Genotype)+(1|Environment)+(1|Environment:Replicate)+(1|Genotype:Environment)",
    if (mode == "A") "3 plots x 3 plants 取均值后，每环境x性状一个环境均值。" else
      "3 plots x 1 plant，保留重复（每环境x性状 r 个重复值）。",
    if (mode == "A") "H2 = Vg / (Vg + Ve/e)" else "H2 = Vg / (Vg + Vge/e + Ve/(e*r))",
    "两种方案均输出基因型 BLUP（来自对应模型的 ranef 效应）。"
  ),
  stringsAsFactors = FALSE
)

output_sheets <- list(
  H2_Summary = summary_df,
  BLUP = blup_df,
  Notes = notes
)

if (mode == "B" && nrow(vc_df) > 0L) {
  output_sheets$Variance_Components <- vc_df
}
if (nrow(missing_df) > 0L) {
  output_sheets$Missing_Data <- missing_df
}

write_xlsx(output_sheets, path = output_file)

cat("\nDone. 结果已写入：", output_file, "\n")
