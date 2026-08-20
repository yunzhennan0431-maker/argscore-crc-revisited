import os
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BASE = f"{_PROJECT_ROOT}"
DATA_DIR = os.path.join(BASE, "analysis_output", "data")
FIG_DIR = os.path.join(BASE, "analysis_output", "figures")

df = pd.read_csv(os.path.join(DATA_DIR, "argscore_tf_correlation_tcga.csv"))
df = df[~df.is_signature_gene]

top_pos = df.sort_values("spearman_rho", ascending=False).head(15)
top_neg = df.sort_values("spearman_rho").head(15)
plot_df = pd.concat([top_pos, top_neg]).sort_values("spearman_rho")

highlight = {"GLI2", "GLI3", "PRDM6", "HAND2", "MEIS1", "MEIS3", "ZEB1"}
colors = ["#C44E52" if r < 0 else "#4C72B0" for r in plot_df["spearman_rho"]]
edge = ["black" if t in highlight else "none" for t in plot_df["TF"]]

fig, ax = plt.subplots(figsize=(7, 8))
bars = ax.barh(plot_df["TF"], plot_df["spearman_rho"], color=colors, edgecolor=edge, linewidth=1.5)
ax.axvline(0, color="black", linewidth=0.8)
ax.set_xlabel("Spearman rho (TF expression vs. ARGscore)")
ax.set_title("Top curated-TF (n=1639) correlates of ARGscore\n"
             "TCGA-COAD+READ, n=380, all FDR<1e-10\n"
             "black outline = pericyte/vascular-mesenchyme-related TFs", fontsize=10)
fig.tight_layout()
fig.savefig(os.path.join(FIG_DIR, "argscore_tf_correlation_top.png"), dpi=200)
print("saved figure")
