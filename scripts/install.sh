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
marketplace_action=$(printf '%s\n' "$marketplaces_json" | "$python_command" -c '
import json
import os
import sys

marketplaces = json.load(sys.stdin).get("marketplaces", [])
matching = [item for item in marketplaces if item.get("name") == "codex-feishu"]
if not matching:
    print("missing")
else:
    current_root = os.path.realpath(os.path.abspath(sys.argv[1]))
    marketplace_root = os.path.realpath(os.path.abspath(matching[0].get("root", "")))
    print("same" if marketplace_root == current_root else "relocate")
' "$repository_root")
case "$marketplace_action" in
    missing)
        codex plugin marketplace add "$repository_root"
        ;;
    relocate)
        codex plugin marketplace remove codex-feishu
        codex plugin marketplace add "$repository_root"
        ;;
    same)
        ;;
    *)
        printf "Could not determine the codex-feishu marketplace state.\n" >&2
        exit 1
        ;;
esac

codex plugin add codex-feishu@codex-feishu
sh "$script_dir/verify.sh"
