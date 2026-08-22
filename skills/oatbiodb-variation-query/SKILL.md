---
name: oatbiodb-variation-query
description: 查询 OatBioDB（燕麦生物信息数据库, www.waooat.cn）目标库 VCF 的 SNP/Indel 基因型分型。Windows 优先复用页面 WASM 工具（方案 A：动态 import oatbiodbworker-*.js 的 d 导出即页面内部 qt 函数，直接调用 bcftools 1.10 wasm 查询远程 VCF 指定位点，无需本地 tabix、无需下载安装）；macOS/Linux 或页面不可用时用 tabix 直查（方案 B，Windows 下按「用户 PATH → app 工具目录 → 官方下载安装」解析 tabix）。结果用 scripts/parse_vcf_tsv.py 解析为本地 TSV（Sample/Info/Base）+ 基因型统计。适用于按库（vhub id）+ 位点查询基因型、自动化保存结果（不经过大模型、无需人工点击）的场景。触发词：OatBioDB、燕麦、位点查询、基因型、tabix、VCF、SNP、Indel、waooat、AVESA、WASM、bcftools、复用页面工具。
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
  - WASM
  - bcftools
  - 复用页面工具
  - 页面工具
  - qt
  - oatbiodbworker
  - aioli
  - biowasm
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
  查询 OatBioDB（燕麦生物信息数据库, www.waooat.cn）目标库 VCF 的 SNP/Indel 基因型分型。
  Windows 优先复用页面 WASM 工具（方案 A：动态 import oatbiodbworker-*.js 的 d 导出
  即页面内部 qt 函数，直接调用 bcftools 1.10 wasm 查询远程 VCF 指定位点，无需本地 tabix、
  无需下载安装）；macOS/Linux 或页面不可用时用 tabix 直查（方案 B，Windows 下按
  「用户 PATH → app 工具目录 → 官方下载安装」解析 tabix）。结果用
  scripts/parse_vcf_tsv.py 解析为本地 TSV（Sample/Info/Base）+ 基因型统计。
  触发词：OatBioDB、燕麦、位点查询、基因型、tabix、VCF、SNP、Indel、waooat、AVESA、
  WASM、bcftools、复用页面工具。
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
  - WASM
  - bcftools
  - 复用页面工具
  - 页面工具
  - qt
  - oatbiodbworker
  - aioli
  - biowasm
  - Windows tabix
  - tabix 安装
  - tabix 找不到
---

# OatBioDB Variation Query

Query SNP/Indel genotypes from OatBioDB by locus (`chr:pos`), then parse the extracted
variant lines into a per-sample TSV + genotype stats.

Two query paths:
- **方案 A — 复用页面 WASM 工具（Windows 优先）**: reuse the vhub page's own
  biowasm (aioli) + bcftools 1.10 toolchain in the browser. No local tabix, no install.
  Full JS code: [📋 WASM 查询代码](./references/wasm-query.md).
- **方案 B — tabix 直查 VCF（macOS/Linux 或页面不可用时）**: run `tabix` directly
  against the remote VCF URL.

## When to use
- User wants genotypes for one or more loci (`chr:pos`) in an OatBioDB vhub database.
- User wants results saved as TSV files without manual clicking or LLM involvement.
- **Windows: prefer 方案 A** (no local toolchain needed). Fall back to 方案 B only if
  the page/worker is unavailable or `mod.d` is missing.

## Workflow

### 0. Resolve the target VCF (API) — both plans
Ask for the vhub id (e.g. `https://www.waooat.cn/vhub/1` → id `1`) and the loci.
Fetch metadata:

```bash
curl -s https://api.waooat.cn/project/vhubtarget/<id>/
```

Take `vcf` (e.g. `https://db.waooat.cn/oatdb/vcf/ng_sanfensan_oat2022_gbs.vcf.gz`)
and `vcfcsi` (CSI index path). Both are needed.

### 方案 A — Reuse the page WASM tool (Windows priority)

1. Open the vhub page (`browser_navigate` to `https://www.waooat.cn/vhub/<id>/`) and click
   the Variation Search card to init the page.
2. Discover the worker module URL dynamically (hash changes): find `oatbiodbworker-*.js`
   in `performance.getEntriesByType('resource')`.
3. `const mod = await import(workerUrl); const qt = mod.d;` — `qt(cmd, vcfUrl, csiUrl)`
   is the page's internal bcftools query function.
4. Query: `const r = await qt('bcftools view -r <chr>:<pos>-<pos> ', vcf, csi);`
   `r.stdout` is the VCF text (header + variant + sample columns).
5. Parse `r.stdout` in-page to TSV + genotype counts (data never passes through the LLM),
   then save via `scripts/receive_tsv.py` or show directly.

Full JS snippets: [📋 WASM 查询代码](./references/wasm-query.md).

### 方案 B — tabix direct (macOS/Linux or fallback)

1. Ensure tabix is available, in this priority order:
   - **Windows**: user PATH (`where tabix`) → app tool directory (`<appData>/tools/`,
     incl. `tabix.exe` under `htslib`) → download install
     `https://ftps.waooat.cn/soft/htslib/htslib-1.23-windows-x64.zip`.
   - **macOS/Linux**: system tabix (`brew install htslib`, `conda install -c bioconda tabix`).
   - Verify with `tabix --version`.
2. Query the locus (End inclusive — single position, no +1):
   ```bash
   tabix -H <vcf.gz> > header.txt
   tabix <vcf.gz> chr1A:5127200 > variant.vcf
   ```
   If empty, check chromosome naming (`chr1A` vs `1A`) and the index.
3. Parse to TSV + stats:
   ```bash
   python3 scripts/parse_vcf_tsv.py variant.vcf header.txt <chr>_<pos>.tsv
   ```

### Summarize for the user
Report REF/ALT and the genotype distribution table:

| 基因型 | 碱基 | 样本数 | 占比 |
|--------|------|--------|------|
| 0/0（纯合参考） | G | 478 | 71.8% |
| 0/1（杂合） | G\|T | 108 | 16.2% |
| 1/1（纯合变异） | T | 0 | 0% |
| ./.（缺失） | . | 80 | 12.0% |

## Notes
- Output naming rule: `<chr>_<pos>.tsv` (e.g. `chr1A_5127200.tsv`).
- 方案 A requires the page to stay open (wasm runs in the browser); first query is slow
  (wasm lazy-loads from `https://cdn.waooat.cn/wasm`).
- **Legacy**: the old browser-based flow (local HTTP receiver + browser JS fetch) is
  deprecated as a query path. `scripts/receive_tsv.py` is kept only as a file-sink helper
  for 方案 A's TSV output — do NOT start a local HTTP server or simulate a browser for
  new tabix queries.
