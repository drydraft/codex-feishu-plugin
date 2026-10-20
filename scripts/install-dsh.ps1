<#
.SYNOPSIS
Install the dsh-feishu bundle into a DeepSeek Harness profile.

.DESCRIPTION
Copies plugins/dsh-feishu into <DshHome>/local-plugins/dsh-feishu, links it from
the profile package.json, selects it in dsh.profile.bundles, and runs
`pnpm install` so node_modules resolves it. The desktop app owns its profile,
so it must be restarted before the bundle is loaded.

The script never writes credentials, never touches cordis.patch.yml, and keeps
a timestamped backup of package.json before changing it.

.PARAMETER ProfileName
Profile directory under <DshHome>/profiles. Defaults to "desktop".

.PARAMETER DshHome
Harness home. Defaults to $env:DSH_HOME, then $HOME/.dsh.

.PARAMETER SkipInstall
Only edit the manifest; do not run pnpm install.

.PARAMETER DryRun
Print the planned changes without copying or writing anything.
#>
[CmdletBinding()]
param(
    [string]$ProfileName = "desktop",
    [string]$DshHome,
    [switch]$SkipInstall,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

$repositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$source = Join-Path $repositoryRoot "plugins\dsh-feishu"

function Require-Command {
    param([Parameter(Mandatory = $true)][string]$Name)
    if (-not (Get-Command -Name $Name -ErrorAction SilentlyContinue)) {
        throw "Missing required command '$Name'. Install it, add it to PATH, and run this script again."
    }
}

if (-not $DshHome) {
    if ($env:DSH_HOME) { $DshHome = $env:DSH_HOME } else { $DshHome = Join-Path $HOME ".dsh" }
}

if (-not (Test-Path -LiteralPath $source -PathType Container)) {
    throw "Bundle source not found: $source"
}
$profileDirectory = Join-Path $DshHome (Join-Path "profiles" $ProfileName)
$profileManifest = Join-Path $profileDirectory "package.json"
if (-not (Test-Path -LiteralPath $profileManifest -PathType Leaf)) {
    throw "Profile not found: $profileDirectory (expected package.json)"
}

Require-Command -Name "node"

$arguments = @(
    (Join-Path $PSScriptRoot "apply-dsh-profile.mjs"),
    "--profile", $profileDirectory,
    "--package", $source
)
if ($DryRun) { $arguments += "--dry-run" }

if ($DryRun) {
    Write-Host "[dry-run] copy $source -> $(Join-Path $DshHome 'local-plugins\dsh-feishu')"
    & node @arguments
    exit $LASTEXITCODE
}

& node (Join-Path $PSScriptRoot "apply-dsh-profile.mjs") "--profile" $profileDirectory "--dry-run" | Out-Null
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$destination = Join-Path $DshHome "local-plugins\dsh-feishu"
$temporary = "$destination.staging"
if (Test-Path -LiteralPath $temporary) { Remove-Item -Recurse -Force -LiteralPath $temporary }
New-Item -ItemType Directory -Path (Split-Path -Parent $destination) -Force | Out-Null
Copy-Item -Recurse -LiteralPath $source -Destination $temporary
if (Test-Path -LiteralPath $destination) { Remove-Item -Recurse -Force -LiteralPath $destination }
Move-Item -LiteralPath $temporary -Destination $destination

& node (Join-Path $PSScriptRoot "apply-dsh-profile.mjs") "--profile" $profileDirectory "--package" $destination
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if (-not $SkipInstall) {
    Require-Command -Name "pnpm"
    Push-Location $profileDirectory
    try {
        & pnpm install --prefer-offline
        if ($LASTEXITCODE -ne 0) {
            throw "pnpm install failed in $profileDirectory (exit $LASTEXITCODE)"
        }
    }
    finally {
        Pop-Location
    }
}

$linked = Join-Path $profileDirectory "node_modules\dsh-feishu"
if (-not (Test-Path -LiteralPath $linked)) {
    Write-Warning "node_modules\dsh-feishu is missing. Run 'pnpm install' in $profileDirectory before restarting the app."
}

@"

dsh-feishu installed for profile '$ProfileName'.
  bundle : $destination
  profile: $profileDirectory

Restart the DeepSeek Harness desktop app so the Electron-managed profile
reloads and the bundle's skills appear in the session catalog.
"@ | Write-Host
