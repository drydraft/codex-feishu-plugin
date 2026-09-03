$ErrorActionPreference = "Stop"

$repositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$larkCliCommand = if ($env:LARK_CLI_COMMAND) { $env:LARK_CLI_COMMAND } else { "lark-cli" }

function Require-Command {
    param([Parameter(Mandatory = $true)][string]$Name)

    if (-not (Get-Command -Name $Name -ErrorAction SilentlyContinue)) {
        throw "Missing required command '$Name'. Install it, add it to PATH, and run this script again."
    }
}

function Invoke-Checked {
    param(
        [Parameter(Mandatory = $true)][string]$Command,
        [Parameter(Mandatory = $true)][string[]]$Arguments
    )

    & $Command @Arguments
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}

foreach ($command in @("node", "npx", "git", "codex")) {
    Require-Command -Name $command
    Invoke-Checked -Command $command -Arguments @("--version")
}

if (-not (Get-Command -Name $larkCliCommand -ErrorAction SilentlyContinue)) {
    Invoke-Checked -Command "npx" -Arguments @("@larksuite/cli@latest", "install")
}

# By default this invokes: lark-cli --version.
Require-Command -Name $larkCliCommand
Invoke-Checked -Command $larkCliCommand -Arguments @("--version")

$marketplaces = Invoke-Checked -Command "codex" -Arguments @("plugin", "marketplace", "list")
$marketplaceRegistered = $marketplaces | Select-String -Quiet -Pattern "^\s*codex-feishu(?:\s|$)"
if (-not $marketplaceRegistered) {
    # Argument arrays invoke: codex plugin marketplace add <repository root>.
    Invoke-Checked -Command "codex" -Arguments @("plugin", "marketplace", "add", $repositoryRoot)
}

# Argument arrays invoke: codex plugin add codex-feishu@codex-feishu.
Invoke-Checked -Command "codex" -Arguments @("plugin", "add", "codex-feishu@codex-feishu")
& (Join-Path $PSScriptRoot "verify.ps1")
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}
