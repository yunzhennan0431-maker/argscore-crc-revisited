"""
Multivariate Cox model for ARGscore's own prognostic hazard ratio, additionally
adjusting for MSI/MMR status. This is distinct from the 3.15 correlation-based
MSI/MMR adjustment (which tests ARGscore-vs-immune-module associations); here
MSI/MMR is added as an explicit covariate alongside age/gender/stage in the
Cox model for ARGscore itself, in GSE39582 and TCGA-COAD/READ. GSE17536 is
excluded (no MSI/MMR annotation available in that series).
"""
import os
import pandas as pd
from lifelines import CoxPHFitter

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BASE = f"{_PROJECT_ROOT}"
DATA_DIR = os.path.join(BASE, "analysis_output", "data")

base_cols = ["ARGscore", "age", "gender_male", "stage_num", "time", "event"]
msi_cols = base_cols + ["msi_dummy"]
results = {}

# ---------------- GSE39582 ----------------
bulk = pd.read_csv(os.path.join(DATA_DIR, "bulk_closure_result.csv"), index_col=0)
clin = pd.read_csv(os.path.join(DATA_DIR, "gse39582_clinical_full.csv"), index_col=0)
g = bulk.join(clin[["Sex", "age.at.diagnosis (year)"]], how="left")

g["time"] = pd.to_numeric(g["os.delay (months)"], errors="coerce")
g["event"] = pd.to_numeric(g["os.event"], errors="coerce")
g["age"] = pd.to_numeric(g["age.at.diagnosis (year)"], errors="coerce")
g["gender_male"] = (g["Sex"].astype(str).str.lower() == "male").astype(float)
g["stage_num"] = pd.to_numeric(g["tnm.stage"], errors="coerce")
g["msi_dummy"] = (g["mmr.status"] == "dMMR").astype(float)

df_base = g[base_cols].dropna()
df_base = df_base[df_base["time"] > 0]
df_msi = g[msi_cols].dropna()
df_msi = df_msi[df_msi["time"] > 0]

cph1 = CoxPHFitter().fit(df_base, duration_col="time", event_col="event")
cph2 = CoxPHFitter().fit(df_msi, duration_col="time", event_col="event")

print(f"GSE39582: n(base)={len(df_base)}, n(+MSI)={len(df_msi)}")
print(cph1.summary.loc["ARGscore", ["exp(coef)", "exp(coef) lower 95%", "exp(coef) upper 95%", "p"]])
print(cph2.summary[["exp(coef)", "exp(coef) lower 95%", "exp(coef) upper 95%", "p"]].round(4))

results["GSE39582_base"] = dict(
    n=len(df_base), hr=cph1.summary.loc["ARGscore", "exp(coef)"],
    hr_lower=cph1.summary.loc["ARGscore", "exp(coef) lower 95%"],
    hr_upper=cph1.summary.loc["ARGscore", "exp(coef) upper 95%"],
    p=cph1.summary.loc["ARGscore", "p"], msi_hr=None, msi_p=None,
)
results["GSE39582_plus_MSI"] = dict(
    n=len(df_msi), hr=cph2.summary.loc["ARGscore", "exp(coef)"],
    hr_lower=cph2.summary.loc["ARGscore", "exp(coef) lower 95%"],
    hr_upper=cph2.summary.loc["ARGscore", "exp(coef) upper 95%"],
    p=cph2.summary.loc["ARGscore", "p"],
    msi_hr=cph2.summary.loc["msi_dummy", "exp(coef)"], msi_p=cph2.summary.loc["msi_dummy", "p"],
)

# ---------------- TCGA-COAD/READ ----------------
tcga = pd.read_csv(os.path.join(DATA_DIR, "tcga_coadread_closure_result.csv"), index_col=0)
msi_c = pd.read_csv(os.path.join(DATA_DIR, "tcga_msi_raw", "COAD_msi.csv"), index_col=0)
msi_r = pd.read_csv(os.path.join(DATA_DIR, "tcga_msi_raw", "READ_msi.csv"), index_col=0)
msi_all = pd.concat([msi_c, msi_r])
t = tcga.join(msi_all[["microsatellite_instability"]], how="left")

t["time"] = pd.to_numeric(t["OS.time"], errors="coerce")
t["event"] = pd.to_numeric(t["OS"], errors="coerce")
t["age"] = pd.to_numeric(t["age_at_initial_pathologic_diagnosis"], errors="coerce")
t["gender_male"] = (t["gender"].astype(str).str.upper() == "MALE").astype(float)
t["stage_num"] = t["pathologic_stage"].astype(str).str.extract(r"Stage\s+(I{1,3}V?)")[0].map(
    {"I": 1, "II": 2, "III": 3, "IV": 4}
)
t_msi = t[t["microsatellite_instability"].isin([0.0, 2.0])].copy()
t_msi["msi_dummy"] = (t_msi["microsatellite_instability"] == 2.0).astype(float)

df_base_t = t[base_cols].dropna()
df_base_t = df_base_t[df_base_t["time"] > 0]
df_msi_t = t_msi[msi_cols].dropna()
df_msi_t = df_msi_t[df_msi_t["time"] > 0]

cph3 = CoxPHFitter().fit(df_base_t, duration_col="time", event_col="event")
# MSI-H stratum has 0 events among its 10 patients -> quasi-complete separation;
# use a ridge-penalized fit to obtain a stable estimate for this small subset.
cph4 = CoxPHFitter(penalizer=0.1).fit(df_msi_t, duration_col="time", event_col="event")

print(f"\nTCGA-COAD/READ: n(base)={len(df_base_t)}, n(+MSI, penalized)={len(df_msi_t)}")
print(cph3.summary.loc["ARGscore", ["exp(coef)", "exp(coef) lower 95%", "exp(coef) upper 95%", "p"]])
print(cph4.summary[["exp(coef)", "exp(coef) lower 95%", "exp(coef) upper 95%", "p"]].round(4))

results["TCGA_base"] = dict(
    n=len(df_base_t), hr=cph3.summary.loc["ARGscore", "exp(coef)"],
    hr_lower=cph3.summary.loc["ARGscore", "exp(coef) lower 95%"],
    hr_upper=cph3.summary.loc["ARGscore", "exp(coef) upper 95%"],
    p=cph3.summary.loc["ARGscore", "p"], msi_hr=None, msi_p=None,
)
results["TCGA_plus_MSI_penalized"] = dict(
    n=len(df_msi_t), hr=cph4.summary.loc["ARGscore", "exp(coef)"],
    hr_lower=cph4.summary.loc["ARGscore", "exp(coef) lower 95%"],
    hr_upper=cph4.summary.loc["ARGscore", "exp(coef) upper 95%"],
    p=cph4.summary.loc["ARGscore", "p"],
    msi_hr=cph4.summary.loc["msi_dummy", "exp(coef)"], msi_p=cph4.summary.loc["msi_dummy", "p"],
)

out = pd.DataFrame(results).T
out_path = os.path.join(DATA_DIR, "msi_adjusted_cox_argscore.csv")
out.to_csv(out_path)
print("\nSaved:", out_path)
print(out.round(4))
