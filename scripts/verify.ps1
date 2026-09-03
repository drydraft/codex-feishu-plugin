$ErrorActionPreference = "Stop"

$repositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$pluginPath = Join-Path $repositoryRoot "plugins\codex-feishu"
$defaultValidator = Join-Path $env:USERPROFILE ".codex\skills\.system\plugin-creator\scripts\validate_plugin.py"
$pluginValidator = if ($env:CODEX_PLUGIN_VALIDATOR) { $env:CODEX_PLUGIN_VALIDATOR } else { $defaultValidator }
$larkCliCommand = if ($env:LARK_CLI_COMMAND) { $env:LARK_CLI_COMMAND } else { "lark-cli" }
$env:PYTHONUTF8 = "1"

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

Require-Command -Name "python"
Require-Command -Name $larkCliCommand
if (-not (Test-Path -LiteralPath $pluginValidator -PathType Leaf)) {
    throw "Codex plugin validator was not found at '$pluginValidator'. Set CODEX_PLUGIN_VALIDATOR to its validate_plugin.py path."
}

Push-Location $repositoryRoot
try {
    # These checked argument arrays run: python -m unittest and validate_plugin.py.
    Invoke-Checked -Command "python" -Arguments @("-m", "unittest", "tests.test_repository")
    Invoke-Checked -Command "python" -Arguments @($pluginValidator, $pluginPath)
    # These checked argument arrays run: lark-cli --version and lark-cli skills list.
    Invoke-Checked -Command $larkCliCommand -Arguments @("--version")
    Invoke-Checked -Command $larkCliCommand -Arguments @("skills", "list")
}
finally {
    Pop-Location
}
