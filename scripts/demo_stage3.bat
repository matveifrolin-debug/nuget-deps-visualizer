@echo off
rem Этап 3: граф зависимостей (DFS без рекурсии, фильтр, циклы)
cd /d "%~dp0.."
set CONFIGS=graph_simple graph_cycle graph_self_loop graph_complex
set CONFIGS=%CONFIGS% graph_filter graph_missing graph_root_filtered
set CONFIGS=%CONFIGS% nuget_graph_serilog nuget_graph_logging_filter
for %%f in (%CONFIGS%) do (
    echo.
    echo ===== configs\%%f.xml =====
    python src\main.py configs\%%f.xml
)