import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BASE = f"{_PROJECT_ROOT}"
DATA_DIR = os.path.join(BASE, "analysis_output", "data")
FIG_DIR = os.path.join(BASE, "analysis_output", "figures")

df = pd.read_csv(os.path.join(DATA_DIR, "nnls_argscore_correlation_summary.csv"))

cohort_order = ["GSE39582", "GSE17536", "TCGA_COADREAD"]
cohort_labels = {"GSE39582": "GSE39582\n(n=585)", "GSE17536": "GSE17536\n(n=177)", "TCGA_COADREAD": "TCGA-COAD/READ\n(n=434)"}
ct_order = ["Pericyte", "Endothelial", "Macrophage_TAM", "CD8T", "Bcell_TLS", "Fibroblast", "Epithelial"]

fig, ax = plt.subplots(figsize=(10, 5.5))
n_ct = len(ct_order)
width = 0.8 / len(cohort_order)
x = np.arange(n_ct)
colors = ["#4C72B0", "#55A868", "#C44E52"]

for i, cohort in enumerate(cohort_order):
    sub = df[df.cohort == cohort].set_index("celltype").loc[ct_order]
    r = sub["pearson_r"].values
    p = sub["pearson_p"].values
    bars = ax.bar(x + i * width - width, r, width=width, label=cohort_labels[cohort], color=colors[i])
    for xi, (rv, pv) in zip(x + i * width - width, zip(r, p)):
        star = "***" if pv < 0.001 else "**" if pv < 0.01 else "*" if pv < 0.05 else "ns"
        ax.text(xi, rv + (0.02 if rv >= 0 else -0.05), star, ha="center", fontsize=8,
                 va="bottom" if rv >= 0 else "top")

ax.axhline(0, color="black", linewidth=0.8)
ax.set_xticks(x)
ax.set_xticklabels(ct_order, rotation=20, ha="right")
ax.set_ylabel("Pearson r (NNLS cell-type fraction vs. ARGscore)")
ax.set_title("Formal NNLS deconvolution: cell-type fraction vs. ARGscore\n(reference signature built from Pelka et al. 2021 CRC atlas, GSE178341)")
ax.legend(loc="upper right", fontsize=8, ncol=1)
ax.set_ylim(-0.8, 0.65)
fig.tight_layout()
out = os.path.join(FIG_DIR, "nnls_deconv_argscore_correlation.png")
fig.savefig(out, dpi=200)
print("saved", out)
