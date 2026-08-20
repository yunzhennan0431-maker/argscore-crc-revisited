"""
Direct validation against the original paper's own published supplementary
data (Zhang et al. 2023 Front Pharmacol, Table_2.xlsx, Sheets S1/S7/S8/S9),
downloaded from the journal's public Supplementary Material (not obtained
from the authors, who reported the original working files could no longer
be located).

Two things this enables that cannot be done without this file:
1. Exact patient-inclusion overlap check between our reproduced cohorts and
   the original 1214-patient cohort (S1).
2. Correlating our reproduced cell-composition modules (marker z-score
   averaging AND formal NNLS deconvolution) against the ORIGINAL paper's own
   CIBERSORT output per patient (S7) -- a direct external validation of the
   "ARGscore encodes TME cell composition" claim that does not depend on
   reproducing ARGscore itself.
"""
import os
import pandas as pd
import numpy as np
from scipy.stats import spearmanr
from lifelines import CoxPHFitter
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BASE = f"{_PROJECT_ROOT}"
SUPP_DIR = os.path.join(BASE, "analysis_output", "original_paper_supplementary")
DATA_DIR = os.path.join(BASE, "analysis_output", "data")
FIG_DIR = os.path.join(BASE, "analysis_output", "figures")

s1 = pd.read_csv(os.path.join(SUPP_DIR, "S1_clinical_1214patients.csv"))
s7 = pd.read_csv(os.path.join(SUPP_DIR, "S7_cibersort.csv"))
s7["dataset"] = s7["Mixture"].str.split("_").str[0]
s7["raw_id"] = s7["Mixture"].str.split("_", n=1).str[1]
s7["Macrophages_M1M2"] = s7["Macrophages M1"] + s7["Macrophages M2"]
s7["Bcells_naive_memory"] = s7["B cells naive"] + s7["B cells memory"]

OUR_FILES = {
    "GSE39582": ("bulk_closure_result.csv", "nnls_fractions_GSE39582.csv", False),
    "GSE17536": ("gse17536_closure_result.csv", "nnls_fractions_GSE17536.csv", False),
    "TCGA": ("tcga_coadread_closure_result.csv", "nnls_fractions_TCGA_COADREAD.csv", True),
}
S1_DATASET_NAME = {"GSE39582": "GSE39582", "GSE17536": "GSE17539", "TCGA": "TCGA"}  # note: original table mislabels GSE17536 as "GSE17539"
S7_DATASET_NAME = {"GSE39582": "GSE39582", "GSE17536": "GSE17536", "TCGA": "TCGA"}

overlap_summary = []
corr_rows = []

for cohort, (closure_f, nnls_f, is_tcga) in OUR_FILES.items():
    ours = pd.read_csv(os.path.join(DATA_DIR, closure_f), index_col=0)
    nnls = pd.read_csv(os.path.join(DATA_DIR, nnls_f), index_col=0)
    if is_tcga:
        ours = ours.copy()
        ours.index = [i[:12] for i in ours.index]
        nnls = nnls.copy()
        nnls.index = [i[:12] for i in nnls.index]

    their_ids_s1 = set(s1[s1.Dataset == S1_DATASET_NAME[cohort]]["ID"])
    overlap_summary.append(dict(
        cohort=cohort, our_n=len(ours), their_n_s1=len(their_ids_s1),
        overlap=len(set(ours.index) & their_ids_s1),
    ))

    sub7 = s7[s7.dataset == S7_DATASET_NAME[cohort]].set_index("raw_id")
    common = ours.index.intersection(sub7.index)
    print(f"{cohort}: our n={len(ours)}, CIBERSORT n={len(sub7)}, common n={len(common)}")

    merged = ours.loc[common].join(sub7.loc[common, ["Macrophages_M1M2", "Macrophages M2", "T cells CD8", "Bcells_naive_memory"]])
    merged_nnls = nnls.loc[nnls.index.intersection(common)].join(
        sub7.loc[nnls.index.intersection(common), ["Macrophages_M1M2", "Macrophages M2", "T cells CD8", "Bcells_naive_memory"]]
    )

    pairs = [
        ("z-score module", "Macrophage_TAM", "Macrophages_M1M2", "CIBERSORT M1+M2 macrophages"),
        ("z-score module", "Macrophage_TAM", "Macrophages M2", "CIBERSORT M2 macrophages"),
        ("z-score module", "CD8T", "T cells CD8", "CIBERSORT CD8 T cells"),
        ("z-score module", "Bcell_TLS", "Bcells_naive_memory", "CIBERSORT naive+memory B cells"),
        ("z-score module", "ARGscore", "Macrophages_M1M2", "CIBERSORT M1+M2 macrophages"),
        ("z-score module", "ARGscore", "Macrophages M2", "CIBERSORT M2 macrophages"),
        ("z-score module", "ARGscore", "T cells CD8", "CIBERSORT CD8 T cells"),
        ("z-score module", "ARGscore", "Bcells_naive_memory", "CIBERSORT naive+memory B cells"),
    ]
    for method, ourcol, theircol, theirlabel in pairs:
        if ourcol not in merged.columns:
            continue
        sub = merged[[ourcol, theircol]].dropna()
        if len(sub) < 5:
            continue
        r, p = spearmanr(sub[ourcol], sub[theircol])
        corr_rows.append(dict(cohort=cohort, method=method, our_var=ourcol, their_var=theirlabel, n=len(sub), rho=r, pvalue=p))

    nnls_pairs = [
        ("NNLS fraction", "Macrophage_TAM", "Macrophages_M1M2", "CIBERSORT M1+M2 macrophages"),
        ("NNLS fraction", "CD8T", "T cells CD8", "CIBERSORT CD8 T cells"),
        ("NNLS fraction", "Bcell_TLS", "Bcells_naive_memory", "CIBERSORT naive+memory B cells"),
    ]
    for method, ourcol, theircol, theirlabel in nnls_pairs:
        if ourcol not in merged_nnls.columns:
            continue
        sub = merged_nnls[[ourcol, theircol]].dropna()
        if len(sub) < 5:
            continue
        r, p = spearmanr(sub[ourcol], sub[theircol])
        corr_rows.append(dict(cohort=cohort, method=method, our_var=ourcol, their_var=theirlabel, n=len(sub), rho=r, pvalue=p))

