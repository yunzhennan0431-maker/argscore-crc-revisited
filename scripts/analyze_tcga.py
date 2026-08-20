# -*- coding: utf-8 -*-
import re
import numpy as np
import pandas as pd
from scipy import stats
from lifelines import CoxPHFitter, KaplanMeierFitter
from lifelines.statistics import logrank_test
from sksurv.metrics import cumulative_dynamic_auc
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

print("Loading COAD + READ expression...")
coad = load_expr("COAD_HiSeqV2")
read = load_expr("READ_HiSeqV2")
print("COAD samples:", coad.shape[0], "READ samples:", read.shape[0])

expr = pd.concat([coad, read], axis=0)
# keep only primary tumor samples (barcode ends in -01)
expr = expr[expr.index.str.endswith("-01")]
print("Combined primary-tumor samples:", expr.shape[0])

SIG5_WEIGHTS = {"ZNF532": 0.2754, "VSIG4": 0.1833, "MEIS2": 0.1599, "CXCL10": -0.1619, "CXCL13": -0.1215}
argscore = sum(expr[g] * w for g, w in SIG5_WEIGHTS.items())
argscore.name = "ARGscore"

z = (expr - expr.mean()) / expr.std()
MARKERS = {
    "Macrophage_TAM": ["CD68", "CD163", "MRC1", "MSR1", "CSF1R"],
    "Endothelial": ["PECAM1", "VWF", "CDH5"],
    "Pericyte": ["RGS5", "ACTA2", "NOTCH3", "PDGFRB"],
    "CD8T": ["CD8A", "CD8B"],
    "Bcell_TLS": ["MS4A1", "CD79A", "CR2"],
}
module_scores = {m: z[genes].mean(axis=1) for m, genes in MARKERS.items()}
module_df = pd.DataFrame(module_scores)

result = pd.concat([argscore, module_df], axis=1)

# clinical + survival
coad_clin = pd.read_csv("COAD_clinicalMatrix", sep="\t", index_col=0)
read_clin = pd.read_csv("READ_clinicalMatrix", sep="\t", index_col=0)
clinical = pd.concat([coad_clin, read_clin], axis=0)

coad_surv = pd.read_csv("COAD_survival.txt", sep="\t", index_col=0)
read_surv = pd.read_csv("READ_survival.txt", sep="\t", index_col=0)
survival = pd.concat([coad_surv, read_surv], axis=0)

result = result.join(clinical[["age_at_initial_pathologic_diagnosis", "gender", "pathologic_stage"]], how="left")
result = result.join(survival[["OS", "OS.time"]], how="left")
result.to_csv("tcga_coadread_closure_result.csv")
print("Merged result shape:", result.shape)
print(result[["age_at_initial_pathologic_diagnosis", "gender", "pathologic_stage", "OS", "OS.time"]].isna().sum())

print("\n=== Spearman correlation: ARGscore vs module scores (TCGA-COAD/READ) ===")
for m in MARKERS:
    rho, pval = stats.spearmanr(result["ARGscore"], result[m], nan_policy="omit")
    print(f"{m:16s}  rho={rho:+.3f}  p={pval:.2e}")

# stage mapping
def map_stage(s):
    if pd.isna(s):
        return np.nan
    s = str(s).lower()
    m = re.search(r"stage\s+(iv|iii|ii|i)", s)
    if not m:
        return np.nan
    roman = m.group(1)
    return {"i": 1, "ii": 2, "iii": 3, "iv": 4}[roman]

result["stage_num"] = result["pathologic_stage"].apply(map_stage)
result["gender_male"] = (result["gender"].astype(str).str.upper() == "MALE").astype(float)
result["age"] = pd.to_numeric(result["age_at_initial_pathologic_diagnosis"], errors="coerce")
result["time"] = pd.to_numeric(result["OS.time"], errors="coerce") / 30.44  # days -> months
result["event"] = pd.to_numeric(result["OS"], errors="coerce")

model_df = result[["ARGscore", "age", "gender_male", "stage_num", "time", "event"]].dropna()
model_df = model_df[model_df["time"] > 0]
print("\nn used in multivariate Cox:", len(model_df))

