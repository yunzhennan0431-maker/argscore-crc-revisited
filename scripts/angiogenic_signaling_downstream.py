"""
Downstream readout: does ARGscore track ACTIVE angiogenic signaling (VEGF/ANGPT/NOTCH
ligand-receptor axis), or only the STRUCTURAL presence of endothelial/pericyte cells
(already established via PECAM1/VWF/CDH5 and RGS5/ACTA2/NOTCH3/PDGFRB marker modules)?
This directly probes whether the "angiogenesis" name is justified by downstream
angiogenic pathway activity, independent of the cell-composition story.
"""
import os
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from statsmodels.stats.multitest import multipletests
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BASE = f"{_PROJECT_ROOT}"
DATA_DIR = os.path.join(BASE, "analysis_output", "data")
FIG_DIR = os.path.join(BASE, "analysis_output", "figures")
UPSTREAM_DIR = f"{_PROJECT_ROOT}/scratch/upstream"

ANGIO_SIGNALING = [
    "VEGFA", "VEGFB", "VEGFC", "FLT1", "KDR", "FLT4", "NRP1", "NRP2",
    "ANGPT1", "ANGPT2", "TEK", "DLL4", "NOTCH1", "NOTCH4", "JAG1",
    "HIF1A", "EPAS1", "FGF2", "PDGFB", "ANGPTL4", "ESM1", "APLN", "APLNR",
]
STRUCTURAL = {
    "Endothelial_structural": ["PECAM1", "VWF", "CDH5"],
    "Pericyte_structural": ["RGS5", "ACTA2", "NOTCH3", "PDGFRB"],
}

expr = pd.read_pickle(os.path.join(UPSTREAM_DIR, "tcga_coadread_full_expr.pkl"))
closure = pd.read_csv(os.path.join(DATA_DIR, "tcga_coadread_closure_result.csv"), index_col=0)
argscore = closure["ARGscore"]

present = [g for g in ANGIO_SIGNALING if g in expr.columns and expr[g].notna().sum() > 30]
print(f"{len(present)}/{len(ANGIO_SIGNALING)} angiogenic signaling genes found on HiSeqV2")

joined = expr[present].join(argscore, how="inner").dropna(subset=["ARGscore"])
rows = []
for g in present:
    sub = joined[[g, "ARGscore"]].dropna()
    r, p = spearmanr(sub[g], sub["ARGscore"])
    rows.append(dict(gene=g, n=len(sub), spearman_rho=r, p=p))
sig_df = pd.DataFrame(rows).sort_values("p")
rej, padj, _, _ = multipletests(sig_df["p"], method="fdr_bh")
sig_df["p_fdr_bh"] = padj
sig_df.to_csv(os.path.join(DATA_DIR, "argscore_angiogenic_signaling_correlation.csv"), index=False)

# z-score module of active angiogenic signaling genes, for direct comparison
z = (expr[present] - expr[present].mean()) / (expr[present].std() + 1e-9)
angio_module = z.mean(axis=1)
mod_df = pd.DataFrame({"AngioSignaling_module": angio_module}).join(closure[["ARGscore", "Endothelial", "Pericyte"]], how="inner").dropna()
r_mod, p_mod = spearmanr(mod_df["AngioSignaling_module"], mod_df["ARGscore"])
r_endo, p_endo = spearmanr(mod_df["Endothelial"], mod_df["ARGscore"])
r_peri, p_peri = spearmanr(mod_df["Pericyte"], mod_df["ARGscore"])

comparison = pd.DataFrame([
    dict(module="AngioSignaling (VEGF/ANGPT/NOTCH ligand-receptor, n=%d genes)" % len(present),
         rho_vs_ARGscore=r_mod, p=p_mod, n=len(mod_df)),
    dict(module="Endothelial_structural (PECAM1/VWF/CDH5)", rho_vs_ARGscore=r_endo, p=p_endo, n=len(mod_df)),
    dict(module="Pericyte_structural (RGS5/ACTA2/NOTCH3/PDGFRB)", rho_vs_ARGscore=r_peri, p=p_peri, n=len(mod_df)),
])
comparison.to_csv(os.path.join(DATA_DIR, "argscore_angio_signaling_vs_structural_comparison.csv"), index=False)

pd.set_option("display.width", 160)
print("\n=== Per-gene angiogenic signaling correlation with ARGscore ===")
print(sig_df.round(4).to_string(index=False))
print("\n=== Module-level comparison: active signaling vs structural cell-abundance ===")
print(comparison.round(4).to_string(index=False))
print(f"\nsignificant (FDR<0.05) angiogenic signaling genes: {(sig_df.p_fdr_bh < 0.05).sum()}/{len(sig_df)}")
