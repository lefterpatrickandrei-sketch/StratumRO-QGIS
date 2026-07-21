@echo off
:: Script de automatizare pentru compilare si instalare plugin StratumRO in QGIS
:: Rulati acest script din terminal sau prin dublu-click

set PLUGIN_NAME=stratum_ro
set QGIS_PLUGINS_DIR=%APPDATA%\QGIS\QGIS3\profiles\default\python\plugins

echo ===================================================
echo [StratumRO] Initiere compilare si instalare locala...
echo ===================================================

:: 1. Compilare resurse folosind pb_tool daca este disponibil
if exist pb_tool.cfg (
    echo [Resurse] Se compileaza resursele Qt...
    :: Incercam sa rulam pb_tool din venv
    .\venv\Scripts\pb_tool.exe compile 2>nul || pb_tool compile 2>nul || (
        echo [Avertisment] pb_tool nu a fost gasit in PATH. Incercam compilarea manuala pyrcc5...
        .\venv\Scripts\pyrcc5.exe -o resources.py resources.qrc 2>nul || pyrcc5 -o resources.py resources.qrc 2>nul || echo [Eroare] Nu s-a putut compila resources.qrc.
    )
)

:: 2. Creare director in QGIS daca nu exista
if not exist "%QGIS_PLUGINS_DIR%\%PLUGIN_NAME%" (
    echo [Director] Se creeaza folderul plugin-ului in QGIS...
    mkdir "%QGIS_PLUGINS_DIR%\%PLUGIN_NAME%"
)

:: 3. Copiere/Sincronizare fisere (excludem venv, .git, .agents, docs)
echo [Copiere] Se copiaza fisierele in directorul QGIS...
xcopy /s /y /e /exclude:exclude_list.txt "%~dp0stratum_ro" "%QGIS_PLUGINS_DIR%\%PLUGIN_NAME%"

echo ===================================================
echo [StratumRO] Sincronizare reusita! 
echo Reporniti QGIS sau folositi Plugin Reloader.
echo ===================================================
pause
