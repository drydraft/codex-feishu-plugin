# Codex Feishu Plugin Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver and locally install a reusable Codex plugin that routes Feishu/Lark tasks through the official `lark-cli` runtime and can be deployed from a private GitHub repository to another machine.

**Architecture:** A repository-local Codex marketplace exposes one `codex-feishu` plugin containing setup and workflow-routing skills. Platform bootstrap and verification scripts install/check the official runtime and register the marketplace, while Python standard-library tests validate the package deterministically without credentials or live API calls.

**Tech Stack:** Codex plugin JSON, Agent Skills Markdown/YAML, PowerShell 7/Windows PowerShell-compatible scripts, POSIX shell, Python 3 standard-library `unittest`, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-09-03-codex-feishu-plugin-design.md`

## Global Constraints

- The repository and original code use the MIT license.
- The official `larksuite/cli` runtime is invoked but not vendored.
- No Trae session files, private product APIs, tokens, App Secrets, `.env` credentials, or private Feishu data enter the repository.
- Runtime truth comes from `lark-cli skills list`, `lark-cli skills read`, command help, and schema output.
- Installation supports Windows, macOS, and Linux; OAuth remains an interactive per-machine step.
- Static verification must not authenticate or call a remote Feishu API.

---

### Task 1: Repository contract and Codex plugin manifest

**Files:**
- Create: `tests/test_repository.py`
- Create: `.agents/plugins/marketplace.json`
- Create: `plugins/codex-feishu/.codex-plugin/plugin.json`
- Create: `LICENSE`

**Interfaces:**
- Consumes: the repository layout defined by the design spec.
- Produces: marketplace name `codex-feishu`, plugin name `codex-feishu`, version `0.1.0`, and `load_json(relative_path: str) -> dict` in the test module.

- [ ] **Step 1: Write failing manifest contract tests**

```python
def test_marketplace_points_to_plugin():
    market = load_json(".agents/plugins/marketplace.json")
    entry = market["plugins"][0]
    assert market["name"] == "codex-feishu"
    assert entry["name"] == "codex-feishu"
    assert entry["source"] == {"source": "local", "path": "./plugins/codex-feishu"}

def test_plugin_manifest_is_safe_and_versioned():
    plugin = load_json("plugins/codex-feishu/.codex-plugin/plugin.json")
    assert plugin["name"] == "codex-feishu"
    assert plugin["version"] == "0.1.0"
    assert plugin["license"] == "MIT"
    assert "mcpServers" not in plugin
    assert plugin["skills"] == "./skills/"
```

- [ ] **Step 2: Run tests and verify missing-file failure**

Run: `python -m unittest tests.test_repository -v`
Expected: FAIL because marketplace and plugin manifest files do not exist.

- [ ] **Step 3: Add the minimal marketplace, plugin manifest, and MIT license**

Create a single local marketplace entry with `AVAILABLE`, `ON_INSTALL`, and `Productivity`; create a strict-semver plugin manifest whose repository/homepage points to `https://github.com/drydraft/codex-feishu-plugin` and whose skill path is `./skills/`.

- [ ] **Step 4: Run the manifest tests and Codex plugin validator**

Run: `python -m unittest tests.test_repository -v`
Expected: PASS.

Run: `python ~/.codex/skills/.system/plugin-creator/scripts/validate_plugin.py plugins/codex-feishu`
Expected: `Plugin validation passed`.

- [ ] **Step 5: Commit the repository contract**

```bash
git add tests/test_repository.py .agents/plugins/marketplace.json plugins/codex-feishu/.codex-plugin/plugin.json LICENSE
git commit -m "feat: add Codex Feishu plugin manifest"
```

### Task 2: Safe setup and diagnostics skill

**Files:**
- Modify: `tests/test_repository.py`
- Create: `plugins/codex-feishu/skills/feishu-setup/SKILL.md`
- Create: `plugins/codex-feishu/skills/feishu-setup/agents/openai.yaml`
- Create: `plugins/codex-feishu/skills/feishu-setup/references/troubleshooting.md`

**Interfaces:**
- Consumes: official `lark-cli` commands `--version`, `skills list`, `config init --new`, `profile list`, `auth login`, `auth status --json --verify`, `whoami --json`, and `doctor --offline`.
- Produces: skill namespace `$codex-feishu:feishu-setup` with a deterministic read-only-first setup and diagnosis workflow.

- [ ] **Step 1: Add failing skill-contract tests**

```python
def test_setup_skill_requires_safe_oauth_flow():
    text = read("plugins/codex-feishu/skills/feishu-setup/SKILL.md")
    for command in ("lark-cli skills list", "lark-cli config init --new", "auth status --json --verify", "whoami --json"):
        assert command in text
    assert "storage.json" not in text
    assert "api.trae" not in text
```

Also validate frontmatter name/description, reference existence, and OpenAI metadata keys.

- [ ] **Step 2: Run the focused tests and verify failure**

