#!/bin/sh
# Этап 1: вывод параметров и обработка ошибок конфигурации
cd "$(dirname "$0")/.." || exit 1
for f in config test_mode err_bad_xml err_root err_missing err_values \
         err_empty err_test_repo no_such_file; do
    echo
    echo "===== configs/$f.xml ====="
    python src/main.py "configs/$f.xml"
done