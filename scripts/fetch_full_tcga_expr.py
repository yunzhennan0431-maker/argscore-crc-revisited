import time
import xenaPython as xena
import pandas as pd
import os
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

HOST = "https://tcga.xenahubs.net"
OUT = f"{_PROJECT_ROOT}/scratch/upstream"

ds = "TCGA.COAD.sampleMap/HiSeqV2"
fields = xena.dataset_field(HOST, ds)
genes = sorted(set(f.split("|")[0] for f in fields if not f.startswith("?")))
print(f"{len(genes)} genes to fetch")


def fetch_cohort(cohort, genes, chunk=4000):
    ds = f"TCGA.{cohort}.sampleMap/HiSeqV2"
    samples = xena.dataset_samples(HOST, ds, None)
    all_vals = {}
    for i in range(0, len(genes), chunk):
        sub = genes[i:i + chunk]
        t0 = time.time()
        vals = xena.dataset_fetch(HOST, ds, samples, sub)
        for g, v in zip(sub, vals):
            all_vals[g] = v
        print(f"  {cohort} chunk {i}-{i+len(sub)} fetched in {time.time()-t0:.1f}s")
    df = pd.DataFrame(all_vals, index=samples)
    for c in df.columns:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


t0 = time.time()
coad = fetch_cohort("COAD", genes)
read = fetch_cohort("READ", genes)
print("total fetch time:", time.time() - t0)

expr = pd.concat([coad, read])
expr = expr[~expr.index.duplicated()]
expr.to_pickle(f"{OUT}/tcga_coadread_full_expr.pkl")
print("saved, shape:", expr.shape)
