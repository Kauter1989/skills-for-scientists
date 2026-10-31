import json
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

AUDIT = Path(__file__).resolve().parents[1] / "scripts" / "audit_library.py"


def skill_md(name: str, description: str, broken_link: bool = False) -> str:
    link = "См. [missing](references/missing.md)." if broken_link else ""
    return textwrap.dedent(
        f"""\
        ---
        name: {name}
        description: >-
          {description}
        license: Apache-2.0
        metadata:
          domain: dev
          contract: harness-skill-template
          version: "0.1.0"
        ---

        # {name}

        {link}

        ## Когда применять

        - при проверке.

        ## Когда не применять

        - когда нужна оценка.

        ## Вход

        - путь.

        ## Процедура

        1. Запустить.

        ## Выход

        - отчёт.

        ## Доказательства

        - код завершения.

        ## Границы

        - не исправляет.

        ## Типовые ошибки

        - запуск без root.

        ## QA

        - [ ] отчёт прочитан.
        """
    )


def make_skill(root: Path, name: str, description: str, broken_link: bool = False, examples: bool = True) -> None:
    skill = root / "dev" / name
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text(skill_md(name, description, broken_link), encoding="utf-8")
    if examples:
        (skill / "examples").mkdir()
        (skill / "examples" / "sample.txt").write_text("sample", encoding="utf-8")


class AuditLibraryTest(unittest.TestCase):
    def test_seeded_defects_are_found(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_skill(root, "dev-valid", "Проверяет одно правило. Use when testing a valid skill.")
            make_skill(root, "dev-dup-a", "Одинаковый триггер для проверки дубля. Use when duplicate.")
            make_skill(root, "dev-dup-b", "Одинаковый триггер для проверки дубля. Use when duplicate.")
            make_skill(root, "dev-no-examples", "Навык без примеров. Use when checking examples.", examples=False)
            make_skill(root, "dev-broken-link", "Навык с битой ссылкой. Use when checking links.", broken_link=True)

            legacy = root / "reports" / "legacy"
            legacy.mkdir(parents=True)
            (legacy / "SKILL.md").write_text("---\nname: legacy\ndescription: Legacy skill.\n---\n", encoding="utf-8")

            html_out = root / "audit.html"
            json_out = root / "audit.json"
            result = subprocess.run(
                [
                    sys.executable, str(AUDIT), "--root", str(root),
                    "--out", str(html_out), "--json-out", str(json_out),
                    "--fail-on", "none",
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertTrue(html_out.is_file())
            self.assertTrue(json_out.is_file())
            html_text = html_out.read_text(encoding="utf-8")
            self.assertIn("<tr>", html_text)
            self.assertNotIn("&lt;tr&gt;", html_text)
            data = json.loads(json_out.read_text(encoding="utf-8"))

            rules = {f["rule"] for f in data["findings"]}
            self.assertIn("дубль триггеров", rules)
            self.assertTrue(any("examples" in rule for rule in rules))
            self.assertIn("битая ссылка", rules)
            self.assertTrue(any("legacy" in rule for rule in rules))
            self.assertGreaterEqual(data["summary"]["blocker"], 1)


if __name__ == "__main__":
    unittest.main()