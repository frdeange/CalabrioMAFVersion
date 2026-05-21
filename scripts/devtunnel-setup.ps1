param(
    [string]$TunnelName = "calabrio-dev",
    [int]$Port = 8000
)

<#
Creates a persistent DevTunnel and configures a public port mapping for local backend access.
Usage: .\scripts\devtunnel-setup.ps1 [-TunnelName "calabrio-dev"] [-Port 8000]

Cleanup examples:
  devtunnel port delete $TunnelName --port-number $Port
  devtunnel delete $TunnelName
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

Write-Host "=== DevTunnel setup ===" -ForegroundColor Cyan
Write-Host "Tunnel name: $TunnelName"
Write-Host "Port: $Port"

$exists = $true
try {
    devtunnel show $TunnelName 1>$null 2>$null
    if ($LASTEXITCODE -ne 0) {
        $exists = $false
    }
}
catch {
    $exists = $false
}

if (-not $exists) {
    Write-Host "Creating persistent tunnel..." -ForegroundColor Yellow
    devtunnel create --name $TunnelName --allow-anonymous | Out-Host
}
else {
    Write-Host "Tunnel already exists. Reusing it." -ForegroundColor Green
}

$portList = devtunnel port list $TunnelName 2>&1 | Out-String
if ($LASTEXITCODE -ne 0) {
    throw "Could not list ports for tunnel '$TunnelName'."
}

$escapedPort = [regex]::Escape([string]$Port)
$portExists = [regex]::IsMatch($portList, "(^|\D)$escapedPort($|\D)")

if (-not $portExists) {
    Write-Host "Adding port $Port..." -ForegroundColor Yellow
    devtunnel port create $TunnelName --port-number $Port | Out-Host
}
else {
    Write-Host "Port $Port already configured." -ForegroundColor Green
}

$tunnelUrl = Get-TunnelUrl -Name $TunnelName
if ([string]::IsNullOrWhiteSpace($tunnelUrl)) {
    Write-Warning "Could not detect tunnel URL automatically. Run: devtunnel show $TunnelName"
}
else {
    Write-Host ""
    Write-Host "DevTunnel URL for APIM backend-url named value:" -ForegroundColor Cyan
    Write-Host "  $tunnelUrl" -ForegroundColor White
}

Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "  1) Start Docker services: docker compose up --build"
Write-Host "  2) Start tunnel hosting: .\scripts\devtunnel-start.ps1 -TunnelName `"$TunnelName`""
Write-Host "  3) In APIM, set Named Value 'backend-url' to the URL above."
Write-Host ""
Write-Host "To stop hosting: press Ctrl+C in the host terminal." -ForegroundColor DarkGray
