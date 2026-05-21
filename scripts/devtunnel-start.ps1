$ErrorActionPreference = 'Stop'

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$tunnelIdFile = Join-Path $repoRoot '.devtunnel-id'

if (-not (Test-Path -Path $tunnelIdFile)) {
    throw ".devtunnel-id was not found at $tunnelIdFile. Run scripts/devtunnel-setup.ps1 first."
}

$tunnelId = (Get-Content -Path $tunnelIdFile -Raw).Trim()
if ([string]::IsNullOrWhiteSpace($tunnelId)) {
    throw ".devtunnel-id is empty. Run scripts/devtunnel-setup.ps1 again."
}

Write-Host "Starting DevTunnel host for tunnel ID: $tunnelId"
& devtunnel host $tunnelId
exit $LASTEXITCODE
