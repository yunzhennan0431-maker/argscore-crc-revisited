import numpy as np
import pandas as pd
from scipy.stats import spearmanr, kruskal, mannwhitneyu
import os
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

WORKDIR = f"{_PROJECT_ROOT}/scratch/gse236581"

SIG5 = ["VSIG4", "CXCL10", "CXCL13", "MEIS2", "ZNF532"]
COEF = {"ZNF532": 0.2754, "VSIG4": 0.1833, "MEIS2": 0.1599, "CXCL10": -0.1619, "CXCL13": -0.1215}
MARKERS = {
    "Macrophage_TAM": ["CD68", "CD163", "MRC1", "MSR1", "CSF1R", "C1QA", "C1QB", "APOE"],
    "Endothelial": ["PECAM1", "VWF", "CDH5", "CLDN5", "ENG"],
    "Pericyte": ["RGS5", "ACTA2", "NOTCH3", "PDGFRB", "MYH11", "TAGLN"],
    "CD8T": ["CD8A", "CD8B", "CD3D", "CD3E", "GZMK"],
    "Bcell_TLS": ["MS4A1", "CD79A", "CD79B", "CR2", "CD19"],
}

sums = pd.read_csv(f"{WORKDIR}/pseudobulk_gene_sums.tsv", sep="\t", index_col=0)
umi = pd.read_csv(f"{WORKDIR}/patient_total_umi.tsv", sep="\t", header=None,
                   names=["Patient", "total_umi", "n_cells"], index_col=0)
patient_meta = pd.read_csv("/tmp/gse236581_patient_meta.csv", index_col=0)

df = sums.join(umi)
# CP10K normalization + log1p
cp10k = sums.div(df["total_umi"], axis=0) * 1e4
log_expr = np.log1p(cp10k)

argscore = pd.Series(0.0, index=log_expr.index)
for g, c in COEF.items():
    argscore += c * log_expr[g]

modules = pd.DataFrame(index=log_expr.index)
for mod, genes in MARKERS.items():
    z = (log_expr[genes] - log_expr[genes].mean()) / (log_expr[genes].std() + 1e-9)
    modules[mod] = z.mean(axis=1)

result = pd.DataFrame({"ARGscore": argscore}).join(modules)
result = result.join(patient_meta[["Response", "Tumor Regression Ratio", "dMMR/pMMR", "MSI/MSS"]])
result = result.join(umi[["n_cells"]])
result.to_csv(f"{WORKDIR}/gse236581_argscore_response.csv")
print(result.round(3).to_string())

print("\n=== ARGscore vs Response (CR/PR/SD) ===")
groups = [result.loc[result.Response == r, "ARGscore"].values for r in ["CR", "PR", "SD"]]
groups = [g for g in groups if len(g) > 0]
stat, p = kruskal(*groups)
print(f"Kruskal-Wallis across CR/PR/SD: H={stat:.3f}, P={p:.4g}")
for r in ["CR", "PR", "SD"]:
    vals = result.loc[result.Response == r, "ARGscore"]
    print(f"  {r}: n={len(vals)}, mean={vals.mean():.3f}, median={vals.median():.3f}")

responder = result.loc[result.Response.isin(["CR", "PR"]), "ARGscore"]
nonresponder = result.loc[result.Response == "SD", "ARGscore"]
if len(nonresponder) > 0:
    u, p2 = mannwhitneyu(responder, nonresponder, alternative="two-sided")
    print(f"\nResponder (CR+PR, n={len(responder)}) vs Non-responder (SD, n={len(nonresponder)}): "
          f"Mann-Whitney P={p2:.4g}, responder_mean={responder.mean():.3f}, nonresponder_mean={nonresponder.mean():.3f}")

print("\n=== ARGscore vs continuous Tumor Regression Ratio ===")
r, p3 = spearmanr(result["ARGscore"], result["Tumor Regression Ratio"])
print(f"Spearman rho={r:.4f}, P={p3:.4g}, n={len(result)}")

print("\n=== Module scores vs Tumor Regression Ratio ===")
for mod in MARKERS:
    r, p = spearmanr(result[mod], result["Tumor Regression Ratio"])
    print(f"  {mod}: rho={r:.4f}, P={p:.4g}")

print("\n=== Module scores vs Response (Kruskal-Wallis CR/PR/SD) ===")
for mod in MARKERS:
    groups = [result.loc[result.Response == r, mod].values for r in ["CR", "PR", "SD"]]
    groups = [g for g in groups if len(g) > 0]
    stat, p = kruskal(*groups)
    print(f"  {mod}: H={stat:.3f}, P={p:.4g}")
