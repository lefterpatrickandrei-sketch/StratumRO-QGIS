# StratumRO -- launch the OpenCode multi-agent UAT Giurgiu mission (version 9 workflow)
# Usage:
#   powershell -ExecutionPolicy Bypass -File scripts\launch_mission.ps1            # interactive TUI
#   powershell -ExecutionPolicy Bypass -File scripts\launch_mission.ps1 -DryRun    # checks only
#   powershell -ExecutionPolicy Bypass -File scripts\launch_mission.ps1 -Headless  # opencode run, no TUI
#
# What it does:
#   1. runs scripts\preflight.ps1 (G0 gate) and aborts on NO-GO
#   2. verifies the mission spec file and workspace tree exist
#   3. starts the read-only supervisor watchdog in a second window (D11, Mode A)
#   4. launches opencode with the ORCHESTRATOR agent and the mission spec attached
param(
  [string]$Repo  = "C:\Users\lefpa\Downloads\QGIS-AI",
  [string]$Spec  = "STRATUMRO_UAT_GIURGIU_MISSION_v9.md",
  [switch]$DryRun,
  [switch]$Headless,
  [switch]$NoSupervisor
)
$ErrorActionPreference = 'Continue'

Write-Output '=== StratumRO mission launcher ==='
Write-Output ('repo: ' + $Repo)

# 1. G0 pre-flight ----------------------------------------------------------
$pre = Join-Path $Repo 'scripts\preflight.ps1'
if (!(Test-Path $pre)) { Write-Output 'ABORT: scripts\preflight.ps1 missing'; exit 2 }
& powershell -ExecutionPolicy Bypass -File $pre
$preCode = $LASTEXITCODE
if ($preCode -eq 2) {
  Write-Output 'ABORT: pre-flight returned NO-GO (fix the FAIL lines above; see workspace\UAT_Giurgiu\reports\preflight_report.txt)'
  exit 2
}
if ($preCode -eq 1) { Write-Output 'WARNING: pre-flight has WARN entries - continuing, but record them in state.json alerts.' }

# 2. mission spec -----------------------------------------------------------
$specPath = Join-Path $Repo $Spec
if (!(Test-Path $specPath)) {
  Write-Output ('ABORT: mission spec not found: ' + $specPath)
  exit 2
}
$ws = Join-Path $Repo 'workspace\UAT_Giurgiu'
foreach ($d in 'state','data\raw','data\raster','data\reference','data\intermediate','data\output','qa','metadata','provenance','reports','logs') {
  $p = Join-Path $ws $d
  if (!(Test-Path $p)) { New-Item -ItemType Directory -Path $p -Force | Out-Null; Write-Output ('created: ' + $p) }
}
Write-Output ('mission spec: ' + $specPath)

if ($DryRun) {
  Write-Output ''
  Write-Output 'DRY RUN complete - nothing launched.'
  Write-Output 'Launch for real with:'
  Write-Output ('  powershell -ExecutionPolicy Bypass -File ' + (Join-Path $Repo 'scripts\launch_mission.ps1'))
  exit $preCode
}

# 3. supervisor watchdog (read-only, second window) --------------------------
if (-not $NoSupervisor) {
  $sup = Join-Path $Repo 'supervisor.ps1'
  if (Test-Path $sup) {
    $loop = 'while ($true) { & powershell -ExecutionPolicy Bypass -File ''' + $sup + '''; Start-Sleep 900 }'
    Start-Process powershell -ArgumentList ('-NoExit','-NoProfile','-ExecutionPolicy','Bypass','-Command',$loop) -WorkingDirectory $Repo
    Write-Output 'supervisor watchdog started in a separate window (15 min interval, read-only).'
  } else {
    Write-Output 'WARN: supervisor.ps1 not found - running without the watchdog.'
  }
}

# 4. launch opencode --------------------------------------------------------
$prompt = 'Execute the mission specification attached at ' + $Spec + ' (workflow version 9, gates G0..G7). ' +
          'You are AGENT 00 (orchestrator). Start at gate G0, persist workspace\UAT_Giurgiu\state\state.json after EVERY task, ' +
          'and follow the invariants I1-I7. Do not stop after planning, agent setup or discovery: continue autonomously through the gates ' +
          'until the product is complete or a documented hard blocker is reached. Never write to the protected assets listed in state\protected_assets.txt.'

if ($Headless) {
  Write-Output 'launching opencode (headless, orchestrator agent)...'
  & opencode run --agent stratumro-orchestrator --file $specPath --title 'UAT Giurgiu v9 production' $prompt
} else {
  Write-Output 'launching opencode (interactive TUI)...'
  Write-Output 'The default agent for this repo is stratumro-orchestrator (see .opencode/opencode.jsonc),'
  Write-Output 'so the orchestrator is already the active agent in the TUI.'
  Write-Output 'Useful inside the TUI: Tab = plan/act mode, /help = commands, Ctrl+C = stop.'
  $inline = $prompt + ' The full specification is on disk at ' + $specPath + ' - read it before acting.'
  & opencode --prompt $inline
}
exit $LASTEXITCODE
