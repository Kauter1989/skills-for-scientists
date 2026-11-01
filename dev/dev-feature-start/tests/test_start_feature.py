import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "start_feature.py"


def run(*args: str, cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def git(root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def make_repo(root: Path) -> None:
    git(root, "init", "-b", "main")
    git(root, "config", "user.email", "test@example.com")
    git(root, "config", "user.name", "Test")
    (root / "README.md").write_text("# test\n", encoding="utf-8")
    git(root, "add", "README.md")
    git(root, "commit", "-m", "init")


class StartFeatureTest(unittest.TestCase):
    def test_creates_branch_and_brief(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_repo(root)
            result = run(
                str(SCRIPT), "demo-feature", "--root", str(root),
                "--plan-item", "P1", "--no-fetch", "--owner", "team",
                cwd=root,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(git(root, "branch", "--show-current").stdout.strip(), "feature/demo-feature")
            brief = root / "docs" / "features" / "demo-feature" / "overview.md"
            self.assertTrue(brief.is_file())
            text = brief.read_text(encoding="utf-8")
            self.assertIn("US-1", text)
            self.assertIn("Красный гейт", text)
            self.assertIn("user", text)
            self.assertIn("not required", text)

    def test_refuses_duplicate_and_dirty_tree(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_repo(root)
            first = run(
                str(SCRIPT), "demo-feature", "--root", str(root),
                "--plan-item", "P1", "--no-fetch", cwd=root,
            )
            self.assertEqual(first.returncode, 0, first.stdout + first.stderr)

            duplicate = run(
                str(SCRIPT), "demo-feature", "--root", str(root),
                "--plan-item", "P1", "--no-fetch", cwd=root,
            )
            self.assertNotEqual(duplicate.returncode, 0)

            git(root, "checkout", "main")
            (root / "dirty.txt").write_text("dirty", encoding="utf-8")
            dirty = run(
                str(SCRIPT), "other-feature", "--root", str(root),
                "--plan-item", "P1", "--no-fetch", cwd=root,
            )
            self.assertNotEqual(dirty.returncode, 0)

    def test_detects_coverage_rule(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_repo(root)
            (root / "pyproject.toml").write_text(
                "[tool.coverage.report]\nfail_under = 80\n", encoding="utf-8"
            )
            git(root, "add", "pyproject.toml")
            git(root, "commit", "-m", "coverage rule")
            result = run(
                str(SCRIPT), "covered-feature", "--root", str(root),
                "--plan-item", "P1", "--no-fetch", cwd=root,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            brief = root / "docs" / "features" / "covered-feature" / "overview.md"
            text = brief.read_text(encoding="utf-8")
            self.assertIn("Требуются: `required`", text)
            self.assertIn("pyproject.toml", text)

    def test_dry_run_does_not_change_repo(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_repo(root)
            result = run(
                str(SCRIPT), "dry-feature", "--root", str(root),
                "--plan-item", "P1", "--no-fetch", "--dry-run", cwd=root,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(git(root, "branch", "--show-current").stdout.strip(), "main")
            self.assertFalse((root / "docs" / "features" / "dry-feature" / "overview.md").exists())


if __name__ == "__main__":
    unittest.main()