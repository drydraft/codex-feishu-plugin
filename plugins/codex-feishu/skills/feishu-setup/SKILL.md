---
name: feishu-setup
description: Use when installing, configuring, authenticating, or diagnosing the official Feishu/Lark CLI on a new machine.
---

# Feishu setup and diagnostics

Use the installed `lark-cli` as runtime truth. Start with local, read-only checks; OAuth is an interactive per-machine boundary. Do not reuse local editor session data, place an App Secret or token on a command line, echo credentials, create credential `.env` files, or commit local configuration.

## Read-only discovery

Run these before configuration or login:

```text
lark-cli --version
lark-cli skills list
lark-cli profile list
lark-cli doctor --offline
```

If `lark-cli` is missing, install the official runtime, then open a new shell and repeat the checks:

```text
npx @larksuite/cli@latest install
```

If a command is absent or its flags differ, inspect its installed help and `lark-cli skills list`; do not guess a newer command. Read `lark-cli skills read lark-shared` before selecting scopes or a domain workflow.

## Configure and authenticate

1. Create a separate app configuration with `lark-cli config init --new`. Enter sensitive values only through its protected interactive prompts; keep the app's permissions to the smallest set required for the intended task.
2. Review the required runtime skill and app scopes. Do not claim a scope or API exists without current CLI help, skill, or schema output.
3. Tell the user that login opens an interactive browser flow on this machine, then run `lark-cli auth login`. Do not automate the browser or continue until that flow completes.
4. Verify the selected profile and effective identity:

   ```text
   lark-cli profile list
   lark-cli auth status --json --verify
   lark-cli whoami --json
   ```

Treat this verification as read-only, but it may contact Feishu to validate the current login. Static checks and CI must stop before configuration, authentication, or any remote API call.

## Diagnose before changing anything

Re-run `lark-cli doctor --offline` first. Then classify the symptom using [troubleshooting.md](references/troubleshooting.md): missing CLI, app configuration, login, scope, resource sharing, or remote API. Collect only redacted command output. For a business operation, consult the current matching `lark-*` skill and command help; do not perform a write while diagnosing.
