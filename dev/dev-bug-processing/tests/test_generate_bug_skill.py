import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GENERATE = ROOT / "scripts" / "generate_bug_skill.py"
CHECK_SKILL = ROOT / "scripts" / "check_bug_skill.py"
CHECK_REPORT = ROOT / "templates" / "check_bug_report.py"
PROBE = ROOT / "templates" / "probe_bug.py"

PYTHON = {
    "repo": "example-service",
    "stack": "python",
    "test_framework": "pytest",
    "test_command": "python -m pytest",
    "test_root": "tests/",
    "tracker": "github",
    "environment": "local",
    "team": "small",
    "compliance": "none",
    "flake_policy": "strict",
    "repro_depth": "standard",
    "approval": "user",
    "approach": "auto",
    "issue_template": "github",
}
CONTAINER = dict(
    PYTHON,
    repo="container-service",
    environment="container",
    team="enterprise",
    compliance="audit",
    repro_depth="deep",
    test_command="docker compose run --rm app python -m pytest",
)
INCIDENT = dict(PYTHON, repo="prod-service", environment="production")
LIGHTWEIGHT = dict(PYTHON, repo="small-service", repro_depth="light")


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
    plan = root / "bug-processing-plan.html"
    meta = root / "bug-processing-plan.json"
    result = run(
        str(GENERATE),
        "plan",
        "--root",
        str(root),
        "--answers",
        str(answers_path),
        "--out",
        str(plan),
        "--json",
        str(meta),
    )
    if result.returncode != 0:
        raise AssertionError(result.stdout + result.stderr)
    return plan, meta


def approve_and_apply(root: Path, plan: Path, meta: Path) -> None:
    approved = run(str(GENERATE), "approve", "--plan", str(plan), "--json", str(meta))
    if approved.returncode != 0:
        raise AssertionError(approved.stdout + approved.stderr)
    applied = run(str(GENERATE), "apply", "--root", str(root), "--plan-json", str(meta))
    if applied.returncode != 0:
        raise AssertionError(applied.stdout + applied.stderr)


