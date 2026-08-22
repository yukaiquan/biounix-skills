# 复用页面 WASM 工具查询位点（Windows 优先）

OatBioDB 的 vhub 页面本身用 **biowasm (aioli) + htslib/bcftools 1.10 (WebAssembly)** 在浏览器内
直接读取远程 VCF.gz + CSI 索引查询位点。我们可以在页面上下文**直接复用这套工具**，完全不需要
本地 tabix、不需要下载安装任何东西。**Windows 环境优先使用本方案。**

## 原理

- 页面 worker 模块 `oatbiodbworker-<hash>.js` 导出 `d` 函数（页面内部叫 `qt`），封装了：
  `new aioli([bcftools 1.10])` → mount 远程 VCF/CSI URL → `bcftools view -r <region>`。
- wasm 工具从 `https://cdn.waooat.cn/wasm` 懒加载（首次查询时自动下载到浏览器缓存）。
- 前提：**页面需保持打开**（wasm 在浏览器内运行）。

## 步骤

### 1. 打开目标 vhub 页面
`browser_navigate` 到用户给的地址（如 `https://www.waooat.cn/vhub/1/`），并点击
Variation Search 卡片（XPath `//*[@id="pageView"]/div[1]/div/div[2]`）确保页面功能已初始化。

### 2. 发现 worker 模块 URL（hash 会变，必须动态发现）
从 `performance.getEntriesByType('resource')` 中找 `oatbiodbworker-*.js`：

```js
const workerUrl = performance.getEntriesByType('resource')
  .map(e => e.name)
  .find(n => /oatbiodbworker-.*\.js$/.test(n));
```

### 3. 动态 import worker 模块，拿到查询函数
```js
const mod = await import(workerUrl);
const qt = mod.d;   // 页面内部 qt 函数：qt(cmd, vcfUrl, csiUrl) => {stdout, stderr}
```

### 4. 从 API 获取目标库 VCF/CSI 路径
```js
const meta = await (await fetch('https://api.waooat.cn/project/vhubtarget/<id>/')).json();
const vcf = meta.vcf;       // 如 https://db.waooat.cn/oatdb/vcf/ng_sanfensan_oat2022_gbs.vcf.gz
const csi = meta.vcfcsi;    // 对应 CSI 索引
```

### 5. 查询位点并解析
```js
const r = await qt(`bcftools view -r ${chr}:${pos}-${pos} `, vcf, csi);
// r.stdout 为 VCF 文本（含 #CHROM 表头行 + 变异行 + 666 个样本列）
// r.stderr 通常有无害警告（如 PL 声明），可忽略
```

### 6. 解析 VCF 输出为 TSV + 基因型统计
用 `browser_eval` 在页面里直接解析 `r.stdout`（数据不经过大模型）：

```js
const lines = r.stdout.split('\n');
const headerLine = lines.find(l => l.startsWith('#CHROM'));
const samples = headerLine ? headerLine.split('\t').slice(9) : [];
const variant = lines.filter(l => l && !l.startsWith('#'));
const rows = [];
const gtCount = {};
if (variant.length) {
  const f = variant[0].split('\t');
  const ref = f[3], alt = f[4];
  const fmtIdx = f[8].split(':').indexOf('GT');
  for (let i = 9; i < f.length; i++) {
    const gt = f[i].split(':')[fmtIdx];
    gtCount[gt] = (gtCount[gt] || 0) + 1;
    const base = gt === '0/0' ? ref : gt === '1/1' ? alt : gt === '0/1' || gt === '1/0' ? ref + '|' + alt : '.';
    rows.push(samples[i - 9] + '\t' + f[i] + '\t' + base);
  }
}
const tsv = 'Sample\tInfo\tBase\n' + rows.join('\n');
// tsv 即完整基因型表；gtCount 即基因型统计
```

### 7. 落盘 TSV（可选）
把 `tsv` 内容 POST 到本地接收服务（用技能自带 `scripts/receive_tsv.py`）写文件，
或直接展示给用户。落盘方式与 tabix 方案一致。

## 注意事项
- worker 文件名带 hash（如 `oatbiodbworker-hneaYbkB.js`），**每次都要动态发现**，不要硬编码。
- 查询函数 `qt` 的调用签名：`qt(cmd, vcfUrl, csiUrl)`，cmd 结尾带空格（如
  `'bcftools view -r chr1A:5127200-5127200 '`）。
- 位点格式 `chr:pos-pos`（End 包含边界，单一位点不要 +1）。
- 首次查询 wasm 懒加载需几秒，属正常。
- 若 `mod.d` 不存在（页面改版），回退到 tabix 直查方案（见 SKILL.md 方案 B）。
