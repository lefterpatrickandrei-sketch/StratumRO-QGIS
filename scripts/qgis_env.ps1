# StratumRO -- valid PyQGIS / GDAL runtime for QGIS 3.40.0 (x64) on Windows 11
# Purpose: run scripts that need `from qgis.core import ...` or the GDAL/OGR toolchain.
# Mirrors OSGeo4W's o4w_env.bat (PATH / PYTHONHOME / GDAL + PROJ data) so that
# `import qgis.core` resolves the compiled _core DLLs.
#
# Usage (dot-source so the env vars persist in the current shell):
#   . C:\Users\lefpa\Downloads\QGIS-AI\scripts\qgis_env.ps1
#   python-qgis -c "from qgis.core import Qgis; print(Qgis.QGIS_VERSION)"
#   ogr2ogr --version
[CmdletBinding()]
param(
  [string]$QgsRoot = "C:\Program Files\QGIS 3.40.0",
  [switch]$Quiet
)
# NOTE: intentionally 'Continue' -- this script is meant to be DOT-SOURCED, and a
# 'Stop' preference would leak into the caller's scope and turn native-command
# stderr into terminating errors.
$ErrorActionPreference = 'Continue'

$qb = Join-Path $QgsRoot 'bin'
if (!(Test-Path (Join-Path $qb 'qgis-bin.exe'))) {
  Write-Error ("QGIS not found at " + $QgsRoot + " -- adjust -QgsRoot")
}

$env:QGIS_PREFIX_PATH = (Join-Path $QgsRoot 'apps\qgis')
$env:PYTHONHOME        = (Join-Path $QgsRoot 'apps\Python312')
$env:GDAL_DATA         = (Join-Path $QgsRoot 'share\gdal')
$env:PROJ_LIB          = (Join-Path $QgsRoot 'share\proj')
$env:PROJ_DATA         = (Join-Path $QgsRoot 'share\proj')
$env:GEOTIFF_CSV       = (Join-Path $QgsRoot 'share\epsg_csv')
$env:QT_PLUGIN_PATH    = (Join-Path $QgsRoot 'apps\Qt5\plugins')

# PyQGIS needs the QGIS python dir on the module path (o4w_env does this too)
$env:PYTHONPATH = (Join-Path $env:QGIS_PREFIX_PATH 'python')

# prepend OSGeo4W/QGIS tool directories to PATH (Qt first: _core needs its DLLs)
$paths = @(
  (Join-Path $QgsRoot 'apps\qgis\bin'),
  (Join-Path $QgsRoot 'apps\Qt5\bin'),
  $qb,
  (Join-Path $QgsRoot 'apps\Python312\Scripts'),
  (Join-Path $QgsRoot 'apps\Python312'),
  (Join-Path $QgsRoot 'apps\gdal\bin'),
  (Join-Path $QgsRoot 'apps\proj\bin')
)
foreach ($p in $paths) { if (Test-Path $p) { $env:PATH = $p + ';' + $env:PATH } }

if (-not $Quiet) {
  Write-Output 'StratumRO QGIS runtime ready:'
  Write-Output ('  QGIS_PREFIX_PATH = ' + $env:QGIS_PREFIX_PATH)
  Write-Output ('  PYTHONHOME       = ' + $env:PYTHONHOME)
  Write-Output ('  GDAL_DATA        = ' + $env:GDAL_DATA)
  Write-Output ('  PROJ_LIB         = ' + $env:PROJ_LIB)
  Write-Output 'Verify with:  python-qgis -c "from qgis.core import Qgis; print(Qgis.QGIS_VERSION)"'
  Write-Output '              ogr2ogr --version'
}
