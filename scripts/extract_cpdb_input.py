"""
Extract counts + meta files for CellPhoneDB statistical analysis from the
Pelka et al. 2021 CRC atlas (GSE178341), restricted to the CellPhoneDB gene
panel and to Macro / TCD8 / Peri (+ Endo, B for context) cell types.
Subsamples large populations to keep permutation testing tractable.
"""
import csv
import random

import h5py
import numpy as np
import pandas as pd
import scipy.sparse as sp

random.seed(0)
np.random.seed(0)

H5 = "../deconv/GSE178341_full.h5"
CLUSTER_CSV = "../deconv/GSE178341_cluster.csv"
GENE_INPUT = "db/gene_input.csv"

TARGET_CT = ["Macro", "TCD8", "Peri", "Endo", "B"]
MAX_CELLS_PER_CT = 1200

cpdb_genes = set()
with open(GENE_INPUT) as f:
    r = csv.DictReader(f)
    for row in r:
        cpdb_genes.add(row["hgnc_symbol"])
print("CellPhoneDB gene panel size:", len(cpdb_genes))

print("Loading barcode -> celltype map...")
bc2ct = {}
with open(CLUSTER_CSV) as f:
    r = csv.DictReader(f)
    for row in r:
        if row["clMidwayPr"] in TARGET_CT:
            bc2ct[row["sampleID"]] = row["clMidwayPr"]

by_ct = {}
for bc, ct in bc2ct.items():
    by_ct.setdefault(ct, []).append(bc)
selected_bc = set()
for ct, bcs in by_ct.items():
    if len(bcs) > MAX_CELLS_PER_CT:
        bcs = random.sample(bcs, MAX_CELLS_PER_CT)
    selected_bc.update(bcs)
    print(ct, "selected", len(bcs), "of", len(by_ct[ct]))

print("total selected cells:", len(selected_bc))

print("Loading h5...")
f = h5py.File(H5, "r")
n_genes, n_cells = f["matrix/shape"][:]
names = np.array([x.decode() for x in f["matrix/features/name"][:]])
barcodes = np.array([x.decode() for x in f["matrix/barcodes"][:]])

gene_mask = np.isin(names, list(cpdb_genes))
gene_idx = np.where(gene_mask)[0]
print("genes found in h5 matching CellPhoneDB panel:", len(gene_idx), "/", len(cpdb_genes))

bc_to_pos = {bc: i for i, bc in enumerate(barcodes)}
cell_positions = [bc_to_pos[bc] for bc in selected_bc if bc in bc_to_pos]
print("cells found in h5:", len(cell_positions))

print("Loading sparse matrix (this may take a bit)...")
data = f["matrix/data"][:]
indices = f["matrix/indices"][:]
indptr = f["matrix/indptr"][:]
mat = sp.csc_matrix((data, indices, indptr), shape=(n_genes, n_cells))
del data, indices, indptr

sub = mat[gene_idx, :][:, cell_positions]
sub = sub.tocsc()
print("submatrix:", sub.shape, "nnz:", sub.nnz)

total_counts = np.asarray(mat[:, cell_positions].sum(axis=0)).flatten()
total_counts[total_counts == 0] = 1
del mat

norm = sub.multiply(1.0 / total_counts).tocsc() * 1e4
norm = norm.tocsr()
lognorm = norm.copy()
lognorm.data = np.log1p(lognorm.data)

gene_names_sel = names[gene_idx]
cell_ids_sel = [barcodes[p] for p in cell_positions]

print("Writing counts.txt (genes x cells, log-normalized)...")
counts_df = pd.DataFrame.sparse.from_spmatrix(lognorm, index=gene_names_sel, columns=cell_ids_sel)
counts_df = counts_df.groupby(counts_df.index).mean()  # collapse duplicate gene symbols
counts_df.to_csv("counts.txt", sep="\t")

meta_df = pd.DataFrame({"Cell": cell_ids_sel, "cell_type": [bc2ct[bc] for bc in cell_ids_sel]})
meta_df.to_csv("meta.txt", sep="\t", index=False)

print("counts shape:", counts_df.shape)
print(meta_df.cell_type.value_counts())
print("Done.")
