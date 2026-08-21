# ARGscore CRC Revisited: Analysis Code

Code and derived (processed/summary-level) data supporting a single-cell, spatial, and
bulk-transcriptomic re-examination of **ARGscore**, a five-gene (VSIG4, CXCL10, CXCL13,
MEIS2, ZNF532) angiogenesis-related prognostic model for colorectal cancer originally
described in Zhang et al., *Front Pharmacol* 2023 (doi:10.3389/fphar.2023.1103547).

The central question addressed here: does a bulk-deconvolution-derived prognostic
signature whose gene set is named after a biological process (angiogenesis) actually
reflect that process, or does it instead encode tumor-microenvironment cell composition?
Across three independent single-cell datasets, one spatial transcriptomics dataset, three
independent bulk cohorts, and an external pan-cancer vasculature atlas, we find that the
five ARGscore genes anchor to three independent cellular programs (M2-polarized
tumor-associated macrophages, T-cell-driven tertiary lymphoid structures, and activated
vascular pericytes) rather than to angiogenic signaling itself.

This repository contains the analysis scripts and derived result tables; it does not
include the manuscript itself, raw sequencing/microarray data, or any third-party
copyrighted material (e.g., the original paper's supplementary files, which were used
locally for cross-validation but are not redistributed here).

## Repository structure

```
scripts/    all analysis scripts (Python unless noted), one script per analysis step
data/       derived/summary-level result tables produced by the scripts (CSV/TSV/TXT)
figures/    all generated figures (PNG)
```

## Script index (grouped by analysis stage)

| Stage | Scripts |
|---|---|
| Single-cell cell-type attribution | `analyze_ge81861.py`, `analyze_pelka.py`, `build_pelka_reference.py`, `analyze_gse146771.py` |
| Spatial transcriptomics co-localization | `analyze_spatial.py`, `plot_panvc.py` |
| Bulk cohort parsing & ARGscore/module scoring | `parse_gse39582.py`, `parse_gse17536.py`, `analyze_tcga.py`, `analyze_coad_read_split.py` |
| Cox regression / time-dependent AUC | `cox_auc_analysis.py`, `optimal_cutpoint_sensitivity.py` |
| Formal NNLS deconvolution | `run_nnls_deconv.py`, `plot_nnls_summary.py` |
| Formal CellPhoneDB ligand-receptor analysis | `extract_cpdb_input.py`, `summarize_cellphonedb.py`, `plot_cpdb_summary.py` |
| TCGA mutation/CNV | `analyze_tcga_mutcnv.py`, `analyze_znf532_cnv_expr.py` |
| External CIBERSORT cross-validation | `validate_against_original_cibersort.py` |
| Meta-analysis / MSI adjustment / FDR correction | `meta_analysis_argscore_hr.py`, `msi_adjusted_association.py`, `msi_adjusted_cox_argscore.py`, `fdr_correction_summary.py` |
| ESTIMATE cross-validation (ssGSEA StromalScore/ImmuneScore) | `estimate_crossvalidation.py`, `plot_estimate_crossvalidation.py` |
| Immunotherapy cohort (pseudobulk from single-cell) | `prepare_indices.py`, `extract_pseudobulk.sh`, `aggregate_pseudobulk.py`, `analyze_icb.py`, `analyze_response.py` |
| Upstream regulator analysis (TF enrichment, methylation) | `enrichr_tf_enrichment.py`, `tf_target_corr_tcga.py`, `tf_target_heatmap.py`, `methylation_analysis.py`, `methylation_figure.py`, `argscore_tf_correlation.py`, `tf_argscore_figure.py` |
| Downstream functional readout & drug connectivity | `fetch_full_tcga_expr.py`, `angiogenic_signaling_downstream.py`, `angio_signaling_figure.py`, `cmap_l1000fwd.py` |
| Manuscript rendering (generic Markdown->docx renderer; the manuscript .md itself is not published here) | `render_paper.py` |
| Working-report assembly (docx generation, not the report itself) | `build_report.py` |

## Data sources

All primary data are public. No data requiring restricted/controlled access were used.

- **UCSC Xena classic hub** (`tcga.xenahubs.net`, via the `xenaPython` package): TCGA-COAD/READ expression (HiSeqV2), somatic mutation (MC3), copy number (GISTIC2), DNA methylation (HumanMethylation450), and clinical/survival data.
- **GEO**: GSE81861, GSE178341, GSE146771 (single-cell), GSE267401 (spatial), GSE39582, GSE17536 (bulk microarray cohorts), GSE205506 and GSE236581 (immunotherapy single-cell cohorts).
- **Enrichr** (`maayanlab.cloud/Enrichr`) and **L1000FWD** (`maayanlab.cloud/l1000fwd`): public REST APIs, no authentication required.
- **CellPhoneDB** official ligand-receptor database, via the official `cellphonedb` Python package.
- Original paper's own Supplementary Material (Zhang et al. 2023) was used locally to cross-validate our independently-computed cell-composition modules against their originally published CIBERSORT output; it is not redistributed in this repository (see `analysis_output/scripts/validate_against_original_cibersort.py` for the analysis code, which expects the reader to obtain that Supplementary Material directly from the journal).

Raw/intermediate files too large for version control (e.g., full single-cell count
matrices) are not included; scripts that consume them expect a local `scratch/`
directory (created automatically, see below) or externally-downloaded raw data — file
paths for externally-sourced raw data are marked in the relevant scripts and need to be
set to your own local download location.

## Reproducing an analysis

```bash
pip install -r requirements.txt
python scripts/<script_name>.py
```

Each script resolves paths relative to the repository root automatically
(`_PROJECT_ROOT` is computed from the script's own location), so scripts can be run
directly after cloning without editing hardcoded paths, with the exception of a small
number of scripts that read externally-downloaded raw data (their raw-data path
variables are clearly marked and need to be set locally).

## Citation

If you use this code, please cite the accompanying manuscript (citation to be added upon
publication) and the original ARGscore paper:

> Zhang C, Liu T, Yun Z, Liang B, Li X, Zhang J. Identification of angiogenesis-related
> subtypes, the development of prognostic models, and the landscape of tumor
> microenvironment infiltration in colorectal cancer. *Front Pharmacol*. 2023;14:1103547.
> doi:10.3389/fphar.2023.1103547

## License

Code is released under the MIT License (see `LICENSE`). This license applies to the
analysis code only; it does not extend to any third-party data referenced but not
redistributed here.
