@echo off
chcp 65001 >nul
echo ========================================================
echo   Lansare QGIS 3.40 - Inspectie StratumRO vs Cadastru
echo ========================================================
call "C:\Program Files\QGIS 3.40.0\bin\o4w_env.bat"
path %OSGEO4W_ROOT%\apps\qgis\bin;%PATH%
set QGIS_PREFIX_PATH=%OSGEO4W_ROOT:\=/%/apps/qgis
set GDAL_FILENAME_IS_UTF8=YES
set QT_PLUGIN_PATH=%OSGEO4W_ROOT%\apps\qgis\qtplugins;%OSGEO4W_ROOT%\apps\qt5\plugins

echo [+] Se deschide proiectul: %~dp0StratumRO_Inspectie_Vizuala.qgz
start "" "%OSGEO4W_ROOT%\bin\qgis-bin.exe" "%~dp0StratumRO_Inspectie_Vizuala.qgz"
