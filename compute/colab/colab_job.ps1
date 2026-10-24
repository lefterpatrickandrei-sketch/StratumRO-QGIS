<#
.SYNOPSIS
  Run a StratumRO Colab job card from Windows via WSL2 + google-colab-cli.

.DESCRIPTION
  -DryRun   validates the card and prints the plan. Runs nothing, uploads nothing.
  -Confirm  required for a real run (spends Colab compute units and uploads data).
  Without either switch the script behaves like -DryRun.

  A real run needs WSL2 with `colab` installed (see compute/colab/README.md).
  Results are proposals and land in workspace/colab_runs/<job>/<UTC timestamp>/.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$Job,
    [switch]$DryRun,
    [switch]$Confirm
)

$ErrorActionPreference = 'Stop'
function Fail([string]$Message, [int]$Code) { [Console]::Error.WriteLine("ERROR: $Message"); exit $Code }
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$python = Join-Path $repo 'venv\Scripts\python.exe'
if (-not (Test-Path $python)) { $python = 'python' }

# 1. Validate the card (pure Python, no network).
& $python (Join-Path $PSScriptRoot 'job_plan.py') $Job
if ($LASTEXITCODE -ne 0) { Fail "Job card '$Job' is invalid." 1 }

if ($DryRun -or -not $Confirm) {
    Write-Host "`nDry run only. Nothing started, nothing uploaded. Add -Confirm for a real run."
    exit 0
}

# 2. A real run needs WSL2.
$wslOk = $false
try {
    $null = & wsl.exe --status 2>&1
    $wslOk = ($LASTEXITCODE -eq 0)
} catch { $wslOk = $false }
if (-not $wslOk) {
    Fail "WSL2 is not available. google-colab-cli is Linux/macOS only. Install it first: wsl.exe --install -d Ubuntu (admin shell + reboot). See compute/colab/README.md." 2
}

$card = & $python (Join-Path $PSScriptRoot 'job_plan.py') $Job --json | ConvertFrom-Json
if ($card.status -ne 'scaffolded') {
    Fail "Job '$Job' is '$($card.status)': there is no script to run yet." 3
}

$stamp = (Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssZ')
$outDir = Join-Path $repo "workspace\colab_runs\$Job\$stamp"
New-Item -ItemType Directory -Force $outDir | Out-Null
$sha = (git -C $repo rev-parse HEAD).Trim()

$wslRepo = (& wsl.exe wslpath -a $repo).Trim()
$wslOut = (& wsl.exe wslpath -a $outDir).Trim()
& wsl.exe bash "$wslRepo/compute/colab/colab_job.sh" $Job $card.gpu $card.script $card.time_limit_minutes $wslOut $sha
exit $LASTEXITCODE
