# -*- coding: utf-8 -*-
import numpy as np
import pandas as pd
from scipy import stats
from lifelines import CoxPHFitter, KaplanMeierFitter
from lifelines.statistics import logrank_test
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

TARGETS = ["VSIG4", "CXCL10", "CXCL13", "MEIS2", "ZNF532",
           "CD68", "CD163", "MRC1", "MSR1", "CSF1R",
           "PECAM1", "VWF", "CDH5",
           "RGS5", "ACTA2", "NOTCH3", "PDGFRB",
           "CD8A", "CD8B", "MS4A1", "CD79A", "CR2"]

def load_expr(fp):
    rows = {}
    with open(fp) as f:
        header = f.readline().rstrip("\n").split("\t")
        samples = header[1:]
        for line in f:
            parts = line.rstrip("\n").split("\t")
            gene = parts[0]
            if gene in TARGETS:
                rows[gene] = [float(x) if x not in ("", "NA") else np.nan for x in parts[1:]]
    df = pd.DataFrame(rows, index=samples)
    return df

SIG5_WEIGHTS = {"ZNF532": 0.2754, "VSIG4": 0.1833, "MEIS2": 0.1599, "CXCL10": -0.1619, "CXCL13": -0.1215}
MARKERS = {
    "Macrophage_TAM": ["CD68", "CD163", "MRC1", "MSR1", "CSF1R"],
    "Endothelial": ["PECAM1", "VWF", "CDH5"],
    "Pericyte": ["RGS5", "ACTA2", "NOTCH3", "PDGFRB"],
    "CD8T": ["CD8A", "CD8B"],
    "Bcell_TLS": ["MS4A1", "CD79A", "CR2"],
}

import re
def map_stage(s):
    if pd.isna(s):
        return np.nan
    s = str(s).lower()
    m = re.search(r"stage\s+(iv|iii|ii|i)", s)
    if not m:
        return np.nan
    roman = m.group(1)
    return {"i": 1, "ii": 2, "iii": 3, "iv": 4}[roman]

def process_cohort(name, expr_file, clin_file, surv_file):
    expr = load_expr(expr_file)
    expr = expr[expr.index.str.endswith("-01")]

    z = (expr - expr.mean()) / expr.std()
    argscore = sum(expr[g] * w for g, w in SIG5_WEIGHTS.items())
    argscore.name = "ARGscore"
    module_scores = {m: z[genes].mean(axis=1) for m, genes in MARKERS.items()}
    result = pd.DataFrame(module_scores)
    result["ARGscore"] = argscore

    clin = pd.read_csv(clin_file, sep="\t", index_col=0)
    surv = pd.read_csv(surv_file, sep="\t", index_col=0)
    result = result.join(clin[["age_at_initial_pathologic_diagnosis", "gender", "pathologic_stage"]], how="left")
    result = result.join(surv[["OS", "OS.time"]], how="left")

    print(f"\n{'='*15} {name} (n={result.shape[0]}) {'='*15}")
    print("=== Spearman: ARGscore vs modules ===")
    for m in MARKERS:
        rho, pval = stats.spearmanr(result["ARGscore"], result[m], nan_policy="omit")
        print(f"  {m:16s} rho={rho:+.3f} p={pval:.3f}")

    result["stage_num"] = result["pathologic_stage"].apply(map_stage)
    result["gender_male"] = (result["gender"].astype(str).str.upper() == "MALE").astype(float)
    result["age"] = pd.to_numeric(result["age_at_initial_pathologic_diagnosis"], errors="coerce")
    result["time"] = pd.to_numeric(result["OS.time"], errors="coerce") / 30.44
    result["event"] = pd.to_numeric(result["OS"], errors="coerce")

    model_df = result[["ARGscore", "age", "gender_male", "stage_num", "time", "event"]].dropna()
    model_df = model_df[model_df["time"] > 0]
    print(f"n in Cox model: {len(model_df)}")
    if len(model_df) > 30:
        try:
            cph = CoxPHFitter()
            cph.fit(model_df, duration_col="time", event_col="event")
            hr = cph.summary.loc["ARGscore", "exp(coef)"]
            lo = cph.summary.loc["ARGscore", "exp(coef) lower 95%"]
            hi = cph.summary.loc["ARGscore", "exp(coef) upper 95%"]
            p = cph.summary.loc["ARGscore", "p"]
            print(f"  Multivariate Cox ARGscore: HR={hr:.2f} (95% CI {lo:.2f}-{hi:.2f}) p={p:.3f}")
        except Exception as e:
            print("  Cox model failed:", e)

    med = result["ARGscore"].median()
    have_surv = result.dropna(subset=["time", "event"])
    high = have_surv[have_surv["ARGscore"] >= med]
    low = have_surv[have_surv["ARGscore"] < med]
    if len(high) > 5 and len(low) > 5:
        res_lr = logrank_test(high["time"], low["time"], event_observed_A=high["event"], event_observed_B=low["event"])
        print(f"  Log-rank (median split, n={len(have_surv)}): p={res_lr.p_value:.4f}")

    result.to_csv(f"{name}_split_result.csv")
    return result, model_df

coad_result, coad_model = process_cohort("COAD", "COAD_HiSeqV2", "COAD_clinicalMatrix", "COAD_survival.txt")
read_result, read_model = process_cohort("READ", "READ_HiSeqV2", "READ_clinicalMatrix", "READ_survival.txt")

# KM plot side by side
fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
for ax, (name, model_df) in zip(axes, [("COAD", coad_model), ("READ", read_model)]):
    med = model_df["ARGscore"].median()
    high = model_df[model_df["ARGscore"] >= med]
    low = model_df[model_df["ARGscore"] < med]
    res_lr = logrank_test(high["time"], low["time"], event_observed_A=high["event"], event_observed_B=low["event"])
    kmf_h = KaplanMeierFitter().fit(high["time"], high["event"], label="ARGscore-high")
    kmf_l = KaplanMeierFitter().fit(low["time"], low["event"], label="ARGscore-low")
    kmf_h.plot_survival_function(ax=ax, color="#c0392b")
    kmf_l.plot_survival_function(ax=ax, color="#2980b9")
    ax.set_title(f"TCGA-{name} (n={len(model_df)})\nlog-rank p={res_lr.p_value:.4f}")
    ax.set_xlabel("Time (months)"); ax.set_ylabel("Survival probability")
plt.tight_layout()
plt.savefig("coad_vs_read_km.png", dpi=150)
print("\nSaved coad_vs_read_km.png")
