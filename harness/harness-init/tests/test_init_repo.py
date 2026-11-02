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
    "domain": "mixed",
    "stack": "python",
    "default_branch": "main",
    "workflow": "extended",
    "ci": "github",
    "commands": {"test": "pytest -q", "lint": "ruff check .", "build": ""},
    "roles": ["developer", "reviewer", "researcher"],
    "tasks": ["feature", "bugfix", "literature", "report", "dataset"],
    "constraints": ["private"],
    "skills": [],
    "science_work": ["literature", "dataset"],
    "science_data": "OpenAlex/DataCite metadata; public",
    "science_outputs": ["html-report", "dataset"],
    "reproducibility": "code, data, env, license",
    "project_mode": "greenfield",
    "dev_specifics": "python, cli, integrations",
    "sdd_setup": "yes",
    "library_contribution": "new-skill",
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
            self.assertIn("sci-literature-news", data["skills"])
            self.assertEqual(data["route"]["sdd"], "/dev-spec-chain")
            self.assertTrue(any(stage["skills"] == "/dev-spec-chain" for stage in data["stages"]))

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
            agents_text = (root / "AGENTS.md").read_text(encoding="utf-8")
            self.assertIn("/dev-spec-chain", agents_text)
            self.assertIn("Научные данные и отчёты", agents_text)
            self.assertIn("Пополнение библиотеки навыков", agents_text)

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