cph = CoxPHFitter()
cph.fit(model_df, duration_col="time", event_col="event")
print("\n--- Multivariate Cox (ARGscore + age + gender + stage), TCGA-COAD/READ ---")
summ = cph.summary[["coef", "exp(coef)", "exp(coef) lower 95%", "exp(coef) upper 95%", "p"]]
print(summ.round(4))
summ.to_csv("cox_summary_TCGA_COADREAD.csv")

combined_risk = cph.predict_log_partial_hazard(model_df)
y = np.array([(bool(e), t) for e, t in zip(model_df["event"], model_df["time"])],
             dtype=[("event", "bool"), ("time", "float")])
times = np.array([12, 36, 60])
times = times[(times > model_df["time"].min()) & (times < model_df["time"].max())]
auc_arg, mean_arg = cumulative_dynamic_auc(y, y, model_df["ARGscore"].values, times)
auc_comb, mean_comb = cumulative_dynamic_auc(y, y, combined_risk.values, times)
print("\n--- Time-dependent AUC ---")
for t, a1, a2 in zip(times, auc_arg, auc_comb):
    print(f"  t={t:.0f}mo  ARGscore-only AUC={a1:.3f}  Combined AUC={a2:.3f}")
print(f"  mean: ARGscore-only={mean_arg:.3f}  Combined={mean_comb:.3f}")

# KM curve
med = model_df["ARGscore"].median()
high = model_df[model_df["ARGscore"] >= med]
low = model_df[model_df["ARGscore"] < med]
res_lr = logrank_test(high["time"], low["time"], event_observed_A=high["event"], event_observed_B=low["event"])
print(f"\nOS log-rank p={res_lr.p_value:.4e}  (high n={len(high)}, low n={len(low)})")

kmf_h = KaplanMeierFitter().fit(high["time"], high["event"], label="ARGscore-high")
kmf_l = KaplanMeierFitter().fit(low["time"], low["event"], label="ARGscore-low")
fig, ax = plt.subplots(figsize=(5.5, 4.5))
kmf_h.plot_survival_function(ax=ax, color="#c0392b")
kmf_l.plot_survival_function(ax=ax, color="#2980b9")
ax.set_title(f"TCGA-COAD/READ (n={len(model_df)}): OS by ARGscore\n(median split, log-rank p={res_lr.p_value:.4f})")
ax.set_xlabel("Time (months)"); ax.set_ylabel("Survival probability")
plt.tight_layout()
plt.savefig("tcga_km_argscore.png", dpi=150)

colors = ["#8e44ad", "#16a085", "#c0392b", "#2980b9", "#f39c12"]
fig, axes = plt.subplots(1, 5, figsize=(18, 3.6))
for ax, m, c in zip(axes, MARKERS.keys(), colors):
    rho, pval = stats.spearmanr(result["ARGscore"], result[m], nan_policy="omit")
    ax.scatter(result["ARGscore"], result[m], s=6, alpha=0.35, color=c)
    valid = result[["ARGscore", m]].dropna()
    zz = np.polyfit(valid["ARGscore"], valid[m], 1)
    xs = np.linspace(result["ARGscore"].min(), result["ARGscore"].max(), 50)
    ax.plot(xs, np.polyval(zz, xs), color="black", lw=1.5)
    ax.set_title(f"{m}\nρ={rho:+.2f}, p={pval:.1e}", fontsize=10)
    ax.set_xlabel("ARGscore")
    if ax is axes[0]:
        ax.set_ylabel("marker module z-score")
fig.suptitle(f"TCGA-COAD/READ (n={result.shape[0]}): ARGscore vs independent marker-gene module scores", y=1.08)
plt.tight_layout()
plt.savefig("tcga_correlation_panel.png", dpi=150, bbox_inches="tight")

fig, ax = plt.subplots(figsize=(6, 4.5))
ax.plot(times, auc_arg, marker="o", color="#2980b9", label=f"ARGscore only (mean={mean_arg:.3f})")
ax.plot(times, auc_comb, marker="s", color="#c0392b", label=f"+age/gender/stage (mean={mean_comb:.3f})")
ax.axhline(0.5, color="gray", ls="--", lw=1)
ax.set_ylim(0.4, 1.0); ax.set_xlabel("Time (months)"); ax.set_ylabel("Time-dependent AUC")
ax.set_title("TCGA-COAD/READ"); ax.legend(fontsize=9)
plt.tight_layout()
plt.savefig("tcga_time_dependent_auc.png", dpi=150)

print("\nAll figures and tables saved.")
