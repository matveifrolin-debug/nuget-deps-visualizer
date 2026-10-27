#!/bin/sh
# Этап 4: обратные зависимости (тот же DFS по обратным рёбрам)
cd "$(dirname "$0")/.." || exit 1
for f in reverse_simple reverse_cycle reverse_complex reverse_filter \
         reverse_missing reverse_leaf reverse_not_found nuget_serilog; do
    echo
    echo "===== configs/$f.xml --reverse ====="
    python src/main.py "configs/$f.xml" --reverse
done
