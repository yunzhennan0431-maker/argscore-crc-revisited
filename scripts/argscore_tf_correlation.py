"""
Correlate expression of the curated human transcription-factor compendium
(Lambert et al. 2018, n=1639 TFs) with ARGscore across TCGA-COAD/READ patients,
to identify candidate master upstream regulators of the ARGscore transcriptional
program (broader than just the 5 signature genes themselves).
"""
import os
import numpy as np
import pandas as pd
import xenaPython as xena
from scipy.stats import spearmanr
from statsmodels.stats.multitest import multipletests
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BASE = f"{_PROJECT_ROOT}"
DATA_DIR = os.path.join(BASE, "analysis_output", "data")
FIG_DIR = os.path.join(BASE, "analysis_output", "figures")
UPSTREAM_DIR = f"{_PROJECT_ROOT}/scratch/upstream"
HOST = "https://tcga.xenahubs.net"

SIG5 = {"VSIG4", "CXCL10", "CXCL13", "MEIS2", "ZNF532"}

with open(os.path.join(UPSTREAM_DIR, "TF_names_v_1.01.txt")) as f:
    tf_list = sorted(set(line.strip() for line in f if line.strip()))
print(f"loaded {len(tf_list)} curated TFs")


def fetch_cohort(cohort, genes):
    ds = f"TCGA.{cohort}.sampleMap/HiSeqV2"
    samples = xena.dataset_samples(HOST, ds, None)
    vals = xena.dataset_fetch(HOST, ds, samples, genes)
    df = pd.DataFrame(dict(zip(genes, vals)), index=samples)
    for c in df.columns:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


expr_coad = fetch_cohort("COAD", tf_list)
expr_read = fetch_cohort("READ", tf_list)
expr = pd.concat([expr_coad, expr_read])
expr = expr[~expr.index.duplicated()]
# drop TFs entirely absent from the platform
present = [c for c in expr.columns if expr[c].notna().sum() > 30]
print(f"{len(present)}/{len(tf_list)} TFs found with data on HiSeqV2 platform")
expr = expr[present]
expr.to_csv(os.path.join(DATA_DIR, "tcga_coadread_curated_tf_expression.csv"))

argscore = pd.read_csv(os.path.join(DATA_DIR, "tcga_coadread_closure_result.csv"), index_col=0)["ARGscore"]
joined = expr.join(argscore, how="inner").dropna(subset=["ARGscore"])
print(f"n={len(joined)} patients with ARGscore + TF expression")

rows = []
for tf in present:
    sub = joined[[tf, "ARGscore"]].dropna()
    if len(sub) < 30:
        continue
    r, p = spearmanr(sub[tf], sub["ARGscore"])
    rows.append(dict(TF=tf, n=len(sub), spearman_rho=r, p=p, is_signature_gene=(tf in SIG5)))

out = pd.DataFrame(rows).sort_values("p")
out = out.dropna(subset=["p", "spearman_rho"])
rej, padj, _, _ = multipletests(out["p"], method="fdr_bh")
out["p_fdr_bh"] = padj
out["significant_fdr01"] = padj < 0.01
out.to_csv(os.path.join(DATA_DIR, "argscore_tf_correlation_tcga.csv"), index=False)

pd.set_option("display.width", 160)
print(f"\ntotal TFs tested: {len(out)}, FDR<0.01 significant: {out.significant_fdr01.sum()}")
print("\n=== Top 20 positively correlated with ARGscore ===")
print(out[~out.is_signature_gene].sort_values("spearman_rho", ascending=False).head(20)
      [["TF", "n", "spearman_rho", "p", "p_fdr_bh"]].round(4).to_string(index=False))
print("\n=== Top 20 negatively correlated with ARGscore ===")
print(out[~out.is_signature_gene].sort_values("spearman_rho").head(20)
      [["TF", "n", "spearman_rho", "p", "p_fdr_bh"]].round(4).to_string(index=False))
