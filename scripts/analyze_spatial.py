# -*- coding: utf-8 -*-
import numpy as np
import pandas as pd
import scipy.io as sio
from scipy import stats
import pickle

SAMPLES = ["GSM8265211_CTC21P", "GSM8265212_CTC21M", "GSM8265213_CTC17P", "GSM8265214_CTC17M"]
PERICYTE = ["RGS5", "ACTA2", "NOTCH3", "PDGFRB"]
ENDO = ["PECAM1", "VWF", "CDH5"]
TARGET = ["ZNF532", "MEIS2", "VSIG4"] + PERICYTE + ENDO

all_results = []
sample_spot_data = {}

for s in SAMPLES:
    print(f"\n=== {s} ===")
    features = pd.read_csv(f"{s}_features.tsv.gz", sep="\t", header=None, names=["ensembl", "symbol", "type"])
    barcodes = pd.read_csv(f"{s}_barcodes.tsv.gz", sep="\t", header=None, names=["barcode"])
    positions = pd.read_csv(f"{s}_tissue_positions.csv.gz")
    positions = positions.set_index("barcode")

    mat = sio.mmread(f"{s}_matrix.mtx.gz").tocsr()
    print("matrix shape (genes x spots):", mat.shape)

    total_counts = np.asarray(mat.sum(axis=0)).flatten()
    total_counts[total_counts == 0] = 1

    sym2idx = {}
    for i, sym in enumerate(features["symbol"]):
        sym2idx.setdefault(sym, []).append(i)

    gene_expr = {}
    for g in TARGET:
        if g in sym2idx:
            idxs = sym2idx[g]
            row = np.asarray(mat[idxs, :].sum(axis=0)).flatten()
            gene_expr[g] = row

    norm = {g: np.log1p(v / total_counts * 1e4) for g, v in gene_expr.items()}
    df = pd.DataFrame(norm, index=barcodes["barcode"].values)
    df = df.join(positions[["in_tissue", "array_row", "array_col", "pxl_row_in_fullres", "pxl_col_in_fullres"]])
    df = df[df["in_tissue"] == 1].copy()
    print("n spots in tissue:", df.shape[0])

    for g in TARGET:
        if g in df.columns:
            df[g + "_z"] = (df[g] - df[g].mean()) / (df[g].std() + 1e-9)
    df["Pericyte_score"] = df[[c + "_z" for c in PERICYTE if c in df.columns]].mean(axis=1)
    df["Endo_score"] = df[[c + "_z" for c in ENDO if c in df.columns]].mean(axis=1)

    for target_module, name in [("Pericyte_score", "Pericyte"), ("Endo_score", "Endothelial")]:
        rho, pval = stats.spearmanr(df["ZNF532"], df[target_module])
        print(f"  ZNF532 vs {name}: rho={rho:+.3f} p={pval:.2e} (n={df.shape[0]})")
        all_results.append({"sample": s, "module": name, "rho": rho, "p": pval, "n": df.shape[0]})

    sample_spot_data[s] = df

results_df = pd.DataFrame(all_results)
results_df.to_csv("spatial_znf532_pericyte_correlation.csv", index=False)
print("\n=== Summary ===")
print(results_df)

with open("sample_spot_data.pkl", "wb") as f:
    pickle.dump(sample_spot_data, f)
print("Saved sample_spot_data.pkl and spatial_znf532_pericyte_correlation.csv")