Run: `python -m unittest tests.test_repository.RepositoryTests.test_setup_skill_requires_safe_oauth_flow -v`
Expected: FAIL because `feishu-setup/SKILL.md` does not exist.

- [ ] **Step 3: Implement the setup skill and troubleshooting reference**

Document prerequisite checks, installation via `npx @larksuite/cli@latest install`, app initialization, minimal-scope OAuth, profile/identity verification, offline diagnostics, and a table distinguishing missing CLI, app config, login, scope, sharing, and remote API errors. Explicitly prohibit passing secrets on command lines or committing local configuration.

- [ ] **Step 4: Validate the setup skill**

Run: `python -m unittest tests.test_repository -v`
Expected: PASS.

Run: `python ~/.codex/skills/.system/skill-creator/scripts/quick_validate.py plugins/codex-feishu/skills/feishu-setup`
Expected: validation succeeds.

- [ ] **Step 5: Commit the setup skill**

```bash
git add tests/test_repository.py plugins/codex-feishu/skills/feishu-setup
git commit -m "feat: add safe Feishu setup workflow"
```

### Task 3: Runtime-discovered Feishu workflow router

**Files:**
- Modify: `tests/test_repository.py`
- Create: `plugins/codex-feishu/skills/feishu-workflow-router/SKILL.md`
- Create: `plugins/codex-feishu/skills/feishu-workflow-router/agents/openai.yaml`
- Create: `plugins/codex-feishu/skills/feishu-workflow-router/references/domain-routing.md`

**Interfaces:**
- Consumes: a natural-language task plus installed `lark-cli` skill/help/schema output.
- Produces: skill namespace `$codex-feishu:feishu-workflow-router`, domain selection, profile/identity choice, safe command escalation, and evidence-preserving completion reporting.

- [ ] **Step 1: Add failing router contract tests**

```python
def test_router_discovers_runtime_before_business_calls():
    text = read("plugins/codex-feishu/skills/feishu-workflow-router/SKILL.md")
    required = (
        "lark-cli skills list",
        "lark-cli skills read lark-shared",
        "lark-cli skills read <skill>",
        "lark-cli schema",
        "--dry-run",
        "high-risk-write",
    )
    for value in required:
        assert value in text
```

Add a table test asserting the routing reference contains the canonical domains `docs`, `drive`, `wiki`, `sheets`, `base`, `slides`, `whiteboard`, `im`, `calendar`, `mail`, `task`, `approval`, `attendance`, `okr`, `meeting`, `contact`, and `event`.

- [ ] **Step 2: Run focused router tests and verify failure**

Run: `python -m unittest tests.test_repository.RepositoryTests.test_router_discovers_runtime_before_business_calls -v`
Expected: FAIL because the router does not exist.

- [ ] **Step 3: Implement router and domain map**

Implement instruction flow in this exact priority: resolve target and intent; verify CLI; list skills; read `lark-shared`; read matching skill and required references; inspect help/schema only when needed; select profile; select user/bot identity; dry-run supported writes; ask for required confirmation; execute; verify result. Map meetings to the current runtime's meeting-related skill rather than hard-coding legacy aliases.

- [ ] **Step 4: Validate router and complete test suite**

Run: `python -m unittest tests.test_repository -v`
Expected: PASS.

Run: `python ~/.codex/skills/.system/skill-creator/scripts/quick_validate.py plugins/codex-feishu/skills/feishu-workflow-router`
Expected: validation succeeds.

- [ ] **Step 5: Commit the router**

```bash
git add tests/test_repository.py plugins/codex-feishu/skills/feishu-workflow-router
git commit -m "feat: add runtime-discovered Feishu router"
```

### Task 4: Cross-platform installation and verification scripts

**Files:**
- Modify: `tests/test_repository.py`
- Create: `scripts/install.ps1`
- Create: `scripts/install.sh`
- Create: `scripts/verify.ps1`
- Create: `scripts/verify.sh`

**Interfaces:**
- Consumes: repository root, `node`/`npx`, `git`, `codex`, and optional `lark-cli` already installed.
- Produces: idempotent plugin installation, repository marketplace registration, and static/runtime-safe verification with nonzero failures.

- [ ] **Step 1: Add failing script safety tests**

```python
def test_installers_have_no_secret_or_trae_inputs():
    for path in ("scripts/install.ps1", "scripts/install.sh"):
        text = read(path).lower()
        assert "app_secret" not in text
        assert "storage.json" not in text
        assert "api.trae" not in text
        assert "plugin marketplace add" in text
        assert "plugin add codex-feishu@codex-feishu" in text
```

Add checks that both verify scripts run `lark-cli --version`, `lark-cli skills list`, the repository tests, and the Codex plugin validator without calling `auth login` or a business API.

- [ ] **Step 2: Run script tests and verify failure**

Run: `python -m unittest tests.test_repository.RepositoryTests.test_installers_have_no_secret_or_trae_inputs -v`
Expected: FAIL because installers do not exist.

