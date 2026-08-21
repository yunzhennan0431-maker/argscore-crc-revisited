"""
ESTIMATE algorithm cross-validation (3.24): computes ssGSEA-based StromalScore/
ImmuneScore/ESTIMATEScore for GSE39582, GSE17536, and TCGA-COAD/READ, and
correlates them with ARGscore, as a second deconvolution/enrichment method
orthogonal to the CIBERSORT-based validation in 3.13.

Gene sets: official ESTIMATE StromalSignature/ImmuneSignature (141 genes each),
extracted from the ESTIMATE R package v1.0.11 inst/extdata/SI_geneset.gmt
(Yoshihara et al. 2013, Nat Commun 4:2612).

Raw-data prerequisites (not bundled in this repo due to size; download once
locally and point RAW_DATA_DIR at the containing folder):
  - GPL570.txt: platform annotation table for Affymetrix HG-U133 Plus 2.0,
    from https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GPL570
  - GSE39582_series_matrix.txt.gz, GSE17536_series_matrix.txt.gz, from
    https://ftp.ncbi.nlm.nih.gov/geo/series/GSE39nnn/GSE39582/matrix/ and
    https://ftp.ncbi.nlm.nih.gov/geo/series/GSE17nnn/GSE17536/matrix/
Expected layout: RAW_DATA_DIR/GPL570/GPL570.txt,
RAW_DATA_DIR/GSE39582/GSE39582_series_matrix.txt.gz,
RAW_DATA_DIR/GSE17536/GSE17536_series_matrix.txt.gz.
TCGA-COAD/READ expression is fetched live via xenaPython, no local file needed.
"""
import gzip
import os
import warnings

import numpy as np
import pandas as pd
import xenaPython as xena
from scipy.stats import spearmanr
import gseapy

warnings.filterwarnings("ignore")

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BASE = f"{_PROJECT_ROOT}"
DATA_DIR = os.path.join(BASE, "analysis_output", "data")
RAW_DATA_DIR = os.environ.get("ESTIMATE_RAW_DATA_DIR", os.path.expanduser("~/CRC_raw_data"))
XENA_HOST = "https://tcga.xenahubs.net"

