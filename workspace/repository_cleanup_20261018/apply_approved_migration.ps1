$ErrorActionPreference = 'Stop'
$auditDirectory = [System.IO.Path]::GetFullPath($PSScriptRoot)
$projectDirectory = [System.IO.Path]::GetFullPath((Join-Path $auditDirectory '..\..'))
$projectPrefix = $projectDirectory.TrimEnd('\') + '\'
$archivePrefix = (Join-Path $projectDirectory 'junk\2026-10-18').TrimEnd('\') + '\'
$manifest = Get-Content -LiteralPath (Join-Path $auditDirectory 'migration_manifest.json') -Raw | ConvertFrom-Json
$actions = @($manifest.files)
# The documentation directory also has an old duplicate README. Preserve it before
# replacing that directory's navigation, within the authorized documentation work.
$docsReadme = Join-Path $projectDirectory 'docs\README.md'
$actions += [pscustomobject]@{
    action = 'COPY_BEFORE_REPLACE'; source = 'docs/README.md'
    destination = 'junk/2026-10-18/source_snapshots/docs_README.original.md'
    sha256 = (Get-FileHash -LiteralPath $docsReadme -Algorithm SHA256).Hash.ToLowerInvariant()
    reason = 'Preserve the old documentation landing page before consolidating navigation.'
}
if (Test-Path -LiteralPath (Join-Path $auditDirectory 'migration_applied.json')) {
    throw 'This migration was already applied; inspect its completion record instead of rerunning.'
}
# Validate every final absolute path and every input before the first mutation.
foreach ($entry in $actions) {
    $sourcePath = [System.IO.Path]::GetFullPath((Join-Path $projectDirectory $entry.source))
    $archivePath = [System.IO.Path]::GetFullPath((Join-Path $projectDirectory $entry.destination))
    if (-not $sourcePath.StartsWith($projectPrefix, [System.StringComparison]::OrdinalIgnoreCase)) { throw 'Source outside project' }
    if (-not $archivePath.StartsWith($archivePrefix, [System.StringComparison]::OrdinalIgnoreCase)) { throw 'Destination outside approved archive' }
    if (-not (Test-Path -LiteralPath $sourcePath -PathType Leaf)) { throw "Missing input: $sourcePath" }
    if (Test-Path -LiteralPath $archivePath) { throw "Archive collision: $archivePath" }
    if ((Get-FileHash -LiteralPath $sourcePath -Algorithm SHA256).Hash.ToLowerInvariant() -ne $entry.sha256) { throw "Input changed since approval: $sourcePath" }
}
foreach ($entry in $actions) {
    $sourcePath = [System.IO.Path]::GetFullPath((Join-Path $projectDirectory $entry.source))
    $archivePath = [System.IO.Path]::GetFullPath((Join-Path $projectDirectory $entry.destination))
    [System.IO.Directory]::CreateDirectory([System.IO.Path]::GetDirectoryName($archivePath)) | Out-Null
    if ($entry.action -eq 'MOVE') { Move-Item -LiteralPath $sourcePath -Destination $archivePath }
    elseif ($entry.action -eq 'COPY_BEFORE_REPLACE') { Copy-Item -LiteralPath $sourcePath -Destination $archivePath }
    else { throw "Unknown action: $($entry.action)" }
    if ((Get-FileHash -LiteralPath $archivePath -Algorithm SHA256).Hash.ToLowerInvariant() -ne $entry.sha256) { throw "Archive hash mismatch: $archivePath" }
}
$record = [ordered]@{
    completed_utc = [DateTime]::UtcNow.ToString('o')
    status = 'APPLIED_HASH_VERIFIED'
    moves = @($actions | Where-Object action -eq 'MOVE').Count
    snapshots = @($actions | Where-Object action -eq 'COPY_BEFORE_REPLACE').Count
    files = $actions
    deletion = 'No content discarded; original paths of MOVE entries now resolve through the migration table.'
}
$recordJson = $record | ConvertTo-Json -Depth 8
[System.IO.File]::WriteAllText((Join-Path $auditDirectory 'migration_applied.json'), $recordJson + "`n", [System.Text.UTF8Encoding]::new($false))
Write-Output "Applied $($record.moves) approved moves and preserved $($record.snapshots) original document snapshots."
