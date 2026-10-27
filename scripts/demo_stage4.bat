@echo off
rem Этап 4: обратные зависимости (тот же DFS по обратным рёбрам)
cd /d "%~dp0.."
set CONFIGS=reverse_simple reverse_cycle reverse_complex reverse_filter
set CONFIGS=%CONFIGS% reverse_missing reverse_leaf reverse_not_found
set CONFIGS=%CONFIGS% nuget_serilog
for %%f in (%CONFIGS%) do (
    echo.
    echo ===== configs\%%f.xml --reverse =====
    python src\main.py configs\%%f.xml --reverse
)