IMMUNE_GENES = ["LCP2","LSP1","FYB","PLEK","HCK","IL10RA","LILRB1","NCKAP1L","LAIR1","NCF2","CYBB","PTPRC","IL7R","LAPTM5","CD53","EVI2B","SLA","ITGB2","GIMAP4","MYO1F","HCLS1","MNDA","IL2RG","CD48","AOAH","CCL5","LTB","GMFG","GIMAP6","GZMK","LST1","GPR65","LILRB2","WIPF1","CD37","BIN2","FCER1G","IKZF1","TYROBP","FGL2","FLI1","IRF8","ARHGAP15","SH2B3","TNFRSF1B","DOCK2","CD2","ARHGEF6","CORO1A","LY96","LYZ","ITGAL","TNFAIP3","RNASE6","TGFB1","PSTPIP1","CST7","RGS1","FGR","SELL","MICAL1","TRAF3IP3","ITGA4","MAFB","ARHGDIB","IL4R","RHOH","HLA-DPA1","NKG7","NCF4","LPXN","ITK","SELPLG","HLA-DPB1","CD3D","CD300A","IL2RB","ADCY7","PTGER4","SRGN","CD247","CCR7","MSN","ALOX5AP","PTGER2","RAC2","GBP2","VAV1","CLEC2B","P2RY14","NFKBIA","S100A9","IFI30","MFSD1","RASSF2","TPP1","RHOG","CLEC4A","GZMB","PVRIG","S100A8","CASP1","BCL2A1","HLA-E","KLRB1","GNLY","RAB27A","IL18RAP","TPST2","EMP3","GMIP","LCK","IL32","PTPRCAP","LGALS9","CCDC69","SAMHD1","TAP1","GBP1","CTSS","GZMH","ADAM8","GLRX","PRF1","CD69","HLA-B","HLA-DMA","CD74","KLRK1","PTPRE","HLA-DRA","VNN2","TCIRG1","RABGAP1L","CSTA","ZAP70","HLA-F","HLA-G","CD52","CD302","CD27"]
STROMAL_GENES = ["DCN","PAPPA","SFRP4","THBS2","LY86","CXCL14","FOXF1","COL10A1","ACTG2","APBB1IP","SH2D1A","SULF1","MSR1","C3AR1","FAP","PTGIS","ITGBL1","BGN","CXCL12","ECM2","FCGR2A","MS4A4A","WISP1","COL1A2","MS4A6A","EDNRA","VCAM1","GPR124","SCUBE2","AIF1","HEPH","LUM","PTGER3","RUNX1T1","CDH5","PIK3R5","RAMP3","LDB2","COX7A1","EDIL3","DDR2","FCGR2B","LPPR4","COL15A1","AOC3","ITIH3","FMO1","PRKG1","PLXDC1","VSIG4","COL6A3","SGCD","COL3A1","F13A1","OLFML1","IGSF6","COMP","HGF","GIMAP5","ABCA6","ITGAM","MAF","ITM2A","CLEC7A","ASPN","LRRC15","ERG","CD86","TRAT1","COL8A2","TCF21","CD93","CD163","GREM1","LMOD1","TLR2","ZEB2","C1QB","KCNJ8","KDR","CD33","RASGRP3","TNFSF4","CCR1","CSF1R","BTK","MFAP5","MXRA5","ISLR","ARHGAP28","ZFPM2","TLR7","ADAM12","OLFML2B","ENPP2","CILP","SIGLEC1","SPON2","PLXNC1","ADAMTS5","SAMSN1","CH25H","COL14A1","EMCN","RGS4","PCDH12","RARRES2","CD248","PDGFRB","C1QA","COL5A3","IGF1","SP140","TFEC","TNN","ATP8B4","ZNF423","FRZB","SERPING1","ENPEP","CD14","DIO2","FPR1","IL18R1","HDC","TXNDC3","PDE2A","RSAD2","ITIH5","FASLG","MMP3","NOX4","WNT2","LRRC32","CXCL9","ODZ4","FBLN2","EGFL6","IL1B","SPON1","CD200"]
GENE_SETS = {"StromalSignature": STROMAL_GENES, "ImmuneSignature": IMMUNE_GENES}


def parse_gpl570_probe2gene(path):
    probe2gene = {}
    with open(path, "r", encoding="latin1") as f:
        in_table = False
        header = None
        for line in f:
            if line.startswith("!platform_table_begin"):
                in_table = True
                continue
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
            field = parts[gs_idx]
            if not field or "///" in field:
                continue  # unambiguous single-gene probes only
            probe2gene[parts[0]] = field
    return probe2gene


def extract_full_genome(gz_path, probe2gene):
    with gzip.open(gz_path, "rt", encoding="latin1") as f:
        line = f.readline()
        while line and not line.startswith("!series_matrix_table_begin"):
            line = f.readline()
        header_line = f.readline().rstrip("\n").split("\t")
        sample_ids = [h.strip('"') for h in header_line[1:]]
        sums, counts = {}, {}
        for line in f:
            if line.startswith("!series_matrix_table_end"):
                break
            parts = line.rstrip("\n").split("\t")
            gene = probe2gene.get(parts[0].strip('"'))
            if gene is None:
                continue
            vals = np.array([float(x) if x not in ("", "NA", "null") else np.nan for x in parts[1:]],
                             dtype=np.float32)
            if gene not in sums:
                sums[gene] = np.zeros(len(sample_ids))
                counts[gene] = np.zeros(len(sample_ids), dtype=np.int32)
            mask = ~np.isnan(vals)
            sums[gene][mask] += vals[mask]
            counts[gene][mask] += 1
    genes = list(sums.keys())
    mat = np.array([sums[g] / np.maximum(counts[g], 1) for g in genes], dtype=np.float32)
    return pd.DataFrame(mat, index=genes, columns=sample_ids)


