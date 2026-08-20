import csv
import os
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

WORKDIR = f"{_PROJECT_ROOT}/scratch/gse236581"

SIG5 = ["VSIG4", "CXCL10", "CXCL13", "MEIS2", "ZNF532"]
MARKERS = {
    "Macrophage_TAM": ["CD68", "CD163", "MRC1", "MSR1", "CSF1R", "C1QA", "C1QB", "APOE"],
    "Endothelial": ["PECAM1", "VWF", "CDH5", "CLDN5", "ENG"],
    "Pericyte": ["RGS5", "ACTA2", "NOTCH3", "PDGFRB", "MYH11", "TAGLN"],
    "CD8T": ["CD8A", "CD8B", "CD3D", "CD3E", "GZMK"],
    "Bcell_TLS": ["MS4A1", "CD79A", "CD79B", "CR2", "CD19"],
}
TARGET_GENES = list(dict.fromkeys(SIG5 + [g for v in MARKERS.values() for g in v]))
print("target genes:", len(TARGET_GENES))

# --- gene indices (1-based, matching features.tsv line order = mtx row index) ---
gene_idx = {}
with open(f"{WORKDIR}/features.tsv") as f:
    for i, line in enumerate(f, start=1):
        name = line.split("\t")[0]
        if name in TARGET_GENES and name not in gene_idx:
            gene_idx[name] = i

missing = [g for g in TARGET_GENES if g not in gene_idx]
print("genes found:", len(gene_idx), "missing:", missing)
with open(f"{WORKDIR}/target_gene_indices.tsv", "w") as f:
    for g, idx in gene_idx.items():
        f.write(f"{idx}\t{g}\n")

# --- cell indices (1-based, matching barcodes.tsv line order = mtx col index) ---
# baseline tumor cells for the 20 CRC patients
import csv as csvmod
baseline_samples = set()
with open("/tmp/gse236581_baseline_tumor_samples.csv") as f:
    r = csvmod.DictReader(f)
    for row in r:
        baseline_samples.add(row["Patient ID"])
print("target patients:", len(baseline_samples))

# cell_id -> (patient, nCount_RNA), from metadata.txt
# parts: 0=cell_id 1=orig.ident 2=nCount_RNA 3=nFeature_RNA 4=Ident 5=Patient 6=Treatment 7=Tissue 8=MajorCellType 9=SubCellType
target_cell_to_patient = {}
target_cell_ncount = {}
with open(f"{WORKDIR}/metadata.txt") as f:
    header = f.readline()
    for line in f:
        parts = line.rstrip("\n").split()
        if len(parts) < 9:
            continue
        cell_id = parts[0].strip('"')
        ncount = parts[2]
        patient = parts[5].strip('"')
        treatment = parts[6].strip('"')
        tissue = parts[7].strip('"')
        if tissue == "Tumor" and treatment == "I" and patient in baseline_samples:
            target_cell_to_patient[cell_id] = patient
            target_cell_ncount[cell_id] = float(ncount)

print("target baseline tumor cells (metadata):", len(target_cell_to_patient))

# per-patient total UMI (genome-wide library size sum) for CP10K-style normalization
from collections import defaultdict
patient_total_umi = defaultdict(float)
patient_n_cells = defaultdict(int)
for cid, patient in target_cell_to_patient.items():
    patient_total_umi[patient] += target_cell_ncount[cid]
    patient_n_cells[patient] += 1
with open(f"{WORKDIR}/patient_total_umi.tsv", "w") as f:
    for p, tot in patient_total_umi.items():
        f.write(f"{p}\t{tot}\t{patient_n_cells[p]}\n")
print("patient total UMI saved")

cell_idx_to_patient = {}
with open(f"{WORKDIR}/barcodes.tsv") as f:
    for i, line in enumerate(f, start=1):
        cid = line.strip()
        if cid in target_cell_to_patient:
            cell_idx_to_patient[i] = target_cell_to_patient[cid]

print("matched in barcodes.tsv:", len(cell_idx_to_patient))
with open(f"{WORKDIR}/target_cell_indices.tsv", "w") as f:
    for idx, patient in cell_idx_to_patient.items():
        f.write(f"{idx}\t{patient}\n")
print("done")
