param(
    [int]$Limit = 0,
    [int]$Workers = 4,
    [switch]$Force
)
$ErrorActionPreference = "Stop"
Set-Location "C:\Users\lefpa\Downloads\QGIS-AI"
$py = "venv\Scripts\python.exe"
$args = @("tools\vlm_real_audit.py", "--workers", $Workers)
if ($Limit -gt 0) { $args += @("--limit", $Limit) }
if ($Force) { $args += "--force" }
& $py @args 2>&1 | Tee-Object -FilePath "workspace\output\vlm_audit_run.log"
exit $LASTEXITCODE