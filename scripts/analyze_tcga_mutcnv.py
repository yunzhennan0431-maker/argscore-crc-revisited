"""
TCGA-COAD/READ mutation and GISTIC2 thresholded CNV analysis
for the 5 ARGscore genes (VSIG4, CXCL10, CXCL13, MEIS2, ZNF532).
Data source: UCSC Xena classic hub (tcga.xenahubs.net) via xenaPython RPC:
  - mc3_gene_level/{COAD,READ}_mc3_gene_level.txt  (binary gene-level somatic mutation, MC3 calls)
  - TCGA.{COAD,READ}.sampleMap/Gistic2_CopyNumber_Gistic2_all_thresholded.by_genes
    (-2 deep del, -1 shallow del, 0 diploid, 1 gain, 2 amplification)
"""
import csv
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BASE = f"{_PROJECT_ROOT}"
RAW_DIR = f"{_PROJECT_ROOT}/scratch/tcga_mutcnv"
FIG_DIR = os.path.join(BASE, "analysis_output", "figures")
DATA_DIR = os.path.join(BASE, "analysis_output", "data")

GENES = ["VSIG4", "CXCL10", "CXCL13", "MEIS2", "ZNF532"]


def load(path):
    with open(os.path.join(RAW_DIR, path)) as f:
        r = csv.reader(f)
        header = next(r)
        rows = {row[0]: [float(x) if x not in ("", "NA", "nan") else None for x in row[1:]] for row in r}
    return rows


def main():
    mut_coad = load("COAD_mut.csv")
    mut_read = load("READ_mut.csv")
    cnv_coad = load("COAD_cnv.csv")
    cnv_read = load("READ_cnv.csv")

    results = []
    for g in GENES:
        mvals = [v for v in mut_coad[g] if v is not None] + [v for v in mut_read[g] if v is not None]
        n_mut = sum(1 for v in mvals if v == 1)
        mut_freq = n_mut / len(mvals) * 100

        cvals = [v for v in cnv_coad[g] if v is not None] + [v for v in cnv_read[g] if v is not None]
        n_amp = sum(1 for v in cvals if v >= 1)
        n_del = sum(1 for v in cvals if v <= -1)
        n_deep_amp = sum(1 for v in cvals if v == 2)
        n_deep_del = sum(1 for v in cvals if v == -2)
        amp_freq = n_amp / len(cvals) * 100
        del_freq = n_del / len(cvals) * 100

        results.append(dict(
            gene=g, n_mut_samples=len(mvals), n_mut=n_mut, mut_freq=mut_freq,
            n_cnv_samples=len(cvals), n_amp=n_amp, amp_freq=amp_freq,
            n_del=n_del, del_freq=del_freq, n_deep_amp=n_deep_amp, n_deep_del=n_deep_del,
            cna_freq=amp_freq + del_freq,
        ))

    out_csv = os.path.join(DATA_DIR, "tcga_mut_cnv_summary.csv")
    with open(out_csv, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(results[0].keys()))
        w.writeheader()
        w.writerows(results)
    print("saved", out_csv)

    # ---- figure: mutation freq (left) + stacked CNV gain/loss freq (right) ----
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))

    genes = [r["gene"] for r in results]
    mut_freqs = [r["mut_freq"] for r in results]
    amp_freqs = [r["amp_freq"] for r in results]
    del_freqs = [r["del_freq"] for r in results]

    ax = axes[0]
    bars = ax.bar(genes, mut_freqs, color="#4C72B0")
    ax.set_ylabel("Somatic mutation frequency (%)")
    ax.set_title("A. Somatic mutation (MC3), TCGA-COAD+READ, n=380")
    for b, r in zip(bars, results):
        ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 0.3,
                 f"{r['n_mut']}/{r['n_mut_samples']}", ha="center", fontsize=8)
    ax.set_ylim(0, max(mut_freqs) * 1.4 + 1)

    ax = axes[1]
    x = np.arange(len(genes))
    b1 = ax.bar(x, amp_freqs, color="#C44E52", label="Copy-number gain/amplification")
    b2 = ax.bar(x, [-v for v in del_freqs], color="#55A868", label="Copy-number loss/deletion")
    ax.set_xticks(x)
    ax.set_xticklabels(genes)
    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_ylabel("CNV frequency (%)  (gain up / loss down)")
    ax.set_title("B. GISTIC2 thresholded CNV, TCGA-COAD+READ, n=616")
    for xi, r in zip(x, results):
        ax.text(xi, r["amp_freq"] + 1.5, f"{r['amp_freq']:.0f}%", ha="center", fontsize=8)
        ax.text(xi, -r["del_freq"] - 4.5, f"{r['del_freq']:.0f}%", ha="center", fontsize=8)
    ax.legend(loc="upper right", fontsize=8)
    ax.set_ylim(-80, 30)

    fig.suptitle("Somatic alterations of the 5 ARGscore genes in TCGA-COAD/READ", fontsize=12)
    fig.tight_layout()
    out_fig = os.path.join(FIG_DIR, "tcga_mut_cnv_summary.png")
    fig.savefig(out_fig, dpi=200)
    print("saved", out_fig)

    for r in results:
        print(f"{r['gene']}: mut {r['mut_freq']:.1f}% | gain {r['amp_freq']:.1f}% | loss {r['del_freq']:.1f}% | total CNA {r['cna_freq']:.1f}%")


if __name__ == "__main__":
    main()
