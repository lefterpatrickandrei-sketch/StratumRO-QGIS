param([string[]]$Models)

$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.Drawing

$envs = @{}
Get-Content .env | ForEach-Object {
    if ($_ -match '^\s*([^#=]+)=(.*)$') { $envs[$matches[1].Trim()] = $matches[2].Trim() }
}

# Build genuinely solid-colour PNGs in memory. A text-only model cannot
# tell these apart; a vision model must name the correct colour each time.
function New-SolidPng([int]$r, [int]$g, [int]$b) {
    $bmp = New-Object System.Drawing.Bitmap 32, 32
    for ($y = 0; $y -lt 32; $y++) {
        for ($x = 0; $x -lt 32; $x++) {
            $bmp.SetPixel($x, $y, [System.Drawing.Color]::FromArgb(255, $r, $g, $b))
        }
    }
    $ms = New-Object IO.MemoryStream
    $bmp.Save($ms, [System.Drawing.Imaging.ImageFormat]::Png)
    $b64 = [Convert]::ToBase64String($ms.ToArray())
    $bmp.Dispose(); $ms.Dispose()
    return $b64
}

$redB64  = New-SolidPng 255 0 0
$greenB64 = New-SolidPng 0 255 0

function Ask($model, $b64, $question) {
    $body = @{
        model    = $model
        messages = @(@{
            role    = "user"
            content = @(
                @{ type = "text";      text = $question }
                @{ type = "image_url"; image_url = @{ url = "data:image/png;base64,$b64" } }
            )
        })
        max_tokens = 20
    } | ConvertTo-Json -Depth 12 -Compress

    $r = Invoke-RestMethod -Uri "https://openrouter.ai/api/v1/chat/completions" -Method Post `
        -Headers @{ Authorization = "Bearer $($envs['OPENROUTER_API_KEY'])" } -Body $body `
        -ContentType 'application/json' -TimeoutSec 30
    return ($r.choices[0].message.content -replace '\s+', ' ').Trim()
}

$q = "Name the dominant colour of this image. One word only."
$results = @()

foreach ($m in $Models) {
    try {
        $sw = [Diagnostics.Stopwatch]::StartNew()
        $red   = Ask $m $redB64   $q
        $green = Ask $m $greenB64 $q
        $sw.Stop()

        $rOK = $red   -match '(?i)\bred\b|crimson|scarlet'
        $gOK = $green -match '(?i)\bgreen\b|verde'

        $verdict = if ($rOK -and $gOK)   { "VISION-REAL" }
                   elseif ($rOK -or $gOK) { "VISION-PARTIAL" }
                   else                   { "NO-VISION" }

        $results += [pscustomobject]@{
            Model = $m; Verdict = $verdict; Ms = $sw.ElapsedMilliseconds
            Red = $red; Green = $green
        }
    }
    catch {
        $code = $_.Exception.Response.StatusCode.value__
        if (-not $code) { $code = "NET" }
        $results += [pscustomobject]@{ Model = $m; Verdict = "FAIL:$code"; Ms = 0; Red = ""; Green = "" }
    }
}

$results | Format-Table -AutoSize | Out-String -Width 170