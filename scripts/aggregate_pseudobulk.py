import csv
import os
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

WORKDIR = f"{_PROJECT_ROOT}/scratch/gse236581"

gene_idx_to_name = {}
with open(f"{WORKDIR}/target_gene_indices.tsv") as f:
    for line in f:
        idx, name = line.rstrip("\n").split("\t")
        gene_idx_to_name[int(idx)] = name

cell_idx_to_patient = {}
with open(f"{WORKDIR}/target_cell_indices.tsv") as f:
    for line in f:
        idx, patient = line.rstrip("\n").split("\t")
        cell_idx_to_patient[int(idx)] = patient

print("target genes:", len(gene_idx_to_name), "target cells:", len(cell_idx_to_patient))

patients = sorted(set(cell_idx_to_patient.values()))
genes = sorted(set(gene_idx_to_name.values()))
sums = {p: {g: 0.0 for g in genes} for p in patients}

n_lines = 0
n_matched = 0
with open(f"{WORKDIR}/filtered_gene_rows.txt") as f:
    for line in f:
        n_lines += 1
        row, col, val = line.split()
        col = int(col)
        patient = cell_idx_to_patient.get(col)
        if patient is None:
            continue
        gene = gene_idx_to_name[int(row)]
        sums[patient][gene] += float(val)
        n_matched += 1

print(f"done: {n_lines} filtered lines scanned, {n_matched} matched to target cells")

with open(f"{WORKDIR}/pseudobulk_gene_sums.tsv", "w") as f:
    f.write("Patient\t" + "\t".join(genes) + "\n")
    for p in patients:
        f.write(p + "\t" + "\t".join(str(sums[p][g]) for g in genes) + "\n")
print("saved pseudobulk_gene_sums.tsv")
