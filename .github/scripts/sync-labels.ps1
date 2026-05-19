[CmdletBinding()]
param(
    [string]$Repo
)

<#
.SYNOPSIS
Creates/updates GitHub labels idempotently for this repository.

.USAGE
pwsh .github/scripts/sync-labels.ps1
pwsh .github/scripts/sync-labels.ps1 -Repo frdeange/CalabrioMAFVersion
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if (-not $Repo) {
    $Repo = gh repo view --json nameWithOwner --jq .nameWithOwner
}

$labels = @(
    @{ Name = "kind:bug"; Color = "d73a4a"; Description = "Defect or incorrect behavior" },
    @{ Name = "kind:feature"; Color = "a2eeef"; Description = "New feature or capability" },
    @{ Name = "kind:security"; Color = "ee0701"; Description = "Security risk or hardening task" },
    @{ Name = "kind:test"; Color = "0e8a16"; Description = "Test coverage or quality task" },
    @{ Name = "kind:docs"; Color = "0075ca"; Description = "Documentation work" },
    @{ Name = "kind:infra"; Color = "5319e7"; Description = "Infrastructure and environment work" },
    @{ Name = "kind:spike"; Color = "fbca04"; Description = "Time-boxed investigation" },
    @{ Name = "kind:chore"; Color = "cfd3d7"; Description = "Maintenance and housekeeping" },
    @{ Name = "kind:release"; Color = "1d76db"; Description = "Release preparation and execution" },
    @{ Name = "kind:perf"; Color = "fef2c0"; Description = "Performance-focused change" },
    @{ Name = "area:frontend"; Color = "1f883d"; Description = "Angular frontend area" },
    @{ Name = "area:agent-host"; Color = "2ea043"; Description = "Agent host and orchestration layer" },
    @{ Name = "area:mcp-schema"; Color = "3fb950"; Description = "MCP schema provider server" },
    @{ Name = "area:mcp-sqlexec"; Color = "56d364"; Description = "MCP SQL execution server" },
    @{ Name = "area:apim"; Color = "238636"; Description = "API Management policies and config" },
    @{ Name = "area:obs"; Color = "2da44e"; Description = "Observability and telemetry" },
    @{ Name = "area:infra"; Color = "347d39"; Description = "Infrastructure and networking" },
    @{ Name = "area:devops"; Color = "46954a"; Description = "CI/CD and repository operations" },
    @{ Name = "area:tests"; Color = "4ac26b"; Description = "Automated testing area" },
    @{ Name = "area:docs"; Color = "6fdd8b"; Description = "Documentation area" },
    @{ Name = "phase:0a-spike"; Color = "8250df"; Description = "Phase 0a - validation spikes" },
    @{ Name = "phase:0b-foundations"; Color = "8957e5"; Description = "Phase 0b - platform foundations" },
    @{ Name = "phase:1-mcp-base"; Color = "986ee2"; Description = "Phase 1 - MCP baseline" },
    @{ Name = "phase:2-agents"; Color = "a475f9"; Description = "Phase 2 - agent implementation" },
    @{ Name = "phase:3-workflow"; Color = "b083f0"; Description = "Phase 3 - workflow orchestration" },
    @{ Name = "phase:4-host-ui"; Color = "bc8cff"; Description = "Phase 4 - host and UI integration" },
    @{ Name = "phase:5-apim-sec"; Color = "c297ff"; Description = "Phase 5 - APIM and security controls" },
    @{ Name = "phase:6-obs"; Color = "cfb3ff"; Description = "Phase 6 - observability" },
    @{ Name = "phase:7-hardening"; Color = "d8b9ff"; Description = "Phase 7 - hardening and pentest readiness" },
    @{ Name = "phase:8-tuning"; Color = "e2c5ff"; Description = "Phase 8 - tuning and optimization" },
    @{ Name = "squad"; Color = "fb8f44"; Description = "Squad inbox / untriaged issue" },
    @{ Name = "squad:morpheus"; Color = "d97706"; Description = "Assigned to Morpheus (Lead)" },
    @{ Name = "squad:trinity"; Color = "ea580c"; Description = "Assigned to Trinity (Frontend)" },
    @{ Name = "squad:tank"; Color = "f97316"; Description = "Assigned to Tank (Backend)" },
    @{ Name = "squad:mouse"; Color = "f59e0b"; Description = "Assigned to Mouse (MAF)" },
    @{ Name = "squad:apoc"; Color = "fb923c"; Description = "Assigned to Apoc (QA)" },
    @{ Name = "squad:oracle"; Color = "fdba74"; Description = "Assigned to Oracle (Security)" },
    @{ Name = "squad:switch"; Color = "ffb77c"; Description = "Assigned to Switch (DevOps)" }
)

foreach ($label in $labels) {
    gh label create $label.Name --repo $Repo --color $label.Color --description $label.Description --force | Out-Null
    Write-Host "Synced label: $($label.Name)"
}

Write-Host "Label sync complete for $Repo"

