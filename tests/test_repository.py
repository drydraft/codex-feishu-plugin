"""Repository-level contract tests for the Codex Feishu plugin."""

import json
from pathlib import Path
import unittest


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def load_json(relative_path: str) -> dict:
    """Load a JSON fixture relative to the repository root."""
    with (REPOSITORY_ROOT / relative_path).open(encoding="utf-8") as file:
        return json.load(file)


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
