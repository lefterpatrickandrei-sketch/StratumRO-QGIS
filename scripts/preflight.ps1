# StratumRO -- G0 pre-flight (Windows PowerShell 5.1 compatible, ASCII only)
# Checks everything the v9 workflow requires BEFORE `opencode` starts the mission.
# Usage: powershell -ExecutionPolicy Bypass -File scripts\preflight.ps1
# Exit codes: 0 = GO, 1 = GO with WARN, 2 = NO-GO (hard blocker)
param(
  [string]$Repo = "C:\Users\lefpa\Downloads\QGIS-AI"
)
$ErrorActionPreference = 'Continue'
$ws = Join-Path $Repo "workspace\UAT_Giurgiu"
$script:level = 0
$script:lines = @()

function Say([int]$l, [string]$m) {
  if ($l -gt $script:level) { $script:level = $l }
  $tag = 'OK   '
  if ($l -eq 1) { $tag = 'WARN ' }
  if ($l -eq 2) { $tag = 'FAIL ' }
  $script:lines += ($tag + $m)
}

Say 0 '=== StratumRO G0 PRE-FLIGHT ==='
Say 0 ('repo: ' + $Repo)

# --- 1. repo + baseline -----------------------------------------------------
if (Test-Path (Join-Path $Repo '.git')) { Say 0 'git repo present' } else { Say 2 'git repo missing' }
$branch = (& git -C $Repo branch --show-current 2>&1 | Out-String).Trim()
Say 0 ('git branch: ' + $branch)
$dirty = (& git -C $Repo status --short 2>&1 | Measure-Object -Line).Lines
Say 0 ('git dirty entries: ' + $dirty + '  (DIRTY STATE IS BASELINE)')

# --- 2. API keys (presence only, never printed) -----------------------------
function Has-Key([string]$key, [string]$altKey) {
  $v = [Environment]::GetEnvironmentVariable($key)
  if (-not [string]::IsNullOrEmpty($v)) { return 'env' }
  if ($altKey) {
    $v = [Environment]::GetEnvironmentVariable($altKey)
    if (-not [string]::IsNullOrEmpty($v)) { return 'env(' + $altKey + ')' }
  }
  $envFile = Join-Path $Repo '.env'
  if (Test-Path $envFile) {
    $pat = ('^' + [regex]::Escape($key) + '\s*=')
    $line = Get-Content $envFile | Where-Object { $_ -match $pat } | Select-Object -First 1
    if (-not $line -and $altKey) {
      $line = Get-Content $envFile | Where-Object { $_ -match ('^' + [regex]::Escape($altKey) + '\s*=') } | Select-Object -First 1
    }
    if ($line) { return '.env' }
  }
  return $null
}
$nim = Has-Key 'NVIDIA_NIM_API_KEY' 'NVIDIA_API_KEY'
$or  = Has-Key 'OPENROUTER_API_KEY' $null
if ($nim) { Say 0 ('NVIDIA NIM key: PRESENT (' + $nim + ')') } else { Say 2 'NVIDIA NIM key: MISSING' }
if ($or)  { Say 0 ('OpenRouter key: PRESENT (' + $or + ')') }  else { Say 2 'OpenRouter key: MISSING' }

# --- 3. protected assets (I2) ----------------------------------------------
$listFile = Join-Path $ws 'state\protected_assets.txt'
if (Test-Path $listFile) {
  $entries = @(Get-Content $listFile | Where-Object { $_ -and $_.Trim() -ne '' -and $_ -notmatch '^\s*#' })
  $bad = 0
  foreach ($e in $entries) {
    $exp = $null
    $path = $e
    if ($e -match '^sha256:([0-9a-f]{64})\s+(.+)$') { $exp = $Matches[1]; $path = $Matches[2].Trim() }
    if (Test-Path $path) {
      $act = ((certutil -hashfile $path SHA256 | Select-Object -Index 1) -replace '\s', '')
      if ($exp -and ($act -ne $exp)) { $bad++; Say 2 ('PROTECTED MODIFIED: ' + $path) }
    }
  }
  if ($bad -eq 0) { Say 0 ('protected assets verified: ' + $entries.Count + ' unchanged') }
} else {
  Say 2 'protected_assets.txt missing - G0 cannot record the I2 baseline'
}

# --- 4. state contract -----------------------------------------------------
$state = Join-Path $ws 'state\state.json'
if (Test-Path $state) {
  try {
    $s = Get-Content $state -Raw | ConvertFrom-Json
    foreach ($f in 'gate','gate_since','updated_at','alerts') {
      if ($null -eq $s.$f) { Say 1 ('state.json missing field: ' + $f) }
    }
    Say 0 ('state.json OK (gate=' + $s.gate + ', alerts=' + (@($s.alerts).Count) + ')')
  } catch { Say 2 ('state.json invalid JSON: ' + $_.Exception.Message) }
} else { Say 2 'state.json missing' }

