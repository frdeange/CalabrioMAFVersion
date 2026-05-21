param(
    [int]$Port = 8000
)

$ErrorActionPreference = 'Stop'

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$tunnelIdFile = Join-Path $repoRoot '.devtunnel-id'

Write-Host "Creating DevTunnel with anonymous access enabled..."
$createOutput = (& devtunnel create --allow-anonymous 2>&1 | Out-String)
if ($LASTEXITCODE -ne 0) {
    throw "Failed to create DevTunnel.`n$createOutput"
}

$tunnelIdMatch = [regex]::Match($createOutput, 'Tunnel ID\s*:\s*(?<id>[A-Za-z0-9-]+)')
if (-not $tunnelIdMatch.Success) {
    throw "Could not parse tunnel ID from devtunnel output.`n$createOutput"
}

$tunnelId = $tunnelIdMatch.Groups['id'].Value
Set-Content -Path $tunnelIdFile -Value $tunnelId -NoNewline -Encoding utf8
Write-Host "Saved tunnel ID to $tunnelIdFile"

Write-Host "Configuring tunnel port $Port..."
$portOutput = (& devtunnel port create $tunnelId --port-number $Port 2>&1 | Out-String)
if ($LASTEXITCODE -ne 0) {
    throw "Failed to configure tunnel port.`n$portOutput"
}

$tunnelUrl = $null
$showOutput = (& devtunnel show $tunnelId 2>&1 | Out-String)
if ($LASTEXITCODE -eq 0) {
    $urlMatch = [regex]::Match($showOutput, 'https://[^\s]+')
    if ($urlMatch.Success) {
        $tunnelUrl = $urlMatch.Value
    }
}
if (-not $tunnelUrl) {
    $tunnelUrl = "https://$tunnelId-$Port.devtunnels.ms"
}

Write-Host ""
Write-Host "DevTunnel setup complete."
Write-Host "Tunnel ID  : $tunnelId"
Write-Host "Tunnel URL : $tunnelUrl"
Write-Host ""
Write-Host "Copy 'Tunnel URL' to APIM Named Value 'backend-url'."