def fetch_tcga_full_expr():
    ds_probe = "TCGA.COAD.sampleMap/HiSeqV2"
    genes = sorted(set(f.split("|")[0] for f in xena.dataset_field(XENA_HOST, ds_probe) if not f.startswith("?")))
    frames = []
    for cohort in ("COAD", "READ"):
        ds = f"TCGA.{cohort}.sampleMap/HiSeqV2"
        samples = xena.dataset_samples(XENA_HOST, ds, None)
        vals = {}
        for i in range(0, len(genes), 4000):
            sub = genes[i:i + 4000]
            for g, v in zip(sub, xena.dataset_fetch(XENA_HOST, ds, samples, sub)):
                vals[g] = v
        df = pd.DataFrame(vals, index=samples).apply(pd.to_numeric, errors="coerce")
        frames.append(df)
    expr = pd.concat(frames)
    return expr[~expr.index.duplicated()].T  # genes x samples


def run_ssgsea(gene_by_sample_df):
    res = gseapy.ssgsea(data=gene_by_sample_df, gene_sets=GENE_SETS, outdir=None,
                         min_size=5, sample_norm_method="rank", no_plot=True)
    return res.res2d.pivot(index="Name", columns="Term", values="ES").astype(float)


def analyze_cohort(tag, gene_expr_df, argscore_series):
    scores = run_ssgsea(gene_expr_df)
    scores["ESTIMATEScore"] = scores["StromalSignature"] + scores["ImmuneSignature"]
    common = scores.index.intersection(argscore_series.index)
    scores, arg = scores.loc[common], argscore_series.loc[common]
    rows = []
    for col in ["StromalSignature", "ImmuneSignature", "ESTIMATEScore"]:
        rho, p = spearmanr(arg, scores[col])
        rows.append(dict(cohort=tag, n=len(common), score=col, spearman_rho=rho, spearman_p=p))
    scores.to_csv(os.path.join(DATA_DIR, f"estimate_scores_{tag}.csv"))
    return rows


if __name__ == "__main__":
    print("Parsing GPL570 platform annotation...")
    probe2gene = parse_gpl570_probe2gene(os.path.join(RAW_DATA_DIR, "GPL570", "GPL570.txt"))
    print("unambiguous single-gene probes:", len(probe2gene))

    all_rows = []

    print("\nGSE39582 full-transcriptome extraction + ssGSEA...")
    gse39582_expr = extract_full_genome(
        os.path.join(RAW_DATA_DIR, "GSE39582", "GSE39582_series_matrix.txt.gz"), probe2gene)
    bulk = pd.read_csv(os.path.join(DATA_DIR, "bulk_closure_result.csv"), index_col=0)
    all_rows += analyze_cohort("GSE39582", gse39582_expr, bulk["ARGscore"])

    print("\nGSE17536 full-transcriptome extraction + ssGSEA...")
    gse17536_expr = extract_full_genome(
        os.path.join(RAW_DATA_DIR, "GSE17536", "GSE17536_series_matrix.txt.gz"), probe2gene)
    g17536 = pd.read_csv(os.path.join(DATA_DIR, "gse17536_closure_result.csv"), index_col=0)
    all_rows += analyze_cohort("GSE17536", gse17536_expr, g17536["ARGscore"])

    print("\nTCGA-COAD/READ full-transcriptome fetch + ssGSEA...")
    tcga_expr = fetch_tcga_full_expr()
    tcga = pd.read_csv(os.path.join(DATA_DIR, "tcga_coadread_closure_result.csv"), index_col=0)
    all_rows += analyze_cohort("TCGA_COADREAD", tcga_expr, tcga["ARGscore"])

    summary = pd.DataFrame(all_rows)
    summary.to_csv(os.path.join(DATA_DIR, "estimate_crossvalidation_summary.csv"), index=False)
    pd.set_option("display.width", 160)
    print("\n" + summary.round(4).to_string(index=False))
