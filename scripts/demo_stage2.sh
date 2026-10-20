#!/bin/sh
# Этап 2: прямые зависимости пакетов из репозитория NuGet
cd "$(dirname "$0")/.." || exit 1
for f in nuget_serilog nuget_v3_index nuget_newtonsoft_json \
         nuget_microsoft_extensions_logging nuget_nosuchpackage12345 \
         err_bad_url test_mode; do
    echo
    echo "===== configs/$f.xml ====="
    python src/main.py "configs/$f.xml"
done