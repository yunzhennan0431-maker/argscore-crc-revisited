#!/bin/bash
set -e
PROJECT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
WORKDIR="$PROJECT_ROOT/scratch/gse236581"
cd "$WORKDIR"

GENE_ROWS=$(cut -f1 target_gene_indices.tsv | tr '\n' ' ')

echo "Filtering counts.mtx.gz for target gene rows via awk (this streams through the full file once)..."
time gunzip -c counts.mtx.gz | awk -v rows="$GENE_ROWS" '
BEGIN {
    n = split(rows, arr, " ");
    for (i = 1; i <= n; i++) target[arr[i]] = 1;
}
NR <= 3 { next }
{
    if ($1 in target) print $1, $2, $3;
}
' > filtered_gene_rows.txt

echo "done, filtered line count:"
wc -l filtered_gene_rows.txt
