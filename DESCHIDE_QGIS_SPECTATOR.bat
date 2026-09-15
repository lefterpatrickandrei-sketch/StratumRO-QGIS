@echo off
chcp 65001 >nul
title StratumRO — Mod Spectator Live in QGIS 3.40
echo =========================================================================
echo   STRATUM-RO — Mod Spectator Live QGIS 3.40 (Stereo 70 / ANCPI)
echo =========================================================================
echo.
echo [+] Incarcare mediu OSGeo4W QGIS 3.40...
call "C:\Program Files\QGIS 3.40.0\bin\o4w_env.bat"

set PROJECT=%~dp0workspace\output\StratumRO_Rezultate.qgz
set SCRIPT=%~dp0tools\live_qgis_spectator.py

echo [+] Proiect: %PROJECT%
echo [+] Script de control live: %SCRIPT%
echo.
echo [+] Se deschide QGIS... Urmareste etapele pe ecran!
start "QGIS 3.40" "%OSGEO4W_ROOT%\bin\qgis-bin.exe" "%PROJECT%" --code "%SCRIPT%"
exit
