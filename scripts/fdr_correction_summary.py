"""
Benjamini-Hochberg FDR correction applied within each family of related
correlation-type hypothesis tests reported across the report/manuscript.
Correcting within (rather than across) families is the standard, appropriate
approach here since each family addresses a distinct question with its own
natural multiple-comparisons structure.

Families:
  A. ARGscore vs 5 marker-composition modules, 3 cohorts (Table 2 in the
     manuscript) -- recomputed here since it was not previously saved to CSV.
  B. NNLS-deconvolved cell fraction vs ARGscore, 3 cohorts x 7 cell types.
  C. Reproduced modules/ARGscore vs the original paper's own CIBERSORT output
     (3.13 / 4.12 section).
  D. ARGscore-immune module associations, naive and MSI/MMR-adjusted partial
     correlations (3.15 / 4.14 section; within-strata rows excluded as they
     are already flagged as exploratory/underpowered, not primary tests).
"""
import os
import pandas as pd
from scipy.stats import spearmanr
from statsmodels.stats.multitest import multipletests
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BASE = f"{_PROJECT_ROOT}"
DATA_DIR = os.path.join(BASE, "analysis_output", "data")


def bh(df, pcol):
    df = df.copy()
    reject, qval, _, _ = multipletests(df[pcol], alpha=0.05, method="fdr_bh")
    df["qvalue_fdr_bh"] = qval
    df["significant_raw_p05"] = df[pcol] < 0.05
    df["significant_fdr_q05"] = df["qvalue_fdr_bh"] < 0.05
    return df


all_rows = []

# ---------------- Family A: ARGscore vs 5 modules, 3 cohorts (Table 2) ----------------
cohorts_a = {
    "GSE39582": "bulk_closure_result.csv",
    "GSE17536": "gse17536_closure_result.csv",
    "TCGA-COAD/READ": "tcga_coadread_closure_result.csv",
}
modules_a = ["Macrophage_TAM", "Endothelial", "Pericyte", "CD8T", "Bcell_TLS"]
rows_a = []
for cohort, fname in cohorts_a.items():
    df = pd.read_csv(os.path.join(DATA_DIR, fname), index_col=0)
    for mod in modules_a:
        sub = df.dropna(subset=["ARGscore", mod])
        r, p = spearmanr(sub["ARGscore"], sub[mod])
        rows_a.append(dict(family="A_ARGscore_vs_modules", cohort=cohort, test=mod, n=len(sub), rho=r, pvalue=p))
fam_a = bh(pd.DataFrame(rows_a), "pvalue")

# ---------------- Family B: NNLS fraction vs ARGscore ----------------
fam_b_raw = pd.read_csv(os.path.join(DATA_DIR, "nnls_argscore_correlation_summary.csv"))
fam_b_raw = fam_b_raw.rename(columns={"celltype": "test", "spearman_p": "pvalue", "spearman_rho": "rho"})
fam_b_raw["family"] = "B_NNLS_vs_ARGscore"
fam_b = bh(fam_b_raw[["family", "cohort", "test", "n", "rho", "pvalue"]], "pvalue")

# ---------------- Family C: reproduced modules/ARGscore vs original CIBERSORT ----------------
fam_c_raw = pd.read_csv(os.path.join(DATA_DIR, "cibersort_crossvalidation_summary.csv"))
fam_c_raw["test"] = fam_c_raw["method"] + " | " + fam_c_raw["our_var"] + " vs " + fam_c_raw["their_var"]
fam_c_raw = fam_c_raw.rename(columns={"pvalue": "pvalue"})
fam_c_raw["family"] = "C_vs_original_CIBERSORT"
fam_c = bh(fam_c_raw[["family", "cohort", "test", "n", "rho", "pvalue"]], "pvalue")

# ---------------- Family D: MSI/MMR-adjusted associations (naive + partial only) ----------------
msi_raw = pd.read_csv(os.path.join(DATA_DIR, "msi_adjusted_association_summary.csv"))
rows_d = []
for _, r in msi_raw.iterrows():
    rows_d.append(dict(family="D_MSI_adjusted", cohort=r.cohort, test=f"{r.module} (naive)", n=r.n, rho=r.rho_naive, pvalue=r.p_naive))
    rows_d.append(dict(family="D_MSI_adjusted", cohort=r.cohort, test=f"{r.module} (MSI-adjusted)", n=r.n, rho=r.rho_partial_msi_adj, pvalue=r.p_partial_msi_adj))
fam_d = bh(pd.DataFrame(rows_d), "pvalue")

# ---------------- combine + summarize ----------------
combined = pd.concat([fam_a, fam_b, fam_c, fam_d], ignore_index=True)
combined.to_csv(os.path.join(DATA_DIR, "fdr_correction_all_families.csv"), index=False)

summary = combined.groupby("family").agg(
    n_tests=("pvalue", "size"),
    n_sig_raw_p05=("significant_raw_p05", "sum"),
    n_sig_fdr_q05=("significant_fdr_q05", "sum"),
).reset_index()
summary["n_lost_after_fdr"] = summary["n_sig_raw_p05"] - summary["n_sig_fdr_q05"]
summary.to_csv(os.path.join(DATA_DIR, "fdr_correction_family_summary.csv"), index=False)

pd.set_option("display.width", 160)
print(summary.to_string(index=False))
print(f"\nTotal tests across all 4 families: {len(combined)}")
print(f"Total significant at raw P<0.05: {combined.significant_raw_p05.sum()}")
print(f"Total significant at FDR q<0.05: {combined.significant_fdr_q05.sum()}")

lost = combined[combined.significant_raw_p05 & ~combined.significant_fdr_q05]
print(f"\n{len(lost)} tests lost significance after FDR correction:")
if len(lost):
    print(lost[["family", "cohort", "test", "n", "rho", "pvalue", "qvalue_fdr_bh"]].to_string(index=False))
