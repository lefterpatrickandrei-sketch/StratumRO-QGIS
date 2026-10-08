param([string[]]$Models)

$envs = @{}
Get-Content .env -ErrorAction SilentlyContinue | ForEach-Object {
    if ($_ -match '^\s*([^#=]+)=(.*)$') { $envs[$matches[1].Trim()] = $matches[2].Trim() }
}

# 1x1 red PNG - minimal valid image
$b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="

$results = @()
foreach ($m in $Models) {
    $sw = [Diagnostics.Stopwatch]::StartNew()
    try {
        $body = @{
            model    = $m
            messages = @(@{
                role    = "user"
                content = @(
                    @{ type = "text";      text = "What single colour is this image? Answer one word." }
                    @{ type = "image_url"; image_url = @{ url = "data:image/png;base64,$b64" } }
                )
            })
            max_tokens = 24
        } | ConvertTo-Json -Depth 12 -Compress

        $r = Invoke-RestMethod -Uri "https://openrouter.ai/api/v1/chat/completions" -Method Post `
            -Headers @{ Authorization = "Bearer $($envs['OPENROUTER_API_KEY'])" } -Body $body `
            -ContentType 'application/json' -TimeoutSec 30
        $sw.Stop()
        $txt = ($r.choices[0].message.content -replace '\s+', ' ')
        if ($txt.Length -gt 40) { $txt = $txt.Substring(0, 40) }
        $vision = if ($txt -match '(?i)red|rosu|roșu|crimson') { "VISION-OK" }
                  elseif ($txt -match '(?i)black|negru') { "VISION-OK" }
                  else { "VISION-UNCLEAR" }
        $results += [pscustomobject]@{ Model = $m; Status = $vision; Ms = $sw.ElapsedMilliseconds; Reply = $txt }
    }
    catch {
        $sw.Stop()
        $code = $_.Exception.Response.StatusCode.value__
        if (-not $code) { $code = "NET" }
        $results += [pscustomobject]@{ Model = $m; Status = "FAIL:$code"; Ms = $sw.ElapsedMilliseconds; Reply = "" }
    }
}
$results | Format-Table -AutoSize | Out-String -Width 170