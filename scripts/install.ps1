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

function Normalize-PathForComparison {
    param([Parameter(Mandatory = $true)][string]$Path)

    try {
        $normalizedPath = (Resolve-Path -LiteralPath $Path -ErrorAction Stop).Path
    }
    catch {
        $normalizedPath = [IO.Path]::GetFullPath($Path)
    }
    return $normalizedPath.TrimEnd([char[]]@('\', '/'))
}

foreach ($command in @("node", "npx", "git", "codex")) {
    Require-Command -Name $command
    Invoke-Checked -Command $command -Arguments @("--version")
}

Require-Command -Name "python"
& python -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 9) else 1)"
$pythonVersionStatus = $LASTEXITCODE
if ($pythonVersionStatus -ne 0) {
    [Console]::Error.WriteLine("Python 3.9 or newer is required to run the installer.")
    exit $pythonVersionStatus
}

if (-not (Get-Command -Name $larkCliCommand -ErrorAction SilentlyContinue)) {
    Invoke-Checked -Command "npx" -Arguments @("@larksuite/cli@latest", "install")
}

# By default this invokes: lark-cli --version.
Require-Command -Name $larkCliCommand
Invoke-Checked -Command $larkCliCommand -Arguments @("--version")

$marketplacesJson = Invoke-Checked -Command "codex" -Arguments @("plugin", "marketplace", "list", "--json")
try {
    $marketplaces = $marketplacesJson | ConvertFrom-Json -ErrorAction Stop
}
catch {
    throw "Codex returned invalid marketplace JSON: $($_.Exception.Message)"
}
$matchingMarketplaces = @($marketplaces.marketplaces).Where({ $_.name -eq "codex-feishu" })
if ($matchingMarketplaces.Count -eq 0) {
    # Argument arrays invoke: codex plugin marketplace add <repository root>.
    Invoke-Checked -Command "codex" -Arguments @("plugin", "marketplace", "add", $repositoryRoot)
}
else {
    try {
        $currentRoot = Normalize-PathForComparison -Path $repositoryRoot
        $marketplaceRoot = Normalize-PathForComparison -Path $matchingMarketplaces[0].root
        $sameRoot = [String]::Equals(
            $marketplaceRoot,
            $currentRoot,
            [StringComparison]::OrdinalIgnoreCase
        )
    }
    catch {
        $sameRoot = $false
    }

    if (-not $sameRoot) {
        Invoke-Checked -Command "codex" -Arguments @("plugin", "marketplace", "remove", "codex-feishu")
        Invoke-Checked -Command "codex" -Arguments @("plugin", "marketplace", "add", $repositoryRoot)
    }
}

# Argument arrays invoke: codex plugin add codex-feishu@codex-feishu.
Invoke-Checked -Command "codex" -Arguments @("plugin", "add", "codex-feishu@codex-feishu")
& (Join-Path $PSScriptRoot "verify.ps1")
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}