overlap_df = pd.DataFrame(overlap_summary)
overlap_df.to_csv(os.path.join(DATA_DIR, "patient_overlap_vs_original.csv"), index=False)
print("\n=== Patient overlap summary ===")
print(overlap_df.to_string(index=False))

corr_df = pd.DataFrame(corr_rows)
corr_df.to_csv(os.path.join(DATA_DIR, "cibersort_crossvalidation_summary.csv"), index=False)
pd.set_option("display.width", 160)
print("\n=== Cross-validation vs original CIBERSORT ===")
print(corr_df.round(4).to_string(index=False))


# ---------- sensitivity: restrict Cox to overlap patients only ----------
print("\n=== Cox sensitivity: full cohort vs overlap-only (matching original patient list) ===")
sens_rows = []
for cohort, (closure_f, _, is_tcga) in OUR_FILES.items():
    ours = pd.read_csv(os.path.join(DATA_DIR, closure_f), index_col=0)
    if is_tcga:
        ours = ours.copy()
        ours.index = [i[:12] for i in ours.index]
        d = ours.rename(columns={"OS": "event", "OS.time": "time"})
    elif cohort == "GSE39582":
        d = ours.rename(columns={"os.event": "event", "os.delay (months)": "time"})
    else:
        d = ours.rename(columns={
            "overall_event (death from any cause)": "event_raw",
            "overall survival follow-up time": "time",
        })
        d["event"] = (d["event_raw"] == "death").astype(int)
    d = d.dropna(subset=["event", "time", "ARGscore"])

    their_ids = set(s1[s1.Dataset == S1_DATASET_NAME[cohort]]["ID"])
    d_overlap = d.loc[d.index.intersection(their_ids)]

    for label, dd in [("full", d), ("overlap_only", d_overlap)]:
        cph = CoxPHFitter()
        cph.fit(dd[["time", "event", "ARGscore"]], duration_col="time", event_col="event")
        hr = np.exp(cph.params_["ARGscore"])
        p = cph.summary.loc["ARGscore", "p"]
        sens_rows.append(dict(cohort=cohort, patient_set=label, n=len(dd), hr=hr, p=p))
        print(f"{cohort} [{label}] n={len(dd)}: HR={hr:.3f}, P={p:.4g}")

sens_df = pd.DataFrame(sens_rows)
sens_df.to_csv(os.path.join(DATA_DIR, "cox_sensitivity_overlap_patients.csv"), index=False)

# ---------- figure: scatter panels for the core ARGscore vs CIBERSORT tests ----------
fig, axes = plt.subplots(1, 3, figsize=(15, 4.5))
targets = [("Macrophages M2", "CIBERSORT M2 Macrophage fraction"),
           ("T cells CD8", "CIBERSORT CD8 T cell fraction"),
           ("Bcells_naive_memory", "CIBERSORT naive+memory B cell fraction")]
colors = {"GSE39582": "#4C72B0", "GSE17536": "#55A868", "TCGA": "#C44E52"}

for ax, (theircol, ylabel) in zip(axes, targets):
    for cohort, (closure_f, _, is_tcga) in OUR_FILES.items():
        ours = pd.read_csv(os.path.join(DATA_DIR, closure_f), index_col=0)
        if is_tcga:
            ours = ours.copy()
            ours.index = [i[:12] for i in ours.index]
        sub7 = s7[s7.dataset == S7_DATASET_NAME[cohort]].set_index("raw_id")
        common = ours.index.intersection(sub7.index)
        x = ours.loc[common, "ARGscore"]
        y = sub7.loc[common, theircol]
        ax.scatter(x, y, s=8, alpha=0.4, color=colors[cohort], label=cohort)
    ax.set_xlabel("Our reproduced ARGscore")
    ax.set_ylabel(ylabel)
    ax.legend(fontsize=8)

fig.suptitle("Our reproduced ARGscore vs. the original paper's own published CIBERSORT fractions (S7)")
fig.tight_layout()
out = os.path.join(FIG_DIR, "argscore_vs_original_cibersort.png")
fig.savefig(out, dpi=200)
print("\nsaved", out)
