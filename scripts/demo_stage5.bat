@echo off
rem Этап 5: Graphviz (DOT), SVG и ASCII-дерево
cd /d "%~dp0.."
set CONFIGS=viz_serilog viz_logging viz_polly viz_complex viz_missing
for %%f in (%CONFIGS%) do (
    echo.
    echo ===== configs\%%f.xml =====
    python src\main.py configs\%%f.xml
)
