@echo off
REM StratumRO — OSGeo4W QGIS Detached Launcher (No /B flag)
call "C:\Program Files\QGIS 3.40.0\bin\o4w_env.bat"
if not exist "%OSGEO4W_ROOT%\apps\qgis\bin\qgisgrass8.dll" goto nograss
set savedpath=%PATH%
call "%OSGEO4W_ROOT%\apps\grass\grass84\etc\env.bat"
path %OSGEO4W_ROOT%\apps\grass\grass84\lib;%OSGEO4W_ROOT%\apps\grass\grass84\bin;%savedpath%
:nograss
@echo off
path %OSGEO4W_ROOT%\apps\qgis\bin;%PATH%
set QGIS_PREFIX_PATH=%OSGEO4W_ROOT:\=/%/apps/qgis
set GDAL_FILENAME_IS_UTF8=YES
set VSI_CACHE=TRUE
set VSI_CACHE_SIZE=1000000
set QT_PLUGIN_PATH=%OSGEO4W_ROOT%\apps\qgis\qtplugins;%OSGEO4W_ROOT%\apps\qt5\plugins

REM Launch detached independent window WITHOUT /B so process persists after console exits:
start "" "%OSGEO4W_ROOT%\bin\qgis-bin.exe" %*
