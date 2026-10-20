<#
.SYNOPSIS
Remove the dsh-feishu bundle from a DeepSeek Harness profile.

.PARAMETER ProfileName
Profile directory under <DshHome>/profiles. Defaults to "desktop".

.PARAMETER DshHome
Harness home. Defaults to $env:DSH_HOME, then $HOME/.dsh.

.PARAMETER KeepFiles
Leave <DshHome>/local-plugins/dsh-feishu in place.
#>
[CmdletBinding()]
param(
    [string]$ProfileName = "desktop",
    [string]$DshHome,
    [switch]$KeepFiles
)

$ErrorActionPreference = "Stop"

if (-not $DshHome) {
    if ($env:DSH_HOME) { $DshHome = $env:DSH_HOME } else { $DshHome = Join-Path $HOME ".dsh" }
}

$profileDirectory = Join-Path $DshHome (Join-Path "profiles" $ProfileName)
if (-not (Test-Path -LiteralPath (Join-Path $profileDirectory "package.json"))) {
    throw "Profile not found: $profileDirectory"
}

& node (Join-Path $PSScriptRoot "apply-dsh-profile.mjs") "--profile" $profileDirectory "--remove"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if (-not $KeepFiles) {
    $destination = Join-Path $DshHome "local-plugins\dsh-feishu"
    if (Test-Path -LiteralPath $destination) {
        Remove-Item -Recurse -Force -LiteralPath $destination
        Write-Host "Removed $destination"
    }
}

Write-Host "dsh-feishu removed from profile '$ProfileName'. Restart the desktop app to unload it."
