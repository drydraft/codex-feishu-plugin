#!/bin/sh
set -eu

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
repository_root=$(CDPATH= cd -- "$script_dir/.." && pwd)
plugin_path="$repository_root/plugins/codex-feishu"
default_validator="${HOME}/.codex/skills/.system/plugin-creator/scripts/validate_plugin.py"
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
if [ "${CODEX_PLUGIN_VALIDATOR+x}" = "x" ]; then
    plugin_validator=$CODEX_PLUGIN_VALIDATOR
elif [ -f "$default_validator" ]; then
    plugin_validator=$default_validator
else
    plugin_validator=
fi
if [ "${CODEX_PLUGIN_VALIDATOR+x}" = "x" ] && [ ! -f "$plugin_validator" ]; then
    printf "Codex plugin validator was not found at '%s'. Set CODEX_PLUGIN_VALIDATOR to its validate_plugin.py path.\n" "$plugin_validator" >&2
    exit 1
fi
if [ -z "$plugin_validator" ]; then
    printf "Codex plugin validator is not installed; skipping the optional external validator.\n"
fi
if ! "$python_command" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 9) else 1)'; then
    printf "Python 3.9 or newer is required to run repository verification.\n" >&2
    exit 1
fi

cd "$repository_root"
"$python_command" -m unittest tests.test_repository
if [ -n "$plugin_validator" ]; then
    "$python_command" "$plugin_validator" "$plugin_path"
fi
# By default these invoke: lark-cli --version and lark-cli skills list.
"$lark_cli_command" --version
"$lark_cli_command" skills list
