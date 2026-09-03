# Codex Feishu Plugin Design

## Objective

Build a reusable Codex plugin that lets Codex route and execute Feishu/Lark work through the official `lark-cli` runtime and its embedded `lark-*` skills. The repository must install cleanly on another Windows, macOS, or Linux machine without copying local credentials.

## Scope

The first release provides:

- a repository-local Codex marketplace;
- one installable `codex-feishu` plugin;
- a workflow router that discovers current `lark-cli` skills and command help at runtime;
- a setup and diagnostics skill for installation, app configuration, OAuth login, identity, profile, and scope checks;
- Windows PowerShell and POSIX shell bootstrap scripts;
- deterministic static tests and GitHub Actions validation;
- Chinese-first documentation with concise English command references.

The first release does not implement a separate MCP server, vendor the official `lark-*` skills, store credentials, or depend on Trae session files or private product APIs.

## Source and licensing strategy

All original repository code is released under MIT. The plugin invokes, but does not vendor, the official MIT-licensed `larksuite/cli` project. No source is copied from GPL-licensed community wrappers. The repository retains its own copyright and license notice while linking to upstream documentation.

## Repository layout

```text
.
├── .agents/plugins/marketplace.json
├── .github/workflows/validate.yml
├── docs/
│   ├── deployment.md
│   └── superpowers/specs/...
├── plugins/codex-feishu/
│   ├── .codex-plugin/plugin.json
│   └── skills/
│       ├── feishu-setup/
│       │   ├── SKILL.md
│       │   ├── agents/openai.yaml
│       │   └── references/troubleshooting.md
│       └── feishu-workflow-router/
│           ├── SKILL.md
│           ├── agents/openai.yaml
│           └── references/domain-routing.md
├── scripts/
│   ├── install.ps1
│   ├── install.sh
│   ├── verify.ps1
│   └── verify.sh
├── tests/
│   └── test_repository.py
├── LICENSE
└── README.md
```

## Runtime architecture

The plugin is an instruction and workflow layer. It never calls Feishu APIs directly.

```text
User request
  -> feishu-workflow-router
  -> verify lark-cli availability/version
  -> lark-cli skills list
  -> lark-cli skills read lark-shared
  -> select and read the matching current lark-* skill
  -> inspect command help/schema when necessary
  -> select profile and user/bot identity explicitly
  -> dry-run supported write operations
  -> execute official lark-cli command
  -> verify and summarize the result
```

`lark-cli skills list`, `lark-cli skills read`, domain help, and schema output are the runtime source of truth. The plugin keeps only a routing index and must not assume the installed CLI exposes a command solely because a newer source tree does.

## Authentication

Setup uses an app owned by the person or organization installing the plugin:

1. Install official `lark-cli`.
2. Run `lark-cli config init --new` to configure the Feishu/Lark app.
3. Run a narrowly scoped `lark-cli auth login` flow.
4. Verify with `lark-cli auth status --json --verify` and `lark-cli whoami`.

Credentials remain in storage managed by `lark-cli`. Bootstrap scripts must never accept secrets as command-line arguments, echo tokens, copy profiles into the repository, or write `.env` files containing credentials.

## Routing behavior

The router classifies requests by resource URL/token and business intent. It maps common domains to current upstream skills, including documents, Drive, Wiki, Sheets, Base, Slides, Whiteboard, IM, Calendar, Mail, Tasks, Approval, Attendance, OKR, meetings, contacts, events, and raw OpenAPI exploration.

Before a business call it must:

- confirm `lark-cli` is available;
- read `lark-shared` and the matching domain skill;
- resolve the configured profile and effective identity;
- distinguish authentication failure, missing scope, missing resource sharing, unsupported runtime command, and remote API failure;
- prefer shortcuts, then typed API commands, then the raw API escape hatch;
- obtain explicit user confirmation for destructive or high-risk writes when required by upstream skill/help.

## Installation and deployment

Bootstrap scripts are idempotent and perform four steps:

1. Check prerequisites (`node`, `npx`, `git`, `codex`).
2. Install or update official `lark-cli` with the upstream installer.
3. Register this repository as a local Codex marketplace.
4. Install `codex-feishu@codex-feishu` and run static/runtime-safe checks.

OAuth remains a separate interactive step because another machine must authorize its own account. Deployment documentation will identify exactly which steps are automatic and which require a browser.

## Error handling and safety

- Missing prerequisites produce an actionable message and nonzero exit code.
- Static verification never authenticates or calls remote Feishu APIs.
- Runtime diagnostics are read-only unless the user explicitly requests a business write.
- Write examples use `--dry-run` where supported.
- No token, App Secret, session file, exported private document, or local profile is committed.
- Commands must not claim a scope or API exists until verified from the installed runtime.

## Testing

The test suite validates:

- marketplace and plugin manifest schemas and path resolution;
- strict semantic versioning and plugin/marketplace name alignment;
- every skill has valid frontmatter and `agents/openai.yaml` metadata;
- required safety and runtime-discovery instructions are present;
- installer scripts contain no credential parameters or Trae session access;
- referenced local files exist;
- PowerShell and shell scripts parse successfully where the runner supports them;
- repository contract tests pass; when locally installed, the optional Codex plugin validator and the skill validators pass.

GitHub Actions runs deterministic tests on Windows and Ubuntu. Live Feishu API calls are excluded from CI because they require user credentials and must not rely on repository secrets for this personal plugin.

## Acceptance criteria

- When locally installed, the optional Codex plugin validator passes.
- The Codex skill validator passes for both bundled skills.
- Repository tests pass on the local Windows machine.
- GitHub Actions configuration is present and least-privilege.
- The local Codex installation lists `codex-feishu` from this repository marketplace.
- A fresh machine can follow the deployment guide through installation up to the interactive Feishu OAuth boundary.
- The repository contains no credentials or generated private data.
