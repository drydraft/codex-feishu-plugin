"""Repository-level contract tests for the Codex Feishu plugin."""

import json
from pathlib import Path
import unittest


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def load_json(relative_path: str) -> dict:
    """Load a JSON fixture relative to the repository root."""
    with (REPOSITORY_ROOT / relative_path).open(encoding="utf-8") as file:
        return json.load(file)


def read(relative_path: str) -> str:
    """Read a UTF-8 repository file for structural contract checks."""
    return (REPOSITORY_ROOT / relative_path).read_text(encoding="utf-8")


class RepositoryTests(unittest.TestCase):
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
        self.assertNotIn("storage.json", text)
        self.assertNotIn("api.trae", text)

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
