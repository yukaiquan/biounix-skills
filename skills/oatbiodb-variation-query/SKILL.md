---
name: oatbiodb-variation-query
description: "通过 tabix 直查 OatBioDB（燕麦生物信息数据库, www.waooat.cn）目标库的 VCF 文件，按位点（chr:pos）查询 SNP/Indel 在不同材料中的基因型分型，并用 scripts/parse_vcf_tsv.py 解析为本地 TSV（Sample/Info/Base）+ 基因型统计。Windows 下按「用户 PATH → 本 app 工具目录 → 官方下载安装」优先级自动解析 tabix。适用于需要按库（vhub id）+ 位点查询基因型、且希望自动化保存结果（不经过大模型、无需人工点击）的场景。触发词：OatBioDB、燕麦、位点查询、基因型、tabix、VCF、SNP、Indel、waooat、AVESA。"
triggers:
  - OatBioDB
  - 燕麦
  - 位点查询
  - 基因型
  - tabix
  - VCF
  - SNP
  - Indel
  - waooat
  - AVESA
  - vhub
  - Windows tabix
  - tabix 安装
  - tabix 找不到
always_active: false
version: null
category: null
author: deepseek-v4-flash + BioUnix
---
---
name: oatbiodb-variation-query
description: >-
  通过 tabix 直查 OatBioDB（燕麦生物信息数据库, www.waooat.cn）目标库的 VCF 文件，
  按位点（chr:pos）查询 SNP/Indel 在不同材料中的基因型分型，并用
  scripts/parse_vcf_tsv.py 解析为本地 TSV（Sample/Info/Base）+ 基因型统计。
  Windows 下按「用户 PATH → 本 app 工具目录 → 官方下载安装」优先级自动解析 tabix。
  适用于需要按库（vhub id）+ 位点查询基因型、且希望自动化保存结果
  （不经过大模型、无需人工点击）的场景。
  触发词：OatBioDB、燕麦、位点查询、基因型、tabix、VCF、SNP、Indel、waooat、AVESA。
triggers:
  - OatBioDB
  - 燕麦
  - 位点查询
  - 基因型
  - tabix
  - VCF
  - SNP
  - Indel
  - waooat
  - AVESA
  - vhub
  - Windows tabix
  - tabix 安装
  - tabix 找不到
---

# OatBioDB Variation Query (tabix direct)

Query SNP/Indel genotypes from OatBioDB by running `tabix` directly against the target
database's VCF, then parse the extracted variant lines into a per-sample TSV.

## When to use
- User wants genotypes for one or more loci (`chr:pos`) in an OatBioDB vhub database.
- User wants results saved as TSV files without manual clicking or LLM involvement.

## Workflow

### 1. Resolve the target VCF (API)
Ask the user for the vhub id (e.g. `https://www.waooat.cn/vhub/1` → id `1`) and the loci.
Fetch the target database metadata:

```bash
curl -s https://api.waooat.cn/project/vhubtarget/<id>/
```

From the JSON take the `vcf` field (e.g. `https://db.waooat.cn/oatdb/vcf/ng_sanfensan_oat2022_gbs.vcf.gz`)
and the `vcfcsi` field (CSI index path). Both are needed for tabix queries.

### 2. Ensure tabix is available
Resolve `tabix` in this priority order:

- **Windows**:
  1. Check the user environment PATH first: `where tabix` (PowerShell: `Get-Command tabix`).
  2. If not found, look in the BioUnix app tool directory (e.g. `<appData>/tools/` or the
     user-configured tool directory), including `tabix.exe` under an `htslib` subdirectory.
  3. Only if still missing, download and install the Windows build:
     `https://ftps.waooat.cn/soft/htslib/htslib-1.23-windows-x64.zip` — unzip it, use
     `tabix.exe` inside the `htslib` directory (copy it into the tool directory and add to
     PATH, or call it by full path).
- **macOS/Linux**: system tabix (`brew install htslib`, `conda install -c bioconda tabix`,
  or `which tabix`).
- **Other cases**: ask the user to provide the tabix path or install it.

Verify with `tabix --version` (or `<path>/tabix.exe --version`).

### 3. Query the locus
Locus format is `chr:pos` (End is inclusive — for a single position do NOT add +1).
tabix can query the remote VCF URL directly:

```bash
tabix -H <vcf.gz> > header.txt
tabix <vcf.gz> chr1A:5127200 > variant.vcf
```

If the query returns nothing, check the chromosome naming (e.g. `chr1A` vs `1A`) and the
index. tabix auto-fetches `<vcf>.csi`; if the `vcfcsi` path differs, download the index
next to the VCF (or query a local copy).

### 4. Parse to TSV + genotype stats
```bash
python3 scripts/parse_vcf_tsv.py variant.vcf header.txt <chr>_<pos>.tsv
```

Outputs:
- `<chr>_<pos>.tsv` — per-sample table (Sample / Info / Base)
- `<chr>_<pos>.tsv.variant.txt` — variant summary line (CHROM POS ID REF ALT FORMAT)
- stdout — genotype counts (0/0, 0/1, 1/1, ./.)

### 5. Summarize for the user
Report REF/ALT and the genotype distribution table:

| 基因型 | 碱基 | 样本数 | 占比 |
|--------|------|--------|------|
| 0/0（纯合参考） | G | 478 | 71.8% |
| 0/1（杂合） | G\|T | 108 | 16.2% |
| 1/1（纯合变异） | T | 0 | 0% |
| ./.（缺失） | . | 80 | 12.0% |

## Notes
- Output naming rule: `<chr>_<pos>.tsv` (e.g. `chr1A_5127200.tsv`).
- **Legacy**: the old browser-based flow (`scripts/receive_tsv.py` + local HTTP receiver +
  browser JS fetch) is deprecated. The script is kept for reference only — do NOT start a
  local HTTP server or simulate a browser for new queries.
