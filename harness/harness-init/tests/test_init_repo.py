import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INIT = ROOT / "scripts" / "init_repo.py"
CHECK = ROOT / "scripts" / "check_bootstrap.py"

ANSWERS = {
    "project": "example-service",
    "domain": "dev",
    "stack": "python",
    "default_branch": "main",
    "workflow": "minimal",
    "ci": "github",
    "commands": {"test": "pytest -q", "lint": "ruff check .", "build": ""},
    "roles": ["developer", "reviewer"],
    "tasks": ["feature", "bugfix", "report"],
    "constraints": ["private"],
    "skills": [],
    "plugins": ["md-viewer"],
}


def run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


class InitRepoTest(unittest.TestCase):
    def test_plan_requires_approval_and_scaffolds(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            answers = root / "answers.json"
            answers.write_text(json.dumps(ANSWERS, ensure_ascii=False), encoding="utf-8")
            plan = root / "bootstrap-plan.html"
            meta = root / "bootstrap-plan.json"

            result = run(str(INIT), "plan", "--root", str(root), "--answers", str(answers),
                         "--out", str(plan), "--json", str(meta))
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            data = json.loads(meta.read_text(encoding="utf-8"))
            self.assertEqual(data["status"], "draft")
            self.assertTrue(data["skills"])
            self.assertEqual(data["plugins"], ["md-viewer"])

            blocked = run(str(INIT), "apply", "--root", str(root), "--plan-json", str(meta))
            self.assertNotEqual(blocked.returncode, 0)

            approved = run(str(INIT), "approve", "--plan", str(plan), "--json", str(meta))
            self.assertEqual(approved.returncode, 0, approved.stdout + approved.stderr)

            applied = run(str(INIT), "apply", "--root", str(root), "--plan-json", str(meta))
            self.assertEqual(applied.returncode, 0, applied.stdout + applied.stderr)
            self.assertTrue((root / "profile.yml").is_file())
            self.assertTrue((root / "AGENTS.md").is_file())
            self.assertTrue((root / "docs" / "rules" / "registry.yml").is_file())
            self.assertTrue((root / "docs" / "plugins.md").is_file())
            self.assertTrue((root / ".github" / "workflows" / "ci.yml").is_file())

            profile = (root / "profile.yml").read_text(encoding="utf-8")
            self.assertIn("plugins:", profile)
            self.assertIn("- md-viewer", profile)
            agents_text = (root / "AGENTS.md").read_text(encoding="utf-8")
            self.assertIn("md-viewer", agents_text)
            self.assertIn("opencode-plugins/md-viewer/INSTALL.md", agents_text)
            plugins_text = (root / "docs" / "plugins.md").read_text(encoding="utf-8")
            self.assertIn("md-viewer", plugins_text)
            self.assertIn("opencode-plugins/md-viewer/INSTALL.md", plugins_text)

            checked = run(str(CHECK), "--root", str(root))
            self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)

            agents = root / "AGENTS.md"
            agents.write_text("user content", encoding="utf-8")
            again = run(str(INIT), "apply", "--root", str(root), "--plan-json", str(meta))
            self.assertEqual(again.returncode, 0, again.stdout + again.stderr)
            self.assertIn("skip", again.stdout)
            self.assertEqual(agents.read_text(encoding="utf-8"), "user content")

    def test_temporary_plugin_is_marked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            answers = root / "answers.json"
            answers.write_text(
                json.dumps(dict(ANSWERS, plugins=["cae-mesh-mcp"]), ensure_ascii=False),
                encoding="utf-8",
            )
            plan = root / "bootstrap-plan.html"
            meta = root / "bootstrap-plan.json"
            planned = run(
                str(INIT), "plan", "--root", str(root), "--answers", str(answers),
                "--out", str(plan), "--json", str(meta),
            )
            self.assertEqual(planned.returncode, 0, planned.stdout + planned.stderr)
            self.assertIn("temporary", plan.read_text(encoding="utf-8"))
            approved = run(str(INIT), "approve", "--plan", str(plan), "--json", str(meta))
            self.assertEqual(approved.returncode, 0, approved.stdout + approved.stderr)
            applied = run(str(INIT), "apply", "--root", str(root), "--plan-json", str(meta))
            self.assertEqual(applied.returncode, 0, applied.stdout + applied.stderr)
            plugins_text = (root / "docs" / "plugins.md").read_text(encoding="utf-8")
            self.assertIn("cae-mesh-mcp", plugins_text)
            self.assertIn("temporary", plugins_text)
            checked = run(str(CHECK), "--root", str(root))
            self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)

    def test_no_plugins_is_supported(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            answers = root / "answers.json"
            answers.write_text(
                json.dumps(dict(ANSWERS, plugins=[]), ensure_ascii=False),
                encoding="utf-8",
            )
            plan = root / "bootstrap-plan.html"
            meta = root / "bootstrap-plan.json"
            planned = run(
                str(INIT), "plan", "--root", str(root), "--answers", str(answers),
                "--out", str(plan), "--json", str(meta),
            )
            self.assertEqual(planned.returncode, 0, planned.stdout + planned.stderr)
            approved = run(str(INIT), "approve", "--plan", str(plan), "--json", str(meta))
            self.assertEqual(approved.returncode, 0, approved.stdout + approved.stderr)
            applied = run(str(INIT), "apply", "--root", str(root), "--plan-json", str(meta))
            self.assertEqual(applied.returncode, 0, applied.stdout + applied.stderr)

            profile = (root / "profile.yml").read_text(encoding="utf-8")
            self.assertIn("plugins:\n  []", profile)
            plugins_text = (root / "docs" / "plugins.md").read_text(encoding="utf-8")
            self.assertIn("Плагины не выбраны", plugins_text)
            checked = run(str(CHECK), "--root", str(root))
            self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)


if __name__ == "__main__":
    unittest.main()