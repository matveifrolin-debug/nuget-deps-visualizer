@echo off
rem Этап 2: прямые зависимости пакетов из репозитория NuGet
cd /d "%~dp0.."
set CONFIGS=nuget_serilog nuget_v3_index nuget_newtonsoft_json
set CONFIGS=%CONFIGS% nuget_microsoft_extensions_logging
set CONFIGS=%CONFIGS% nuget_nosuchpackage12345 err_bad_url test_mode
for %%f in (%CONFIGS%) do (
    echo.
    echo ===== configs\%%f.xml =====
    python src\main.py configs\%%f.xml
)