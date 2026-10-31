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

            blocked = run(str(INIT), "apply", "--root", str(root), "--plan-json", str(meta))
            self.assertNotEqual(blocked.returncode, 0)

            approved = run(str(INIT), "approve", "--plan", str(plan), "--json", str(meta))
            self.assertEqual(approved.returncode, 0, approved.stdout + approved.stderr)

            applied = run(str(INIT), "apply", "--root", str(root), "--plan-json", str(meta))
            self.assertEqual(applied.returncode, 0, applied.stdout + applied.stderr)
            self.assertTrue((root / "profile.yml").is_file())
            self.assertTrue((root / "AGENTS.md").is_file())
            self.assertTrue((root / "docs" / "rules" / "registry.yml").is_file())
            self.assertTrue((root / ".github" / "workflows" / "ci.yml").is_file())

            checked = run(str(CHECK), "--root", str(root))
            self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)

            agents = root / "AGENTS.md"
            agents.write_text("user content", encoding="utf-8")
            again = run(str(INIT), "apply", "--root", str(root), "--plan-json", str(meta))
            self.assertEqual(again.returncode, 0, again.stdout + again.stderr)
            self.assertIn("skip", again.stdout)
            self.assertEqual(agents.read_text(encoding="utf-8"), "user content")


if __name__ == "__main__":
    unittest.main()