def write_complete_report(root: Path, with_test: bool = True) -> Path:
    bug_dir = root / "docs" / "bugs" / "demo"
    bug_dir.mkdir(parents=True, exist_ok=True)
    tests = root / "tests"
    tests.mkdir(parents=True, exist_ok=True)
    if with_test:
        (tests / "test_demo.py").write_text("def test_demo():\n    assert False\n", encoding="utf-8")
    report = {
        "version": 1,
        "id": "demo",
        "status": "reproduced",
        "symptom": "demo returns 3 instead of 2.5",
        "expected": "2.5",
        "actual": "3",
        "environment": "Python 3.12",
        "command": "python -m pytest",
        "runs": 3,
        "results": {"failed": 3, "passed": 0},
        "minimal_case": "demo([1, 2, 3, 4])",
        "removed": ["cli", "file input"],
        "test": {
            "path": "tests/test_demo.py" if with_test else "",
            "name": "tests.test_demo.test_demo",
            "red_output": "AssertionError: 3 != 2.5" if with_test else "",
            "failure_matches_symptom": with_test,
        },
        "diagnosis": {
            "hypotheses": [
                {
                    "claim": "middle element is returned without averaging",
                    "evidence": "only even lengths fail",
                    "confidence": "derived",
                    "next_probe": "check length 2",
                }
            ]
        },
        "probe_path": "docs/bugs/demo/probe.json",
        "next_steps": [],
        "blocked_reason": "",
    }
    (bug_dir / "repro.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    probe = {
        "version": 1,
        "runs": 3,
        "classification": "deterministic-fail",
        "failed": 3,
        "passed": 0,
    }
    (bug_dir / "probe.json").write_text(
        json.dumps(probe, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return bug_dir / "repro.json"


class GenerateBugSkillTest(unittest.TestCase):
    def test_python_profile_generates_and_checks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plan, meta = prepare(root, PYTHON)

            blocked = run(str(GENERATE), "apply", "--root", str(root), "--plan-json", str(meta))
            self.assertNotEqual(blocked.returncode, 0)

            approve_and_apply(root, plan, meta)
            manifest = (root / ".opencode" / "bug-processing.yml").read_text(encoding="utf-8")
            self.assertIn("generated_skill: dev-bug-process", manifest)
            self.assertIn("approach: test-first", manifest)
            self.assertIn("reproducibility: true", manifest)
            self.assertIn("min_runs: 3", manifest)
            self.assertTrue(
                (root / ".opencode" / "skill" / "dev-bug-process" / "SKILL.md").is_file()
            )
            checked = run(str(CHECK_SKILL), "--root", str(root))
            self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)

    def test_container_profile_selects_container_first(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plan, meta = prepare(root, CONTAINER)
            data = json.loads(meta.read_text(encoding="utf-8"))
            self.assertEqual(data["approach"], "container-first")
            self.assertEqual(data["min_runs"], 5)
            approve_and_apply(root, plan, meta)
            manifest = (root / ".opencode" / "bug-processing.yml").read_text(encoding="utf-8")
            self.assertIn("approach: container-first", manifest)
            self.assertIn("min_runs: 5", manifest)

    def test_incident_profile_selects_incident_first(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _, meta = prepare(root, INCIDENT)
            data = json.loads(meta.read_text(encoding="utf-8"))
            self.assertEqual(data["approach"], "incident-first")

    def test_lightweight_profile_selects_lightweight(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _, meta = prepare(root, LIGHTWEIGHT)
            data = json.loads(meta.read_text(encoding="utf-8"))
            self.assertEqual(data["approach"], "lightweight")

    def test_dry_run_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plan, meta = prepare(root, PYTHON)
            approved = run(str(GENERATE), "approve", "--plan", str(plan), "--json", str(meta))
            self.assertEqual(approved.returncode, 0, approved.stdout + approved.stderr)
            dry = run(
                str(GENERATE),
                "apply",
                "--root",
                str(root),
                "--plan-json",
                str(meta),
                "--dry-run",
            )
            self.assertEqual(dry.returncode, 0, dry.stdout + dry.stderr)
            self.assertFalse((root / ".opencode" / "bug-processing.yml").exists())

    def test_check_rejects_false_invariant(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plan, meta = prepare(root, PYTHON)
            approve_and_apply(root, plan, meta)
            manifest_path = root / ".opencode" / "bug-processing.yml"
            manifest = manifest_path.read_text(encoding="utf-8")
            manifest_path.write_text(
                manifest.replace("reproducibility: true", "reproducibility: false"),
                encoding="utf-8",
            )
            checked = run(str(CHECK_SKILL), "--root", str(root))
            self.assertNotEqual(checked.returncode, 0)
            self.assertIn("reproducibility", checked.stdout + checked.stderr)

    def test_apply_does_not_overwrite_without_force(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plan, meta = prepare(root, PYTHON)
            approve_and_apply(root, plan, meta)
            skill = root / ".opencode" / "skill" / "dev-bug-process" / "SKILL.md"
            skill.write_text("local edit\n", encoding="utf-8")
            again = run(str(GENERATE), "apply", "--root", str(root), "--plan-json", str(meta))
            self.assertEqual(again.returncode, 0, again.stdout + again.stderr)
            self.assertEqual(skill.read_text(encoding="utf-8"), "local edit\n")
            forced = run(
                str(GENERATE), "apply", "--root", str(root), "--plan-json", str(meta), "--force"
            )
            self.assertEqual(forced.returncode, 0, forced.stdout + forced.stderr)
            self.assertIn("dev-bug-process", skill.read_text(encoding="utf-8"))


class ProbeBugTest(unittest.TestCase):
    def test_stable_pass_is_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "probe.json"
            probed = run(
                str(PROBE),
                "--runs",
                "2",
                "--out",
                str(out),
                "--",
                sys.executable,
                "-c",
                "print('ok')",
            )
            self.assertEqual(probed.returncode, 0, probed.stdout + probed.stderr)
            data = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(data["classification"], "deterministic-pass")
            self.assertEqual(data["passed"], 2)

    def test_stable_failure_is_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "probe.json"
            probed = run(
                str(PROBE),
                "--runs",
                "2",
                "--out",
                str(out),
                "--",
                sys.executable,
                "-c",
                "raise SystemExit(1)",
            )
            self.assertEqual(probed.returncode, 0, probed.stdout + probed.stderr)
            data = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(data["classification"], "deterministic-fail")
            self.assertEqual(data["failed"], 2)
            self.assertTrue(data["identical_output"])


class CheckBugReportTest(unittest.TestCase):
    def test_complete_report_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report = write_complete_report(root)
            checked = run(
                str(CHECK_REPORT), "--root", str(root), "--report", str(report), "--strict"
            )
            self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)

    def test_missing_test_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report = write_complete_report(root, with_test=False)
            checked = run(
                str(CHECK_REPORT), "--root", str(root), "--report", str(report), "--strict"
            )
            self.assertNotEqual(checked.returncode, 0)
            self.assertIn("test.path", checked.stdout + checked.stderr)

    def test_flaky_is_rejected_in_strict_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report = write_complete_report(root)
            data = json.loads(report.read_text(encoding="utf-8"))
            data["status"] = "flaky"
            data["results"] = {"failed": 1, "passed": 2}
            data["next_steps"] = ["stabilize the test"]
            report.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            probe_path = root / "docs" / "bugs" / "demo" / "probe.json"
            probe = json.loads(probe_path.read_text(encoding="utf-8"))
            probe["classification"] = "flaky"
            probe["failed"] = 1
            probe["passed"] = 2
            probe_path.write_text(json.dumps(probe, ensure_ascii=False, indent=2), encoding="utf-8")
            checked = run(
                str(CHECK_REPORT), "--root", str(root), "--report", str(report), "--strict"
            )
            self.assertNotEqual(checked.returncode, 0)
            self.assertIn("flaky", checked.stdout + checked.stderr)


if __name__ == "__main__":
    unittest.main()