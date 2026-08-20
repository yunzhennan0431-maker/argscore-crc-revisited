# -*- coding: utf-8 -*-
import glob
import numpy as np
import pandas as pd
import scipy.io as sio
from scipy import stats
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

meta = pd.read_csv("sample_metadata.csv")
print("Samples:", meta.shape[0])

SIG5 = ["VSIG4", "CXCL10", "CXCL13", "MEIS2", "ZNF532"]
MARKERS = {
    "Macrophage_TAM": ["CD68", "CD163", "MRC1", "MSR1", "CSF1R"],
    "Endothelial": ["PECAM1", "VWF", "CDH5"],
    "Pericyte": ["RGS5", "ACTA2", "NOTCH3", "PDGFRB"],
    "CD8T": ["CD8A", "CD8B"],
    "Bcell_TLS": ["MS4A1", "CD79A", "CR2"],
}
TARGETS = set(SIG5)
for v in MARKERS.values():
    TARGETS.update(v)

pseudobulk = {}
total_counts = {}
for _, row in meta.iterrows():
    gsm = row["gsm"]
    feat_files = glob.glob(f"{gsm}_*_features.tsv.gz")
    mtx_files = glob.glob(f"{gsm}_*_matrix.mtx.gz")
    if not feat_files or not mtx_files:
        print("MISSING", gsm)
        continue
    features = pd.read_csv(feat_files[0], sep="\t", header=None, names=["ensembl", "symbol", "type"])
    mat = sio.mmread(mtx_files[0]).tocsr()  # genes x cells
    gene_sums = np.asarray(mat.sum(axis=1)).flatten()
    total = gene_sums.sum()
    total_counts[gsm] = total

    sym2idx = {}
    for i, sym in enumerate(features["symbol"]):
        sym2idx.setdefault(sym, []).append(i)

    row_vals = {}
    for g in TARGETS:
        if g in sym2idx:
            row_vals[g] = gene_sums[sym2idx[g]].sum()
        else:
            row_vals[g] = np.nan
    pseudobulk[gsm] = row_vals
    print(f"{gsm}: total_counts={total:.0f}, n_cells={mat.shape[1]}")

pb_df = pd.DataFrame(pseudobulk).T  # samples x genes (raw summed counts)
totals = pd.Series(total_counts)
cpm = pb_df.div(totals, axis=0) * 1e6
lognorm = np.log1p(cpm)

lognorm = lognorm.join(meta.set_index("gsm")[["subject", "tissue", "genotype", "treatment"]])
lognorm.to_csv("icb_pseudobulk_lognorm.csv")
print("\nSaved icb_pseudobulk_lognorm.csv, shape:", lognorm.shape)

z = (lognorm[list(TARGETS)] - lognorm[list(TARGETS)].mean()) / lognorm[list(TARGETS)].std()
SIG5_WEIGHTS = {"ZNF532": 0.2754, "VSIG4": 0.1833, "MEIS2": 0.1599, "CXCL10": -0.1619, "CXCL13": -0.1215}
argscore = sum(lognorm[g] * w for g, w in SIG5_WEIGHTS.items())
module_scores = {m: z[genes].mean(axis=1) for m, genes in MARKERS.items()}
result = pd.DataFrame(module_scores)
result["ARGscore"] = argscore
result = result.join(meta.set_index("gsm")[["subject", "tissue", "genotype", "treatment"]])
result.to_csv("icb_result.csv")
print(result.groupby(["genotype", "treatment"]).size())

# tumor-only comparison across treatment groups
tumor = result[result["genotype"] == "tumor"].copy()
treat_order = ["untreated", "anti-PD-1", "Anti-PD-1+celecoxib"]
tumor["treatment"] = pd.Categorical(tumor["treatment"], categories=treat_order, ordered=True)

print("\n=== Kruskal-Wallis across treatment groups (tumor samples only) ===")
metrics = ["ARGscore"] + list(MARKERS.keys())
for m in metrics:
    groups = [tumor[tumor["treatment"] == t][m].dropna().values for t in treat_order]
    groups = [g for g in groups if len(g) > 0]
    if len(groups) >= 2:
        stat, pval = stats.kruskal(*groups)
        means = [f"{t}: n={len(g)}, mean={g.mean():.2f}" for t, g in zip(treat_order, groups)]
        print(f"{m}: H={stat:.2f} p={pval:.3f} | " + " | ".join(means))

# plot
fig, axes = plt.subplots(1, 6, figsize=(22, 4.2))
for ax, m in zip(axes, metrics):
    data = [tumor[tumor["treatment"] == t][m].dropna().values for t in treat_order]
    ax.boxplot(data, labels=["Untreated", "anti-PD-1", "anti-PD-1\n+celecoxib"])
    for i, d in enumerate(data):
        x = np.random.normal(i + 1, 0.05, size=len(d))
        ax.scatter(x, d, s=15, alpha=0.6, color="#c0392b")
    ax.set_title(m, fontsize=10)
fig.suptitle("GSE205506 (dMMR/MSI-H CRC, neoadjuvant PD-1 blockade, pseudobulk): ARGscore & modules by treatment (tumor samples)", y=1.05)
plt.tight_layout()
plt.savefig("icb_treatment_comparison.png", dpi=150, bbox_inches="tight")
print("\nSaved icb_treatment_comparison.png")

# tumor vs normal (paired-ish, within treated groups)
print("\n=== tumor vs normal (all treated samples) ===")
for m in metrics:
    tum = result[result["genotype"] == "tumor"][m].dropna()
    nor = result[result["genotype"] == "normal"][m].dropna()
    u, p = stats.mannwhitneyu(tum, nor)
    print(f"{m}: tumor mean={tum.mean():.2f} (n={len(tum)}) | normal mean={nor.mean():.2f} (n={len(nor)}) | p={p:.3f}")
