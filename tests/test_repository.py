"""Repository-level contract tests for the Codex Feishu plugin."""

import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import tempfile
import unittest


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
POWERSHELL = shutil.which("powershell") or shutil.which("pwsh")


def load_json(relative_path: str) -> dict:
    """Load a JSON fixture relative to the repository root."""
    with (REPOSITORY_ROOT / relative_path).open(encoding="utf-8") as file:
        return json.load(file)


def read(relative_path: str) -> str:
    """Read a UTF-8 repository file for structural contract checks."""
    return (REPOSITORY_ROOT / relative_path).read_text(encoding="utf-8")


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
        metadata = read(metadata_path)

        self.assertTrue((REPOSITORY_ROOT / reference_path).is_file())
        self.assertIn("name: feishu-setup", text)
        self.assertIn("description: Use when", text)
        for command in (
            "lark-cli skills list",
            "lark-cli config init --new",
            "lark-cli profile list",
            "lark-cli auth status --json --verify",
            "lark-cli whoami --json",
            "lark-cli doctor --offline",
        ):
            self.assertIn(command, text)
        self.assertIn("troubleshooting.md", text)
        self.assertIn("display_name:", metadata)
        self.assertIn("short_description:", metadata)
        self.assertIn("default_prompt:", metadata)
        self.assertNotIn("storage" + ".json", text)
        self.assertNotIn("api" + ".trae", text)

    def test_setup_skill_metadata_uses_public_namespace(self):
        """The invocation prompt must name the plugin's public skill namespace."""
        metadata = read("plugins/codex-feishu/skills/feishu-setup/agents/openai.yaml")
        prompt_line = next(
            line
            for line in metadata.splitlines()
            if line.lstrip().startswith("default_prompt:")
        )

        self.assertEqual(
            prompt_line,
            '  default_prompt: "Use $codex-feishu:feishu-setup to install and verify Feishu CLI access on this machine."',
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
        metadata = read(
            "plugins/codex-feishu/skills/feishu-workflow-router/agents/openai.yaml"
        )
        prompt_line = next(
            line
            for line in metadata.splitlines()
            if line.lstrip().startswith("default_prompt:")
        )

        self.assertEqual(
            prompt_line,
            '  default_prompt: "Use $codex-feishu:feishu-workflow-router to safely route and execute this Feishu task with the installed lark-cli runtime."',
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
                '    echo {"marketplaces":[{"name":"codex-feishu"}]}\r\n'
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
                calls[:13],
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
                    '    *codex-feishu*) printf "1\\n" ;;\n'
                    '    *) printf "0\\n" ;;\n'
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
                '    printf \'%s\\n\' \'{"marketplaces":[{"name":"codex-feishu"}]}\'\n'
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
                calls[:14],
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
            self.assertEqual(calls, ["python|-m unittest tests.test_repository"])

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
            self.assertEqual(calls, ["python3|-m unittest tests.test_repository"])
