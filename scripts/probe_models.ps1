param([string]$Provider = "openrouter", [string[]]$Models)

$envs = @{}
Get-Content .env -ErrorAction SilentlyContinue | ForEach-Object {
    if ($_ -match '^\s*([^#=]+)=(.*)$') { $envs[$matches[1].Trim()] = $matches[2].Trim() }
}

$urls = @{
    "openrouter" = @{
        url  = "https://openrouter.ai/api/v1/chat/completions"
        hdr  = @{ Authorization = "Bearer $($envs['OPENROUTER_API_KEY'])" }
    }
    "nvidia" = @{
        url  = "https://integrate.api.nvidia.com/v1/chat/completions"
        hdr  = @{ Authorization = "Bearer $($envs['NVIDIA_API_KEY'])" }
    }
}

$results = @()
foreach ($m in $Models) {
    $sw = [Diagnostics.Stopwatch]::StartNew()
    try {
        $body = @{
            model    = $m
            messages = @(@{ role = "user"; content = "reply with the single word OK" })
            max_tokens = 16
        } | ConvertTo-Json -Depth 8 -Compress
        $r = Invoke-RestMethod -Uri $urls[$Provider].url -Method Post `
            -Headers $urls[$Provider].hdr -Body $body `
            -ContentType 'application/json' -TimeoutSec 20
        $sw.Stop()
        $txt = $r.choices[0].message.content -replace '\s+', ' '
        if ($txt.Length -gt 20) { $txt = $txt.Substring(0, 20) }
        $results += [pscustomobject]@{ Model = $m; Status = "OK"; Ms = $sw.ElapsedMilliseconds; Reply = $txt }
    }
    catch {
        $sw.Stop()
        $code = $_.Exception.Response.StatusCode.value__
        if (-not $code) { $code = "NET" }
        $results += [pscustomobject]@{ Model = $m; Status = "FAIL:$code"; Ms = $sw.ElapsedMilliseconds; Reply = "" }
    }
}
$results | Sort-Object Status, Ms | Format-Table -AutoSize | Out-String -Width 160