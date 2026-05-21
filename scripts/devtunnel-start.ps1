param(
    [string]$TunnelName = "calabrio-dev"
)

<#
Starts hosting a previously created DevTunnel.
Usage: .\scripts\devtunnel-start.ps1 [-TunnelName "calabrio-dev"]
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Get-TunnelUrl {
    param([string]$Name)
    $showOutput = devtunnel show $Name 2>&1 | Out-String
    $match = [regex]::Match($showOutput, 'https://[a-zA-Z0-9\-]+\.devtunnels\.ms')
    if ($match.Success) {
        return $match.Value
    }

    return ""
}

Write-Host "=== DevTunnel host ===" -ForegroundColor Cyan
Write-Host "Tunnel name: $TunnelName"

$tunnelUrl = Get-TunnelUrl -Name $TunnelName
if ([string]::IsNullOrWhiteSpace($tunnelUrl)) {
    Write-Warning "Could not detect tunnel URL automatically. Run: devtunnel show $TunnelName"
}
else {
    Write-Host "Public URL:" -ForegroundColor Cyan
    Write-Host "  $tunnelUrl" -ForegroundColor White
}

Write-Host ""
Write-Host "Starting host. Keep this terminal open. Stop with Ctrl+C." -ForegroundColor Yellow
devtunnel host $TunnelName
