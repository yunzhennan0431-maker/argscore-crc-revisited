"""
Formal CellPhoneDB (v5, statistical_analysis method, 1000 permutations) on our
own primary CRC single-cell atlas (GSE178341, Pelka et al. 2021 Cell),
restricted to Macro / TCD8 / Peri / Endo / B (1200 cells each, subsampled for
tractability), testing whether the Macro->Pericyte and CD8T->Pericyte ligand-
receptor interactions found opportunistically in the external Pan-tumor
Vasculature Atlas (Pan et al. 2024 Nature) replicate in our own data.
"""
import os
import pandas as pd
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BASE = f"{_PROJECT_ROOT}"
DATA_DIR = os.path.join(BASE, "analysis_output", "data")

sig = pd.read_csv(os.path.join(DATA_DIR, "cpdb_significant_means.txt"), sep="\t")

pairs_of_interest = ["Macro|Peri", "TCD8|Peri", "Peri|Macro", "Peri|TCD8"]
comparison = [
    ("GAS6-AXL", "M2-like Macro -> BASP1+ matPC", ["GAS6_AXL"], "TAM->Peri 耐受轴"),
    ("LGALS9 (multi-receptor)", "M2-like Macro -> BASP1+ matPC", ["LGALS9_P4HB"], "Galectin-9 免疫抑制信号"),
    ("SIRPA-CD47", "M2-like Macro -> BASP1+ matPC", ["CD47_SIRPA"], "\"别吃我\"信号"),
    ("TYROBP-CD44", "M2-like Macro -> BASP1+ matPC", ["CD44_TYROBP"], "髓系激活相关"),
    ("FASLG-TNFRSF1A/FAS", "CD8_Tex/TRM -> BASP1+ matPC", ["FASLG_FAS"], "细胞毒性/凋亡诱导"),
    ("LTB-LTBR", "CD8_Tem/Tm -> BASP1+ matPC", ["LTB_LTBR"], "三级淋巴结构(TLS)组织信号"),
    ("CD74-APP/COPA", "CD8_TRM/Tex -> BASP1+ matPC", ["APP_CD74"], "MIF-CD74轴"),
]

rows = []
for label, external_direction, gene_pairs, meaning in comparison:
    hits = []
    for gp in gene_pairs:
        match = sig[sig["interacting_pair"] == gp]
        if len(match) == 0:
            continue
        row = match.iloc[0]
        for pair in pairs_of_interest:
            if pd.notna(row[pair]):
                hits.append(f"{pair}={row[pair]:.3f}")
    rows.append(dict(
        lr_pair=label,
        external_atlas_direction=external_direction,
        our_gse178341_hits="; ".join(hits) if hits else "未检出显著信号",
        replicated=bool(hits),
        biological_meaning=meaning,
    ))

out_df = pd.DataFrame(rows)
out_df.to_csv(os.path.join(DATA_DIR, "cpdb_replication_comparison.csv"), index=False)
print(out_df.to_string(index=False))
print(f"\n{out_df.replicated.sum()}/{len(out_df)} target L-R molecule pairs replicated (any direction) in our own GSE178341 CellPhoneDB analysis.")
