"""Contract tests for the DeepSeek Harness bundle and its profile installer."""

import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
BUNDLE_ROOT = REPOSITORY_ROOT / "plugins" / "dsh-feishu"
NODE = shutil.which("node")
POWERSHELL = shutil.which("powershell") or shutil.which("pwsh")
HAS_NODE = NODE is not None


def read(relative_path: str) -> str:
    return (REPOSITORY_ROOT / relative_path).read_text(encoding="utf-8")


def load_json(relative_path: str) -> dict:
    with (REPOSITORY_ROOT / relative_path).open(encoding="utf-8") as file:
        return json.load(file)


def frontmatter(relative_path: str) -> tuple[dict[str, str], str]:
    """Parse the flat frontmatter shape shared by bundled Harness skills."""
    lines = read(relative_path).splitlines()
    if not lines or lines[0] != "---":
        raise AssertionError(f"{relative_path} has no opening frontmatter delimiter")
    closing = lines.index("---", 1)
    metadata = {}
    for line in lines[1:closing]:
        match = re.fullmatch(r"([a-z0-9_-]+):\s*(.+)", line)
        if match:
            metadata[match.group(1)] = match.group(2)
    return metadata, "\n".join(lines[closing + 1 :])


class DshBundleTests(unittest.TestCase):
    def test_manifest_declares_a_bundle_patch_and_resources(self):
        manifest = load_json("plugins/dsh-feishu/package.json")

        self.assertEqual(manifest["name"], "dsh-feishu")
        self.assertEqual(manifest["version"], "0.2.0")
        self.assertEqual(manifest["license"], "MIT")
        self.assertEqual(manifest["type"], "module")
        self.assertEqual(manifest["dsh"]["bundle"]["patch"], "./cordis.patch.yml")
        self.assertIn("./icon", manifest["exports"])
        self.assertIn("./locale/*.json", manifest["exports"])
        for entry in ("index.js", "cordis.patch.yml", "skills", "locale", "icon.svg"):
            self.assertIn(entry, manifest["files"])
        self.assertNotIn("mcpServers", manifest)

    def test_patch_inserts_exactly_one_row(self):
        text = read("plugins/dsh-feishu/cordis.patch.yml")
        active = "\n".join(line.split("#", 1)[0] for line in text.splitlines())

        self.assertIn("- insert:", active)
        self.assertIn("id: dsh-feishu", active)
        self.assertIn("name: dsh-feishu", active)
        self.assertEqual(active.count("id: dsh-feishu"), 1)
        self.assertNotIn("client", active)

    def test_bundled_skills_are_complete_and_model_invocable(self):
        for name in ("feishu-workflow-router", "feishu-setup"):
            metadata, body = frontmatter(f"plugins/dsh-feishu/skills/{name}/SKILL.md")

            self.assertEqual(metadata["name"], name)
            self.assertTrue(metadata["description"].strip())
            self.assertIn("description", metadata)
            # The Harness catalog is model-driven: hiding the skill would defeat
            # the bundle, so the DSH build must not disable model invocation.
            self.assertNotIn("disable-model-invocation", metadata)
            self.assertTrue(body.strip())

    def test_router_keeps_the_runtime_first_safety_order(self):
        text = read("plugins/dsh-feishu/skills/feishu-workflow-router/SKILL.md")

        for marker in (
            "lark-cli --version",
            "lark-cli skills list",
            "lark-cli skills read lark-shared",
            "lark-cli skills read <skill>",
            "--dry-run",
            "high-risk-write",
            "profile list",
        ):
            self.assertIn(marker, text)

    def test_router_reference_covers_current_runtime_domains(self):
        reference = read(
            "plugins/dsh-feishu/skills/feishu-workflow-router/references/domain-routing.md"
        )
        rows = {
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
                "apps",
            }.issubset(rows)
        )

    def test_setup_skill_documents_the_verified_identity_command(self):
        skill = read("plugins/dsh-feishu/skills/feishu-setup/SKILL.md")
        reference = read("plugins/dsh-feishu/skills/feishu-setup/references/troubleshooting.md")
        text = f"{skill}\n{reference}"

        self.assertRegex(skill, r"(?m)^\s*lark-cli whoami\s*$")
        self.assertIn("lark-cli whoami", reference)
        self.assertNotRegex(text, r"(?<![a-z-])whoami\s+--json\b")
        self.assertIn("1.0.98", text)
        self.assertIn("npx @larksuite/cli@latest install", skill)
        self.assertNotIn("storage" + ".json", text)
        self.assertNotIn("api" + ".trae", text)

    def test_bundle_contains_no_credentials_or_private_state(self):
        for path in BUNDLE_ROOT.rglob("*"):
            if not path.is_file():
                continue
            if path.suffix.lower() not in {".md", ".json", ".yml", ".js", ".svg"}:
                continue
            text = path.read_text(encoding="utf-8", errors="replace").lower()
            for prohibited in ("app_secret", "storage" + ".json", "api" + ".trae", "bearer "):
                self.assertNotIn(prohibited, text, str(path))

    @unittest.skipUnless(HAS_NODE, "Node.js is required")
    def test_module_registers_both_skills_and_unwinds_them(self):
        harness = r"""
import { pathToFileURL } from 'node:url';
const module = await import(pathToFileURL(process.argv[2]).href);
const registered = [];
const removed = [];
const service = {
  register(definition) {
    registered.push(definition);
    return () => removed.push(definition.name);
  },
};
const ctx = {
  inject(dependencies, callback) {
    if (dependencies.join(',') !== 'skills') throw new Error('unexpected dependency set');
    const fiber = callback({ get: (name) => (name === 'skills' ? service : undefined) });
    return { dispose: typeof fiber === 'function' ? fiber : () => {} };
  },
};
const dispose = await module.apply(ctx, {});
const summary = registered.map((entry) => ({
  name: entry.name,
  description: Boolean(entry.description),
  source: entry.source,
  path: Boolean(entry.path),
  resourceBase: entry.resourceBase?.kind,
  invocation: entry.invocation,
  content: entry.content.length > 100,
}));
await dispose();
process.stdout.write(JSON.stringify({ summary, removed }, null, 2));
"""
        with tempfile.TemporaryDirectory() as temporary:
            script = Path(temporary) / "harness.mjs"
            script.write_text(harness, encoding="utf-8")
            result = subprocess.run(
                [NODE, str(script), str(BUNDLE_ROOT / "index.js")],
                capture_output=True,
                text=True,
            )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        names = [entry["name"] for entry in payload["summary"]]
        self.assertEqual(names, ["feishu-workflow-router", "feishu-setup"])
        for entry in payload["summary"]:
            self.assertTrue(entry["description"])
            self.assertEqual(entry["source"], "bundled")
            self.assertTrue(entry["path"])
            self.assertEqual(entry["resourceBase"], "directory")
            self.assertTrue(entry["invocation"]["modelInvocable"])
            self.assertTrue(entry["invocation"]["userInvocable"])
            self.assertTrue(entry["content"])
        self.assertEqual(payload["removed"], ["feishu-setup", "feishu-workflow-router"])

    @unittest.skipUnless(HAS_NODE, "Node.js is required")
    def test_module_passes_node_syntax_check(self):
        result = subprocess.run(
            [NODE, "--check", str(BUNDLE_ROOT / "index.js")],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)