- [ ] **Step 3: Implement idempotent installers and read-only verifiers**

PowerShell uses `$PSScriptRoot`, `Get-Command`, arrays, and checked `$LASTEXITCODE`; shell uses `set -eu`, quoted paths, and `command -v`. Both installers calculate the repository root, install official `lark-cli` only when unavailable, register the repository marketplace, install the named plugin, and invoke the matching verifier. Neither performs OAuth automatically.

- [ ] **Step 4: Run tests and parse checks**

Run: `python -m unittest tests.test_repository -v`
Expected: PASS.

Run: `powershell -NoProfile -Command "$errors=@(); [System.Management.Automation.Language.Parser]::ParseFile((Resolve-Path 'scripts/install.ps1'),[ref]$null,[ref]$errors) | Out-Null; if($errors){exit 1}"`
Expected: exit 0.

Run: `bash -n scripts/install.sh && bash -n scripts/verify.sh`
Expected: exit 0 where Bash is available.

- [ ] **Step 5: Commit the scripts**

```bash
git add tests/test_repository.py scripts
git commit -m "feat: add cross-platform plugin installers"
```

### Task 5: Documentation and continuous validation

**Files:**
- Modify: `tests/test_repository.py`
- Create: `README.md`
- Create: `docs/deployment.md`
- Create: `.github/workflows/validate.yml`

**Interfaces:**
- Consumes: plugin, scripts, and authentication boundary from Tasks 1-4.
- Produces: complete local/fresh-machine instructions and least-privilege CI for Windows and Ubuntu.

- [ ] **Step 1: Add failing documentation and workflow tests**

```python
def test_docs_define_interactive_oauth_boundary():
    deployment = read("docs/deployment.md")
    assert "lark-cli config init --new" in deployment
    assert "lark-cli auth login" in deployment
    assert "不会" in deployment and "App Secret" in deployment

def test_workflow_is_read_only_and_cross_platform():
    workflow = read(".github/workflows/validate.yml")
    assert "contents: read" in workflow
    assert "windows-latest" in workflow
    assert "ubuntu-latest" in workflow
```

- [ ] **Step 2: Run focused tests and verify failure**

Run: `python -m unittest tests.test_repository.RepositoryTests.test_docs_define_interactive_oauth_boundary -v`
Expected: FAIL because deployment documentation does not exist.

- [ ] **Step 3: Write README, deployment guide, and CI workflow**

README covers capabilities, trust boundary, installation, first authentication, update, uninstall, and upstream links. Deployment guide provides separate Windows and macOS/Linux commands, explains per-machine OAuth, and includes a credential-free acceptance checklist. CI checks out code with read-only permissions, installs Python, runs unit tests, checks PowerShell on Windows and shell syntax on Ubuntu, and validates the plugin using repository tests without requiring a Codex account.

- [ ] **Step 4: Run complete local verification**

Run: `python -m unittest discover -s tests -v`
Expected: PASS.

Run: `python ~/.codex/skills/.system/plugin-creator/scripts/validate_plugin.py plugins/codex-feishu`
Expected: `Plugin validation passed`.

- [ ] **Step 5: Commit documentation and CI**

```bash
git add tests/test_repository.py README.md docs/deployment.md .github/workflows/validate.yml
git commit -m "docs: add deployment and validation workflow"
```

### Task 6: Local installation, audit, and GitHub delivery

**Files:**
- Modify only if verification reveals a defect: files owned by Tasks 1-5.

**Interfaces:**
- Consumes: completed repository at version `0.1.0`.
- Produces: installed local plugin, clean Git history, pushed `main`, and visible passing GitHub Actions run.

- [ ] **Step 1: Run secret and residue scans**

Run: `git grep -n -i -E "(ghp_|github_pat_|app_secret[[:space:]]*=|user_access_token[[:space:]]*=|api\.trae|storage\.json|\[TODO|TBD)" -- . ":(exclude)docs/superpowers/**"`
Expected: no output.

- [ ] **Step 2: Install the marketplace and plugin locally**

Run: `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/install.ps1`
Expected: official `lark-cli` is available, marketplace `codex-feishu` is registered, plugin `codex-feishu@codex-feishu` is installed, and static verification passes. Stop only if interactive OAuth is necessary for a live identity check.

- [ ] **Step 3: Verify local Codex discovery**

Run: `codex plugin list`
Expected: `codex-feishu` appears from marketplace `codex-feishu`.

- [ ] **Step 4: Run final verification and inspect changes**

Run: `python -m unittest discover -s tests -v`
Expected: PASS.

Run: `git diff --check && git status --short`
Expected: no whitespace errors and only intentional changes, if any.

- [ ] **Step 5: Push and verify the private remote repository**

```bash
git push -u origin main
gh repo view drydraft/codex-feishu-plugin --json nameWithOwner,visibility,url,defaultBranchRef
gh run list --repo drydraft/codex-feishu-plugin --limit 3
```

Expected: private repository, default branch `main`, and the validation workflow completes successfully.