# --- 5. QGIS + GDAL runtime ------------------------------------------------
$qgs = 'C:\Program Files\QGIS 3.40.0'
if (Test-Path (Join-Path $qgs 'bin\qgis-bin.exe')) { Say 0 'QGIS desktop present (3.40.0)' } else { Say 2 ('QGIS not found at ' + $qgs) }
$envScript = Join-Path $Repo 'scripts\qgis_env.ps1'
if (Test-Path $envScript) {
  . $envScript -Quiet
  $gdal = (& ogr2ogr --version 2>&1 | Out-String).Trim()
  if ($gdal -match 'GDAL') { Say 0 ('GDAL runtime: ' + $gdal) } else { Say 1 'GDAL runtime not resolvable' }
  $py = Join-Path $qgs 'apps\Python312\python.exe'
  if (Test-Path $py) { Say 0 'PyQGIS interpreter present (apps\Python312)' } else { Say 2 'PyQGIS interpreter missing' }
} else { Say 2 'scripts\qgis_env.ps1 missing' }

# --- 6. opencode config ----------------------------------------------------
$cfg = Join-Path $Repo '.opencode\opencode.jsonc'
if (Test-Path $cfg) {
  $txt = Get-Content $cfg -Raw
  $agentCount = ([regex]::Matches($txt, '"mode":\s*"subagent"')).Count
  Say 0 ('.opencode/opencode.jsonc present (' + $agentCount + ' subagents)')
  if ($txt -match 'sk-or-|nvapi-|sk-ant-|sk-proj-|ssh-rsa') { Say 2 'SECRET LEAK detected in opencode.jsonc' } else { Say 0 'no secrets in opencode.jsonc' }
} else { Say 2 'opencode.jsonc missing' }
$ocVer = (& opencode --version 2>&1 | Out-String).Trim()
if ($ocVer -match 'opencode') { Say 0 ('opencode CLI: ' + $ocVer) } else { Say 2 'opencode CLI not resolved' }
# NOTE: `opencode debug agents` has no directory argument -- it resolves
# .opencode/opencode.jsonc relative to the current working directory.
Push-Location $Repo
try {
  $agents = (& opencode debug agents 2>&1 | Out-String)
} finally {
  Pop-Location
}
foreach ($a in 'stratumro-orchestrator','stratumro-architect','stratumro-coder','stratumro-geospatial','stratumro-qgis','stratumro-researcher','stratumro-reviewer') {
  if ($agents -match [regex]::Escape($a)) { Say 0 ('agent registered: ' + $a) } else { Say 2 ('agent NOT registered: ' + $a) }
}

# --- 7. supervisor ---------------------------------------------------------
$sup = Join-Path $Repo 'supervisor.ps1'
if (Test-Path $sup) {
  $supOut = (& powershell -ExecutionPolicy Bypass -File $sup 2>&1 | Out-String).Trim()
  $code = $LASTEXITCODE
  if ($code -eq 0) { Say 0 'supervisor: OK (exit 0)' } else { Say 1 ('supervisor exit ' + $code + ': ' + $supOut) }
} else { Say 2 'supervisor.ps1 missing' }

# --- 8. disk + GPU ---------------------------------------------------------
$freeGB = [long]((Get-PSDrive ((Get-Item $Repo).PSDrive.Name)).Free / 1GB)
if ($freeGB -ge 5) { Say 0 ('disk free: ' + $freeGB + ' GB') } else { Say 2 ('disk free too low: ' + $freeGB + ' GB') }
$smi = (& nvidia-smi --query-gpu=name,memory.total --format=csv,noheader 2>&1 | Out-String).Trim()
if ($smi -match 'MiB') { Say 0 ('GPU: ' + $smi + ' (SAM2 verdict decided at G1)') } else { Say 1 'nvidia-smi unavailable - SAM2 likely DISABLED_FALLBACK' }

# --- report ----------------------------------------------------------------
$verdict = @('GO','GO (with WARN)','NO-GO')[$script:level]
$out = @()
$out += ''
$out += ('=== RESULT: ' + $verdict + ' ===')
$out += ''
$all = $script:lines + $out
$all | ForEach-Object { Write-Output $_ }
$reportDir = Join-Path $ws 'reports'
if (!(Test-Path $reportDir)) { New-Item -ItemType Directory -Path $reportDir -Force | Out-Null }
$outFile = Join-Path $reportDir 'preflight_report.txt'
$all | Set-Content -Path $outFile -Encoding utf8
Write-Output ('report written: ' + $outFile)
exit $script:level

