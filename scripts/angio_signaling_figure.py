import os
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BASE = f"{_PROJECT_ROOT}"
DATA_DIR = os.path.join(BASE, "analysis_output", "data")
FIG_DIR = os.path.join(BASE, "analysis_output", "figures")

df = pd.read_csv(os.path.join(DATA_DIR, "argscore_angiogenic_signaling_correlation.csv")).sort_values("spearman_rho", ascending=False)
comp = pd.read_csv(os.path.join(DATA_DIR, "argscore_angio_signaling_vs_structural_comparison.csv"))

fig, axes = plt.subplots(1, 2, figsize=(14, 6), gridspec_kw={"width_ratios": [2, 1]})

ax = axes[0]
colors = ["#C44E52" if g == "VEGFA" else ("#999999" if p >= 0.05 else "#4C72B0") for g, p in zip(df["gene"], df["p_fdr_bh"])]
bars = ax.barh(df["gene"], df["spearman_rho"], color=colors)
ax.axvline(0, color="black", linewidth=0.8)
ax.invert_yaxis()
ax.set_xlabel("Spearman rho (gene expression vs. ARGscore)")
ax.set_title("A. Core angiogenic ligand-receptor genes vs. ARGscore\nTCGA-COAD+READ, n=380 (red = VEGFA, grey = not FDR-significant)", fontsize=10)

ax = axes[1]
labels = ["Angio-\nSignaling\n(n=23)", "Endothelial\nstructural\n(n=3)", "Pericyte\nstructural\n(n=4)"]
vals = comp["rho_vs_ARGscore"].values
bars2 = ax.bar(labels, vals, color=["#4C72B0", "#55A868", "#8172B2"])
ax.set_ylabel("Spearman rho vs. ARGscore")
ax.set_title("B. Module-level comparison", fontsize=10)
for b, v in zip(bars2, vals):
    ax.text(b.get_x() + b.get_width() / 2, v + 0.01, f"{v:.2f}", ha="center", fontsize=9)
ax.set_ylim(0, 0.75)

fig.suptitle("Downstream check: does ARGscore track active angiogenic signaling or vascular cell abundance?", fontsize=11)
fig.tight_layout()
fig.savefig(os.path.join(FIG_DIR, "argscore_angiogenic_signaling_downstream.png"), dpi=200)
print("saved figure")
