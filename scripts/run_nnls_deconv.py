"""
NNLS-based formal deconvolution of bulk cohorts (GSE39582, GSE17536, TCGA-COAD/READ)
using a cell-type reference signature matrix built from the Pelka et al. 2021 Cell
CRC single-cell atlas (GSE178341), as a formal alternative to the simplified
marker-gene z-score averaging used previously.

Method: per-gene min-max normalization of both reference (across cell types) and
bulk (across samples within a cohort) to [0,1], then non-negative least squares
(scipy.optimize.nnls) per sample against the marker panel, followed by
sum-to-1 normalization of the resulting cell-type fraction vector (as in CIBERSORT).
"""
import json
import numpy as np
import pandas as pd
from scipy.optimize import nnls
from scipy.stats import pearsonr, spearmanr

SIG5 = ["VSIG4", "CXCL10", "CXCL13", "MEIS2", "ZNF532"]
COEF = {"ZNF532": 0.2754, "VSIG4": 0.1833, "MEIS2": 0.1599, "CXCL10": -0.1619, "CXCL13": -0.1215}
MARKERS = {
    "Macrophage_TAM": ["CD68", "CD163", "MRC1", "MSR1", "CSF1R", "C1QA", "C1QB", "APOE"],
    "Endothelial": ["PECAM1", "VWF", "CDH5", "CLDN5", "ENG"],
    "Pericyte": ["RGS5", "ACTA2", "NOTCH3", "PDGFRB", "MYH11", "TAGLN"],
    "CD8T": ["CD8A", "CD8B", "CD3D", "CD3E", "GZMK"],
    "Bcell_TLS": ["MS4A1", "CD79A", "CD79B", "CR2", "CD19"],
    "Epithelial": ["EPCAM", "KRT8", "KRT18", "KRT19"],
    "Fibroblast": ["COL1A1", "COL1A2", "DCN", "LUM"],
}
ALL_MARKERS = [g for v in MARKERS.values() for g in v]

ref = pd.read_csv("pelka_reference_signature_linear.csv", index_col=0)  # genes x celltypes, linear
ref = ref.loc[[g for g in ALL_MARKERS if g in ref.index]]
celltypes = list(ref.columns)
print("Reference:", ref.shape, "celltypes:", celltypes)

ref_norm = (ref - ref.min(axis=1).values.reshape(-1, 1))
denom = (ref.max(axis=1) - ref.min(axis=1)).replace(0, 1)
ref_norm = ref_norm.div(denom, axis=0)  # min-max per gene across celltypes, [0,1]
S = ref_norm.values  # genes x celltypes


def collapse_probes_to_gene(expr_probe_df, gene2probes, genes):
    rows = {}
    for g in genes:
        probes = [p for p in gene2probes.get(g, []) if p in expr_probe_df.index]
        if not probes:
            continue
        rows[g] = expr_probe_df.loc[probes].mean(axis=0)
    return pd.DataFrame(rows).T


def deconvolve_cohort(gene_expr_df, tag):
    """gene_expr_df: genes x samples, LINEAR scale."""
    genes_avail = [g for g in ref.index if g in gene_expr_df.index]
    X = gene_expr_df.loc[genes_avail]
    Sg = ref_norm.loc[genes_avail].values

    Xn = X.sub(X.min(axis=1), axis=0)
    denom_x = (X.max(axis=1) - X.min(axis=1)).replace(0, 1)
    Xn = Xn.div(denom_x, axis=0)

    fractions = {}
    for sample in Xn.columns:
        b = Xn[sample].values
        f, _ = nnls(Sg, b)
        if f.sum() > 0:
            f = f / f.sum()
        fractions[sample] = f
    frac_df = pd.DataFrame(fractions, index=celltypes).T
    frac_df.to_csv(f"nnls_fractions_{tag}.csv")
    print(tag, "fractions:", frac_df.shape)
    return frac_df


def compute_argscore(gene_expr_df_log2):
    """gene_expr_df_log2: genes(SIG5) x samples, log2 scale (as used in original model)."""
    score = pd.Series(0.0, index=gene_expr_df_log2.columns)
    for g, c in COEF.items():
        if g in gene_expr_df_log2.index:
            score += c * gene_expr_df_log2.loc[g]
    return score


results_summary = []

# ---------- GSE39582 ----------
print("\n=== GSE39582 ===")
expr39582 = pd.read_csv("GSE39582_panel_probe_expr.csv", index_col=0)
with open("GSE39582_gene2probes.json") as f:
    g2p_39582 = json.load(f)
gene_log2_39582 = collapse_probes_to_gene(expr39582, g2p_39582, ref.index.tolist() + SIG5)
gene_lin_39582 = 2 ** gene_log2_39582
frac_39582 = deconvolve_cohort(gene_lin_39582, "GSE39582")
argscore_39582 = compute_argscore(gene_log2_39582.loc[SIG5])

# ---------- GSE17536 ----------
print("\n=== GSE17536 ===")
expr17536 = pd.read_csv("GSE17536_panel_probe_expr.csv", index_col=0)
with open("GSE17536_gene2probes.json") as f:
    g2p_17536 = json.load(f)
gene_log2_17536 = collapse_probes_to_gene(expr17536, g2p_17536, ref.index.tolist() + SIG5)
gene_lin_17536 = 2 ** gene_log2_17536
frac_17536 = deconvolve_cohort(gene_lin_17536, "GSE17536")
argscore_17536 = compute_argscore(gene_log2_17536.loc[SIG5])

# ---------- TCGA COAD+READ ----------
print("\n=== TCGA COAD+READ ===")
coad = pd.read_csv("TCGA_COAD_panel_expr.csv", index_col=0)
read = pd.read_csv("TCGA_READ_panel_expr.csv", index_col=0)
tcga_log2 = pd.concat([coad, read], axis=1)
tcga_lin = 2 ** tcga_log2 - 1
tcga_lin[tcga_lin < 0] = 0
frac_tcga = deconvolve_cohort(tcga_lin, "TCGA_COADREAD")
argscore_tcga = compute_argscore(tcga_log2.loc[SIG5])

# ---------- correlations: NNLS fraction vs ARGscore ----------
cohorts = [
    ("GSE39582", frac_39582, argscore_39582),
    ("GSE17536", frac_17536, argscore_17536),
    ("TCGA_COADREAD", frac_tcga, argscore_tcga),
]

for tag, frac_df, argscore in cohorts:
    common = frac_df.index.intersection(argscore.index)
    frac_df = frac_df.loc[common]
    argscore_c = argscore.loc[common]
    for ct in celltypes:
        r, p = pearsonr(frac_df[ct], argscore_c)
        rho, ps = spearmanr(frac_df[ct], argscore_c)
        results_summary.append(dict(cohort=tag, celltype=ct, n=len(common),
                                     pearson_r=r, pearson_p=p, spearman_rho=rho, spearman_p=ps))

summary_df = pd.DataFrame(results_summary)
summary_df.to_csv("nnls_argscore_correlation_summary.csv", index=False)
pd.set_option("display.width", 160)
print("\n=== NNLS fraction vs ARGscore correlation summary ===")
print(summary_df.round(4).to_string(index=False))
