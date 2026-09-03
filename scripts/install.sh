#!/bin/sh
set -eu

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
repository_root=$(CDPATH= cd -- "$script_dir/.." && pwd)
lark_cli_command=${LARK_CLI_COMMAND:-lark-cli}
python_command=${PYTHON:-python3}

require_command() {
    if ! command -v "$1" >/dev/null 2>&1; then
        printf "Missing required command '%s'. Install it, add it to PATH, and run this script again.\n" "$1" >&2
        exit 127
    fi
}

for command_name in node npx git codex; do
    require_command "$command_name"
    "$command_name" --version
done
require_command "$python_command"

if ! command -v "$lark_cli_command" >/dev/null 2>&1; then
    npx @larksuite/cli@latest install
fi

# By default this invokes: lark-cli --version.
require_command "$lark_cli_command"
"$lark_cli_command" --version

marketplaces_json=$(codex plugin marketplace list --json)
marketplace_registered=$(printf '%s\n' "$marketplaces_json" | "$python_command" -c '
import json
import sys

marketplaces = json.load(sys.stdin).get("marketplaces", [])
print("1" if any(item.get("name") == "codex-feishu" for item in marketplaces) else "0")
')
if [ "$marketplace_registered" != "1" ]; then
    codex plugin marketplace add "$repository_root"
fi

codex plugin add codex-feishu@codex-feishu
sh "$script_dir/verify.sh"
