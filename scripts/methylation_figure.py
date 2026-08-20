import os
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.stats import spearmanr
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BASE = f"{_PROJECT_ROOT}"
DATA_DIR = os.path.join(BASE, "analysis_output", "data")
FIG_DIR = os.path.join(BASE, "analysis_output", "figures")

GENES = ["VSIG4", "CXCL10", "CXCL13", "MEIS2", "ZNF532"]
probe_df = pd.read_csv(os.path.join(DATA_DIR, "methylation_probe_level_summary.csv"))
gene_summary = pd.read_csv(os.path.join(DATA_DIR, "methylation_gene_avg_summary.csv"))

fig, axes = plt.subplots(1, 2, figsize=(13, 5))

# Panel A: best (most negative) probe rho per gene, bar chart
ax = axes[0]
best_rows = []
for g in GENES:
    sub = probe_df[probe_df.gene == g].sort_values("rho_meth_vs_expr")
    best_rows.append(sub.iloc[0])
best = pd.DataFrame(best_rows)
colors = ["#C44E52" if p < 0.05 else "#999999" for p in best["p_meth_vs_expr_fdr"]]
bars = ax.bar(best["gene"], best["rho_meth_vs_expr"], color=colors)
ax.axhline(0, color="black", linewidth=0.8)
ax.set_ylabel("Spearman rho (CpG methylation vs. mRNA expression)")
ax.set_title("A. Most negatively-correlated CpG probe per gene\n(candidate functional/promoter CpG), TCGA-COAD+READ n=370")
for b, (_, r) in zip(bars, best.iterrows()):
    ax.text(b.get_x() + b.get_width() / 2, b.get_height() - 0.03 if b.get_height() < 0 else b.get_height() + 0.02,
            f"{r['probe']}\nq={r['p_meth_vs_expr_fdr']:.1e}", ha="center", va="top" if b.get_height() < 0 else "bottom", fontsize=7)
ax.set_ylim(-0.6, 0.1)

# Panel B: ZNF532 top-probe methylation vs expression scatter (strongest, most relevant gene)
gene = "ZNF532"
full = pd.read_csv(os.path.join(DATA_DIR, f"methylation_{gene}_full.csv"), index_col=0)
top_probe = probe_df[probe_df.gene == gene].sort_values("rho_meth_vs_expr").iloc[0]["probe"]
sub = full[[top_probe, gene]].dropna()
r, p = spearmanr(sub[top_probe], sub[gene])

ax = axes[1]
ax.scatter(sub[top_probe], sub[gene], alpha=0.35, s=14, color="#4C72B0")
z = np.polyfit(sub[top_probe], sub[gene], 1)
xs = np.linspace(sub[top_probe].min(), sub[top_probe].max(), 50)
ax.plot(xs, np.polyval(z, xs), color="#C44E52", linewidth=2)
ax.set_xlabel(f"{top_probe} methylation beta value")
ax.set_ylabel(f"{gene} log2(RSEM+1) expression")
ax.set_title(f"B. ZNF532 promoter CpG methylation vs. expression\n"
             f"TCGA-COAD+READ, rho={r:.2f}, P={p:.1e}, n={len(sub)}")

fig.suptitle("DNA methylation as a candidate upstream regulatory layer for the 5 ARGscore genes", fontsize=12)
fig.tight_layout()
fig.savefig(os.path.join(FIG_DIR, "methylation_upstream_regulation.png"), dpi=200)
print("saved figure")
print(best[["gene", "probe", "rho_meth_vs_expr", "p_meth_vs_expr_fdr"]].to_string(index=False))
