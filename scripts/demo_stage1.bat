@echo off
rem Этап 1: вывод параметров и обработка ошибок конфигурации
cd /d "%~dp0.."
for %%f in (config test_mode err_bad_xml err_root err_missing err_values err_empty err_test_repo) do (
    echo.
    echo ===== configs\%%f.xml =====
    python src\main.py configs\%%f.xml
)
echo.
echo ===== configs\no_such_file.xml =====
python src\main.py configs\no_such_file.xml