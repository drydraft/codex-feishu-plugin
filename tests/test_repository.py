"""Repository-level contract tests for the Codex Feishu plugin."""

import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import tempfile
import unittest
from urllib.parse import unquote, urlsplit


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
POWERSHELL = shutil.which("powershell") or shutil.which("pwsh")
MARKDOWN_LINK = re.compile(r"(?<!!)\[[^\]]*\]\(([^)]+)\)")
FENCED_CODE_BLOCK = re.compile(r"```[^\n]*\n(.*?)```", re.DOTALL)
MAINTAINED_DOCUMENTS = (
    "README.md",
    "docs/deployment.md",
    "docs/superpowers/specs/2026-09-03-codex-feishu-plugin-design.md",
    "docs/superpowers/plans/2026-09-03-codex-feishu-plugin.md",
)


def load_json(relative_path: str) -> dict:
    """Load a JSON fixture relative to the repository root."""
    with (REPOSITORY_ROOT / relative_path).open(encoding="utf-8") as file:
        return json.load(file)


def read(relative_path: str) -> str:
    """Read a UTF-8 repository file for structural contract checks."""
    return (REPOSITORY_ROOT / relative_path).read_text(encoding="utf-8")


def markdown_relative_links(relative_path: str) -> list[tuple[str, Path]]:
    """Resolve local Markdown links and reject paths outside this repository."""
    source = REPOSITORY_ROOT / relative_path
    links = []
    for match in MARKDOWN_LINK.finditer(source.read_text(encoding="utf-8")):
        target = match.group(1).strip().split(maxsplit=1)[0]
        parsed = urlsplit(target)
        if parsed.scheme or parsed.netloc or not parsed.path:
            continue
        if parsed.path.startswith(("/", "\\")):
            raise AssertionError(f"{relative_path} uses an absolute local link: {target}")
        resolved = (source.parent / unquote(parsed.path)).resolve()
        try:
            resolved.relative_to(REPOSITORY_ROOT.resolve())
        except ValueError as error:
            raise AssertionError(
                f"{relative_path} links outside the repository: {target}"
            ) from error
        links.append((target, resolved))
    return links


def fenced_code(relative_path: str) -> str:
    """Return executable examples from Markdown fences without testing prose."""
    return "\n".join(FENCED_CODE_BLOCK.findall(read(relative_path)))


def parse_frontmatter(relative_path: str) -> dict[str, str]:
    """Parse the flat YAML frontmatter shape used by bundled Agent Skills."""
    lines = read(relative_path).splitlines()
    if not lines or lines[0] != "---":
        raise AssertionError(f"{relative_path} has no opening frontmatter delimiter")
    try:
        closing_index = lines.index("---", 1)
    except ValueError as error:
        raise AssertionError(f"{relative_path} has no closing frontmatter delimiter") from error

    metadata = {}
    for line in lines[1:closing_index]:
        match = re.fullmatch(r"([a-z_]+):\s*(.+)", line)
        if not match:
            raise AssertionError(f"Unsupported frontmatter entry in {relative_path}: {line}")
        key, value = match.groups()
        if key in metadata:
            raise AssertionError(f"Duplicate frontmatter key in {relative_path}: {key}")
        metadata[key] = value
    return metadata


def parse_skill_interface(relative_path: str) -> dict[str, str]:
    """Parse the repository's small, quoted-string OpenAI skill metadata mapping."""
    lines = [line for line in read(relative_path).splitlines() if line.strip()]
    if not lines or lines[0] != "interface:":
        raise AssertionError(f"{relative_path} must start with an interface mapping")

    metadata = {}
    for line in lines[1:]:
        match = re.fullmatch(r'  ([a-z_]+):\s*("(?:[^"\\]|\\.)*")', line)
        if not match:
            raise AssertionError(f"Unsupported interface entry in {relative_path}: {line}")
        key, value = match.groups()
        if key in metadata:
            raise AssertionError(f"Duplicate interface key in {relative_path}: {key}")
        metadata[key] = json.loads(value)
    return metadata


def active_yaml_line(line: str) -> str:
    """Remove YAML comments from this workflow's scalar-only subset."""
    return line.split("#", 1)[0].rstrip()


def indentation(line: str) -> int:
    """Return leading-space indentation for the constrained workflow parser."""
    return len(line) - len(line.lstrip(" "))


def parse_validate_workflow() -> dict[str, object]:
    """Inspect the deliberately small YAML subset used by validate.yml without PyYAML."""
    raw_lines = read(".github/workflows/validate.yml").splitlines()
    active_lines = [active_yaml_line(line) for line in raw_lines]

    try:
        permissions_index = next(
            index for index, line in enumerate(active_lines) if line == "permissions:"
        )
    except StopIteration as error:
        raise AssertionError("Workflow has no permissions mapping") from error
    permissions = {}
    for line in active_lines[permissions_index + 1 :]:
        if line and indentation(line) == 0:
            break
        match = re.fullmatch(r"  ([a-z-]+):\s*(\S+)", line)
        if match:
            permissions[match.group(1)] = match.group(2)

    matrix_match = re.search(
        r"^\s*os:\s*\[([^\]]+)\]\s*$", "\n".join(active_lines), re.MULTILINE
    )
    if not matrix_match:
        raise AssertionError("Workflow has no inline operating-system matrix")
    matrix_os = [value.strip() for value in matrix_match.group(1).split(",")]

    steps = []
    step_starts = [
        index
        for index, line in enumerate(active_lines)
        if re.fullmatch(r"\s*- name:\s*.+", line)
    ]
    for position, start in enumerate(step_starts):
        end = step_starts[position + 1] if position + 1 < len(step_starts) else len(raw_lines)
        raw_step = raw_lines[start:end]
        active_step = active_lines[start:end]
        name = active_step[0].split(":", 1)[1].strip()
        step = {"name": name, "run": "", "with": {}, "uses": None, "uses_line": None, "if": None}
        for index, line in enumerate(active_step):
            stripped = line.strip()
            if stripped.startswith("uses:"):
                step["uses"] = stripped.split(":", 1)[1].strip()
                step["uses_line"] = raw_step[index]
            elif stripped.startswith("if:"):
                step["if"] = stripped.split(":", 1)[1].strip()
            elif stripped == "with:":
                with_indent = indentation(line)
                for child in active_step[index + 1 :]:
                    if child.strip() and indentation(child) <= with_indent:
                        break
                    match = re.fullmatch(r"\s+([a-z-]+):\s*(\S+)", child)
                    if match:
                        step["with"][match.group(1)] = match.group(2)
            elif re.fullmatch(r"\s*run:\s*[|>][-+]?\s*", line):
                run_indent = indentation(line)
                run_lines = []
                for child in raw_step[index + 1 :]:
                    if child.strip() and indentation(child) <= run_indent:
                        break
                    if not child.lstrip().startswith("#"):
                        run_lines.append(child.strip())
                step["run"] = "\n".join(run_lines)
            elif match := re.fullmatch(r"\s*run:\s*(\S.*)", line):
                step["run"] = match.group(1)
        steps.append(step)

    return {
        "active_text": "\n".join(active_lines),
        "permissions": permissions,
        "matrix_os": matrix_os,
        "steps": steps,
    }


