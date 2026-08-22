---
name: oatbiodb-variation-query
description: "Query SNP/Indel genotypes from OatBioDB (www.waooat.cn) by locus (chr:pos). Uses tabix to query remote VCF.gz directly (Plan A), or reuses the page's browser WASM bcftools as a Windows fallback (Plan B). Results are parsed to per-sample TSV + genotype stats. Use when the user wants genotypes for specific loci in an OatBioDB vhub database without manual clicking."
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
always_active: false
version: 2.0.0
category: bioinformatics
author: BioUnix
---
# OatBioDB Variation Query

Query SNP/Indel genotypes from OatBioDB by locus (`chr:pos`), then parse the extracted
variant lines into a per-sample TSV + genotype stats.

## When to use
- User wants genotypes for one or more loci (`chr:pos`) in an OatBioDB vhub database.
- User wants results saved as TSV files without manual clicking or LLM involvement.

## Workflow

### 0. Resolve the target VCF (API) — both plans
Ask for the vhub id (e.g. `https://www.waooat.cn/vhub/1` → id `1`) and the loci.
Fetch metadata:

```bash
curl -s https://api.waooat.cn/project/vhubtarget/<id>/
```

Take `vcf` (e.g. `https://db.waooat.cn/oatdb/vcf/ng_sanfensan_oat2022_gbs.vcf.gz`)
and `vcfcsi` (CSI index path). Both are needed.

### 方案 A — tabix 直查（主方案）

1. Ensure tabix is available:
   - **macOS**: `brew install htslib` or `conda install -c bioconda tabix`
   - **Linux**: `conda install -c bioconda tabix` or system package
   - **Windows**: user PATH → app tool directory → download
     `https://ftps.waooat.cn/soft/htslib/htslib-1.23-windows-x64.zip`
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

### 方案 B — 复用页面 WASM 工具（Windows 备选）

Only when tabix is unavailable on Windows. Reuse the vhub page's biowasm (aioli) +
bcftools 1.10 toolchain in the browser. No local tabix, no install.
Full JS code: [📋 WASM 查询代码](./references/wasm-query.md).

1. Open the vhub page (`browser_navigate` to `https://www.waooat.cn/vhub/<id>/`) and click
   the Variation Search card to init the page.
2. Discover the worker module URL dynamically (hash changes): find `oatbiodbworker-*.js`
   in `performance.getEntriesByType('resource')`.
3. `const mod = await import(workerUrl); const qt = mod.d;` — `qt(cmd, vcfUrl, csiUrl)`
   is the page's internal bcftools query function.
4. Query: `const r = await qt('bcftools view -r <chr>:<pos>-<pos> ', vcf, csi);`
   `r.stdout` is the VCF text (header + variant + sample columns).
5. Parse `r.stdout` in-page to TSV + genotype counts (data never passes through the LLM),
   then display directly to the user.

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
- 方案 B requires the page to stay open (wasm runs in the browser); first query is slow
  (wasm lazy-loads from `https://cdn.waooat.cn/wasm`).
- If `mod.d` is missing (page changed), fall back to 方案 A (tabix).