"""
Figure for the ESTIMATE tumor-purity-algorithm cross-validation (3.24): ARGscore
vs ssGSEA-derived StromalScore in the three bulk cohorts, mirroring the visual
style of the existing CIBERSORT cross-validation figure (validate_against_original_cibersort.py).
"""
import os
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.stats import spearmanr

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BASE = f"{_PROJECT_ROOT}"
DATA_DIR = os.path.join(BASE, "analysis_output", "data")
FIG_DIR = os.path.join(BASE, "analysis_output", "figures")

COHORTS = {
    "GSE39582": ("bulk_closure_result.csv", "#4C72B0"),
    "GSE17536": ("gse17536_closure_result.csv", "#55A868"),
    "TCGA_COADREAD": ("tcga_coadread_closure_result.csv", "#C44E52"),
}

fig, axes = plt.subplots(1, 3, figsize=(15, 4.5))
score_cols = ["StromalSignature", "ImmuneSignature", "ESTIMATEScore"]
titles = ["ssGSEA StromalScore", "ssGSEA ImmuneScore", "ESTIMATEScore\n(Stromal+Immune)"]

for ax, col, title in zip(axes, score_cols, titles):
    for cohort, (closure_f, color) in COHORTS.items():
        closure = pd.read_csv(os.path.join(DATA_DIR, closure_f), index_col=0)
        scores = pd.read_csv(os.path.join(DATA_DIR, f"estimate_scores_{cohort}.csv"), index_col=0)
        common = closure.index.intersection(scores.index)
        x = closure.loc[common, "ARGscore"]
        y = scores.loc[common, col]
        rho, p = spearmanr(x, y)
        ax.scatter(x, y, s=8, alpha=0.4, color=color, label=f"{cohort} (ρ={rho:.2f})")
    ax.set_xlabel("ARGscore")
    ax.set_ylabel(title)
    ax.legend(fontsize=7.5)

fig.suptitle("ARGscore vs ESTIMATE algorithm (ssGSEA StromalScore/ImmuneScore/ESTIMATEScore)")
fig.tight_layout()
out = os.path.join(FIG_DIR, "estimate_crossvalidation.png")
fig.savefig(out, dpi=200)
print("saved", out)
