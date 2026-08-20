# -*- coding: utf-8 -*-
import json
import numpy as np
import pandas as pd
from lifelines import CoxPHFitter
from sksurv.metrics import cumulative_dynamic_auc
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

SIG5_WEIGHTS = {"ZNF532": 0.2754, "VSIG4": 0.1833, "MEIS2": 0.1599, "CXCL10": -0.1619, "CXCL13": -0.1215}

def load_gene_df(expr_path, gene2probes_path):
    expr = pd.read_csv(expr_path, index_col=0)
    with open(gene2probes_path) as f:
        gene2probes = json.load(f)
    gene_expr = {}
    for g, probes in gene2probes.items():
        probes = [p for p in probes if p in expr.index]
        if probes:
            gene_expr[g] = expr.loc[probes].mean(axis=0)
    return pd.DataFrame(gene_expr)

def run_cohort(name, expr_path, gene2probes_path, clinical_path, time_col, event_col,
                event_map, age_col, gender_col, stage_col, stage_map=None, time_unit="months"):
    print(f"\n{'='*20} {name} {'='*20}")
    gene_df = load_gene_df(expr_path, gene2probes_path)
    argscore = sum(gene_df[g] * w for g, w in SIG5_WEIGHTS.items())
    argscore.name = "ARGscore"

    clinical = pd.read_csv(clinical_path, index_col=0)
    df = pd.concat([argscore, clinical], axis=1)

    df["event"] = df[event_col].map(event_map) if event_map else pd.to_numeric(df[event_col], errors="coerce")
    df["time"] = pd.to_numeric(df[time_col], errors="coerce")
    df["age"] = pd.to_numeric(df[age_col], errors="coerce")
    df["gender_male"] = (df[gender_col].astype(str).str.lower().isin(["male", "m"])).astype(float)

    if stage_map:
        df["stage_num"] = df[stage_col].astype(str).map(stage_map)
    else:
        df["stage_num"] = pd.to_numeric(df[stage_col], errors="coerce")

    model_df = df[["ARGscore", "age", "gender_male", "stage_num", "time", "event"]].dropna()
    model_df = model_df[model_df["time"] > 0]
    print("n used in multivariate Cox:", len(model_df))

    cph = CoxPHFitter()
    cph.fit(model_df, duration_col="time", event_col="event")
    print("\n--- Multivariate Cox (ARGscore + age + gender + stage) ---")
    summ = cph.summary[["coef", "exp(coef)", "exp(coef) lower 95%", "exp(coef) upper 95%", "p"]]
    print(summ.round(4))

    # time-dependent AUC via sksurv
    y = np.array([(bool(e), t) for e, t in zip(model_df["event"], model_df["time"])],
                 dtype=[("event", "bool"), ("time", "float")])
    risk_score = model_df["ARGscore"].values
    if time_unit == "months":
        times = np.array([12, 36, 60])
        time_labels = ["1-year", "3-year", "5-year"]
    else:
        times = np.array([1, 3, 5])
        time_labels = ["1-year", "3-year", "5-year"]
    times = times[(times > model_df["time"].min()) & (times < model_df["time"].max())]

    auc, mean_auc = cumulative_dynamic_auc(y, y, risk_score, times)
    print(f"\n--- Time-dependent AUC (ARGscore alone) ---")
    for t, a in zip(times, auc):
        print(f"  t={t:.0f} {time_unit}: AUC={a:.3f}")
    print(f"  mean AUC={mean_auc:.3f}")

    return {"name": name, "cox_summary": summ, "times": times, "auc": auc,
            "mean_auc": mean_auc, "model_df": model_df}

results = {}

results["GSE39582"] = run_cohort(
    "GSE39582", "bulk/gse39582_target_probe_expr.csv", "bulk/gene2probes.json",
    "bulk/gse39582_clinical.csv",
    time_col="os.delay (months)", event_col="os.event", event_map=None,
    age_col="age.at.diagnosis (year)", gender_col="Sex", stage_col="tnm.stage",
    stage_map=None, time_unit="months",
)

results["GSE17536"] = run_cohort(
    "GSE17536", "bulk2/gse17536_target_probe_expr.csv", "bulk2/gene2probes.json",
    "bulk2/gse17536_clinical.csv",
    time_col="overall survival follow-up time", event_col="overall_event (death from any cause)",
    event_map={"death": 1, "no death": 0},
    age_col="age", gender_col="gender", stage_col="ajcc_stage",
    stage_map=None, time_unit="months",
)

# plot AUC curves
fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
for ax, (name, res) in zip(axes, results.items()):
    ax.plot(res["times"], res["auc"], marker="o", color="#c0392b")
    ax.axhline(0.5, color="gray", ls="--", lw=1)
    ax.set_ylim(0.4, 1.0)
    ax.set_xlabel("Time (months)")
    ax.set_ylabel("Time-dependent AUC")
    ax.set_title(f"{name} (ARGscore alone)\nmean AUC={res['mean_auc']:.3f}")
plt.tight_layout()
plt.savefig("cox_auc/time_dependent_auc.png" if False else "time_dependent_auc.png", dpi=150)
print("\nsaved time_dependent_auc.png")

for name, res in results.items():
    res["cox_summary"].to_csv(f"cox_summary_{name}.csv")
print("saved cox_summary_*.csv")
