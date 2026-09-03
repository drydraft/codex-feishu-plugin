#!/bin/sh
set -eu

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
repository_root=$(CDPATH= cd -- "$script_dir/.." && pwd)
lark_cli_command=${LARK_CLI_COMMAND:-lark-cli}

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

if ! command -v "$lark_cli_command" >/dev/null 2>&1; then
    npx @larksuite/cli@latest install
fi

# By default this invokes: lark-cli --version.
require_command "$lark_cli_command"
"$lark_cli_command" --version

marketplaces=$(codex plugin marketplace list)
if ! printf '%s\n' "$marketplaces" | awk '$1 == "codex-feishu" { found = 1 } END { exit !found }'; then
    codex plugin marketplace add "$repository_root"
fi

codex plugin add codex-feishu@codex-feishu
sh "$script_dir/verify.sh"