class DshProfileTests(unittest.TestCase):
    def run_apply(self, profile: Path, *arguments: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [
                NODE,
                str(REPOSITORY_ROOT / "scripts" / "apply-dsh-profile.mjs"),
                "--profile",
                str(profile),
                *arguments,
            ],
            capture_output=True,
            text=True,
        )

    def make_profile(self, root: Path) -> Path:
        profile = root / "profile"
        profile.mkdir()
        (profile / "package.json").write_text(
            json.dumps(
                {
                    "name": "dsh-profile-test",
                    "private": True,
                    "dependencies": {"existing": "1.0.0"},
                    "dsh": {"profile": {"bundles": ["@deepseek-ai/dsh-base"]}},
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        return profile

    @unittest.skipUnless(HAS_NODE, "Node.js is required")
    def test_apply_is_idempotent_and_reversible(self):
        with tempfile.TemporaryDirectory() as temporary:
            profile = self.make_profile(Path(temporary))
            package = BUNDLE_ROOT

            first = self.run_apply(profile, "--package", str(package))
            self.assertEqual(first.returncode, 0, first.stderr)
            payload = json.loads(first.stdout)
            self.assertTrue(payload["changed"])

            manifest = json.loads((profile / "package.json").read_text(encoding="utf-8"))
            self.assertEqual(
                manifest["dependencies"]["dsh-feishu"],
                "link:" + package.as_posix(),
            )
            self.assertIn("dsh-feishu", manifest["dsh"]["profile"]["bundles"])
            self.assertEqual(manifest["dependencies"]["existing"], "1.0.0")
            self.assertEqual(len(list(profile.glob("package.json.bak-dsh-feishu-*"))), 1)

            second = self.run_apply(profile, "--package", str(package))
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertFalse(json.loads(second.stdout)["changed"])
            self.assertEqual(len(list(profile.glob("package.json.bak-dsh-feishu-*"))), 1)

            removal = self.run_apply(profile, "--remove")
            self.assertEqual(removal.returncode, 0, removal.stderr)
            manifest = json.loads((profile / "package.json").read_text(encoding="utf-8"))
            self.assertNotIn("dsh-feishu", manifest["dependencies"])
            self.assertNotIn("dsh-feishu", manifest["dsh"]["profile"]["bundles"])
            self.assertEqual(manifest["dsh"]["profile"]["bundles"], ["@deepseek-ai/dsh-base"])

    @unittest.skipUnless(HAS_NODE, "Node.js is required")
    def test_apply_refuses_unknown_bundle_or_missing_profile(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            profile = self.make_profile(root)
            other = root / "other"
            other.mkdir()
            (other / "package.json").write_text(
                json.dumps({"name": "not-ours", "dsh": {"bundle": {"patch": "./p"}}}),
                encoding="utf-8",
            )

            wrong_name = self.run_apply(profile, "--package", str(other))
            self.assertNotEqual(wrong_name.returncode, 0)
            self.assertIn("expected", wrong_name.stderr)

            missing = self.run_apply(root / "absent", "--package", str(BUNDLE_ROOT))
            self.assertNotEqual(missing.returncode, 0)

    @unittest.skipUnless(HAS_NODE, "Node.js is required")
    def test_apply_dry_run_changes_nothing(self):
        with tempfile.TemporaryDirectory() as temporary:
            profile = self.make_profile(Path(temporary))
            before = (profile / "package.json").read_bytes()

            result = self.run_apply(profile, "--package", str(BUNDLE_ROOT), "--dry-run")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(json.loads(result.stdout)["dryRun"])
            self.assertEqual((profile / "package.json").read_bytes(), before)
            self.assertEqual(list(profile.glob("package.json.bak-dsh-feishu-*")), [])

    @unittest.skipUnless(HAS_NODE, "Node.js is required")
    def test_apply_requires_a_bundles_array(self):
        with tempfile.TemporaryDirectory() as temporary:
            profile = Path(temporary) / "p"
            profile.mkdir()
            (profile / "package.json").write_text(
                json.dumps({"name": "x", "dsh": {"profile": {}}}), encoding="utf-8"
            )
            result = self.run_apply(profile, "--package", str(BUNDLE_ROOT))
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("dsh.profile.bundles", result.stderr)


class DshScriptTests(unittest.TestCase):
    def test_installer_parses_and_avoids_credentials(self):
        for name in ("install-dsh.ps1", "uninstall-dsh.ps1"):
            text = read(f"scripts/{name}")
            lowered = text.lower()
            for prohibited in ("app_secret", "auth login", "config init", "lark-cli api"):
                self.assertNotIn(prohibited, lowered, name)
            self.assertIn("apply-dsh-profile.mjs", text, name)

        installer = read("scripts/install-dsh.ps1")
        self.assertIn("pnpm install", installer)
        self.assertIn("local-plugins", installer)
        self.assertIn("Restart the DeepSeek Harness desktop app", installer)
        # Every direct invocation must supply the bundle package; the helper
        # refuses to guess which package to link.
        for line in installer.splitlines():
            if "& node" in line and "apply-dsh-profile.mjs" in line:
                self.assertIn("--package", line, line)

    @unittest.skipUnless(POWERSHELL, "PowerShell is required")
    def test_powershell_scripts_parse(self):
        for name in ("install-dsh.ps1", "uninstall-dsh.ps1"):
            result = subprocess.run(
                [
                    POWERSHELL,
                    "-NoProfile",
                    "-Command",
                    (
                        "$errors = @(); "
                        f"[System.Management.Automation.Language.Parser]::ParseFile("
                        f"'{REPOSITORY_ROOT / 'scripts' / name}', [ref]$null, [ref]$errors) | Out-Null; "
                        "if ($errors.Count -gt 0) { $errors | ForEach-Object { Write-Error $_ }; exit 1 }"
                    ),
                ],
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
