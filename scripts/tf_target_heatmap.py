import os
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BASE = f"{_PROJECT_ROOT}"
DATA_DIR = os.path.join(BASE, "analysis_output", "data")
FIG_DIR = os.path.join(BASE, "analysis_output", "figures")

df = pd.read_csv(os.path.join(DATA_DIR, "tf_target_correlation_tcga.csv"))
SIG5 = ["VSIG4", "CXCL10", "CXCL13", "MEIS2", "ZNF532"]
tfs = sorted(df["TF"].unique(), key=lambda t: df[df.TF == t]["p"].min())

mat = pd.DataFrame(np.nan, index=tfs, columns=SIG5)
sig = pd.DataFrame("", index=tfs, columns=SIG5)
for _, r in df.iterrows():
    mat.loc[r["TF"], r["target"]] = r["spearman_rho"]
    stars = "***" if r["p_fdr_bh"] < 0.001 else "**" if r["p_fdr_bh"] < 0.01 else "*" if r["p_fdr_bh"] < 0.05 else ""
    sig.loc[r["TF"], r["target"]] = stars

fig, ax = plt.subplots(figsize=(6, 8))
vmax = np.nanmax(np.abs(mat.values))
im = ax.imshow(mat.values, cmap="RdBu_r", vmin=-vmax, vmax=vmax, aspect="auto")
ax.set_xticks(range(len(SIG5)))
ax.set_xticklabels(SIG5, rotation=30, ha="right")
ax.set_yticks(range(len(tfs)))
ax.set_yticklabels(tfs)
for i in range(len(tfs)):
    for j in range(len(SIG5)):
        v = mat.values[i, j]
        if not np.isnan(v):
            ax.text(j, i, f"{v:.2f}{sig.values[i, j]}", ha="center", va="center", fontsize=7,
                    color="white" if abs(v) > vmax * 0.6 else "black")
cbar = fig.colorbar(im, ax=ax, shrink=0.6)
cbar.set_label("Spearman rho (TF vs. target expression)")
ax.set_title("Candidate upstream TF vs. ARGscore-gene expression\n"
             "TCGA-COAD+READ, n=434 (Enrichr TRRUST/ChEA/TF-Perturbation pairs)\n"
             "*q<0.05 **q<0.01 ***q<0.001 (BH-FDR)", fontsize=10)
fig.tight_layout()
fig.savefig(os.path.join(FIG_DIR, "tf_target_correlation_heatmap.png"), dpi=200)
print("saved figure")
