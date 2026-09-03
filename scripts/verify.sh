#!/bin/sh
set -eu

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
repository_root=$(CDPATH= cd -- "$script_dir/.." && pwd)
plugin_path="$repository_root/plugins/codex-feishu"
default_validator="${HOME}/.codex/skills/.system/plugin-creator/scripts/validate_plugin.py"
plugin_validator="${CODEX_PLUGIN_VALIDATOR:-$default_validator}"
python_command="${PYTHON:-python3}"
lark_cli_command="${LARK_CLI_COMMAND:-lark-cli}"
PYTHONUTF8=1
export PYTHONUTF8

require_command() {
    if ! command -v "$1" >/dev/null 2>&1; then
        printf "Missing required command '%s'. Install it, add it to PATH, and run this script again.\n" "$1" >&2
        exit 127
    fi
}

require_command "$python_command"
require_command "$lark_cli_command"
if [ ! -f "$plugin_validator" ]; then
    printf "Codex plugin validator was not found at '%s'. Set CODEX_PLUGIN_VALIDATOR to its validate_plugin.py path.\n" "$plugin_validator" >&2
    exit 1
fi

cd "$repository_root"
"$python_command" -m unittest tests.test_repository
"$python_command" "$plugin_validator" "$plugin_path"
# By default these invoke: lark-cli --version and lark-cli skills list.
"$lark_cli_command" --version
"$lark_cli_command" skills list
