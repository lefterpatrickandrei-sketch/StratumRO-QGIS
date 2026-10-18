# Launch QGIS 3.40 Desktop with StratumRO Inspection Project
$qgisBat = "C:\Program Files\QGIS 3.40.0\bin\qgis.bat"
$project = "C:\Users\lefpa\Downloads\QGIS-AI\StratumRO_Inspectie_Vizuala.qgz"
if (!(Test-Path $project)) {
    $project = "C:\Users\lefpa\Downloads\QGIS-AI\workspace\output\StratumRO_Rezultate.qgz"
}

Write-Host "[+] Launching QGIS 3.40 Desktop with project: $project"
$p = Start-Process -FilePath $qgisBat -ArgumentList "`"$project`"" -PassThru
Write-Host "[+] Process started. PID: $($p.Id)"
Start-Sleep -Seconds 3
Get-Process | Where-Object { $_.ProcessName -match "qgis" } | Format-Table Id, ProcessName, MainWindowTitle, WorkingSet64
