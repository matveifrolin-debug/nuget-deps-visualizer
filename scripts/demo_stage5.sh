#!/bin/sh
# Этап 5: Graphviz (DOT), SVG и ASCII-дерево
cd "$(dirname "$0")/.." || exit 1
for f in viz_serilog viz_logging viz_polly viz_complex viz_missing; do
    echo
    echo "===== configs/$f.xml ====="
    python src/main.py "configs/$f.xml"
done
