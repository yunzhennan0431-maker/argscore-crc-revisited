import gzip, json
import pandas as pd
import numpy as np

MATRIX_GZ = "GSE17536_series_matrix.txt.gz"
PLATFORM = "GPL570.txt"

probe2gene = {}
with open(PLATFORM, "r", encoding="latin1") as f:
    in_table = False
    header = None
    for line in f:
        if line.startswith("!platform_table_begin"):
            in_table = True; continue
        if line.startswith("!platform_table_end"):
            break
        if not in_table:
            continue
        if header is None:
            header = line.rstrip("\n").split("\t")
            gs_idx = header.index("Gene Symbol")
            continue
        parts = line.rstrip("\n").split("\t")
        if len(parts) <= gs_idx:
            continue
        probe2gene[parts[0]] = parts[gs_idx]

TARGET_SIG5 = ["VSIG4", "CXCL10", "CXCL13", "MEIS2", "ZNF532"]
MARKERS = {
    "Macrophage_TAM": ["CD68", "CD163", "MRC1", "MSR1", "CSF1R"],
    "Endothelial": ["PECAM1", "VWF", "CDH5"],
    "Pericyte": ["RGS5", "ACTA2", "NOTCH3", "PDGFRB"],
    "CD8T": ["CD8A", "CD8B"],
    "Bcell_TLS": ["MS4A1", "CD79A", "CR2"],
}
ALL_TARGETS = set(TARGET_SIG5)
for v in MARKERS.values():
    ALL_TARGETS.update(v)

def gene_match(field, gene):
    return gene in [s.strip() for s in field.split("///")]

gene2probes = {g: [] for g in ALL_TARGETS}
for probe, field in probe2gene.items():
    if not field:
        continue
    for g in ALL_TARGETS:
        if gene_match(field, g):
            gene2probes[g].append(probe)

sample_ids = None
char_rows = []
with gzip.open(MATRIX_GZ, "rt", encoding="latin1") as f:
    line = f.readline()
    while line:
        if line.startswith("!Sample_geo_accession"):
            sample_ids = [s.strip('"') for s in line.rstrip("\n").split("\t")[1:]]
        elif line.startswith("!Sample_characteristics_ch1"):
            char_rows.append(line.rstrip("\n").split("\t")[1:])
        elif line.startswith("!series_matrix_table_begin"):
            break
        line = f.readline()
    header_line = f.readline().rstrip("\n").split("\t")
    header_line = [h.strip('"') for h in header_line]
    matrix_sample_ids = header_line[1:]
    data_rows = []
    probe_ids = []
    for line in f:
        if line.startswith("!series_matrix_table_end"):
            break
        parts = line.rstrip("\n").split("\t")
        probe_ids.append(parts[0].strip('"'))
        data_rows.append(parts[1:])

print("n samples:", len(matrix_sample_ids), "n probes:", len(probe_ids))

clinical = {}
for row in char_rows:
    row = [c.strip('"') for c in row]
    key = None
    for c in row:
        if ":" in c:
            key = c.split(":", 1)[0].strip(); break
    if key is None:
        continue
    vals = [c.split(":", 1)[1].strip() if ":" in c else np.nan for c in row]
    clinical[key] = vals
clinical_df = pd.DataFrame(clinical, index=sample_ids)
clinical_df.to_csv("gse17536_clinical.csv")
print("clinical fields:", list(clinical_df.columns))

target_probes = set()
for plist in gene2probes.values():
    target_probes.update(plist)
keep_idx = [i for i, pid in enumerate(probe_ids) if pid in target_probes]
kept_probe_ids = [probe_ids[i] for i in keep_idx]
expr_rows = []
for i in keep_idx:
    vals = [float(x) if x not in ("", "NA", "null") else np.nan for x in data_rows[i]]
    expr_rows.append(vals)
expr_df = pd.DataFrame(expr_rows, index=kept_probe_ids, columns=matrix_sample_ids)
expr_df.to_csv("gse17536_target_probe_expr.csv")
with open("gene2probes.json", "w") as f:
    json.dump(gene2probes, f)
print("Done.")
