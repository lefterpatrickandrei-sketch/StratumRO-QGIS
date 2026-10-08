param([string[]]$Models)

$envs = @{}
Get-Content .env -ErrorAction SilentlyContinue | ForEach-Object {
    if ($_ -match '^\s*([^#=]+)=(.*)$') { $envs[$matches[1].Trim()] = $matches[2].Trim() }
}

# Two 8x8 solid-colour PNGs: pure RED and pure BLUE.
# A text-only model cannot distinguish them. A vision model must.
$redB64  = "iVBORw0KGgoAAAANSUhEUgAAAAgAAAAICAYAAADED76LAAAAHElEQVQoz2P8//8/AzWBiYGaYFThqMJRhaMKAV4lBAX4lBbvAAAAAElFTkSuQmCC"
$blueB64 = "iVBORw0KGgoAAAANSUhEUgAAAAgAAAAICAYAAADED76LAAAAHElEQVQoz2P8z8Dwn4EIwDiqkL4hEBv4lBbvAAAAAElFTkSuQmCC"

function Ask($model, $b64) {
    $body = @{
        model    = $model
        messages = @(@{
            role    = "user"
            content = @(
                @{ type = "text";      text = "Name the dominant colour of this image. One word only." }
                @{ type = "image_url"; image_url = @{ url = "data:image/png;base64,$b64" } }
            )
        })
        max_tokens = 16
    } | ConvertTo-Json -Depth 12 -Compress

    $r = Invoke-RestMethod -Uri "https://openrouter.ai/api/v1/chat/completions" -Method Post `
        -Headers @{ Authorization = "Bearer $($envs['OPENROUTER_API_KEY'])" } -Body $body `
        -ContentType 'application/json' -TimeoutSec 30
    return ($r.choices[0].message.content -replace '\s+', ' ').Trim()
}

$results = @()
foreach ($m in $Models) {
    try {
        $sw = [Diagnostics.Stopwatch]::StartNew()
        $red  = Ask $m $redB64
        $blue = Ask $m $blueB64
        $sw.Stop()

        $redOK  = $red  -match '(?i)\bred\b|roșu|rosu'
        $blueOK = $blue -match '(?i)\bblue\b|albastru'
        $verdict = if ($redOK -and $blueOK)      { "VISION-REAL" }
                   elseif ($redOK -or $blueOK)   { "VISION-PARTIAL" }
                   else                          { "NO-VISION" }

        $results += [pscustomobject]@{
            Model  = $m
            Verdict = $verdict
            Ms     = $sw.ElapsedMilliseconds
            Red    = $red
            Blue   = $blue
        }
    }
    catch {
        $code = $_.Exception.Response.StatusCode.value__
        if (-not $code) { $code = "NET" }
        $results += [pscustomobject]@{ Model = $m; Verdict = "FAIL:$code"; Ms = 0; Red = ""; Blue = "" }
    }
}
$results | Format-Table -AutoSize | Out-String -Width 170