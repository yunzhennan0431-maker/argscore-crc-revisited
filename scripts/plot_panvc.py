# -*- coding: utf-8 -*-
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

# raw box stats extracted from http://resource.yin-lab.com/Panvascular/ (Pan et al. 2024 Nature)
# format: label -> (low, q1, median, q3, high)
vascular_ec = {
    "VenEC": (-0.596, -0.297, -0.164, -0.097, None),
    "CapEC": (-0.857, -0.453, -0.320, -0.184, None),
    "ArtEC": (-0.853, -0.444, -0.292, -0.171, None),
}
lymphatic_ec = {
    "NLEC": (-0.457, -0.251, -0.171, -0.112, None),
    "inter_LEC": (-0.682, -0.318, -0.175, -0.074, None),
    "apLEC": (-0.430, -0.199, -0.126, -0.043, None),
    "Tip_like_LEC": (-1.286, -0.538, -0.277, -0.024, None),
    "Stalk_like_LEC": (-1.018, -0.451, -0.175, -0.032, None),
}
mural = {
    "matPC_Q": (-1.325, -0.672, -0.338, -0.141, 0.648),
    "myoPC": (-1.061, -0.510, -0.249, -0.137, 0.364),
    "adiPC": (-0.634, -0.304, -0.147, -0.081, 0.081),
    "vdPC": (-0.527, -0.302, -0.217, -0.151, 0.073),
    "inter.matPC": (-1.657, -0.753, -0.398, 0.654, 2.755),
    "BASP1+ matPC": (-2.049, -0.870, -0.511, 1.009, 3.824),
    "SMC": (-0.607, -0.304, -0.173, -0.102, 0.087),
}

def to_bxp_stats(d):
    stats = []
    for label, (lo, q1, med, q3, hi) in d.items():
        if hi is None:
            hi = q3 + 1.5 * (q3 - lo)  # not used for display since EC/LEC panels omit whisker-high in our extraction
        stats.append({
            "label": label, "whislo": lo, "q1": q1, "med": med, "q3": q3, "whishi": hi,
            "fliers": []
        })
    return stats

fig, axes = plt.subplots(1, 3, figsize=(16, 5), gridspec_kw={"width_ratios": [3, 5, 7]})

for ax, d, title in zip(axes, [vascular_ec, lymphatic_ec, mural], ["Vascular EC", "Lymphatic EC", "Mural Cell"]):
    stats = to_bxp_stats(d)
    bp = ax.bxp(stats, showfliers=False, patch_artist=True)
    colors = ["#c0392b" if "BASP1" in s["label"] or "inter.matPC" == s["label"] else "#2980b9" for s in stats]
    for patch, color in zip(bp["boxes"], colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.5)
    ax.set_title(f"{title}: ZNF532 expression", fontsize=11)
    ax.tick_params(axis="x", rotation=35)
    ax.axhline(0, color="gray", ls="--", lw=0.8)
    if title == "Mural Cell":
        ax.set_ylabel("Expression level (scaled)")

fig.suptitle("ZNF532 expression across the Pan-tumor Vasculature Atlas (Pan et al. 2024, Nature 632:429-436)\n"
             "~200,000 cells, 372 donors, 31 cancer types — red boxes = BASP1+ matPC and its precursor (inter.matPC)",
             fontsize=11, y=1.06)
plt.tight_layout()
plt.savefig("panvc_znf532_boxplots.png", dpi=150, bbox_inches="tight")
print("saved")
