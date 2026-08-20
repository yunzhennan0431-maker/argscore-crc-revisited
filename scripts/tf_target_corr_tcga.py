import os
import xenaPython as xena
import pandas as pd
from scipy.stats import spearmanr
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BASE = f"{_PROJECT_ROOT}"
DATA_DIR = os.path.join(BASE, "analysis_output", "data")
HOST = "https://tcga.xenahubs.net"

SIG5 = ["VSIG4", "CXCL10", "CXCL13", "MEIS2", "ZNF532"]

# candidate TF -> target gene pairs to test, from Enrichr enrichment
# (TF, target, source_library)
PAIRS = [
    ("NFKB1", "CXCL10", "TRRUST"), ("NFKB1", "CXCL13", "TRRUST"),
    ("IRF7", "CXCL10", "TRRUST"), ("IRF3", "CXCL10", "TRRUST"),
    ("IRF1", "CXCL10", "TRRUST"), ("STAT1", "CXCL10", "TRRUST"),
    ("RELA", "CXCL10", "TRRUST"), ("BCL3", "CXCL10", "TRRUST"),
    ("IKBKB", "CXCL10", "TRRUST"),
    ("TFAP2A", "VSIG4", "ChEA"), ("TFAP2A", "MEIS2", "ChEA"), ("TFAP2A", "ZNF532", "ChEA"),
    ("SMAD2", "CXCL13", "ChEA"), ("SMAD2", "MEIS2", "ChEA"), ("SMAD2", "ZNF532", "ChEA"),
    ("SMAD3", "CXCL13", "ChEA"), ("SMAD3", "MEIS2", "ChEA"), ("SMAD3", "ZNF532", "ChEA"),
    ("UBTF", "CXCL13", "ChEA"), ("UBTF", "MEIS2", "ChEA"), ("UBTF", "ZNF532", "ChEA"),
    ("E2F1", "CXCL10", "ChEA"), ("E2F1", "CXCL13", "ChEA"), ("E2F1", "MEIS2", "ChEA"), ("E2F1", "VSIG4", "ChEA"),
    ("MYC", "CXCL10", "TF_Pert"), ("MYC", "VSIG4", "TF_Pert"), ("MYC", "CXCL13", "TF_Pert"),
    ("FOSL1", "CXCL10", "TF_Pert"), ("FOSL1", "VSIG4", "TF_Pert"), ("FOSL1", "CXCL13", "TF_Pert"),
]

genes_needed = sorted(set([p[0] for p in PAIRS] + [p[1] for p in PAIRS]))


def fetch_cohort_expr(cohort, genes):
    expr_ds = f"TCGA.{cohort}.sampleMap/HiSeqV2"
    samples = xena.dataset_samples(HOST, expr_ds, None)
    vals = xena.dataset_fetch(HOST, expr_ds, samples, genes)
    df = pd.DataFrame(dict(zip(genes, vals)), index=samples)
    return df


coad = fetch_cohort_expr("COAD", genes_needed)
read = fetch_cohort_expr("READ", genes_needed)
combined = pd.concat([coad, read])
combined = combined.dropna(how="all")
combined.to_csv(os.path.join(DATA_DIR, "tf_target_expr_tcga_coadread.csv"))
print(f"n={len(combined)} TCGA-COAD/READ samples, {len(genes_needed)} genes fetched")

rows = []
for tf, target, src in PAIRS:
    sub = combined[[tf, target]].dropna()
    if len(sub) < 30:
        continue
    r, p = spearmanr(sub[tf], sub[target])
    rows.append(dict(TF=tf, target=target, source=src, n=len(sub), spearman_rho=r, p=p))

out = pd.DataFrame(rows).sort_values("p")
out.to_csv(os.path.join(DATA_DIR, "tf_target_correlation_tcga.csv"), index=False)
pd.set_option("display.width", 160)
print(out.round(4).to_string(index=False))

# multiple testing correction within this family
from statsmodels.stats.multitest import multipletests
rej, padj, _, _ = multipletests(out["p"], method="fdr_bh")
out["p_fdr_bh"] = padj
out["significant_fdr05"] = rej
out.to_csv(os.path.join(DATA_DIR, "tf_target_correlation_tcga.csv"), index=False)
print("\n=== FDR-significant TF-target pairs (BH q<0.05) ===")
print(out[out.significant_fdr05].sort_values("p").round(4).to_string(index=False))
