#!/usr/bin/env python3
"""
Parse tabix-extracted VCF variant lines into per-sample TSV and genotype summary.

Usage:
    python3 parse_vcf_tsv.py <variant.vcf> <header.txt> <out.tsv>

- <variant.vcf>: output of `tabix <vcf.gz> chr:start-end` (variant lines only)
- <header.txt>: output of `tabix -H <vcf.gz>` (contains #CHROM line with sample names)
- <out.tsv>: per-sample genotype table (Sample / Info / Base)

Prints genotype counts (0/0, 0/1, 1/1, ./.) to stdout.
"""
import sys
from collections import Counter


def parse_vcf(vcf_path, header_path, out_tsv):
    samples = []
    with open(header_path) as f:
        for line in f:
            if line.startswith('#CHROM'):
                samples = line.strip().split('\t')[9:]
                break
    if not samples:
        sys.stderr.write(f"ERROR: no #CHROM header in {header_path}\n")
        sys.exit(1)

    rows = []
    variant_info = None
    with open(vcf_path) as f:
        for line in f:
            if line.startswith('#'):
                continue
            parts = line.strip().split('\t')
            chrom, pos, vid, ref, alt = parts[0], parts[1], parts[2], parts[3], parts[4]
            fmt_keys = parts[8].split(':')
            samples_data = parts[9:]
            variant_info = f"{chrom}\t{pos}\t{vid}\t{ref}\t{alt}\t{parts[8]}"
            for name, sd in zip(samples, samples_data):
                fields = dict(zip(fmt_keys, sd.split(':')))
                gt = fields.get('GT', './.')
                if gt == '0/0':
                    base = ref
                elif gt in ('0/1', '1/0'):
                    base = ref + '|' + alt
                elif gt == '1/1':
                    base = alt
                else:
                    base = '.'
                rows.append((name, sd, base))

    with open(out_tsv, 'w') as f:
        f.write('Sample\tInfo\tBase\n')
        for name, sd, base in rows:
            f.write(f"{name}\t{sd}\t{base}\n")

    if variant_info:
        with open(out_tsv + '.variant.txt', 'w') as vf:
            vf.write(variant_info + '\n')

    gt_counter = Counter(sd.split(':')[0] for _, sd, _ in rows)
    return len(rows), gt_counter


if __name__ == '__main__':
    if len(sys.argv) != 4:
        print("Usage: python3 parse_vcf_tsv.py <variant.vcf> <header.txt> <out.tsv>", file=sys.stderr)
        sys.exit(1)
    n, counter = parse_vcf(sys.argv[1], sys.argv[2], sys.argv[3])
    print(f"{sys.argv[3]}: {n} samples")
    for gt, cnt in sorted(counter.items()):
        print(f"  {gt}: {cnt}")
