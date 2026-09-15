@echo off
chcp 65001 >nul
echo =========================================================================
echo   StratumRO — Lansare Mod Spectator Live in QGIS 3.40
echo =========================================================================

call "C:\Program Files\QGIS 3.40.0\bin\o4w_env.bat"
path %OSGEO4W_ROOT%\apps\qgis\bin;%PATH%
set QGIS_PREFIX_PATH=%OSGEO4W_ROOT:\=/%/apps/qgis
set GDAL_FILENAME_IS_UTF8=YES
set QT_PLUGIN_PATH=%OSGEO4W_ROOT%\apps\qgis\qtplugins;%OSGEO4W_ROOT%\apps\qt5\plugins

set PROJECT_PATH=%~dp0workspace\output\StratumRO_Rezultate.qgz
if not exist "%PROJECT_PATH%" (
    set PROJECT_PATH=%~dp0StratumRO_Inspectie_Vizuala.qgz
)

set SCRIPT_PATH=%~dp0tools\live_qgis_spectator.py

echo [+] Proiect incarcat: %PROJECT_PATH%
echo [+] Script de animatie si control: %SCRIPT_PATH%
echo [+] Se deschide QGIS... Te poti aseza comod sa urmaresti fiecare etapa live!

start "" "%OSGEO4W_ROOT%\bin\qgis-bin.exe" --project "%PROJECT_PATH%" --code "%SCRIPT_PATH%"
