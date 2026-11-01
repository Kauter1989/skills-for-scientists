import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GENERATE = ROOT / "scripts" / "generate_chain.py"
CHECK = ROOT / "scripts" / "check_spec_chain.py"

GREENFIELD = {
    "repo": "example-service",
    "mode": "greenfield",
    "change_size": "medium",
    "roles": "small",
    "compliance": "none",
    "stack": "python",
    "approval": "user",
    "strict": "standard",
    "approach": "auto",
}
BROWNFIELD = dict(GREENFIELD, repo="legacy-service", mode="brownfield")


def run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def prepare(root: Path, answers: dict) -> tuple[Path, Path]:
    answers_path = root / "answers.json"
    answers_path.write_text(json.dumps(answers, ensure_ascii=False), encoding="utf-8")
    plan = root / "spec-chain-plan.html"
    meta = root / "spec-chain-plan.json"
    result = run(str(GENERATE), "plan", "--root", str(root), "--answers", str(answers_path),
                 "--out", str(plan), "--json", str(meta))
    if result.returncode != 0:
        raise AssertionError(result.stdout + result.stderr)
    return plan, meta


class GenerateChainTest(unittest.TestCase):
    def test_greenfield_requires_approval_and_generates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plan, meta = prepare(root, GREENFIELD)

            blocked = run(str(GENERATE), "apply", "--root", str(root), "--plan-json", str(meta))
            self.assertNotEqual(blocked.returncode, 0)

            approved = run(str(GENERATE), "approve", "--plan", str(plan), "--json", str(meta))
            self.assertEqual(approved.returncode, 0, approved.stdout + approved.stderr)

            applied = run(str(GENERATE), "apply", "--root", str(root), "--plan-json", str(meta))
            self.assertEqual(applied.returncode, 0, applied.stdout + applied.stderr)
            manifest = (root / ".opencode" / "spec-chain.yml").read_text(encoding="utf-8")
            self.assertIn("approach: spec-kit", manifest)
            self.assertTrue((root / ".opencode" / "skill" / "dev-specify" / "SKILL.md").is_file())
            self.assertTrue((root / ".opencode" / "skill" / "dev-implement" / "SKILL.md").is_file())

            checked = run(str(CHECK), "--root", str(root))
            self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)

    def test_brownfield_selects_openspec(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _, meta = prepare(root, BROWNFIELD)
            data = json.loads(meta.read_text(encoding="utf-8"))
            self.assertEqual(data["approach"], "openspec")
            self.assertNotIn("implement", [stage["id"] for stage in data["stages"]])

    def test_dry_run_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plan, meta = prepare(root, GREENFIELD)
            approved = run(str(GENERATE), "approve", "--plan", str(plan), "--json", str(meta))
            self.assertEqual(approved.returncode, 0, approved.stdout + approved.stderr)
            dry = run(str(GENERATE), "apply", "--root", str(root), "--plan-json", str(meta), "--dry-run")
            self.assertEqual(dry.returncode, 0, dry.stdout + dry.stderr)
            self.assertFalse((root / ".opencode" / "spec-chain.yml").exists())


if __name__ == "__main__":
    unittest.main()