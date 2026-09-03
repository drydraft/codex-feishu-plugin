---
name: feishu-workflow-router
description: Use when a Feishu or Lark task needs domain routing, profile and identity selection, or a safe lark-cli read or write workflow.
---

# Runtime-discovered Feishu workflow router

Treat the installed official `lark-cli` and its installed `lark-*` skills as runtime truth. This plugin supplies safe routing guidance; it does not vendor skills, call Feishu APIs directly, retain credentials, or assume that a remembered command exists.

## Routing order

Follow this order exactly before a business call:

1. Resolve the target and intent: identify the resource URL/token or identifiers, requested operation, affected records or recipients, and missing required business inputs. Classify it as `read`, `normal-write`, or `high-risk-write`.
2. Verify the CLI locally with `lark-cli --version`. If it is missing or fails, stop and use `$codex-feishu:feishu-setup`; do not guess commands.
3. Discover installed capabilities with `lark-cli skills list`.
4. Read shared runtime rules with `lark-cli skills read lark-shared`.
5. Select the domain using [domain-routing.md](references/domain-routing.md), then read the selected installed skill with `lark-cli skills read <skill>`. Read every reference that the selected skill requires before choosing its business command.
6. Inspect the selected command's help only when its arguments, flags, or availability remain uncertain. Inspect `lark-cli schema` only when the runtime documents a relevant schema/query; do not infer a command, endpoint, field, or flag from memory.
7. Select the configured profile and verify its effective identity before the business operation. Use `lark-cli profile list`, then the current runtime's status/identity commands documented by `lark-shared` or the selected skill. Record the selected profile and redacted identity evidence.
8. Choose identity deliberately: use a **user** identity when the requested action must reflect a person's authority, personal access, ownership, or user-granted sharing; use a **bot/app** identity only when the operation is intentionally app-owned and the target is shared with that app. Do not force either identity as a default. If the expected profile or effective identity cannot be established, stop for correction.
9. For a supported write, run the validated command with `--dry-run` first and inspect its target count, fields, recipients, and reported changes. A missing dry-run capability is not permission to improvise one; state that limitation and follow the selected skill's supported preview or confirmation behavior.
10. Request explicit confirmation immediately before any `high-risk-write`, after presenting the validated target, selected profile/identity, dry-run or preview evidence, and impact. A `high-risk-write` includes destructive actions, bulk updates (including the 200-record Base scenario), broad/external messaging, irreversible permission or approval changes, and other writes the installed skill/help marks as confirmation-required. Preserve upstream confirmation requirements for normal writes too.
11. Execute only the runtime-validated command after the required confirmation. Verify the returned object or follow-up read using the selected skill's documented method.

## Command selection and failures

Prefer a current skill's supported shortcut, then its typed API command, and use its raw API escape hatch only when the runtime documents it and the request needs it. Never authenticate, create configuration, or call a remote API during static validation.

Distinguish and report these separately: unavailable CLI or command, invalid/missing profile or login, insufficient scope, missing resource sharing, invalid user input, and remote API failure. Do not retry, broaden scope, change profile, or change identity merely to turn one class into another.

## Completion report

Never report only “success.” State the target, requested operation, selected profile and effective user/bot identity, command/result evidence or identifiers, verification result, partial failures, and remaining limitations. If execution did not occur, say why and list the exact missing input, runtime capability, confirmation, or authorization.
