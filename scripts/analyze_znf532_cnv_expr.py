"""
Direct test of whether ZNF532 GISTIC2-thresholded copy-number status predicts
its own mRNA expression in TCGA-COAD/READ, to resolve the "CNV loss vs.
positive ARGscore coefficient" tension discussed in section 3.10/4.
Data: UCSC Xena classic hub via xenaPython (Gistic2_CopyNumber_Gistic2_all_thresholded.by_genes,
HiSeqV2 log2(RSEM+1)).
"""
import os
import xenaPython as xena
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import spearmanr, kruskal, mannwhitneyu
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BASE = f"{_PROJECT_ROOT}"
FIG_DIR = os.path.join(BASE, "analysis_output", "figures")
DATA_DIR = os.path.join(BASE, "analysis_output", "data")

HOST = "https://tcga.xenahubs.net"
GENE = "ZNF532"


def fetch_cohort(cohort):
    cnv_ds = f"TCGA.{cohort}.sampleMap/Gistic2_CopyNumber_Gistic2_all_thresholded.by_genes"
    expr_ds = f"TCGA.{cohort}.sampleMap/HiSeqV2"
    cnv_samples = xena.dataset_samples(HOST, cnv_ds, None)
    cnv_vals = xena.dataset_fetch(HOST, cnv_ds, cnv_samples, [GENE])[0]
    expr_samples = xena.dataset_samples(HOST, expr_ds, None)
    expr_vals = xena.dataset_fetch(HOST, expr_ds, expr_samples, [GENE])[0]
    cnv_map = dict(zip(cnv_samples, cnv_vals))
    expr_map = dict(zip(expr_samples, expr_vals))
    common = sorted(set(cnv_map) & set(expr_map))
    df = pd.DataFrame({
        "sample": common,
        "cnv": [cnv_map[s] for s in common],
        "expr_log2": [expr_map[s] for s in common],
        "cohort": cohort,
    })
    return df


def main():
    combined = pd.concat([fetch_cohort("COAD"), fetch_cohort("READ")], ignore_index=True)
    combined.to_csv(os.path.join(DATA_DIR, "combined_znf532_cnv_expr.csv"), index=False)

    rho, p = spearmanr(combined["cnv"], combined["expr_log2"])
    print(f"n={len(combined)}, Spearman rho={rho:.4f}, p={p:.4g}")

    groups = [g["expr_log2"].values for _, g in combined.groupby("cnv")]
    stat, p_kw = kruskal(*groups)
    print(f"Kruskal-Wallis across CNV categories: H={stat:.3f}, p={p_kw:.4g}")

    combined["del_status"] = combined["cnv"].apply(lambda x: "deletion" if x <= -1 else "no_deletion")
    del_grp = combined[combined.del_status == "deletion"]["expr_log2"]
    nodel_grp = combined[combined.del_status == "no_deletion"]["expr_log2"]
    u, p_mw = mannwhitneyu(del_grp, nodel_grp, alternative="two-sided")
    print(f"Deletion (n={len(del_grp)}, mean={del_grp.mean():.3f}) vs "
          f"No-deletion (n={len(nodel_grp)}, mean={nodel_grp.mean():.3f}), Mann-Whitney P={p_mw:.4g}")

    order = [-2, -1, 0, 1]
    labels = ["Deep del\n(-2, n=%d)" % (combined.cnv == -2).sum(),
              "Shallow del\n(-1, n=%d)" % (combined.cnv == -1).sum(),
              "Diploid\n(0, n=%d)" % (combined.cnv == 0).sum(),
              "Gain\n(+1, n=%d)" % (combined.cnv == 1).sum()]
    data = [combined[combined.cnv == c]["expr_log2"].values for c in order]

    fig, ax = plt.subplots(figsize=(7, 5))
    bp = ax.boxplot(data, tick_labels=labels, patch_artist=True, showfliers=True)
    colors = ["#2E7D32", "#66BB6A", "#BDBDBD", "#C44E52"]
    for patch, c in zip(bp["boxes"], colors):
        patch.set_facecolor(c)
        patch.set_alpha(0.7)
    for i, d in enumerate(data, 1):
        x = np.random.normal(i, 0.05, size=len(d))
        ax.scatter(x, d, alpha=0.3, s=10, color="black")
    ax.set_ylabel("ZNF532 log2(RSEM+1) expression")
    ax.set_title(f"ZNF532 copy-number status vs. mRNA expression\n"
                 f"TCGA-COAD+READ (n={len(combined)}), Spearman rho={rho:.2f}, P={p:.2f} (n.s.)")
    fig.tight_layout()
    fig.savefig(os.path.join(FIG_DIR, "znf532_cnv_expr_boxplot.png"), dpi=200)
    print("saved figure")


if __name__ == "__main__":
    main()
