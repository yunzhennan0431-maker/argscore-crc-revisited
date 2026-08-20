"""
TCGA-COAD/READ HumanMethylation450 promoter/gene-body methylation of the 5
ARGscore genes: correlate per-CpG-probe beta value with matched mRNA
expression (cis-regulation check) and with ARGscore.
Data: UCSC Xena classic hub via xenaPython (HumanMethylation450, HiSeqV2).
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
HOST = "https://tcga.xenahubs.net"

GENES = ["VSIG4", "CXCL10", "CXCL13", "MEIS2", "ZNF532"]


def fetch_methylation(cohort, gene):
    ds = f"TCGA.{cohort}.sampleMap/HumanMethylation450"
    samples = xena.dataset_samples(HOST, ds, None)
    meta, scores = xena.dataset_gene_probes_values(HOST, ds, samples, gene)
    probes = meta["name"]
    df = pd.DataFrame(scores, index=probes, columns=samples).T  # samples x probes
    for c in df.columns:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["cohort"] = cohort
    return df


def fetch_expr(cohort, genes):
    ds = f"TCGA.{cohort}.sampleMap/HiSeqV2"
    samples = xena.dataset_samples(HOST, ds, None)
    vals = xena.dataset_fetch(HOST, ds, samples, genes)
    df = pd.DataFrame(dict(zip(genes, vals)), index=samples)
    for c in df.columns:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


argscore = pd.read_csv(os.path.join(DATA_DIR, "tcga_coadread_closure_result.csv"), index_col=0)["ARGscore"]

expr = pd.concat([fetch_expr("COAD", GENES), fetch_expr("READ", GENES)])
expr = expr[~expr.index.duplicated()]

all_rows = []
probe_level_rows = []
for gene in GENES:
    meth = pd.concat([fetch_methylation("COAD", gene), fetch_methylation("READ", gene)])
    meth = meth[~meth.index.duplicated()]
    probe_cols = [c for c in meth.columns if c != "cohort"]
    print(f"{gene}: {len(probe_cols)} probes, {len(meth)} samples")

    joined = meth.join(expr[[gene]], how="inner").join(argscore, how="inner")
    joined.to_csv(os.path.join(DATA_DIR, f"methylation_{gene}_full.csv"))

    for probe in probe_cols:
        sub = joined[[probe, gene, "ARGscore"]].dropna()
        if len(sub) < 30:
            continue
        r_expr, p_expr = spearmanr(sub[probe], sub[gene])
        r_arg, p_arg = spearmanr(sub[probe], sub["ARGscore"])
        probe_level_rows.append(dict(
            gene=gene, probe=probe, n=len(sub),
            rho_meth_vs_expr=r_expr, p_meth_vs_expr=p_expr,
            rho_meth_vs_ARGscore=r_arg, p_meth_vs_ARGscore=p_arg,
        ))

    # gene-level average-probe methylation (Xena's own gene-probe-avg)
    avg_beta = meth[probe_cols].mean(axis=1)
    sub2 = pd.DataFrame({"avg_beta": avg_beta}).join(expr[[gene]], how="inner").join(argscore, how="inner").dropna()
    r_expr, p_expr = spearmanr(sub2["avg_beta"], sub2[gene])
    r_arg, p_arg = spearmanr(sub2["avg_beta"], sub2["ARGscore"])
    all_rows.append(dict(gene=gene, n=len(sub2), n_probes=len(probe_cols),
                          rho_avgmeth_vs_expr=r_expr, p_avgmeth_vs_expr=p_expr,
                          rho_avgmeth_vs_ARGscore=r_arg, p_avgmeth_vs_ARGscore=p_arg))

gene_summary = pd.DataFrame(all_rows)
rej, padj, _, _ = multipletests(gene_summary["p_avgmeth_vs_expr"], method="fdr_bh")
gene_summary["p_avgmeth_vs_expr_fdr"] = padj
gene_summary.to_csv(os.path.join(DATA_DIR, "methylation_gene_avg_summary.csv"), index=False)

probe_df = pd.DataFrame(probe_level_rows)
rej2, padj2, _, _ = multipletests(probe_df["p_meth_vs_expr"], method="fdr_bh")
probe_df["p_meth_vs_expr_fdr"] = padj2
probe_df.to_csv(os.path.join(DATA_DIR, "methylation_probe_level_summary.csv"), index=False)

pd.set_option("display.width", 180)
print("\n=== Gene-level average-probe methylation vs expression / ARGscore ===")
print(gene_summary.round(4).to_string(index=False))

print("\n=== Most negatively-correlated probe per gene (candidate functional/promoter CpG) ===")
for gene in GENES:
    sub = probe_df[probe_df.gene == gene].sort_values("rho_meth_vs_expr")
    if len(sub) == 0:
        continue
    top = sub.iloc[0]
    print(f"  {gene}: {top['probe']}  rho(meth,expr)={top['rho_meth_vs_expr']:.3f} "
          f"p={top['p_meth_vs_expr']:.2e}  p_fdr={top['p_meth_vs_expr_fdr']:.3f}  n={int(top['n'])}")

print(f"\ntotal probes tested: {len(probe_df)}")
print("significant (FDR<0.05) meth-vs-expr probes:", (probe_df.p_meth_vs_expr_fdr < 0.05).sum())
