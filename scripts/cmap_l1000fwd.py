"""
Downstream therapeutic-hypothesis analysis: compute a genome-wide ARGscore-associated
expression signature in TCGA-COAD/READ (excluding the 5 ARGscore genes themselves to
avoid circularity), then query the public L1000FWD connectivity map (Wang et al. 2018
Bioinformatics) for small molecules whose induced transcriptomic signature is most
OPPOSITE (candidate reversal compounds) or most SIMILAR (candidate mimetics/risk
factors) to the high-ARGscore state.
"""
import os
import time
import requests
import numpy as np
import pandas as pd
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BASE = f"{_PROJECT_ROOT}"
DATA_DIR = os.path.join(BASE, "analysis_output", "data")
UPSTREAM_DIR = f"{_PROJECT_ROOT}/scratch/upstream"
L1000FWD_URL = "https://maayanlab.cloud/l1000fwd/"

SIG5 = {"VSIG4", "CXCL10", "CXCL13", "MEIS2", "ZNF532"}

expr = pd.read_pickle(os.path.join(UPSTREAM_DIR, "tcga_coadread_full_expr.pkl"))
closure = pd.read_csv(os.path.join(DATA_DIR, "tcga_coadread_closure_result.csv"), index_col=0)
argscore = closure["ARGscore"]

joined = expr.join(argscore, how="inner").dropna(subset=["ARGscore"])
gene_cols = [c for c in joined.columns if c != "ARGscore" and c not in SIG5]
print(f"correlating {len(gene_cols)} genes (excluding the 5 ARGscore genes) with ARGscore, n={len(joined)}")

corr = joined[gene_cols].corrwith(joined["ARGscore"], method="spearman")
corr = corr.dropna().sort_values(ascending=False)
corr.to_csv(os.path.join(DATA_DIR, "argscore_genomewide_spearman_tcga.csv"), header=["spearman_rho"])

N = 150
up_genes = corr.head(N).index.tolist()
down_genes = corr.tail(N).index.tolist()
print(f"top up gene: {up_genes[0]} rho={corr.iloc[0]:.3f}; top down gene: {down_genes[-1]} rho={corr.iloc[-1]:.3f}")

payload = {"up_genes": up_genes, "down_genes": down_genes}
resp = requests.post(L1000FWD_URL + "sig_search", json=payload)
result_id = resp.json()["result_id"]
print("L1000FWD result_id:", result_id)
time.sleep(2)

resp2 = requests.get(L1000FWD_URL + "result/topn/" + result_id)
topn = resp2.json()
print("keys:", list(topn.keys()))

records = []
for direction in ["opposite", "similar"]:
    for item in topn.get(direction, []):
        records.append(dict(direction=direction, sig_id=item["sig_id"], score=item["scores"]))
topn_df = pd.DataFrame(records)
topn_df.to_csv(os.path.join(DATA_DIR, "cmap_l1000fwd_topn_raw.csv"), index=False)
print(f"opposite: {len(topn_df[topn_df.direction=='opposite'])}, similar: {len(topn_df[topn_df.direction=='similar'])}")

# fetch drug metadata for top candidates in each direction (dedup by pert_id, most extreme score kept)
def fetch_sig_meta(sig_id):
    for attempt in range(3):
        try:
            r = requests.get(L1000FWD_URL + "sig/" + sig_id, timeout=15)
            d = r.json()
            return dict(pert_id=d.get("pert_id"), pert_desc=d.get("pert_desc"),
                        cell_id=d.get("cell_id"), pert_time=d.get("pert_time"),
                        pert_dose=d.get("pert_dose"))
        except Exception as e:
            time.sleep(1)
    return dict(pert_id=None, pert_desc=None, cell_id=None, pert_time=None, pert_dose=None)


meta_rows = []
for direction in ["opposite", "similar"]:
    sub = topn_df[topn_df.direction == direction].sort_values("score", key=lambda s: s.abs(), ascending=False).head(25)
    for _, row in sub.iterrows():
        meta = fetch_sig_meta(row["sig_id"])
        meta_rows.append(dict(direction=direction, sig_id=row["sig_id"], score=row["score"], **meta))
        time.sleep(0.15)

meta_df = pd.DataFrame(meta_rows)
meta_df.to_csv(os.path.join(DATA_DIR, "cmap_l1000fwd_top_compounds_meta.csv"), index=False)

pd.set_option("display.width", 160)
for direction in ["opposite", "similar"]:
    sub = meta_df[meta_df.direction == direction].dropna(subset=["pert_desc"])
    dedup = sub.sort_values("score", key=lambda s: s.abs(), ascending=False).drop_duplicates("pert_id")
    print(f"\n=== Top unique compounds ({direction}, n={len(dedup)}) ===")
    print(dedup[["pert_desc", "pert_id", "cell_id", "pert_time", "pert_dose", "score"]].head(15).to_string(index=False))
