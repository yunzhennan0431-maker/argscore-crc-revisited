"""
Check whether the ARGscore <-> immune module (CD8T, Bcell_TLS, Macrophage_TAM)
associations survive adjustment for MSI/MMR status, to rule out that they
are simply re-capturing the already-published ARGscore-MSI relationship
rather than providing independent information.

GSE39582: mmr.status field (pMMR / dMMR), from original clinical annotation.
TCGA-COAD/READ: MSI_updated_Oct62011 field from the TCGA clinicalMatrix
(UCSC Xena classic hub), coded 1=MSS, 2=MSI-H, 3=MSI-L; binarized as
MSI-H vs non-MSI-H (MSS+MSI-L) to align with the pMMR/dMMR binary framing.
GSE17536 has no MSI/MMR annotation available and is not included here.

Method: partial Spearman correlation via rank-based OLS residualization
(regress ARGscore and each module separately on the MSI/MMR dummy, then
Spearman-correlate the residuals), plus stratified (within-group) Spearman
correlation as a complementary, assumption-light check.
"""
import os
import numpy as np
import pandas as pd
from scipy.stats import spearmanr, rankdata
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BASE = f"{_PROJECT_ROOT}"
DATA_DIR = os.path.join(BASE, "analysis_output", "data")
MSI_DIR = f"{_PROJECT_ROOT}/scratch/msi"

MODULES = ["Macrophage_TAM", "CD8T", "Bcell_TLS"]


def partial_spearman(x, y, covariate_dummy):
    """Partial Spearman correlation of x,y controlling for a binary covariate,
    via rank-transform + linear residualization."""
    rx = rankdata(x)
    ry = rankdata(y)
    c = covariate_dummy.astype(float)
    c = np.column_stack([np.ones(len(c)), c])
    beta_x = np.linalg.lstsq(c, rx, rcond=None)[0]
    beta_y = np.linalg.lstsq(c, ry, rcond=None)[0]
    resid_x = rx - c @ beta_x
    resid_y = ry - c @ beta_y
    r, p = spearmanr(resid_x, resid_y)
    return r, p


rows = []

# ---------------- GSE39582 ----------------
g39582 = pd.read_csv(os.path.join(DATA_DIR, "bulk_closure_result.csv"), index_col=0)
g39582 = g39582.dropna(subset=["mmr.status", "ARGscore"])
g39582["msi_dummy"] = (g39582["mmr.status"] == "dMMR").astype(int)
print(f"GSE39582: n={len(g39582)}, dMMR={g39582.msi_dummy.sum()}, pMMR={(1-g39582.msi_dummy).sum()}")

for mod in MODULES:
    sub = g39582.dropna(subset=[mod])
    r_naive, p_naive = spearmanr(sub["ARGscore"], sub[mod])
    r_partial, p_partial = partial_spearman(sub["ARGscore"].values, sub[mod].values, sub["msi_dummy"].values)
    r_pmmr, p_pmmr = spearmanr(sub.loc[sub.msi_dummy == 0, "ARGscore"], sub.loc[sub.msi_dummy == 0, mod])
    r_dmmr, p_dmmr = spearmanr(sub.loc[sub.msi_dummy == 1, "ARGscore"], sub.loc[sub.msi_dummy == 1, mod])
    rows.append(dict(cohort="GSE39582", module=mod, n=len(sub),
                      rho_naive=r_naive, p_naive=p_naive,
                      rho_partial_msi_adj=r_partial, p_partial_msi_adj=p_partial,
                      rho_within_pMMR=r_pmmr, p_within_pMMR=p_pmmr,
                      rho_within_dMMR=r_dmmr, p_within_dMMR=p_dmmr))

# ---------------- TCGA-COAD/READ ----------------
# NOTE: MSI_updated_Oct62011 has poor overlap with our RNA-seq patient subset
# (only 7/380 non-missing); microsatellite_instability (code: 0=NO/MSS,
# 2=YES/MSI-H, 1=ambiguous/excluded) has much better coverage (108/380).
tcga = pd.read_csv(os.path.join(DATA_DIR, "tcga_coadread_closure_result.csv"), index_col=0)
msi_coad = pd.read_csv(os.path.join(MSI_DIR, "COAD_msi.csv"), index_col=0)
msi_read = pd.read_csv(os.path.join(MSI_DIR, "READ_msi.csv"), index_col=0)
msi_all = pd.concat([msi_coad, msi_read])
tcga = tcga.join(msi_all[["microsatellite_instability"]], how="inner")
tcga = tcga[tcga["microsatellite_instability"].isin([0.0, 2.0])]
tcga = tcga.dropna(subset=["microsatellite_instability", "ARGscore"])
tcga["msi_dummy"] = (tcga["microsatellite_instability"] == 2.0).astype(int)  # 2 = YES/MSI-H
print(f"TCGA: n={len(tcga)}, MSI-H={tcga.msi_dummy.sum()}, MSS={(1-tcga.msi_dummy).sum()}")

for mod in MODULES:
    sub = tcga.dropna(subset=[mod])
    r_naive, p_naive = spearmanr(sub["ARGscore"], sub[mod])
    r_partial, p_partial = partial_spearman(sub["ARGscore"].values, sub[mod].values, sub["msi_dummy"].values)
    r_mss, p_mss = spearmanr(sub.loc[sub.msi_dummy == 0, "ARGscore"], sub.loc[sub.msi_dummy == 0, mod])
    r_msih, p_msih = spearmanr(sub.loc[sub.msi_dummy == 1, "ARGscore"], sub.loc[sub.msi_dummy == 1, mod])
    rows.append(dict(cohort="TCGA-COAD/READ", module=mod, n=len(sub),
                      rho_naive=r_naive, p_naive=p_naive,
                      rho_partial_msi_adj=r_partial, p_partial_msi_adj=p_partial,
                      rho_within_pMMR=r_mss, p_within_pMMR=p_mss,
                      rho_within_dMMR=r_msih, p_within_dMMR=p_msih))

out = pd.DataFrame(rows)
out.to_csv(os.path.join(DATA_DIR, "msi_adjusted_association_summary.csv"), index=False)
pd.set_option("display.width", 200)
print("\n(rho_within_pMMR/dMMR columns = within MSS/non-MSI-H and within dMMR/MSI-H strata for TCGA)")
print(out.round(4).to_string(index=False))
