import h5py
import numpy as np
import scipy.sparse as sp
import pandas as pd

H5 = "GSE178341_full.h5"
ARGS36 = ["APOH","APP","CCND2","COL3A1","COL5A2","CXCL6","FGFR1","FSTL1","ITGAV","JAG1",
          "JAG2","KCNJ8","LPL","LRPAP1","LUM","MSX1","NRP1","OLR1","PDGFA","PF4",
          "PGLYRP1","POSTN","PRG2","PTK2","S100A4","SERPINA5","SLCO2A1","SPP1","STC1","THBD",
          "TIMP1","TNFRSF21","VAV2","VCAN","VEGFA","VTN"]
SIG5 = ["VSIG4","CXCL10","CXCL13","MEIS2","ZNF532"]
RECEPTORS = ["FLT1","KDR","NOTCH4","PDGFRB","CXCR3","CXCR5","NOTCH1","NOTCH2","NOTCH3"]
TARGETS = list(dict.fromkeys(ARGS36 + SIG5 + RECEPTORS))

print("Loading h5 file...")
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

print("Loading sparse matrix arrays...")
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
norm = expr_df.div(total_counts, axis=0) * 1e4
lognorm = np.log1p(norm)

lognorm.to_csv("pelka_target_gene_lognorm.csv")
print("Saved lognorm matrix:", lognorm.shape)
