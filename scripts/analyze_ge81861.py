import pandas as pd
import numpy as np

ARGS36 = ["APOH","APP","CCND2","COL3A1","COL5A2","CXCL6","FGFR1","FSTL1","ITGAV","JAG1",
          "JAG2","KCNJ8","LPL","LRPAP1","LUM","MSX1","NRP1","OLR1","PDGFA","PF4",
          "PGLYRP1","POSTN","PRG2","PTK2","S100A4","SERPINA5","SLCO2A1","SPP1","STC1","THBD",
          "TIMP1","TNFRSF21","VAV2","VCAN","VEGFA","VTN"]
SIG5 = ["VSIG4","CXCL10","CXCL13","MEIS2","ZNF532"]

def load(fp):
    df = pd.read_csv(fp, index_col=0)
    df.index = [str(i).split('_')[1] if len(str(i).split('_')) >= 3 else str(i) for i in df.index]
    return df

nm = load("GSE81861_CRC_NM_all_cells_FPKM.csv")
tm = load("GSE81861_CRC_tumor_all_cells_FPKM.csv")

nm = nm.groupby(nm.index).mean()
tm = tm.groupby(tm.index).mean()

common_genes = nm.index.intersection(tm.index)
nm = nm.loc[common_genes]
tm = tm.loc[common_genes]

combined = pd.concat([nm, tm], axis=1)

cols = combined.columns
cell_type = [c.split('__')[1] if '__' in c else 'NA' for c in cols]
source = (['NM'] * nm.shape[1]) + (['Tumor'] * tm.shape[1])

meta = pd.DataFrame({'cell': cols, 'celltype': cell_type, 'source': source})
meta = meta[meta.celltype != 'NA']
combined = combined[meta.cell.values]

genes_present = [g for g in ARGS36 + SIG5 if g in combined.index]
logexpr = np.log2(combined.loc[genes_present] + 1)

result = {}
for ct in meta.celltype.unique():
    cells = meta[meta.celltype == ct].cell.values
    result[ct] = logexpr[cells].mean(axis=1)
mean_by_ct = pd.DataFrame(result)
mean_by_ct['n_cells'] = meta.celltype.value_counts()
mean_by_ct.to_csv("mean_expr_by_celltype.csv")

meta.to_csv("cell_meta.csv", index=False)
combined.loc[genes_present].to_csv("target_gene_expr_matrix.csv")
print("n cells by type:")
print(meta.celltype.value_counts())
print("Saved: mean_expr_by_celltype.csv, cell_meta.csv, target_gene_expr_matrix.csv")

z = mean_by_ct.drop(columns=['n_cells'])
z = z.sub(z.mean(axis=1), axis=0).div(z.std(axis=1)+1e-9, axis=0)
top_ct = z.idxmax(axis=1)
summary = pd.DataFrame({'top_celltype': top_ct, 'zscore': z.max(axis=1).round(2)})
summary = summary.join(mean_by_ct.drop(columns=['n_cells']).round(2))
summary.to_csv("gene_celltype_attribution.csv")
print(summary.sort_values(['top_celltype','zscore'], ascending=[True,False])[['top_celltype','zscore']])
