"""
Query the Enrichr API for TF-target enrichment of the 5 ARGscore genes
(VSIG4, CXCL10, CXCL13, MEIS2, ZNF532) against curated TF-target libraries
(TRRUST, ChEA, ENCODE ChIP-seq, TF perturbation-followed-by-expression),
to generate candidate upstream-regulator hypotheses.
"""
import requests
import json
import time
import os

OUT = os.path.join(os.path.dirname(__file__), "..", "data", "enrichr")
os.makedirs(OUT, exist_ok=True)

genes = "VSIG4\nCXCL10\nCXCL13\nMEIS2\nZNF532"
r = requests.post("https://maayanlab.cloud/Enrichr/addList",
                   files={'list': (None, genes), 'description': (None, 'ARGscore5')})
uid = r.json()["userListId"]
print("userListId", uid)

libraries = ["TRRUST_Transcription_Factors_2019", "ChEA_2022", "ENCODE_TF_ChIP-seq_2015",
             "TF_Perturbations_Followed_by_Expression"]

for lib in libraries:
    time.sleep(1)
    resp = requests.get("https://maayanlab.cloud/Enrichr/enrich",
                         params={"userListId": uid, "backgroundType": lib})
    data = resp.json()
    with open(os.path.join(OUT, f"enrich_5genes_{lib}.json"), "w") as f:
        json.dump(data, f)
    n = len(data.get(lib, []))
    print(lib, "-> ", n, "terms")

for lib in libraries:
    with open(os.path.join(OUT, f"enrich_5genes_{lib}.json")) as f:
        data = json.load(f)[lib]
    print(f"\n=== {lib} (top 10 by adj-p) ===")
    rows = sorted(data, key=lambda x: x[6])[:10]
    for row in rows:
        rank, term, pval, zscore, comb, genes_hit, adjp = row[:7]
        print(f"  {term:45s} p={pval:.2e} adjp={adjp:.3f} genes={genes_hit}")