class RepositoryTests(unittest.TestCase):
    @staticmethod
    def bash_path(path: Path) -> str:
        """Translate Windows paths only when the available Bash is WSL."""
        if os.name != "nt":
            return str(path)
        wsl_probe = subprocess.run(
            ["bash", "-lc", "test -d /mnt/c"], capture_output=True, text=True
        )
        if wsl_probe.returncode == 0:
            drive = path.drive.rstrip(":").lower()
            return "/mnt/" + drive + "/" + path.relative_to(path.drive + "\\").as_posix()
        git_bash_probe = subprocess.run(
            ["bash", "-lc", "test -d /c"], capture_output=True, text=True
        )
        if git_bash_probe.returncode == 0:
            drive = path.drive.rstrip(":").lower()
            return "/" + drive + "/" + path.relative_to(path.drive + "\\").as_posix()
        return str(path)

    def assert_call_subsequence(self, calls: list[str], expected: list[str]) -> None:
        """Assert that observable command calls preserve the required order."""
        cursor = 0
        for call in calls:
            if cursor < len(expected) and call.startswith(expected[cursor]):
                cursor += 1
        self.assertEqual(cursor, len(expected), calls)
        self.assertEqual(calls[cursor:], [])

    def test_call_subsequence_rejects_a_truncated_expected_tail(self):
        """A verifier tail that never runs must not satisfy sequence assertions."""
        with self.assertRaises(AssertionError):
            self.assert_call_subsequence(["python|-m unittest"], ["python|", "lark-cli|--version"])

    def write_windows_fake(
        self, directory: Path, name: str, body: str = "", record_name: str | None = None
    ) -> Path:
        """Create a Windows command shim that records its real invocation."""
        path = directory / f"{name}.cmd"
        path.write_text(
            "@echo off\r\n"
            f"echo {record_name or name}^|%*>>\"%CALL_LOG%\"\r\n"
            f"{body}\r\n"
            "exit /b 0\r\n",
            encoding="utf-8",
        )
        return path

    def write_posix_fake(
        self, directory: Path, name: str, body: str = "", record_name: str | None = None
    ) -> Path:
        """Create a POSIX command shim that records its real invocation."""
        path = directory / name
        with path.open("w", encoding="utf-8", newline="\n") as file:
            file.write(
                "#!/bin/sh\n"
                "arguments=$(printf '%s' \"$*\" | tr '\\n' ' ')\n"
                f"printf '{record_name or name}|%s\\n' \"$arguments\" >> \"$CALL_LOG\"\n"
                f"{body}\n"
                "exit 0\n"
            )
        path.chmod(0o755)
        return path

    def test_marketplace_points_to_plugin(self):
        market = load_json(".agents/plugins/marketplace.json")
        entry = market["plugins"][0]
        self.assertEqual(market["name"], "codex-feishu")
        self.assertEqual(entry["name"], "codex-feishu")
        self.assertEqual(
            entry["source"],
            {"source": "local", "path": "./plugins/codex-feishu"},
        )

    def test_plugin_manifest_is_safe_and_versioned(self):
        plugin = load_json("plugins/codex-feishu/.codex-plugin/plugin.json")
        self.assertEqual(plugin["name"], "codex-feishu")
        self.assertEqual(plugin["version"], "0.1.0")
        self.assertEqual(plugin["license"], "MIT")
        self.assertNotIn("mcpServers", plugin)
        self.assertEqual(plugin["skills"], "./skills/")

    def test_setup_skill_requires_safe_oauth_flow(self):
        """Setup guidance must expose the verified, credential-safe handoff."""
        skill_path = "plugins/codex-feishu/skills/feishu-setup/SKILL.md"
        metadata_path = "plugins/codex-feishu/skills/feishu-setup/agents/openai.yaml"
        reference_path = (
            "plugins/codex-feishu/skills/feishu-setup/references/troubleshooting.md"
        )
        text = read(skill_path)
        frontmatter = parse_frontmatter(skill_path)
        metadata = parse_skill_interface(metadata_path)

        self.assertTrue((REPOSITORY_ROOT / reference_path).is_file())
        self.assertEqual(set(frontmatter), {"name", "description"})
        self.assertEqual(frontmatter["name"], "feishu-setup")
        self.assertTrue(frontmatter["description"])
        for command in (
            "lark-cli skills list",
            "lark-cli config init --new",
            "lark-cli profile list",
            "lark-cli auth status --json --verify",
            "lark-cli whoami",
            "lark-cli doctor --offline",
        ):
            self.assertIn(command, text)
        self.assertIn("troubleshooting.md", text)
        self.assertEqual(
            set(metadata), {"display_name", "short_description", "default_prompt"}
        )
        self.assertNotIn("storage" + ".json", text)
        self.assertNotIn("api" + ".trae", text)

    def test_setup_skill_uses_supported_identity_command(self):
        """Identity verification must not attach an unsupported JSON output flag."""
        paths = (
            "plugins/codex-feishu/skills/feishu-setup/SKILL.md",
            "plugins/codex-feishu/skills/feishu-setup/references/troubleshooting.md",
        )
        skill, reference = (read(path) for path in paths)
        text = "\n".join((skill, reference))

        self.assertRegex(skill, r"(?m)^\s*lark-cli whoami\s*$")
        self.assertIn("`lark-cli whoami`", reference)
        self.assertNotRegex(text, r"(?<![a-z-])whoami\s+--json\b")
        self.assertIn("`lark-cli whoami` already emits JSON", text)
        self.assertIn("installed command help is authoritative", text)

    def test_setup_skill_metadata_uses_public_namespace(self):
        """The invocation prompt must name the plugin's public skill namespace."""
        metadata = parse_skill_interface(
            "plugins/codex-feishu/skills/feishu-setup/agents/openai.yaml"
        )

        self.assertEqual(
            metadata["default_prompt"],
            "Use $codex-feishu:feishu-setup to install and verify Feishu CLI access on this machine.",
        )

    def test_router_discovers_runtime_before_business_calls(self):
        """Router guidance must discover the installed CLI before it operates."""
        text = read("plugins/codex-feishu/skills/feishu-workflow-router/SKILL.md")

        for value in (
            "lark-cli skills list",
            "lark-cli skills read lark-shared",
            "lark-cli skills read <skill>",
            "lark-cli schema",
            "--dry-run",
            "high-risk-write",
        ):
            self.assertIn(value, text)

    def test_router_domain_reference_covers_canonical_domains(self):
        """The routing table must give every supported domain a runtime route."""
        reference = read(
            "plugins/codex-feishu/skills/feishu-workflow-router/"
            "references/domain-routing.md"
        )
        table_rows = {
            line.split("|")[1].strip()
            for line in reference.splitlines()
            if line.startswith("|") and not line.startswith("|-")
        }

        self.assertTrue(
            {
                "docs",
                "drive",
                "wiki",
                "sheets",
                "base",
                "slides",
                "whiteboard",
                "im",
                "calendar",
                "mail",
                "task",
                "approval",
                "attendance",
                "okr",
                "meeting",
                "contact",
                "event",
            }.issubset(table_rows)
        )

    def test_router_metadata_uses_public_namespace(self):
        """The public invocation prompt must name the router's plugin namespace."""
        skill_path = "plugins/codex-feishu/skills/feishu-workflow-router/SKILL.md"
        frontmatter = parse_frontmatter(skill_path)
        metadata = parse_skill_interface(
            "plugins/codex-feishu/skills/feishu-workflow-router/agents/openai.yaml"
        )
        self.assertEqual(set(frontmatter), {"name", "description"})
        self.assertEqual(frontmatter["name"], "feishu-workflow-router")
        self.assertTrue(frontmatter["description"])
        self.assertEqual(
            set(metadata), {"display_name", "short_description", "default_prompt"}
        )

        self.assertEqual(
            metadata["default_prompt"],
            "Use $codex-feishu:feishu-workflow-router to safely route and execute this Feishu task with the installed lark-cli runtime.",
        )

    def test_installers_have_no_secret_or_trae_inputs(self):
        """Installers must not accept credentials or read private Trae state."""
        for path in ("scripts/install.ps1", "scripts/install.sh"):
            text = read(path).lower()
            self.assertNotIn("app_secret", text)
            self.assertNotIn("storage" + ".json", text)
            self.assertNotIn("api" + ".trae", text)
            self.assertIn("plugin marketplace add", text)
            self.assertIn("plugin add codex-feishu@codex-feishu", text)

    def test_verifiers_are_read_only_and_run_required_checks(self):
        """Removing a required safe check or adding auth/business calls is a bug."""
        for path in ("scripts/verify.ps1", "scripts/verify.sh"):
            text = read(path).lower()
            for command in (
                "lark-cli --version",
                "lark-cli skills list",
                "-m unittest",
                "validate_plugin.py",
            ):
                self.assertIn(command, text)
            for prohibited in (
                "auth login",
                "config init",
                "lark-cli api",
                "app_secret",
                "storage" + ".json",
                "api" + ".trae",
            ):
                self.assertNotIn(prohibited, text)

    def test_docs_define_interactive_oauth_boundary(self):
        """Fresh-machine examples must keep OAuth separate from static checks."""
        examples = fenced_code("docs/deployment.md")

        for command in (
            "lark-cli config init --new",
            "lark-cli auth login",
            "lark-cli auth status --json --verify",
            "lark-cli whoami\n",
        ):
            self.assertIn(command, examples)

    def test_maintained_docs_use_the_verified_identity_command(self):
        """Published guidance must never revive the invalid whoami JSON flag."""
        for document in MAINTAINED_DOCUMENTS:
            text = read(document)
            self.assertIn("lark-cli whoami", text, document)
            self.assertNotRegex(text, r"(?<![a-z-])lark-cli\s+whoami\s+--json\b", document)
        for document in ("README.md", "docs/deployment.md"):
            self.assertIn("1.0.93", read(document), document)

    def test_docs_state_the_supported_python_minimum(self):
        """Fresh-machine prerequisites must match the verifier's Python floor and CI."""
        for document in ("README.md", "docs/deployment.md"):
            self.assertIn("Python 3.9", read(document), document)
        workflow = parse_validate_workflow()
        setup_python = next(
            step for step in workflow["steps"] if step["name"] == "Set up Python"
        )
        self.assertEqual(setup_python["with"].get("python-version"), '"3.11"')

    def test_docs_resolve_every_local_markdown_link_inside_the_repository(self):
        """Documentation links must neither break nor escape the checkout."""
        for document in ("README.md", "docs/deployment.md"):
            links = markdown_relative_links(document)
            self.assertTrue(links, f"{document} has no local Markdown links")
            for target, resolved in links:
                self.assertTrue(resolved.is_file(), f"{document} -> {target}")

    def test_deployment_examples_explain_validator_discovery_and_override(self):
        """Fresh machines need executable validator-path and override examples."""
        examples = fenced_code("docs/deployment.md")
        for example in (
            "$env:USERPROFILE\\.codex\\skills\\.system\\plugin-creator\\scripts\\validate_plugin.py",
            "$HOME/.codex/skills/.system/plugin-creator/scripts/validate_plugin.py",
            "$env:CODEX_PLUGIN_VALIDATOR",
            "CODEX_PLUGIN_VALIDATOR=",
        ):
            self.assertIn(example, examples)
        deployment = read("docs/deployment.md").lower()
        self.assertIn("optional external validator", deployment)
        self.assertIn("skipping", deployment)
        self.assertIn("非零", deployment)

    def test_workflow_is_read_only_and_cross_platform(self):
        """CI must execute only deterministic checks with least privileges."""
        workflow = parse_validate_workflow()
        steps = {step["name"]: step for step in workflow["steps"]}
        checkout = steps["Check out repository"]
        setup_python = steps["Set up Python"]

        self.assertEqual(workflow["permissions"], {"contents": "read"})
        self.assertEqual(workflow["matrix_os"], ["windows-latest", "ubuntu-latest"])
        self.assertRegex(checkout["uses"], r"^actions/checkout@[0-9a-f]{40}$")
        self.assertRegex(checkout["uses_line"], r"#\s+v4\s*$")
        self.assertEqual(checkout["with"], {"persist-credentials": "false"})
        self.assertRegex(setup_python["uses"], r"^actions/setup-python@[0-9a-f]{40}$")
        self.assertRegex(setup_python["uses_line"], r"#\s+v5\s*$")

        runs = "\n".join(step["run"] for step in workflow["steps"])
        for command in (
            "python -m unittest discover -s tests -v",
            "test_plugin_manifest_is_safe_and_versioned",
            "test_setup_skill_requires_safe_oauth_flow",
            "test_router_discovers_runtime_before_business_calls",
        ):
            self.assertIn(command, runs)
        self.assertIn("Run selected repository contract tests", steps)
        self.assertNotIn("Validate plugin manifest and bundled skills", steps)
        self.assertIn("runner.os == 'Windows'", steps["Parse PowerShell scripts"]["if"])
        self.assertIn("Parser]::ParseFile", steps["Parse PowerShell scripts"]["run"])
        self.assertIn("runner.os == 'Linux'", steps["Check POSIX shell syntax"]["if"])
        self.assertIn("bash -n scripts/install.sh", steps["Check POSIX shell syntax"]["run"])
        self.assertIn("bash -n scripts/verify.sh", steps["Check POSIX shell syntax"]["run"])
        for prohibited in ("secrets", "auth login", "config init", "lark-cli", "feishu api"):
            self.assertNotIn(prohibited, workflow["active_text"].lower())

    def test_installers_use_json_marketplace_discovery(self):
        """Marketplace state is parsed from Codex JSON, never display columns."""
        self.assertIn(
            '"plugin", "marketplace", "list", "--json"', read("scripts/install.ps1")
        )
        self.assertIn("ConvertFrom-Json", read("scripts/install.ps1"))
        self.assertIn("plugin marketplace list --json", read("scripts/install.sh"))
        self.assertIn("json.load", read("scripts/install.sh"))

    @unittest.skipUnless(POWERSHELL, "PowerShell is required")
    def test_powershell_installer_converges_with_isolated_fake_commands(self):
        """A missing CLI is installed once; reruns preserve marketplace state."""
        with tempfile.TemporaryDirectory(dir=REPOSITORY_ROOT) as temporary_directory:
            temporary = Path(temporary_directory)
            fake_bin = temporary / "bin"
            fake_bin.mkdir()
            call_log = temporary / "calls.log"
            state = temporary / "marketplace-state"
            validator = temporary / "validate_plugin.py"
            validator.write_text("# fake validator\n", encoding="utf-8")
            lark_template = self.write_windows_fake(
                temporary, "runtime-template", record_name="lark-cli"
            )
            self.write_windows_fake(fake_bin, "node")
            self.write_windows_fake(fake_bin, "git")
            self.write_windows_fake(
                fake_bin,
                "codex",
                'if "%1"=="plugin" if "%2"=="marketplace" if "%3"=="list" (\r\n'
                '  if exist "%MARKETPLACE_STATE%" (\r\n'
                '    echo {"marketplaces":[{"name":"codex-feishu","root":"%REPOSITORY_ROOT_JSON%"}]}\r\n'
                '  ) else (\r\n'
                '    echo {"marketplaces":[]}\r\n'
                '  )\r\n'
                '  exit /b 0\r\n'
                ')\r\n'
                'if "%1"=="plugin" if "%2"=="marketplace" if "%3"=="add" type nul > "%MARKETPLACE_STATE%"',
            )
            self.write_windows_fake(
                fake_bin,
                "npx",
                'if "%1"=="@larksuite/cli@latest" copy /Y "%LARK_TEMPLATE%" "%FAKE_BIN%\\%FAKE_LARK_COMMAND%.cmd" >nul',
            )
            self.write_windows_fake(fake_bin, "python", 'if "%1"=="-c" echo 0')

            environment = os.environ.copy()
            for key in tuple(environment):
                if key.lower() == "path":
                    del environment[key]
            environment.update(
                {
                    "PATH": f"{fake_bin}{os.pathsep}C:\\Windows\\System32",
                    "CALL_LOG": str(call_log),
                    "MARKETPLACE_STATE": str(state),
                    "FAKE_BIN": str(fake_bin),
                    "LARK_TEMPLATE": str(lark_template),
                    "LARK_CLI_COMMAND": "fake-lark-cli",
                    "FAKE_LARK_COMMAND": "fake-lark-cli",
                    "CODEX_PLUGIN_VALIDATOR": str(validator),
                    "REPOSITORY_ROOT_JSON": REPOSITORY_ROOT.as_posix(),
                }
            )
            command = [
                POWERSHELL,
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(REPOSITORY_ROOT / "scripts" / "install.ps1"),
            ]
            for _ in range(2):
                result = subprocess.run(
                    command,
                    cwd=REPOSITORY_ROOT,
                    env=environment,
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(result.returncode, 0, result.stderr)

            calls = call_log.read_text(encoding="utf-8").splitlines()
            self.assertEqual(calls.count("npx|@larksuite/cli@latest install"), 1, calls)
            self.assertEqual(
                sum(call.startswith("codex|plugin marketplace add ") for call in calls), 1
            )
            self.assertEqual(calls.count("codex|plugin add codex-feishu@codex-feishu"), 2)
            self.assert_call_subsequence(
                calls[:14],
                [
                    "node|--version",
                    "npx|--version",
                    "git|--version",
                    "codex|--version",
                    "npx|@larksuite/cli@latest install",
                    "lark-cli|--version",
                    "codex|plugin marketplace list --json",
                    "codex|plugin marketplace add ",
                    "codex|plugin add codex-feishu@codex-feishu",
                    "python|-c ",
                    "python|-m unittest tests.test_repository",
                    "python|",
                    "lark-cli|--version",
                    "lark-cli|skills list",
                ],
            )

    @unittest.skipUnless(shutil.which("bash"), "Bash is required")
    def test_shell_installer_converges_with_isolated_fake_commands(self):
        """The POSIX path has the same safe, idempotent observable behavior."""
        with tempfile.TemporaryDirectory(dir=REPOSITORY_ROOT) as temporary_directory:
            temporary = Path(temporary_directory)
            fake_bin = temporary / "bin"
            fake_bin.mkdir()
            call_log = temporary / "calls.log"
            state = temporary / "marketplace-state"
            validator = temporary / "validate_plugin.py"
            validator.write_text("# fake validator\n", encoding="utf-8")
            lark_template = self.write_posix_fake(
                temporary, "runtime-template", record_name="lark-cli"
            )
            for name in ("node", "git", "python3"):
                body = (
                    'if [ "$1" = "-c" ]; then\n'
                    '  case "$(cat)" in\n'
                    '    *codex-feishu*) printf "same\\n" ;;\n'
                    '    *) printf "missing\\n" ;;\n'
                    '  esac\n'
                    'fi'
                    if name == "python3"
                    else ""
                )
                self.write_posix_fake(fake_bin, name, body)
            self.write_posix_fake(
                fake_bin,
                "codex",
                'if [ "$1 $2 $3" = "plugin marketplace list" ]; then\n'
                '  if [ -f "$MARKETPLACE_STATE" ]; then\n'
                '    printf \'%s\\n\' \'{"marketplaces":[{"name":"codex-feishu","root":"%s"}]}\' "$REPOSITORY_ROOT_JSON"\n'
                '  else\n'
                '    printf \'%s\\n\' \'{"marketplaces":[]}\'\n'
                '  fi\n'
                '  exit 0\n'
                'fi\n'
                'if [ "$1 $2 $3" = "plugin marketplace add" ]; then\n'
                '  : > "$MARKETPLACE_STATE"\n'
                'fi',
            )
            self.write_posix_fake(
                fake_bin,
                "npx",
                'if [ "$1" = "@larksuite/cli@latest" ]; then\n'
                '  cp "$LARK_TEMPLATE" "$FAKE_BIN/$FAKE_LARK_COMMAND"\n'
                '  chmod +x "$FAKE_BIN/$FAKE_LARK_COMMAND"\n'
                'fi',
            )
            if os.name == "nt":
                subprocess.run(
                    [
                        "bash",
                        "-lc",
                        f"chmod +x {shlex.quote(self.bash_path(fake_bin))}/*",
                    ],
                    check=True,
            )

            environment = os.environ.copy()
            for key in tuple(environment):
                if key.lower() == "path":
                    del environment[key]
            environment.update(
                {
                    "PATH": f"{self.bash_path(fake_bin)}:/usr/local/bin:/usr/bin:/bin",
                    "CALL_LOG": self.bash_path(call_log),
                    "MARKETPLACE_STATE": self.bash_path(state),
                    "FAKE_BIN": self.bash_path(fake_bin),
                    "LARK_TEMPLATE": self.bash_path(lark_template),
                    "LARK_CLI_COMMAND": "fake-lark-cli",
                    "FAKE_LARK_COMMAND": "fake-lark-cli",
                    "CODEX_PLUGIN_VALIDATOR": self.bash_path(validator),
                    "REPOSITORY_ROOT_JSON": self.bash_path(REPOSITORY_ROOT),
                }
            )
            shell_environment = " ".join(
                f"{key}={shlex.quote(value)}"
                for key, value in environment.items()
                if key
                in {
                    "PATH",
                    "CALL_LOG",
                    "MARKETPLACE_STATE",
                    "FAKE_BIN",
                    "LARK_TEMPLATE",
                    "LARK_CLI_COMMAND",
                    "FAKE_LARK_COMMAND",
                    "CODEX_PLUGIN_VALIDATOR",
                    "REPOSITORY_ROOT_JSON",
                }
            )
            command = [
                "bash",
                "-c",
                f"export {shell_environment}; exec sh {shlex.quote(self.bash_path(REPOSITORY_ROOT / 'scripts' / 'install.sh'))}",
            ]
            for _ in range(2):
                result = subprocess.run(
                    command,
                    cwd=REPOSITORY_ROOT,
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(result.returncode, 0, result.stderr + result.stdout + repr(command))

            calls = call_log.read_text(encoding="utf-8").splitlines()
            self.assertEqual(calls.count("npx|@larksuite/cli@latest install"), 1)
            self.assertEqual(
                sum(call.startswith("codex|plugin marketplace add ") for call in calls), 1
            )
            self.assertEqual(calls.count("codex|plugin add codex-feishu@codex-feishu"), 2)
            self.assert_call_subsequence(
                calls[:15],
                [
                    "node|--version",
                    "npx|--version",
                    "git|--version",
                    "codex|--version",
                    "npx|@larksuite/cli@latest install",
                    "lark-cli|--version",
                    "codex|plugin marketplace list --json",
                    "python3|-c ",
                    "codex|plugin marketplace add ",
                    "codex|plugin add codex-feishu@codex-feishu",
                    "python3|-c ",
                    "python3|-m unittest tests.test_repository",
                    "python3|",
                    "lark-cli|--version",
                    "lark-cli|skills list",
                ],
            )

    @unittest.skipUnless(POWERSHELL, "PowerShell is required")
    def test_powershell_installer_stops_after_marketplace_list_failure(self):
        """A failed marketplace probe must prevent registration, install, and verification."""
        with tempfile.TemporaryDirectory(dir=REPOSITORY_ROOT) as temporary_directory:
            temporary = Path(temporary_directory)
            fake_bin = temporary / "bin"
            fake_bin.mkdir()
            call_log = temporary / "calls.log"
            self.write_windows_fake(fake_bin, "node")
            self.write_windows_fake(fake_bin, "npx")
            self.write_windows_fake(fake_bin, "git")
            self.write_windows_fake(fake_bin, "python")
            self.write_windows_fake(fake_bin, "fake-lark-cli", record_name="lark-cli")
            self.write_windows_fake(
                fake_bin,
                "codex",
                'if "%1"=="plugin" if "%2"=="marketplace" if "%3"=="list" exit /b 41',
            )
            environment = os.environ.copy()
            for key in tuple(environment):
                if key.lower() == "path":
                    del environment[key]
            environment.update(
                {
                    "PATH": f"{fake_bin}{os.pathsep}C:\\Windows\\System32",
                    "CALL_LOG": str(call_log),
                    "LARK_CLI_COMMAND": "fake-lark-cli",
                    "CODEX_PLUGIN_VALIDATOR": str(temporary / "validate_plugin.py"),
                }
            )
            result = subprocess.run(
                [POWERSHELL, "-NoProfile", "-File", str(REPOSITORY_ROOT / "scripts" / "install.ps1")],
                cwd=REPOSITORY_ROOT,
                env=environment,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 41, result.stderr)
            calls = call_log.read_text(encoding="utf-8").splitlines()
            self.assertIn("codex|plugin marketplace list --json", calls)
            self.assertFalse(any("plugin marketplace add" in call for call in calls))
            self.assertFalse(any("plugin add codex-feishu" in call for call in calls))
            self.assertFalse(any(call.startswith("python|") for call in calls))

    @unittest.skipUnless(POWERSHELL, "PowerShell is required")
    def test_powershell_verifier_stops_after_test_failure(self):
        """A failed repository test preserves its code and skips validation/runtime checks."""
        with tempfile.TemporaryDirectory(dir=REPOSITORY_ROOT) as temporary_directory:
            temporary = Path(temporary_directory)
            fake_bin = temporary / "bin"
            fake_bin.mkdir()
            call_log = temporary / "calls.log"
            validator = temporary / "validate_plugin.py"
            validator.write_text("# fake validator\n", encoding="utf-8")
            self.write_windows_fake(fake_bin, "fake-lark-cli", record_name="lark-cli")
            self.write_windows_fake(fake_bin, "python", 'if "%1"=="-m" exit /b 43')
            environment = os.environ.copy()
            for key in tuple(environment):
                if key.lower() == "path":
                    del environment[key]
            environment.update(
                {
                    "PATH": f"{fake_bin}{os.pathsep}C:\\Windows\\System32",
                    "CALL_LOG": str(call_log),
                    "LARK_CLI_COMMAND": "fake-lark-cli",
                    "CODEX_PLUGIN_VALIDATOR": str(validator),
                }
            )
            result = subprocess.run(
                [POWERSHELL, "-NoProfile", "-File", str(REPOSITORY_ROOT / "scripts" / "verify.ps1")],
                cwd=REPOSITORY_ROOT,
                env=environment,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 43, result.stderr)
            calls = call_log.read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(calls), 2)
            self.assertTrue(calls[0].startswith("python|-c "))
            self.assertEqual(calls[1], "python|-m unittest tests.test_repository")

    @unittest.skipUnless(shutil.which("bash"), "Bash is required")
    def test_shell_installer_stops_after_marketplace_list_failure(self):
        """The POSIX installer must preserve the failed marketplace probe status."""
        with tempfile.TemporaryDirectory(dir=REPOSITORY_ROOT) as temporary_directory:
            temporary = Path(temporary_directory)
            fake_bin = temporary / "bin"
            fake_bin.mkdir()
            call_log = temporary / "calls.log"
            for name in ("node", "npx", "git", "python3"):
                self.write_posix_fake(fake_bin, name)
            self.write_posix_fake(fake_bin, "fake-lark-cli", record_name="lark-cli")
            self.write_posix_fake(
                fake_bin,
                "codex",
                'if [ "$1 $2 $3" = "plugin marketplace list" ]; then exit 41; fi',
            )
            if os.name == "nt":
                subprocess.run(
                    ["bash", "-lc", f"chmod +x {shlex.quote(self.bash_path(fake_bin))}/*"],
                    check=True,
                )
            environment = {
                "PATH": f"{self.bash_path(fake_bin)}:/usr/local/bin:/usr/bin:/bin",
                "CALL_LOG": self.bash_path(call_log),
                "LARK_CLI_COMMAND": "fake-lark-cli",
                "CODEX_PLUGIN_VALIDATOR": self.bash_path(temporary / "validate_plugin.py"),
            }
            exported = " ".join(f"{key}={shlex.quote(value)}" for key, value in environment.items())
            result = subprocess.run(
                [
                    "bash",
                    "-c",
                    f"export {exported}; exec sh {shlex.quote(self.bash_path(REPOSITORY_ROOT / 'scripts' / 'install.sh'))}",
                ],
                cwd=REPOSITORY_ROOT,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 41, result.stderr)
            calls = call_log.read_text(encoding="utf-8").splitlines()
            self.assertIn("codex|plugin marketplace list --json", calls)
            self.assertFalse(any("plugin marketplace add" in call for call in calls))
            self.assertFalse(any("plugin add codex-feishu" in call for call in calls))
            self.assertFalse(any(call.startswith("python3|-m") for call in calls))

    @unittest.skipUnless(shutil.which("bash"), "Bash is required")
    def test_shell_verifier_stops_after_test_failure(self):
        """The POSIX verifier must preserve test failure and skip later checks."""
        with tempfile.TemporaryDirectory(dir=REPOSITORY_ROOT) as temporary_directory:
            temporary = Path(temporary_directory)
            fake_bin = temporary / "bin"
            fake_bin.mkdir()
            call_log = temporary / "calls.log"
            validator = temporary / "validate_plugin.py"
            validator.write_text("# fake validator\n", encoding="utf-8")
            self.write_posix_fake(fake_bin, "fake-lark-cli", record_name="lark-cli")
            self.write_posix_fake(
                fake_bin, "python3", 'if [ "$1" = "-m" ]; then exit 43; fi'
            )
            if os.name == "nt":
                subprocess.run(
                    ["bash", "-lc", f"chmod +x {shlex.quote(self.bash_path(fake_bin))}/*"],
                    check=True,
                )
            environment = {
                "PATH": f"{self.bash_path(fake_bin)}:/usr/local/bin:/usr/bin:/bin",
                "CALL_LOG": self.bash_path(call_log),
                "LARK_CLI_COMMAND": "fake-lark-cli",
                "CODEX_PLUGIN_VALIDATOR": self.bash_path(validator),
            }
            exported = " ".join(f"{key}={shlex.quote(value)}" for key, value in environment.items())
            result = subprocess.run(
                [
                    "bash",
                    "-c",
                    f"export {exported}; exec sh {shlex.quote(self.bash_path(REPOSITORY_ROOT / 'scripts' / 'verify.sh'))}",
                ],
                cwd=REPOSITORY_ROOT,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 43, result.stderr)
            calls = call_log.read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(calls), 2)
            self.assertTrue(calls[0].startswith("python3|-c "))
            self.assertEqual(calls[1], "python3|-m unittest tests.test_repository")

    @unittest.skipUnless(POWERSHELL, "PowerShell is required")
    def test_powershell_installer_replaces_a_stale_marketplace_root(self):
        """A same-name marketplace at another root is removed before current-root install."""
        with tempfile.TemporaryDirectory(dir=REPOSITORY_ROOT) as temporary_directory:
            temporary = Path(temporary_directory)
            staged_root = temporary / "repository with spaces"
            shutil.copytree(REPOSITORY_ROOT / "scripts", staged_root / "scripts")
            fake_bin = temporary / "bin"
            fake_bin.mkdir()
            call_log = temporary / "calls.log"
            validator = temporary / "validate_plugin.py"
            validator.write_text("# fake validator\n", encoding="utf-8")
            for name in ("node", "npx", "git", "python"):
                self.write_windows_fake(fake_bin, name, 'if "%1"=="-c" exit /b 0')
            self.write_windows_fake(fake_bin, "fake-lark-cli", record_name="lark-cli")
            self.write_windows_fake(
                fake_bin,
                "codex",
                'if "%1"=="plugin" if "%2"=="marketplace" if "%3"=="list" (echo {"marketplaces":[{"name":"codex-feishu","root":"C:/stale root"}]})',
            )
            environment = os.environ.copy()
            for key in tuple(environment):
                if key.lower() == "path":
                    del environment[key]
            environment.update(
                {
                    "PATH": f"{fake_bin}{os.pathsep}C:\\Windows\\System32",
                    "CALL_LOG": str(call_log),
                    "LARK_CLI_COMMAND": "fake-lark-cli",
                    "CODEX_PLUGIN_VALIDATOR": str(validator),
                }
            )
            result = subprocess.run(
                [POWERSHELL, "-NoProfile", "-File", str(staged_root / "scripts" / "install.ps1")],
                cwd=staged_root,
                env=environment,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            calls = call_log.read_text(encoding="utf-8").splitlines()
            marketplace_add = next(call for call in calls if "plugin marketplace add" in call)
            self.assertIn(str(staged_root), marketplace_add)
            self.assert_call_subsequence(
                calls[5:9],
                [
                    "codex|plugin marketplace list --json",
                    "codex|plugin marketplace remove codex-feishu",
                    "codex|plugin marketplace add ",
                    "codex|plugin add codex-feishu@codex-feishu",
                ],
            )

    @unittest.skipUnless(shutil.which("bash"), "Bash is required")
    def test_shell_installer_replaces_a_stale_marketplace_root(self):
        """The POSIX installer relocates a same-name marketplace before plugin install."""
        with tempfile.TemporaryDirectory(dir=REPOSITORY_ROOT) as temporary_directory:
            temporary = Path(temporary_directory)
            staged_root = temporary / "repository with spaces"
            shutil.copytree(REPOSITORY_ROOT / "scripts", staged_root / "scripts")
            fake_bin = temporary / "bin"
            fake_bin.mkdir()
            call_log = temporary / "calls.log"
            validator = temporary / "validate_plugin.py"
            validator.write_text("# fake validator\n", encoding="utf-8")
            for name in ("node", "npx", "git"):
                self.write_posix_fake(fake_bin, name)
            self.write_posix_fake(fake_bin, "python3", 'if [ "$1" = "-c" ]; then printf "relocate\\n"; fi')
            self.write_posix_fake(fake_bin, "fake-lark-cli", record_name="lark-cli")
            self.write_posix_fake(
                fake_bin,
                "codex",
                'if [ "$1 $2 $3" = "plugin marketplace list" ]; then\n'
                '  printf \'%s\\n\' \'{"marketplaces":[{"name":"codex-feishu","root":"/stale root"}]}\'\n'
                'fi',
            )
            if os.name == "nt":
                subprocess.run(
                    ["bash", "-lc", f"chmod +x {shlex.quote(self.bash_path(fake_bin))}/*"],
                    check=True,
                )
            environment = {
                "PATH": f"{self.bash_path(fake_bin)}:/usr/local/bin:/usr/bin:/bin",
                "CALL_LOG": self.bash_path(call_log),
                "LARK_CLI_COMMAND": "fake-lark-cli",
                "CODEX_PLUGIN_VALIDATOR": self.bash_path(validator),
            }
            exported = " ".join(f"{key}={shlex.quote(value)}" for key, value in environment.items())
            result = subprocess.run(
                [
                    "bash",
                    "-c",
                    f"export {exported}; exec sh {shlex.quote(self.bash_path(staged_root / 'scripts' / 'install.sh'))}",
                ],
                cwd=staged_root,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            calls = call_log.read_text(encoding="utf-8").splitlines()
            marketplace_add = next(call for call in calls if "plugin marketplace add" in call)
            self.assertIn(self.bash_path(staged_root), marketplace_add)
            self.assert_call_subsequence(
                calls[5:10],
                [
                    "codex|plugin marketplace list --json",
                    "python3|-c ",
                    "codex|plugin marketplace remove codex-feishu",
                    "codex|plugin marketplace add ",
                    "codex|plugin add codex-feishu@codex-feishu",
                ],
            )

    @unittest.skipUnless(POWERSHELL, "PowerShell is required")
    def test_powershell_verifier_skips_absent_default_validator_but_rejects_missing_override(self):
        """A fresh install skips no validator, while an explicit bad override is fatal."""
        with tempfile.TemporaryDirectory(dir=REPOSITORY_ROOT) as temporary_directory:
            temporary = Path(temporary_directory)
            fake_bin = temporary / "bin"
            fake_bin.mkdir()
            call_log = temporary / "calls.log"
            self.write_windows_fake(fake_bin, "python", 'if "%1"=="-c" exit /b 0')
            self.write_windows_fake(fake_bin, "fake-lark-cli", record_name="lark-cli")
            base_environment = os.environ.copy()
            for key in tuple(base_environment):
                if key.lower() == "path":
                    del base_environment[key]
            base_environment.update(
                {
                    "PATH": f"{fake_bin}{os.pathsep}C:\\Windows\\System32",
                    "CALL_LOG": str(call_log),
                    "USERPROFILE": str(temporary / "fresh-user"),
                    "LARK_CLI_COMMAND": "fake-lark-cli",
                }
            )
            command = [POWERSHELL, "-NoProfile", "-File", str(REPOSITORY_ROOT / "scripts" / "verify.ps1")]
            result = subprocess.run(command, cwd=REPOSITORY_ROOT, env=base_environment, capture_output=True, text=True, encoding="utf-8", errors="replace")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("lark-cli|skills list", call_log.read_text(encoding="utf-8"))

            explicit_environment = {**base_environment, "CODEX_PLUGIN_VALIDATOR": str(temporary / "missing.py")}
            call_log.unlink()
            result = subprocess.run(command, cwd=REPOSITORY_ROOT, env=explicit_environment, capture_output=True, text=True, encoding="utf-8", errors="replace")
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(call_log.exists())

    @unittest.skipUnless(shutil.which("bash"), "Bash is required")
    def test_shell_verifier_skips_absent_default_validator_but_rejects_missing_override(self):
        """The POSIX verifier has the same fresh-install and explicit-override boundary."""
        with tempfile.TemporaryDirectory(dir=REPOSITORY_ROOT) as temporary_directory:
            temporary = Path(temporary_directory)
            fake_bin = temporary / "bin"
            fake_bin.mkdir()
            call_log = temporary / "calls.log"
            self.write_posix_fake(fake_bin, "python3", 'if [ "$1" = "-c" ]; then exit 0; fi')
            self.write_posix_fake(fake_bin, "fake-lark-cli", record_name="lark-cli")
            if os.name == "nt":
                subprocess.run(["bash", "-lc", f"chmod +x {shlex.quote(self.bash_path(fake_bin))}/*"], check=True)
            base_environment = {
                "PATH": f"{self.bash_path(fake_bin)}:/usr/local/bin:/usr/bin:/bin",
                "CALL_LOG": self.bash_path(call_log),
                "HOME": self.bash_path(temporary / "fresh-user"),
                "LARK_CLI_COMMAND": "fake-lark-cli",
            }
            command = ["bash", "-c", f"export {' '.join(f'{key}={shlex.quote(value)}' for key, value in base_environment.items())}; exec sh {shlex.quote(self.bash_path(REPOSITORY_ROOT / 'scripts' / 'verify.sh'))}"]
            result = subprocess.run(command, cwd=REPOSITORY_ROOT, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("lark-cli|skills list", call_log.read_text(encoding="utf-8"))

            call_log.unlink()
            explicit_environment = {**base_environment, "CODEX_PLUGIN_VALIDATOR": self.bash_path(temporary / "missing.py")}
            command = ["bash", "-c", f"export {' '.join(f'{key}={shlex.quote(value)}' for key, value in explicit_environment.items())}; exec sh {shlex.quote(self.bash_path(REPOSITORY_ROOT / 'scripts' / 'verify.sh'))}"]
            result = subprocess.run(command, cwd=REPOSITORY_ROOT, capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(call_log.exists())

    @unittest.skipUnless(POWERSHELL, "PowerShell is required")
    def test_powershell_verifier_requires_python_39_or_newer(self):
        """An old Python must fail before unit tests, validation, or runtime checks."""
        with tempfile.TemporaryDirectory(dir=REPOSITORY_ROOT) as temporary_directory:
            temporary = Path(temporary_directory)
            fake_bin = temporary / "bin"
            fake_bin.mkdir()
            call_log = temporary / "calls.log"
            validator = temporary / "validator.py"
            validator.write_text("# fake\n", encoding="utf-8")
            self.write_windows_fake(fake_bin, "python", 'if "%1"=="-c" exit /b 1')
            self.write_windows_fake(fake_bin, "fake-lark-cli", record_name="lark-cli")
            environment = os.environ.copy()
            for key in tuple(environment):
                if key.lower() == "path":
                    del environment[key]
            environment.update({"PATH": f"{fake_bin}{os.pathsep}C:\\Windows\\System32", "CALL_LOG": str(call_log), "LARK_CLI_COMMAND": "fake-lark-cli", "CODEX_PLUGIN_VALIDATOR": str(validator)})
            result = subprocess.run([POWERSHELL, "-NoProfile", "-File", str(REPOSITORY_ROOT / "scripts" / "verify.ps1")], cwd=REPOSITORY_ROOT, env=environment, capture_output=True, text=True, encoding="utf-8", errors="replace")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Python 3.9 or newer is required", result.stderr + result.stdout)
            calls = call_log.read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(calls), 1)
            self.assertTrue(calls[0].startswith("python|-c "))

    @unittest.skipUnless(shutil.which("bash"), "Bash is required")
    def test_shell_verifier_requires_python_39_or_newer(self):
        """The POSIX verifier must reject an old Python before other checks."""
        with tempfile.TemporaryDirectory(dir=REPOSITORY_ROOT) as temporary_directory:
            temporary = Path(temporary_directory)
            fake_bin = temporary / "bin"
            fake_bin.mkdir()
            call_log = temporary / "calls.log"
            validator = temporary / "validator.py"
            validator.write_text("# fake\n", encoding="utf-8")
            self.write_posix_fake(fake_bin, "python3", 'if [ "$1" = "-c" ]; then exit 1; fi')
            self.write_posix_fake(fake_bin, "fake-lark-cli", record_name="lark-cli")
            if os.name == "nt":
                subprocess.run(["bash", "-lc", f"chmod +x {shlex.quote(self.bash_path(fake_bin))}/*"], check=True)
            environment = {"PATH": f"{self.bash_path(fake_bin)}:/usr/local/bin:/usr/bin:/bin", "CALL_LOG": self.bash_path(call_log), "LARK_CLI_COMMAND": "fake-lark-cli", "CODEX_PLUGIN_VALIDATOR": self.bash_path(validator)}
            result = subprocess.run(["bash", "-c", f"export {' '.join(f'{key}={shlex.quote(value)}' for key, value in environment.items())}; exec sh {shlex.quote(self.bash_path(REPOSITORY_ROOT / 'scripts' / 'verify.sh'))}"], cwd=REPOSITORY_ROOT, capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(call_log.read_text(encoding="utf-8").splitlines(), ["python3|-c import sys; raise SystemExit(0 if sys.version_info >= (3, 9) else 1)"])
