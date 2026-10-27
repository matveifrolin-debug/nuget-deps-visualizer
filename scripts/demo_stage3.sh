#!/bin/sh
# Этап 3: граф зависимостей (DFS без рекурсии, фильтр, циклы)
cd "$(dirname "$0")/.." || exit 1
for f in graph_simple graph_cycle graph_self_loop graph_complex \
         graph_filter graph_missing graph_root_filtered \
         nuget_graph_serilog nuget_graph_logging_filter; do
    echo
    echo "===== configs/$f.xml ====="
    python src/main.py "configs/$f.xml"
done