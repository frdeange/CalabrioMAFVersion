[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [int]$IssueNumber,

    [Parameter(Mandatory = $true)]
    [ValidatePattern("^squad:[a-z-]+$")]
    [string]$SquadLabel,

    [string]$Repo
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if (-not $Repo) {
    $Repo = gh repo view --json nameWithOwner --jq .nameWithOwner
}

gh issue edit $IssueNumber --repo $Repo --add-label $SquadLabel
Write-Host "Issue #$IssueNumber updated with label '$SquadLabel' in $Repo"

