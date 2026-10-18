@echo off
chcp 65001 > nul
echo ===================================================================
echo     LANSARE BROWSER NATIONAL QGIS — STRATUMRO DATE OFICIALE
echo ===================================================================
echo.
set "PROJECT_PATH=%~dp0ROMANIA_NATIONAL_OFICIAL_BROWSER.qgs"
if exist "C:\Program Files\QGIS 3.40.0\bin\qgis-bin.exe" (
    echo Deschid QGIS 3.40 cu proiectul National...
    start "" "C:\Program Files\QGIS 3.40.0\bin\qgis-bin.exe" "%PROJECT_PATH%"
) else (
    echo QGIS 3.40 nu a fost gasit in calea standard.
    pause
)
