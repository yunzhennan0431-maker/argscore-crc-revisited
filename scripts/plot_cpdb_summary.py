import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BASE = f"{_PROJECT_ROOT}"
DATA_DIR = os.path.join(BASE, "analysis_output", "data")
FIG_DIR = os.path.join(BASE, "analysis_output", "figures")

sig = pd.read_csv(os.path.join(DATA_DIR, "cpdb_significant_means.txt"), sep="\t")
pvals = pd.read_csv(os.path.join(DATA_DIR, "cpdb_pvalues.txt"), sep="\t")

targets = [
    ("GAS6_AXL", "Macro|Peri"),
    ("LGALS9_P4HB", "Macro|Peri"),
    ("CD47_SIRPA", "Peri|Macro"),
    ("CD44_TYROBP", "Peri|Macro"),
    ("FASLG_FAS", "TCD8|Peri"),
    ("LTB_LTBR", "TCD8|Peri"),
    ("APP_CD74", "Peri|Macro"),
]

rows = []
for gp, pair in targets:
    m = sig[sig["interacting_pair"] == gp]
    pv = pvals[pvals["interacting_pair"] == gp]
    if len(m) == 0:
        continue
    mean_val = m.iloc[0][pair]
    p_val = pv.iloc[0][pair] if len(pv) else np.nan
    rows.append((f"{gp}\n({pair})", mean_val, p_val))

labels = [r[0] for r in rows]
means = [r[1] for r in rows]
ps = [r[2] for r in rows]

fig, ax = plt.subplots(figsize=(9, 5))
y = np.arange(len(labels))
colors = ["#C44E52" if "Macro" in l.split("(")[1] and l.split("|")[0].split("(")[1] == "Macro" else "#4C72B0" for l in labels]
bar_colors = []
for gp, pair in targets:
    if pair.startswith("Macro") or pair.startswith("Peri|Macro"):
        bar_colors.append("#C44E52" if pair == "Macro|Peri" else "#DD8452")
    else:
        bar_colors.append("#4C72B0")

bars = ax.barh(y, means, color=bar_colors)
for yi, (m, p) in zip(y, zip(means, ps)):
    star = "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else "ns"
    ax.text(m + 0.03, yi, f"mean={m:.2f}, p={star}", va="center", fontsize=8)

ax.set_yticks(y)
ax.set_yticklabels(labels, fontsize=9)
ax.invert_yaxis()
ax.set_xlabel("CellPhoneDB significant mean (statistical_analysis method, 1000 permutations)")
ax.set_title("Formal CellPhoneDB replication in our own GSE178341 data\n(Macro / CD8T <-> Pericyte, matching external atlas L-R pairs)")
ax.set_xlim(0, max(means) * 1.5)
fig.tight_layout()
out = os.path.join(FIG_DIR, "cpdb_own_data_replication.png")
fig.savefig(out, dpi=200)
print("saved", out)
