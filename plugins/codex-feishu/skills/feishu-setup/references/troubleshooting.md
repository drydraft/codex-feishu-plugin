# Feishu CLI troubleshooting

Start with `lark-cli doctor --offline` and preserve only redacted output. It must not authenticate or call a remote API. For the tested `lark-cli 1.0.93`, `lark-cli whoami` already emits JSON; the installed command help is authoritative for another runtime version.

| Class | Evidence | Safe next action |
| --- | --- | --- |
| Missing CLI | Command is not found, or `--version` fails | Install with `npx @larksuite/cli@latest install`; open a new shell and rerun local checks. |
| App configuration | `config init --new` is incomplete or the selected profile is not expected | Create or select the intended app interactively. Keep secrets out of shells, files, logs, and commits. |
| Login | `auth status --json --verify` reports no valid login | Ask the user to complete `auth login` in a browser on this machine; then verify identity. |
| Scope | The CLI or API reports insufficient permission | Read the current relevant `lark-*` skill, command help, and schema; request only the missing least-privilege scope through the app owner. |
| Sharing | Identity is valid but a named document, space, chat, or record is inaccessible | Confirm the effective identity with `lark-cli whoami`, then have the resource owner share only the required resource with that identity. |
| Remote API | Authentication, scopes, and sharing are confirmed but the call returns a service error | Record the redacted status, request ID, and time; check official CLI help/status and retry only when the user authorizes the business operation. |

Do not treat one class as proof of another: a valid login does not grant app scopes or resource sharing, and a remote error does not justify changing credentials.
