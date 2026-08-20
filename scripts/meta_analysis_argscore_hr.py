"""
Fixed-effect and random-effects (DerSimonian-Laird) meta-analysis of the
ARGscore multivariate Cox HR across the three independent bulk cohorts
(GSE39582, GSE17536, TCGA-COAD/READ), pooling on the log(HR) scale using
the reported 95% CIs to derive per-study SE. Produces a standard forest plot.
"""
import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BASE = f"{_PROJECT_ROOT}"
DATA_DIR = os.path.join(BASE, "analysis_output", "data")
FIG_DIR = os.path.join(BASE, "analysis_output", "figures")

cohorts = {
    "GSE39582 (n=579)": "cox_summary_GSE39582.csv",
    "GSE17536 (n=177)": "cox_summary_GSE17536.csv",
    "TCGA-COAD/READ (n=376)": "cox_summary_TCGA_COADREAD.csv",
}

rows = []
for label, fname in cohorts.items():
    df = pd.read_csv(os.path.join(DATA_DIR, fname))
    r = df[df.covariate == "ARGscore"].iloc[0]
    hr = r["exp(coef)"]
    lo = r["exp(coef) lower 95%"]
    hi = r["exp(coef) upper 95%"]
    log_hr = np.log(hr)
    se = (np.log(hi) - np.log(lo)) / (2 * 1.96)
    rows.append(dict(cohort=label, hr=hr, lo=lo, hi=hi, log_hr=log_hr, se=se, p=r["p"]))

study_df = pd.DataFrame(rows)
print(study_df)

# ---- fixed-effect (inverse-variance) ----
w_fixed = 1 / study_df["se"] ** 2
pooled_log_hr_fixed = (w_fixed * study_df["log_hr"]).sum() / w_fixed.sum()
pooled_se_fixed = np.sqrt(1 / w_fixed.sum())

# ---- heterogeneity (Cochran's Q, I^2, tau^2 via DerSimonian-Laird) ----
Q = (w_fixed * (study_df["log_hr"] - pooled_log_hr_fixed) ** 2).sum()
k = len(study_df)
df_ = k - 1
I2 = max(0.0, (Q - df_) / Q * 100) if Q > 0 else 0.0
C = w_fixed.sum() - (w_fixed ** 2).sum() / w_fixed.sum()
tau2 = max(0.0, (Q - df_) / C) if C > 0 else 0.0

# ---- random-effects (DerSimonian-Laird) ----
w_random = 1 / (study_df["se"] ** 2 + tau2)
pooled_log_hr_random = (w_random * study_df["log_hr"]).sum() / w_random.sum()
pooled_se_random = np.sqrt(1 / w_random.sum())

def summarize(log_hr, se):
    hr = np.exp(log_hr)
    lo = np.exp(log_hr - 1.96 * se)
    hi = np.exp(log_hr + 1.96 * se)
    z = log_hr / se
    from scipy.stats import norm
    p = 2 * (1 - norm.cdf(abs(z)))
    return hr, lo, hi, p

hr_f, lo_f, hi_f, p_f = summarize(pooled_log_hr_fixed, pooled_se_fixed)
hr_r, lo_r, hi_r, p_r = summarize(pooled_log_hr_random, pooled_se_random)

print(f"\nCochran's Q = {Q:.3f} (df={df_}), I^2 = {I2:.1f}%, tau^2 = {tau2:.4f}")
print(f"Fixed-effect pooled HR  = {hr_f:.3f} (95% CI {lo_f:.3f}-{hi_f:.3f}), P = {p_f:.4g}")
print(f"Random-effects pooled HR = {hr_r:.3f} (95% CI {lo_r:.3f}-{hi_r:.3f}), P = {p_r:.4g}")

summary_out = pd.DataFrame([
    dict(model="fixed_effect", hr=hr_f, lo=lo_f, hi=hi_f, p=p_f),
    dict(model="random_effects", hr=hr_r, lo=lo_r, hi=hi_r, p=p_r),
])
summary_out.to_csv(os.path.join(DATA_DIR, "argscore_meta_analysis_pooled.csv"), index=False)
study_df.to_csv(os.path.join(DATA_DIR, "argscore_meta_analysis_studies.csv"), index=False)
with open(os.path.join(DATA_DIR, "argscore_meta_analysis_heterogeneity.txt"), "w") as f:
    f.write(f"Cochran's Q = {Q:.3f} (df={df_})\nI^2 = {I2:.1f}%\ntau^2 = {tau2:.4f}\n")

# ---- forest plot ----
fig, ax = plt.subplots(figsize=(8, 4.5))
y_positions = list(range(len(study_df), 0, -1))
for y, (_, row) in zip(y_positions, study_df.iterrows()):
    ax.plot([row.lo, row.hi], [y, y], color="black", linewidth=1.2)
    ax.scatter([row.hr], [y], s=80, color="#4C72B0", zorder=3, marker="s")
    ax.text(6.5, y, f"{row.hr:.2f} ({row.lo:.2f}-{row.hi:.2f})", va="center", fontsize=9)

# diamond for random-effects pooled estimate
diamond_y = 0
diamond_x = [lo_r, hr_r, hi_r, hr_r]
diamond_y_pts = [diamond_y, diamond_y + 0.25, diamond_y, diamond_y - 0.25]
ax.fill(diamond_x, diamond_y_pts, color="#C44E52", zorder=3)
ax.text(6.5, diamond_y, f"{hr_r:.2f} ({lo_r:.2f}-{hi_r:.2f})", va="center", fontsize=9, fontweight="bold")

ax.axvline(1, color="gray", linestyle="--", linewidth=0.8)
ax.set_yticks(y_positions + [diamond_y])
ax.set_yticklabels(list(study_df.cohort) + ["Random-effects pooled"])
ax.set_xlabel("Hazard Ratio (95% CI), multivariate Cox (ARGscore + age + gender + stage)")
ax.set_xlim(0.5, 8)
ax.set_title(f"Meta-analysis of ARGscore prognostic HR across 3 independent cohorts\n(I²={I2:.0f}%)")
fig.subplots_adjust(left=0.26, right=0.82, top=0.85, bottom=0.15)
out = os.path.join(FIG_DIR, "argscore_meta_analysis_forest_plot.png")
fig.savefig(out, dpi=200)
print("saved", out)
