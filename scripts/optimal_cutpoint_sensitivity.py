"""
Sensitivity analysis: compare median-split ARGscore stratification (used
throughout the manuscript) against a maxstat/surv_cutpoint-style optimal
cutpoint (scan candidate cutoffs between the 10th-90th percentile of
ARGscore, minprop=0.1, pick the cutoff maximizing the log-rank statistic)
for GSE39582, GSE17536, and TCGA-COAD/READ.
"""
import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from lifelines import KaplanMeierFitter, CoxPHFitter
from lifelines.statistics import logrank_test
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BASE = f"{_PROJECT_ROOT}"
DATA_DIR = os.path.join(BASE, "analysis_output", "data")
FIG_DIR = os.path.join(BASE, "analysis_output", "figures")


def load_gse39582():
    df = pd.read_csv(os.path.join(DATA_DIR, "bulk_closure_result.csv"), index_col=0)
    df = df.rename(columns={"os.event": "event", "os.delay (months)": "time"})
    df = df.dropna(subset=["event", "time", "ARGscore"])
    return df[["ARGscore", "event", "time"]]


def load_gse17536():
    df = pd.read_csv(os.path.join(DATA_DIR, "gse17536_closure_result.csv"), index_col=0)
    df = df.rename(columns={
        "overall_event (death from any cause)": "event_raw",
        "overall survival follow-up time": "time",
    })
    df["event"] = (df["event_raw"] == "death").astype(int)
    df = df.dropna(subset=["event", "time", "ARGscore"])
    return df[["ARGscore", "event", "time"]]


def load_tcga():
    df = pd.read_csv(os.path.join(DATA_DIR, "tcga_coadread_closure_result.csv"), index_col=0)
    df = df.rename(columns={"OS": "event", "OS.time": "time"})
    df = df.dropna(subset=["event", "time", "ARGscore"])
    return df[["ARGscore", "event", "time"]]


def optimal_cutpoint(df, minprop=0.1, n_candidates=200):
    """maxstat-style scan: candidate cutoffs restricted to [minprop, 1-minprop]
    quantile range of ARGscore, pick cutoff maximizing the log-rank chi2."""
    lo = df["ARGscore"].quantile(minprop)
    hi = df["ARGscore"].quantile(1 - minprop)
    candidates = np.linspace(lo, hi, n_candidates)
    best_stat, best_cut, best_p = -np.inf, None, None
    for c in candidates:
        high = df["ARGscore"] > c
        if high.sum() < 2 or (~high).sum() < 2:
            continue
        res = logrank_test(
            df.loc[high, "time"], df.loc[~high, "time"],
            event_observed_A=df.loc[high, "event"], event_observed_B=df.loc[~high, "event"],
        )
        if res.test_statistic > best_stat:
            best_stat, best_cut, best_p = res.test_statistic, c, res.p_value
    return best_cut, best_stat, best_p


def cox_hr(df, cutoff):
    d = df.copy()
    d["group"] = (d["ARGscore"] > cutoff).astype(int)
    cph = CoxPHFitter()
    cph.fit(d[["time", "event", "group"]], duration_col="time", event_col="event")
    hr = np.exp(cph.params_["group"])
    ci_lo, ci_hi = np.exp(cph.confidence_intervals_.loc["group"])
    p = cph.summary.loc["group", "p"]
    return hr, ci_lo, ci_hi, p


def analyze_cohort(name, df):
    median_cut = df["ARGscore"].median()
    hr_med, lo_med, hi_med, p_med = cox_hr(df, median_cut)

    opt_cut, opt_stat, opt_logrank_p = optimal_cutpoint(df)
    hr_opt, lo_opt, hi_opt, p_opt = cox_hr(df, opt_cut)

    n_high_med = (df["ARGscore"] > median_cut).sum()
    n_high_opt = (df["ARGscore"] > opt_cut).sum()

    print(f"\n=== {name} (n={len(df)}) ===")
    print(f"Median split:  cutoff={median_cut:.3f}, n_high={n_high_med}, HR={hr_med:.2f} "
          f"(95% CI {lo_med:.2f}-{hi_med:.2f}), P={p_med:.4g}")
    print(f"Optimal split: cutoff={opt_cut:.3f}, n_high={n_high_opt}, HR={hr_opt:.2f} "
          f"(95% CI {lo_opt:.2f}-{hi_opt:.2f}), P={p_opt:.4g}, logrank P={opt_logrank_p:.4g}")

    return dict(
        cohort=name, n=len(df),
        median_cutoff=median_cut, median_n_high=n_high_med,
        median_hr=hr_med, median_hr_lo=lo_med, median_hr_hi=hi_med, median_p=p_med,
        optimal_cutoff=opt_cut, optimal_n_high=n_high_opt,
        optimal_hr=hr_opt, optimal_hr_lo=lo_opt, optimal_hr_hi=hi_opt, optimal_p=p_opt,
    ), df, median_cut, opt_cut


def plot_km_comparison(cohort_data):
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5))
    for ax, (name, df, med_cut, opt_cut) in zip(axes, cohort_data):
        kmf = KaplanMeierFitter()
        for cut, style, label_prefix in [(med_cut, "-", "Median"), (opt_cut, "--", "Optimal")]:
            high = df["ARGscore"] > cut
            for grp, grp_label, color in [(high, "High", "#C44E52"), (~high, "Low", "#4C72B0")]:
                kmf.fit(df.loc[grp, "time"], df.loc[grp, "event"], label=f"{label_prefix}-{grp_label}")
                kmf.plot_survival_function(ax=ax, ci_show=False, linestyle=style, color=color)
        ax.set_title(name)
        ax.set_xlabel("Time")
        ax.set_ylabel("Survival probability")
        ax.legend(fontsize=7)
    fig.suptitle("Median-split (solid) vs. optimal-cutpoint (dashed) ARGscore stratification")
    fig.tight_layout()
    out = os.path.join(FIG_DIR, "cutoff_sensitivity_km_comparison.png")
    fig.savefig(out, dpi=200)
    print("saved", out)


def main():
    cohorts = {
        "GSE39582": load_gse39582(),
        "GSE17536": load_gse17536(),
        "TCGA-COAD/READ": load_tcga(),
    }
    results = []
    cohort_data = []
    for name, df in cohorts.items():
        r, df_, med_cut, opt_cut = analyze_cohort(name, df)
        results.append(r)
        cohort_data.append((name, df_, med_cut, opt_cut))

    out_df = pd.DataFrame(results)
    out_df.to_csv(os.path.join(DATA_DIR, "cutoff_sensitivity_summary.csv"), index=False)
    print("\nsaved summary csv")

    plot_km_comparison(cohort_data)


if __name__ == "__main__":
    main()
