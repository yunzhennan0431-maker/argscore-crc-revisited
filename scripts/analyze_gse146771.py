# -*- coding: utf-8 -*-
import numpy as np
import pandas as pd

HEADER = "/tmp/gse146771_header.txt"
ROWS = "/tmp/gse146771_target_rows.txt"
METADATA = "metadata.txt"

with open(HEADER) as f:
    header = f.readline().strip()
cell_names = [c.strip('"') for c in header.split(" ")]
print("n cells (header):", len(cell_names))

gene_rows = {}
with open(ROWS) as f:
    for line in f:
        parts = line.strip().split(" ")
        gene = parts[0].strip('"')
        vals = np.array(parts[1:], dtype=float)
        gene_rows[gene] = vals

expr = pd.DataFrame(gene_rows, index=cell_names)
print("expr shape:", expr.shape)

meta = pd.read_csv(METADATA, sep="\t")
meta = meta.set_index("CellName")

common = expr.index.intersection(meta.index)
print("common cells:", len(common))
expr = expr.loc[common]
meta = meta.loc[common]

log_expr = np.log2(expr + 1)
log_expr["Global_Cluster"] = meta["Global_Cluster"].values
log_expr["Sub_Cluster"] = meta["Sub_Cluster"].values

log_expr.to_csv("gse146771_target_expr_with_meta.csv")
print("Saved gse146771_target_expr_with_meta.csv")
