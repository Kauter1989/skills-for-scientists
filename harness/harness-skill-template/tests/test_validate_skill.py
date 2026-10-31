import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

VALIDATOR = Path(__file__).resolve().parents[1] / "scripts" / "validate_skill.py"


def valid_skill(name: str) -> str:
    return textwrap.dedent(
        f"""\
        ---
        name: {name}
        description: >-
          Проверяет структуру навыка. Use when testing the validator.
        license: Apache-2.0
        metadata:
          domain: harness
          contract: harness-skill-template
          version: "0.1.0"
        ---

        # {name}

        ## Когда применять

        - при проверке структуры.

        ## Когда не применять

        - когда нужна оценка пользы.

        ## Вход

        - путь к навыку.

        ## Процедура

        1. Запустить валидатор.

        ## Выход

        - отчёт.

        ## Доказательства

        - код завершения.

        ## Границы

        - не проверяет смысл.

        ## Типовые ошибки

        - запуск без --root.

        ## QA

        - [ ] отчёт прочитан.
        """
    )


def invalid_skill(name: str) -> str:
    return textwrap.dedent(
        f"""\
        ---
        name: {name}
        description: Слишком коротко.
        ---

        # {name}

        ## Когда применять

        - всегда.
        """
    )


def run_validator(root: Path, name: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(VALIDATOR), f"harness/{name}", "--root", str(root)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


class ValidateSkillContractTest(unittest.TestCase):
    def test_valid_skill_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            name = "harness-valid"
            skill = root / "harness" / name
            (skill / "examples").mkdir(parents=True)
            (skill / "examples" / "sample.txt").write_text("sample", encoding="utf-8")
            (skill / "SKILL.md").write_text(valid_skill(name), encoding="utf-8")

            result = run_validator(root, name)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_invalid_skill_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            name = "harness-invalid"
            skill = root / "harness" / name
            (skill / "examples").mkdir(parents=True)
            (skill / "examples" / "sample.txt").write_text("sample", encoding="utf-8")
            (skill / "SKILL.md").write_text(invalid_skill(name), encoding="utf-8")

            result = run_validator(root, name)
            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()