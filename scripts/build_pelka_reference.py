"""
Build a cell-type reference signature matrix from the Pelka et al. 2021 Cell
CRC atlas (GSE178341), for NNLS-based deconvolution of bulk cohorts.
Uses clMidwayPr cell-type labels (Epi, Endo, Fibro, Peri, Macro, TCD8, B, ...).
"""
import h5py
import numpy as np
import scipy.sparse as sp
import pandas as pd
import csv

H5 = "GSE178341_full.h5"
CLUSTER_CSV = "GSE178341_cluster.csv"

SIG5 = ["VSIG4", "CXCL10", "CXCL13", "MEIS2", "ZNF532"]
MARKERS = {
    "Macrophage_TAM": ["CD68", "CD163", "MRC1", "MSR1", "CSF1R", "C1QA", "C1QB", "APOE"],
    "Endothelial": ["PECAM1", "VWF", "CDH5", "CLDN5", "ENG"],
    "Pericyte": ["RGS5", "ACTA2", "NOTCH3", "PDGFRB", "MYH11", "TAGLN"],
    "CD8T": ["CD8A", "CD8B", "CD3D", "CD3E", "GZMK"],
    "Bcell_TLS": ["MS4A1", "CD79A", "CD79B", "CR2", "CD19"],
    "Epithelial": ["EPCAM", "KRT8", "KRT18", "KRT19"],
    "Fibroblast": ["COL1A1", "COL1A2", "DCN", "LUM"],
}
TARGETS = list(dict.fromkeys(SIG5 + [g for v in MARKERS.values() for g in v]))

# celltype label (clMidwayPr) -> our module name
CT_MAP = {
    "Macro": "Macrophage_TAM",
    "TCD8": "CD8T",
    "B": "Bcell_TLS",
    "Endo": "Endothelial",
    "Peri": "Pericyte",
    "Epi": "Epithelial",
    "Fibro": "Fibroblast",
}

print("Loading barcode -> celltype map...")
bc2ct = {}
with open(CLUSTER_CSV) as f:
    r = csv.DictReader(f)
    for row in r:
        ct = row["clMidwayPr"]
        if ct in CT_MAP:
            bc2ct[row["sampleID"]] = CT_MAP[ct]
print("n barcodes with target celltype:", len(bc2ct))

print("Loading h5...")
f = h5py.File(H5, "r")
n_genes, n_cells = f["matrix/shape"][:]
print("genes:", n_genes, "cells:", n_cells)

names = np.array([x.decode() for x in f["matrix/features/name"][:]])
barcodes = np.array([x.decode() for x in f["matrix/barcodes"][:]])

name_to_idx = {}
for i, n in enumerate(names):
    name_to_idx.setdefault(n, []).append(i)

present = [g for g in TARGETS if g in name_to_idx]
missing = [g for g in TARGETS if g not in name_to_idx]
print("present:", len(present), "missing:", missing)

print("Loading sparse matrix...")
data = f["matrix/data"][:]
indices = f["matrix/indices"][:]
indptr = f["matrix/indptr"][:]
mat = sp.csc_matrix((data, indices, indptr), shape=(n_genes, n_cells))
del data, indices, indptr
print("Matrix built:", mat.shape, "nnz:", mat.nnz)

total_counts = np.asarray(mat.sum(axis=0)).flatten()
total_counts[total_counts == 0] = 1

mat_csr_rows = mat.tocsr()
gene_expr = {}
for g in present:
    idxs = name_to_idx[g]
    row = np.asarray(mat_csr_rows[idxs, :].sum(axis=0)).flatten()
    gene_expr[g] = row
del mat, mat_csr_rows

expr_df = pd.DataFrame(gene_expr, index=barcodes)
norm = expr_df.div(total_counts, axis=0) * 1e4  # CP10K, linear scale

barcode_ct = pd.Series({bc: bc2ct.get(bc) for bc in barcodes})
norm["celltype"] = barcode_ct.values
norm = norm[norm["celltype"].notna()]
print("cells retained with target celltype:", norm.shape[0])
print(norm["celltype"].value_counts())

ref = norm.groupby("celltype").mean()
ref = ref[present].T  # genes x celltypes, linear CP10K scale
ref.to_csv("pelka_reference_signature_linear.csv")
print("Reference signature matrix saved:", ref.shape)
print(ref.round(2))
